# Stability and performance baseline

Measured before product fixes on x86_64 WSL2/Python 3.10.12/Rust 1.89.0; see
[environment](evidence/baseline/environment.json) and [command results](evidence/baseline/results.json).
The clean builds use fresh temporary target directories; their results are
[separate](evidence/baseline-clean/results.json). Ordinary cached build results
are not mislabeled as clean builds.

Baseline source checks: Rust formatting/Clippy succeed for both crates; six
native Rust tests, sixteen FCA Rust tests, 116 Python regressions, six FCA harness
oracles and nineteen FCA real-process tests pass. All 23 deterministic cases and
15 protocol probes meet their respective recovery/rejection expectations.
Both profiles stage and unit syntax validates; this starts no service.

Baseline defects: nine targeted tests produce eleven failure records including
subtests (two control tests already pass). The retained log identifies the FIFO,
malformed-state, lock-descriptor, optional-child, rate-policy and temporary-file
failures. The existing GTK smoke also times out at image preview. cargo-audit
is initially missing. These outcomes are not removed from the baseline.

| Requested measurement | Recorded status |
|---|---|
| Clean debug/release builds | Actual logs and elapsed times retained for both Rust crates |
| Tests/lints | Exact commands/counts/results retained |
| Startup duration, boot/login | Not measured for this branch |
| OS idle CPU/RAM | Not measured; WSL telemetry would describe the development environment |
| Journal/service/filesystem/crash health | Not measured in an installed FetianOS guest |
| Memory growth/FD leak/24-hour soak | Not completed; source inspection is not a soak test |
| Physical device errors | No target hardware available |

No performance optimization or speedup claim is made. Bounded reads and retry
policy address reproduced reliability risks. Individual command durations on a
shared WSL/Windows filesystem are not OS startup or idle benchmarks. A later
GTK pass alone cannot prove the baseline timeout was environmentally caused.
