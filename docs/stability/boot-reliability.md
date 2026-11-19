# Boot and recovery reliability

`profile/sway/profiledef.sh` selects only `uefi.systemd-boot`. The loader entries
reference vmlinuz-fetian/initramfs-fetian.img and carry Archiso media parameters.
The second entry selects systemd multi-user.target. GRUB's presence in the package
list does not establish a configured legacy BIOS boot path.

The image-only ALPM/customization helpers inspect installed kernel files, build
the live initramfs, reject incomplete artifacts and remove their build markers.
Initramfs hooks include udev, microcode, modconf, archiso, block, filesystems and
keyboard; autodetect is deliberately absent for live media. Archiso handles root
mounting. The host's WSL kernel is not this image's kernel.

SDDM requires the guarded live-user preparation unit; that oneshot has a 60-second
timeout. Installed accounts are not reset. A partial account creation without its
ownership marker is rejected for manual recovery rather than overwritten. This
safe refusal can still prevent live graphical login; automatic destructive repair
is not introduced. Recovery remains the text entry and journal inspection.

STAB-003 closes fd 9 only in each compositor child. The parent session wrapper
retains the exclusive lock through cleanup. Fixture compositors previously saw
the descriptor and returned 42; both now return 0 without inheriting the lock.
This demonstrates descriptor ownership, not real compositor crash/relogin success.

STAB-005 cleans temporary state even when write/flush/fsync fails. A disposable
ENOSPC injection preserves the previous marker and leaves no temporary file.
Credentials, account guards, SDDM ordering and timeouts are unchanged.

The old preview's [UEFI evidence](../verification-2026-11-18-uefi.md) remains valid
only for its identified image. This branch has not been built into or booted as an
ISO locally: mkarchiso, Docker and QEMU are absent. No new boot acceptance claimed.
