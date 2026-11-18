#!/usr/bin/env python3
"""Publish current-run verified assets as a draft, then expose a developer prerelease."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def validate(root, environment):
    repository = environment['GITHUB_REPOSITORY']; commit = environment['GITHUB_SHA']; run_id = environment['GITHUB_RUN_ID']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or not re.fullmatch('[0-9a-f]{40}', commit): raise ValueError('Invalid repository/commit')
    manifests = list(root.rglob('*-downloads.json')); assets = []; variants = []
    if not manifests: raise ValueError('No download manifests')
    for path in manifests:
        manifest = json.loads(path.read_text()); desktop = manifest['desktop']
        if desktop not in ('sway', 'hyprland') or desktop in variants or path.name != desktop + '-downloads.json': raise ValueError('Invalid/duplicate variant')
        ci = manifest['ci']
        if ci.get('repository') != repository or ci.get('commit') != commit or str(ci.get('run_id')) != str(run_id): raise ValueError('Assets do not belong to this repository/commit/run')
        verification = manifest['verification']
        if not all(verification.get(key) is True for key in ('image_static_checks', 'vm_boot', 'live_account_reported_ready')): raise ValueError('Required checks did not pass')
        if any(verification.get(key) for key in ('graphical_login', 'installation', 'hardware', 'reproducible')): raise ValueError('Unexpected promotion claim')
        sums = path.parent / ('SHA256SUMS-' + desktop); listed = set()
        for line in sums.read_text().splitlines():
            checksum, name = line.split('  ', 1)
            if not re.fullmatch('[0-9a-f]{64}', checksum) or Path(name).name != name or '\\' in name or name in ('.', '..'): raise ValueError('Unsafe checksum entry')
            asset = path.parent / name
            if name in listed or asset.is_symlink() or not asset.is_file() or digest(asset) != checksum: raise ValueError('Asset integrity failed: ' + name)
            if asset.stat().st_size >= 2 * 1024**3: raise ValueError('Release asset exceeds 2 GiB')
            listed.add(name); assets.append(asset)
        required = {path.name, desktop + '-build.json', desktop + '-packages.json', desktop + '-vm-evidence.json', desktop + '-vm-serial.log'}
        required.update(part['file'] for part in manifest['parts'])
        if not required <= listed: raise ValueError('Missing checksummed assets')
        assets.append(sums); variants.append(desktop)
    if len({path.name for path in assets}) != len(assets): raise ValueError('Release asset names collide')
    return assets, variants


def publish(root, environment=os.environ, run=subprocess.run):
    ref = environment['GITHUB_REF']
    if ref != 'refs/heads/main' and not ref.startswith('refs/tags/v'): raise ValueError('Publish only main or version tags')
    assets, variants = validate(root, environment)
    repository = environment['GITHUB_REPOSITORY']; commit = environment['GITHUB_SHA']
    tag = ref.removeprefix('refs/tags/') if ref.startswith('refs/tags/') else 'preview-' + environment['GITHUB_RUN_NUMBER'] + '-' + environment.get('GITHUB_RUN_ATTEMPT', '1')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}', tag): raise ValueError('Unsafe release tag')
    notes = root / 'release-notes.md'
    notes.write_text(f'''FetianOS developer preview ({", ".join(variants)})\n\nSource commit: `{commit}`\n\n[CI build and serial-boot logs](https://github.com/{repository}/actions/runs/{environment['GITHUB_RUN_ID']})\n\nStatic ISO validation and a real disposable OVMF serial/live-account boot probe passed for every included variant.\nGraphical login, installation, hardware acceptance and reproducibility are not attested. Installation remains disabled.\n\nDownload the ISO and its SHA-256 sidecar. If split, download every numbered part, the variant downloads.json and assemble-iso.py, then follow DOWNLOAD.txt. Checksums cover every asset. Build/package/evidence JSON records are included.\n\n[Downloads and documentation](https://{repository.split('/')[0]}.github.io/{repository.split('/')[1]}/downloads.html)\n''')
    base = ['gh', 'release']
    # No clobber, force-push, existing-release edit or visibility change on failure.
    run(base + ['create', tag, '--repo', repository, '--target', commit, '--draft', '--prerelease', '--title', 'FetianOS ' + tag + ' — developer preview', '--notes-file', str(notes)], check=True)
    for offset in range(0, len(assets), 20):
        run(base + ['upload', tag, '--repo', repository, *map(str, assets[offset:offset + 20])], check=True)
    run(base + ['edit', tag, '--repo', repository, '--draft=false', '--prerelease'], check=True)
    return 'https://github.com/' + repository + '/releases/tag/' + tag


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('assets', type=Path); args = parser.parse_args()
    try: print(publish(args.assets))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error: parser.exit(1, str(error) + '\n')
