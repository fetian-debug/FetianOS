#!/usr/bin/env python3
"""Return public build bundles to the checkout owner; never touch embedded rootfs."""
import os
from pathlib import Path
import stat


def handoff(workspace, change_owner=None):
    if change_owner is None:
        change_owner = os.chown
    workspace = workspace.resolve(strict=True)
    owner = workspace.stat()
    if owner.st_uid == 0:
        raise ValueError("Expected a non-root runner-owned checkout")
    output = workspace / 'output'
    if not output.exists() and not output.is_symlink():
        return 0
    if output.is_symlink() or not output.is_dir():
        raise ValueError("Output must be a real directory inside the checkout")
    paths = [output]
    for directory, folders, files in os.walk(output, followlinks=False):
        for name in folders + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("Output contains an unexpected link or special file")
            paths.append(path)
    # Validate the whole tree before changing any ownership. No chmod is needed:
    # private atomic bundle directories remain 0700, now owned by the runner.
    for path in paths:
        change_owner(path, owner.st_uid, owner.st_gid, follow_symlinks=False)
    return len(paths)


if __name__ == '__main__':
    if os.name != 'posix' or os.environ.get('GITHUB_ACTIONS') != 'true' or os.geteuid() != 0 or not Path('/.dockerenv').is_file() or Path.cwd() != Path('/workspace'):
        raise SystemExit('Run only in the disposable CI container at /workspace')
    print(f'Returned {handoff(Path("/workspace"))} public artifact paths to the runner owner.')
