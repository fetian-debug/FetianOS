# System stabilization report

**Acceptance: NOT MET. This branch is not certified for daily use.**

The branch `stabilization/system-reliability` applies seven scoped reliability
corrections without changing FCA, the published ISO, the default desktop or
application policy. Fixes cover bounded configuration reads, malformed fields,
session-lock ownership, optional-child isolation, temporary-file cleanup,
explicit restart-rate bounds and actual ISO payload extraction.
[Defects, severity, reproduction and regression mapping](defects.json).

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
The byte-identical Linux-executable control completed all 1,000 cases: 997 met
expectations and three different cases timed out. Its deterministic control
passed all 23. Relocation did not remove the WSL timing issue. Initial failed
runs remain failures; neither deadlines nor SQLite durability was weakened.

[Hosted FCA run 44505308690](https://github.com/fetian-debug/FetianOS/actions/runs/44505308690)
at source `4b41effbc9451c05aac19ea52c346e52df414a1c` passed all five jobs and all
1,000 cases met expectations: 408 recoveries, 514 rejections, 78 safely detected
unrecoverable cases. Complete plans/raw records, boundary and performance evidence
are retained. This supports environment-sensitive timing but does not identify
every timeout's cause or establish a daily-use guarantee.

The first GTK smoke timed out in image preview. The later local smoke and hosted
source/GTK checks passed with the existing deadlines; the preview implementation
was not changed. Root cause of that
timing failure remains unresolved, not proven environmental by a later pass.

Candidate Sway and Hyprland checks completed in
[ISO workflow 44505284369](https://github.com/fetian-debug/FetianOS/actions/runs/44505284369)
with `desktop=both`, `publish=false`. Source/GTK and Sway image/UEFI/live-account
checks passed at source 4b41eff. Its ISO SHA-256 is
`fe476ab1b14ed5b88e9ebd30088c20cca178e9dada1d0a973c18a707b24b6802`.
Hyprland generated an ISO and verified pins but failed embedded-root extraction
before boot. Publication was skipped. The extractor fix rebuilt Hyprland
in [run 44540057276](https://github.com/fetian-debug/FetianOS/actions/runs/44540057276)
with publication disabled. All 130 Python tests passed without skips, including
the real >2 GiB byte-exact extraction fixture. The rebuilt Hyprland image passed
static embedded-root verification and actual UEFI/live-account boot at source
`e155b7574c9b082ca0edcafec5cc302bc9a259fa`. Its ISO SHA-256 is
`4ab3545d402c5d13adb2036da311d09d43e4a2700f66f57103520ff66c51a47c`.
The repaired run completed successfully and its publication job was skipped.
The local post-fix Python suite completed 130 tests with two real ISO-tool cases
explicitly skipped; three new contract checks passed. Graphical login,
lock/unlock, actual Wayland failure recovery, installation/upgrade, hardware,
idle-resource measurements and a 24-hour soak remain untested. The existing
preview's historical boot evidence is not assigned to this new source branch.

The user confirmed an HP 15-bs0xx/i5-7200U/Intel HD 620/AMD target. AMD's exact
PCI ID, RAM and storage remain pending. The [live-USB plan](hp-15-bs-live-test.md)
supports a physical trial without enabling installation or claiming hardware acceptance.

See [audit](system-audit.md), [matrix](stability-matrix.md),
[reproduction](failure-injection.md) and evidence/*/results.json for command-level
results. Completed candidate and FCA jobs are source-identified in the raw
metadata; a later documentation/evidence commit does not create a new tested ISO.

The published preview remains release 450149449 / preview-7-1 with its original
part sizes/digests, checked read-only. Main was not merged. FCA implementation,
contracts, dependencies, opt-in staging and normal startup isolation are unchanged.
Candidate images are CI artifacts; no production stability or installation
acceptance is asserted. The next acceptance work is the actual HP live-USB
trial, followed by separate graphical, recovery, installed-system and soak tests.
