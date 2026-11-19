# FCA Phase 2 research validation

The bounded FCA workload works across executor death and compatible Rust/Python
replacement in these experiments. This is research validation of one local
semantic ABI, not a production operating-system execution guarantee.

The [complete Linux CI run](https://github.com/fetian-debug/FetianOS/actions/runs/44480983113)
on source `7723bda6e2902d44c351fe7edf59d30ff3cdb707` passed **all five jobs**:
fast, fault, security, stress and performance. The stress command actually
executed all 1,000 cases using master seed 2090; it did not merely configure them.

| Experiment | Actual result |
|---|---|
| Randomized suite | 1,000 expectations met; zero unexpected failures |
| Successful recoveries within that suite | 408 |
| Expected rejections within that suite | 514 |
| Safely detected unrecoverable stores within that suite | 78; not recoveries |
| Deterministic suite, including real lease expiry | 23/23: 15 recovery, 5 rejection, 3 unrecoverable |
| Actual private-worker IPC probes | 15/15 expected rejections |
| Rust model/store/protocol tests | 16 passed |
| Existing real-process regression tests | 19 passed |
| Harness/evidence oracle tests | 6 passed |
| Performance experiments | 12 measured size/population conditions, 10 restarts each |
| Default desktop/native checks on WSL | 6 Rust + 116 Python tests; telemetry, profile and shell validation passed |

## Real failures and corrections

The first deterministic run found a preexisting **forbidden handoff bug**:
requesting an executor excluded by the immutable contract revoked/killed the
healthy worker before returning `EXECUTOR_NOT_ALLOWED`. Admission now checks the
replacement permission and normal-mode test-barrier restriction **before**
revocation. A forbidden replacement preserves the complete authority snapshot,
including epoch/current executor/checkpoint, and the original executor finishes.
Retained [before-fix evidence](evidence/phase2/forbidden-handoff-before-fix.json)
and [successful exact-seed replay](evidence/phase2/forbidden-handoff-fixed-replay.json)
show the regression and correction. The seed is 2111.

The first 1,000-case WSL run had 288 unexpected outcomes, primarily an experiment
oracle error: it compared a valid rejection response with the later socket EOF.
The corrected oracle selects the actual request-response audit event; malformed
frame/envelope cases select transport rejection instead. The earlier summary is
retained as [initial WSL evidence](evidence/phase2/wsl-initial-summary.json), not
silently replaced by a successful run.

The subsequent WSL 1,000-case run met 995 expectations and retained **five timeout
failures** (two socket deadlines, three broker wait deadlines). Together with
four timeout cases from the initial run and one separate probe run, all ten
exact configurations passed when replayed without overlapping compilation.
This suggests host/load sensitivity; its root cause is **not established**.
Deadlines were not relaxed, failed trials were not automatically retried into
success, and the WSL run is not reported as 1,000/1,000. See the
[WSL summary](evidence/phase2/wsl-final-summary.json) and
[ten replay results](evidence/phase2/wsl-timeout-replays.json).
Timeout diagnostics now retain load average and broker thread wait channels for
future occurrences. The separate GitHub Ubuntu Linux run completed all 1,000
with zero unexpected outcomes using the same recorded workload configurations.

## Evidence and reproduction

[Evidence manifest](evidence/phase2/manifest.json) identifies the CI source,
checksums and downloaded reports. [Stress summary](evidence/phase2/stress-summary.json),
[complete 1,000-case plan](evidence/phase2/stress-plan.json),
[all raw experiments, gzip JSON lines](evidence/phase2/randomized-runs.jsonl.gz),
[fault summary](evidence/phase2/fault-summary.json),
[protocol summary](evidence/phase2/protocol-summary.json),
[security evidence](evidence/phase2/security.json) and
[full performance observations](evidence/phase2/performance.json) are retained
in Git so the essential evidence survives CI artifact expiration. The full
workflow also uploads reports/logs with 14-day retention. Hashes are not signed
attestations; traces/snapshots redact usable lease identifiers.

```sh
bash scripts/build-fca.sh --release
export FCA_BIN_DIR="$PWD/system/fetian-fca/target/release"
python3 -m unittest discover -s system/fetian-fca/validation -p 'test_*.py' -v
python3 system/fetian-fca/tests/process_tests.py
python3 system/fetian-fca/validation/lab.py deterministic --include-expiry --output fca-evidence/fault
python3 system/fetian-fca/validation/lab.py security --output fca-evidence/probes
python3 system/fetian-fca/validation/security.py --output fca-evidence/security
python3 system/fetian-fca/validation/lab.py stress --runs 1000 --seed 2090 --output fca-evidence/stress
python3 system/fetian-fca/validation/performance.py --output fca-evidence/performance
# Replay any saved experiment; always choose a new output directory:
python3 system/fetian-fca/validation/lab.py replay --case docs/fca/evidence/phase2/forbidden-handoff-before-fix.json --output fca-evidence/replay
```

To replay a case from the compressed retained set, decompress one JSON line into
a file, then pass that file to `replay --case`. Each line includes the complete
configuration, outcome, operation trace, journal, effects and snapshots. Replay
repeats the logical fault window; process IDs and scheduling are not reproduced.

## Scope and preserved system

FCA remains opt-in, excluded from the default workspace and ISO staging. No
service was enabled, desktop/boot/login/Sway recovery changed, or installer
activated. The ISO workflow was not edited or dispatched, and the research
branch was not merged to main. The published
[preview-7-1 release](https://github.com/fetian-debug/FetianOS/releases/tag/preview-7-1)
retains its 18 November assets, sizes and server SHA-256 digests. Its combined
ISO remains 2,446,166,016 bytes, SHA-256
`bf400ab7801805d6375511d07f4c605667d73e539b1e70a06843fc33514ea11f`.
Asset metadata was rechecked; the ISO was not rebuilt or downloaded again.

Kernel resource exhaustion remains unverified because delegation was unavailable
on the tested launches; strict refusal was actually verified. Same-UID hostile
code is not isolated. No external provider effect adapter, power-cut/storage
fault proof, arbitrary program migration or general exactly-once computation is
claimed. Read the [fault model](fault-model.md), [security review](security-review.md),
[performance results](performance.md), [prior-art comparison](prior-art-comparison.md)
and [limitations](limitations.md) before extending this prototype.
