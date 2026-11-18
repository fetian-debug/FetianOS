"""Disposable release fixtures; these tests never build an ISO or call GitHub."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


assets = load('package-downloads'); assembler = load('assemble-iso'); recorder = load('record-vm-evidence'); publisher = load('publish-preview'); docs = load('build-docs')


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fetian-ci-fixture-'); self.root = Path(self.temporary.name)
        self.bundle = self.root / 'bundle'; self.bundle.mkdir(); self.iso = self.bundle / 'fixture.iso'
        self.iso.write_bytes(b'fixture data, not a real bootable ISO' * 10)
        self.environment = {'GITHUB_REPOSITORY': 'owner/FetianOS', 'GITHUB_SHA': 'a' * 40, 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_NUMBER': '12', 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REF': 'refs/heads/main'}
        self.metadata = {'desktop': 'sway', 'iso': {'file': self.iso.name, 'size': self.iso.stat().st_size, 'sha256': assets.digest(self.iso)},
                         'ci': {'repository': 'owner/FetianOS', 'commit': 'a' * 40, 'run_id': '123'},
                         'verification': {'image_static_checks': True, 'vm_boot': True, 'live_account_reported_ready': True,
                                          'graphical_login': False, 'installation': False, 'hardware': False, 'reproducible': False}}
        self.evidence = {'iso_sha256': assets.digest(self.iso), 'probe_passed': True, 'uefi_firmware_configured': True,
                         'linux_userspace_observed': True, 'live_account_reported_ready': True, 'installed_reboot_attempt': False}
        (self.bundle / 'vm-evidence.json').write_text(json.dumps(self.evidence))
        (self.bundle / 'vm-serial.log').write_text('systemd[1]: fixture\nFETIANOS_LIVE_LOGIN_READY\n')
        self.metadata['vm_evidence'] = {'file': 'vm-evidence.json', 'sha256': assets.digest(self.bundle / 'vm-evidence.json'), 'serial_file': 'vm-serial.log', 'serial_sha256': assets.digest(self.bundle / 'vm-serial.log')}
        self.write_metadata(); (self.bundle / 'packages.json').write_text('{}')
    def tearDown(self): self.temporary.cleanup()
    def write_metadata(self): (self.bundle / 'build.json').write_text(json.dumps(self.metadata))
    def package(self, split=False):
        return assets.package(self.bundle, self.root / 'downloads', chunk_size=100, asset_limit=200 if split else 1000)
    def test_unsplit_release_is_verified_and_does_not_claim_gui(self):
        output = self.package(); manifest = output / 'sway-downloads.json'
        data = json.loads(manifest.read_text())
        self.assertEqual(len(data['parts']), 1); self.assertFalse(data['verification']['graphical_login'])
        self.assertEqual(assembler.verify(manifest), output / self.iso.name)
        self.assertTrue((output / 'SHA256SUMS-sway').is_file())
    def test_split_assembly_roundtrip_and_no_overwrite(self):
        output = self.package(split=True); manifest = output / 'sway-downloads.json'
        data = json.loads(manifest.read_text()); self.assertGreater(len(data['parts']), 1)
        self.assertTrue(all(part['size'] <= 100 for part in data['parts']))
        assembled = assembler.verify(manifest); self.assertEqual(assembled.read_bytes(), self.iso.read_bytes())
        with self.assertRaises(FileExistsError): assembler.verify(manifest)
        self.assertEqual(assembled.read_bytes(), self.iso.read_bytes())
    def test_tampered_part_does_not_leave_output_or_temporary_file(self):
        output = self.package(split=True); manifest = output / 'sway-downloads.json'
        data = json.loads(manifest.read_text()); (output / data['parts'][0]['file']).write_bytes(b'bad')
        with self.assertRaises(ValueError): assembler.verify(manifest)
        self.assertFalse((output / self.iso.name).exists()); self.assertFalse(list(output.glob('.fetian-iso-*')))
    def test_assembler_rejects_traversal_and_duplicate_parts(self):
        output = self.package(split=True); manifest = output / 'sway-downloads.json'; data = json.loads(manifest.read_text())
        for value in ('../outside', '/absolute', 'C:\\unsafe', 'a\\b', ''):
            with self.assertRaises(ValueError): assembler.safe_name(value)
        data['parts'].append(data['parts'][0]); manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError): assembler.verify(manifest)
    def test_unbooted_or_promoted_bundle_cannot_be_packaged(self):
        for field, value in (('vm_boot', False), ('image_static_checks', False), ('installation', True)):
            original = self.metadata['verification'][field]; self.metadata['verification'][field] = value; self.write_metadata()
            with self.assertRaises(ValueError): self.package()
            self.assertFalse((self.root / 'downloads').exists())
            self.metadata['verification'][field] = original
    def test_mismatched_evidence_or_iso_cannot_be_packaged(self):
        (self.bundle / 'vm-serial.log').write_text('changed')
        with self.assertRaises(ValueError): self.package()
        self.iso.write_bytes(b'tampered')
        with self.assertRaises(ValueError): self.package()
    def test_recorder_matches_image_and_retains_unverified_acceptance_flags(self):
        run = self.root / 'runs/test'; run.mkdir(parents=True)
        (run / 'evidence.json').write_text(json.dumps(self.evidence)); (run / 'serial.log').write_text('FETIANOS_LIVE_LOGIN_READY')
        self.metadata['verification']['vm_boot'] = False; self.metadata['verification']['installation'] = True; self.write_metadata()
        recorder.record(self.iso, run.parent)
        record = json.loads((self.bundle / 'build.json').read_text())
        self.assertTrue(record['verification']['vm_boot']); self.assertFalse(record['verification']['installation'])
        self.evidence['probe_passed'] = False; (run / 'evidence.json').write_text(json.dumps(self.evidence))
        with self.assertRaises(ValueError): recorder.record(self.iso, run.parent)
    def test_recorder_requires_actual_serial_readiness_marker(self):
        run = self.root / 'runs/test'; run.mkdir(parents=True)
        (run / 'evidence.json').write_text(json.dumps(self.evidence)); (run / 'serial.log').write_text('firmware only')
        with self.assertRaises(ValueError): recorder.record(self.iso, run.parent)
    def test_publisher_checks_current_run_and_every_checksum(self):
        output = self.package(); paths, variants = publisher.validate(output, self.environment)
        self.assertIn('sway', variants); self.assertTrue(paths)
        wrong = dict(self.environment, GITHUB_RUN_ID='999')
        with self.assertRaises(ValueError): publisher.validate(output, wrong)
        (output / 'sway-packages.json').write_text('changed')
        with self.assertRaises(ValueError): publisher.validate(output, self.environment)
    def test_publisher_exposes_release_only_after_all_uploads(self):
        output = self.package(); calls = []
        url = publisher.publish(output, self.environment, lambda arguments, **kwargs: calls.append(arguments))
        self.assertIn('--draft', calls[0]); self.assertIn('--prerelease', calls[0]); self.assertIn('--draft=false', calls[-1])
        self.assertFalse(any('--clobber' in call for call in calls)); self.assertTrue(url.endswith('/preview-12-1'))
        with self.assertRaises(ValueError): publisher.publish(output, dict(self.environment, GITHUB_REF='refs/heads/unreviewed'), lambda *_: None)
    def test_upload_failure_leaves_draft_and_never_publishes(self):
        output = self.package(); calls = []
        def run(arguments, **kwargs):
            calls.append(arguments)
            if arguments[2] == 'upload': raise subprocess.CalledProcessError(1, arguments)
        with self.assertRaises(subprocess.CalledProcessError): publisher.publish(output, self.environment, run)
        self.assertFalse(any('edit' in call for call in calls))


@unittest.skipUnless(importlib.util.find_spec('markdown'), 'Python-Markdown required for site integration')
class DocumentationTests(unittest.TestCase):
    def test_full_site_build_preserves_docs_and_rewrites_project_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'site'; docs.build(ROOT, output)
            home = (output / 'index.html').read_text(); page = (output / 'downloads.html').read_text()
            self.assertIn('href="downloads.html"', home)
            self.assertIn('href="docs/index.html"', home)
            self.assertIn('id="releases"', page); self.assertIn('downloads.js', page)
            self.assertTrue((output / 'docs/ci-cd.html').is_file())
            self.assertIn('<table>', (output / 'docs/ci-cd.html').read_text())
            self.assertIn('href="../downloads.html"', (output / 'docs/index.html').read_text())
            self.assertTrue((output / 'docs/application-inventory.json').is_file())
            self.assertEqual(json.loads((output / 'assets/repository.json').read_text())['repository'], 'fetian-debug/FetianOS')
    def test_site_refuses_output_overwrite_and_invalid_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileExistsError): docs.build(ROOT, Path(temporary))
            with self.assertRaises(ValueError): docs.build(ROOT, Path(temporary) / 'site', 'invalid/../../repo')


@unittest.skipUnless(importlib.util.find_spec('yaml'), 'PyYAML required for workflow structure checks')
class WorkflowTests(unittest.TestCase):
    def test_workflow_permission_and_trigger_boundaries(self):
        import yaml
        iso = yaml.load((ROOT / '.github/workflows/iso-release.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertNotIn('pull_request', iso['on'])
        self.assertEqual(iso['permissions']['contents'], 'read')
        self.assertEqual(iso['jobs']['publish']['permissions']['contents'], 'write')
        self.assertEqual(iso['jobs']['publish']['needs'], 'build')
        self.assertIn('checks', iso['jobs']['build']['needs'])
        source = yaml.load((ROOT / '.github/workflows/source-checks.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn('workflow_call', source['on'])
        pages = yaml.load((ROOT / '.github/workflows/docs-pages.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn("github.event_name != 'pull_request'", pages['jobs']['deploy']['if'])
        for file in (ROOT / '.github/workflows').glob('*.yml'):
            data = yaml.load(file.read_text(), Loader=yaml.BaseLoader)
            for job in data['jobs'].values():
                for step in job.get('steps', []):
                    if step.get('uses', '').startswith('actions/'):
                        self.assertRegex(step['uses'], r'@\b[0-9a-f]{40}$')


if __name__ == '__main__': unittest.main()
