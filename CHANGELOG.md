# Changelog

## 2026-11-18 — Experimental Continuation Authority architecture

- Added an independent opt-in Rust broker, CLI, gated launcher and Rust/Python
  semantic executors, with SQLite WAL/FULL transactions and managed capabilities.
- Implemented durable epoch fencing, idempotent effects, checkpoint recovery,
  explicit lifecycle management, verified unsigned audit chains and safe export.
- Proved real Rust SIGKILL followed by Python continuation of the same authority;
  tested broker crash windows and restart without duplicate managed effects.
- Added delegated-cgroup admission with truthful advisory/unavailable reporting
  and strict rejection before execution where kernel enforcement is absent.
- Added isolated CI, manual-only packaging, specifications, primary-source prior
  art, real measurements and retained dependency license notices.
- Default desktop, Sway recovery, existing apps and telemetry stay independent;
  FCA is not included in default ISO payloads or enabled at login.

## CI/CD and downloads

- Connected the source snapshot to existing GitHub history without replacing it.
- Added Manjaro-container ISO builds, required disposable UEFI serial probes,
  evidence-bound release packaging and draft-first developer prereleases.
- Added checksummed large-ISO parts and a cross-platform assembly helper.
- Added GitHub Pages documentation and a download page listing actual releases.
- Preserved Sway defaults, opt-in Hyprland, existing applications and disabled installation.

## 2026-11-18 — Application and verification milestone

- Added one-primary-per-task policy and full declared-package/application audit.
- Added native FetianFiles preview with safe local jobs, GIO integration,
  bounded archives/previews, tabs, split view, search and appearance controls.
- Added guarded evidence bundles, embedded-image validation, byte comparison,
  disposable OVMF/QEMU tooling and guest evidence collection.
- Kept installation disabled; added inactive modular templates and read-only
  installed-root security checks. Kept Thunar, existing backends and Rust services.
- Added source/GTK CI workflow and expanded local regressions. Actual image,
  VM, installation, hardware and reproducibility acceptance remain outstanding.

## 0.1.0 — Developer Preview

- Initial Sway/Wayland profile.
- English and Arabic locale and keyboard support.
- Calamares package included; a validated installer configuration was not supplied.
- Initial build, validation, checksum and VM scripts; reproducibility unverified.
