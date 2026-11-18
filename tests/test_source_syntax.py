import ast
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceSyntaxTests(unittest.TestCase):
    def test_python_sources_parse(self):
        paths = list((ROOT / "desktop/hyprland").glob("*.py"))
        paths += [ROOT / "scripts/stage-profile.py", ROOT / "scripts/check-hyprland-packages.py",
                  ROOT / "apps/fetian-control-center/fetian_control_center.py"]
        paths += list((ROOT / "system/boot").glob("*.py"))
        paths += [ROOT / "apps/fetian-desktop/fetian_daily.py", ROOT / "scripts/verify-boot-artifacts.py"]
        paths += list((ROOT / "apps/fetian-files").glob("*.py"))
        paths += list((ROOT / "scripts").glob("*.py"))
        paths += list((ROOT / "installer").rglob("*.py"))
        for path in paths:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    @unittest.skipUnless(sys.platform == "linux" and shutil.which("bash"), "Linux Bash required")
    def test_session_and_build_scripts_parse(self):
        paths = list((ROOT / "desktop/hyprland/bin").glob("*"))
        paths += list((ROOT / "scripts").glob("*.sh"))
        paths.append(ROOT / "apps/fetian-dev-bin/fetian-desktop")
        paths += list((ROOT / "system/boot/airootfs/usr/bin").glob("*"))
        paths.append(ROOT / "system/boot/airootfs/usr/lib/fetian/display-manager")
        paths.append(ROOT / "system/boot/airootfs/root/customize_airootfs.sh")
        for path in paths:
            if path.is_file():
                with self.subTest(path=path.name):
                    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
