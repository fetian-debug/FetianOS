# Fetian Control Center

The first FetianOS system settings application. It is intentionally small and uses existing Linux interfaces instead of maintaining a second system configuration database.

## Safety model

- Read-only status pages do not require privileges.
- Update operations are explicit and run through `pkexec`.
- Future privileged actions must be added as narrowly scoped helpers, validated before execution, and logged.

## Planned phases

1. Overview, Appearance, Network, Software, and System pages (current).
2. Real Sway/Waybar/theme editing with validation and rollback.
3. Hardware, audio, Bluetooth, users, storage, and services.
4. Recovery snapshots, diagnostics, and an authenticated helper service.
