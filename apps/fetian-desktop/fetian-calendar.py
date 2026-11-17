#!/usr/bin/env python3
import datetime
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

class Calendar(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="online.fetian.Calendar", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self, title="Fetian Calendar")
        window.set_default_size(420, 360)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("top", "bottom", "start", "end"): getattr(box, "set_margin_" + side)(20)
        heading = Gtk.Label(label="Fetian Calendar", xalign=0); heading.add_css_class("title-1")
        today = Gtk.Label(label=datetime.date.today().strftime("%A, %d %B %Y"), xalign=0); today.add_css_class("dim-label")
        box.append(heading); box.append(today); box.append(Gtk.Calendar())
        note = Gtk.Label(label="Use the Control Center for system settings and Waybar for quick access.", wrap=True, xalign=0)
        note.add_css_class("dim-label"); box.append(note); window.set_child(box); window.present()

if __name__ == "__main__": Calendar().run()
