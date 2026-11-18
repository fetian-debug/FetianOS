# Desktop migration security

The original [security policy](../SECURITY.md) and Rust service sandbox remain
unchanged. No compositor process or metrics view receives root access. The
Hyprland session explicitly refuses root. No cloud provider or telemetry upload
is enabled.

Package versions and hashes are recorded from the inspected Manjaro index.
Research downloads are not a substitute for package signature authentication.
Candidate builds use the configured Manjaro keyring and preserve required
package signatures. Their sync database/cache live in the build workspace;
the host's installed package database is not refreshed or upgraded. A mismatch
fails the candidate instead of following a moving development branch.

The shell uses an unprivileged user unit. Child cleanup is confined to its own
process groups and systemd cgroup, with no broad `pkill` or root shell dispatch.
Compositor IPC uses an argument vector; workspace IDs/window addresses are
validated before forming a Lua selector. Firmware strings in widget tooltips
are escaped. The user's effects file is data, never sourced shell code.

No native plugins are enabled. Source review, license review, exact ABI pins and
load/unload/recovery testing are mandatory before adding compositor code.
The observed repository compositor is older than latest upstream; no production
security-support claim is made. Reassess supported upstream fixes before release.

Both staged images now use guarded live-only provisioning. The public disposable
guest credential is `fetian`/`fetian`; root is locked, sudo authenticates, and only
the first live Sway login is automatic. Existing accounts/homes are not reset.
The helper is inert on installed systems. See [boot/login policy](boot-login.md).
Installer account/credential cleanup remains a release blocker. Portals, capture
consent, Polkit prompts, lock/unlock and suspend ordering need real-session tests.

Before redistribution, retain package licenses and meet corresponding-source
obligations for copyleft software. The direct-package license inventory in
`THIRD_PARTY_NOTICES` is not a completed distribution-wide legal audit.

The application/build milestone adds nonprivileged FetianFiles jobs and bounded
archive/raster worker processes, disabled-installer image policy and read-only
installed-target checks. Workers have resource limits, not full filesystem or
network sandboxing. Target checks do not establish password authentication,
sudo syntax, bootloader execution or installed reboot. See the exact boundaries
in [FetianFiles](fetian-files.md), [installer preparation](installer-architecture.md)
and [verification evidence](verification-2026-11-18.md).
