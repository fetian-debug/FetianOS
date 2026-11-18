# Known limitations

The current milestone is documented in [verification-2026-11-18.md](verification-2026-11-18.md).
FetianFiles remains a preview; see [its feature matrix](fetian-files.md).
No packages were removed. Actual image build, UEFI boot, target graphical login,
installation and installed reboot remain blocked/unverified here. Installer
configuration is inactive and target cleanup is not implemented.

- No ISO has been built, booted or installed as part of the Rust port until
  explicitly recorded with an image checksum and VM results.
- Both staged images now include guarded live-user provisioning, SDDM and Sway
  recovery; actual boot, login and lock behavior remain unverified in a VM.
  Calamares configuration and installed-user cleanup remain unfinished.
- An image-only hook now generates fixed kernel/initramfs names from the kernel
  package's files. EFI consistency and build-state checks gate publication, but
  no real image has yet been built with this hook.
- The compositor cohort has strict version/archive pins. Remaining distribution
  dependencies and build tools still need an immutable repository snapshot.
- The QEMU probe checks serial Linux userspace evidence, not GUI functionality.
- Rust telemetry requires Linux. Required `/proc` read errors fail visibly;
  missing optional hardware metrics are reported rather than fabricated.
- The Rust JSON interface is schema version 1, replacing the old shell schema.
- DynamicUser state-directory protections can restrict access to stored snapshots
  by other local users. Desktop consumers should use the unprivileged CLI until a
  separately authorized IPC contract exists. Do not put secrets in health data.
- The Control Center now performs hardware/network/update reads asynchronously
  and opens real device tools. Wallpaper/theme editors, display settings and
  hibernation remain incomplete; no graphical interaction result is claimed.
- Native compositor blur/shadow/animation is configured but has no GPU test.
  Physical Liquid Glass optics, live-thumbnail overview, workspace drag/drop,
  3D cube/perspective, AI providers, rollback and hardware certification remain
  incomplete. No plugins are shipped and Hyprland is not promoted to default.
