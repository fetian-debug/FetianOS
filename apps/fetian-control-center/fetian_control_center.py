#!/usr/bin/env python3
"""FetianOS Control Center: a safe, small control surface for the desktop."""
import os
import platform
import subprocess
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
        def filter_rows(entry, _param):
            query = entry.get_text().lower().strip()
            row = listbox.get_first_child()
            while row:
                action = row.get_child()
                title = action.get_title() if action else ""
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
        for label, callback in [("Search applications", self.open_launcher), ("Check for updates", self.check_updates), ("Open terminal", self.open_terminal)]:
            button = Gtk.Button(label=label); button.connect("clicked", callback); row.append(button)
        return row

    def power_actions(self):
        row = Gtk.Box(spacing=8)
        for label, command in [("Suspend", ["systemctl", "suspend"]), ("Hibernate", ["systemctl", "hibernate"]),
                               ("Reboot", ["systemctl", "reboot"]), ("Shut down", ["systemctl", "poweroff"]),
                               ("Log out", ["swaymsg", "exit"])]:
            button = Gtk.Button(label=label); button.connect("clicked", self.confirm_power, command); row.append(button)
        return row

    def confirm_power(self, _button, command):
        labels = {"suspend": "Suspend FetianOS?", "hibernate": "Hibernate FetianOS?", "reboot": "Reboot FetianOS?", "poweroff": "Shut down FetianOS?", "exit": "Log out of FetianOS?"}
        action = command[-1]
        dialog = Adw.MessageDialog(transient_for=self.window, heading=labels.get(action, "Confirm power action"), body="Save your work before continuing.")
        dialog.add_response("cancel", "Cancel"); dialog.add_response("confirm", "Continue")
        dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda _d, response: response == "confirm" and subprocess.Popen(command))
        dialog.present()

    def open_launcher(self, _button):
        subprocess.Popen(["wofi", "--show", "drun", "--allow-images", "--prompt", "Search applications"])

    def build_appearance(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(Gtk.Label(label="Make FetianOS yours", xalign=0))
        for title, subtitle in [("Theme", "Choose light, dark, or system appearance."),
                                ("Sway layout", "Configure gaps, borders, focus, and workspace behavior."),
                                ("Panel and wallpaper", "Customize Waybar, wallpaper, lock screen, and notifications.")]:
            row = Adw.ActionRow(title=title, subtitle=subtitle)
            button = Gtk.Button(label="Configure"); button.set_valign(Gtk.Align.CENTER); row.add_suffix(button)
            box.append(card(title, subtitle, row))
        return self.scrolled(box)

    def build_hardware(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(Gtk.Label(label="Hardware detected automatically", xalign=0))
        box.append(Gtk.Label(label="FetianOS uses the Linux kernel, firmware, and standard device services. Supported hardware needs no manual driver installation.", xalign=0, wrap=True))
        devices = run(["lspci", "-nnk"]).stdout.strip()
        box.append(card("PCI devices and drivers", "Graphics, Wi-Fi, Ethernet, audio, storage controllers, and chipset devices.", Gtk.Label(label=devices or "No PCI information available.", xalign=0, wrap=True)))
        storage = run(["lsblk", "-o", "NAME,MODEL,SIZE,TYPE,FSTYPE,MOUNTPOINTS"]).stdout.strip()
        box.append(card("Storage", "Detected disks and filesystems.", Gtk.Label(label=storage or "No storage information available.", xalign=0, wrap=True)))
        row = Gtk.Box(spacing=8)
        report = Gtk.Button(label="Export hardware report"); report.connect("clicked", self.export_hardware_report); row.append(report)
        refresh = Gtk.Button(label="Rescan hardware"); refresh.connect("clicked", lambda _b: self.show_page("Hardware")); row.append(refresh)
        box.append(row)
        return self.scrolled(box)

    def export_hardware_report(self, _button):
        path = os.path.expanduser("~/fetian-hardware-report.json")
        reporter = os.path.join(os.environ.get("FETIAN_DEV_ROOT", ""), "apps/fetian-hardware/fetian-hardware-report")
        if not reporter or not os.path.isfile(reporter): reporter = "fetian-hardware-report"
        result = run([reporter, "--json"])
        if result.returncode == 0: Path(path).write_text(result.stdout, encoding="utf-8")
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Hardware report exported", body=path if result.returncode == 0 else result.stderr)
        dialog.add_response("close", "Close"); dialog.present()

    def build_network(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        output = run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE,STATE", "connection", "show"]).stdout.strip()
        label = Gtk.Label(label=output or "NetworkManager is unavailable.", xalign=0, wrap=True)
        label.set_selectable(True); box.append(card("Connections", "Network connections detected on this device.", label))
        refresh = Gtk.Button(label="Refresh connections"); refresh.connect("clicked", lambda _b: self.show_page("Network")); box.append(refresh)
        return self.scrolled(box)

    def build_software(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(Gtk.Label(label="Software and updates", xalign=0))
        update = Gtk.Button(label="Check for updates"); update.connect("clicked", self.check_updates)
        box.append(card("System updates", "Updates are signed by the configured Manjaro repositories.", update))
        apps = Gtk.Button(label="Open Fetian Apps"); apps.connect("clicked", lambda _b: subprocess.Popen(["fetian-apps"]))
        box.append(card("Packages", "Search, install, and remove applications. Changes require authentication.", apps))
        return self.scrolled(box)

    def build_system(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12); margins(box, 24)
        box.append(card("Kernel", f"Running: {platform.release()}\nFetianOS uses the signed Manjaro kernel selected in the ISO profile."))
        box.append(card("Services", "Manage NetworkManager, Bluetooth, audio, Docker, and other services safely."))
        box.append(card("Recovery", "Backups, snapshots, logs, and repair tools will be added here."))
        return self.scrolled(box)

    def check_updates(self, _button):
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Check for updates?",
                                   body="This opens pacman’s signed repository update check. Installing updates will require authentication.")
        dialog.add_response("cancel", "Cancel"); dialog.add_response("check", "Check")
        dialog.set_response_appearance("check", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self.update_response); dialog.present()

    def update_response(self, _dialog, response):
        if response != "check": return
        result = run(["pkexec", "pacman", "-Syu"], timeout=120)
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Update command finished",
                                   body=result.stdout[-1800:] if result.stdout else result.stderr[-1800:] or "No output.")
        dialog.add_response("close", "Close"); dialog.present()

    def open_terminal(self, _button):
        for terminal in ("foot", "alacritty"):
            if run(["sh", "-c", f"command -v {terminal}"]).returncode == 0:
                subprocess.Popen([terminal]); return


if __name__ == "__main__":
    ControlCenter().run()
