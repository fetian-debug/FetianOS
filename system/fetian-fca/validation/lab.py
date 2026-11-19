#!/usr/bin/env python3
"""Seeded FCA experiments: actual processes, private IPC and SQLite failure windows."""
import argparse
import concurrent.futures
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import random
import signal
import sqlite3
import sys
import time
import traceback

from common import (BIN, FCA_ROOT, Session, StartupRejected, RemoteError, atomic_json,
                    check, checkpoint_oracle, environment, process_stopped, subreaper)

RECOVERY = "expected_recovery"
REJECTION = "expected_rejection"
SAFE_FAILURE = "safely_detected_unrecoverable"
UNEXPECTED = "unexpected_correctness_failure"
FAULTS = ("executor-sigkill", "executor-before-commit", "executor-after-commit",
          "broker-active", "broker-before-commit", "broker-after-commit", "journal-interrupt",
          "pending-restart", "sqlite-reopen", "stale-commit", "competing-executors",
          "duplicate-start", "duplicate-effect", "conflicting-effect", "checkpoint-corrupt",
          "checkpoint-incomplete", "journal-corrupt", "python-to-rust", "rust-to-python",
          "suspend-resume", "terminal-cancel", "handoff-forbidden")
PROBES = ("wrong-lease", "wrong-executor", "cross-authority", "stale-epoch", "version",
          "request-order", "unknown-envelope", "unknown-argument", "unknown-operation",
          "forged-result", "invalid-position", "capability", "oversize", "truncated", "invalid-json")


@dataclass
class Config:
    scenario: str
    seed: int
    items: int = 128
    chunk: int = 32
    barrier: int = 1
    executor: str = "rust"
    jitter_us: int = 0

    def validate(self):
        check(self.scenario in FAULTS or self.scenario in PROBES or self.scenario == "lease-expiry", "unknown scenario")
        check(self.executor in ("rust", "python"), "unsupported reference executor")
        check(16 <= self.chunk <= 128 and self.chunk < self.items <= 4096, "invalid bounded workload")
        check(1 <= self.barrier < math.ceil(self.items / self.chunk), "barrier must precede completion")
        check(0 <= self.jitter_us <= 10000, "jitter bound exceeded")


def generated(seed, scenario=None):
    rng = random.Random(seed)
    chunk = rng.choice((16, 32, 64))
    items = rng.choice((chunk * 2, chunk * 4, chunk * 8))
    return Config(scenario or rng.choice(FAULTS + PROBES), seed, items, chunk,
                  rng.randrange(1, items // chunk), rng.choice(("rust", "python")), rng.randrange(2001))


def credential(authority):
    lease = authority["current_executor"]
    return {key: lease[key] for key in ("executor_id", "lease_id", "epoch")}


def progress(values, chunk, sequence):
    start = (sequence - 1) * chunk
    end = min(sequence * chunk, len(values))
    return dict(sequence=sequence, input_position=start, next_input_position=end,
                accumulated_result=sum(values[:end]), idempotency_key=f"chunk-{sequence}")


def same_checkpoint(before, after, values, chunk, advanced=True):
    check(before["id"] == after["id"], "authority identity changed across failure")
    check(before["contract"] == after["contract"], "execution permissions/contract changed across failure")
    check(before["continuation"] == after["continuation"], "committed continuation changed across failure")
    if advanced:
        check(after["epoch"] > before["epoch"], "recovery did not fence the old generation")
    checkpoint_oracle(after, values, chunk)


def finish(session, identity, values, chunk, executor):
    state = session.inspect(identity)
    if state["lifecycle"] == "Suspended":
        session.call("resume", id=identity)
    if state["lifecycle"] != "Completed":
        session.call("run", id=identity, executor=executor)
    verification = session.complete(identity)
    state = session.inspect(identity)
    checkpoint_oracle(state, values, chunk)
    check(state["continuation"]["next_input_position"] == len(values), "completion skipped input")
    check(state["continuation"]["accumulated_result"] == sum(values), "final sum differs from independent oracle")
    check(verification["effects"] == math.ceil(len(values) / chunk), "duplicate or missing broker-managed effects")
    check(verification["valid"], "event/lifecycle/checkpoint verification failed")
    return verification


def corrupt(session, identity, kind):
    session.stop()
    with sqlite3.connect(session.database) as connection:
        if kind == "journal-corrupt":
            connection.execute("DROP TRIGGER events_no_update")
            connection.execute("UPDATE events SET hash='deliberate-corruption' WHERE authority_id=? AND sequence=1", (identity,))
        else:
            raw = connection.execute("SELECT document FROM authorities WHERE id=?", (identity,)).fetchone()[0]
            value = json.loads(raw)
            if kind == "checkpoint-incomplete":
                del value["continuation"]["schema_version"]
            else:
                value["continuation"]["accumulated_result"] += 1
            connection.execute("UPDATE authorities SET document=? WHERE id=?", (json.dumps(value), identity))
    try:
        session.start()
    except StartupRejected as error:
        check(any(code in str(error) for code in ("CORRUPT", "INVALID_MESSAGE")), "startup failed for unrelated reason")
        return dict(classification=SAFE_FAILURE, corruption=kind, recovered=False, startup_error=str(error))
    raise AssertionError("broker accepted a corrupted or incomplete committed checkpoint/journal")


def private_probe(session, config, identity, values, paused):
    authority = paused["authority"]
    grant = credential(authority)
    request = dict(version=1, request_id=paused["test_barrier_request_id"] + 1,
                   operation="read", arguments=dict(credential=grant, position=authority["continuation"]["next_input_position"]))
    mode, expected = "request", None
    scenario = config.scenario
    foreign = None
    if scenario == "wrong-lease":
        request["arguments"]["credential"]["lease_id"] = "lease_" + "0" * 32
        expected = "LEASE_REVOKED"
    elif scenario == "wrong-executor":
        request["arguments"]["credential"]["executor_id"] = "python-reference-v1" if config.executor == "rust" else "rust-reference-v1"
        expected = "LEASE_REVOKED"
    elif scenario == "cross-authority":
        other = session.create(values, chunk_size=config.chunk)
        session.call("run", id=other, executor=config.executor, barrier_after=1)
        target = session.barrier_state(other)["authority"]
        foreign = (other, target)
        request["arguments"]["credential"] = credential(target)
        expected = "LEASE_REVOKED"
    elif scenario == "stale-epoch":
        request["arguments"]["credential"]["epoch"] -= 1
        expected = "STALE_EPOCH"
    elif scenario == "version":
        request["version"] = 2
        expected = "UNSUPPORTED_VERSION"
    elif scenario == "request-order":
        request["request_id"] += 1
        expected = "REQUEST_ORDER"
    elif scenario == "unknown-envelope":
        request["unknown"] = True
        expected = "INVALID_MESSAGE"
    elif scenario == "unknown-argument":
        request["arguments"]["authority_id"] = "ca_" + "0" * 32
        expected = "UNKNOWN_FIELD"
    elif scenario == "unknown-operation":
        request["operation"] = "shell"
        expected = "CAPABILITY_DENIED"
    elif scenario == "forged-result":
        candidate = progress(values, config.chunk, config.barrier + 1)
        candidate["accumulated_result"] += 1
        request["operation"] = "commit"
        request["arguments"] = dict(credential=grant, progress=candidate)
        expected = "INVALID_RESULT"
    elif scenario == "invalid-position":
        request["arguments"]["position"] += 1
        expected = "INVALID_POSITION"
    elif scenario == "capability":
        request["operation"] = "inspect"
        request["arguments"] = dict(credential=grant)
        expected = "CAPABILITY_DENIED"
    else:
        mode = scenario
        expected = {"oversize": "FRAME_LIMIT", "truncated": "IO_ERROR", "invalid-json": "INVALID_MESSAGE"}[scenario]
    session.call("fault-release", id=identity, probe=dict(mode=mode, request=request))
    session.ready(identity)
    captured = session.archive()
    observation_kind = "ResearchProbeResult" if mode == "request" and scenario != "unknown-envelope" else "ResearchProbeTransportRejected"
    observations = [event["payload"]["details"] for event in captured["events"][identity]
                    if event["payload"]["kind"] == observation_kind]
    # A worker closing after its response also produces an EOF transport event.
    # Judge the actual request response, never that subsequent socket shutdown.
    check(len(observations) == 1 and observations[0]["code"] == expected, f"private worker {scenario} probe: expected {expected}, observed {observations}")
    same_checkpoint(authority, session.inspect(identity), values, config.chunk)
    if foreign:
        check(session.inspect(foreign[0])["continuation"] == foreign[1]["continuation"], "probe changed another authority's checkpoint")
        session.call("cancel", id=foreign[0])
    return dict(classification=REJECTION, transport="actual executor private socket", rejected_code=expected,
                verification=finish(session, identity, values, config.chunk, "python" if config.executor == "rust" else "rust"))


def experiment(session, config):
    rng = random.Random(config.seed)
    values = [rng.randrange(-1000, 1001) for _ in range(config.items)]
    changes = dict(chunk_size=config.chunk)
    if config.scenario == "capability":
        changes["capabilities"] = ["input.read", "checkpoint.commit", "result.commit"]
    if config.scenario == "handoff-forbidden":
        changes["permitted_executors"] = [config.executor + "-reference-v1"]
    identity = session.create(values, **changes)
    initial = session.inspect(identity)
    scenario = config.scenario
    first = "python" if scenario == "python-to-rust" else "rust" if scenario == "rust-to-python" else config.executor
    other = "python" if first == "rust" else "rust"
    if scenario == "pending-restart":
        suspended = session.create(values, chunk_size=config.chunk)
        session.call("suspend", id=suspended)
        before = session.inspect(suspended)
        session.kill_broker()
        session.start()
        same_checkpoint(initial, session.inspect(identity), values, config.chunk)
        same_checkpoint(before, session.inspect(suspended), values, config.chunk)
        check(session.inspect(suspended)["lifecycle"] == "Suspended", "restart resumed an explicitly suspended authority")
        finish(session, suspended, values, config.chunk, other)
        return dict(classification=RECOVERY, verification=finish(session, identity, values, config.chunk, first))
    if scenario == "competing-executors":
        def acquire(executor):
            try:
                return dict(accepted=session.call("run", id=identity, executor=executor, barrier_after=config.barrier))
            except RemoteError as error:
                return dict(rejected=error.code)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(acquire, (first, other)))
        check(sum("accepted" in value for value in outcomes) == 1, "competing requests granted zero or multiple execution contexts")
        check([v["rejected"] for v in outcomes if "rejected" in v] == ["INVALID_STATE"], "competing acquisition rejected unexpectedly")
        session.barrier(identity)
        session.call("suspend", id=identity)
        return dict(classification=REJECTION, acquisitions=outcomes, verification=finish(session, identity, values, config.chunk, other))
    session.call("run", id=identity, executor=first, barrier_after=config.barrier)
    paused = session.barrier_state(identity)
    before = paused["authority"]
    check(before["id"] == identity, "initial authority identity mismatch")
    checkpoint_oracle(before, values, config.chunk)
    old = credential(before)
    if config.jitter_us:
        time.sleep(config.jitter_us / 1_000_000)  # Random scheduling jitter, never an oracle for progress.
    if scenario in PROBES:
        return private_probe(session, config, identity, values, paused)
    if scenario in ("checkpoint-corrupt", "checkpoint-incomplete", "journal-corrupt"):
        return corrupt(session, identity, scenario)
    expected_count = config.barrier
    if scenario == "executor-sigkill":
        pid = before["current_executor"]["pid"]
        os.kill(pid, signal.SIGKILL)
        session.wait(lambda: process_stopped(pid))
        session.ready(identity)
    elif scenario == "broker-active":
        session.kill_broker()
        session.start()
        session.ready(identity)
    elif scenario in ("broker-before-commit", "broker-after-commit", "journal-interrupt", "executor-before-commit", "executor-after-commit"):
        phase = {"broker-before-commit": "before-commit", "broker-after-commit": "after-commit", "journal-interrupt": "after-effect-insert"}.get(scenario, scenario)
        session.call("fault-arm", id=identity, phase=phase)
        session.call("fault-release", id=identity)
        if scenario.startswith("broker-") or scenario == "journal-interrupt":
            session.process.wait(timeout=10)
            check(session.process.returncode == {"before-commit": 86, "after-commit": 87, "after-effect-insert": 88}[phase], "broker did not crash at the armed transaction boundary")
            session.start()
        session.ready(identity)
        if phase in ("after-commit", "executor-after-commit"):
            expected_count += 1
    elif scenario in ("stale-commit", "python-to-rust", "rust-to-python"):
        session.call("fault-kill", id=identity)
    elif scenario in ("sqlite-reopen", "suspend-resume"):
        session.call("suspend", id=identity)
        if scenario == "sqlite-reopen":
            session.stop()
            session.start()
        session.call("resume", id=identity)
    elif scenario == "terminal-cancel":
        session.call("cancel", id=identity)
        session.expect("INVALID_STATE", "resume", id=identity)
        check(session.inspect(identity)["lifecycle"] == "Cancelled", "terminal state changed")
        return dict(classification=REJECTION, verification=session.call("verify", id=identity))
    elif scenario == "handoff-forbidden":
        session.expect("EXECUTOR_NOT_ALLOWED", "handoff", id=identity, executor=other)
        check(session.inspect(identity) == before, "forbidden handoff mutated authority or killed its current executor")
        session.call("fault-release", id=identity)
        return dict(classification=REJECTION, verification=session.complete(identity))
    elif scenario in ("duplicate-start", "duplicate-effect", "conflicting-effect"):
        if scenario == "duplicate-start":
            session.expect("INVALID_STATE", "run", id=identity, executor=other)
        else:
            candidate = progress(values, config.chunk, config.barrier)
            if scenario == "conflicting-effect":
                candidate["accumulated_result"] += 1
                session.expect("IDEMPOTENCY_CONFLICT", "stale-probe", id=identity, credential=old, progress=candidate)
            else:
                first_ack = session.call("stale-probe", id=identity, credential=old, progress=candidate)
                second_ack = session.call("stale-probe", id=identity, credential=old, progress=candidate)
                check(first_ack == second_ack, "identical duplicate changed its committed effect identity")
        check(session.inspect(identity) == before, "duplicate request changed committed authority")
        session.call("fault-release", id=identity)
        return dict(classification=REJECTION if scenario != "duplicate-effect" else RECOVERY,
                    verification=session.complete(identity))
    elif scenario == "lease-expiry":
        session.wait(lambda: session.inspect(identity)["lifecycle"] == "Ready", seconds=35)
        events = session.archive()["events"][identity]
        check(any(event["payload"]["details"].get("reason") == "lease-expired" for event in events), "lease did not expire using the real deadline")
    else:
        raise AssertionError("scenario has no implemented failure mechanism")
    recovered = session.inspect(identity)
    check(recovered["id"] == identity and recovered["contract"] == before["contract"], "identity or execution permissions changed")
    checkpoint_oracle(recovered, values, config.chunk)
    check(recovered["epoch"] > before["epoch"], "old executor was not fenced")
    check(recovered["continuation"]["last_committed_chunk"] == expected_count, "failure committed too much or lost committed progress")
    session.expect("STALE_EPOCH", "stale-probe", id=identity, credential=old,
                   progress=progress(values, config.chunk, config.barrier))
    result = finish(session, identity, values, config.chunk, other)
    return dict(classification=RECOVERY, verification=result, identity_preserved=True,
                before_checkpoint=before["continuation"], recovered_checkpoint=recovered["continuation"],
                epoch_before=before["epoch"], epoch_after=recovered["epoch"], stale_rejected=True,
                expected_result=sum(values), resumes_with=other)


def run_case(config, path):
    config.validate()
    started = time.perf_counter_ns()
    session, result = None, dict(schema_version=1, config=asdict(config))
    try:
        session = Session()
        result.update(experiment(session, config))
        result["expectations_met"] = True
    except Exception as error:
        result.update(classification=UNEXPECTED, expectations_met=False,
                      explanation=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
    finally:
        if session:
            try:
                session.close()
                result["evidence"] = session.captured
                result["operations"] = session.trace
            except Exception as error:
                result.update(classification=UNEXPECTED, expectations_met=False, cleanup_error=str(error))
    result["duration_us"] = (time.perf_counter_ns() - started) / 1000
    result["replay"] = f"python3 system/fetian-fca/validation/lab.py replay --case {path} --output NEW_DIRECTORY"
    atomic_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("deterministic", "stress", "replay", "security"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2090)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--scenario", choices=FAULTS + PROBES + ("lease-expiry",))
    parser.add_argument("--include-expiry", action="store_true")
    args = parser.parse_args()
    if args.runs < 1 or args.runs > 100000:
        parser.error("runs must be 1–100000")
    if args.output.exists():
        parser.error("choose a fresh output directory; evidence is never overwritten")
    args.output.mkdir(parents=True, mode=0o700)
    adopted = subreaper()
    if args.mode == "replay":
        if args.case is None:
            parser.error("replay requires --case")
        configs = [Config(**json.loads(args.case.read_text())["config"])]
    elif args.scenario and args.mode != "stress":
        configs = [generated(args.seed, args.scenario)]
    elif args.mode == "stress":
        rng = random.Random(args.seed)
        configs = [generated(rng.getrandbits(64), args.scenario) for _ in range(args.runs)]
    else:
        scenarios = PROBES if args.mode == "security" else FAULTS
        configs = [generated(args.seed + index, scenario) for index, scenario in enumerate(scenarios)]
        if args.include_expiry:
            configs.append(generated(args.seed + len(configs), "lease-expiry"))
    atomic_json(args.output / "plan.json", dict(schema_version=1, master_seed=args.seed,
                environment=environment(), subreaper_enabled=adopted, cases=[asdict(config) for config in configs]))
    counts, failures = {}, []
    for index, config in enumerate(configs):
        path = args.output / f"run-{index:06d}-seed-{config.seed}.json"
        result = run_case(config, path)
        category = result["classification"]
        counts[category] = counts.get(category, 0) + 1
        if not result["expectations_met"]:
            failures.append(dict(index=index, seed=config.seed, scenario=config.scenario, report=path.name, explanation=result.get("explanation", result.get("cleanup_error"))))
        if index % 25 == 0 or failures and failures[-1]["index"] == index:
            print(json.dumps(dict(completed=index + 1, planned=len(configs), counts=counts)), flush=True)
    summary = dict(schema_version=1, mode=args.mode, master_seed=args.seed, completed=len(configs),
                   expectations_met=len(configs) - len(failures), counts=counts, failures=failures,
                   recovered=counts.get(RECOVERY, 0), rejected=counts.get(REJECTION, 0),
                   safely_unrecoverable=counts.get(SAFE_FAILURE, 0), unexpected_failures=len(failures),
                   replay_contract="same configuration and logical fault boundary; OS scheduling/IDs/latencies are not bit-identical")
    atomic_json(args.output / "summary.json", summary)
    print(json.dumps(summary), flush=True)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
