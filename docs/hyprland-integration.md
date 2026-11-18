# Hyprland migration

Hyprland is the intended primary compositor. Sway remains the unchanged default
build and recovery choice until actual compositor, login, hardware and UEFI VM
tests pass. `manifests/hyprland.json` explicitly records `runtime_tested: false`
and `default_promoted: false`. No installed login preferences are overwritten.

## Version decision (2026-11-17)

The configured Manjaro stable extra index advertises **0.56.2-4**, whereas
[upstream releases](https://github.com/hyprwm/Hyprland/releases) advertise 0.57.2.
The candidate uses 0.56.2-4, upstream commit
`efb50993780079460b0cbed1363e2166a2de1d9f`. This is an observed repository-compatible
candidate, not a runtime-tested or production-approved release.

The manifest records package archive names, SHA-256 checksums, dependency
constraints and licenses for the compositor, its Hypr libraries, Lua, SDDM,
lock/idle tools and portals. The image builder rejects changed pins and checks
the installed candidate package versions before publishing an image checksum.
The remaining distribution dependency closure is not frozen. Reproducible release
builds still need an immutable, signed repository snapshot and recorded toolchain.

The version-specific API references are the
[0.56.2 example](https://github.com/hyprwm/Hyprland/blob/v0.56.2/example/hyprland.lua),
[Lua dispatchers](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsDispatchers.cpp)
and [layer rule definitions](https://github.com/hyprwm/Hyprland/blob/v0.56.2/src/config/lua/bindings/LuaBindingsConfigRules.cpp).
The spring field is `dampening` in this release. Do not substitute the newer
`damping` spelling or copy rolling-wiki options without updating/testing the pin.
The release notes were reviewed for fullscreen, rendering and screen-share fixes.

## Session architecture

The candidate image adds two selectable Wayland entries: **FETIANOS — Hyprland**
and **FETIANOS — Sway recovery**. Both staged images now enable SDDM with guarded
live-only account provisioning and one initial Sway autologin. Installed accounts
are not created/reset by the helper. See [boot/login policy](boot-login.md) for
public live credentials, root guards and the remaining Calamares lifecycle gate.

`fetian-hyprland-session` rejects root, nested compositor environments and a
package version mismatch. It uses the login's user D-Bus and runtime directory.
After Hyprland signals startup, `fetian-session-ready` imports the compositor
environment and starts `fetian-hyprland.target` and the portal frontend.

`fetian-shell.service` owns Waybar (status bar and dock), Mako, NetworkManager's
applet, the existing Polkit agent and Swaybg. Hypridle and Hyprlock have separate
user units so a shell restart does not kill an active lock client. Stopping/restarting this
user service does not stop Hyprland or the independent system health service.
Required child failures appear in the journal and trigger a bounded systemd
restart policy. Logout/crash cleanup stops the user target and Hyprland portal,
then clears compositor activation variables. One graphical session per user is
supported; simultaneous Sway/Hyprland sessions for the same UID are not supported.

The portal preference file routes screen capture to Hyprland and file dialogs to
GTK. Sway's portal configuration is retained. Clipboard and screenshots reuse
wl-clipboard, Grim and Slurp. Locking uses the pinned Hyprlock/Hypridle packages;
PAM authentication and suspend/lock ordering require real-session tests.

## Controls and profiles

| Control | Action |
|---|---|
| Super+Enter | Foot |
| Super+D / Super+Space | Wofi installed-application search |
| Super+comma | Existing Control Center |
| Super+Shift+A | Existing package tool |
| Super+E | Existing Thunar file manager |
| Super+Tab | Workspace/window navigator |
| Super+I | Real Rust system health |
| Super+V / Super+F | Toggle floating / fullscreen |
| Super+1…0 | Focus workspace 1…10 |
| Super+Shift+1…0 | Move active window to workspace |
| Super+arrows | Change window focus |
| Super+mouse drag | Move/resize |
| Super+L | Lock |
| Super+Shift+E | Confirmed session/power menu |
| Print / Super+Print | Region / full-screen capture to clipboard |

`fetian-desktop quick` exposes network, audio, power and four effects profiles.
`fetian-desktop effects accessible` writes only the user's Fetian profile choice,
reloads the compositor, and restarts the shell. Balanced/cinematic use blur and
shadows; performance/accessible disable compositor animation and blur and use
solid panel styles. Accessibility adds larger text and stronger focus borders.
No frame-rate or battery-life target has been measured yet.

The dock launches real applications. Workspace navigation uses current Hyprland
JSON IPC and validated numeric IDs/window addresses. It is a text navigator,
not a live-thumbnail overview; drag/drop, favorites editing, window grouping and
auto-hide are not implemented. There is no configured AI provider or AI panel.

Metrics are sampled by the unchanged `fetian-health-rs --json` read-only interface.
The widget and monitor show genuine data and explicitly unavailable sensors;
network values are cumulative byte counters. The existing Control Center now
loads the same metrics asynchronously. It also dispatches logout to the active
compositor instead of always calling Sway.

## Plugin assessment

The official plugin registry maps the selected upstream commit to plugin commit
`7644cecdb947060682891a0db2a0cdc5c0b9e704`. The inspected upstream
`borders-plus-plus` entry point checks compositor/header hashes and installs native
window decorations. `hyprfocus` manipulates animation internals and uses
`#define private public`; its unload path must clear callbacks. Their repository
license is BSD-3-Clause. Inspection of current source is not an audit or a test
of the registry's older pinned commit.

No plugins are packaged, loaded or required. Adding one requires reviewing the
exact pinned source, building against the exact compositor package, testing
load/unload/crash recovery and preserving its license. Native gradient borders,
shadows and spring transitions provide the initial appearance without plugins.

## Recovery

Log out, then select **FETIANOS — Sway recovery** in SDDM. If graphics fail, switch
to a text VT, log in and inspect `journalctl --user -u fetian-shell.service` and
the display-manager logs. Stop `fetian-hyprland.target` if required; the system
metrics timer remains separate. Rebuild with `sudo make build` for the retained
Sway image. No default promotion is performed by these source changes.
