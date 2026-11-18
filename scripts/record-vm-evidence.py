#!/usr/bin/env python3
"""Attach matching serial-boot evidence without promoting graphical/install status."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.hexdigest()


def record(iso, runs=ROOT / 'work/vm'):
    iso = iso.resolve(strict=True); expected = digest(iso)
    metadata_path = iso.parent / 'build.json'; metadata = json.loads(metadata_path.read_text())
    if metadata['iso']['sha256'] != expected or metadata['iso']['file'] != iso.name:
        raise ValueError('Image/build record mismatch')
    matches = []
    for path in runs.glob('*/evidence.json'):
        evidence = json.loads(path.read_text())
        if evidence.get('iso_sha256') == expected and not evidence.get('installed_reboot_attempt'):
            matches.append((path, evidence))
    if not matches: raise ValueError('No matching VM evidence')
    path, evidence = max(matches, key=lambda item: item[0].stat().st_mtime_ns)
    required = ('probe_passed', 'uefi_firmware_configured', 'linux_userspace_observed', 'live_account_reported_ready')
    if not all(evidence.get(key) is True for key in required): raise ValueError('Required serial/live-account probe did not pass')
    serial = path.parent / 'serial.log'
    if 'FETIANOS_LIVE_LOGIN_READY' not in serial.read_text(errors='replace'): raise ValueError('Readiness marker absent from serial log')
    shutil.copyfile(path, iso.parent / 'vm-evidence.json')
    shutil.copyfile(serial, iso.parent / 'vm-serial.log')
    metadata['verification']['vm_boot'] = True
    metadata['verification']['live_account_reported_ready'] = True
    metadata['vm_evidence'] = {'file': 'vm-evidence.json', 'sha256': digest(iso.parent / 'vm-evidence.json'),
                               'serial_file': 'vm-serial.log', 'serial_sha256': digest(iso.parent / 'vm-serial.log')}
    # Keep every unrelated acceptance claim false even if future input adds fields.
    for key in ('graphical_login', 'installation', 'hardware', 'reproducible'): metadata['verification'][key] = False
    with tempfile.NamedTemporaryFile(mode='w', dir=iso.parent, prefix='.metadata-', delete=False) as stream:
        temporary = Path(stream.name); json.dump(metadata, stream, indent=2); stream.write('\n')
    temporary.replace(metadata_path)
    return iso.parent


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('iso', type=Path); args = parser.parse_args()
    try: print(record(args.iso))
    except (OSError, ValueError, KeyError) as error: parser.exit(1, str(error) + '\n')
