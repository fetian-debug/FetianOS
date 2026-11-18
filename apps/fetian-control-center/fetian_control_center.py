#!/usr/bin/env python3
"""FetianOS Control Center: a safe, small control surface for the desktop."""
import os
import json
import platform
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk, Gdk


APP_ID = "online.fetian.ControlCenter"
THEME = os.environ.get("FETIAN_CONTROL_CENTER_THEME", "/usr/share/fetian-control-center/theme.css")


def run(command, timeout=8):
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(command, 1, "", str(error))


def card(title, subtitle, child=None):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.set_margin_top(14); box.set_margin_bottom(14)
    box.set_margin_start(16); box.set_margin_end(16)
    heading = Gtk.Label(label=title, xalign=0)
    heading.add_css_class("title-4")
    box.append(heading)
    if subtitle:
        label = Gtk.Label(label=subtitle, xalign=0, wrap=True)
        label.add_css_class("dim-label")
        box.append(label)
    if child:
        box.append(child)
    frame = Gtk.Frame()
    frame.set_child(box)
    return frame


def margins(widget, value):
    widget.set_margin_top(value); widget.set_margin_bottom(value)
    widget.set_margin_start(value); widget.set_margin_end(value)


class ControlCenter(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        if hasattr(self, "window"):
            self.window.present(); return
        provider = Gtk.CssProvider()
        try: provider.load_from_path(THEME)
        except GLib.Error: pass
        display = Gdk.Display.get_default()
        if display: Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Adw.ApplicationWindow(application=self, title="Fetian Control Center")
        self.window.set_default_size(980, 700)
        self.window.set_size_request(760, 520)
        self.window.set_content(self.build_content())
        self.window.present()

    def build_content(self):
        split = Adw.NavigationSplitView()
        sidebar = Adw.NavigationPage(title="FetianOS", tag="sidebar")
        sidebar.set_child(self.build_sidebar(split))
        content = Adw.NavigationPage(title="Overview", tag="overview")
        content.set_child(self.build_overview())
        split.set_sidebar(sidebar); split.set_content(content)
        self.content_page = content
        return split

    def build_sidebar(self, split):
        search = Gtk.SearchEntry(placeholder_text="Search settings")
        search.set_margin_top(10); search.set_margin_bottom(8); search.set_margin_start(10); search.set_margin_end(10)
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        listbox.add_css_class("navigation-sidebar")
        pages = [("▦", "Overview"), ("◈", "Hardware"), ("✦", "Appearance"), ("⌁", "Network"),
                 ("↻", "Software"), ("⚙", "System")]
        for icon, name in pages:
            row = Adw.ActionRow(title=name)
            row.set_title_lines(1)
            row.add_prefix(Gtk.Label(label=icon))
            row.set_activatable(True)
            row.connect("activated", lambda _row, n=name: self.show_page(n))
            listbox.append(row)
        def filter_rows(entry):
            query = entry.get_text().lower().strip()
            row = listbox.get_first_child()
            while row:
                title = row.get_title() if isinstance(row, Adw.ActionRow) else ""
                row.set_visible(not query or query in title.lower())
                row = row.get_next_sibling()
        search.connect("search-changed", filter_rows)
        listbox.select_row(listbox.get_row_at_index(0))
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="FetianOS"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header); box.append(search); box.append(listbox)
        footer = Gtk.Label(label="FetianOS Control Center\nDeveloper Preview", xalign=0)
        footer.add_css_class("dim-label"); margins(footer, 16)
        box.append(footer)
        return box

    def show_page(self, name):
        page = Adw.NavigationPage(title=name, tag=name.lower())
        builders = {"Overview": self.build_overview, "Hardware": self.build_hardware, "Appearance": self.build_appearance,
                    "Network": self.build_network, "Software": self.build_software,
                    "System": self.build_system}
        page.set_child(builders[name]())
        self.content_page = page
        self.window.get_content().set_content(page)

    def scrolled(self, child):
        scroll = Gtk.ScrolledWindow(); scroll.set_child(child); return scroll

    def build_overview(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24); box.set_margin_bottom(24); box.set_margin_start(24); box.set_margin_end(24)
        title = Gtk.Label(label="Welcome to FetianOS", xalign=0); title.add_css_class("title-1"); box.append(title)
        subtitle = Gtk.Label(label="Your system, clearly in your hands.", xalign=0); subtitle.add_css_class("dim-label"); box.append(subtitle)
        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.attach(card("System", f"{platform.node()}\n{platform.machine()}"), 0, 0, 1, 1)
        grid.attach(card("Kernel", platform.release()), 1, 0, 1, 1)
        grid.attach(card("Desktop", os.environ.get("XDG_CURRENT_DESKTOP", "Sway")), 0, 1, 1, 1)
        grid.attach(card("Uptime", self.uptime()), 1, 1, 1, 1)
        box.append(grid)
        try:
            live = "archisobasedir=fetianos" in Path("/proc/cmdline").read_text().split() and Path("/run/archiso/bootmnt").is_dir()
        except OSError:
            live = False
        if live:
            box.append(card("Disposable live session", "Live account: fetian · password: fetian. This public password is for the live media only. Installation is not yet configured."))
        box.append(card("Quick actions", "Common system tasks", self.actions()))
        box.append(card("Power", "Manage the laptop session safely.", self.power_actions()))
        return self.scrolled(box)

    def uptime(self):
        try:
            seconds = float(Path("/proc/uptime").read_text().split()[0]); hours, rem = divmod(int(seconds), 3600)
            return f"{hours}h {rem // 60}m"
        except (OSError, ValueError): return "Unavailable"

    def actions(self):
        row = Gtk.Box(spacing=8)
        for label, callback in [("Search applications", self.open_launcher), ("System health", self.show_health), ("Check for updates", self.check_updates), ("Open terminal", self.open_terminal)]:
            button = Gtk.Button(label=label); button.connect("clicked", callback); row.append(button)
        return row

    def power_actions(self):
        row = Gtk.Box(spacing=8)
        logout = ["hyprctl", "dispatch", "hl.dsp.exit()"] if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") else ["swaymsg", "exit"]
        lock = "fetian-lock.service" if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") else "fetian-sway-lock.service"
        for label, command in [("Lock", ["systemctl", "--user", "start", lock]), ("Suspend", ["systemctl", "suspend"]),
                               ("Reboot", ["systemctl", "reboot"]), ("Shut down", ["systemctl", "poweroff"]),
                               ("Log out", logout)]:
            button = Gtk.Button(label=label); button.connect("clicked", self.confirm_power, command); row.append(button)
        return row

    def confirm_power(self, _button, command):
        if command[-1] in ("fetian-lock.service", "fetian-sway-lock.service"):
            self.perform_power(command)
            return
        labels = {"suspend": "Suspend FetianOS?", "hibernate": "Hibernate FetianOS?", "reboot": "Reboot FetianOS?", "poweroff": "Shut down FetianOS?", "exit": "Log out of FetianOS?"}
        action = command[-1]
        if command[0] == "hyprctl": action = "exit"
        dialog = Adw.MessageDialog(transient_for=self.window, heading=labels.get(action, "Confirm power action"), body="Save your work before continuing.")
        dialog.add_response("cancel", "Cancel"); dialog.add_response("confirm", "Continue")
        dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        def respond(_dialog, response):
            if response != "confirm": return
            self.perform_power(command)
        dialog.connect("response", respond)
        dialog.present()

    def perform_power(self, command):
        def finished(result):
            if result.returncode:
                error = Adw.MessageDialog(transient_for=self.window, heading="Power action failed", body=result.stderr.strip() or "The system could not perform this action.")
                error.add_response("close", "Close"); error.present()
        self.background(command, finished, timeout=30)

    def open_launcher(self, _button):
        self.launch(["wofi", "--show", "drun", "--allow-images", "--prompt", "Search applications"])

    def launch(self, command):
        try:
            subprocess.Popen(command)
        except OSError as error:
            dialog = Adw.MessageDialog(transient_for=self.window, heading="Application unavailable", body=str(error))
            dialog.add_response("close", "Close"); dialog.present()

    def background(self, command, callback, timeout=8):
        def work():
            result = run(command, timeout)
            def finish():
                callback(result)
                return False
            GLib.idle_add(finish)
        threading.Thread(target=work, daemon=True).start()

    def command_card(self, title, subtitle, command):
        label = Gtk.Label(label="Reading system information…", xalign=0, wrap=True, selectable=True)
        def update(result):
            if label.get_root():
                label.set_text(result.stdout.strip() if result.returncode == 0 and result.stdout.strip()
                               else result.stderr.strip() or "Information unavailable.")
        self.background(command, update)
        return card(title, subtitle, label)

    def show_health(self, _button):
        dialog = Adw.MessageDialog(transient_for=self.window, heading="System health", body="Reading system metrics…")
        dialog.add_response("close", "Close")
        dialog.present()
        binary = shutil.which("fetian-health-rs")
        if not binary:
            source = Path(os.environ.get("FETIAN_DEV_ROOT", ".")) / "target/release/fetian-health-rs"
            binary = str(source.resolve()) if source.is_file() else None
        if not binary:
            dialog.set_body("System health is unavailable: the system collector is not installed.")
            return
        def ready(process, result):
            try:
                _, output, error = process.communicate_utf8_finish(result)
                if not process.get_successful(): raise ValueError(error or "Collector failed")
                data = json.loads(output)
                if not isinstance(data, dict) or data.get("schema_version") != 1: raise ValueError("Unsupported health schema")
                memory = data["memory"]
                cpu = data.get("cpu_usage_percent")
                lines = [f"CPU: {cpu:.1f}%" if cpu is not None else "CPU: unavailable",
                         f"Memory: {memory['used_bytes'] / 1048576:.0f} / {memory['total_bytes'] / 1048576:.0f} MiB",
                         f"Uptime: {data['uptime_seconds'] / 3600:.1f} hours",
                         f"Battery devices: {len(data['batteries'])}" if data.get("batteries") is not None else "Battery: unavailable"]
                lines.extend(f"{t['sensor']}: {t['celsius']:.1f} °C" for t in data.get("temperatures") or [])
                dialog.set_body("\n".join(lines))
            except (GLib.Error, ValueError, KeyError, TypeError) as error:
                dialog.set_body("System health unavailable: " + str(error))
        try:
            process = Gio.Subprocess.new([binary, "--json"], Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
            process.communicate_utf8_async(None, None, ready)
        except GLib.Error as error:
            dialog.set_body("System health unavailable: " + str(error))

    def build_appearance(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("fetian-desktop"):
            button = Gtk.Button(label="Effects and accessibility")
            button.connect("clicked", lambda _: self.launch(["fetian-desktop", "quick"]))
            box.append(card("Desktop effects", "Choose balanced, cinematic, performance or accessible materials.", button))
        else:
            box.append(card("Sway appearance", "Keyboard, layout and appearance use your Sway configuration. A graphical editor is not available yet."))
        if shutil.which("nwg-displays"):
            button = Gtk.Button(label="Configure displays")
            button.connect("clicked", lambda _: self.launch(["nwg-displays"]))
            box.append(card("Displays", "Arrange monitors, resolution and scaling.", button))
        box.append(card("Personal settings", "Wallpaper and theme editors are not yet implemented. Existing user configuration is preserved."))
        return self.scrolled(box)

    def build_hardware(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(Gtk.Label(label="Hardware detected automatically", xalign=0))
        box.append(Gtk.Label(label="FetianOS uses the Linux kernel, firmware, and standard device services. Supported hardware needs no manual driver installation.", xalign=0, wrap=True))
        box.append(self.command_card("PCI devices and drivers", "Graphics, Wi-Fi, audio, storage and chipset devices.", ["lspci", "-nnk"]))
        box.append(self.command_card("Storage", "Detected disks and filesystems.", ["lsblk", "-o", "NAME,MODEL,SIZE,TYPE,FSTYPE,MOUNTPOINTS"]))
        row = Gtk.Box(spacing=8)
        report = Gtk.Button(label="Export hardware report"); report.connect("clicked", self.export_hardware_report); row.append(report)
        refresh = Gtk.Button(label="Rescan hardware"); refresh.connect("clicked", lambda _b: self.show_page("Hardware")); row.append(refresh)
        box.append(row)
        return self.scrolled(box)

    def export_hardware_report(self, _button):
        path = os.path.expanduser("~/fetian-hardware-report.json")
        reporter = os.path.join(os.environ.get("FETIAN_DEV_ROOT", ""), "apps/fetian-hardware/fetian-hardware-report")
        if not reporter or not os.path.isfile(reporter): reporter = "fetian-hardware-report"
        # Do not silently overwrite a previous report.
        if Path(path).exists():
            from datetime import datetime
            path = os.path.expanduser("~/fetian-hardware-report-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
        def finish(result):
            try:
                if result.returncode: raise ValueError(result.stderr or "Report command failed")
                with open(path, "x", encoding="utf-8") as output: output.write(result.stdout)
                heading, body = "Hardware report exported", path
            except (OSError, ValueError) as error:
                heading, body = "Report export failed", str(error)
            dialog = Adw.MessageDialog(transient_for=self.window, heading=heading, body=body)
            dialog.add_response("close", "Close"); dialog.present()
        self.background([reporter, "--json"], finish)

    def build_network(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(self.command_card("Connections", "NetworkManager connections on this device.", ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,STATE", "connection", "show"]))
        for label, command in (("Configure network", ["nm-connection-editor"]),
                               ("Bluetooth devices", ["blueman-manager"]),
                               ("Audio and microphone", ["pavucontrol"]),
                               ("Printers", ["system-config-printer"])):
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _, c=command: self.launch(c))
            box.append(button)
        refresh = Gtk.Button(label="Refresh connections"); refresh.connect("clicked", lambda _b: self.show_page("Network")); box.append(refresh)
        return self.scrolled(box)

    def build_software(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(Gtk.Label(label="Software and updates", xalign=0))
        update = Gtk.Button(label="Check for updates"); update.connect("clicked", self.check_updates)
        box.append(card("System updates", "Updates are signed by the configured Manjaro repositories.", update))
        install = Gtk.Button(label="Install updates in terminal"); install.connect("clicked", self.install_updates)
        box.append(card("Upgrade", "Review and confirm the complete signed package transaction in a terminal. Authentication is required.", install))
        apps = Gtk.Button(label="Open Fetian Apps"); apps.connect("clicked", lambda _b: self.launch(["fetian-apps"]))
        repair = Gtk.Button(label="Repair theme package conflicts"); repair.connect("clicked", self.repair_theme_packages)
        actions = Gtk.Box(spacing=8); actions.append(apps); actions.append(repair)
        box.append(card("Packages", "Search, install, and remove applications. Changes require authentication.", actions))
        return self.scrolled(box)

    def repair_theme_packages(self, _button):
        root = os.environ.get("FETIAN_DEV_ROOT")
        script = os.path.join(root, "scripts/migrate-kvantum-matcha.sh") if root else "/usr/lib/fetian/migrate-kvantum-matcha.sh"
        # The repair script may require interaction; keep its terminal attached.
        self.terminal(["bash", script])

    def build_system(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(card("Kernel", f"Running: {platform.release()}\nFetianOS uses the signed Manjaro kernel selected in the ISO profile."))
        box.append(self.command_card("Core services", "Genuine service state; unavailable services are reported.", ["systemctl", "--no-pager", "--plain", "list-units", "NetworkManager.service", "bluetooth.service", "fetian-health.timer"]))
        logs = Gtk.Button(label="Open startup logs")
        logs.connect("clicked", lambda _: self.terminal(["journalctl", "--boot", "--unit=sddm.service", "--unit=fetian-live-user.service"]))
        box.append(card("Recovery", "Select the text recovery boot entry if graphics fail. The Sway recovery session remains available at login.", logs))
        box.append(card("Hibernate", "Hibernate is unavailable until swap and resume support are configured and tested."))
        return self.scrolled(box)

    def check_updates(self, _button):
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Checking for updates", body="Reading signed repository metadata. No packages will be installed.")
        dialog.add_response("close", "Close"); dialog.present()
        source = os.environ.get("FETIAN_DEV_ROOT")
        helper = str(Path(source) / "apps/fetian-desktop/fetian_daily.py") if source else "/usr/share/fetian-desktop/fetian_daily.py"
        def finish(result):
            if dialog.get_visible():
                dialog.set_heading("Available updates" if result.returncode == 0 else "Update check failed")
                dialog.set_body(result.stdout[-6000:] if result.returncode == 0 else result.stderr[-1800:] or "Update check unavailable.")
        self.background([sys.executable, helper, "check-updates"], finish, timeout=125)

    def install_updates(self, _button):
        self.terminal(["fetian-update", "install"])

    def terminal(self, command):
        for terminal in ("foot", "alacritty"):
            if shutil.which(terminal):
                self.launch([terminal, "-e", *command] if command else [terminal])
                return
        self.launch(["foot", "-e", *command] if command else ["foot"])

    def open_terminal(self, _button):
        self.terminal([])


if __name__ == "__main__":
    ControlCenter().run()
