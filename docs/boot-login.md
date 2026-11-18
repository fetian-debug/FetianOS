# Boot and login integration

Implemented on 2026-11-18; actual ISO boot and graphical login remain untested.
The existing Rust collector, snapshot schema and hardened system service/timer
are unchanged. Sway is the first live session; Hyprland remains an opt-in candidate.

## Image construction

The base package list now includes `mkinitcpio-archiso` and SDDM. An image-only
pacman hook selects the kernel image and module version from `pacman -Qql linux72`,
not the build host's `uname`. It explicitly generates an Archiso-capable
`initramfs-fetian.img` and `vmlinuz-fetian`. Module directories named
`extramodules-*` are not mistaken for installed kernel versions.

The hook removes itself, its build marker and the temporary live initramfs
configuration after success. The image pipeline rejects missing boot files,
unexpanded EFI placeholders, leftover build markers, non-executable essential
payloads, prematurely provisioned live state, and missing default-application
desktop entries before publishing an ISO checksum.

Archiso does not preserve copied executable modes. The staging script therefore
generates explicit `file_permissions` entries for every first-party command and
the display-manager wrapper. This includes the Rust binary.

The configuration was checked against the upstream
[Archiso builder](https://github.com/archlinux/archiso/blob/master/archiso/mkarchiso)
and [live initramfs example](https://github.com/archlinux/archiso/blob/master/configs/releng/airootfs/etc/mkinitcpio.conf.d/archiso.conf).
The actual Manjaro image build remains a required acceptance gate.

## Disposable live account

`fetian-live-user.service` runs before SDDM and the primary text/serial gettys.
The helper changes accounts only when all three conditions hold:

- the kernel command line contains exactly `archisobasedir=fetianos`;
- `/` is an overlay filesystem;
- the Archiso boot-media mount is present.

The live username and public live-media password are **`fetian` / `fetian`**.
This is a disposable guest credential, never an installed-user password. The
root account is locked. Sudo requires the guest password and its rule is checked
with visudo; there is no `NOPASSWD` rule. No SSH or Docker daemon is enabled.

The helper refuses to reset an unrecognized existing account or overwrite an
existing home. Private root-owned state in `/run/fetian` makes service retries
idempotent, while failed password/sudo preparation cannot enable autologin.
Persistent live roots with an existing guest account are deliberately refused
instead of resetting their credentials.

SDDM reads a generated runtime-only configuration for one initial Sway autologin.
Logging out returns to the greeter; choose **FETIANOS — Hyprland** or **FETIANOS —
Sway recovery** there. The integration follows
[SDDM 0.21 configuration](https://github.com/sddm/sddm/blob/v0.21.0/data/man/sddm.conf.rst.in).
On a non-live system the helper does nothing and SDDM uses its normal configuration.
No account database or permanent autologin password is embedded in the profile.

## Recovery and session boundaries

The UEFI menu has a text-recovery entry using `multi-user.target`; it does not
require SDDM, a compositor or the visual shell. Log in with the live guest
credentials, then inspect:

```bash
systemctl status fetian-live-user.service sddm.service
journalctl -b -u fetian-live-user.service -u sddm.service
```

The Sway session explicitly includes the Fetian configuration, while an existing
personal Sway config is preserved. Personal configs should run
`exec fetian-sway-ready` to start shared desktop services. Both managed sessions
use one lock file per user, stop their own user target on exit and preserve the
independent system metrics timer. Lock/idle units are separate from panel restarts.

## Tests and release gates

Fixture tests execute no account commands. They cover live guards, existing
account/home protection, retry behavior, malformed state, password/sudo failure,
changed login config, kernel selection, failed image generation and EFI checks.

```bash
make native-check native profile-check
sudo make build                 # disposable x86_64 Manjaro host
make validate
make test-live-account
```

The last command requires both Linux userspace output and the live service's
readiness marker in a UEFI VM. It is not a GUI login test. Keyboard/mouse,
SDDM selection, authentication, logout, suspend, lock/unlock and installed-system
boot still need interactive acceptance records.

Calamares remains unconfigured. Before installation is enabled, its distribution
configuration must remove/convert the disposable account, remove
`/etc/sudoers.d/90-fetian-live`, omit runtime state and generate a normal installed
initramfs/bootloader with the new user's credentials. Do not advertise this image
as installable until that cleanup and an installed-system reboot are tested.
