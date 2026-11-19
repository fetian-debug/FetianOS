#!/usr/bin/env python3
"""Managed admission checks and explicit counterexamples outside the same-UID boundary."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import tempfile
from common import (BIN, FCA_ROOT, Session, StartupRejected, RemoteError, atomic_json,
                    check, environment, process_stopped, subreaper)


def controller_values(path):
    return {line.split()[0]: int(line.split()[1]) for line in path.read_text().splitlines()}


def pressure(kind, delegated):
    session, child = None, None
    try:
        try:
            session = Session(delegated=delegated)
        except (StartupRejected, FileNotFoundError) as error:
            return dict(status="unavailable", enforced=False, reason=str(error))
        identity = session.create()
        normal = session.inspect(identity)
        budget = dict(normal["contract"]["resource_budget"], strict=True,
                      memory_bytes=(32 if kind == "memory" else 128) * 1024**2, pids_max=8)
        strict = session.create(resource_budget=budget)
        try:
            launch = session.call("run", id=strict, executor="python", barrier_after=1)
        except RemoteError as error:
            check(error.code == "STRICT_RESOURCE_UNAVAILABLE", "strict resources failed for an unexpected reason")
            state = session.inspect(strict)
            check(state["epoch"] == 0 and state["current_executor"] is None, "strict rejection started or leased an executor")
            return dict(status="unavailable", enforced=False, strict_rejection_verified=True, reason=error.code)
        check(launch["resources"]["kernel_enforced"], "strict contract silently downgraded")
        session.barrier(strict)
        relative = next(line[3:] for line in Path(f"/proc/{session.daemon_pid}/cgroup").read_text().splitlines() if line.startswith("0::"))
        manager = Path("/sys/fs/cgroup") / relative.lstrip("/")
        check(manager.name == "fca-manager", "unexpected delegated manager location")
        group = manager.parent / strict
        check(group.stat().st_uid == os.getuid(), "refusing a foreign cgroup")
        counter = {"cpu": ("cpu.stat", "nr_throttled"), "memory": ("memory.events", "oom_kill"), "pids": ("pids.events", "max")}[kind]
        before = controller_values(group / counter[0])
        child = subprocess.Popen(["/usr/bin/python3", "-I", str(Path(__file__).with_name("pressure.py")), kind],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, start_new_session=True)
        check(child.stdout.readline().strip() == "READY", "pressure helper failed before resource gate")
        with (group / "cgroup.procs").open("w") as stream:
            stream.write(str(child.pid))
        output, errors = child.communicate("ATTACHED\n", timeout=10)
        after = controller_values(group / counter[0])
        delta = after.get(counter[1], 0) - before.get(counter[1], 0)
        return dict(status="verified" if delta > 0 else "incomplete", enforced=delta > 0,
                    controller_counter=counter, before=before, after=after, delta=delta,
                    helper_exit=child.returncode, output=output, stderr=errors,
                    reason=None if delta > 0 else "No enforcement counter changed; configuration alone is not proof")
    finally:
        if child and child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
        if session:
            session.close()


def boundaries():
    session = Session(faults=False)
    try:
        values = list(range(128))
        identity = session.create(values)
        check(session.call("status")["test_faults"] is False, "production mode enabled fault hooks")
        for phase in ("before-commit", "after-commit", "after-effect-insert", "executor-before-commit", "executor-after-commit"):
            session.expect("FAULTS_DISABLED", "fault-arm", id=identity, phase=phase)
        session.expect("FAULTS_DISABLED", "fault-release", id=identity)
        # A compromised process with the same Unix identity can read the private
        # store outside the protocol. This is a demonstrated limitation, not a
        # successful managed capability check or a sandbox claim.
        script = "import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); s=c.execute('SELECT document FROM authorities WHERE id=?',(sys.argv[2],)).fetchone()[0]; print(json.dumps({'readable':True,'id':json.loads(s)['id']}))"
        observed = json.loads(subprocess.check_output(["/usr/bin/python3", "-I", "-c", script, str(session.database), identity]))
        check(observed["id"] == identity, "same-UID access counterexample did not exercise the target store")
        # Bounded real external effect + producer death + retry, outside FCA's
        # transaction. Nothing is written outside this session's private fixture.
        external = session.root / "external-effect.txt"
        producer = "import os,signal,sys; f=open(sys.argv[1],'a'); f.write('effect\\n'); f.flush(); os.fsync(f.fileno()); os.kill(os.getpid(),signal.SIGKILL)"
        codes = [subprocess.run(["/usr/bin/python3", "-I", "-c", producer, str(external)]).returncode for _ in range(2)]
        check(codes == [-9, -9] and external.read_text().splitlines() == ["effect", "effect"], "external duplicate counterexample was not actually exercised")
        check(session.call("verify", id=identity)["effects"] == 0, "standalone filesystem writes unexpectedly entered managed transaction")
        return dict(normal_mode_fault_rejections_verified=True,
                    same_uid_store_access=dict(observed=True, isolated=False, severity="high", scope="known trusted-executor boundary; no hostile same-UID sandbox"),
                    external_effect_retry=dict(producer_exit_codes=codes, observed_effects=2, managed_effects=0,
                                               exactly_once=False, scope="standalone counterexample, not an FCA provider adapter"))
    finally:
        session.close()


def admission_limits():
    session = Session()
    try:
        active = []
        for _ in range(8):
            identity = session.create()
            session.call("run", id=identity, executor="rust", barrier_after=1)
            active.append(identity)
        blocked = session.create()
        session.expect("EXECUTOR_LIMIT", "run", id=blocked, executor="python")
        check(session.inspect(blocked)["epoch"] == 0, "executor-limit rejection granted a lease")
        for identity in active:
            session.call("cancel", id=identity)
        for _ in range(55):
            session.create()
        try:
            session.create()
        except RemoteError as error:
            check(error.code == "AUTHORITY_LIMIT", "unexpected authority-limit error")
        else:
            raise AssertionError("authority limit not enforced")
        check(len(session.call("list")) == 64, "bounded list lost authorities")
        return dict(active_executors=8, ninth_rejected=True, authority_limit=64, sixty_fifth_rejected=True)
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delegated", action="store_true", help="Launch only transient user services with cgroup delegation; never request root")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    subreaper()
    report = dict(schema_version=1, environment=environment(), boundaries=boundaries(), limits=admission_limits(),
                  resource_enforcement={kind: pressure(kind, args.delegated) for kind in ("cpu", "memory", "pids")})
    report["kernel_enforcement_verified"] = all(value["status"] == "verified" for value in report["resource_enforcement"].values())
    report["limitations_are_not_recoveries"] = True
    atomic_json(args.output / "security.json", report)
    print(json.dumps(dict(boundaries_observed=True, resources=report["resource_enforcement"])), flush=True)


if __name__ == "__main__":
    main()
