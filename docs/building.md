# Building

Run `make inspect`, then install the missing host dependencies with the command printed by `make setup`. Build with `sudo make build`; the ISO is written to `output/`. `make validate` checks the checksum, ISO descriptor, and kernel/initramfs entries. `make test` performs a disposable QEMU boot probe when the ISO exists.

Use an x86_64 Manjaro/Archiso host. Run `make native-check native` first with
Rust (minimum 1.74), rustfmt, Clippy, and a C linker. Native code has no external
crate dependencies; Cargo runs locked and offline. The ISO builder also requires
`cargo`, `rustc` and `cc` in its root execution environment and builds/stages the
Rust health executable before invoking mkarchiso. Install the distribution Rust
package or configure that environment explicitly if using rustup as a user.

For the staged Hyprland migration use `sudo make build-hyprland`; see
[candidate image build](iso-build.md) for pin checks, sessions and remaining gates.
The Sway build target is preserved. Builds now stage into a fresh workspace
profile rather than modifying the source airootfs.

The UEFI-only image probe needs `edk2-ovmf` (or `OVMF_CODE` pointing to firmware).
It checks serial Linux userspace evidence. Graphical login and installation need
separate VM tests. Package snapshots, live-session acceptance and installer
configuration are still release blockers; see [known issues](known-issues.md).

Completed builds now publish a directory containing the ISO, SHA-256, package
inventory and source/tool metadata. The embedded squashfs is validated before
publication. Use `make environment`, `make application-audit` and
`make test-uefi` for capability, policy and disposable OVMF workflows. See
[image evidence and comparison commands](iso-build.md) and
[latest executed checks](verification-2026-11-18.md). Reproducibility is not yet
established by independent builds.
