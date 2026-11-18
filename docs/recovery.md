# Recovery boundaries

The existing UEFI text-recovery entry requests `multi-user.target`, keeping
graphics independent of the initial boot path. The live account service remains
guarded by this distribution's exact cmdline, overlay root and boot-media mount.
The public `fetian / fetian` credential belongs only to disposable live media.

If graphics fail, choose text recovery or switch to another virtual terminal.
Inspect `journalctl -b -u fetian-live-user.service -u sddm.service` and
`systemctl --failed`. If live provisioning failed, inspect the error before
attempting account repair; it deliberately refuses to overwrite unknown users
or homes. There is no fallback blank-password or passwordless-root login.

At graphical login select FetianOS Sway. Hyprland remains opt-in. If an optional
shell component fails, use the compositor's existing terminal/launcher bindings
and inspect user-unit logs. Validate configuration before restarting a session;
save work first. Sway is retained in both staged profiles.

Rebuild a damaged ISO from source after checking its SHA-256 and recorded inputs.
Do not edit boot artifacts blindly; static validation must pass again. UEFI
firmware variables are private copies in each disposable VM run, so a broken
test boot configuration can be isolated by starting a fresh run.

For a failed installation, retain the VM disk and logs and return to the live
ISO for diagnosis. No host disk repair command, automatic rollback, snapshot
restore or production reinstall flow has been implemented. Installed recovery
is an acceptance requirement, not an already tested capability. See
[VM testing](vm-testing.md) and [installer preparation](installer-architecture.md).
