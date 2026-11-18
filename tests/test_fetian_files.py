import errno
import gzip
import importlib.util
import io
import lzma
import os
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/fetian-files"))
import fileops
import archiveops
import preferences


@unittest.skipUnless(sys.platform == "linux", "Descriptor-relative file operations require Linux")
class FilesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fetian-files-test-")
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"; self.source.mkdir()
        self.target = self.root / "target"; self.target.mkdir()
        (self.source / "hello.txt").write_text("Hello العربية", encoding="utf-8")
    def tearDown(self): self.temporary.cleanup()
    def test_batch_rename_conflicts_and_cancellation_roll_back(self):
        first = self.source / "hello.txt"; second = self.source / "two.txt"; second.write_text("two")
        receipts = fileops.batch_rename([first, second], "{n}-{stem}{suffix}")
        self.assertEqual(len(receipts), 2); self.assertTrue((self.source / "1-hello.txt").exists())
        for receipt in reversed(receipts): fileops.undo_move(receipt)
        with self.assertRaises(ValueError): fileops.batch_rename([first, second], "same")
        with self.assertRaises(ValueError): fileops.batch_rename([first], "{name.__class__}")
        with self.assertRaises(FileExistsError): fileops.batch_rename([first], "two.txt")
        token = fileops.Token(); original = fileops.move
        def interrupt(*args, **kwargs):
            receipt = original(*args, **kwargs); token.cancel(); return receipt
        with patch.object(fileops, "move", side_effect=interrupt), self.assertRaisesRegex(RuntimeError, "Rollback incomplete for 0"):
            fileops.batch_rename([first, second], "renamed-{name}", token)
        self.assertTrue(first.exists()); self.assertTrue(second.exists())
    def test_permission_editor_rejects_links_and_special_bits(self):
        path = self.source / "hello.txt"; fileops.permissions(path, 0o640)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
        alias = self.source / "alias"; alias.symlink_to(path)
        with self.assertRaises(ValueError): fileops.permissions(alias, 0o777)
        with self.assertRaises(ValueError): fileops.permissions(path, 0o4755)
    def test_search_filters_type_size_and_modification(self):
        (self.source / "folder").mkdir()
        paths, _ = fileops.search(self.source, "", kind="file", minimum=1, maximum=100)
        self.assertEqual(paths, [str(self.source / "hello.txt")])
        paths, _ = fileops.search(self.source, "", kind="folder")
        self.assertEqual(paths, [str(self.source / "folder")])
        self.assertEqual(fileops.search(self.source, "", modified_after=10**12)[0], [])
        with self.assertRaises(ValueError): fileops.search(self.source, "", minimum=100, maximum=1)
    def test_preferences_are_private_bounded_and_omit_credentials(self):
        path = self.root / "config/state.json"
        preferences.save({"bookmarks": ["smb://user:secret@server/share", "smb://server/share", "file:///tmp", "sftp://host/path?secret=1"], "tabs": ["/tmp", "relative"], "theme": "Dark"}, path)
        state = preferences.load(path)
        self.assertEqual(state["bookmarks"], ["smb://server/share", "file:///tmp"])
        self.assertEqual(state["tabs"], ["/tmp"]); self.assertEqual(state["theme"], "Dark")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        path.write_text("x" * 65537); self.assertEqual(preferences.load(path)["bookmarks"], [])
        path.unlink(); path.symlink_to(self.source / "hello.txt")
        self.assertEqual(preferences.load(path)["tabs"], [])
    def test_copy_and_conflict_preserve_both_files(self):
        source, target = self.source / "hello.txt", self.target / "hello.txt"
        fileops.copy(source, target)
        self.assertEqual(target.read_bytes(), source.read_bytes())
        target.write_text("keep")
        with self.assertRaises(FileExistsError): fileops.copy(source, target)
        self.assertEqual(target.read_text(), "keep")
        self.assertFalse(list(self.target.glob(".fetian-job-*")))
    def test_recursive_copy_preserves_links_without_following_them(self):
        outside = self.root / "outside"; outside.write_text("private")
        (self.source / "link").symlink_to(outside)
        fileops.copy(self.source, self.target / "copy")
        self.assertTrue((self.target / "copy/link").is_symlink())
        self.assertEqual(outside.read_text(), "private")
    def test_destination_symlink_ancestor_is_rejected(self):
        alias = self.root / "alias"; alias.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(OSError): fileops.copy(self.source / "hello.txt", alias / "new")
        self.assertFalse((self.target / "new").exists())
    def test_self_copy_is_rejected(self):
        with self.assertRaises(ValueError): fileops.copy(self.source, self.source / "nested")
    def test_cancel_does_not_publish_partial_output(self):
        token = fileops.Token()
        with self.assertRaises(fileops.Cancelled):
            fileops.copy(self.source / "hello.txt", self.target / "partial", token, lambda _: token.cancel())
        self.assertFalse((self.target / "partial").exists())
        self.assertFalse(list(self.target.glob(".fetian-job-*")))
    def test_changed_source_does_not_publish_stale_copy(self):
        source = self.source / "hello.txt"
        with self.assertRaises(OSError):
            fileops.copy(source, self.target / "changed", progress=lambda _: source.write_text("changed while copying"))
        self.assertFalse((self.target / "changed").exists())
    def test_move_rename_and_undo_never_overwrite(self):
        source, target = self.source / "hello.txt", self.target / "renamed"
        receipt = fileops.move(source, target)
        self.assertFalse(source.exists()); self.assertTrue(target.exists())
        fileops.undo_move(receipt)
        self.assertTrue(source.exists()); self.assertFalse(target.exists())
        target.write_text("existing")
        with self.assertRaises(FileExistsError): fileops.move(source, target)
        self.assertEqual(target.read_text(), "existing")
    def test_undo_refuses_a_replaced_target(self):
        target = self.target / "renamed"
        receipt = fileops.move(self.source / "hello.txt", target)
        replacement = self.target / "replacement"; replacement.write_text("new")
        os.replace(replacement, target)
        with self.assertRaises(ValueError): fileops.undo_move(receipt)
        self.assertEqual(target.read_text(), "new")
    def test_directory_move_and_cross_device_folder_refusal(self):
        child = self.source / "folder"; child.mkdir()
        fileops.move(child, self.target / "folder")
        with patch.object(fileops, "rename_no_replace", side_effect=OSError(errno.EXDEV, "cross device")):
            with self.assertRaisesRegex(OSError, "Cross-device folder"):
                fileops.move(self.target / "folder", self.source / "folder")
        self.assertTrue((self.target / "folder").exists())
    def test_cross_device_file_move_uses_copy_then_unlink(self):
        real = fileops.rename_no_replace; calls = 0
        def rename(*args):
            nonlocal calls
            calls += 1
            if calls == 1: raise OSError(errno.EXDEV, "cross device")
            return real(*args)
        with patch.object(fileops, "rename_no_replace", side_effect=rename):
            fileops.move(self.source / "hello.txt", self.target / "hello.txt")
        self.assertFalse((self.source / "hello.txt").exists())
        self.assertTrue((self.target / "hello.txt").exists())
    def test_create_and_explicit_delete_do_not_follow_links(self):
        fileops.create(self.target / "new")
        fileops.create(self.target / "folder", folder=True)
        with self.assertRaises(FileExistsError): fileops.create(self.target / "new")
        with self.assertRaises(ValueError): fileops.delete(self.target / "new")
        outside = self.root / "outside"; outside.write_text("keep")
        (self.target / "link").symlink_to(outside)
        fileops.delete(self.target / "link", confirmed=True)
        self.assertTrue(outside.exists())
        fileops.delete(self.target / "folder", confirmed=True)
    def test_preview_is_bounded_plain_text_and_rejects_links_and_pipes(self):
        source = self.source / "hello.txt"
        text, truncated = fileops.preview_text(source, limit=5)
        self.assertEqual(text, "Hello"); self.assertTrue(truncated)
        link = self.source / "link"; link.symlink_to(source)
        with self.assertRaises(OSError): fileops.preview_text(link)
        pipe = self.source / "pipe"; os.mkfifo(pipe)
        with self.assertRaises(ValueError): fileops.preview_text(pipe)
        source.write_bytes(b"binary\0payload")
        with self.assertRaises(ValueError): fileops.preview_text(source)
    def test_search_is_bounded_and_does_not_recurse_into_links(self):
        outside = self.root / "elsewhere"; outside.mkdir(); (outside / "secret.txt").touch()
        (self.source / "link").symlink_to(outside, target_is_directory=True)
        paths, limited = fileops.search(self.source, ".TXT")
        self.assertEqual(paths, [str(self.source / "hello.txt")]); self.assertFalse(limited)
        self.assertTrue(fileops.search(self.source, "", limit=1)[1])
    def test_name_validation(self):
        for value in ("", ".", "..", "a/b", "nul\0x"):
            with self.assertRaises(ValueError): fileops.name(value)
    @unittest.skipIf(os.geteuid() == 0, "Permission behavior requires a regular account")
    def test_permission_denied_is_reported(self):
        self.target.chmod(0o500)
        try:
            with self.assertRaises(PermissionError): fileops.create(self.target / "no")
        finally: self.target.chmod(0o700)


@unittest.skipUnless(sys.platform == "linux", "Secure archive writes require Linux")
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fetian-archive-test-")
        self.root = Path(self.temp.name); self.archive = self.root / "test.zip"
    def tearDown(self): self.temp.cleanup()
    def zip(self, entries):
        with zipfile.ZipFile(self.archive, "w") as output:
            for name, data in entries: output.writestr(name, data)
    def test_zip_create_browse_and_extract_roundtrip(self):
        source = self.root / "source"; source.mkdir()
        (source / "عربي.txt").write_text("test", encoding="utf-8")
        archiveops.create_zip([source], self.archive)
        self.assertTrue(any(item["name"].endswith("عربي.txt") for item in archiveops.listing(self.archive)))
        archiveops.extract(self.archive, self.root / "out")
        self.assertEqual((self.root / "out/source/عربي.txt").read_text(), "test")
    def test_tar_gzip_and_xz_are_supported(self):
        for extension, mode in (("tar", "w"), ("tar.gz", "w:gz"), ("tar.xz", "w:xz")):
            source = self.root / ("test." + extension)
            with tarfile.open(source, mode) as output:
                info = tarfile.TarInfo("./folder/file"); info.size = 4
                output.addfile(info, io.BytesIO(b"test"))
            target = self.root / ("out-" + extension)
            archiveops.extract(source, target)
            self.assertEqual((target / "folder/file").read_bytes(), b"test")
    def test_standalone_gzip_xz_and_actual_expansion_limits(self):
        for suffix, compress in (("gz", gzip.compress), ("xz", lzma.compress)):
            source = self.root / ("hello." + suffix); source.write_bytes(compress(b"hello"))
            self.assertIsNone(archiveops.listing(source)[0]["size"])
            archiveops.extract(source, self.root / suffix)
            self.assertEqual((self.root / suffix / "hello").read_bytes(), b"hello")
            with patch.object(archiveops, "MAX_FILE", 4):
                with self.assertRaises(ValueError): archiveops.extract(source, self.root / (suffix + "-limit"))
            self.assertFalse((self.root / (suffix + "-limit")).exists())
    def test_zip_compression_levels_and_cli_selected_names(self):
        source = self.root / "text"; source.write_text("a" * 10000)
        archiveops.create_zip([source], self.archive, level=0)
        uncompressed = self.archive.stat().st_size; self.archive.unlink()
        archiveops.create_zip([source], self.archive, level=9)
        self.assertLess(self.archive.stat().st_size, uncompressed)
        with self.assertRaises(ValueError): archiveops.create_zip([source], self.root / "bad.zip", level=10)
        import subprocess
        target = self.root / "selected"
        subprocess.run([sys.executable, str(ROOT / "apps/fetian-files/archiveops.py"), "extract", str(self.archive), str(target), "--", "text"], check=True, capture_output=True)
        self.assertEqual((target / "text").read_text(), source.read_text())
    def test_traversal_absolute_windows_and_null_paths_are_rejected(self):
        for path in ("../escape", "/absolute", "a/../../escape", "C:/evil", "a\\..\\evil", "bad\0name"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError): archiveops.parts(path)
        self.zip([("../escape", b"bad")])
        with self.assertRaises(ValueError): archiveops.extract(self.archive, self.root / "out")
        self.assertFalse((self.root / "escape").exists()); self.assertFalse((self.root / "out").exists())
    def test_zip_symlink_and_tar_hardlink_are_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as output:
            info = zipfile.ZipInfo("link"); info.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(info, "/etc/passwd")
        with self.assertRaises(ValueError): archiveops.extract(self.archive, self.root / "out")
        source = self.root / "links.tar"
        with tarfile.open(source, "w") as output:
            info = tarfile.TarInfo("hard"); info.type = tarfile.LNKTYPE; info.linkname = "outside"
            output.addfile(info)
        with self.assertRaises(ValueError): archiveops.extract(source, self.root / "out")
    def test_duplicates_conflicts_and_malformed_archives_preserve_existing_files(self):
        self.zip([("file", b"one"), ("file", b"two")])
        with self.assertRaises(ValueError): archiveops.extract(self.archive, self.root / "out")
        self.zip([("file", b"new")]); target = self.root / "out"; target.mkdir(); (target / "keep").touch()
        with self.assertRaises(FileExistsError): archiveops.extract(self.archive, target)
        self.assertTrue((target / "keep").exists())
        self.archive.write_bytes(b"not an archive")
        with self.assertRaises(ValueError): archiveops.extract(self.archive, self.root / "bad")
    def test_resource_limits_and_cancellation_leave_no_committed_output(self):
        self.zip([("file", b"12345")])
        with patch.object(archiveops, "MAX_FILE", 4):
            with self.assertRaises(ValueError): archiveops.extract(self.archive, self.root / "out")
        token = fileops.Token(); token.cancel()
        with self.assertRaises(fileops.Cancelled): archiveops.extract(self.archive, self.root / "out", token)
        self.assertFalse((self.root / "out").exists())
        self.assertFalse(list(self.root.glob(".fetian-job-*")))
    def test_archive_creation_refuses_links_and_self_inclusion(self):
        link = self.root / "link"; link.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError): archiveops.create_zip([link], self.archive)
        with self.assertRaises(ValueError): archiveops.create_zip([self.root], self.archive)
    def test_selected_extraction(self):
        self.zip([("one", b"1"), ("two", b"2")])
        archiveops.extract(self.archive, self.root / "out", selected=["two"])
        self.assertFalse((self.root / "out/one").exists()); self.assertTrue((self.root / "out/two").exists())
