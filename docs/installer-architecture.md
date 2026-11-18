# Disabled installation preparation

Calamares is packaged, but no FETIANOS installer is enabled or installation-tested.
Image construction hides package-owned installer desktop IDs with same-ID XDG
shadows. It never removes the installer package or replaces user preferences.
No disk partitioning, formatting, mounting, cleanup or bootloader operation was
executed during this development milestone.

`installer/plan.json` describes the pages and ordered jobs. The `.conf.in` files
under `installer/calamares-preview` are inactive templates and are deliberately
not staged under `/etc/calamares`. No executable partition configuration or
installer entry point has been added.

The intended flow is welcome → locale/time zone → keyboard → explicitly
confirmed disposable disk/partition plan → normal user/password → summary →
partition/mount/unpack → identity/locale/fstab/user setup → fail-closed live
cleanup → normal initramfs → services/bootloader → security audit → unmount.
UEFI ESP/root layout and GRUB configuration still need target-version testing.

The upstream [Calamares users configuration](https://raw.githubusercontent.com/calamares/calamares/v3.3.14/src/modules/users/users.conf)
and [unpackfs configuration](https://raw.githubusercontent.com/calamares/calamares/v3.3.14/src/modules/unpackfs/unpackfs.conf)
were inspected. Templates select a locked root policy, passworded wheel sudo,
no initial autologin and a 12-character minimum. The copied squashfs source
matches this Archiso profile. Validate the actual packaged Calamares version,
module availability and password enforcement before using any template.
Initial autologin selection alone is insufficient: the final target audit
rejects any effective SDDM autologin configuration.

`cleanup-contract.json` specifies required target-only cleanup. Upstream
[removeuser](https://raw.githubusercontent.com/calamares/calamares/v3.3.14/src/modules/removeuser/removeuser.conf)
does not fail installation on cleanup errors, so it cannot be the only assurance.
Actual cleanup is not implemented: safely proving target/account provenance and
testing failure handling must precede any deletion job.

The installed system must lose the public live account/home, live sudoers,
provisioning service, runtime autologin and image hooks. Remove the SDDM live
drop-in and wrapper together: leaving the wrapper while removing its provisioning
module would break normal SDDM startup. Preserve the Rust metrics timer,
NetworkManager and Sway recovery. Generate normal initramfs without archiso
hooks and configure persistent UUID-based boot/mount entries.

`scripts/verify-installed.py` reads a mounted target and rejects missing
installer provenance, live/build state, live/extra UID-0 accounts, unlocked root,
missing normal-user password hash, missing wheel membership/passworded sudo,
writable sudo rules, autologin, live initramfs hooks, missing persistent root
mount/identity and missing boot/session files. It resolves target symlinks inside
the target. It never prints password hashes or changes accounts, files or disks.

Its result explicitly leaves sudo syntax, authentication, initramfs contents,
bootloader execution and installed reboot unverified. Hash shape checks do not
prove password strength. Run visudo in the real target, test the actual password,
sudo, lock/unlock and reboot without ISO before declaring installation acceptance.
The provenance marker is an installer contract, not proof that an installer ran.

Enabling installation requires explicit disk confirmation and a completed,
reviewed target-cleanup implementation, then successful disposable-VM install,
security checks, installed reboot, recovery and persistence tests. FETIANOS is
not ready for public installation. No rollback or automatic installation
recovery is claimed.
