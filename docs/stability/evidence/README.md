# Retained stability evidence

The baseline predates product fixes at source 06aa67f. The first code-fix commit
is 4b41effbc9451c05aac19ea52c346e52df414a1c. Later evidence/documentation commits
do not silently assign an ISO result to a different source revision.

* `baseline` and `baseline-clean`: initial commands and genuine fresh-target builds.
* `regressions-before*`: exact original test source and eleven failure records,
  including subtests, across nine test methods. Two controls already passed.
* `regressions-after.log`: first successful focused run. `regressions-final.log`
  adds the positive live-wrapper exclusion/cleanup check without changing product code.
* `final`: full local suite, including all 1,000 FCA cases (five timeouts), one
  deterministic timeout, and the later successful GTK smoke.
* `linux-fca-control`: byte-identical FCA executables on Linux temporary storage;
  all 1,000 cases completed with three different timeouts. This did not resolve
  the WSL timing problem or establish that executable location caused it.
* `hosted-fca`: source-identified GitHub run/job metadata and downloaded raw
  artifacts. All 1,000 cases met expectations: 408 recoveries, 514 rejections,
  78 safely detected unrecoverable cases. Those categories are not all recoveries.
* `dependency-audit`: official tool version/digest, advisory revision, unchanged
  lock hashes and zero listed findings; the original missing-tool failures remain.
* `supplemental`: additional admission/boundary checks and development-host
  telemetry. WSL metrics are not FetianOS idle-performance measurements.
* `iso-attempt-1`: successful Sway serial boot, failed Hyprland extraction,
  exact source/run identity and skipped publication. The raw PPM is binary.
* `iso-attempt-2`: repaired-candidate source job, including 130 tests with no
  skips and the opt-in real >2 GiB payload roundtrip. The repaired Hyprland
  image/UEFI/live-account probe passed; publication was skipped. Its exact
  source/checksum and raw serial/boot evidence remain separate from Sway's.

Completed FCA raw records are stored byte-for-byte in each `runs.tar.gz` with
an `archive-index.json` of entry hashes. Failed cases also remain as plain JSON.
Extract a chosen entry to a new temporary file to use lab.py's existing replay
command; preserve its configuration and choose a fresh output directory.
Three 1,000-case executions reuse the same seeded cases, not 3,000 unique cases.

`python3 scripts/verify-stability.py` checks record counts, plan/configuration
identity, classifications, failures, archives and command-log hashes. It verifies
evidence consistency, not OS stability, external peer review or all functional
properties. Raw whitespace is intentional. Checksums are local unsigned integrity
records; they do not make the evidence independent or cryptographically attested.
