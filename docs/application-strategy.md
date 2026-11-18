# One primary application per task

This is a source inventory and migration policy, not an inventory of a booted
image. `manifests/applications.json` selects the primary for each task.
`application-inventory.json` records every declared base package, first-party
desktop entry and system MIME default, plus the pinned opt-in Hyprland cohort
and optional post-install AI runtime plans. Regenerate it with:

```bash
python3 scripts/application-audit.py > docs/application-inventory.json
```

No packages were removed. No replacement has passed image/device acceptance.
The existing Thunar, Xarchiver, imv and media tools remain available. FetianFiles
is a hidden, explicitly launched preview (`fetian-files`), with no directory or
archive MIME takeover. Existing user MIME preferences are never rewritten.

| Task | Primary and package | Dependencies / delegated functionality | Duplication and proposed replacement | Removal decision and risk |
|---|---|---|---|---|
| Files / directory opening | Thunar (`thunar`) | GVfs, MTP backend, UDisks, thunar-volman, Tumbler | FetianFiles preview overlaps; remote/device coverage incomplete | Retain: data transfer and device regressions |
| Archives | Thunar integration | thunar-archive-plugin, Xarchiver, tar, zip, unzip | FetianFiles integrates ZIP/TAR/GZIP/XZ; no 7z | Retain: remaining formats and external integrations |
| Images | imv | Distribution image libraries | Bounded FetianFiles raster preview is a partial viewer | Retain: full viewing, large images and formats |
| Audio and video | mpv | Distribution codecs / PipeWire | One player handles both; no extra player added | Retain: playback not replaced |
| Web / PDF | Firefox | Distribution browser libraries | A single browser also handles PDFs | Retain: no PDF parser added to file manager |
| Terminal | Foot | Wayland | Alacritty is an existing optional alternative | Retain optional package until Foot image acceptance |
| System metrics | Control Center / Fetian health | `fetian-health-rs`, safe Rust system library | btop/htop are optional troubleshooting tools; Sway panel clicks now open Control Center | Retain: terminal recovery and diagnostics |
| Settings / appearance / power | Fetian Control Center | GTK4, libadwaita, python-gobject, polkit, power-profiles-daemon, brightnessctl, gammastep | Existing effects controls remain in desktop settings; no new standalone settings app | Retain system backends |
| Network | Control Center network page | NetworkManager, nm-connection-editor; nm-applet supplies tray integration | nmtui is a terminal recovery interface, not another default | Retain: Control Center delegates advanced configuration |
| Bluetooth | Control Center action | BlueZ, bluez-utils, Blueman | Blueman supplies the actual device UI | Retain: do not hide/remove a delegated dependency |
| Audio settings | Control Center action | PipeWire, pipewire-pulse, WirePlumber, pavucontrol | pavucontrol is the delegated mixer | Retain: routing and device functionality |
| Printing | Control Center action | CUPS, system-config-printer | Delegated printer UI | Retain: setup and driver workflows |
| Launcher | Wofi | Desktop entries; Fetian Apps opens package operations | Fetian Apps is software management, not a competing application launcher | Retain both roles |
| Notifications | Mako | libnotify / notify-send | No competing notification daemon added | Retain |
| Screenshots | fetian-screenshot | grim, slurp, wl-clipboard | Commands form one capture workflow | Retain all backends |
| Clipboard | Wayland clipboard | wl-clipboard; optional cliphist history | History complements the clipboard | Retain: no duplicate clipboard daemon introduced |
| Lock | Session-specific lock service | Swaylock for Sway; Hyprlock for opt-in Hyprland | Alternatives serve different compositor sessions | Retain: recovery compatibility |
| Panel / dock / workspaces | Waybar and existing shell | Compositor IPC | Dock and workspace controls are shell functions | Retain: candidate session needs VM checks |
| Updates / packages | Fetian Apps / Control Center | pacman, pacman-contrib, terminal, polkit | Read-only checking is separate from interactive installation | Retain package infrastructure |
| Calendar | Fetian Calendar | GTK4 / python-gobject | One primary | Retain |
| Text | Vim in Foot | `vim`, `foot`; hidden MIME desktop entry | No editor package added | Retain; native graphical editor remains future work |
| Disk administration | GParted | polkit, filesystem utilities | Administrative utility, not a file-manager duplicate | Retain; never started by automated tests |
| Graphical login | SDDM | Existing system display-manager unit / live-only wrapper | Login infrastructure, not another desktop shell | Retain; real login remains unverified |
| Installation | Calamares, disabled in launcher | Packaging retained; configuration not enabled | Same-ID XDG shadows hide actual installer launchers during image construction | Retain package; enabling requires disposable installation acceptance |

GTK libraries, codecs, firmware, portals, polkit agents, filesystem tools and
services are dependencies, not duplicate applications. Node/npm, Python tooling,
Docker and base-devel are existing developer tools; slimming that toolset is a
separate product decision. `networkmanager-qt` is a library, not another network
settings application. Exact transitive dependency and license metadata comes
from the actual image's pacman database, not assumptions made by this audit.

The image-only application hook applies the disabled-installer policy, records
hidden desktop IDs and an empty removal list, and removes its own build marker.
Failed policy work prevents publication. It does not delete package desktop
files, libraries, backends or user configuration.

Promotion of FetianFiles requires ordinary file workflows, permission/conflict
recovery, archives, MIME launching, real GVfs/SMB/MTP transfers and disconnects,
accessibility and performance checks in both compositor sessions. Only then
should system defaults change and redundant GUI exposure be reconsidered.
Current implementation/test boundaries are in [FetianFiles](fetian-files.md).
