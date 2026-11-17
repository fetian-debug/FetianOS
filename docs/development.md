# FetianOS development workflow

The development workflow runs FetianOS components from the repository. It is intended for UI, applications, themes, Sway configuration, and desktop-service work. It does not rebuild the ISO, replace the installed system, or reboot the laptop.

## Start UI hot reload

From the repository:

```bash
make profile-check
make dev
```

The Control Center runs directly from `apps/fetian-control-center/`. Changes to its Python source or `theme.css` restart only the development Control Center. The installed copy is untouched.

## Start desktop hot reload

```bash
make dev-desktop
```

This additionally starts a repository-backed Waybar and reloads Sway after changes to Sway or desktop configuration. It owns only the processes started by the development session.

## What reloads

- Python application changes: Control Center restart
- GTK CSS changes: Control Center restart
- Waybar config/style changes: owned Waybar restart
- Sway configuration changes: `swaymsg reload`
- Wofi and Foot configuration: used by the next launch
- Hardware and health scripts: execute directly from the repository for testing

Install `inotify-tools` for immediate filesystem events. Without it, the workflow uses a one-second polling fallback.

## Service development

Test a service without touching the installed system by running its executable directly, then validate the unit file separately:

```bash
systemd-analyze verify profile/sway/airootfs/etc/systemd/system/fetian-health.service
```

For a user service iteration, copy only the unit under development into `~/.config/systemd/user/`, run `systemctl --user daemon-reload`, and restart that user unit. Do not use `systemctl restart` on production system services during UI development.

## ISO boundary

Use `sudo make build` only when you want to produce a distributable ISO. Daily development should use `make dev` or `make dev-desktop` and should not require root.
