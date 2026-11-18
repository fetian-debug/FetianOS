#!/usr/bin/env python3
"""Shared unprivileged desktop operations. System metrics stay in Rust."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def check_updates(run=subprocess.run):
    # checkupdates uses a separate temporary pacman DB; no root or package upgrade.
    result = run(["checkupdates"], text=True, capture_output=True, timeout=120, check=False)
    if result.returncode == 2:
        return "No updates available."
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Update check failed; check network connectivity and repository configuration.")
    packages = result.stdout.strip()
    return packages or "No updates available."


def battery_decision(batteries, previous):
    """Notify once per threshold; reset after charging or recovery above 20%."""
    next_state = {}
    alerts = []
    for battery in batteries or []:
        name = battery.get("name")
        capacity = battery.get("capacity_percent")
        status = battery.get("status")
        if not isinstance(name, str) or type(capacity) is not int or not 0 <= capacity <= 100:
            continue
        if status != "Discharging" or capacity > 20:
            continue
        threshold = 5 if capacity <= 5 else 15 if capacity <= 15 else 0
        old = previous.get(name, 0)
        if type(old) is not int or old not in (0, 5, 15): old = 0
        if threshold and (not old or threshold < old):
            alerts.append((name, capacity, "critical" if threshold == 5 else "normal"))
        next_state[name] = threshold or old
    return alerts, next_state


def battery_check(run=subprocess.run, runtime=None):
    result = run(["fetian-health-rs", "--json"], text=True, capture_output=True, timeout=5, check=True)
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported Rust metrics schema")
    if data.get("batteries") is None:
        return  # unavailable is not an empty battery or a zero reading
    directory = Path(runtime or os.environ["XDG_RUNTIME_DIR"]) / "fetian-battery"
    directory.mkdir(mode=0o700 if os.name == "posix" else 0o755, exist_ok=True)
    state = directory / "warnings.json"
    try:
        previous = json.loads(state.read_text())
        if not isinstance(previous, dict): previous = {}
    except (OSError, ValueError):
        previous = {}
    alerts, updated = battery_decision(data["batteries"], previous)
    for name, capacity, urgency in alerts:
        run(["notify-send", "--app-name=FetianOS Power", "--urgency=" + urgency, "--",
             "Battery low" if urgency == "normal" else "Battery critical",
             f"{name}: {capacity}% remaining. Connect external power."], check=True, timeout=5)
    with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as stream:
        json.dump(updated, stream)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, state)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check-updates", "battery-check"))
    args = parser.parse_args()
    try:
        if args.action == "check-updates": print(check_updates())
        else: battery_check()
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
