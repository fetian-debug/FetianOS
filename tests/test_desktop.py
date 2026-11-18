import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


desktop = load("fetian_desktop", "desktop/hyprland/fetian_desktop.py")
stager = load("stage_profile", "scripts/stage-profile.py")
pins = load("hyprland_pins", "scripts/check-hyprland-packages.py")


class DesktopTests(unittest.TestCase):
    def test_ci_compression_is_explicit_and_rejects_unknown_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "health"; binary.write_bytes(b"fixture")
            destination = root / "profile"
            stager.stage(ROOT, destination, "sway", binary, compression="zstd")
            definition = (destination / "profiledef.sh").read_text()
            self.assertIn("'-comp' 'zstd'", definition)
            self.assertTrue((destination / "airootfs/root/customize_airootfs.sh").is_file())
            with self.assertRaises(ValueError): stager.stage(ROOT, root / "invalid", "sway", binary, compression="unsafe")
    def test_unavailable_metrics_are_not_zeroed(self):
        with patch.object(desktop, "health", side_effect=OSError("missing")):
            self.assertEqual(desktop.widget()["text"], "METRICS —")

    def test_metrics_widget_escapes_markup_and_labels_counters(self):
        data = {"schema_version": 1, "cpu_usage_percent": None,
                "memory": {"used_bytes": 512, "total_bytes": 1024}, "uptime_seconds": 42,
                "batteries": [], "temperatures": [{"sensor": "<unsafe>", "celsius": 42}],
                "network": [{"interface": "eth0", "received_bytes": 42, "transmitted_bytes": 10}]}
        with patch.object(desktop, "health", return_value=data):
            widget = desktop.widget()
        self.assertIn("CPU —", widget["text"])
        self.assertIn("RAM 50%", widget["text"])
        self.assertIn("&lt;unsafe&gt;", widget["tooltip"])
        self.assertIn("cumulative", widget["tooltip"])

    def test_unknown_health_schema_fails(self):
        for value in ('{"schema_version": 2}', '[]'):
            with patch.object(desktop, "run", return_value=value):
                with self.assertRaises(ValueError):
                    desktop.health()

    def test_workspace_and_window_selectors_reject_injection(self):
        with patch.object(desktop, "run") as run:
            for value in (True, -1, 0, "1; execute", 2147483648):
                with self.assertRaises(ValueError):
                    desktop.focus_workspace(value)
            for value in ('0x1"; os.execute("bad")', "all", "0x"):
                with self.assertRaises(ValueError):
                    desktop.focus_window(value)
            run.assert_not_called()
            desktop.focus_workspace(3)
            self.assertEqual(run.call_args.args[0], ["hyprctl", "dispatch", "hl.dsp.focus({ workspace = 3 })"])

    def test_effects_profile_persists_only_valid_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_CONFIG_HOME=directory):
            with patch.object(desktop, "run"):
                desktop.set_profile("accessible")
                self.assertEqual(desktop.selected_profile(), "accessible")
                with self.assertRaises(ValueError):
                    desktop.set_profile("../../evil")
                self.assertEqual(desktop.selected_profile(), "accessible")


class ProfileTests(unittest.TestCase):
    def test_staging_preserves_rust_services_and_sway(self):
        watched = [ROOT / "profile/sway/packages.x86_64", ROOT / "system/fetian-system/src/main.rs",
                   ROOT / "profile/sway/airootfs/etc/systemd/system/fetian-health.service"]
        before = [path.read_bytes() for path in watched]
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "native"
            native.write_bytes(b"test fixture")
            stage = Path(directory) / "profile"
            stager.stage(ROOT, stage, "hyprland", native)
            tree = stage / "airootfs"
            for name in ("fetian-health.service", "fetian-health.timer"):
                relative = Path("etc/systemd/system") / name
                self.assertEqual((tree / relative).read_bytes(), (ROOT / "profile/sway/airootfs" / relative).read_bytes())
            self.assertIn("sway", (stage / "packages.x86_64").read_text().splitlines())
            self.assertTrue((tree / "usr/share/wayland-sessions/fetianos-sway.desktop").is_file())
            self.assertTrue((tree / "usr/share/wayland-sessions/fetianos-hyprland.desktop").is_file())
            self.assertEqual((tree / "usr/bin/fetian-health-rs").read_bytes(), b"test fixture")
            for prefix in ("usr/share", "usr/lib"):
                self.assertEqual((tree / prefix / "fetian-control-center/fetian_control_center.py").read_bytes(),
                                 (ROOT / "apps/fetian-control-center/fetian_control_center.py").read_bytes())
            self.assertTrue((tree / "etc/systemd/system/timers.target.wants/fetian-health.timer").is_symlink())
            definition = (stage / "profiledef.sh").read_text(encoding="utf-8")
            self.assertIn('file_permissions["/usr/bin/fetian-health-rs"]="0:0:755"', definition)
            self.assertIn('file_permissions["/usr/lib/fetian/display-manager"]="0:0:755"', definition)
            with self.assertRaises(ValueError):
                stager.stage(ROOT, stage, "hyprland", native)
        self.assertEqual(before, [path.read_bytes() for path in watched])

    def test_default_profile_keeps_sway_with_graphical_login(self):
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "native"
            native.touch()
            stage = Path(directory) / "profile"
            stager.stage(ROOT, stage, "sway", native)
            self.assertNotIn("hyprland", (stage / "packages.x86_64").read_text().splitlines())
            self.assertTrue((stage / "airootfs/etc/systemd/system/display-manager.service").is_symlink())

    def test_packages_reject_version_and_checksum_drift(self):
        lock = {"packages": {"hyprland": {"version": "1-1", "filename": "pkg", "sha256": hashlib.sha256(b"valid").hexdigest()}}}
        metadata = {"hyprland": {"VERSION": ["1-1"], "FILENAME": ["pkg"], "SHA256SUM": [lock["packages"]["hyprland"]["sha256"]]}}
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            (cache / "pkg").write_bytes(b"valid")
            pins.verify(lock, metadata, cache)
            (cache / "pkg").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                pins.verify(lock, metadata, cache)
        metadata["hyprland"]["VERSION"] = ["2-1"]
        with self.assertRaises(ValueError):
            pins.verify(lock, metadata)

    def test_missing_installed_package_is_rejected(self):
        lock = {"packages": {"hyprland": {"version": "1-1"}}}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                pins.verify_installed(lock, Path(directory))

    def test_package_db_reader_does_not_extract_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra.db"
            with tarfile.open(path, "w:gz") as archive:
                entry = tarfile.TarInfo("../../outside/desc")
                data = b"%NAME%\nhyprland\n\n%VERSION%\n1-1\n\n"
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
            self.assertEqual(pins.metadata(path)["hyprland"]["VERSION"], ["1-1"])
            self.assertFalse((Path(directory) / "outside").exists())

    def test_bar_and_material_json(self):
        assets = ROOT / "desktop/hyprland/airootfs/usr/share/fetian/hyprland"
        config = json.loads((assets / "waybar/config.json").read_text())
        self.assertEqual(len(config), 2)
        self.assertEqual(len(json.loads((assets / "materials.json").read_text())["families"]), 6)


@unittest.skipUnless(os.name == "posix" and os.geteuid() != 0, "unprivileged Linux session fixture")
class SessionTests(unittest.TestCase):
    def session(self, version="0.56.2-4"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "bin"
            binary.mkdir()
            for name, body in {
                "pacman": f"echo hyprland {version}",
                "Hyprland": 'echo compositor >> "$FETIAN_TEST_LOG"; exit 17',
                "systemctl": 'echo "$*" >> "$FETIAN_TEST_LOG"',
                "dbus-update-activation-environment": 'echo "dbus activation environment cleared" >> "$FETIAN_TEST_LOG"',
            }.items():
                path = binary / name
                path.write_text("#!/usr/bin/env bash\n" + body + "\n")
                path.chmod(0o755)
            env = dict(os.environ, PATH=f"{binary}:{os.environ['PATH']}", XDG_RUNTIME_DIR=str(root),
                       DBUS_SESSION_BUS_ADDRESS="test", FETIAN_TEST_LOG=str(root / "log"))
            env.pop("SWAYSOCK", None)
            env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
            result = subprocess.run(["bash", str(ROOT / "desktop/hyprland/bin/fetian-hyprland-session")],
                                    env=env, capture_output=True, text=True, timeout=10)
            return result, (root / "log").read_text() if (root / "log").exists() else ""

    def test_compositor_failure_cleans_up_only_user_session(self):
        result, log = self.session()
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertIn("--user stop fetian-hyprland.target", log)
        self.assertNotIn("fetian-health", log)

    def test_version_mismatch_never_launches_compositor(self):
        result, log = self.session("99.0.0-1")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("compositor", log)


if __name__ == "__main__":
    unittest.main()
