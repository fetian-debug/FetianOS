#!/usr/bin/env python3
"""Prepare verified release assets, splitting ISO files below GitHub's 2 GiB cap."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSET_LIMIT = 2 * 1024**3


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def package(bundle, output, chunk_size=1900 * 1024**2, asset_limit=ASSET_LIMIT):
    if not 0 < chunk_size < asset_limit: raise ValueError('Invalid release chunk size')
    if output.exists(): raise FileExistsError('Choose a fresh asset destination')
    metadata = json.loads((bundle / 'build.json').read_text())
    desktop = metadata['desktop']
    if desktop not in ('sway', 'hyprland'): raise ValueError('Unknown desktop variant')
    verification = metadata['verification']
    if not all(verification.get(key) is True for key in ('image_static_checks', 'vm_boot', 'live_account_reported_ready')):
        raise ValueError('Static image and actual serial/live-account boot checks required before download publication')
    if any(verification.get(key) for key in ('graphical_login', 'installation', 'hardware', 'reproducible')):
        raise ValueError('This developer-preview pipeline does not attest GUI/install/hardware/reproducibility')
    iso_name = metadata['iso']['file']
    if Path(iso_name).name != iso_name or '/' in iso_name or '\\' in iso_name: raise ValueError('Unsafe ISO name')
    iso = bundle / iso_name
    if iso.is_symlink() or not iso.is_file() or iso.stat().st_size != metadata['iso']['size'] or digest(iso) != metadata['iso']['sha256']:
        raise ValueError('ISO does not match build record')
    evidence = metadata['vm_evidence']
    if evidence.get('file') != 'vm-evidence.json' or evidence.get('serial_file') != 'vm-serial.log': raise ValueError('Unexpected evidence path')
    if digest(bundle / evidence['file']) != evidence['sha256'] or digest(bundle / evidence['serial_file']) != evidence['serial_sha256']:
        raise ValueError('VM evidence changed')
    report = json.loads((bundle / 'vm-evidence.json').read_text())
    if report.get('iso_sha256') != metadata['iso']['sha256'] or not all(report.get(key) is True for key in ('probe_passed', 'linux_userspace_observed', 'live_account_reported_ready', 'uefi_firmware_configured')):
        raise ValueError('VM evidence is incomplete or belongs to another image')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.assets-', dir=output.parent) as temporary:
        temporary = Path(temporary); parts = []
        if iso.stat().st_size < asset_limit:
            shutil.copyfile(iso, temporary / iso.name)
            parts.append({'file': iso.name, 'size': iso.stat().st_size, 'sha256': digest(temporary / iso.name)})
        else:
            with iso.open('rb') as source:
                index = 1
                while source.tell() < iso.stat().st_size:
                    path = temporary / (iso.name + f'.part{index:03d}'); remaining = chunk_size
                    with path.open('wb') as target:
                        while remaining:
                            block = source.read(min(1024 * 1024, remaining))
                            if not block: break
                            target.write(block); remaining -= len(block)
                    parts.append({'file': path.name, 'size': path.stat().st_size, 'sha256': digest(path)}); index += 1
        for name in ('build.json', 'packages.json', 'vm-evidence.json', 'vm-serial.log'):
            shutil.copyfile(bundle / name, temporary / (desktop + '-' + name))
        (temporary / (iso.name + '.sha256')).write_text(metadata['iso']['sha256'] + '  ' + iso.name + '\n')
        shutil.copyfile(ROOT / 'scripts/assemble-iso.py', temporary / (desktop + '-assemble-iso.py'))
        manifest = {'schema_version': 1, 'desktop': desktop, 'iso': metadata['iso'], 'parts': parts,
                    'verification': verification, 'ci': metadata.get('ci', {}), 'build_record': desktop + '-build.json',
                    'policy': 'Developer preview for disposable UEFI VM evaluation; installation is disabled.'}
        (temporary / (desktop + '-downloads.json')).write_text(json.dumps(manifest, indent=2) + '\n')
        instructions = f'''FetianOS {desktop} developer preview\n\nInstallation is disabled. Serial boot is tested; GUI/login/hardware acceptance remains separate.\n\nDownload all .partNNN files when the ISO is split, plus {desktop}-downloads.json and {desktop}-assemble-iso.py.\nVerify and assemble with Python 3 on Windows/Linux/macOS:\n\npython3 {desktop}-assemble-iso.py {desktop}-downloads.json\n\nFor an unsplit ISO, verify its .sha256 sidecar. SHA256SUMS-{desktop} covers all supplied assets.\nThe JSON build/package/evidence records identify the tested source, tools and package set.\n'''
        (temporary / (desktop + '-DOWNLOAD.txt')).write_text(instructions)
        # The configurable small limit used by unit tests only applies to ISO parts.
        if any(path.stat().st_size >= ASSET_LIMIT for path in temporary.iterdir()): raise ValueError('Release asset exceeds GitHub limit')
        lines = [digest(path) + '  ' + path.name for path in sorted(temporary.iterdir())]
        (temporary / ('SHA256SUMS-' + desktop)).write_text('\n'.join(lines) + '\n')
        # Exercise the same assembler shipped to users before exposing the assets.
        spec = importlib.util.spec_from_file_location('assemble', ROOT / 'scripts/assemble-iso.py')
        assembler = importlib.util.module_from_spec(spec); spec.loader.exec_module(assembler)
        assembler.verify(temporary / (desktop + '-downloads.json'), verify_only=True)
        temporary.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path); parser.add_argument('output', type=Path); args = parser.parse_args()
    try:
        config = json.loads((ROOT / 'ci/manjaro.json').read_text())
        print(package(args.bundle, args.output, config['release_chunk_mib'] * 1024**2))
    except (OSError, ValueError, KeyError) as error: parser.exit(1, str(error) + '\n')
