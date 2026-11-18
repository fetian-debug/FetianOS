import importlib.util
import configparser
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


release = load("release", "scripts/release-artifacts.py")
selector = load("selector", "scripts/select-iso.py")
policy = load("policy", "system/boot/image_policy.py")
artifacts = load("artifacts", "scripts/verify-boot-artifacts.py")
installed = load("installed", "scripts/verify-installed.py")
vm = load("vm", "scripts/vm-test.py")
guest = load("guest_audit", "system/boot/session_audit.py")


def write(root, name, text="fixture", mode=0o644):
    path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text); path.chmod(mode)
    return path


class ReleaseTests(unittest.TestCase):
    def fixture(self, root):
        write(root, "source/Cargo.toml")
        write(root, "profile/profiledef.sh")
        write(root, "rootfs/var/lib/pacman/local/test-1/desc", "%NAME%\ntest\n\n%VERSION%\n1-1\n\n%LICENSE%\nMIT\n\n")
        return write(root, "image.iso", "not a real ISO; fixture only")

    def test_publication_is_complete_and_fixture_never_claims_image_validation(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(release, "tool_versions", return_value={}):
            root = Path(temporary); iso = self.fixture(root)
            output = release.publish(iso, root / "output", root / "source", root / "profile", root / "rootfs", "sway", lambda *_: "fixture")
            data = json.loads((output / "build.json").read_text())
            self.assertFalse(data["verification"]["image_static_checks"])
            self.assertFalse(data["verification"]["reproducible"])
            self.assertEqual(data["packages"]["test"]["licenses"], ["MIT"])
            self.assertEqual((output / "image.iso.sha256").read_text(), release.digest(iso) + "  image.iso\n")
            self.assertFalse(list((root / "output").glob(".candidate-*")))
            with self.assertRaises(ValueError): selector.select(root / "output")

    def test_validator_failure_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); iso = self.fixture(root)
            def fail(*_): raise ValueError("invalid image")
            with self.assertRaises(ValueError): release.publish(iso, root / "output", root / "source", root / "profile", root / "rootfs", "sway", fail)
            self.assertFalse((root / "output").exists())

    def test_compare_checks_actual_bytes_and_requires_distinct_builds(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(release, "tool_versions", return_value={}):
            root = Path(temporary); iso = self.fixture(root)
            def publish(): return release.publish(iso, root / "output", root / "source", root / "profile", root / "rootfs", "sway", lambda *_: "fixture") / "build.json"
            first, second = publish(), publish()
            result = release.compare(first, second)
            self.assertTrue(result["iso_bytes_identical"]); self.assertTrue(result["recorded_inputs_match"])
            self.assertTrue(result["independent_execution_attestation_required"])
            with self.assertRaises(ValueError): release.compare(first, first)
            (second.parent / "image.iso").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "does not match"): release.compare(first, second)

    def test_missing_package_inventory_or_license_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError): release.installed_packages(root)
            write(root, "var/lib/pacman/local/a/desc", "%NAME%\na\n\n%VERSION%\n1\n")
            with self.assertRaisesRegex(ValueError, "license"): release.installed_packages(root)

    def test_version_queries_record_status_and_use_tool_specific_options(self):
        def query(arguments, **kwargs): return subprocess.CompletedProcess(arguments, 0, "fixture version", "")
        with patch.object(release.subprocess, "run", side_effect=query):
            versions = release.tool_versions()
            self.assertEqual(versions["mkarchiso"]["query"], ["mkarchiso", "-V"])
            self.assertEqual(versions["mksquashfs"]["query"], ["mksquashfs", "-version"])
            self.assertEqual(versions["rustc"]["exit_code"], 0)

    def test_source_fingerprint_tracks_symlinks_and_excludes_caches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); write(root, "file"); write(root, "__pycache__/file")
            (root / "link").symlink_to("file")
            result = release.tree_manifest(root)
            self.assertEqual(result["link"], {"link": "file"}); self.assertEqual(len(result), 2)

    def test_selector_ignores_incomplete_hidden_and_unsafe_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for folder, name in ((".candidate-x", "a.iso"), ("unsafe", "../a.iso"), ("complete", "a.iso")):
                write(root, folder + "/build.json", json.dumps({"iso": {"file": name}, "verification": {"image_static_checks": True}}))
                write(root, folder + "/a.iso"); write(root, folder + "/a.iso.sha256")
            self.assertEqual(selector.select(root), root / "complete/a.iso")

    def test_qemu_checksum_and_command_never_attach_host_drives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); iso = write(root, "image.iso")
            write(root, "image.iso.sha256", release.digest(iso) + "  image.iso\n")
            self.assertEqual(vm.checked_iso(iso)[0], iso)
            args = vm.command(root, root / "code.fd", root / "vars.fd", iso, "none", "tcg")
            self.assertIn("if=pflash,format=raw,readonly=on,file=" + str(root / "code.fd"), args)
            self.assertIn("file=" + str(root / "disk.qcow2") + ",format=qcow2,if=virtio", args)
            self.assertIn("-monitor", args); self.assertNotIn("-hda", args)
            self.assertNotIn("-cdrom", vm.command(root, root / "code.fd", root / "vars.fd", None, "none", "tcg"))
            iso.write_text("tampered")
            with self.assertRaises(ValueError): vm.checked_iso(iso)
            with self.assertRaises(ValueError): vm.command(root / "comma,path", root / "code", root / "vars", None, "none", "tcg")

    def test_resume_rejects_external_disk(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError): vm.disk_path(Path(temporary))

    def test_qemu_qmp_uses_structured_commands(self):
        # Device interaction remains a VM acceptance task; this checks the
        # workflow's authority boundary, not a simulated boot success.
        source = (ROOT / "scripts/vm-test.py").read_text()
        self.assertNotIn("/dev/sd", source); self.assertNotIn("hostfwd", source)
        self.assertIn('"installation_validated": False', source)


class ImagePolicyTests(unittest.TestCase):
    def test_application_desktop_entries_have_unix_line_endings(self):
        for folder in ("apps", "desktop", "system", "profile"):
            for path in (ROOT / folder).rglob("*.desktop"):
                with self.subTest(path=str(path)): self.assertNotIn(b"\r", path.read_bytes())
    def test_sddm_session_entries_preserve_desktop_names_and_absolute_wrappers(self):
        entries = list((ROOT / "system/boot/airootfs/usr/share/wayland-sessions").glob("*.desktop"))
        entries += list((ROOT / "desktop/hyprland/airootfs/usr/share/wayland-sessions").glob("*.desktop"))
        self.assertEqual(len(entries), 3)
        for path in entries:
            with self.subTest(path=str(path)):
                config = configparser.ConfigParser(interpolation=None); config.read(path)
                entry = config["Desktop Entry"]
                name = "hyprland" if path.name == "fetianos-hyprland.desktop" else "sway"
                self.assertEqual(entry["Type"], "Application")
                self.assertEqual(entry["Exec"], "/usr/bin/fetian-" + name + "-session")
                self.assertEqual(entry["DesktopNames"].lower(), name)
                self.assertTrue(entry["TryExec"].startswith("/usr/bin/"))
    def fixture(self, root):
        write(root, "etc/fetian/application-image-build")
        write(root, "etc/pacman.d/hooks/99-zzyy-fetian-applications.hook")
        write(root, "usr/share/fetian/applications.json", (ROOT / "manifests/applications.json").read_text())
        write(root, "usr/share/applications/vendor-installer.desktop", "[Desktop Entry]\nExec=pkexec /usr/bin/calamares %f\n")
        write(root, "usr/share/applications/thunar.desktop", "[Desktop Entry]\nExec=thunar %U\n")

    def test_installer_hidden_without_deleting_apps_or_backend_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            self.assertTrue(policy.apply_policy(root))
            self.assertTrue((root / "usr/share/applications/vendor-installer.desktop").exists())
            self.assertIn("Hidden=true", (root / "usr/local/share/applications/vendor-installer.desktop").read_text())
            self.assertFalse((root / "usr/local/share/applications/thunar.desktop").exists())
            self.assertEqual(json.loads((root / "usr/share/fetian/applications-audit.json").read_text())["packages_removed"], [])
            self.assertFalse(policy.apply_policy(root))

    def test_unverified_promotion_fails_and_retains_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            path = root / "usr/share/fetian/applications.json"; data = json.loads(path.read_text()); data["installer"]["enabled"] = True; path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): policy.apply_policy(root)
            self.assertTrue((root / "etc/fetian/application-image-build").exists())

    def test_iso_requires_real_x64_efi_and_squashfs(self):
        entry = "linux /kernel\ninitrd /initrd\noptions archisobasedir=fetianos\n"
        binary = bytearray(100); binary[:2] = b"MZ"; struct.pack_into("<I", binary, 0x3c, 64); binary[64:68] = b"PE\0\0"; struct.pack_into("<H", binary, 68, 0x8664)
        names = ["/kernel", "/initrd", "/loader/entries/01.conf", "/EFI/BOOT/BOOTx64.EFI", "/fetianos/x86_64/airootfs.sfs"]
        def run(args, **kwargs):
            value = "\n".join(names) if "-f" in args else entry if args[-1].endswith(".conf") else bytes(binary)
            return subprocess.CompletedProcess(args, 0, value)
        artifacts.verify_iso(Path("fixture.iso"), run)
        binary[64:68] = b"fake"
        with self.assertRaises(ValueError): artifacts.verify_iso(Path("fixture.iso"), run)
        names.pop()
        with self.assertRaises(ValueError): artifacts.verify_iso(Path("fixture.iso"), run)

    def test_target_symlinks_are_resolved_inside_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); write(root, "usr/lib/service"); (root / "link").symlink_to("/usr/lib/service")
            self.assertEqual(artifacts.rooted(root, "link"), root / "usr/lib/service")
            (root / "escape").symlink_to("../outside")
            with self.assertRaises(ValueError): artifacts.rooted(root, "escape")
            (root / "loop").symlink_to("loop")
            with self.assertRaises(ValueError): artifacts.rooted(root, "loop")

    def test_complete_image_rejects_usable_credentials_and_build_machine_identity(self):
        # These checks precede promotion and service validation, so a broken
        # security boundary is rejected without needing real distro packages.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("fetian-health-rs", "fetian-control-center", "fetian-sway-session"):
                write(root, "usr/bin/" + name, mode=0o755)
            write(root, "usr/lib/fetian/display-manager", mode=0o755)
            write(root, "etc/xdg/mimeapps.list", "[Default Applications]\ntext/html=firefox.desktop\n")
            write(root, "usr/share/applications/firefox.desktop")
            write(root, "etc/passwd", "root:x:0:0:root:/root:/bin/bash\n")
            write(root, "etc/shadow", "root:$6$shared$hash:1:0:99999:7:::\n")
            with self.assertRaisesRegex(ValueError, "locked"): artifacts.verify_rootfs(root, complete=True)
            write(root, "etc/shadow", "root:!:1:0:99999:7:::\n")
            write(root, "etc/machine-id", "1234567890abcdef1234567890abcdef")
            with self.assertRaisesRegex(ValueError, "machine identity"): artifacts.verify_rootfs(root, complete=True)


class InstalledPolicyTests(unittest.TestCase):
    def fixture(self, root):
        files = {"etc/fetian/installed.json": json.dumps({"kind": "fetian-installed", "username": "alice"}),
                 "etc/passwd": "root:x:0:0:root:/root:/bin/bash\nalice:x:1000:1000:Alice:/home/alice:/bin/bash\n",
                 "etc/shadow": "root:!:1:0:99999:7:::\nalice:$6$fixture$not-a-real-password-hash:1:0:99999:7:::\n",
                 "etc/group": "wheel:x:998:alice\n", "etc/shells": "/bin/bash\n",
                 "etc/sudoers": "root ALL=(ALL:ALL) ALL\n@includedir /etc/sudoers.d\n", "etc/sudoers.d/10-installer": "%wheel ALL=(ALL:ALL) ALL\n",
                 "etc/mkinitcpio.conf": "HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block filesystems fsck)\n",
                 "etc/fstab": "UUID=fixture / ext4 defaults 0 1\n", "etc/machine-id": "1234567890abcdef1234567890abcdef\n",
                 "usr/share/wayland-sessions/fetianos-sway.desktop": "fixture", "usr/bin/fetian-sway-session": "fixture",
                 "etc/systemd/system/display-manager.service": "fixture", "boot/grub/grub.cfg": "fixture"}
        for name, text in files.items(): write(root, name, text, 0o600 if name == "etc/shadow" else 0o644)

    def test_clean_fixture_passes_static_checks_without_claiming_boot_or_auth(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root); result = installed.validate(root, "alice")
            self.assertTrue(result["static_policy_passed"]); self.assertFalse(result["installed_reboot_tested"])
            self.assertFalse(result["password_authentication_tested"])

    def test_live_state_credentials_autologin_and_initramfs_are_rejected(self):
        mutations = [("etc/sudoers.d/90-fetian-live", "fetian ALL=(ALL) ALL"),
                     ("etc/sddm.conf.d/autologin.conf", "[Autologin]\nUser=alice\n"),
                     ("etc/shadow", "root::1:0:99999:7:::\n"),
                     ("etc/shadow", "root:!:1:0:99999:7:::\nfetian:!:1:0:99999:7:::\n"),
                     ("etc/passwd", "root:x:0:0:root:/root:/bin/bash\nfetian:x:1000:1000::/home/fetian:/bin/bash\n"),
                     ("etc/mkinitcpio.conf", "HOOKS=(base archiso filesystems)"),
                     ("etc/sudoers.d/99-bad", "%wheel ALL=(ALL) NOPASSWD: ALL"),
                     ("etc/fstab", "/dev/sda1 / ext4 defaults 0 1\n"),
                     ("etc/machine-id", "0" * 32)]
        for name, text in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); self.fixture(root); write(root, name, text, 0o600)
                with self.assertRaises(ValueError): installed.validate(root, "alice")

    def test_missing_provenance_or_live_username_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.fixture(root)
            for user in ("root", "fetian", "live", "../alice"):
                with self.assertRaises(ValueError): installed.validate(root, user)
            (root / "etc/fetian/installed.json").unlink()
            with self.assertRaises(OSError): installed.validate(root, "alice")


class GuestEvidenceTests(unittest.TestCase):
    def test_guest_facts_do_not_claim_manual_or_hardware_acceptance(self):
        from types import SimpleNamespace
        def command(arguments):
            return {"available": True, "exit_code": 0, "stdout": '{"schema_version": 1}' if arguments[0] == "fetian-health-rs" else "active", "stderr": ""}
        with patch.object(guest, "is_live", return_value=True), patch.object(guest.os, "getuid", return_value=1000), patch.object(guest.pwd, "getpwuid", return_value=SimpleNamespace(pw_name="fetian")), patch.object(guest.Path, "is_file", return_value=True), patch.object(guest, "command", side_effect=command):
            result = guest.collect("live", "sway")
            self.assertTrue(result["observed_checks_passed"])
            self.assertFalse(result["hardware_validated"]); self.assertFalse(result["installation_validated"])
            self.assertIn("lock/unlock", result["not_tested"])
            self.assertFalse(guest.collect("installed", "text")["observed_checks_passed"])


if __name__ == "__main__": unittest.main()
