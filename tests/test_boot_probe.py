"""Exercise the boot probe with controlled QEMU output, without booting an image."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import unittest


@unittest.skipUnless(sys.platform == "linux", "Requires Linux Bash/QEMU process semantics")
class BootProbeTests(unittest.TestCase):
    def probe(self, output, status=0, firmware=True, expect_live=False):
        with tempfile.TemporaryDirectory(prefix="fetian-boot-test-") as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "output").mkdir()
            (root / "bin").mkdir()
            shutil.copy2(Path(__file__).resolve().parents[1] / "scripts/test-boot.sh",
                         root / "scripts/test-boot.sh")
            (root / "output/test.iso").write_bytes(b"test fixture, not an ISO")
            firmware_path = root / "firmware.fd"
            if firmware:
                firmware_path.touch()
            qemu = root / "bin/qemu-system-x86_64"
            qemu.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$PROBE_OUTPUT"\nexit "$PROBE_STATUS"\n')
            qemu.chmod(0o755)
            env = dict(os.environ, PATH=f"{root / 'bin'}:{os.environ['PATH']}",
                       OVMF_CODE=str(firmware_path), PROBE_OUTPUT=output,
                       PROBE_STATUS=str(status), FETIAN_EXPECT_LIVE_ACCOUNT="1" if expect_live else "0")
            env["FETIAN_ISO"] = str(root / "output/test.iso")
            return subprocess.run(["bash", str(root / "scripts/test-boot.sh")],
                                  env=env, capture_output=True, text=True, timeout=10)

    def test_firmware_boot_text_is_not_success(self):
        self.assertNotEqual(self.probe("UEFI: boot failed; kernel not found").returncode, 0)

    def test_userspace_evidence_is_required(self):
        result = self.probe("systemd[1]: Reached target Multi-User System.")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("does not validate", result.stdout)

    def test_qemu_error_is_not_masked_by_output(self):
        self.assertNotEqual(self.probe("systemd[1]: cached output", status=2).returncode, 0)

    def test_missing_explicit_firmware_fails(self):
        self.assertEqual(self.probe("systemd[1]: started", firmware=False).returncode, 2)

    def test_live_account_gate_rejects_only_generic_boot_messages(self):
        self.assertNotEqual(self.probe("systemd[1]: started", expect_live=True).returncode, 0)

    def test_live_account_gate_requires_real_service_marker(self):
        output = "systemd[1]: started\nFETIANOS_LIVE_LOGIN_READY\n"
        self.assertEqual(self.probe(output, expect_live=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
