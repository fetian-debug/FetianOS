# FETIANOS verification — 2026-11-18

This milestone extends the existing repository. Rust system components, Sway
and text recovery, existing applications and opt-in Hyprland remain. Thunar is
still the default; FetianFiles is a hidden, explicitly launched preview. No
packages were removed, no real disk was used and no installation was performed.

## Changed files and features

| Area | Files / resulting behavior |
|---|---|
| Application policy | `manifests/applications.json`, `scripts/application-audit.py`, `docs/application-inventory.json`, `docs/application-strategy.md`: one primary per task, all declared packages, source desktop entries, defaults, opt-in cohort and optional runtime plans |
| File manager | `apps/fetian-files/{fetian_files,fileops,archiveops,preferences,image_preview}.py`, CSS and desktop entry: native navigation, jobs, tabs/split/views, search filters, bookmarks, local tab restoration, permissions/batch rename, GIO clipboard/Trash/devices, archives and bounded text/raster previews |
| Integration | Development/image `fetian-files` wrappers, `scripts/stage-profile.py`: preview in both profiles, no MIME takeover; new hidden Vim-in-Foot editor entry and text MIME defaults; single main categories for Control Center/Apps/Calendar; Sway panel monitor clicks use Control Center |
| Image policy | `system/boot/image_policy.py`, image application hook/marker: XDG shadows hide actual installer launcher IDs, preserve packages/backends, record audit and remove build state |
| Build / artifacts | `scripts/{build-environment,release-artifacts,select-iso,verify-boot-artifacts}.py`, build/verification/boot shell scripts: capability audit, complete evidence bundles, embedded squashfs validation, checksums and actual-byte comparison |
| VM / guest | `scripts/vm-test.py`, `system/boot/session_audit.py` and wrapper: disposable qcow2, paired OVMF, serial/QMP artifacts, reboot without ISO, read-only guest evidence |
| Installer | `installer/plan.json`, inactive `calamares-preview` templates/cleanup contract, `scripts/verify-installed.py`: modular plan and fail-closed read-only target checks; no destructive implementation |
| Verification | File/archive/release/security/GTK tests; source/boot-probe test updates; `scripts/verify-staged.py`; Makefile/dependency/profile checks, `.gitattributes`, `.gitignore`, `.github/workflows/source-checks.yml` |
| Documentation | README/changelog, build/install/known-issue pages and new application, file-manager, VM, installer, recovery and release-acceptance documents |

There is no `.git` directory in this snapshot; no commit, PR or Git diff was
created. Rust library/collector code and hardened metrics service definitions
were retained.

## Executed checks

Host: Ubuntu 22.04.5 x86_64 WSL; workspace-local Rust **1.85.1**. Official Ubuntu
GTK 4.6 runtime/introspection and desktop-validator packages were downloaded and
extracted under `.build-tools`, without installing host packages. UI checks ran
under Xvfb with temporary HOME/XDG directories and a disposable D-Bus session.

| Check | Actual result and limit |
|---|---|
| Rust tests | **6 passed**, including Linux metrics, malformed inputs and snapshot failure handling |
| Python regressions | **97 passed**, final run 4.346 seconds |
| Formatting / lint / build | Rust formatting, Clippy with warnings denied, locked/offline tests and optimized release build passed |
| Real telemetry | Live Linux JSON, compatibility wrapper, atomic snapshots and CLI failure behavior passed |
| Native GTK | Listing/hidden files, text/Arabic and bounded raster preview, SVG refusal, actual native URI clipboard deserialization and local GIO Trash/restore, views/tabs/split/search/bookmarks, appearance/reduced-motion/RTL and keyboard/URL guards passed |
| Simulated device failures | Fake providers tested MTP disconnect, mount/auth failure, busy unmount and refused eject; no false success |
| File/archive safety | Disposable copy/move/rename/delete, conflicts, permissions, cancellation, links, undo, batch rollback, search limits; ZIP/TAR/GZIP/XZ roundtrips, compression settings, selected extraction, malformed/traversing/link entries and expansion limits passed |
| Profiles / systemd | Both profiles staged; 8 Sway and 12 Hyprland user-unit syntax checks passed with temporary ExecStart substitutions. Metrics and live-user unit syntax passed. No system services installed/enabled/started |
| Launchers | Application entries passed `desktop-file-validate`; SDDM session entries passed separate structural tests |
| Inventory | **105 base packages**, 15 cohort records including two already in base: **118 distinct direct declarations**. Nine source desktop entries, including legacy/session copies. Zero removals |
| CI | Workflow YAML parsed; hosted workflow not executed |
| VM preflight | Exit **2**, correctly reporting missing QEMU/qemu-img/OVMF; no VM boot |
| ISO selection | Exit **1**, correctly reporting no completed checksummed image; no ISO published |

The duplicate-ZIP fixture intentionally emits a duplicate-name warning.
`systemd-analyze` reported unrelated WSL netplan permission and snapd version
warnings; checked commands exited successfully. User-unit syntax checks used
`ExecStart=/usr/bin/true` only in disposable copies. Metrics checks substituted
the real built binary path in temporary copies. These do not prove service
activation, installed sandbox behavior or target device visibility.

The older desktop validator does not recognize SDDM's session-specific
`DesktopNames` key, so application entries and session entries are checked
separately. Session tests preserve the absolute wrappers, TryExec and desktop
names. [SDDM reads that key](https://github.com/sddm/sddm/blob/develop/src/common/Session.cpp).
Real session startup remains unverified.

Local logs: `logs/native-source-profile.log`, `python-final.log`,
`staged-units.log`, `live-rust-snapshots.log`, `gtk-files.log`,
`desktop-entries.log`, `vm-preflight-blocked.log`, `iso-selector-no-image.log`
and `verification-summary.json`. Logs and `.build-tools` are ignored generated
artifacts. A native Xvfb screenshot was inspected while correcting pane layout.

## Blocked and unverified

[Recorded capabilities](build-environment-2026-11-18.json) show Ubuntu rather
than the supported Manjaro image host, missing `mkarchiso`, `pacman`, `pacman-key`,
`xorriso`, `isoinfo`, `qemu-system-x86_64`, `qemu-img` and `mcopy`, no paired OVMF
and no usable KVM. `unsquashfs`, C compiler, Python and local Rust are available.

No actual ISO construction/embedded-image validation, UEFI menu/boot, target
SDDM/Sway/Hyprland graphical login, installation or installed reboot occurred.
No independent real ISO builds were compared. Physical USB/MTP, audio, printing,
battery and other hardware remain untested. The Control Center's full libadwaita
UI was not run in this GTK-only runtime.

Release/EFI/installed-root/boot tests use labeled fixtures; comparison tests do
not establish reproducibility. Device providers are simulations. Local GTK,
clipboard, Trash/restore and preview tests use real APIs and disposable data.

## Security review and limitations

No privileged file-manager helper, automatic selected-file execution, implicit
overwrite, permanent-delete fallback, forced unmount or destructive disk job was
added. The GUI refuses root. Local jobs use descriptor-relative traversal and
no-clobber commit; parser workers have explicit size/memory/time limits. They
are not full filesystem/network sandboxes. Races, partial multi-item operations,
abrupt termination and power loss remain limitations.

The installed-root checker rejects live/build state, leftover live accounts or
homes, unlocked root, missing normal password-hash shape, unsafe sudo/autologin,
live initramfs configuration and missing persistent boot/session integration.
It cannot prove password strength/authentication, sudo syntax, actual initramfs
contents or successful boot. Target cleanup is a contract, not an implemented
deletion job. Installer templates remain inactive and launchers disabled.

FetianFiles still lacks 7z/encrypted archives, TAR creation, PDF/audio/video
previews, recursive remote transfer, full localization, screen-reader acceptance
and large-directory profiling. Native pointer drag/drop and real SMB/MTP/device
workflows require target-session testing. Keep Thunar, Xarchiver, imv, mpv and
all existing backends. Package metadata checks are not a distribution-wide legal
audit. See [feature/security boundaries](fetian-files.md).

## Exact commands and next milestone

Source verification on Linux with the required tools:

```bash
make native-check native profile-check
python3 scripts/verify-staged.py
python3 scripts/application-audit.py
# Requires GTK4/python-gobject, Xvfb and dbus-run-session:
make gtk-check
```

On a **disposable x86_64 Manjaro host**:

```bash
sudo pacman -S --needed archiso libisoburn cdrtools qemu-desktop edk2-ovmf mtools squashfs-tools rust base-devel python
make environment
make native-check native profile-check
sudo make build
make validate
make test-uefi
# Separate opt-in candidate:
sudo make build-hyprland
python3 scripts/vm-test.py --iso output/BUNDLE/IMAGE.iso --display gtk --seconds 900
```

Use matching `OVMF_CODE`/`OVMF_VARS` overrides when needed and select the desired
desktop bundle explicitly. For independently executed comparison builds, freeze
the entire signed dependency closure/toolchain and use the same epoch:

```bash
sudo env SOURCE_DATE_EPOCH=1794950400 make build
python3 scripts/release-artifacts.py compare output/FIRST/build.json output/SECOND/build.json
```

Next: real image construction and disposable UEFI live-session acceptance.
Only after implementing/reviewing target cleanup should explicitly confirmed
disposable-disk installation and reboot tests begin. Keep promotion/removal and
installer enablement behind [release gates](release-acceptance.md).
FETIANOS is not ready for public installation.
