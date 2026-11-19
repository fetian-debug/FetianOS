#!/usr/bin/env python3
"""Verify retained stability evidence, including failed runs; do not infer acceptance."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/stability/evidence'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify():
    datasets = []
    for summary_path in sorted(EVIDENCE.rglob('summary.json')):
        summary = read(summary_path)
        if not {'completed', 'expectations_met', 'counts', 'failures'} <= set(summary): continue
        folder = summary_path.parent
        plan = read(folder/'plan.json')
        archive_path = folder/'runs.tar.gz'
        if archive_path.exists():
            entries = read(folder/'archive-index.json')
            with tarfile.open(archive_path, 'r:gz') as archive:
                assert len(archive.getmembers()) == len(entries)
                records = []
                for entry in entries:
                    data = archive.extractfile(entry['name']).read()
                    assert hashlib.sha256(data).hexdigest() == entry['sha256']
                    duplicate = folder/entry['name']
                    if duplicate.exists(): assert hashlib.sha256(duplicate.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == entry['sha256']
                    records.append(json.loads(data))
        else:
            records = [read(path) for path in sorted(folder.glob('run-*.json'))]
        assert len(records) == summary['completed'] == len(plan['cases'])
        assert [r['config'] for r in records] == plan['cases']
        assert dict(Counter(r['classification'] for r in records)) == summary['counts']
        assert sum(r['expectations_met'] for r in records) == summary['expectations_met']
        assert sum(not r['expectations_met'] for r in records) == len(summary['failures']) == summary['unexpected_failures']
        for failure in summary['failures']:
            record = records[failure['index']]
            assert not record['expectations_met'] and record['config']['seed'] == failure['seed']
        datasets.append(dict(path=str(folder.relative_to(EVIDENCE)), completed=len(records), failures=summary['unexpected_failures']))
    for phase in ('baseline', 'baseline-clean', 'final'):
        for result in read(EVIDENCE/phase/'results.json'):
            data = (EVIDENCE/phase/result['log']).read_bytes().replace(b'\r\n', b'\n')
            assert hashlib.sha256(data).hexdigest() == result['log_sha256'], (phase, result['name'])
            assert (result['status'] == 'passed') == (result['exit_code'] == 0)
    for name in ('native', 'fca'):
        report = read(EVIDENCE/'dependency-audit'/f'{name}.json')
        finding = report['vulnerabilities']
        assert finding['count'] == len(finding['list'])
        assert finding['found'] == bool(finding['list'])
    if (EVIDENCE/'linux-fca-control/stress/plan.json').exists():
        assert read(EVIDENCE/'final/fca-stress/plan.json')['cases'] == read(EVIDENCE/'linux-fca-control/stress/plan.json')['cases']
    if (EVIDENCE/'hosted-fca/stress/plan.json').exists():
        assert read(EVIDENCE/'final/fca-stress/plan.json')['cases'] == read(EVIDENCE/'hosted-fca/stress/plan.json')['cases']
    assert read(EVIDENCE/'final/acceptance.json')['stable'] is False
    boots = []
    for attempt in sorted(EVIDENCE.glob('iso-attempt-*')):
        if not (attempt/'run.json').exists(): continue
        run = read(attempt/'run.json')
        if (attempt/'jobs.json').exists():
            jobs = read(attempt/'jobs.json')['jobs']
            assert all(job['conclusion'] == 'skipped' for job in jobs if job['name'] == 'publish')
        for path in attempt.glob('*/work/vm/*/evidence.json'):
            boot = read(path)
            assert not any(boot[key] for key in ('graphical_login_validated', 'installation_validated', 'hardware_validated'))
            if boot['probe_passed']:
                assert boot['linux_userspace_observed'] and boot['live_account_reported_ready']
                assert 'FETIANOS_LIVE_LOGIN_READY' in path.with_name('serial.log').read_text()
            boots.append(dict(source=run['head_sha'], iso_sha256=boot['iso_sha256'], probe_passed=boot['probe_passed'], scope='UEFI serial/live account only'))
    if (EVIDENCE/'source-index.json').exists():
        with tarfile.open(EVIDENCE/'source-snapshot.tar.gz', 'r:gz') as archive:
            for entry in read(EVIDENCE/'source-index.json')['files']:
                data = archive.extractfile(entry['path']).read()
                assert hashlib.sha256(data).hexdigest() == entry['sha256']
                assert hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest() == entry['canonical_sha256']
                source = (ROOT/entry['path']).resolve()
                assert source.is_relative_to(ROOT)
                if not entry['path'].startswith('.build-tools/') or source.exists():
                    assert hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == entry['canonical_sha256'], entry['path']
    manifest_path = EVIDENCE/'manifest.json'
    if manifest_path.exists():
        for name, entry in read(manifest_path)['files'].items():
            path = (ROOT/name).resolve()
            assert path.is_relative_to(ROOT)
            data = path.read_bytes()
            if entry['mode'] == 'crlf-to-lf': data = data.replace(b'\r\n', b'\n')
            assert hashlib.sha256(data).hexdigest() == entry['sha256'], name
    print(json.dumps(dict(evidence_consistent=True, datasets=datasets, boot_observations=boots, daily_use_acceptance=False,
                         scope='Integrity and reported outcomes, not independent functional re-execution or security certification.')))


if __name__ == '__main__': verify()
