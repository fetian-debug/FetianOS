"""Payload extraction regressions; real large fixtures are opt-in and disposable."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('payload_release', ROOT/'scripts/release-artifacts.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PayloadTests(unittest.TestCase):
    def test_tool_failure_is_not_downgraded(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'payload'
            run = Mock(side_effect=subprocess.CalledProcessError(1, ['xorriso']))
            with self.assertRaises(subprocess.CalledProcessError): release.extract_payload(Path(directory)/'image.iso', target, run=run)

    def test_success_with_missing_or_empty_output_is_rejected(self):
        for create in (False, True):
            with self.subTest(create=create), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'payload'
                def run(*args, **kwargs):
                    if create: target.touch()
                    return subprocess.CompletedProcess(args[0], 0)
                with self.assertRaises(ValueError): release.extract_payload(Path(directory)/'image.iso', target, run=run)

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'payload'; target.write_bytes(b'previous')
            run = Mock()
            with self.assertRaises(FileExistsError): release.extract_payload(Path(directory)/'image.iso', target, run=run)
            self.assertEqual(target.read_bytes(), b'previous'); run.assert_not_called()

    def roundtrip(self, size):
        with tempfile.TemporaryDirectory(prefix='fetian-iso-payload-') as directory:
            root = Path(directory)
            if size > 2**31 and shutil.disk_usage(root).free < 7*1024**3:
                self.skipTest('At least 7 GiB disposable space required for the real large-file roundtrip')
            source = root/'tree/fetianos/x86_64/airootfs.sfs'; source.parent.mkdir(parents=True)
            # Arbitrary payload, not a claimed valid SquashFS or bootable ISO.
            # Sparse input saves space; both the ISO and extraction are real.
            with source.open('wb') as stream:
                stream.write(b'payload-header')
                tail = b'payload-end-12345'
                stream.seek(size-len(tail)); stream.write(tail)
            image = root/'fixture.iso'
            subprocess.run(['xorriso', '-no_rc', '-as', 'mkisofs', '-R', '-iso-level', '3', '-o', str(image), str(root/'tree')],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=300)
            target = root/'extracted'
            release.extract_payload(image, target)
            self.assertEqual(target.stat().st_size, size)
            self.assertEqual(release.digest(source), release.digest(target))

    @unittest.skipUnless(shutil.which('xorriso'), 'xorriso required for real ISO extraction')
    def test_real_small_payload_roundtrip(self):
        self.roundtrip(65536)

    @unittest.skipUnless(shutil.which('xorriso') and os.environ.get('FETIAN_LARGE_ISO_TEST')=='1', 'Opt-in large ISO fixture with xorriso required')
    def test_real_payload_above_two_gib_roundtrip(self):
        self.roundtrip(2**31+65536)


if __name__ == '__main__': unittest.main(verbosity=2)
