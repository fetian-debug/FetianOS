# Daily usability milestone

The current changes prepare complete workflows; hardware and graphical behavior
are not certified by unit tests. Existing applications and the Rust system
component are preserved. No interface displays simulated hardware values.

| Workflow | Source integration | Acceptance still required |
|---|---|---|
| Boot/login | Live-only account provisioning, SDDM, explicit Sway entry, Hyprland selection, text recovery | Actual UEFI boot, keyboard/mouse, login/logout |
| Network | NetworkManager enabled; real connection status and editor | Saved Wi-Fi, reconnect, Ethernet, offline errors |
| Bluetooth | Blueman pairing agent and device manager; standard Bluetooth service | Pair/reconnect headphones and peripherals |
| Audio | PipeWire/Pulse sockets and WirePlumber enabled; Pavucontrol launcher | Speakers, headphones, microphone and device switching |
| Files | Existing Thunar plus GVfs, MTP, thumbnails and volume management | Copy/move/rename/trash/restore, USB permissions, phone access |
| Media/archives | mpv, imv, Xarchiver and Thunar archive plugin; system MIME defaults | Opening real files, codecs and archive errors |
| Printing | CUPS socket activation and printer configuration UI | Real local/network printer setup and printing |
| Battery/power | Rust-backed low/critical warnings, hysteresis, lock/idle services | Real battery changes, lid, suspend/resume, lock ordering |
| Updates | Read-only checkupdates; separate attached interactive installation terminal | Online/offline checks, Polkit/sudo prompts, interrupted upgrades |
| Diagnostics | Asynchronous hardware/network/service reads; safe report export and startup logs | Real GUI dialogs and hardware error states |
| Accessibility | Existing solid/reduced-motion profiles, visible focus, existing US/Arabic layouts | Screen reader, scaling, contrast and full keyboard review |

The package inventory and direct license notices were refreshed against the
repository metadata already inspected on 2026-11-17. Packages are installed only
when building the image; this work did not install them on the development host.

## Important behavior

- **Check for updates** cannot install packages or refresh the host's real pacman
  database. It uses [checkupdates](https://man.archlinux.org/man/checkupdates.8.en)
  and reports no-updates separately from network/repository failures.
- Installation opens a real terminal for `sudo pacman -Syu`; normal authentication
  and transaction confirmation remain attached. There is no `--noconfirm`.
- Hardware, network and update reads run off the GTK thread. Exports choose a
  fresh filename instead of silently overwriting an old report.
- Battery warnings use actual Rust JSON, notify once at 15% and escalate at 5%.
  Charging or recovery above 20% resets the warning; missing sensors produce no
  invented battery reading. The timer stops with the desktop session.
- Default file associations are system defaults only. Personal MIME preferences
  take precedence. The image checker rejects references to absent desktop files.
- Sway config reloads no longer repeatedly spawn the bar/notification daemon.
  Screenshot cancellation leaves the clipboard alone. Lock clients remain
  independent of restarting panels.
- Inert appearance buttons were removed. Unimplemented wallpaper/theme editing
  and hibernation are described as unavailable. A full display-settings UI,
  account management, backup/rollback and a notification-history center remain
  separate milestones.

## Real-session acceptance sequence

On a disposable VM first, then on recorded target hardware: boot, connect, create
a test folder, copy/move/rename/trash/restore files, open a PDF/image/video/archive,
play audio, record microphone audio, pair a device, capture the screen, share a
window through a portal, lock/unlock, suspend/resume, check updates and shut down.
Repeat critical steps after logout, a panel restart and a network disconnect.
Use disposable files and virtual disks for failure cases. Record package/image
versions, results and logs; do not mark a hardware workflow complete from mocks.
