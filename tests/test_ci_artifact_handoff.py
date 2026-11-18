import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('artifact_handoff', ROOT / 'scripts/ci-artifact-handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


@unittest.skipIf(os.name != 'posix' or os.getuid() == 0, 'Non-root POSIX checkout-owner fixture')
class ArtifactHandoffTests(unittest.TestCase):
    def test_only_public_bundles_are_returned_and_private_modes_remain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / 'output/completed'
            bundle.mkdir(parents=True, mode=0o700)
            (bundle / 'image.iso').write_bytes(b'ownership fixture, not an ISO')
            embedded = root / 'work/build/airootfs/etc'
            embedded.mkdir(parents=True)
            (embedded / 'shadow').write_text('fixture')
            changed = []
            self.assertEqual(handoff.handoff(root, lambda path, uid, gid, **options: changed.append((path, uid, gid, options))), 3)
            self.assertTrue(all(path.is_relative_to(root / 'output') for path, *_ in changed))
            self.assertTrue(all(options == {'follow_symlinks': False} for *_, options in changed))
            self.assertEqual(bundle.stat().st_mode & 0o777, 0o700)

    def test_symlink_escape_is_rejected_before_any_ownership_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'output').mkdir()
            (root / 'work').mkdir()
            (root / 'output/escape').symlink_to(root / 'work', target_is_directory=True)
            changed = []
            with self.assertRaises(ValueError):
                handoff.handoff(root, lambda *args, **kwargs: changed.append(args))
            self.assertEqual(changed, [])


if __name__ == '__main__':
    unittest.main()
