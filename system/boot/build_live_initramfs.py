#!/usr/bin/env python3
"""Image-only pacman hook: build explicit live boot artifacts from package files."""
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys


def select_kernel(paths):
    versions = {p.parts[4] for p in paths if len(p.parts) > 4 and p.parts[1:4] == ("usr", "lib", "modules")
                and re.fullmatch(r"[0-9][A-Za-z0-9._+-]*", p.parts[4])}
    if len(versions) != 1:
        raise ValueError("Expected one module version in the selected kernel package")
    kernels = [p for p in paths if p.name == "vmlinuz" or p.name.startswith("vmlinuz-")]
    if not kernels:
        raise ValueError("Selected kernel package has no kernel image")
    module_kernels = [p for p in kernels if p.parts[1:4] == ("usr", "lib", "modules")]
    if len(module_kernels) == 1:
        return next(iter(versions)), module_kernels[0]
    if len(kernels) != 1:
        raise ValueError("Ambiguous kernel images; refusing to guess")
    return next(iter(versions)), kernels[0]


def build(root=Path("/"), run=subprocess.run):
    marker = root / "etc/fetian/image-build"
    if not marker.is_file():
        return False
    result = run(["/usr/bin/pacman", "-Qql", "linux72"], text=True, capture_output=True, check=True)
    version, kernel = select_kernel([PurePosixPath(p) for p in result.stdout.splitlines() if p.startswith("/")])
    source = root / kernel.relative_to("/")
    if not source.is_file() or not (root / "usr/lib/modules" / version).is_dir():
        raise ValueError("Kernel image/modules are missing from the image root")
    boot = root / "boot"
    boot.mkdir(exist_ok=True)
    shutil.copyfile(source, boot / "vmlinuz-fetian")
    run(["/usr/bin/mkinitcpio", "--kernel", version,
         "--config", "/etc/mkinitcpio.conf.d/fetian-live.conf",
         "--generate", "/boot/initramfs-fetian.img"], check=True)
    if not (boot / "initramfs-fetian.img").is_file() or not (boot / "initramfs-fetian.img").stat().st_size:
        raise ValueError("Live initramfs was not generated")
    # The build hook cannot affect updates after this image is booted/installed.
    (root / "etc/pacman.d/hooks/99-zz-fetian-live-boot.hook").unlink()
    (root / "etc/mkinitcpio.conf.d/fetian-live.conf").unlink()
    marker.unlink()
    return True


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Live boot artifact generation failed: {error}", file=sys.stderr)
        sys.exit(1)
