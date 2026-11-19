"""Real-process experiment sessions and evidence helpers; standard library only."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import sqlite3
import subprocess
import sys
import time

FCA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FCA_ROOT / "tests"))
from process_tests import BIN, Broker, RemoteError, exact, frame


class StartupRejected(RuntimeError):
    pass


def check(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".writing")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def redact(value):
    if isinstance(value, dict):
        return {key: ("sha256:" + hashlib.sha256(str(item).encode()).hexdigest()
                      if key == "lease_id" else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def environment():
    cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")), "unreported")
    memory = next(line.strip() for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal:"))
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=FCA_ROOT, capture_output=True, text=True)
    sources = sorted((FCA_ROOT / "src").rglob("*.rs")) + [FCA_ROOT / "Cargo.toml", FCA_ROOT / "executors/fetian-executor-python.py"]
    source_hash = hashlib.sha256()
    for path in sources:
        source_hash.update(str(path.relative_to(FCA_ROOT)).encode() + b"\0" + path.read_bytes())
    return dict(recorded_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                kernel=platform.release(), architecture=platform.machine(), python=platform.python_version(),
                cpu=cpu, logical_cpus=os.cpu_count(), memory=memory, sqlite_python=sqlite3.sqlite_version,
                source_revision=revision.stdout.strip() if revision.returncode == 0 else None,
                rust_source_sha256=source_hash.hexdigest(), cargo_lock_sha256=digest(FCA_ROOT / "Cargo.lock"),
                harness_sha256={path.name: digest(path) for path in sorted((FCA_ROOT / "validation").glob("*.py"))},
                binaries={name: digest(BIN / name) for name in ("fetian-authorityd", "fetian-authority", "fetian-executor-rust", "fetian-fca-launcher")},
                runtime_state="private temporary Linux directories; never the user's real FCA store")


def subreaper():
    """Adopt only this harness's orphaned descendants, without root privileges."""
    library = ctypes.CDLL(None, use_errno=True)
    return library.prctl(36, 1, 0, 0, 0) == 0  # Linux PR_SET_CHILD_SUBREAPER


def process_stopped(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] in ("Z", "X")
    except FileNotFoundError:
        return True


def checkpoint_oracle(authority, values, chunk):
    state = authority["continuation"]
    position = state["next_input_position"]
    check(0 <= position <= len(values), "checkpoint cursor outside immutable input")
    check(position == len(values) or position % chunk == 0, "checkpoint cursor splits a chunk")
    check(state["schema_version"] == 1, "checkpoint schema changed")
    check(state["accumulated_result"] == sum(values[:position]), "checkpoint sum differs from independent oracle")
    check(state["last_committed_chunk"] == (position + chunk - 1) // chunk, "checkpoint/effect cursor mismatch")


class Session(Broker):
    def __init__(self, faults=True, delegated=False):
        self.trace, self.worker_pids = [], set()
        self.daemon_pid, self.captured = None, None
        self.delegated = delegated
        try:
            super().__init__(faults=faults)
        except Exception:
            if hasattr(self, "root"):
                self.close()
            raise

    @property
    def database(self):
        return self.root / "state/fetian-fca/authorities.sqlite3"

    def start(self):
        command = [str(BIN / "fetian-authorityd")]
        if self.faults:
            command += ["--allow-test-faults"]
        if self.delegated:
            command = ["systemd-run", "--user", "--quiet", "--wait", "--collect", "--pipe",
                       "--property=Delegate=cpu memory pids",
                       "--setenv=XDG_STATE_HOME=" + self.env["XDG_STATE_HOME"],
                       "--setenv=XDG_RUNTIME_DIR=" + self.env["XDG_RUNTIME_DIR"], *command]
        self.process = subprocess.Popen(command, env=os.environ if self.delegated else self.env, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL, stderr=self.log)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise StartupRejected((self.root / "daemon.log").read_text()[-4000:])
            try:
                status = self.call("status")
                if self.delegated or status["pid"] == self.process.pid:
                    self.daemon_pid = status["pid"]
                    return
            except (OSError, EOFError, RemoteError):
                pass
            time.sleep(.002)
        raise TimeoutError("broker startup did not reach a verified status")

    def call(self, operation, **arguments):
        started = time.perf_counter_ns()
        record = dict(operation=operation, arguments=redact(arguments))
        try:
            result = super().call(operation, **arguments)
            record["result"] = redact(result)
            if operation in ("run", "handoff"):
                self.worker_pids.add(result["pid"])
            return result
        except RemoteError as error:
            record["error"] = error.code
            raise
        except (OSError, EOFError) as error:
            record["error"] = type(error).__name__
            if isinstance(error, TimeoutError) and self.daemon_pid:
                record["timeout_diagnostics"] = {"loadavg": Path("/proc/loadavg").read_text().strip()}
                for task in Path(f"/proc/{self.daemon_pid}/task").glob("*"):
                    try:
                        record["timeout_diagnostics"][task.name] = {name: (task / name).read_text().strip()
                                                                  for name in ("comm", "wchan", "stat")}
                    except OSError:
                        pass
            raise
        finally:
            record["elapsed_us"] = (time.perf_counter_ns() - started) / 1000
            if operation != "status":
                self.trace.append(record)

    def create(self, values=range(1, 129), **changes):
        imported = self.call("import", content="".join(f"{number}\n" for number in values))
        if not hasattr(self, "template"):
            self.template = json.loads(subprocess.check_output([str(BIN / "fetian-authority"), "--json", "contract-template", imported["input_id"]]))
        contract = json.loads(json.dumps(self.template))
        contract["input"]["id"] = imported["input_id"]
        contract.update(changes)
        return self.call("create", contract=contract)["id"]

    def expect(self, expected, operation, **arguments):
        try:
            self.call(operation, **arguments)
        except RemoteError as error:
            check(error.code == expected, f"{operation}: expected {expected}, observed {error.code}")
            return error.code
        raise AssertionError(f"{operation}: unauthorized operation accepted; expected {expected}")

    def barrier_state(self, identity):
        self.barrier(identity)
        return self.call("inspect", id=identity)

    def ready(self, identity):
        self.wait(lambda: self.inspect(identity)["lifecycle"] in ("Ready", "Orphaned"))
        if self.inspect(identity)["lifecycle"] == "Orphaned":
            def resume():
                try:
                    self.call("resume", id=identity)
                    return True
                except RemoteError as error:
                    if error.code != "STOP_UNPROVEN":
                        raise
                    return False
            self.wait(resume)
        return self.inspect(identity)

    def kill_broker(self):
        os.kill(self.daemon_pid, signal.SIGKILL)
        self.process.wait(timeout=5)
        for pid in self.worker_pids:
            self.wait(lambda: process_stopped(pid))
        self.reap()

    def stop(self):
        self.call("stop")
        self.process.wait(timeout=5)
        self.reap()

    @staticmethod
    def reap():
        while True:
            try:
                if os.waitpid(-1, os.WNOHANG)[0] == 0:
                    break
            except ChildProcessError:
                break

    def archive(self):
        evidence = dict(events={}, snapshots={}, database={}, log=(self.root / "daemon.log").read_text(errors="replace"))
        try:
            with sqlite3.connect(f"file:{self.database}?mode=ro", uri=True) as connection:
                for identity, document in connection.execute("SELECT id,document FROM authorities ORDER BY id"):
                    try:
                        evidence["snapshots"][identity] = redact(json.loads(document))
                    except ValueError:
                        evidence["snapshots"][identity] = {"invalid_json": True, "sha256": hashlib.sha256(document.encode()).hexdigest()}
                    evidence["events"][identity] = [dict(sequence=row[0], payload=json.loads(row[1]), previous_hash=row[2], hash=row[3])
                                                    for row in connection.execute("SELECT sequence,payload,previous_hash,hash FROM events WHERE authority_id=? ORDER BY sequence", (identity,))]
                evidence["database"]["effects"] = [dict(authority_id=row[0], sequence=row[1], effect_id=row[2], epoch=row[3]) for row in connection.execute("SELECT authority_id,sequence,effect_id,epoch FROM effects ORDER BY authority_id,sequence")]
                evidence["database"]["integrity_check"] = connection.execute("PRAGMA integrity_check").fetchone()[0]
        except (sqlite3.Error, ValueError) as error:
            evidence["database"]["capture_error"] = str(error)
        evidence["sizes"] = {path.name: path.stat().st_size for path in self.database.parent.glob("authorities.sqlite3*") if path.is_file()}
        return evidence

    def close(self):
        try:
            if self.process and self.process.poll() is None:
                try:
                    self.call("stop")
                    self.process.wait(timeout=5)
                except (OSError, EOFError, RemoteError, subprocess.TimeoutExpired):
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.reap()
            self.captured = self.archive()
        finally:
            self.log.close()
            self.temp.cleanup()
