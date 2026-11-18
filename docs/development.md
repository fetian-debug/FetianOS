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

### Hyprland development

`make dev-desktop` detects an active Hyprland instance and uses its source Waybar
configuration/styles and compositor reload command. The watcher also monitors
`desktop/hyprland`. The native GTK tools can run from source with:

```bash
make native
PATH="$PWD/target/release:$PATH" python3 desktop/hyprland/fetian_desktop.py monitor
PATH="$PWD/target/release:$PATH" python3 desktop/hyprland/fetian_desktop.py widget
make desktop-check
```

The workspace view needs a running pinned Hyprland session. GUI modes need
GTK4/PyGObject and a display. A source watcher cannot apply edits to a compositor
configuration still loaded from `/usr/share`: stage/install the candidate in a
disposable VM to test those changes. Do not replace a production login config.

On a candidate installation, use `systemctl --user restart fetian-shell.service`
to restart panels and notifications. Idle/lock and system health units remain
independent. Never use broad process-kill commands to refresh the shell.

### Existing services

Test a service without touching the installed system by running its executable directly, then validate the unit file separately:

```bash
systemd-analyze verify profile/sway/airootfs/etc/systemd/system/fetian-health.service
```

For a user service iteration, copy only the unit under development into `~/.config/systemd/user/`, run `systemctl --user daemon-reload`, and restart that user unit. Do not use `systemctl restart` on production system services during UI development.

## ISO boundary

Use `sudo make build` only when you want to produce a distributable ISO. Daily development should use `make dev` or `make dev-desktop` and should not require root.
