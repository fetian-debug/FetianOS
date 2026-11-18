# Architecture

The existing Manjaro/Archiso Sway profile remains the default image build. Its
`pacman.conf` selects signed Manjaro repositories. Retaining this foundation
preserves the desktop, package tooling, firmware selection, and development
workflow. Changing to Debian or KWin would be a separate migration, not a
prerequisite for introducing Rust. Repository snapshots are not pinned, so the
image build is repeatable in procedure, but not yet bit-for-bit reproducible.
Hyprland is now the intended primary desktop, implemented as an opt-in overlay
and candidate image target. Sway is retained until runtime acceptance passes.

## Repository audit (2026-11-17)

- Existing desktop: Sway, Waybar, Wofi, Foot, Mako, GTK4/libadwaita Control Center,
  Python Calendar, Bash package/power/hardware tools, PipeWire, NetworkManager.
- Existing image tooling: mkarchiso profile, UEFI systemd-boot entry, checksums,
  image inspection and a QEMU probe. No ISO or successful VM result was supplied.
- Development host: Windows with Ubuntu 22.04 WSL available. Rust was initially
  absent. WSL can validate Linux components, but is not the configured Manjaro
  image builder. This directory has no Git metadata.
- Reusable pieces: all existing desktop applications, theme, signed package
  selection, development watcher and image profile are retained.
- The candidate overlay supplies SDDM integration, explicit Hyprland/Sway session
  entries, compositor configuration, portals and independent user shell/idle/lock
  units. Shared boot integration now provisions the live guest under strict
  guards and generates explicit Archiso boot artifacts. Calamares configuration,
  real login and image boot remain acceptance blockers. See [boot/login](boot-login.md).
- Deferred systems: Liquid Glass shaders, a custom Rust shell, D-Bus hardware
  service, AI providers, recovery/rollback and an installation-tested image.

## Rust system layer

`system/fetian-system` is a Cargo workspace member with a reusable library and
`fetian-health-rs` executable. It uses only the Rust standard library and forbids
unsafe code. It reads Linux `/proc` and `/sys`; no subprocess, external service,
root access or network connection is needed for metric collection.

The first port replaces the Bash health collector with sampled CPU utilization,
memory, uptime, kernel, firmware identity, network byte counters, batteries and
thermal-zone temperatures. This is a real system tool, not an OS or compositor
replacement. Existing GTK applications remain Python; Linux and third-party
components retain their implementation languages. “Pure Rust” describes this
new first-party system component, not the entire Linux distribution.

`fetian-health` delegates to the Rust executable. The ISO build compiles and
stages it. A systemd timer invokes a sandboxed dynamic user every minute, writing
an atomic `/var/lib/fetian/health.json` snapshot. No persistent polling daemon is
needed. Required `/proc` failures produce a nonzero exit and preserve the previous
snapshot. Optional metrics are null or absent from sensor lists; consumers must
check the timestamp and `unavailable` fields.

## Boundaries

Linux/systemd own boot and recovery; the selected compositor owns window management; desktop
apps remain unprivileged. Future privileged operations should use existing
Polkit-authorized services. An AI provider must never become an unrestricted
root command executor. Native Rust UI migration proceeds one working component
at a time after boot and session integration are validated.

## Hyprland candidate

`desktop/hyprland` layers onto the retained profile in a fresh build directory.
No source-tree staging, installed user configuration or default-login overwrite
occurs. The candidate pins Hyprland 0.56.2-4 and its integration cohort; it is not
runtime tested. The original Rust crate and system unit/timer are unchanged.
The shell reuses the existing Python/GTK and Waybar stack rather than adding a
second UI framework. Desktop metrics use the backend's read-only CLI because
DynamicUser snapshots are not generally readable by desktop users.

The controller uses public Hyprland JSON/Lua IPC. No compositor plugin, Wayfire
runtime, fake thumbnail pipeline or root desktop service is added. See
[integration](hyprland-integration.md), [materials](liquid-glass.md),
[spatial scope](wayfire-reference.md) and [candidate image build](iso-build.md).
