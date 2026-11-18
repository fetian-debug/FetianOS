#!/usr/bin/env python3
"""Native desktop glue. Metrics remain in the independent, unchanged Rust backend."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PROFILES = ("balanced", "cinematic", "performance", "accessible")
ROOT = Path("/usr/share/fetian/hyprland")


def run(command, timeout=4):
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=True).stdout


def health():
    data = json.loads(run(["fetian-health-rs", "--json"]))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported system health schema")
    return data


def health_text(data):
    memory = data["memory"]
    cpu = data.get("cpu_usage_percent")
    lines = [f"CPU: {cpu:.1f}%" if cpu is not None else "CPU: unavailable",
             f"Memory: {memory['used_bytes'] / 1048576:.0f} / {memory['total_bytes'] / 1048576:.0f} MiB",
             f"Uptime: {data['uptime_seconds'] / 3600:.1f} hours"]
    batteries = data.get("batteries")
    if batteries is None:
        lines.append("Battery: unavailable")
    elif not batteries:
        lines.append("Battery: none detected")
    else:
        for battery in batteries:
            capacity = battery.get("capacity_percent")
            lines.append(f"{battery['name']}: {capacity if capacity is not None else 'unavailable'}% ({battery.get('status') or 'unavailable'})")
    temperatures = data.get("temperatures") or []
    lines.extend(f"{t['sensor']}: {t['celsius']:.1f} °C" for t in temperatures)
    if not temperatures:
        lines.append("Temperature sensors: unavailable")
    if data.get("network") is None:
        lines.append("Network counters: unavailable")
    else:
        for network in data["network"]:
            lines.append(f"{network['interface']}: received {network['received_bytes'] / 1048576:.1f} MiB · sent {network['transmitted_bytes'] / 1048576:.1f} MiB (cumulative)")
    return "\n".join(lines)


def widget():
    try:
        data = health()
        cpu = data.get("cpu_usage_percent")
        memory = data["memory"]
        text = f"CPU {cpu:.0f}%" if cpu is not None else "CPU —"
        text += f" · RAM {100 * memory['used_bytes'] / memory['total_bytes']:.0f}%"
        return {"text": text, "tooltip": html.escape(health_text(data)), "class": "healthy"}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, ZeroDivisionError):
        return {"text": "METRICS —", "tooltip": "System health is unavailable", "class": "unavailable"}


def query(name):
    if name not in ("clients", "workspaces", "monitors", "configerrors"):
        raise ValueError("Unsupported query")
    return json.loads(run(["hyprctl", "-j", name]))


def workspace_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 2147483647:
        raise ValueError("Invalid workspace ID")
    return value


def focus_workspace(value):
    return run(["hyprctl", "dispatch", f"hl.dsp.focus({{ workspace = {workspace_id(value)} }})"])


def focus_window(address):
    if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
        raise ValueError("Invalid window address")
    return run(["hyprctl", "dispatch", f'hl.dsp.focus({{ window = "address:{address}" }})'])


def effects_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "fetian/effects"


def selected_profile():
    try:
        value = effects_path().read_text().strip()
        return value if value in PROFILES else "balanced"
    except OSError:
        return "balanced"


def set_profile(value):
    if value not in PROFILES:
        raise ValueError("Unknown effects profile")
    path = effects_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Do not execute or source any user-provided text.
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        temporary.write(value + "\n")
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    run(["hyprctl", "reload"])
    run(["systemctl", "--user", "restart", "fetian-shell.service"])


def show_window(mode):
    # Reuse the existing GTK stack; no browser or new GUI dependency.
    import threading
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gio, GLib, Gtk, Gdk

    app = Gtk.Application(application_id="online.fetian.Desktop", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def activate(application):
        window = Gtk.ApplicationWindow(application=application, title="FetianOS " + mode.title())
        window.set_default_size(680, 520)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for edge in ("top", "bottom", "start", "end"):
            getattr(box, "set_margin_" + edge)(24)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(box)
        window.set_child(scroll)
        heading = Gtk.Label(label={"monitor": "System health", "workspaces": "Your workspaces", "power": "Session and power", "quick": "Quick settings"}[mode], xalign=0)
        heading.add_css_class("title-1")
        box.append(heading)
        status = Gtk.Label(label="", xalign=0, wrap=True, selectable=True)
        box.append(status)

        def background(work, done):
            def execute():
                try:
                    result, error = work(), None
                except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
                    result, error = None, str(exc)
                def finish():
                    if window.get_visible():
                        if error:
                            status.set_text("Unavailable: " + error)
                        else:
                            done(result)
                    return False
                GLib.idle_add(finish)
            threading.Thread(target=execute, daemon=True).start()

        def action(label, command):
            button = Gtk.Button(label=label)
            def clicked(_):
                background(lambda: subprocess.Popen(command), lambda _: status.set_text("Application opened"))
            button.connect("clicked", clicked)
            box.append(button)

        if mode == "monitor":
            def refresh(*_):
                background(lambda: health_text(health()), status.set_text)
            refresh_button = Gtk.Button(label="Refresh")
            refresh_button.connect("clicked", refresh)
            box.append(refresh_button)
            GLib.idle_add(refresh)
        elif mode == "workspaces":
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.append(content)
            def populate(data):
                workspaces, clients, monitors = data
                status.set_text(f"{len(monitors)} display(s) · Choose a window to focus it. Text list; live thumbnails are not available.")
                for workspace in sorted(workspaces, key=lambda w: w["id"]):
                    ident = workspace["id"]
                    if ident <= 0:
                        continue
                    button = Gtk.Button(label=f"{workspace.get('name', ident)} · {workspace.get('monitor', '')}")
                    button.connect("clicked", lambda _, n=ident: background(lambda: focus_workspace(n), lambda _: window.close()))
                    content.append(button)
                    for client in clients:
                        if client.get("workspace", {}).get("id") != ident:
                            continue
                        item = Gtk.Button(label="    " + (client.get("title") or client.get("class") or "Untitled window"))
                        item.connect("clicked", lambda _, a=client["address"]: background(lambda: focus_window(a), lambda _: window.close()))
                        content.append(item)
            GLib.idle_add(lambda: background(lambda: (query("workspaces"), query("clients"), query("monitors")), populate))
        elif mode == "quick":
            action("Network", ["nm-connection-editor"])
            action("Bluetooth", ["blueman-manager"])
            action("Audio", ["pavucontrol"])
            action("Printers", ["system-config-printer"])
            action("Files and removable drives", ["thunar"])
            action("Power profile", ["fetian-power-profile"])
            for profile in PROFILES:
                button = Gtk.Button(label=profile.title())
                button.connect("clicked", lambda _, p=profile: background(lambda: set_profile(p), lambda _: status.set_text(p.title() + " effects selected")))
                box.append(button)
        else:
            for label, command in (("Lock", ["systemctl", "--user", "start", "fetian-lock.service"]),
                                   ("Log out", ["hyprctl", "dispatch", "hl.dsp.exit()"]),
                                   ("Suspend", ["systemctl", "suspend"]), ("Restart", ["systemctl", "reboot"]),
                                   ("Shut down", ["systemctl", "poweroff"])):
                button = Gtk.Button(label=label)
                def confirm(_, label=label, command=command):
                    dialog = Gtk.MessageDialog(transient_for=window, modal=True, text=label + "?",
                                               secondary_text="Save your work before continuing.", buttons=Gtk.ButtonsType.OK_CANCEL)
                    def respond(dialog, response):
                        dialog.destroy()
                        if response == Gtk.ResponseType.OK:
                            background(lambda: run(command, timeout=30), lambda _: status.set_text("Action requested"))
                    dialog.connect("response", respond)
                    dialog.present()
                button.connect("clicked", confirm)
                box.append(button)
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", lambda _, key, _code, _state: window.close() if key == Gdk.KEY_Escape else False)
        window.add_controller(controller)
        window.present()

    app.connect("activate", activate)
    return app.run([])


def main():
    parser = argparse.ArgumentParser(description="FetianOS desktop tools")
    parser.add_argument("action", choices=("widget", "health", "monitor", "workspaces", "quick", "power", "effects"))
    parser.add_argument("profile", nargs="?", choices=PROFILES)
    args = parser.parse_args()
    try:
        if args.action == "widget":
            print(json.dumps(widget()))
        elif args.action == "health":
            print(json.dumps(health()))
        elif args.action == "effects":
            if args.profile is None:
                parser.error("effects requires a profile")
            set_profile(args.profile)
        else:
            return show_window(args.action)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"fetian-desktop: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
