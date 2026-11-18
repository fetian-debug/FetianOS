"""Opt-in GTK smoke test. Run under Xvfb with an isolated HOME and D-Bus session."""
import os
from pathlib import Path
import sys
import tempfile
import time
import subprocess

if os.environ.get("FETIAN_GTK_TEST") != "1":
    sys.exit("Set FETIAN_GTK_TEST=1 and run under a disposable display/session")

temporary = tempfile.TemporaryDirectory(prefix="fetian-gtk-")
home = Path(temporary.name)
for key, folder in (("HOME", "home"), ("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache")):
    path = home / folder; path.mkdir(); os.environ[key] = str(path)
os.environ["GSETTINGS_BACKEND"] = "memory"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/fetian-files"))
import fetian_files as files
from gi.repository import Gio, GLib, Gtk
files.gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf


def pump(predicate=lambda: True, timeout=8):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        while GLib.MainContext.default().pending(): GLib.MainContext.default().iteration(False)
        if predicate(): return
        time.sleep(0.01)
    raise AssertionError("GTK asynchronous operation timed out")


source = home / "folder"; source.mkdir()
(source / "hello.txt").write_text("FetianFiles مرحبا\n")
(source / ".hidden").write_text("hidden")
(source / "child").mkdir()
app = files.FilesApplication([]); app.register(None)
window = files.FilesWindow(app, [Gio.File.new_for_path(str(source))]); window.present()
pump(lambda: not window.jobs)
assert len(window.active.entries) == 2, window.status.get_text()
for mode in ("Grid", "Compact", "List"): window.set_view(mode)
window.hidden.set_active(True); pump(lambda: not window.jobs)
assert len(window.active.entries) == 3
pane = window.active
row = next(row for row in files.list_children(pane.list) if row.entry["info"].get_name() == "hello.txt")
pane.list.select_row(row); pump(lambda: not window.jobs)
assert "مرحبا" in window.preview.get_buffer().get_text(window.preview.get_buffer().get_start_iter(), window.preview.get_buffer().get_end_iter(), True)
window.clip(False)
target = home / "target"; target.mkdir()
pane.navigate(Gio.File.new_for_path(str(target))); pump(lambda: not window.jobs)
window.paste(); pump(lambda: not window.jobs)
assert (target / "hello.txt").read_text() == "FetianFiles مرحبا\n", window.status.get_text()
# Test real text/uri-list deserialization through the native clipboard API.
external_target = home / "external-target"; external_target.mkdir()
pane.navigate(Gio.File.new_for_path(str(external_target))); pump(lambda: not window.jobs)
window.clipboard = []; window.paste()
pump(lambda: (external_target / "hello.txt").exists())
pump(lambda: not window.jobs)
window.theme.set_selected(2); window.motion.set_active(True)
assert Gtk.Settings.get_default().get_property("gtk-application-prefer-dark-theme")
window.theme.set_selected(1); window.theme.set_selected(0)
window.preview_toggle.set_active(False); assert not window.preview_scroll.get_visible()
window.preview_toggle.set_active(True)
window.bookmark(); assert window.state["bookmarks"]
window.split(); pump(lambda: not window.jobs); window.split()
window.new_tab(Gio.File.new_for_path(str(source))); pump(lambda: not window.jobs)
assert window.tabs.get_n_pages() == 2
window.close_tab(); assert window.tabs.get_n_pages() == 1
window.search.set_text("hello"); window.search_files(window.search); pump(lambda: not window.jobs)
assert len(window.active.entries) == 1
Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)
assert window.get_direction() == Gtk.TextDirection.RTL
window.location.grab_focus()
assert not window.key(None, files.Gdk.KEY_Delete, 0, files.Gdk.ModifierType(0))
class FailedVolume:
    def mount(self, flags, operation, cancellable, callback):
        assert flags == Gio.MountMountFlags.NONE; callback(self, None)
    def mount_finish(self, _result): raise GLib.Error("MTP disconnected (test provider)")
class BusyMount:
    def unmount_with_operation(self, flags, operation, cancellable, callback):
        assert flags == Gio.MountUnmountFlags.NONE; callback(self, None)
    def unmount_with_operation_finish(self, _result): raise GLib.Error("Device busy (test provider)")
window.mount(FailedVolume()); assert "MTP disconnected" in window.status.get_text()
window.unmount(BusyMount()); assert "Device busy" in window.status.get_text()
class BusyEject:
    def eject_with_operation(self, flags, operation, cancellable, callback):
        assert flags == Gio.MountUnmountFlags.NONE; callback(self, None)
    def eject_with_operation_finish(self, _result): raise GLib.Error("Eject refused (test provider)")
window.unmount(BusyEject(), eject=True); assert "Eject refused" in window.status.get_text()
class FailedRemote:
    def get_path(self): return None
    def mount_enclosing_volume(self, flags, operation, cancellable, callback):
        assert flags == Gio.MountMountFlags.NONE; callback(self, None)
    def mount_enclosing_volume_finish(self, _result): raise GLib.Error("Authentication failed (test provider)")
window.connect_location(FailedRemote()); assert "Authentication failed" in window.status.get_text()
assert not window.mount_requests
class DisconnectedFile:
    def get_path(self): return None
    def get_basename(self): return "phone-file"
    def copy(self, *_args): raise GLib.Error("MTP disconnected (test provider)")
window.transfer([DisconnectedFile()], Gio.File.new_for_path(str(target)))
pump(lambda: not window.jobs); assert "Completed 0" in window.status.get_text()
# GIO local Trash writes only beneath the temporary XDG_DATA_HOME.
trash_source = source / "trash-me.txt"; trash_source.write_text("restore this")
trash_file = Gio.File.new_for_path(str(trash_source))
window.active.selected = lambda: [{"file": trash_file}]
window.confirm = lambda _title, _text, callback: callback()  # Explicit test approval.
window.trash(); pump(lambda: not window.jobs)
assert not trash_source.exists(), window.status.get_text()
trashed = next((home / "data/Trash/files").glob("trash-me*"))
info = Gio.FileInfo(); info.set_attribute_byte_string("trash::orig-path", str(trash_source))
window.active.selected = lambda: [{"file": Gio.File.new_for_path(str(trashed)), "info": info}]
window.restore(); pump(lambda: not window.jobs)
assert trash_source.read_text() == "restore this", window.status.get_text()
image = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 20, 10); image.fill(0x54b0ffff)
image_path = source / "preview.png"; image.savev(str(image_path), "png", [], [])
file = Gio.File.new_for_path(str(image_path)); info = file.query_info(files.ATTRIBUTES, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, None)
window.active.selected = lambda: [{"file": file, "info": info}]
window.preview_selection(); pump(lambda: not window.jobs)
assert window.preview_stack.get_visible_child_name() == "image", window.status.get_text()
assert window.picture.get_paintable().get_intrinsic_width() == 20
bad = source / "unsafe.svg"; bad.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
result = subprocess.run([sys.executable, str(Path(files.__file__).with_name("image_preview.py")), str(bad)], text=True, capture_output=True)
assert result.returncode != 0 and "PNG, JPEG" in result.stderr
if os.environ.get("FETIAN_GTK_SCREENSHOT"):
    # Allow a frame to reach Xvfb, then capture that test display only.
    time.sleep(0.2); pump()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "x11grab", "-video_size", "1280x1024", "-i", os.environ["DISPLAY"], "-frames:v", "1", "-y", os.environ["FETIAN_GTK_SCREENSHOT"]], check=True)
try: files.safe_location("smb://user:secret@example/share")
except ValueError: pass
else: raise AssertionError("Embedded password accepted")
window.cancel_jobs(); window.close(); pump()
print("GTK smoke passed: listing, hidden files, text/Arabic preview, bounded raster thumbnail, native URI clipboard, Trash/restore, views, split, tabs, search, themes, reduced motion, bookmarks, RTL, editable-key and URI guards. Device/disconnect errors: fake providers only.")
temporary.cleanup()
