# Failure injection and reproduction

Run from a Linux development checkout with Rust 1.89, rustfmt, Clippy, a native
linker and the locked FCA dependencies available. Commands do not install services:

```sh
python3 -m unittest discover -s tests -p test_stability.py -v
python3 scripts/stability-check.py --phase final --output NEW_EVIDENCE_DIRECTORY --stress-runs 1000
python3 scripts/stability-check.py --phase final --output NEW_CLEAN_DIRECTORY --clean-only
```

Choose fresh output directories. Add `--gtk-prefix /path/to/extracted/dependencies`
only for the local extracted GTK stack; ordinary GTK fixtures also have the
existing `make gtk-check` path. Supply cargo-audit on PATH for advisory scans.
Missing tools, timeouts and failed commands are recorded without a blanket pass.
Use `--gtk-prefix /` with system-installed GTK dependencies. For the executable
filesystem control, copy the release `fetian-*` binaries and Python executor to
a fresh Linux temporary directory and provide `--fca-bin-dir THAT_DIRECTORY`.
Compare SHA-256 before use; preserve the seeds and deadlines. This changes the
executable filesystem, not the FCA implementation or SQLite durability settings.

| Injection | Mechanism | Scope |
|---|---|---|
| Malformed configuration | Invalid URI/field values and a real FIFO | Disposable preferences |
| Interrupted/disk-full writes | ENOSPC at replace/fsync | Mocked syscall failure; not a full disk |
| Session ownership | Real fixture compositor checks inherited descriptor | Unprivileged child; no Wayland |
| Optional shell death/missing command | Controlled child mocks | Does not run/kill actual applets |
| Restart storms | Explicit rate-window checks and staged unit syntax | No live user-manager failure injection |
| Worker/broker crash, interrupted handoff | Existing FCA process/lab suites | Private processes and SQLite files |
| Resource exhaustion | Existing bounded FCA admission tests | Kernel controller enforcement unavailable |
| Unavailable network | Existing application error/provider fixtures | No host network disconnection |

Baseline regression output and its exact test source are retained under
evidence/regressions-before*. The first GTK timeout also remains. The full runner
records commands, exit codes, durations, logs and checksums after each step.
Its exit is nonzero for unavailable required checks; acceptance.json remains
stable=false while critical runtime gates are untested.

No host reboot, suspend, disk fill, actual user-data corruption, real desktop
termination or destructive filesystem test was performed. VM, 24-hour soak,
memory-leak monitoring, reboot loops, concurrent GUI workloads and installed
update interruption remain untested rather than passing by omission.
