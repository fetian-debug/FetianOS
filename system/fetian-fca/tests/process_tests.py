#!/usr/bin/env python3
"""Real isolated Linux processes, SQLite crashes, executor death and protocol tests."""
import concurrent.futures
import json
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import stat
import struct
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("FCA_BIN_DIR", ROOT / "target/debug")).resolve()


class RemoteError(Exception):
    def __init__(self, error):
        super().__init__(error["code"])
        self.code = error["code"]


def frame(stream, value):
    data = json.dumps(value).encode()
    stream.sendall(struct.pack(">I", len(data)) + data)


def exact(stream, size):
    data = b""
    while len(data) < size:
        piece = stream.recv(size - len(data))
        if not piece:
            raise EOFError("truncated response")
        data += piece
    return data


class Broker:
    def __init__(self, faults=True):
        self.temp = tempfile.TemporaryDirectory(prefix="fca-process-")
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, XDG_STATE_HOME=str(self.root / "state"),
                        XDG_RUNTIME_DIR=str(self.root / "runtime"))
        self.socket = self.root / "runtime/fetian-fca/authority.sock"
        self.faults = faults
        self.log = (self.root / "daemon.log").open("wb")
        self.process = None
        self.start()

    def start(self):
        command = [str(BIN / "fetian-authorityd")]
        if self.faults:
            command += ["--allow-test-faults"]
        self.process = subprocess.Popen(command, env=self.env, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=self.log)
        self.wait(lambda: self.call("status")["pid"] == self.process.pid,
                  tolerate=(OSError, EOFError, RemoteError))

    def call(self, operation, **arguments):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
            stream.settimeout(10)
            stream.connect(str(self.socket))
            frame(stream, dict(version=1, request_id=1, operation=operation, arguments=arguments))
            size = struct.unpack(">I", exact(stream, 4))[0]
            if not 0 < size <= 65536:
                raise AssertionError("oversize response")
            response = json.loads(exact(stream, size))
            if response["error"]:
                raise RemoteError(response["error"])
            return response["result"]

    @staticmethod
    def wait(predicate, tolerate=(), seconds=12):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except tolerate:
                pass
            time.sleep(0.01)
        raise AssertionError("observable condition timed out")

    def create(self, values=range(1, 129), **contract_changes):
        imported = self.call("import", content="".join(f"{n}\n" for n in values))
        contract = json.loads(subprocess.check_output(
            [str(BIN / "fetian-authority"), "--json", "contract-template", imported["input_id"]]))
        contract.update(contract_changes)
        return self.call("create", contract=contract)["id"]

    def inspect(self, identity):
        return self.call("inspect", id=identity)["authority"]

    def barrier(self, identity):
        return self.wait(lambda: self.call("inspect", id=identity)["test_barrier_reached"])

    def complete(self, identity):
        self.wait(lambda: self.inspect(identity)["lifecycle"] == "Completed")
        return self.call("verify", id=identity)

    def close(self):
        if self.process.poll() is None:
            try:
                self.call("stop")
                self.process.wait(timeout=5)
            except (OSError, EOFError, RemoteError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        self.log.close()
        self.temp.cleanup()


class ProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ("fetian-authority", "fetian-authorityd", "fetian-fca-launcher", "fetian-executor-rust"):
            if not (BIN / name).is_file():
                raise RuntimeError("Run scripts/build-fca.sh before process tests")
        shutil.copyfile(ROOT / "executors/fetian-executor-python.py", BIN / "fetian-executor-python.py")

    def setUp(self):
        self.broker = Broker()
        self.addCleanup(self.broker.close)

    def assert_remote(self, code, operation, **arguments):
        with self.assertRaises(RemoteError) as caught:
            self.broker.call(operation, **arguments)
        self.assertEqual(caught.exception.code, code)

    def test_real_rust_kill_python_resume_demo(self):
        report = json.loads(subprocess.check_output([str(BIN / "fetian-authority"), "--json", "demo-handoff"], timeout=30))
        self.assertTrue(report["passed"])
        self.assertTrue(report["rust_termination_confirmed"])
        self.assertEqual(report["actual_result"], report["expected_result"])
        self.assertEqual(report["verification"]["effects"], 64)
        self.assertNotEqual(report["rust_pid"], report["python_pid"])
        self.assertGreater(report["python_epoch"], report["rust_epoch"])

    def test_both_executors_agree_on_signed_boundaries(self):
        values = [-(2**63), 2**63-1, 1, -3, 4] * 16
        for executor in ("rust", "python"):
            identity = self.broker.create(values)
            self.broker.call("run", id=identity, executor=executor)
            result = self.broker.complete(identity)
            self.assertEqual(result["checkpoint"]["accumulated_result"], sum(values))
            self.assertEqual(result["checkpoint"]["next_input_position"], len(values))

    def test_handoff_suspend_resume_and_checkpoint(self):
        identity = self.broker.create(range(1, 513))
        self.broker.call("run", id=identity, executor="rust", barrier_after=1)
        self.broker.barrier(identity)
        checkpoint = self.broker.call("checkpoint", id=identity)
        self.broker.call("suspend", id=identity)
        self.assertEqual(self.broker.inspect(identity)["continuation"], checkpoint)
        self.assertEqual(self.broker.inspect(identity)["lifecycle"], "Suspended")
        self.broker.call("resume", id=identity)
        self.broker.call("run", id=identity, executor="python", barrier_after=2)
        self.broker.barrier(identity)
        self.broker.call("handoff", id=identity, executor="rust")
        self.assertEqual(self.broker.complete(identity)["effects"], 8)

    def test_cancel_terminal_authority_cannot_resume_or_run(self):
        identity = self.broker.create()
        self.broker.call("run", id=identity, executor="rust", barrier_after=1)
        self.broker.barrier(identity)
        self.broker.call("cancel", id=identity)
        self.assertEqual(self.broker.inspect(identity)["lifecycle"], "Cancelled")
        self.assert_remote("INVALID_STATE", "resume", id=identity)
        self.assert_remote("INVALID_STATE", "run", id=identity, executor="python")
        self.assertEqual(self.broker.call("verify", id=identity)["effects"], 1)

    def test_broker_sigkill_fences_and_recovers_without_pid_kill(self):
        identity = self.broker.create()
        first = self.broker.call("run", id=identity, executor="rust", barrier_after=1)
        self.broker.barrier(identity)
        checkpoint = self.broker.inspect(identity)["continuation"]
        self.broker.process.kill()
        self.broker.process.wait(timeout=5)
        # Parent-death SIGKILL is observable, including a zombie waiting for init.
        def stopped():
            try:
                return Path(f'/proc/{first["pid"]}/stat').read_text().rsplit(")", 1)[1].split()[0] in ("Z", "X")
            except FileNotFoundError:
                return True
        self.broker.wait(stopped)
        self.broker.start()
        recovered = self.broker.inspect(identity)
        self.assertEqual(recovered["lifecycle"], "Ready")
        self.assertEqual(recovered["continuation"], checkpoint)
        self.assertGreater(recovered["epoch"], first["epoch"])
        self.broker.call("run", id=identity, executor="python")
        self.assertEqual(self.broker.complete(identity)["effects"], 2)

    def test_process_crash_before_commit_rolls_back(self):
        self.crash_transaction("before-commit", 0)

    def test_process_crash_after_commit_before_ack_does_not_duplicate(self):
        self.crash_transaction("after-commit", 1)

    def crash_transaction(self, phase, committed):
        identity = self.broker.create()
        self.broker.call("fault-arm", id=identity, phase=phase)
        self.broker.call("run", id=identity, executor="rust")
        self.broker.process.wait(timeout=10)
        self.assertEqual(self.broker.process.returncode, 86 if committed == 0 else 87)
        self.broker.start()
        state = self.broker.inspect(identity)
        if state["lifecycle"] == "Orphaned":
            self.broker.wait(lambda: self.try_resume(identity))
        self.assertEqual(self.broker.call("verify", id=identity)["effects"], committed)
        self.broker.call("run", id=identity, executor="python")
        self.assertEqual(self.broker.complete(identity)["effects"], 2)

    def try_resume(self, identity):
        try:
            self.broker.call("resume", id=identity)
            return True
        except RemoteError as error:
            if error.code != "STOP_UNPROVEN":
                raise
            return False

    def test_strict_resources_fail_before_lease_when_unavailable(self):
        identity = self.broker.create()
        state = self.broker.inspect(identity)
        budget = dict(state["contract"]["resource_budget"], strict=True)
        strict = self.broker.create(resource_budget=budget)
        try:
            launched = self.broker.call("run", id=strict, executor="rust")
        except RemoteError as error:
            self.assertEqual(error.code, "STRICT_RESOURCE_UNAVAILABLE")
            after = self.broker.inspect(strict)
            self.assertEqual(after["epoch"], 0)
            self.assertIsNone(after["current_executor"])
            self.assertEqual(after["lifecycle"], "Ready")
        else:
            self.assertTrue(launched["resources"]["kernel_enforced"])
            self.broker.complete(strict)

    def test_duplicate_run_race_grants_only_one_executor(self):
        identity = self.broker.create()
        def start():
            try:
                return self.broker.call("run", id=identity, executor="rust", barrier_after=1)
            except RemoteError as error:
                return error.code
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: start(), range(2)))
        self.assertEqual(sum(isinstance(value, dict) for value in results), 1)
        self.assertIn("INVALID_STATE", results)
        self.broker.barrier(identity)

    def test_bad_protocol_isolated_from_broker(self):
        for payload in (b"\0\x01\0\x01", b"\0\0\0\x02{"):
            with socket.socket(socket.AF_UNIX) as stream:
                stream.connect(str(self.broker.socket))
                stream.sendall(payload)
                stream.shutdown(socket.SHUT_WR)
        self.assert_remote("UNKNOWN_OPERATION", "shell", command="touch /tmp/forbidden")
        self.assert_remote("UNKNOWN_FIELD", "status", path="/etc/passwd")
        self.assertTrue(self.broker.call("status")["running"])
        with socket.socket(socket.AF_UNIX) as stream:
            stream.connect(str(self.broker.socket))
            frame(stream, dict(version=2, request_id=1, operation="status", arguments={}))
            size = struct.unpack(">I", exact(stream, 4))[0]
            self.assertEqual(json.loads(exact(stream, size))["error"]["code"], "UNSUPPORTED_VERSION")

    def test_launcher_gate_does_not_prefetch_worker_descriptor(self):
        parent, child = socket.socketpair()
        self.addCleanup(parent.close)
        code = "import sys,struct,json; n=struct.unpack('>I',sys.stdin.buffer.read(4))[0]; v=json.loads(sys.stdin.buffer.read(n)); b=json.dumps(v).encode(); sys.stdout.buffer.write(struct.pack('>I',len(b))+b); sys.stdout.buffer.flush()"
        process = subprocess.Popen([str(BIN / "fetian-fca-launcher"), "/usr/bin/python3", "-I", "-c", code], stdin=child, stdout=child, stderr=subprocess.PIPE)
        child.close()
        self.addCleanup(lambda: process.poll() is None and process.kill())
        parent.settimeout(5)
        size = struct.unpack(">I", exact(parent, 4))[0]
        self.assertTrue(json.loads(exact(parent, size))["launcher_ready"])
        frames = b""
        for value in (dict(version=1, gate="resources-attached"), dict(worker_received="complete descriptor")):
            data = json.dumps(value).encode()
            frames += struct.pack(">I", len(data)) + data
        parent.sendall(frames)  # Deliberately coalesce both frames before exec.
        size = struct.unpack(">I", exact(parent, 4))[0]
        self.assertEqual(json.loads(exact(parent, size)), dict(worker_received="complete descriptor"))
        _, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, stderr)

    def test_faults_are_rejected_in_normal_daemon(self):
        normal = Broker(faults=False)
        self.addCleanup(normal.close)
        identity = normal.create()
        with self.assertRaises(RemoteError) as caught:
            normal.call("fault-arm", id=identity, phase="before-commit")
        self.assertEqual(caught.exception.code, "FAULTS_DISABLED")
        with self.assertRaises(RemoteError) as caught:
            normal.call("run", id=identity, executor="rust", barrier_after=1)
        self.assertEqual(caught.exception.code, "FAULTS_DISABLED")
        self.assertEqual(normal.inspect(identity)["epoch"], 0)

    def test_private_files_and_single_writer_across_runtime_dirs(self):
        self.assertEqual(stat.S_IMODE(self.broker.socket.stat().st_mode), 0o600)
        state = self.broker.root / "state/fetian-fca"
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((state / "authorities.sqlite3").stat().st_mode), 0o600)
        env = dict(self.broker.env, XDG_RUNTIME_DIR=str(self.broker.root / "other-runtime"))
        result = subprocess.run([str(BIN / "fetian-authorityd")], env=env, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"BROKER_EXISTS", result.stderr)

    def test_overflow_failure_policy_does_not_commit_effect(self):
        identity = self.broker.create([2**63-1, 1], recovery=dict(automatic_resume=False, failure_behavior="fail", require_executor_compatibility=True))
        self.broker.call("run", id=identity, executor="python")
        self.broker.wait(lambda: self.broker.inspect(identity)["lifecycle"] == "Failed")
        self.assertEqual(self.broker.call("verify", id=identity)["effects"], 0)

    def test_cli_export_and_paginated_event_chain(self):
        identity = self.broker.create(range(512))
        self.broker.call("run", id=identity, executor="python")
        self.broker.complete(identity)
        path = self.broker.root / "export.json"
        subprocess.run([str(BIN / "fetian-authority"), "export", identity, "--output", str(path)], env=self.broker.env, check=True, capture_output=True)
        report = json.loads(path.read_text())
        self.assertEqual(len(report["events"]), report["verification"]["events"])
        self.assertTrue(report["verification"]["valid"])
        result = subprocess.run([str(BIN / "fetian-authority"), "export", identity, "--output", str(path)], env=self.broker.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_executor_and_invalid_contract_fail_without_lease(self):
        identity = self.broker.create()
        self.assert_remote("EXECUTOR_NOT_ALLOWED", "run", id=identity, executor="/bin/sh")
        self.assertEqual(self.broker.inspect(identity)["epoch"], 0)
        contract = self.broker.inspect(identity)["contract"]
        contract["capabilities"].append("host.write")
        self.assert_remote("INVALID_CONTRACT", "create", contract=contract)

    def test_list_remains_bounded_at_authority_limit(self):
        for _ in range(64):
            self.broker.create()
        authorities = self.broker.call("list")
        self.assertEqual(len(authorities), 64)
        self.assertLess(len(json.dumps(authorities).encode()), 65536)
        with self.assertRaises(RemoteError) as caught:
            self.broker.create()
        self.assertEqual(caught.exception.code, "AUTHORITY_LIMIT")

    def test_journal_corruption_blocks_restart(self):
        identity = self.broker.create()
        self.broker.call("stop")
        self.broker.process.wait(timeout=5)
        with sqlite3.connect(self.broker.root / "state/fetian-fca/authorities.sqlite3") as db:
            text = db.execute("SELECT document FROM authorities WHERE id=?", (identity,)).fetchone()[0]
            record = json.loads(text)
            record["epoch"] += 1
            db.execute("UPDATE authorities SET document=? WHERE id=?", (json.dumps(record), identity))
        result = subprocess.run([str(BIN / "fetian-authorityd")], env=self.broker.env, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"STORE_CORRUPT", result.stderr)

    def test_opt_in_profile_payload_is_copied_without_enabling_unit(self):
        if BIN.name != "release":
            self.skipTest("Packaging uses explicitly built release binaries")
        repository = ROOT.parents[1]
        spec = importlib.util.spec_from_file_location("fca_profile_stager", repository / "scripts/stage-profile.py")
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        native = self.broker.root / "native-fixture"
        native.write_bytes(b"packaging-only native fixture")
        destination = self.broker.root / "profile"
        stager.stage(repository, destination, "sway", native, fca=True)
        tree = destination / "airootfs"
        self.assertTrue((tree / "usr/lib/fetian-fca/fetian-authorityd").is_file())
        self.assertTrue((tree / "usr/bin/fetian-authority").is_file())
        self.assertTrue((tree / "usr/lib/systemd/user/fetian-authorityd.service").is_file())
        self.assertFalse(any(path.name == "fetian-authorityd.service" for path in (tree / "etc/systemd").rglob("*")))
        self.assertIn('/usr/lib/fetian-fca/fetian-authorityd', (destination / "profiledef.sh").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
