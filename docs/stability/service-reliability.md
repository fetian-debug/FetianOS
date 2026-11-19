# Service reliability and failure isolation

The mandatory startup path uses distribution systemd and SDDM. Rust health is a
short-lived sandboxed oneshot invoked by a timer, not an always-running daemon.
Its 10-second timeout, DynamicUser, empty capability set, private devices and
read-only protections are preserved. A snapshot error remains visible. CPU
sampling's existing 200 ms interval is measurement, not a startup dependency delay.

FCA remains a separate opt-in user broker with Restart=no. No normal target
requires it; see [FCA validation](fca-stability.md). Its frame/workload/population
bounds, bounded channel and database timeout remain unchanged. Source inspection
does not prove absence of deadlocks, leaked descriptors or slow memory growth.

STAB-006 adds StartLimitIntervalSec=120 and StartLimitBurst=3 to the Bluetooth
agent, Sway idle, Hyprland idle and Hyprland shell units. Their on-failure restart
policies and delays remain unchanged. Under the common 10s/5-start defaults,
delayed persistent failures can evade the default rate window. Explicit windows
now cover three immediate repeated failures and stop automatic retry storms.
This is a start-rate bound, not a lifetime retry limit; slow failures and manual
restarts are different. These semantics follow [systemd.unit](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html).

The regression checks each configuration and staged systemd-analyze verifies
syntax. A live systemd user manager's restart behavior was not exercised. No
existing service was disabled to make a check pass. Targets retain Wants rather
than Requires for optional components; the compositor is not made dependent on
the shell, monitoring or FCA.

On the actual desktop, inspect `systemctl --user status UNIT` and
`journalctl --user -u UNIT`. Resolve the reported cause, then explicitly run
`systemctl --user reset-failed UNIT` and `systemctl --user start UNIT`.
If idle locking fails, use manual lock and do not rely on unattended suspend
until the lock/idle path has been verified. No existing lock security check is
relaxed and no security-sensitive automatic repair is added.
