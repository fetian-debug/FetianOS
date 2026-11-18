# Disposable UEFI VM workflow

Run `python3 scripts/build-environment.py` first. This image targets x86_64 UEFI;
legacy BIOS and Secure Boot are not validated. The current WSL environment lacks
QEMU, qemu-img and paired OVMF firmware, so no actual VM boot has been executed.

On a disposable Manjaro build/test host:

```bash
sudo pacman -S --needed archiso libisoburn cdrtools qemu-desktop edk2-ovmf mtools squashfs-tools rust base-devel python
make environment
make native-check native profile-check
sudo make build
make validate
make test-uefi
# Select a specific completed bundle if both desktop variants exist:
python3 scripts/vm-test.py --iso output/BUNDLE/IMAGE.iso --expect live-account --seconds 240
python3 scripts/vm-test.py --iso output/BUNDLE/IMAGE.iso --display gtk --seconds 900
```

`OVMF_CODE` and `OVMF_VARS` can specify a matching firmware pair. CODE is attached
read-only; VARS is copied into each run. The runner creates a fresh 32 GiB sparse,
self-contained qcow2 under `work/vm/uefi-*`. It attaches no host block devices,
shared folders, USB passthrough or forwarded host ports. KVM is used only when
accessible; otherwise TCG software emulation is selected. No disk is deleted on
completion. Manually inspect and retain useful evidence before cleanup.

Each run stores serial.log, qemu.log and evidence.json, plus screen.ppm when QMP
capture succeeds at the deadline. The evidence records actual commands, firmware,
ISO digest, environment, serial observations and separate unverified acceptance
fields. The probe requests ACPI power-down at timeout, then terminates a stuck VM;
this does not count as a successful guest shutdown test.

A successful probe means Linux userspace appeared in serial output; optionally,
the live-user service reported readiness. It does not prove the boot menu was
visible, SDDM accepted a login, graphics worked or an installation completed.
Keep separate manual acceptance records and screenshots for those behaviors.

Inside the actual guest, as its normal logged-in user:

```bash
fetian-session-audit --expected live --session sway > live-sway.json
fetian-session-audit --expected live --session hyprland > live-hyprland.json
# In a separate text-recovery boot:
fetian-session-audit --expected live --session text > live-recovery.json
```

This read-only collector reports account/environment separation, real service
states, compositor IPC, metrics, network state, audio graph and disk detection.
It never treats those observations as physical audio, hardware or installation
acceptance. Transfer the JSON files out manually after reviewing diagnostic data.

Record the UEFI menu, normal and recovery entries, live account, login/logout,
Sway/Hyprland selection, lock/unlock, failed compositor recovery, networking,
clipboard/capture, volume access, audible playback, reboot and clean shutdown.
Mark emulated devices as emulated. There is no battery simulation configured.

Installation remains disabled. After a separately authorized installation has
been implemented and performed only on that disposable qcow2, verify its target
root and reboot it without the ISO:

```bash
python3 scripts/verify-installed.py --root /MOUNTED/DISPOSABLE/TARGET --username YOURUSER
python3 scripts/vm-test.py --resume-installed "$PWD/work/vm/uefi-RUN" --display gtk --seconds 900
# In the installed guest after real reboot:
fetian-session-audit --expected installed --session sway > installed-sway.json
```

The resume path accepts only provenance-marked direct children of `work/vm`,
owned regular qcow2 files and no backing image. It creates an `installed-*` log
directory, preserves prior evidence and does not attach an ISO. It does not
perform installation. Static installed-root checks cannot replace password,
sudo, initramfs, bootloader and persistent-state tests after reboot.

The older `make test` / `make test-live-account` serial-only probes remain for
compatibility. Prefer the new runner for paired writable OVMF variables,
disposable disks and separate evidence bundles.
