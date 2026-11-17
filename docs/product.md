# FetianOS Product Charter

FetianOS is a calm, capable, developer-focused Linux operating system. It makes supported hardware work automatically, exposes system state clearly, and provides safe recovery when something goes wrong.

## Product pillars

1. Works by default: drivers, firmware, audio, networking, displays, power, and input are detected automatically.
2. Understandable: the Control Center explains system state in plain language.
3. Comfortable: warm visual design, readable typography, night light, and low visual noise.
4. Powerful: developer tools, hardware acceleration, containers, diagnostics, and power profiles.
5. Recoverable: signed updates, health reports, logs, snapshots, and repair paths.
6. Maintainable: standard Linux interfaces, small services, reproducible builds, and release criteria.

## Version 0.1 scope

The developer preview provides Sway, a unified theme, Control Center, hardware reporting, a signed Manjaro kernel, firmware support, and eye-care defaults. It is not yet a hardware certification program or production recovery system.

## Version 1.0 criteria

- reproducible ISO build and automated validation;
- installer tested on real hardware;
- hardware inventory and driver status in Control Center;
- graphics, audio, Wi-Fi, Bluetooth, camera, touchpad, suspend, battery, and external-display tests;
- signed update flow with rollback documentation;
- recovery image or snapshot strategy;
- accessibility and eye-comfort review;
- supported-hardware list and security response process.

FetianOS will not silently install arbitrary vendor drivers, replace the host kernel, collect hardware telemetry by default, or hide failures behind generic success messages.
