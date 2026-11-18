#!/usr/bin/env python3
"""Own only session children; let systemd restart this process independently."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path("/usr/share/fetian/hyprland")


def main():
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        print("fetian-shell: a Hyprland session is required", file=sys.stderr)
        return 1
    spec = importlib.util.spec_from_file_location("fetian_desktop", "/usr/share/fetian-desktop/fetian_desktop.py")
    desktop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(desktop)
    solid = desktop.selected_profile() in ("accessible", "performance")
    style = ROOT / "waybar" / ("solid.css" if solid else "glass.css")
    commands = [
        ["waybar", "-c", str(ROOT / "waybar/config.json"), "-s", str(style)],
        ["mako"], ["nm-applet", "--indicator"],
        ["/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"],
        ["swaybg", "-c", "#090e1b"],
    ]
    children = []
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for command in commands:
            children.append(subprocess.Popen(command, start_new_session=True))
        while not stopping:
            # A failed required component is visible in the journal and restarts
            # the owned shell group, without touching the compositor or metrics.
            if any(child.poll() is not None for child in children):
                return 1
            time.sleep(1)
        return 0
    except OSError as error:
        print(f"fetian-shell: {error}", file=sys.stderr)
        return 1
    finally:
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        for child in children:
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    sys.exit(main())
