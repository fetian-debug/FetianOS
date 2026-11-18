#!/usr/bin/env python3
"""Verify downloaded ISO parts and assemble without replacing an existing file."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def safe_name(value):
    if not isinstance(value, str) or value in ('', '.', '..') or any(char in value for char in ('/', '\\', '\0', ':')):
        raise ValueError('Unsafe download filename')
    return value


def verify(manifest, output=None, verify_only=False):
    data = json.loads(manifest.read_text())
    iso = data['iso']; safe_name(iso['file'])
    if not re.fullmatch('[0-9a-f]{64}', iso['sha256']): raise ValueError('Invalid ISO digest')
    parts = data['parts']
    if not parts or len(parts) > 1000: raise ValueError('Invalid part count')
    names = [safe_name(part['file']) for part in parts]
    if len(set(names)) != len(names): raise ValueError('Duplicate part')
    output = (output or manifest.parent / iso['file']).absolute()
    direct = len(parts) == 1 and (manifest.parent / names[0]).absolute() == output
    if not verify_only and not direct and (output.exists() or output.is_symlink()): raise FileExistsError(output)
    temporary = None; stream = None; whole = hashlib.sha256(); total = 0
    try:
        if not verify_only and not direct:
            stream = tempfile.NamedTemporaryFile(dir=output.parent, prefix='.fetian-iso-', delete=False)
            temporary = Path(stream.name)
        for part in parts:
            path = manifest.parent / part['file']
            if path.is_symlink() or not path.is_file(): raise ValueError('Part is not a regular file: ' + path.name)
            checksum = hashlib.sha256(); size = 0
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    whole.update(block); checksum.update(block); size += len(block); total += len(block)
                    if stream: stream.write(block)
            if size != part['size'] or checksum.hexdigest() != part['sha256']: raise ValueError('Part integrity failed: ' + path.name)
        if total != iso['size'] or whole.hexdigest() != iso['sha256']: raise ValueError('Reassembled ISO integrity failed')
        if stream:
            stream.flush(); os.fsync(stream.fileno()); stream.close(); stream = None
            # Hard-link creation is atomic and cannot replace an existing target.
            os.link(temporary, output)
        return output
    finally:
        if stream: stream.close()
        if temporary: temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--verify-only', action='store_true'); args = parser.parse_args()
    try: print('Integrity verified: ' + str(verify(args.manifest, args.output, args.verify_only)))
    except (OSError, ValueError, KeyError, TypeError) as error: parser.exit(1, str(error) + '\n')
