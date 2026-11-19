# Stability acceptance matrix

**Daily-use acceptance: NOT MET.** Local checks and identified historical ISO
evidence do not satisfy this branch's untested boot, desktop and hardware gates.

| Gate | Evidence/status | Acceptance implication |
|---|---|---|
| Clean debug/release | Both Rust crates built in fresh temporary targets; baseline-clean logs | Source build verified; no ISO inference |
| Existing tests | Baseline counts/logs retained; final results recorded separately | Do not replace failed attempts with later passes |
| Targeted defects | Nine regression tests pass after fixes | Fixture/model scope only |
| Formatting/Clippy/locks | Both crates checked locally | Lock resolution is not a vulnerability scan |
| Advisory scan | Initially unavailable; supplemental scan records tool/database/results | See security report and exact JSON findings |
| Staging/service syntax | Both profiles staged; systemd-analyze syntax checks | No installed service startup proof |
| GTK file workflows | Baseline image-preview timeout retained; later attempt separately recorded | No Wayland/session acceptance |
| FCA | Implementation unchanged; process/fault/security/stress records retained | Inspect failures and known trust/resource limits |
| ISO/UEFI boot of branch | Untested: no mkarchiso, Docker or QEMU locally | Critical open gate |
| Legacy BIOS | Not configured by profile | Not claimed supported |
| Login/recovery desktop | Source/fixtures only; no real sign-in/crash/relogin on branch | Critical open gate |
| Lock/idle/suspend | Configuration retained and rate-limited; runtime untested | Security-critical open gate |
| Hardware/monitor/audio/network | Untested physical devices | No new support certification |
| User data/upgrades | Isolated atomic-write failures checked; no installed upgrade | No universal data-loss guarantee |
| Idle CPU/RAM/journal/filesystem | No installed guest measurements | Performance/health acceptance open |
| 24-hour soak/reboot loops | Not completed | No long-duration claim |
| Published preview/main | No release workflow or merge authorized/executed by this mission | Preserve existing artifacts |

Machine-readable command results and explicit untested areas live in
evidence/*/results.json and evidence/final/acceptance.json. The final report
reconciles supplemental/control results without rewriting the initial run.
