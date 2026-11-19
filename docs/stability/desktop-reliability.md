# Desktop reliability

Sway remains the default image and a selectable recovery session in the Hyprland
overlay. Hyprland still refuses an incompatible pinned compositor version rather
than guessing a configuration. Both session wrappers keep existing user config,
session exclusivity, child cleanup, environment import/removal and portal handling.
STAB-003 prevents inheriting the wrapper-owned flock into compositors/applications.

STAB-004 isolates optional shell children. A missing or exited network applet,
notification daemon, authentication agent or background client logs an explicit
error while the required Waybar panel continues. Exited children are reaped and
removed from the monitored set. They are not silently reported as healthy or
retried indefinitely. After resolving their cause, restart fetian-shell.service
to launch the group again. Authentication-agent failure does not grant privileges;
graphical authentication may be unavailable until recovery.

A missing/exited required panel remains a visible shell failure, eligible for
the bounded systemd restart policy. The compositor, workspace navigator, metrics,
lock service and Sway recovery are not stopped by this policy. Unit tests inject
child startup/exit failures; these are child mocks, not a real Wayland crash test.

The GTK smoke exercises existing file workflows on Xvfb with disposable HOME,
XDG directories and D-Bus. Its first baseline run timed out during image preview;
that result is retained and must not be hidden by a later pass. It is not proof
of a deterministic product defect or of a healthy real Wayland session.

Graphical sign-in, portal use, lock/unlock, logout/restart, monitor hotplug,
resolution changes, compositor crash recovery and suspend/resume still require
the built guest and hardware. No successful daily-use desktop acceptance follows
from static session/configuration checks.
