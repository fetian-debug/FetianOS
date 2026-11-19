#!/usr/bin/env python3
"""Distribution benchmarks over actual FCA lifecycles; no estimated measurements."""
import argparse
import json
import math
import os
from pathlib import Path
import sqlite3
import time
from common import Session, atomic_json, check, checkpoint_oracle, environment, subreaper


def distribution(samples):
    if not samples:
        return dict(samples=0, measured=False)
    ordered = sorted(samples)
    def percentile(value):
        return ordered[max(0, math.ceil(value * len(ordered)) - 1)]
    return dict(measured=True, samples=len(ordered), method="nearest rank", p50=percentile(.50),
                p95=percentile(.95), p99=percentile(.99), minimum=ordered[0], maximum=ordered[-1])


def measured(function):
    start = time.perf_counter_ns()
    result = function()
    return result, (time.perf_counter_ns() - start) / 1000


def process_metrics(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    status = Path(f"/proc/{pid}/status").read_text().splitlines()
    rss = next(int(line.split()[1]) for line in status if line.startswith("VmRSS:"))
    return dict(rss_kib=rss, cpu_seconds=(int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"))


def condition(items, population, restarts):
    session = Session()
    samples = {name: [] for name in ("authority_creation_us", "lease_acquisition_us", "gated_launch_rpc_us",
                "effect_checkpoint_commit_us", "checkpoint_barrier_rpc_us", "handoff_rpc_us",
                "restart_wall_us", "store_verification_recovery_us", "direct_python_parse_sum_us")}
    seen, workers = 0, []
    values = [index - items // 2 for index in range(items)]
    text = "".join(f"{value}\n" for value in values)
    before = process_metrics(session.daemon_pid)
    def collect():
        nonlocal seen
        measurements = session.call("status")["measurements"]
        delta = measurements["effect_commits_seen"] - seen
        check(0 <= delta <= 256, "benchmark missed commit samples; poll more frequently")
        if delta:
            samples["effect_checkpoint_commit_us"].extend(measurements["recent_effect_commit_us"][-delta:])
        seen = measurements["effect_commits_seen"]
    try:
        for _ in range(30):
            result, elapsed = measured(lambda: sum(int(line) for line in text.splitlines()))
            check(result == sum(values), "direct baseline mismatch")
            samples["direct_python_parse_sum_us"].append(elapsed)
        identities = []
        for _ in range(population):
            identity, elapsed = measured(lambda: session.create(values, chunk_size=32))
            identities.append(identity)
            samples["authority_creation_us"].append(elapsed)
        recovery_id = identities[-1]
        resource = None
        for identity in identities:
            launch, elapsed = measured(lambda: session.call("run", id=identity, executor="rust", barrier_after=1))
            samples["gated_launch_rpc_us"].append(elapsed)
            resource = launch["resources"]
            session.barrier(identity)
            workers.append(process_metrics(launch["pid"])["rss_kib"])
            _, elapsed = measured(lambda: session.call("checkpoint", id=identity))
            samples["checkpoint_barrier_rpc_us"].append(elapsed)
            _, elapsed = measured(lambda: session.call("handoff", id=identity, executor="python", barrier_after=2))
            samples["handoff_rpc_us"].append(elapsed)
            session.barrier(identity)
            if identity == recovery_id:
                session.call("suspend", id=identity)
            else:
                session.call("fault-release", id=identity)
                session.complete(identity)
            collect()
        measurements = session.call("status")["measurements"]
        check(measurements["lease_acquisitions_seen"] <= 256, "lease sample window overflow")
        samples["lease_acquisition_us"] = measurements["recent_lease_acquisition_us"]
        after = process_metrics(session.daemon_pid)
        checkpoint = session.inspect(recovery_id)
        for _ in range(restarts):
            session.kill_broker()
            _, elapsed = measured(session.start)
            samples["restart_wall_us"].append(elapsed)
            samples["store_verification_recovery_us"].append(session.call("status")["measurements"]["startup_verification_recovery_us"])
            recovered = session.inspect(recovery_id)
            check(recovered["id"] == checkpoint["id"] and recovered["contract"] == checkpoint["contract"], "restart changed authority identity/permissions")
            check(recovered["continuation"] == checkpoint["continuation"], "restart lost pending checkpoint")
            check(recovered["lifecycle"] == "Suspended", "restart silently resumed suspended work")
            checkpoint_oracle(recovered, values, 32)
        with sqlite3.connect(session.database) as database:
            counts = dict(database.execute("SELECT authority_id,COUNT(*) FROM events GROUP BY authority_id"))
            effect_count = database.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
            db_pages = database.execute("PRAGMA page_count").fetchone()[0]
            page_size = database.execute("PRAGMA page_size").fetchone()[0]
        sizes = {path.name: path.stat().st_size for path in session.database.parent.glob("authorities.sqlite3*")}
        return dict(items=items, authorities=population, chunk_size=32,
                    execution_concurrency=1, authority_population_measured=True,
                    samples=samples, distributions={name: distribution(values) for name, values in samples.items()},
                    storage_bytes=sizes, sqlite_allocated_bytes=db_pages * page_size,
                    journal_events_by_authority=counts, managed_effects=effect_count,
                    broker_before=before, broker_after=after,
                    broker_cpu_seconds_during_work=after["cpu_seconds"] - before["cpu_seconds"],
                    rust_worker_rss_kib=distribution(workers), resources=resource,
                    resource_enforcement_overhead="not isolated; unavailable when no delegated cgroup",
                    pending_checkpoint_verified_each_restart=True)
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", nargs="+", type=int, default=[64, 512, 4096])
    parser.add_argument("--populations", nargs="+", type=int, default=[1, 8, 32, 64])
    parser.add_argument("--restart-samples", type=int, default=10)
    args = parser.parse_args()
    check(all(64 <= size <= 4096 for size in args.sizes), "sizes must be 64–4096")
    check(all(1 <= count <= 64 for count in args.populations), "populations must be 1–64")
    check(1 <= args.restart_samples <= 100, "restart samples must be 1–100")
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    subreaper()
    report = dict(schema_version=1, environment=environment(), conditions=[],
                  units="latencies in microseconds, RSS in KiB, CPU in seconds, storage in bytes",
                  interpretation=["Measured observations, not estimates or throughput promises.",
                                  "Nearest-rank p99 with few samples is descriptive and not a reliable tail estimate.",
                                  "Lease acquisition is timed inside the coordinator's durable Store::issue_lease call.",
                                  "Effect/checkpoint latency is one atomic managed transaction; ACK transport excluded.",
                                  "Restart wall includes process startup, complete store verification and pending-authority recovery.",
                                  "Population scaling is serial admission with resident authorities; not a concurrency scaling claim.",
                                  "Direct Python excludes process startup, IPC, audit and durability. RSS is a point sample, not peak."])
    for size in args.sizes:
        for population in args.populations:
            result = condition(size, population, args.restart_samples)
            report["conditions"].append(result)
            atomic_json(args.output / f"size-{size}-authorities-{population}.json", result)
            print(json.dumps(dict(completed=len(report["conditions"]), items=size, authorities=population)), flush=True)
    atomic_json(args.output / "performance.json", report)


if __name__ == "__main__":
    main()
