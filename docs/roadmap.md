# Development roadmap

## Implemented: first Rust system component

- Standard-library-only Rust telemetry library and executable.
- Linux CPU sampling, memory, uptime, network counters, battery, thermal data.
- Escaped, versioned JSON and atomic health snapshots.
- Restricted systemd oneshot service and timer wired into ISO staging.
- Native build, formatting, lint and test commands.
- UEFI-aware QEMU probe requiring Linux userspace evidence.

These source changes do not establish that an ISO boots or installs.
The Rust release build, six Rust tests, four probe regression tests, live Linux
telemetry and static systemd verification passed on Ubuntu 22.04 WSL with Rust
1.85.1. See [recorded validation](testing.md) for the limits of that evidence.

## Next: bootable foundation acceptance gate

The Hyprland source integration is now staged: candidate package pins, two session
entries, independent shell/idle/lock units, portal preferences, real dock and
launcher actions, a text workspace navigator, four effects profiles and Rust
metrics views. `sudo make build-hyprland` is opt-in. It does not promote the
default session. The original integration passed 26 tests; no graphical or image
acceptance has been claimed. See [integration](hyprland-integration.md).

1. Use a disposable x86_64 Manjaro/Archiso build machine; verify signed package
   availability, kernel selection and EFI kernel/initramfs paths.
2. Test the guarded live-user creation and SDDM with the new Hyprland session and
   retained Sway recovery entry. Validate config-fragment inclusion and portals.
3. Build an ISO; verify checksum and contents; boot it with UEFI in QEMU.
4. Validate real keyboard/mouse, network, audio, app launching and health timer.
5. Configure Calamares for this distribution and test installation exclusively
   on a disposable virtual disk, including reboot into the installed system.
6. Test hardware, screen capture consent, lock/unlock, suspend, accessibility,
   package updates and shell crash recovery before promoting Hyprland to default.

## Subsequent milestones

Port hardware discovery to Rust with a versioned IPC contract and genuine device
status. Migrate selected native UI components only with interaction parity.
Build GPU materials with measured performance and solid/reduced-motion fallbacks.
Then add provider-independent intelligence with explicit action permissions,
package/update integration, recovery, accessibility and hardware qualification.

No release milestone is complete without recorded build and integration evidence.

## Boot/login and daily usability source milestone (2026-11-18)

Added guarded live guest provisioning, SDDM startup in both images, an explicit
Sway entry/config, text recovery, image-only initramfs generation, executable
permissions and image validation gates. Shared user services now wire audio,
Bluetooth pairing, user folders and real battery warnings. Thunar integration,
media/archive defaults and printing packages are included. The Control Center
performs reads asynchronously and separates read-only update checking from
interactive installation. Existing Rust services and applications are retained.

See [boot/login](boot-login.md), [daily workflows](daily-usability.md) and
[current validation](testing.md). Actual Manjaro image generation, UEFI boot,
graphical workflows, installed-system cleanup and hardware qualification remain
the next acceptance gates. These source changes do not establish a usable ISO.
