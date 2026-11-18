# FCA engineering validation report

Recorded 18 November 2026 on x86_64 WSL2, kernel
`6.18.33.2-microsoft-standard-WSL2`, Python 3.10.12. FCA uses the isolated Rust
1.89.0 toolchain and its own locked Cargo graph. Measurements use optimized
release binaries and real processes/SQLite in private temporary Linux storage.

## Demonstrated result

The same authority continued from Rust into Python after the Rust process was
actually terminated by SIGKILL and waited for. The durable termination event
records signal 9 and confirmed group cessation. At the kill, chunk 3 and input
position 192 were committed, with accumulated value -374,688. Python used epoch
2 after Rust's epoch 1 and finished all 4,096 integers with result 2,048, equal
to independent calculation. Verification found exactly 64 managed effects.
An old Rust commit returned `STALE_EPOCH`, including after completion.

The retained [raw measured evidence](evidence/linux-wsl-release-2026-11-18.json)
contains the real PIDs, authority ID, checkpoint, epochs, unsigned journal head,
resource availability and measurements. It is an experiment record, not an
externally authenticated attestation. The benchmark's separate repeated workload
uses -2048 through 2047 and therefore has expected result -2048; its embedded
handoff demo uses -2047 through 2048 and correctly has expected result +2048.

## Test coverage

- FCA Rust model/protocol/store suite: 16 tests covering IDs, contracts, terminal
  transitions, monotonic leases, integer ABI, frame bounds, idempotency/conflict,
  rollback, persistent fencing, invalid progress, missing capability, corruption,
  append-only guards, schema rejection, orphan admission and symlink rejection.
- FCA real-process suite: 19 tests passed in 8.713 seconds with release binaries.
  Includes Rust/Python agreement, deterministic SIGKILL handoff, suspension,
  cancellation, broker SIGKILL/restart, crashes immediately before commit and
  after commit before ACK, competing run requests, single writer across runtime
  directories, malformed protocol, strict resource rejection, export, failure
  policy, opt-in profile packaging and normal-mode rejection of fault operations.
- The release suite found a real launcher buffering race. A raw FD gate read
  fixed it; a deterministic test coalesces the gate and following descriptor in
  one write and proves no bytes are lost across exec.
- Default FETIANOS Python regression suite: 114 tests passed after packaging and
  nested documentation changes. The existing six Rust metrics tests and default
  offline checks are verified separately from the FCA dependency graph.

No tests replace persistence or process death with success-shaped mock outputs.
Packaging tests use a clearly labeled fake telemetry payload only to exercise
file copying; reference FCA programs and process tests use actual binaries.
Fault admission requires an explicit test daemon and is absent from its user unit.

## Measured costs

These are descriptive results from one local release experiment, not performance
guarantees or an apples-to-apples speedup claim. All table values are milliseconds.
The direct Python baseline parses and sums the same input but excludes process
startup, IPC, durability, audit and recovery; the managed path necessarily adds
substantial cost for those features.

| Measurement | Samples | Median | Range |
| --- | --- | --- | --- |
| Direct Python parse and sum | 20 | 0.503 | 0.489–0.731 |
| Operator status round trip | 20 | 5.402 | 4.167–5.725 |
| Durable authority creation | 5 | 9.163 | 6.387–15.436 |
| Lease plus gated launch | 5 | 24.551 | 20.481–27.731 |
| Managed Python to completion | 5 | 501.627 | 478.514–669.094 |
| Effect plus checkpoint FULL transaction | Last 256 | 4.159 | 1.236–79.726 |

The checkpoint barrier round trip was 9.701 ms. Revocation, kill/wait and
replacement launch took 42.015 ms in the benchmark. Restart wall time was
74.186 ms, of which 53.216 ms was store verification/recovery. These are separate
measurements from the embedded demo's own timing fields.

Broker point-sampled RSS grew from 4,780 to 6,372 KiB across the five measured
runs; its CPU counter advanced by 0.56 seconds. The Rust worker at a committed
barrier used 1,972 KiB RSS. These are process observations, not peak or whole-tree
memory/CPU totals. Five uninterrupted runs each produced 268 audit events for
64 effects. After the complete benchmark, the main SQLite file was 962,560
bytes, WAL 329,632 bytes and shared-memory file 32,768 bytes; those sizes include
multiple experiment authorities. The journal grows with accepted transitions
and effects, rather than remaining a constant-sized checkpoint.

## Boundaries and unverified areas

Actual cgroup limits were unavailable in this WSL delegation. The adapter
reported advisory/unavailable, and strict contracts failed before lease creation.
CPU throttling, OOM, pids exhaustion, accounting continuity and enforcement
overhead remain unverified on a properly delegated Linux host. No GPU enforcement.

Daemon restart recovery, real Rust termination, Python continuation and stale
commit rejection passed. No hostile same-UID sandbox, signed audit, remote
effects or automatic recovery execution is implemented. See [limitations](limitations.md).

The independent desktop ISO pipeline constructed actual images and ran actual
OVMF/QEMU boots. Its third recorded attempt reached Linux userspace but blocked
on an interactive firstboot timezone prompt; publication remained gated. A
live-only firstboot condition and console-font fix were pushed for another run.
That evidence does not validate FCA inside an ISO: default images exclude FCA.
No FCA-enabled ISO, physical hardware, graphical login or installation was tested.

## Reproduction and next research step

```sh
bash scripts/build-fca.sh --release
cargo fmt --manifest-path system/fetian-fca/Cargo.toml -- --check
cargo clippy --manifest-path system/fetian-fca/Cargo.toml --locked --all-targets -- -D warnings
cargo test --manifest-path system/fetian-fca/Cargo.toml --locked
FCA_BIN_DIR="$PWD/system/fetian-fca/target/release" python3 system/fetian-fca/tests/process_tests.py
FCA_BIN_DIR="$PWD/system/fetian-fca/target/release" python3 system/fetian-fca/tests/benchmark.py
system/fetian-fca/target/release/fetian-authority --json demo-handoff
```

The core APIs, files, dependencies and four-table schema are described in
[architecture](architecture.md); wire ABI, lifecycle and exact handoff order
have separate specifications. The optional GitHub workflow repeats lint, Rust
tests and actual release-process checks and retains handoff JSON as an artifact.
The [exact change manifest](change-manifest.json) lists created and modified
repository paths, including the retained third-party notices.

Next: run adversarial resource-exhaustion tests in a genuinely delegated user
cgroup, then add a second semantic workload with a precisely defined effect
boundary. Compare recovery and costs against an existing durable workflow
engine before drawing broader conclusions about the authority model.
