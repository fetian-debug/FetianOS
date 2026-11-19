# Hardware compatibility status

No physical device support is newly certified by this branch. Package presence
and Linux module availability are not device-test results.

| Area | Source integration | This branch's physical verification |
|---|---|---|
| Intel/AMD GPU | Mesa, Vulkan packages and distribution kernel drivers | Untested |
| NVIDIA | No new proprietary-driver integration or claim | Untested |
| Wi-Fi/Ethernet | NetworkManager, linux-firmware, distribution drivers | Untested |
| Audio | PipeWire, pipewire-pulse, WirePlumber, pavucontrol | Untested |
| USB/MTP/storage | Kernel/firmware, udisks2, GVfs/MTP, filesystem tools | Untested |
| ACPI/power | power-profiles-daemon, brightnessctl, Rust battery reporting | Untested |
| Suspend/resume | Existing idle/lock integration | Untested; must verify actual lock readiness |
| Multi-monitor/resolution | Existing compositor configuration/query paths | Untested |

The laptop described in README is a validation target, not evidence that this
mission tested its devices. WSL telemetry/fixtures do not substitute for graphics,
network, battery, audio, thermal, suspend or removable-media tests. Hardware faults
are not inferred from unavailable virtual devices. Kernel configuration/module
loading and Secure Boot must be checked in the actual built guest and target PC.
