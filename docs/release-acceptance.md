# Release acceptance gates

Static source checks are a development gate, not a public-installation release.
All gates below need actual retained evidence before promotion:

| Gate | Required evidence | Current boundary |
|---|---|---|
| Source | Rust formatting/lint/tests/release, Python regressions, GTK checks, staged units and desktop entries | Executed locally; see dated verification report |
| Image | Real Manjaro build, signed package resolution, embedded-root validation, license inventory, checksum and metadata | Blocked here by host/tool availability |
| Repeatability | Independent records, fixed full dependency closure/toolchain and artifact comparison | Tooling unit-tested; real builds not compared |
| UEFI / recovery | Normal and text-recovery menu, userspace and live-account logs | Runner implemented; no actual boot here |
| Desktop | SDDM login/logout, Sway, optional Hyprland, portals, lock/unlock, failure recovery | Native file-manager UI tested; target desktops unverified |
| Daily use | Network, playback, clipboard/capture, storage, printing and device failures | Source/backend tests only where documented |
| File-manager promotion | Real local/remote workflows, SMB/MTP/USB, accessibility, performance, MIME integration in both sessions | Preview only; keep Thunar and existing viewers |
| Installation | Explicit disposable disk selection, fail-closed cleanup, successful install | Disabled; cleanup/bootloader work remains |
| Installed reboot | No ISO attached; password, sudo, no live state, normal initramfs, UUID mounts, persistence/recovery | Static validator only; no installation/reboot performed |
| Hardware | Identified physical devices/firmware, drivers/power/suspend/audio tests | No physical hardware validated |

Keep emulation, fake providers, source fixtures and physical hardware results
separate. Unit-tested comparisons are not reproducibility evidence. Serial logs
are not graphical acceptance. The new CI workflow performs source checks only
and has not been executed on a hosted runner during this session.

No file-manager replacement, redundant package removal, Hyprland promotion or
installer enablement should bypass its acceptance gate. There is no tested
automatic rollback implementation.
