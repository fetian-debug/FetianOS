# FetianOS

[Downloads](https://fetian-debug.github.io/FetianOS/downloads.html) ·
[Documentation](https://fetian-debug.github.io/FetianOS/docs/index.html) ·
[Build status](https://github.com/fetian-debug/FetianOS/actions/workflows/iso-release.yml) ·
[Releases](https://github.com/fetian-debug/FetianOS/releases)

Main-branch CI checks source, builds the Sway ISO in a disposable Manjaro
container and requires a real UEFI serial/live-account boot before publishing
developer-preview downloads. Hyprland builds are manually selected. Failed
builds retain diagnostics. The downloads page lists only published release
assets; the source ZIP is labeled separately. See [CI/CD](docs/ci-cd.md).

[Preview 7-1](https://github.com/fetian-debug/FetianOS/releases/tag/preview-7-1)
is the first published Sway ISO: image checks and actual UEFI/live-account boot
passed. Download both numbered parts and use the included verification/assembly
helper. Graphical sign-in, installation and hardware acceptance remain separate.

The opt-in [Continuation Authority prototype](docs/fca/README.md) now keeps a
durable workload identity, contract and transactional checkpoint across real
Rust-to-Python executor replacement. It is isolated from default boot and
desktop startup. Read the [measured validation report](docs/fca/validation-report.md)
for the handoff proof, resource availability and current limitations.

FetianOS is an independent, Manjaro-compatible Linux operating system for developers and power users. It combines a Sway/Wayland desktop, automatic hardware detection, a unified eye-friendly design system, safe system tools, and live development without rebuilding the ISO.

Authored for [fetian.online](https://fetian.online). Not affiliated with Manjaro or Arch Linux.

## Vision

FetianOS is designed to be automatic, understandable, comfortable, powerful, recoverable, and maintainable. Supported hardware should work without manual driver hunting; system state should be visible; privileged actions should be explicit; and the desktop should remain calm and readable.

## Current status

FetianOS is a developer preview. It currently includes Sway, Waybar, Wofi, Foot, Mako, PipeWire, NetworkManager, Bluetooth, Calamares, Fetian Control Center, hardware reporting, health reporting, Fetian Apps, Fetian Calendar, interactive power controls, eye-care defaults, and a source hot-reload workflow.

Do not use it on critical systems without backups. It is not yet a production-certified distribution.

### Boot/login and daily-use integration

The dedicated stabilization work records reproduced reliability fixes and
remaining acceptance gaps in [the stability report](docs/stability/final-stability-report.md).
It does not replace the published ISO or certify daily-use readiness. Boot,
graphical sessions, hardware and long-duration checks apply only when actually
completed for an identified build.

Both staged images now include guarded live-account provisioning, SDDM login,
Sway recovery and an explicit text-recovery boot entry. The image pipeline builds
Archiso initramfs artifacts and checks boot references, executable permissions
and default applications before publishing a checksum. Shared desktop services
wire audio, Bluetooth, user folders and real Rust-backed battery warnings.
Update checking is read-only; installation opens an interactive terminal.

The disposable live credential is **fetian / fetian**. It is created only on
recognized live media; existing installed accounts are not reset. Real ISO boot,
GUI/device tests and Calamares cleanup still need validation. See
[boot/login](docs/boot-login.md) and [daily usability](docs/daily-usability.md).

### Application policy and verification tooling

The repository now includes a one-primary-per-task application inventory,
FetianFiles GTK preview, guarded artifact bundles, a disposable OVMF/QEMU runner,
guest evidence collection and a read-only installed-root policy validator.
FetianFiles adds native file workflows and bounded previews/archives while
Thunar remains the default. Existing packages and Rust services are retained.
Calamares launchers are disabled during image construction; inactive installer
templates do not perform partitioning or installation.

See [application strategy](docs/application-strategy.md),
[FetianFiles](docs/fetian-files.md), [VM testing](docs/vm-testing.md),
[installer preparation](docs/installer-architecture.md),
[release gates](docs/release-acceptance.md) and
[latest verification](docs/verification-2026-11-18.md).

### Hyprland 2090 migration

Hyprland is the intended primary desktop. An opt-in candidate overlay now adds
a pinned compositor cohort, SDDM session entries, a real application dock,
workspace/window navigator, portal integration, Rust metrics views and four
effects profiles. Sway remains available and stays the default build until
graphical/hardware/VM acceptance passes. No plugins or simulated 3D previews
are shipped; physical glass optics and an installation-tested ISO remain pending.

```bash
make native-check native profile-check
sudo make build-hyprland  # on a disposable x86_64 Manjaro build host
```

See [Hyprland integration](docs/hyprland-integration.md),
[candidate ISO steps](docs/iso-build.md) and [actual test evidence](docs/testing.md).

### Rust system foundation

New first-party system code is written in safe Rust. The dependency-free
`fetian-system` library and `fetian-health-rs` command now collect real Linux CPU,
memory, uptime, network, battery and temperature metrics. `fetian-health` delegates
to that backend, and the image stages a sandboxed systemd health timer. Existing
Sway and GTK applications are retained; the whole distribution is not pure Rust.

```bash
make native-check
make native
PATH="$PWD/target/release:$PATH" fetian-health-rs --json
```

Use x86_64 Linux with Rust, a C linker, rustfmt and Clippy. See
[architecture and audit](docs/architecture.md), [test commands](docs/testing.md),
[milestones](docs/roadmap.md) and [known limitations](docs/known-issues.md).
The supplied live-session and installer setup still needs completion and VM
verification; this source update does not constitute a tested bootable ISO.

## Included experience

### Visual preview

These are FetianOS design previews showing the intended Control Center and application-search experience:

![Fetian Control Center preview](docs/images/control-center.svg)

![Fetian application launcher preview](docs/images/app-launcher.svg)

The live UI is available through `make dev-desktop`; these previews are kept in the repository so contributors can discuss the visual language without needing to build the ISO first.

- Sway/Wayland desktop with keyboard-first controls
- Warm dark Fetian design across GTK, Sway, Waybar, Wofi, and Foot
- Gammastep night light and reduced-glare defaults
- Waybar controls for apps, settings, power, CPU, RAM, disk, network, audio, battery, and calendar
- Wofi launcher with icons, fuzzy matching, descriptions, and keyboard search
- Fetian Control Center for overview, hardware, appearance, network, software, system, and power
- Fetian Apps commands such as `install chromium`, `uninstall firefox`, and `search browser`
- Fetian Hardware Report and Fetian Health in text and JSON formats
- Signed Manjaro repositories, Linux kernel, firmware, `fwupd`, sensors, and power profiles

## Keyboard controls

| Shortcut | Action |
|---|---|
| `Super + Enter` | Open terminal |
| `Super + D` / `Super + Space` | Search applications |
| `Super + ,` | Open Control Center |
| `Super + Shift + A` | Open Fetian Apps |
| `Super + Shift + N` | Warm night light action |
| `Super + Shift + C` | Reload Sway configuration |
| `Super + Shift + Q` | Close focused window |
| `Print` | Select screenshot |
| `Super + Print` | Full screenshot |

## Waybar controls

Click **APPS** for icon-based application search; right-click it for Fetian Apps. Click **SETTINGS** for Control Center. Click **POWER** to cycle balanced, performance, and power-saver profiles. CPU and RAM open `htop`; disk opens `btop`; network opens NetworkManager; volume opens audio controls; the clock opens Fetian Calendar; right-clicking the clock opens Control Center.

## Hardware support

FetianOS uses Linux kernel drivers, trusted firmware, and standard services instead of random driver installers. The validation laptop is an HP Laptop 15-bs0xx with Intel i5-7200U, Intel HD 620 (`i915`), AMD Radeon R5 M330/Radeon 520 (`radeon`), Intel AC 3168 Wi-Fi (`iwlwifi`), Realtek Ethernet (`r8169`), Intel/Realtek audio, Synaptics touchpad, UVC webcam support, ACPI battery, and HP WMI controls.

The profile includes `linux-firmware`, `hwdata`, `pciutils`, `usbutils`, `fwupd`, `lm_sensors`, `power-profiles-daemon`, and `udisks2`.

```bash
fetian-hardware-report
fetian-hardware-report --json
fetian-health
fetian-health --json
```

## Repository layout

```text
apps/       Control Center, desktop tools, hardware and health commands
docs/       Architecture, product, installation, development, troubleshooting
manifests/  Kernel and AI compatibility metadata
profile/    mkarchiso Sway profile and installed desktop files
scripts/    Build, validation, host inspection, and live development
```

## Build the ISO

The build uses signed Manjaro repositories and does not format disks or change the host bootloader.

```bash
cd /home/fty/fetianOS
make inspect
make setup
make profile-check
sudo make build
make validate
make test
```

ISO files and checksums go to `output/`; temporary build state is in `work/` and is ignored by Git.

## Live development

Daily UI and desktop development does not require an ISO build or reboot:

```bash
make profile-check
make dev
```

For Control Center, Waybar, Wofi, and Sway:

```bash
make dev-desktop
```

The watcher monitors `apps/`, `profile/sway/airootfs/etc/xdg/`, and `profile/sway/airootfs/etc/sway/`. Python/CSS changes restart the source Control Center; Waybar changes restart the development Waybar; Sway changes use `swaymsg reload`; Wofi and Foot changes apply on their next launch. Install `inotify-tools` for immediate events, otherwise one-second polling is used.

```bash
sudo pacman -S inotify-tools
```

Press `Ctrl+C` to stop. The installed system and ISO remain unchanged.

## Fetian Apps

Open with Waybar, Control Center, `Super + Shift + A`, or `fetian-apps`. Type:

```text
install chromium
uninstall firefox
remove vlc
search browser
```

Matching signed repository packages are shown, confirmation is required, and `pkexec` authenticates the transaction. If a package is unavailable, Fetian Apps reports that rather than using an untrusted source.

## Installation safety

Install only from a live ISO and verify the disk in Calamares. On the validation laptop, `/dev/sdb` contains the current system and `/dev/sda` is a separate 465 GB HGST disk. A full `/dev/sda` install would normally use `/dev/sda1` as `/boot/efi`, `/dev/sda2` as `/`, and `/dev/sda` as bootloader target. Formatting erases data; back up first and never select `/dev/sdb` accidentally.

## Security model

Read-only detection needs no privilege. Package, firmware, power, and destructive operations require authentication or confirmation. Sources must be signed. Hardware reports stay local unless the user shares them. Build artifacts, logs, caches, and reports are excluded from Git.

## Validation and contribution

```bash
make profile-check
```

This checks manifests, duplicate packages, required platform packages, and required source files. Use `make validate` for a built ISO. Contributions should use a feature branch, hot reload for testing, profile validation, documentation updates, and a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/development.md](docs/development.md).

## Roadmap

Next: a real `fetian-hardwared` D-Bus service, package descriptions and icons in Fetian Apps, richer audio/display/Bluetooth/network pages, automated hardware diagnostics, signed updates with rollback, snapshots, recovery tooling, supported-hardware certification, accessibility review, and reproducible release builds.

See [docs/product.md](docs/product.md) for the full product charter.

## License

FetianOS project files are MIT licensed. Third-party packages retain their upstream licenses.
