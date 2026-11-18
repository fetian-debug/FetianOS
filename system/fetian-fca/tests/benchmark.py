#!/usr/bin/env python3
"""Small measured experiment; not a scalability or hardware benchmark."""
import json
import os
import platform
import statistics
import subprocess
import time
from process_tests import BIN, Broker


def measured(function):
    start = time.perf_counter_ns()
    result = function()
    return result, (time.perf_counter_ns() - start) / 1000


def summary(values):
    return dict(samples=len(values), median_us=statistics.median(values),
                min_us=min(values), max_us=max(values))


def proc(pid):
    with open(f"/proc/{pid}/stat") as file:
        fields = file.read().rsplit(")", 1)[1].split()
    with open(f"/proc/{pid}/status") as file:
        rss = next(int(line.split()[1]) for line in file if line.startswith("VmRSS:"))
    return dict(cpu_seconds=(int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"), rss_kib=rss)


def main():
    broker = Broker()
    try:
        values = list(range(-2048, 2048))
        expected = sum(values)
        content = "".join(f"{n}\n" for n in values)
        direct = [measured(lambda: sum(int(line) for line in content.splitlines()))[1] for _ in range(20)]
        rpc = [measured(lambda: broker.call("status"))[1] for _ in range(20)]
        created, launched, completed = [], [], []
        before = proc(broker.process.pid)
        resources = None
        events = []
        for _ in range(5):
            imported = broker.call("import", content=content)
            contract = json.loads(subprocess.check_output([str(BIN / "fetian-authority"), "--json", "contract-template", imported["input_id"]]))
            authority, duration = measured(lambda: broker.call("create", contract=contract))
            created.append(duration)
            identity = authority["id"]
            started = time.perf_counter_ns()
            launch, duration = measured(lambda: broker.call("run", id=identity, executor="python"))
            launched.append(duration)
            resources = launch["resources"]
            result = broker.complete(identity)
            completed.append((time.perf_counter_ns() - started) / 1000)
            assert result["checkpoint"]["accumulated_result"] == expected
            assert result["effects"] == 64
            events.append(result["events"])
        status = broker.call("status")
        after = proc(broker.process.pid)
        identity = broker.create()
        broker.call("run", id=identity, executor="rust", barrier_after=1)
        broker.barrier(identity)
        worker_pid = broker.inspect(identity)["current_executor"]["pid"]
        worker = proc(worker_pid)
        _, checkpoint_us = measured(lambda: broker.call("checkpoint", id=identity))
        _, handoff_us = measured(lambda: broker.call("handoff", id=identity, executor="python"))
        broker.complete(identity)
        broker.process.kill()
        broker.process.wait()
        _, restart_us = measured(broker.start)
        recovered = broker.call("status")["measurements"]["startup_verification_recovery_us"]
        store = broker.root / "state/fetian-fca"
        sizes = {name: (store / name).stat().st_size for name in ("authorities.sqlite3", "authorities.sqlite3-wal", "authorities.sqlite3-shm") if (store / name).exists()}
        demo = json.loads(subprocess.check_output([str(BIN / "fetian-authority"), "--json", "demo-handoff"], timeout=30))
        report = dict(schema_version=1, recorded_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      environment=dict(kernel=platform.release(), architecture=platform.machine(), python=platform.python_version(), binary_profile=BIN.name),
                      workload=dict(items=4096, chunk_size=64, expected_result=expected),
                      direct_python_parse_sum=summary(direct), operator_status_rpc=summary(rpc),
                      authority_creation=summary(created), lease_and_gated_launch=summary(launched),
                      managed_python_to_completion=summary(completed),
                      broker_effect_checkpoint_transaction=summary(status["measurements"]["recent_effect_commit_us"]),
                      checkpoint_barrier_rpc_us=checkpoint_us, revoke_kill_wait_replacement_rpc_us=handoff_us,
                      daemon_restart_wall_us=restart_us, startup_verification_recovery_us=recovered,
                      broker_before=before, broker_after=after, rust_worker_at_barrier=worker,
                      store_bytes=sizes, events_per_64_effect_run=events, resources=resources,
                      resource_enforcement_overhead="unmeasured: delegated enforcement unavailable" if not resources["kernel_enforced"] else "not isolated by this experiment",
                      notes=["Single local experiment; medians are descriptive, not guarantees.",
                             "Client wall timings include IPC, scheduling and state polling; direct baseline excludes process startup and durability.",
                             "Effect latency is coordinator monotonic time around the SQLite FULL transaction, excluding ACK transport.",
                             "CPU values cover broker only; RSS is a point sample; store sizes include other experiment authorities."],
                      handoff_demo=demo)
        print(json.dumps(report, indent=2))
    finally:
        broker.close()


if __name__ == "__main__":
    main()
