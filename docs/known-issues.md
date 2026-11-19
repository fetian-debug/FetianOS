# Known limitations

The current milestone is documented in [verification-2026-11-18.md](verification-2026-11-18.md).
FetianFiles remains a preview; see [its feature matrix](fetian-files.md).
No packages were removed. Preview 7-1 has a recorded image build and UEFI
live-account boot; see [the identified release evidence](verification-2026-11-18-uefi.md).
Graphical sign-in, installation, installed reboot and physical-device acceptance
remain separate. The stabilization branch's own image/runtime gates are recorded
in [its report](stability/final-stability-report.md). Installer configuration is
inactive and target cleanup is not implemented.

- The published preview's checksum and UEFI evidence do not validate later source
  branches. No successful installation is recorded.
- Both staged images now include guarded live-user provisioning, SDDM and Sway
  recovery; the published preview has bounded serial/live-account boot evidence,
  while graphical login and lock behavior remain unverified.
  Calamares configuration and installed-user cleanup remain unfinished.
- An image-only hook now generates fixed kernel/initramfs names from the kernel
  package's files. EFI consistency and build-state checks gate publication, but
  the published preview passed these checks. Later changes need new image tests.
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
