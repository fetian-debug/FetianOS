# Building desktop image candidates

For automatic builds and actual published downloads, see
[CI/CD](ci-cd.md) and [the download page](https://fetian-debug.github.io/FetianOS/downloads.html).
Each published build carries its own source/package/VM evidence.

Use a disposable x86_64 **Manjaro** host with a populated Manjaro signing keyring.
Ubuntu WSL was used for source/Rust validation, not for building this image.

```bash
make setup
make native-check native profile-check
sudo make build-hyprland
make validate
make test
```

`sudo make build` retains the Sway image. The Hyprland target opts into the
experimental overlay and produces a distinct `fetianOS-hyprland-candidate` ISO.
No installed session preference is changed. The source tree is never used as
mutable staging: each build gets a fresh `work/build-…/profile` directory.

For Hyprland, the builder syncs repositories into an isolated pacman database,
checks pinned metadata, downloads the compositor cohort into a dedicated cache,
verifies archive SHA-256 values and preserves normal package signature checks.
After mkarchiso it verifies installed package versions before publishing a
complete bundle under `output/`. A changing
mirror causes a visible failure; explicitly update/retest the lock or use a
matching signed snapshot. Do not downgrade individual host libraries to match it.

The other distribution packages remain on moving mirrors. Full reproducibility
requires freezing the entire dependency closure and build tools, not just these
compositor archives. The unsigned metadata observed during research is not
treated as production signature-verification evidence.

For source staging without an image build:

```bash
make native
python3 scripts/stage-profile.py --desktop hyprland /tmp/fetian-profile-review
```

The destination must not exist. Review session entries, systemd units, portals,
package list and application payloads before building. This does not start a
compositor or modify the running system.
Project and third-party notices are staged under `/usr/share/licenses/fetianos`;
installed packages retain their own upstream license payloads.

Both staged images now enable SDDM and live-only user provisioning. The candidate
includes both compositor sessions. An image-only hook creates fixed EFI boot
artifacts, and validation checks their references and essential executables.
Actual boot/login and distribution-specific Calamares configuration/cleanup
remain unfinished. A package build is not acceptance of a bootable
or installable ISO. UEFI VM tests must cover login with an actual account,
graphics, applications, network, audio, clipboard/capture, portals, Rust service,
lock/unlock, restart/shutdown, and installation onto a disposable virtual disk
followed by an installed-system boot. Never test partitioning against host disks.

Run `make test-live-account` after building to require the real provisioning
service's serial readiness marker as well as Linux userspace evidence. This
still does not establish that graphical login or unlocking works. See
[boot/login](boot-login.md) and [daily usability](daily-usability.md).

## Build evidence and publication gates

`scripts/build-environment.py` reports actual tool/firmware/KVM availability.
`make setup` only checks dependencies and prints a setup command; it does not
install packages. Use a disposable Manjaro host with space for staging, the ISO
and a second extracted root filesystem.

The builder creates a unique work directory and exports `SOURCE_DATE_EPOCH`.
For two comparison builds, explicitly use the same chosen epoch and signed
repository snapshot. Most packages still resolve from moving mirrors; a fixed
epoch and compositor lock do not make the whole distribution reproducible.

The publication validator checks loader references, x86_64 PE EFI fallback,
squashfs presence, executable modes, MIME handlers, session executables,
essential service links, package-license metadata, project notices, locked
image accounts, absence of live credentials/build markers, machine identity,
SSH host keys, application policy and disabled-installer launchers. It extracts
the actual embedded squashfs and checks it independently of the staging tree.
Package inventories must match. Any failure prevents publication.

Each complete `output/<image>-<build-id>/` contains the ISO, relative SHA-256
sidecar, build.json and packages.json. Metadata records source/profile file
fingerprints, symlinks, tool versions, installed package versions/licenses,
epoch, desktop variant and separate validation flags. A private `.candidate-*`
directory is renamed only after the entire bundle is written. Selectors ignore
incomplete/hidden bundles. No VM, graphical, hardware, installation or
reproducibility success is inferred from static checks.

```bash
sudo env SOURCE_DATE_EPOCH=1794950400 make build
# Independently rebuild from the same frozen inputs, then:
python3 scripts/release-artifacts.py compare output/FIRST/build.json output/SECOND/build.json
```

Comparison verifies actual artifact bytes against each record and reports input
differences and byte identity. It requires distinct build IDs and independent-
execution attestation. No real independent ISO builds have been compared here.
See [VM workflow](vm-testing.md), [installer architecture](installer-architecture.md)
and [release acceptance](release-acceptance.md).
