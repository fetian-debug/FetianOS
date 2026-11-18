#!/usr/bin/env python3
"""Read-only guest evidence; interactive actions and hardware require separate tests."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys


def is_live():
    mounts = [line.split() for line in Path("/proc/mounts").read_text().splitlines()]
    return ("archisobasedir=fetianos" in Path("/proc/cmdline").read_text().split()
            and any(len(row) >= 3 and row[1:3] == ["/", "overlay"] for row in mounts)
            and any(len(row) >= 3 and row[1] == "/run/archiso/bootmnt" for row in mounts))


def command(arguments):
    try:
        result = subprocess.run(arguments, text=True, capture_output=True, timeout=10, check=False)
        return {"available": True, "exit_code": result.returncode, "stdout": result.stdout[:12000], "stderr": result.stderr[:2000]}
    except (OSError, subprocess.SubprocessError) as error:
        return {"available": False, "error": str(error)}


def collect(expected, session):
    try: live = is_live()
    except OSError: live = False
    user = pwd.getpwuid(os.getuid()).pw_name
    services = {name: command(["systemctl", "is-active", name]) for name in ("NetworkManager.service", "sddm.service", "fetian-live-user.service", "fetian-health.timer")}
    compositor = command(["swaymsg", "-t", "get_version"]) if session == "sway" else command(["hyprctl", "-j", "version"]) if session == "hyprland" else None
    checks = {"expected_environment": live == (expected == "live"), "non_root_user": os.getuid() != 0,
              "account_separation": user == "fetian" if expected == "live" else user not in ("fetian", "live", "root"),
              "network_manager_active": services["NetworkManager.service"].get("exit_code") == 0,
              "metrics_timer_active": services["fetian-health.timer"].get("exit_code") == 0,
              "sway_recovery_available": Path("/usr/share/wayland-sessions/fetianos-sway.desktop").is_file()}
    if expected == "live": checks["live_provisioning_active"] = services["fetian-live-user.service"].get("exit_code") == 0
    if session != "text":
        checks["display_manager_active"] = services["sddm.service"].get("exit_code") == 0
        checks["compositor_ipc_responds"] = compositor.get("exit_code") == 0
    metrics = command(["fetian-health-rs", "--json"])
    try: checks["real_metrics_schema"] = metrics.get("exit_code") == 0 and json.loads(metrics["stdout"])["schema_version"] == 1
    except (ValueError, KeyError): checks["real_metrics_schema"] = False
    return {"schema_version": 1, "collected_utc": datetime.now(timezone.utc).isoformat(), "expected": expected, "session": session,
            "user": user, "live_guard_matched": live, "checks": checks, "observed_checks_passed": all(checks.values()),
            "services": services, "compositor": compositor, "metrics": metrics,
            "network": command(["nmcli", "-t", "-f", "STATE,CONNECTIVITY", "general"]),
            "disks": command(["lsblk", "--json", "--output", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS"]),
            "audio_graph": command(["wpctl", "status"]),
            "portals": command(["systemctl", "--user", "is-active", "xdg-desktop-portal.service"]),
            "not_tested": ["boot menu", "logout", "session switching", "lock/unlock", "reboot", "shutdown", "audio playback", "USB/MTP hardware", "battery hardware", "installation", "rollback"],
            "hardware_validated": False, "installation_validated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", choices=("live", "installed"), required=True)
    parser.add_argument("--session", choices=("sway", "hyprland", "text"), required=True)
    args = parser.parse_args(); result = collect(args.expected, args.session)
    print(json.dumps(result, indent=2)); sys.exit(0 if result["observed_checks_passed"] else 1)
