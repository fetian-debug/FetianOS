# System stabilization report

**Acceptance: NOT MET. This branch is not certified for daily use.**

The branch `stabilization/system-reliability` applies six scoped reliability
corrections without changing FCA, the published ISO, the default desktop or
application policy. [Defects and exact regression mapping](defects.json).

Completed local evidence: clean debug/release builds for both Rust crates,
formatting and Clippy, six native Rust and sixteen FCA Rust tests, 125 Python
regressions after fixes (116 before), nineteen FCA process tests, six harness
oracle tests, both staged profiles/unit syntax, and the nine targeted regressions.
The supplemental RustSec scan found zero listed vulnerabilities and no warnings
at the retained database revision; this does not certify all OS packages.

The original post-fix FCA batch completed all 1,000 cases: 995 met expectations,
five timed out. Its deterministic suite also has one timeout. The baseline
deterministic suite passed all 23. One captured daemon thread waited in
`jbd2_log_wait_commit`; no durability or authorization check was weakened.
The same-code Linux-executable control is in progress and will be recorded
separately. Initial failed runs are preserved.

The first GTK smoke timed out in image preview. The later identical-timeout
smoke passed; the preview implementation was not changed. Root cause of that
timing failure remains unresolved, not proven environmental by a later pass.

ISO build and UEFI boot of this branch have not yet completed. Graphical login,
lock/unlock, actual Wayland failure recovery, installation/upgrade, hardware,
idle-resource measurements and a 24-hour soak remain untested. The existing
preview's historical boot evidence is not assigned to this new source branch.

See [audit](system-audit.md), [matrix](stability-matrix.md),
[reproduction](failure-injection.md) and evidence/*/results.json for command-level
results. This report will be updated with the remaining control/CI outcomes.
