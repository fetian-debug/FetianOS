# Stability acceptance matrix

**Daily-use acceptance: NOT MET.** Local checks and identified historical ISO
evidence do not satisfy this branch's untested boot, desktop and hardware gates.

| Gate | Evidence/status | Acceptance implication |
|---|---|---|
| Clean debug/release | Both Rust crates built in fresh temporary targets; baseline-clean logs | Source build verified; no ISO inference |
| Existing tests | 116 baseline Python tests; 125 after first fixes; 130 after extractor regression additions | Local real-tool skips and actual hosted outcomes retained separately |
| Targeted defects | Nine regression tests pass after fixes | Fixture/model scope only |
| Formatting/Clippy/locks | Both crates checked locally | Lock resolution is not a vulnerability scan |
| Advisory scan | Supplemental cargo-audit 0.23.0: zero listed vulnerabilities/warnings at recorded database revision | Dated lock scan, not an OS-wide security audit |
| Staging/service syntax | Both profiles staged; systemd-analyze syntax checks | No installed service startup proof |
| GTK file workflows | Baseline image-preview timeout retained; later attempt separately recorded | No Wayland/session acceptance |
| FCA | Hosted 1,000/1,000 expectations met; local 995/1,000 and control 997/1,000 | Local timing failures and trust/resource limits remain recorded |
| ISO/UEFI boot of branch | Sway passed at 4b41eff; repaired Hyprland passed at e155b75; original extraction failure retained | Source-identified serial/live-account boot, not graphical or hardware acceptance |
| Legacy BIOS | Not configured by profile | Not claimed supported |
| Login/recovery desktop | Source/fixtures only; no real sign-in/crash/relogin on branch | Critical open gate |
| Lock/idle/suspend | Configuration retained and rate-limited; runtime untested | Security-critical open gate |
| Hardware/monitor/audio/network | Untested physical devices | No new support certification |
| User data/upgrades | Isolated atomic-write failures checked; no installed upgrade | No universal data-loss guarantee |
| Idle CPU/RAM/journal/filesystem | No installed guest measurements | Performance/health acceptance open |
| 24-hour soak/reboot loops | Not completed | No long-duration claim |
| Published preview/main | Candidate workflows use publish=false; completed first publication job skipped; no main merge | Existing release remains separate from candidate artifacts |

Machine-readable command results and explicit untested areas live in
evidence/*/results.json and evidence/final/acceptance.json. The final report
reconciles supplemental/control results without rewriting the initial run.
