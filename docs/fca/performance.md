# FCA Phase 2 measured performance

Actual optimized Linux measurements from [CI run 44480983113](https://github.com/fetian-debug/FetianOS/actions/runs/44480983113), source `7723bda6e2902d44c351fe7edf59d30ff3cdb707`. No estimates are substituted for missing observations.

Environment: Ubuntu 24.04 runner, kernel `7.0.0-1014-aws`, Intel(R) Xeon(R) 6975P-C, 4 logical CPUs, Python 3.12.3, Rust 1.89.0, bundled SQLite. Full source/binary/harness hashes, environment, raw samples, counts, storage and CPU/RSS observations are in [performance.json](evidence/phase2/performance.json).

Each condition admits 1, 8, 32 or 64 resident authorities over 64, 512 or 4,096 integers, chunk size 32. Execution concurrency is **one**. Every authority runs Rust through chunk 1, then hands off to Python through chunk 2. All except the last finish; the last stays suspended at chunk 2 for ten restart/recovery measurements. Thus population 1 measures a two-chunk pending job, not full-input execution. This is population/storage scaling, not parallel throughput scaling.

## Distributions at 4,096 integers and 64 authorities

Latency units are microseconds. Percentiles use nearest rank. Small-sample p99 is descriptive; with ten restarts it equals the observed maximum and is not a reliable tail estimate.

| Operation | n | min | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| authority_creation_us | 64 | 10,814.68 | 10,981.00 | 11,360.91 | 11,874.17 | 11,874.17 |
| lease_acquisition_us | 128 | 79.00 | 210.00 | 445.00 | 655.00 | 739.00 |
| gated_launch_rpc_us | 64 | 6,165.59 | 6,390.30 | 6,780.28 | 7,057.75 | 7,057.75 |
| effect_checkpoint_commit_us | 8066 | 211.00 | 323.00 | 646.00 | 718.00 | 1,171.00 |
| checkpoint_barrier_rpc_us | 64 | 4,354.29 | 5,067.99 | 5,413.51 | 5,590.81 | 5,590.81 |
| handoff_rpc_us | 64 | 7,662.12 | 8,047.24 | 8,605.27 | 8,680.24 | 8,680.24 |
| restart_wall_us | 10 | 152,363.07 | 156,215.41 | 157,716.72 | 157,716.72 | 157,716.72 |
| store_verification_recovery_us | 10 | 149,822.00 | 150,260.00 | 151,551.00 | 151,551.00 | 151,551.00 |
| direct_python_parse_sum_us | 30 | 291.61 | 302.52 | 311.67 | 312.61 | 312.61 |

Creation includes import and creation RPCs (and one contract-template invocation per session). Lease acquisition is timed only around the durable store lease call; gated launch additionally includes process bootstrap and resource admission. Effect/checkpoint latency includes the atomic broker-managed transaction, excluding ACK transport. Checkpoint RPC is a durable barrier for accepted state. Handoff RPC includes revocation, group cessation and replacement bootstrap; it does not include the replacement completing its next chunk. Restart wall includes process startup and full store verification/reconciliation.

Direct Python parses and sums in an existing interpreter without process startup, IPC, durability or audit. It is a lower-level computation baseline and cannot justify a platform superiority claim. There is no measured comparison against Temporal, CRIU or another supervisor.

## Observed population and storage scaling

| Integers | Authorities | Commit p50 us | Restart p50 us | Broker RSS KiB | Broker CPU s during work | SQLite allocated bytes | Journal events |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 1 | 362 | 7,321.43 | 5532 | 0.00 | 81920 | 89 |
| 64 | 8 | 297 | 8,437.34 | 5780 | 0.04 | 233472 | 341 |
| 64 | 32 | 286 | 12,835.14 | 6300 | 0.17 | 708608 | 1205 |
| 64 | 64 | 283 | 18,788.43 | 7092 | 0.36 | 1376256 | 2357 |
| 512 | 1 | 429 | 7,072.77 | 5588 | 0.00 | 81920 | 89 |
| 512 | 8 | 232 | 10,259.00 | 6040 | 0.07 | 491520 | 733 |
| 512 | 32 | 248 | 20,587.65 | 7628 | 0.30 | 1839104 | 2941 |
| 512 | 64 | 243 | 33,394.35 | 7816 | 0.61 | 3674112 | 5885 |
| 4096 | 1 | 449 | 7,055.18 | 5636 | 0.00 | 98304 | 89 |
| 4096 | 8 | 322 | 23,234.09 | 7912 | 0.46 | 2551808 | 3869 |
| 4096 | 32 | 323 | 79,279.83 | 7856 | 2.02 | 10809344 | 16829 |
| 4096 | 64 | 323 | 156,215.41 | 7892 | 4.07 | 21938176 | 34109 |

CPU seconds come from `/proc` user+system ticks, with tick resolution; RSS values are point samples, **not peak memory**. Per-condition Rust worker RSS distributions, separate SQLite/WAL/SHM file sizes, effect counts, per-authority event growth and broker before/after samples are retained in raw evidence. Restart events contribute to the final journal counts. Absolute values depend on CPU, storage, SQLite/filesystem synchronization and shared runner load.

The larger retained journal raises startup verification cost: for 4,096 integers the median restart is about 7.1 ms with one pending authority and 156.2 ms at 64 authorities. This is an observation of these fixtures, not an extrapolated complexity or capacity guarantee. No event compaction is implemented.

Kernel cgroup controls were unavailable in these launches, so enforcement overhead is **not measured**. Normal-mode transaction/lease timing instrumentation retains at most 256 recent samples plus lifetime counts. The benchmark checks the window before consuming samples so it cannot quietly publish truncated distributions.

```sh
export FCA_BIN_DIR="$PWD/system/fetian-fca/target/release"
python3 system/fetian-fca/validation/performance.py --output fca-evidence/performance
```

The command records every raw observation and requires a fresh output directory. Use the smaller `--sizes 64 --populations 1 --restart-samples 3` only for debugging, not as a replacement for the recorded matrix.
