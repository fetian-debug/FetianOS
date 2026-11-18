#!/usr/bin/env python3
"""FetianFiles preview: native GTK, GIO devices/trash, bounded local operations."""
import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

if __name__ == "__main__" and os.geteuid() == 0:
    sys.exit("FetianFiles refuses root. Use your regular desktop account.")

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk
import fileops
import preferences

ATTRIBUTES = "standard::*,unix::mode,time::modified,trash::orig-path"


def file_provider(files):
    # text/uri-list interoperates with other file managers and older GTK 4
    # versions which expose FileList but not its constructors.
    data = ("\r\n".join(file.get_uri() for file in files) + "\r\n").encode()
    return Gdk.ContentProvider.new_for_bytes("text/uri-list", GLib.Bytes.new(data))


def safe_location(value):
    parsed = urlsplit(value)
    if parsed.password is not None: raise ValueError("Use the GVfs authentication dialog instead of passwords in location URLs")
    return Gio.File.parse_name(value)


def enumerate_location(location, cancellable, hidden=False):
    entries = []
    iterator = location.enumerate_children(ATTRIBUTES, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, cancellable)
    try:
        while True:
            info = iterator.next_file(cancellable)
            if info is None: break
            if not hidden and info.get_is_hidden(): continue
            entries.append({"file": location.get_child(info.get_name()), "info": info})
            if len(entries) >= 20000: raise ValueError("Folder exceeds the 20,000-item preview limit. Use Thunar for this location.")
    finally: iterator.close(cancellable)
    return sorted(entries, key=lambda item: (item["info"].get_file_type() != Gio.FileType.DIRECTORY, item["info"].get_display_name().casefold()))


class Pane(Gtk.Box):
    def __init__(self, window, location, lazy=False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.window = window; self.location = location; self.generation = 0
        self.entries = []; self.mode = "List"; self.back = []
        self.breadcrumbs = Gtk.Box(spacing=4)
        self.append(self.breadcrumbs)
        self.stack = Gtk.Stack()
        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.MULTIPLE)
        self.grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.MULTIPLE, max_children_per_line=8, min_children_per_line=1)
        for child, mode in ((self.list, "List"), (self.grid, "Grid")):
            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
            scroll.set_child(child); self.stack.add_named(scroll, mode)
        self.list.connect("row-activated", lambda _, row: self.open(row.entry))
        self.grid.connect("child-activated", lambda _, row: self.open(row.entry))
        self.list.connect("selected-rows-changed", lambda _: self.selected_changed())
        self.grid.connect("selected-children-changed", lambda _: self.selected_changed())
        self.append(self.stack)
        gesture = Gtk.GestureClick(button=3)
        gesture.connect("pressed", self.context_menu)
        self.add_controller(gesture)
        if hasattr(Gdk, "FileList"):
            drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
            def dropped(_target, value, _x, _y):
                self.window.transfer(value.get_files(), self.location, False)
                return True
            drop.connect("drop", dropped); self.add_controller(drop)
            drag = Gtk.DragSource.new(); drag.set_actions(Gdk.DragAction.COPY)
            def prepare(_source, _x, _y):
                selected = [entry["file"] for entry in self.selected()]
                return file_provider(selected) if selected else None
            drag.connect("prepare", prepare); self.add_controller(drag)
        if not lazy: self.navigate(location, remember=False)

    def selected_changed(self):
        self.window.active = self
        self.window.location.set_text(self.location.get_parse_name())
        self.window.preview_selection()

    def selected(self):
        rows = self.grid.get_selected_children() if self.mode == "Grid" else self.list.get_selected_rows()
        return [row.entry for row in rows]

    def navigate(self, location, remember=True):
        if remember: self.back.append(self.location)
        # Resolve only intentional native navigation; later file mutations walk
        # every canonical parent using O_NOFOLLOW descriptor-relative operations.
        native = location.get_path()
        if native and Path(native).exists(): location = Gio.File.new_for_path(str(Path(native).resolve()))
        self.location = location; self.generation += 1; generation = self.generation
        self.window.active = self
        self.window.location.set_text(location.get_parse_name())
        self.window.run_job(lambda token, cancel: enumerate_location(location, cancel, self.window.hidden.get_active()),
                            lambda entries: self.populate(entries) if generation == self.generation else None)
        for child in list_children(self.breadcrumbs): self.breadcrumbs.remove(child)
        chain = []; cursor = location
        while cursor is not None and len(chain) < 10:
            chain.append(cursor); cursor = cursor.get_parent()
        for item in reversed(chain):
            button = Gtk.Button(label=item.get_basename() or "/")
            button.connect("clicked", lambda _, target=item: self.navigate(target))
            self.breadcrumbs.append(button)

    def populate(self, entries):
        self.entries = entries
        for child in list_children(self.list): self.list.remove(child)
        for child in list_children(self.grid): self.grid.remove(child)
        for entry in entries:
            info = entry["info"]
            row = Gtk.ListBoxRow(); row.entry = entry
            box = Gtk.Box(spacing=10)
            box.append(Gtk.Image.new_from_gicon(info.get_icon()))
            label = Gtk.Label(label=info.get_display_name(), xalign=0, hexpand=True, ellipsize=3)
            label.set_tooltip_text(entry["file"].get_parse_name())
            box.append(label)
            box.append(Gtk.Label(label=GLib.format_size(info.get_size()) if info.get_file_type() != Gio.FileType.DIRECTORY else "Folder"))
            row.set_child(box); self.list.append(row)
            tile = Gtk.FlowBoxChild(); tile.entry = entry
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            icon = Gtk.Image.new_from_gicon(info.get_icon()); icon.set_pixel_size(40); box.append(icon)
            box.append(Gtk.Label(label=info.get_display_name(), wrap=True, max_width_chars=18))
            tile.set_child(box); self.grid.append(tile)
        self.window.status.set_text(f"{len(entries)} items · {self.location.get_parse_name()}")
        page = self.get_parent()
        if isinstance(page, Gtk.Paned) and page.get_start_child() is self:
            self.window.tabs.set_tab_label_text(page, self.location.get_basename() or "Files")

    def open(self, entry):
        self.window.active = self
        info, file = entry["info"], entry["file"]
        if info.get_file_type() == Gio.FileType.DIRECTORY:
            self.navigate(file); return
        if info.get_content_type() in ("application/zip", "application/x-tar", "application/gzip", "application/x-xz", "application/x-compressed-tar"):
            self.window.archive_list(entry); return
        mode = info.get_attribute_uint32("unix::mode")
        if mode & 0o111 or info.get_content_type() in ("application/x-desktop", "application/x-executable", "application/x-shellscript"):
            self.window.message("Executable not launched", "Inspect this file as text or intentionally run it from a terminal. Preview never executes files.")
            return
        try: Gio.AppInfo.launch_default_for_uri(file.get_uri(), None)
        except GLib.Error as error: self.window.message("Open failed", str(error))

    def context_menu(self, gesture, _count, x, y):
        self.window.active = self
        popover = Gtk.Popover(); popover.set_parent(self)
        rectangle = Gdk.Rectangle(); rectangle.x = int(x); rectangle.y = int(y); rectangle.width = rectangle.height = 1
        popover.set_pointing_to(rectangle)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for label, action in self.window.actions():
            button = Gtk.Button(label=label)
            button.connect("clicked", lambda _, call=action: (popover.popdown(), call()))
            box.append(button)
        popover.set_child(box); popover.connect("closed", lambda p: p.unparent()); popover.popup()


def list_children(widget):
    result = []; child = widget.get_first_child()
    while child:
        result.append(child); child = child.get_next_sibling()
    return result


class FilesWindow(Gtk.ApplicationWindow):
    def __init__(self, application, locations):
        super().__init__(application=application, title="FetianFiles Preview")
        self.set_default_size(1100, 720)
        self.add_css_class("fetian-files")
        provider = Gtk.CssProvider(); provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.active = None; self.clipboard = []; self.cut = False; self.undo = None
        self.jobs = []; self.mount_requests = []; self.preview_generation = 0
        self.state = preferences.load()
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for direction in ("top", "bottom", "start", "end"): getattr(self.root, "set_margin_" + direction)(10)
        self.set_child(self.root)
        self.location = Gtk.Entry(hexpand=True, placeholder_text="Location or GVfs URI")
        self.location.update_property([Gtk.AccessibleProperty.LABEL], ["Location or GVfs URI"])
        self.location.connect("activate", self.go_location)
        toolbar = Gtk.Box(spacing=6)
        for label, action in (("Back", self.go_back), ("Up", self.go_up), ("New tab", self.new_tab),
                              ("Split", self.split), ("Copy", lambda: self.clip(False)),
                              ("Cut", lambda: self.clip(True)), ("Paste", self.paste)):
            self.button(toolbar, label, action)
        toolbar.append(self.location); self.root.append(toolbar)
        options = Gtk.Box(spacing=6)
        self.search = Gtk.SearchEntry(hexpand=True, placeholder_text="Search filenames in this folder")
        self.search.connect("activate", self.search_files); options.append(self.search)
        self.hidden = Gtk.CheckButton(label="Hidden files")
        self.hidden.connect("toggled", lambda _: self.refresh()); options.append(self.hidden)
        for mode in ("List", "Grid", "Compact"):
            self.button(options, mode, lambda selected=mode: self.set_view(selected))
        self.button(options, "Close tab", self.close_tab)
        self.root.append(options)
        filters = Gtk.Box(spacing=6)
        self.kind = Gtk.DropDown.new_from_strings(["Any type", "Files", "Folders"])
        self.kind.set_tooltip_text("Search item type"); filters.append(self.kind)
        self.minimum = Gtk.Entry(placeholder_text="Min KiB", width_chars=8)
        self.maximum = Gtk.Entry(placeholder_text="Max KiB", width_chars=8)
        self.after = Gtk.Entry(placeholder_text="Modified since YYYY-MM-DD", width_chars=24)
        for entry in (self.minimum, self.maximum, self.after): filters.append(entry)
        self.button(filters, "Bookmark", self.bookmark)
        self.preview_toggle = Gtk.CheckButton(label="Preview", active=self.state["preview"])
        self.preview_toggle.connect("toggled", lambda toggle: self.preview_scroll.set_visible(toggle.get_active()))
        filters.append(self.preview_toggle)
        advanced = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6); advanced.append(filters)
        appearance = Gtk.Box(spacing=6)
        appearance.append(Gtk.Label(label="Appearance"))
        self.theme = Gtk.DropDown.new_from_strings(["System", "Light", "Dark"])
        self.theme.set_selected(["System", "Light", "Dark"].index(self.state["theme"]))
        self.theme.connect("notify::selected", lambda *_: self.apply_appearance()); appearance.append(self.theme)
        self.motion = Gtk.CheckButton(label="Reduced motion", active=self.state["reduced_motion"])
        self.motion.connect("toggled", lambda _: self.apply_appearance()); appearance.append(self.motion)
        advanced.append(appearance)
        expander = Gtk.Expander(label="Search filters and appearance"); expander.set_child(advanced)
        self.root.append(expander); self.apply_appearance()
        body = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        side_scroll = Gtk.ScrolledWindow(min_content_width=185); side_scroll.set_child(self.sidebar)
        body.set_start_child(side_scroll)
        body.set_resize_start_child(False); body.set_shrink_start_child(False); body.set_position(200)
        self.tabs = Gtk.Notebook(scrollable=True, hexpand=True)
        self.tabs.set_size_request(320, -1)
        self.tabs.connect("switch-page", self.tab_switched)
        content = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        content.set_start_child(self.tabs)
        self.preview = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.preview.update_property([Gtk.AccessibleProperty.LABEL], ["Read-only file preview"])
        self.preview_stack = Gtk.Stack()
        self.preview_stack.add_named(self.preview, "text")
        self.picture = Gtk.Picture(can_shrink=True)
        self.preview_stack.add_named(self.picture, "image")
        self.preview_scroll = Gtk.ScrolledWindow(min_content_width=240); self.preview_scroll.set_child(self.preview_stack)
        self.preview_scroll.set_visible(self.state["preview"])
        content.set_end_child(self.preview_scroll); content.set_resize_end_child(False)
        content.set_shrink_start_child(False); content.set_position(620)
        body.set_end_child(content); self.root.append(body)
        footer = Gtk.Box(spacing=8)
        self.spinner = Gtk.Spinner(); footer.append(self.spinner)
        self.status = Gtk.Label(label="", xalign=0, hexpand=True, wrap=True); footer.append(self.status)
        self.button(footer, "Cancel jobs", self.cancel_jobs)
        self.root.append(footer)
        self.monitor = Gio.VolumeMonitor.get()
        for signal in ("mount-added", "mount-removed", "volume-added", "volume-removed"):
            self.monitor.connect(signal, lambda *_: self.sidebar_refresh())
        self.sidebar_refresh()
        key = Gtk.EventControllerKey(); key.connect("key-pressed", self.key); self.add_controller(key)
        self.connect("close-request", self.closed)
        restored = [Gio.File.new_for_path(path) for path in self.state["tabs"] if Path(path).is_dir()]
        for location in locations[:10] or restored or [Gio.File.new_for_path(str(Path.home()))]: self.new_tab(location)

    def apply_appearance(self):
        settings = Gtk.Settings.get_default()
        settings.reset_property("gtk-application-prefer-dark-theme")
        if self.theme.get_selected() != 0: settings.set_property("gtk-application-prefer-dark-theme", self.theme.get_selected() == 2)
        settings.set_property("gtk-enable-animations", not self.motion.get_active())

    def bookmark(self):
        uri = self.active.location.get_uri()
        self.state = preferences.validate(dict(self.state, bookmarks=[*self.state["bookmarks"], uri]))
        self.sidebar_refresh()

    def button(self, container, label, action):
        button = Gtk.Button(label=label); button.connect("clicked", lambda _: action()); container.append(button)
        return button

    def run_job(self, work, done=lambda _: None):
        token = fileops.Token(); cancel = Gio.Cancellable(); job = (token, cancel)
        self.jobs.append(job); self.spinner.start(); self.status.set_text("Working…")
        def worker():
            try: value, error = work(token, cancel), None
            except Exception as exc: value, error = None, exc
            def finish():
                if job in self.jobs: self.jobs.remove(job)
                if not self.jobs: self.spinner.stop()
                if self.get_visible():
                    if error: self.status.set_text(str(error))
                    else:
                        self.status.set_text(f"{len(self.jobs)} job(s) running" if self.jobs else "Ready")
                        try: done(value)
                        except Exception as exc: self.status.set_text(str(exc))
                return False
            GLib.idle_add(finish)
        threading.Thread(target=worker, daemon=True).start()

    def cancel_jobs(self):
        for token, cancel in self.jobs: token.cancel(); cancel.cancel()
        for cancel in self.mount_requests: cancel.cancel()

    def new_tab(self, location=None):
        location = location if isinstance(location, Gio.File) else Gio.File.new_for_path(str(Path.home()))
        page = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        page.set_position(400)
        first = Pane(self, location); page.set_start_child(first)
        second = Pane(self, location, lazy=True); second.set_visible(False); page.set_end_child(second)
        self.tabs.append_page(page, Gtk.Label(label=location.get_basename() or "Files"))
        self.tabs.set_current_page(self.tabs.page_num(page)); self.active = first

    def close_tab(self):
        if self.tabs.get_n_pages() > 1: self.tabs.remove_page(self.tabs.get_current_page())

    def tab_switched(self, _tabs, page, _number):
        self.active = page.get_start_child()
        self.location.set_text(self.active.location.get_parse_name())

    def split(self):
        page = self.tabs.get_nth_page(self.tabs.get_current_page())
        second = page.get_end_child(); second.set_visible(not second.get_visible())
        self.active = second if second.get_visible() else page.get_start_child()
        if second.get_visible() and not second.entries: second.navigate(second.location, remember=False)

    def go_location(self, _entry):
        try: self.connect_location(safe_location(self.location.get_text()))
        except (ValueError, GLib.Error) as error: self.status.set_text(str(error))

    def connect_location(self, location):
        if location.get_path(): self.active.navigate(location); return
        pane = self.active; cancel = Gio.Cancellable(); self.mount_requests.append(cancel)
        self.status.set_text("Connecting…")
        def ready(item, result):
            if cancel in self.mount_requests: self.mount_requests.remove(cancel)
            try: item.mount_enclosing_volume_finish(result)
            except GLib.Error as error:
                if not any(error.matches(Gio.io_error_quark(), code) for code in (Gio.IOErrorEnum.ALREADY_MOUNTED, Gio.IOErrorEnum.NOT_SUPPORTED)):
                    self.status.set_text(str(error)); return
            if not cancel.is_cancelled() and self.get_visible(): pane.navigate(location)
        location.mount_enclosing_volume(Gio.MountMountFlags.NONE, Gtk.MountOperation.new(self), cancel, ready)
    def go_up(self):
        parent = self.active.location.get_parent()
        if parent: self.active.navigate(parent)
    def go_back(self):
        if self.active.back: self.active.navigate(self.active.back.pop(), remember=False)
    def refresh(self):
        if self.active: self.active.navigate(self.active.location, remember=False)
    def set_view(self, mode):
        self.active.mode = mode
        self.active.stack.set_visible_child_name("Grid" if mode == "Grid" else "List")
        if mode == "Compact": self.active.list.add_css_class("compact")
        else: self.active.list.remove_css_class("compact")

    def sidebar_refresh(self):
        for child in list_children(self.sidebar): self.sidebar.remove(child)
        for title, uri in (("Home", Path.home().as_uri()), ("Trash", "trash:///"), ("Recent", "recent:///"), ("Network", "network:///")):
            self.button(self.sidebar, title, lambda value=uri: self.active.navigate(Gio.File.new_for_uri(value)) if self.active else None)
        for kind, title in ((GLib.UserDirectory.DIRECTORY_DESKTOP, "Desktop"), (GLib.UserDirectory.DIRECTORY_DOCUMENTS, "Documents"),
                            (GLib.UserDirectory.DIRECTORY_DOWNLOAD, "Downloads"), (GLib.UserDirectory.DIRECTORY_PICTURES, "Pictures"),
                            (GLib.UserDirectory.DIRECTORY_MUSIC, "Music"), (GLib.UserDirectory.DIRECTORY_VIDEOS, "Videos")):
            path = GLib.get_user_special_dir(kind)
            if path: self.button(self.sidebar, title, lambda p=path: self.active.navigate(Gio.File.new_for_path(p)))
        for mount in self.monitor.get_mounts():
            row = Gtk.Box(spacing=2)
            self.button(row, mount.get_name(), lambda m=mount: self.active.navigate(m.get_root()))
            self.button(row, "Eject" if mount.can_eject() else "Unmount", lambda m=mount: self.unmount(m, eject=m.can_eject()))
            row.set_tooltip_text(mount.get_root().get_parse_name())
            self.sidebar.append(row)
        for volume in self.monitor.get_volumes():
            if volume.get_mount() is None:
                self.button(self.sidebar, "Mount " + volume.get_name(), lambda v=volume: self.mount(v))
        for uri in self.state["bookmarks"]:
            location = safe_location(uri); row = Gtk.Box(spacing=2)
            self.button(row, location.get_basename() or uri, lambda item=location: self.connect_location(item))
            self.button(row, "Remove", lambda value=uri: (self.state["bookmarks"].remove(value), self.sidebar_refresh()))
            self.sidebar.append(row)

    def mount(self, volume):
        def ready(item, result):
            try:
                item.mount_finish(result)
                if item.get_mount(): self.active.navigate(item.get_mount().get_root())
            except GLib.Error as error: self.status.set_text(str(error))
        volume.mount(Gio.MountMountFlags.NONE, Gtk.MountOperation.new(self), None, ready)

    def unmount(self, mount, eject=False):
        def ready(item, result):
            try:
                if eject: item.eject_with_operation_finish(result)
                else: item.unmount_with_operation_finish(result)
                self.status.set_text("Ejected safely" if eject else "Unmounted safely")
            except GLib.Error as error: self.status.set_text(str(error))
        operation = mount.eject_with_operation if eject else mount.unmount_with_operation
        operation(Gio.MountUnmountFlags.NONE, Gtk.MountOperation.new(self), None, ready)

    def actions(self):
        return [("Open", lambda: [self.active.open(e) for e in self.active.selected()]),
                ("Copy", lambda: self.clip(False)), ("Cut", lambda: self.clip(True)), ("Paste", self.paste),
                ("New folder", lambda: self.create(True)), ("New file", lambda: self.create(False)),
                ("Rename", self.rename), ("Move to Trash", self.trash), ("Restore from Trash", self.restore),
                ("Delete permanently", self.delete), ("Properties", self.properties), ("Permissions", self.permissions),
                ("Extract to new folder", self.extract), ("Create ZIP", self.compress), ("Undo last move/rename", self.undo_last)]

    def message(self, title, body):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, text=title, secondary_text=body, buttons=Gtk.ButtonsType.CLOSE)
        dialog.connect("response", lambda d, _: d.destroy()); dialog.present()

    def prompt(self, title, callback, initial=""):
        dialog = Gtk.Dialog(title=title, transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL); dialog.add_button("Continue", Gtk.ResponseType.OK)
        entry = Gtk.Entry(text=initial, activates_default=True); dialog.get_content_area().append(entry)
        dialog.set_default_response(Gtk.ResponseType.OK)
        def ready(dialog, response):
            text = entry.get_text(); dialog.destroy()
            if response == Gtk.ResponseType.OK:
                try: callback(fileops.name(text))
                except Exception as error: self.status.set_text(str(error))
        dialog.connect("response", ready); dialog.present()

    def confirm(self, title, text, callback):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, text=title, secondary_text=text, buttons=Gtk.ButtonsType.OK_CANCEL)
        def ready(dialog, response):
            dialog.destroy()
            if response == Gtk.ResponseType.OK: callback()
        dialog.connect("response", ready); dialog.present()

    def clip(self, cut):
        self.clipboard = [entry["file"] for entry in self.active.selected()]; self.cut = cut
        if hasattr(Gdk, "FileList"):
            self.get_clipboard().set_content(file_provider(self.clipboard))
        else: self.get_clipboard().set("\n".join(file.get_uri() for file in self.clipboard))
        self.status.set_text(f"{len(self.clipboard)} items {'cut' if cut else 'copied'}; paste into a pane")

    def paste(self):
        if not self.get_clipboard().is_local(): self.clipboard = []; self.cut = False
        if not self.clipboard and hasattr(Gdk, "FileList"):
            destination = self.active.location
            def ready(clipboard, result):
                try: self.transfer(clipboard.read_value_finish(result).get_files(), destination, False)
                except (GLib.Error, AttributeError) as error: self.status.set_text(str(error))
            self.get_clipboard().read_value_async(Gdk.FileList, GLib.PRIORITY_DEFAULT, None, ready)
            return
        sources = list(self.clipboard); destination = self.active.location; cut = self.cut
        self.transfer(sources, destination, cut)

    def transfer(self, sources, destination, cut=False):
        def work(token, cancel):
            completed = []; receipts = []
            for source in sources:
                token.check(); target = destination.get_child(source.get_basename())
                try:
                    if source.get_path() and target.get_path():
                        if cut: receipts.append(fileops.move(source.get_path(), target.get_path(), token))
                        else: fileops.copy(source.get_path(), target.get_path(), token)
                    elif cut: source.move(target, Gio.FileCopyFlags.NONE, cancel, None, None)
                    else: source.copy(target, Gio.FileCopyFlags.NOFOLLOW_SYMLINKS, cancel, None, None)
                    completed.append(source.get_basename())
                except Exception as error: raise RuntimeError(f"Completed {len(completed)} item(s); stopped at {source.get_basename()}: {error}") from error
            return receipts
        def done(receipts):
            self.undo = receipts[-1] if len(receipts) == 1 else None
            if cut: self.clipboard = []
            self.refresh()
        self.run_job(work, done)

    def create(self, folder):
        parent = self.active.location
        def create(value):
            def work(token, cancel):
                target = parent.get_child(value)
                if target.get_path(): return fileops.create(target.get_path(), folder)
                if folder: return target.make_directory(cancel)
                stream = target.create(Gio.FileCreateFlags.NONE, cancel); stream.close(cancel)
            self.run_job(work, lambda _: self.refresh())
        self.prompt("New folder" if folder else "New file", create)

    def rename(self):
        selected = self.active.selected()
        if len(selected) > 1:
            paths = [entry["file"].get_path() for entry in selected]
            if any(path is None for path in paths): return self.message("Unavailable", "Batch rename supports local items only.")
            def apply(pattern):
                self.confirm("Apply batch rename?", f"{len(paths)} items. Pattern: {pattern}. Existing names cause failure; rollback is attempted on error.",
                             lambda: self.run_job(lambda token, cancel: fileops.batch_rename(paths, pattern, token), lambda _: self.refresh()))
            return self.prompt("Rename pattern: {n}, {name}, {stem}, {suffix}", apply, "{n}-{name}")
        if not selected: return
        file = selected[0]["file"]
        def apply(value):
            def work(token, cancel):
                destination = file.get_parent().get_child(value)
                if file.get_path(): return fileops.move(file.get_path(), destination.get_path(), token)
                file.move(destination, Gio.FileCopyFlags.NONE, cancel, None, None)
            def done(receipt): self.undo = receipt; self.refresh()
            self.run_job(work, done)
        self.prompt("Rename without overwriting", apply, file.get_basename())

    def undo_last(self):
        if self.undo: self.run_job(lambda token, cancel: fileops.undo_move(self.undo), lambda _: (setattr(self, "undo", None), self.refresh()))

    def trash(self):
        files = [entry["file"] for entry in self.active.selected()]
        def work(token, cancel):
            completed = 0
            for file in files:
                token.check()
                try: file.trash(cancel); completed += 1
                except GLib.Error as error: raise RuntimeError(f"Trashed {completed}; no permanent-delete fallback: {error}") from error
        self.confirm("Move to Trash?", f"{len(files)} selected item(s). Unsupported locations will fail without deleting permanently.",
                     lambda: self.run_job(work, lambda _: self.refresh()))

    def restore(self):
        entries = list(self.active.selected())
        def work(token, cancel):
            for entry in entries:
                token.check(); original = entry["info"].get_attribute_byte_string("trash::orig-path")
                if not original: raise ValueError("Select an item in Trash with an original path")
                entry["file"].move(Gio.File.new_for_path(original), Gio.FileCopyFlags.NONE, cancel, None, None)
        self.run_job(work, lambda _: self.refresh())

    def delete(self):
        paths = [entry["file"].get_path() for entry in self.active.selected()]
        if not paths or any(path is None for path in paths): return self.message("Unavailable", "Permanent deletion in this preview supports only local files.")
        def work(token, cancel):
            for path in paths: fileops.delete(path, confirmed=True, token=token)
        self.confirm("Permanently delete?", f"{len(paths)} item(s) will be irreversibly removed. Partial deletion cannot be undone. This is not secure erasure.", lambda: self.run_job(work, lambda _: self.refresh()))

    def properties(self):
        entries = self.active.selected()
        text = "\n\n".join(f"{e['info'].get_display_name()}\n{e['file'].get_parse_name()}\n{GLib.format_size(e['info'].get_size())}\nMode: {e['info'].get_attribute_uint32('unix::mode') & 0o777:o}\n{e['info'].get_content_type()}" for e in entries)
        self.message("Properties (read only)", text or "Select a file")

    def permissions(self):
        entries = self.active.selected()
        if len(entries) != 1 or not entries[0]["file"].get_path(): return self.message("Select one local item", "Permission editing does not elevate privileges or recurse.")
        path = entries[0]["file"].get_path()
        def apply(value):
            if len(value) != 3 or any(char not in "01234567" for char in value): raise ValueError("Enter three octal digits, e.g. 644")
            self.confirm("Change permissions?", f"{path}: {value}. This may affect access or executable status.",
                         lambda: self.run_job(lambda token, cancel: fileops.permissions(path, int(value, 8)), lambda _: self.refresh()))
        self.prompt("Permissions (octal, local owner access only)", apply, f"{entries[0]['info'].get_attribute_uint32('unix::mode') & 0o777:03o}")

    def preview_selection(self):
        if not self.preview_toggle.get_active(): return
        entries = self.active.selected(); self.preview_generation += 1; generation = self.preview_generation
        self.preview_stack.set_visible_child_name("text")
        if len(entries) != 1: self.preview.get_buffer().set_text("Select one file for a bounded text preview."); return
        path = entries[0]["file"].get_path()
        if not path: self.preview.get_buffer().set_text("Remote previews are not enabled."); return
        if (entries[0]["info"].get_content_type() or "").startswith("image/"):
            def image(token, cancel):
                token.check()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("image_preview.py")), path], text=True, capture_output=True, timeout=10, check=False)
                token.check()
                if result.returncode: raise ValueError(result.stderr.strip() or "Image preview failed")
                if len(result.stdout) > 1500000: raise ValueError("Thumbnail output limit exceeded")
                return base64.b64decode(json.loads(result.stdout)["png"], validate=True)
            def done_image(data):
                if generation == self.preview_generation:
                    self.picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)))
                    self.preview_stack.set_visible_child_name("image")
            self.run_job(image, done_image)
            return
        def done(value):
            if generation == self.preview_generation:
                text, truncated = value; self.preview.get_buffer().set_text(text + ("\n[Preview truncated]" if truncated else ""))
        self.run_job(lambda token, cancel: fileops.preview_text(path), done)

    def search_files(self, _entry):
        path = self.active.location.get_path(); pane = self.active; query = self.search.get_text(); generation = pane.generation
        if not path: return self.message("Search unavailable", "Recursive search currently supports local folders only.")
        try:
            minimum = int(self.minimum.get_text() or "0") * 1024
            maximum = int(self.maximum.get_text()) * 1024 if self.maximum.get_text() else None
            after = datetime.strptime(self.after.get_text(), "%Y-%m-%d").timestamp() if self.after.get_text() else None
            kind = ("any", "file", "folder")[self.kind.get_selected()]
        except ValueError as error: return self.status.set_text("Invalid search filter: " + str(error))
        def work(token, cancel):
            paths, truncated = fileops.search(path, query, token, minimum=minimum, maximum=maximum, kind=kind, modified_after=after)
            entries = []
            for path in paths:
                file = Gio.File.new_for_path(path)
                entries.append({"file": file, "info": file.query_info(ATTRIBUTES, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, cancel)})
            return entries, truncated
        def done(result):
            if generation != pane.generation: return
            entries, truncated = result; pane.populate(entries)
            self.status.set_text(f"{len(entries)} matches" + (" · search limit reached" if truncated else ""))
        self.run_job(work, done)

    def archive_job(self, action, source, destination=None, extra=(), level=6):
        path = source.get_path()
        if not path: raise ValueError("Archive operations currently support local files only")
        command = [sys.executable, str(Path(__file__).with_name("archiveops.py")), "--level", str(level), action, path]
        if destination: command.append(str(destination))
        if extra: command.extend(["--", *extra])
        def work(token, cancel):
            child = subprocess.Popen(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            started = time.monotonic()
            try:
                while True:
                    token.check()
                    if time.monotonic() - started > 40: raise TimeoutError("Archive worker timed out; inspect hidden .fetian-job folders before manually removing incomplete output")
                    try: output, error = child.communicate(timeout=0.1); break
                    except subprocess.TimeoutExpired: continue
                if child.returncode: raise ValueError(error.strip() or "Archive worker failed")
                return json.loads(output)
            finally:
                if child.poll() is None:
                    child.terminate()
                    try: child.communicate(timeout=2)
                    except subprocess.TimeoutExpired: child.kill(); child.communicate()
        return work

    def archive_list(self, entry):
        try: job = self.archive_job("list", entry["file"])
        except ValueError as error: return self.message("Archive unavailable", str(error))
        self.run_job(job, lambda entries: self.archive_browser(entry["file"], entries))

    def archive_browser(self, file, entries):
        dialog = Gtk.Dialog(title="Archive contents", transient_for=self, modal=True)
        dialog.set_default_size(650, 500); dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.connect("response", lambda item, _: item.destroy())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll = Gtk.ScrolledWindow(vexpand=True); scroll.set_child(box)
        dialog.get_content_area().append(scroll); checks = []
        for item in entries[:1000]:
            size = "unknown length; bounded during extraction" if item["size"] is None else GLib.format_size(item["size"])
            label = f"{item['name']} · {size}"
            if item["folder"]: box.append(Gtk.Label(label=label, xalign=0, wrap=True))
            else:
                check = Gtk.CheckButton(label=label); checks.append((check, item["name"])); box.append(check)
        if len(entries) > 1000: box.append(Gtk.Label(label="Only the first 1,000 entries are shown. Full extraction remains available.", wrap=True))
        def selected():
            names = [name for check, name in checks if check.get_active()]
            if not names: return
            def extract(value): self.run_job(self.archive_job("extract", file, Path(file.get_path()).parent / value, names), lambda _: self.refresh())
            self.prompt("Extract selected files into a new folder", extract, file.get_basename() + "-selected")
            dialog.destroy()
        self.button(dialog.get_content_area(), "Extract selected files", selected)
        dialog.present()

    def extract(self):
        entries = self.active.selected()
        if len(entries) != 1 or not self.active.location.get_path(): return
        parent = Path(self.active.location.get_path()); file = entries[0]["file"]
        def apply(value): self.run_job(self.archive_job("extract", file, parent / value), lambda _: self.refresh())
        self.prompt("Extract into a new folder (no overwrite)", apply, file.get_basename() + "-extracted")

    def compress(self):
        files = [entry["file"] for entry in self.active.selected()]
        if not files or not self.active.location.get_path() or any(file.get_path() is None for file in files): return
        parent = Path(self.active.location.get_path())
        def apply(value):
            def compress(level):
                if level not in tuple(str(number) for number in range(10)): raise ValueError("Choose a ZIP compression level from 0 to 9")
                self.run_job(self.archive_job("create", files[0], parent / value, [file.get_path() for file in files[1:]], int(level)), lambda _: self.refresh())
            self.prompt("ZIP compression level: 0 fast, 9 smaller", compress, "6")
        self.prompt("Create ZIP (no overwrite)", apply, "Archive.zip")

    def key(self, _controller, key, _code, state):
        control = bool(state & Gdk.ModifierType.CONTROL_MASK)
        focus = self.get_focus()
        if isinstance(focus, (Gtk.Editable, Gtk.TextView)) and (key in (Gdk.KEY_Delete, Gdk.KEY_F2) or (control and key in (Gdk.KEY_c, Gdk.KEY_x, Gdk.KEY_v, Gdk.KEY_z))):
            return False
        if control:
            actions = {Gdk.KEY_c: lambda: self.clip(False), Gdk.KEY_x: lambda: self.clip(True), Gdk.KEY_v: self.paste,
                       Gdk.KEY_t: self.new_tab, Gdk.KEY_w: self.close_tab, Gdk.KEY_z: self.undo_last,
                       Gdk.KEY_l: lambda: self.location.grab_focus(), Gdk.KEY_f: lambda: self.search.grab_focus(),
                       Gdk.KEY_h: lambda: self.hidden.set_active(not self.hidden.get_active())}
            if key in actions: actions[key](); return True
        if key == Gdk.KEY_F2: self.rename(); return True
        if key == Gdk.KEY_Delete: self.trash(); return True
        if key == Gdk.KEY_F5: self.refresh(); return True
        return False

    def closed(self, _window):
        self.cancel_jobs()
        tabs = [self.tabs.get_nth_page(index).get_start_child().location.get_path() for index in range(self.tabs.get_n_pages())]
        try: preferences.save(dict(self.state, tabs=[path for path in tabs if path], theme=["System", "Light", "Dark"][self.theme.get_selected()], preview=self.preview_toggle.get_active(), reduced_motion=self.motion.get_active()))
        except (OSError, ValueError, TypeError) as error: print(f"Preferences not saved: {error}", file=sys.stderr)
        return False


class FilesApplication(Gtk.Application):
    def __init__(self, locations):
        super().__init__(application_id="online.fetian.Files", flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.locations = locations
    def do_activate(self):
        window = FilesWindow(self, self.locations)
        window.present()


def main():
    parser = argparse.ArgumentParser(description="FetianFiles preview; Thunar remains the existing primary")
    parser.add_argument("locations", nargs="*")
    parser.add_argument("--rtl", action="store_true")
    args = parser.parse_args()
    if args.rtl or os.environ.get("LANG", "").startswith("ar"):
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)
    return FilesApplication([safe_location(value) for value in args.locations]).run([sys.argv[0]])


if __name__ == "__main__": sys.exit(main())
