# FetianOS developer preview

A Manjaro-compatible Wayland desktop with Rust system services, Sway recovery,
and an opt-in Hyprland session. Built in the open, with inspectable source,
checksums, package inventories and test evidence.

[Get preview downloads](downloads.md) · [Read the documentation](../docs/index.md) · [Build from source](../docs/iso-build.md)

## A coherent desktop

One primary application per task. Existing apps and Linux backends stay available
while their integrated replacements are developed and verified. FetianFiles
adds a native GTK file-management preview; Thunar remains the default.

## Real system information

The dependency-free Rust collector reads Linux system data and publishes atomic
snapshots. Missing sensors stay unavailable rather than turning into invented
readings. Existing services keep their privilege and sandbox boundaries.

## Recoverable by design

Sway remains available alongside the Hyprland candidate, with a separate text
recovery boot entry. The installer is disabled pending disposable installation
and installed-system reboot acceptance.

## Downloads that describe their evidence

The release pipeline checks source and image contents, then requires an actual
disposable OVMF serial/live-account boot probe. Each published preview includes
SHA-256 checksums, build metadata, package inventory and boot evidence. This
does not attest graphical login, physical hardware or public-installation readiness.

[Explore the application strategy](../docs/application-strategy.md) · [See release gates](../docs/release-acceptance.md)
