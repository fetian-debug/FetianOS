# System health audit

Baseline: `06aa67fc4a1ee25d37211c288d0fa0630c9b44dc` (existing FCA Phase 2).
Branch: `stabilization/system-reliability`. Research commits are kept on their
own branches; this mission introduces no research architecture.

The tracked-file inventory is [retained](evidence/baseline/repository-files.json).
The audit followed the build entry points, staged profiles, boot helpers,
system/user units, both Rust crates, desktop wrappers/shell, application helpers,
file/archive operations, FCA persistence/IPC/resource code, tests and CI workflows.
This is a source/integration audit, not a proof that every line or every possible
execution is correct. Third-party packages are not vendored OS implementations.

| Component | Actual implementation and boundary |
|---|---|
| Kernel | Manjaro `linux72` package; version in `manifests/kernels.json` is recorded metadata, not a newly tested kernel |
| Boot | Archiso 91, UEFI systemd-boot; fixed kernel/initramfs names; SquashFS live root with Archiso overlay |
| Init | Distribution systemd; not a custom Rust init or kernel |
| Login | SDDM; live-only provisioning requires kernel command line, root overlay and boot-media mount |
| Recovery | UEFI text entry into multi-user.target; Sway session retained in both profiles |
| Desktop | Sway default; pinned Hyprland candidate overlay; existing GTK shell/dock and workspace UI |
| Integration | XDG portals, PipeWire sockets/WirePlumber, NetworkManager, Bluetooth, lock/idle units |
| Rust | Dependency-free fetian-system telemetry; independent opt-in fetian-fca broker/executors |
| Applications | Control Center, Apps, Calendar, Files preview and retained distribution applications; Thunar remains primary |
| Installer | Calamares present but launchers disabled; installation/cleanup not accepted |
| ISO | scripts/stage-profile.py → disposable Manjaro/mkarchiso → artifact/boot checks → explicit release workflow |

Default image staging excludes FCA. Its user unit has no Install target and no
normal startup dependency. No package, app, security restriction or configuration
format was removed. No service was installed or enabled on the development host.

See [baseline](performance-baseline.md), [defects](defects.json),
[acceptance matrix](stability-matrix.md) and [final report](final-stability-report.md).
The user's confirmed HP target has a separate [live-USB plan](hp-15-bs-live-test.md);
it does not enable the disabled installer or assign VM results to physical devices.
