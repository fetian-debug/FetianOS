# Rust and image testing

## Current application/build milestone

See [verification-2026-11-18.md](verification-2026-11-18.md): **97 Python tests,
6 Rust tests**, native GTK integration, release build, lint/format, launcher,
profile and staged systemd syntax checks passed. Actual ISO/VM/installation and
hardware acceptance remain outstanding. Earlier counts below describe previous
milestones. The new CI workflow was parsed but has not run on a hosted runner.

## Boot/login and daily usability validation: 2026-11-18

On Ubuntu 22.04 WSL with Rust 1.85.1, the complete check passed with **53 tests:
six Rust and forty-seven Python, with no Linux-suite skips**. Formatting, Clippy
with warnings denied, the offline locked release build, profile validation and
live Rust JSON checks also passed. Earlier Windows fixture checks were only a
partial fallback while WSL approval was pending; they are not the final result.

New tests cover live-root guards, existing-account/home protection, idempotent
provisioning, malformed state, changed login configuration, failed password/sudo
setup, kernel selection including extramodules, failed initramfs generation,
build-hook cleanup, EFI paths, image payload/default-app gates, update action
separation, attached terminals, battery thresholds/hysteresis and missing sensors.
Privileged commands are replaced by explicit fake runners inside temporary
fixtures; no real account creation/password/sudo operation occurred in these tests.

Both real Rust-binary profiles staged successfully into temporary directories.
`systemd-analyze --user verify` accepted eight Sway and twelve Hyprland user units
with ExecStart substituted by `/usr/bin/true` only in temporary validation copies.
The live root unit also passed static verification. The WSL host emitted unrelated
netplan/snapd warnings and permission warnings when inspecting a source unit on
the Windows mount. Actual image copying uses Archiso's normalized modes plus the
explicit executable permission map; the image payload gate checks the latter.

No user/root services were installed or started. No actual ISO build, QEMU boot,
SDDM authentication, graphical interaction, PAM unlock, device workflow or
installation was performed. Those remain acceptance gates on a disposable
Manjaro image host and UEFI VM, then recorded target hardware.
The available WSL host has no `mkarchiso`, QEMU or `isoinfo` executable. PyGObject
is present, but the GTK namespace is unavailable, so native GUI tests cannot run
there without additional host dependencies. None were installed for this change.

```bash
make native-check native profile-check
sudo make build                 # or build-hyprland, on Manjaro
make validate
make test-live-account
```

The live-account VM gate requires its real service marker; mocked tests of that
gate do not constitute a boot result. Follow [boot/login](boot-login.md) and
[daily workflow acceptance](daily-usability.md).

## Recorded validation: 2026-11-17

On Ubuntu 22.04 WSL x86_64, using an isolated Rust 1.85.1 toolchain:

- Release binary built successfully with locked, offline Cargo.
- `make native-check` passed formatting, Clippy with warnings denied, six Rust
  tests, four mocked-QEMU regression tests and live Linux JSON validation.
- The compatibility command, repeated atomic snapshot writes, invalid CLI
  arguments and invalid output paths were checked against the release binary.
- `systemd-analyze verify` accepted temporary copies of both units with ExecStart
  redirected to the workspace binary. It emitted unrelated host netplan/snapd
  warnings. No service was installed or started.
- Profile validation and Bash syntax checks passed.

No mkarchiso build, real QEMU boot, graphical desktop interaction, installation
or installed-service sandbox run was performed in this environment.

## Commands

### Hyprland migration evidence (2026-11-17)

Before migration, the original six Rust/four boot-probe tests, formatting,
Clippy, release build and live JSON check passed. After integration the same
checks pass with **six Rust and twenty Python tests (26 total)**. Python checks
cover staged source/service preservation, Sway retention, canonical application
payloads, package version/archive drift, installed-package rejection, IPC
selector validation, real/unavailable widget formatting, profile persistence,
mocked compositor crash cleanup, version-mismatch rejection, Lua profile
evaluation and source syntax.

The available Lua 5.1 library evaluated all four profiles with a public-API test
harness, checking reduced-effects overrides. This validates syntax/composition,
not Hyprland's runtime option acceptance. Exact option/API references were read
from the pinned 0.56.2 source. The manifest pins were checked against the
downloaded stable repository metadata, not an installed compositor.

The desktop adapter also successfully consumed live Rust JSON and produced its
Waybar widget payload. `systemd-analyze --user verify` accepted temporary copies
of all four user units (target, shell, idle, lock), with ExecStart
substituted by `/usr/bin/true` solely for syntax validation on WSL. No user unit
was installed or started, so lifecycle/PAM behavior remains unverified.

Still required on Manjaro/UEFI VM: candidate package/ISO build, real compositor
configuration parsing, GPU initialization, SDDM login/logout, fallback login,
GTK dialogs, app launch/focus/fullscreen, multi-monitor layouts, blur/shadows,
gestures, screenshots/clipboard, portal permission prompts, notifications, shell
restart, lock/unlock and suspend ordering, Rust service startup/restrictions,
network/audio, shutdown/restart, Calamares and installed-system boot. No such
graphical/image result is recorded yet. Follow [candidate ISO steps](iso-build.md)
and record image hashes, GPU/driver, package versions, logs and measured behavior.

On x86_64 Linux with Rust 1.74 or later, a C linker, rustfmt, Clippy, Python 3
and Bash:

```bash
make native-check
make native
PATH="$PWD/target/release:$PATH" bash apps/fetian-health/fetian-health --json
```

Cargo builds use `--locked --offline`; the current workspace has no third-party
crates. The build host needs standard Rust libraries and a C linker. Formatting,
Clippy and unit/integration tests cover CPU guest accounting and counter resets,
memory bounds/overflow, network columns, JSON string escaping, fixture-based Linux
collection, missing sensors, and atomic snapshot replacement/failure. The check
script also parses genuine live Linux JSON and checks numeric invariants.

For an isolated manual snapshot:

```bash
mkdir -p /tmp/fetian-health-test
target/release/fetian-health-rs --output /tmp/fetian-health-test/health.json
python3 -m json.tool /tmp/fetian-health-test/health.json
```

JSON schema version 1 includes `timestamp_unix_seconds`, nullable
`cpu_usage_percent`, `memory` (byte counts), nullable `network` (cumulative byte
counters, not throughput), nullable `batteries`, nullable `temperatures` and an
`unavailable` list. An empty battery array means no battery was discovered;
`null` means the power-supply directory was unreadable. Thermal-zone readings do
not guarantee a CPU-specific sensor. This replaces the old unversioned shell
JSON; Wi-Fi connection state and an ISO-8601 timestamp are not provided by v1.

On an installed development image, inspect the actual sandbox and refresh:

```bash
systemd-analyze verify /etc/systemd/system/fetian-health.service /etc/systemd/system/fetian-health.timer
systemctl status fetian-health.timer
sudo systemctl start fetian-health.service
journalctl -u fetian-health.service --no-pager
python3 -m json.tool /var/lib/fetian/health.json
```

Check the timestamp changes after a timer cycle. Confirm there is no root-owned
collector process and failure leaves the last complete JSON intact. DynamicUser
and device visibility must be verified in the target image; WSL execution alone
does not establish the service's installed behavior.

For image testing use `make profile-check`, `sudo make build`, `make validate`
and `make test` on the configured image host. The QEMU probe needs UEFI OVMF;
`OVMF_CODE=/path/to/OVMF_CODE.fd make test` overrides discovery. It requires serial
Linux userspace evidence and does not establish that the desktop or installer
works. Keep separate manual VM records for login, applications, networking,
power actions, Calamares disk confirmation and installed-system reboot.
