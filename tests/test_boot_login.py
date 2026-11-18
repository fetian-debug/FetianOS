import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


live = load("live_setup", "system/boot/live_setup.py")
boot = load("build_live_initramfs", "system/boot/build_live_initramfs.py")
artifacts = load("verify_boot_artifacts", "scripts/verify-boot-artifacts.py")


class Commands:
    def __init__(self, fail=None):
        self.user = False
        self.calls = []
        self.fail = fail

    def __call__(self, arguments, input=None, **kwargs):
        self.calls.append((arguments, input))
        program = Path(arguments[0]).name
        if program == self.fail:
            if os.name == "nt" and program == "visudo":
                # Linux unlink permissions apply to the directory, unlike the
                # Windows read-only attribute set by chmod(0440).
                Path(arguments[-1]).chmod(0o600)
            return subprocess.CompletedProcess(arguments, 1, "", "not logged")
        if program == "getent":
            return subprocess.CompletedProcess(arguments, 0 if self.user else 2,
                                               "fetian:x:1001:1001:Live:/home/fetian:/bin/bash\n" if self.user else "", "")
        if program == "useradd":
            self.user = True
        return subprocess.CompletedProcess(arguments, 0, "", "")


class LiveLoginTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "proc").mkdir()
        (self.root / "run").mkdir()
        (self.root / "proc/cmdline").write_text("archisobasedir=fetianos console=tty0")
        (self.root / "proc/mounts").write_text("overlay / overlay rw 0 0\n/dev/loop0 /run/archiso/bootmnt iso9660 ro 0 0\n")
        self.owner = self.root.stat().st_uid
        self.commands = Commands()

    def tearDown(self):
        self.temporary.cleanup()

    def test_installed_system_is_never_modified(self):
        for commandline, mounts in (("root=UUID=installed", "overlay / overlay rw 0 0"),
                                   ("archisobasedir=fetianos", "/dev/sda / ext4 rw 0 0"),
                                   ("archisobasedir=fetianos", "overlay / overlay rw 0 0")):
            (self.root / "proc/cmdline").write_text(commandline)
            (self.root / "proc/mounts").write_text(mounts)
            self.assertFalse(live.provision(self.root, self.commands, self.owner))
        self.assertEqual(self.commands.calls, [])
        self.assertFalse((self.root / "run/fetian").exists())

    def test_first_live_boot_and_idempotent_restart(self):
        self.assertTrue(live.provision(self.root, self.commands, self.owner))
        config = (self.root / "run/fetian/sddm-live.conf").read_text()
        self.assertIn("Session=fetianos-sway.desktop", config)
        self.assertIn("Relogin=false", config)
        self.assertTrue(json.loads((self.root / "run/fetian/live-user.json").read_text())["ready"])
        self.assertNotIn("NOPASSWD", (self.root / "etc/sudoers.d/90-fetian-live").read_text())
        initial_mutations = [a for a, _ in self.commands.calls if Path(a[0]).name != "getent"]
        self.assertTrue(live.provision(self.root, self.commands, self.owner))
        self.assertEqual(initial_mutations, [a for a, _ in self.commands.calls if Path(a[0]).name != "getent"])

    def test_existing_account_is_never_reset(self):
        self.commands.user = True
        with self.assertRaisesRegex(RuntimeError, "not owned"):
            live.provision(self.root, self.commands, self.owner)
        self.assertEqual(len(self.commands.calls), 1)

    def test_existing_home_is_never_overwritten(self):
        (self.root / "home/fetian").mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            live.provision(self.root, self.commands, self.owner)
        self.assertFalse(self.commands.user)

    def test_failed_password_setup_never_enables_autologin(self):
        commands = Commands(fail="chpasswd")
        with self.assertRaisesRegex(RuntimeError, "chpasswd failed"):
            live.provision(self.root, commands, self.owner)
        self.assertFalse((self.root / "run/fetian/sddm-live.conf").exists())

    def test_bad_sudoers_never_enables_autologin(self):
        commands = Commands(fail="visudo")
        with self.assertRaisesRegex(RuntimeError, "visudo failed"):
            live.provision(self.root, commands, self.owner)
        self.assertFalse((self.root / "etc/sudoers.d/90-fetian-live").exists())
        self.assertFalse((self.root / "run/fetian/sddm-live.conf").exists())

    def test_changed_runtime_login_config_is_not_overwritten(self):
        live.provision(self.root, self.commands, self.owner)
        config = self.root / "run/fetian/sddm-live.conf"
        config.write_text("[Autologin]\nUser=someone-else\n")
        with self.assertRaisesRegex(RuntimeError, "changed live login"):
            live.provision(self.root, self.commands, self.owner)
        self.assertIn("someone-else", config.read_text())

    def test_malformed_provisioning_state_is_rejected(self):
        state = self.root / "run/fetian"
        state.mkdir(mode=0o700 if os.name == "posix" else 0o755)
        (state / "live-user.json").write_text('{"uid": 1001, "ready": "true"}')
        self.commands.user = True
        with self.assertRaisesRegex(RuntimeError, "Invalid live provisioning state"):
            live.provision(self.root, self.commands, self.owner)
        self.assertEqual(len(self.commands.calls), 1)


class BootArtifactTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "Image executable permissions require Linux")
    def test_built_payload_rejects_leaked_live_state_and_missing_default_apps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("usr/bin/fetian-health-rs", "usr/bin/fetian-control-center", "usr/bin/fetian-sway-session", "usr/lib/fetian/display-manager"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
                path.chmod(0o755)
            preferences = root / "etc/xdg/mimeapps.list"
            preferences.parent.mkdir(parents=True)
            preferences.write_text("[Default Applications]\ntext/html=firefox.desktop\n")
            with self.assertRaisesRegex(ValueError, "desktop entry missing"):
                artifacts.verify_rootfs(root)
            desktop = root / "usr/share/applications/firefox.desktop"
            desktop.parent.mkdir(parents=True)
            desktop.touch()
            artifacts.verify_rootfs(root)
            marker = root / "etc/fetian/image-build"
            marker.parent.mkdir()
            marker.touch()
            with self.assertRaisesRegex(ValueError, "unfinished build"):
                artifacts.verify_rootfs(root)
    def image_fixture(self, directory):
        root = Path(directory)
        for path in ("etc/fetian/image-build", "etc/pacman.d/hooks/99-zz-fetian-live-boot.hook",
                     "etc/mkinitcpio.conf.d/fetian-live.conf", "usr/lib/modules/7.2.9-test/kernel/test.ko",
                     "boot/vmlinuz-7.2-x86_64"):
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"fixture")
        return root

    def test_hook_uses_image_kernel_and_removes_build_only_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.image_fixture(directory)
            commands = []
            def run(arguments, **kwargs):
                commands.append(arguments)
                if arguments[0].endswith("pacman"):
                    return subprocess.CompletedProcess(arguments, 0, "/usr/lib/modules/7.2.9-test/kernel/test.ko\n/boot/vmlinuz-7.2-x86_64\n", "")
                (root / "boot/initramfs-fetian.img").write_bytes(b"generated fixture")
                return subprocess.CompletedProcess(arguments, 0)
            self.assertTrue(boot.build(root, run))
            self.assertEqual((root / "boot/vmlinuz-fetian").read_bytes(), b"fixture")
            self.assertIn("7.2.9-test", commands[1])
            for path in ("etc/fetian/image-build", "etc/pacman.d/hooks/99-zz-fetian-live-boot.hook", "etc/mkinitcpio.conf.d/fetian-live.conf"):
                self.assertFalse((root / path).exists())

    def test_failed_image_generation_retains_build_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.image_fixture(directory)
            def run(arguments, **kwargs):
                if arguments[0].endswith("pacman"):
                    return subprocess.CompletedProcess(arguments, 0, "/usr/lib/modules/7.2.9-test/kernel/test.ko\n/boot/vmlinuz-7.2-x86_64\n", "")
                raise subprocess.CalledProcessError(1, arguments)
            with self.assertRaises(subprocess.CalledProcessError):
                boot.build(root, run)
            self.assertTrue((root / "etc/fetian/image-build").exists())
    def test_uefi_entries_must_reference_both_real_artifacts(self):
        entry = "linux /fetianos/boot/x86_64/vmlinuz-fetian\ninitrd /fetianos/boot/x86_64/initramfs-fetian.img\noptions archisobasedir=fetianos\n"
        files = {"/fetianos/boot/x86_64/vmlinuz-fetian", "/fetianos/boot/x86_64/initramfs-fetian.img"}
        artifacts.validate({"01.conf": entry}, files)
        with self.assertRaises(ValueError):
            artifacts.validate({"01.conf": entry}, {"/fetianos/boot/x86_64/vmlinuz-fetian"})
        with self.assertRaises(ValueError):
            artifacts.validate({"02-recovery.conf": entry}, files)
        with self.assertRaises(ValueError):
            artifacts.validate({}, files)

    def test_uefi_rejects_unexpanded_placeholders_and_traversal(self):
        for path in ("/%INSTALL_DIR%/vmlinuz", "/../boot/vmlinuz"):
            with self.assertRaises(ValueError):
                artifacts.validate({"01.conf": f"linux {path}\ninitrd /initrd\noptions archisobasedir=fetianos"}, {path, "/initrd"})

    def test_selects_package_kernel_and_module_version_not_host_kernel(self):
        version, path = boot.select_kernel([PurePosixPath("/usr/lib/modules/7.2.9-1-MANJARO/kernel/x.ko"),
                                           PurePosixPath("/usr/lib/modules/extramodules-7.2-MANJARO/version"),
                                           PurePosixPath("/boot/vmlinuz-7.2-x86_64")])
        self.assertEqual(version, "7.2.9-1-MANJARO")
        self.assertEqual(str(path), "/boot/vmlinuz-7.2-x86_64")

    def test_ambiguous_or_missing_kernel_is_rejected(self):
        for paths in ([], ["/boot/vmlinuz-a"], ["/usr/lib/modules/a/a.ko", "/usr/lib/modules/b/b.ko", "/boot/vmlinuz-a"],
                      ["/usr/lib/modules/a/a.ko", "/boot/vmlinuz-a", "/boot/vmlinuz-b"]):
            with self.assertRaises(ValueError):
                boot.select_kernel([PurePosixPath(p) for p in paths])

    def test_image_hook_is_inert_without_build_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            commands = Commands()
            self.assertFalse(boot.build(Path(directory), commands))
            self.assertEqual(commands.calls, [])
