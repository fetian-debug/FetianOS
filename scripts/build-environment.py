#!/usr/bin/env python3
"""Read-only build/VM capability report; never installs packages or changes disks."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil

TOOLS = ("mkarchiso", "pacman", "pacman-key", "cargo", "rustc", "cc", "python3", "xorriso", "isoinfo",
         "unsquashfs", "qemu-system-x86_64", "qemu-img", "mcopy")
FIRMWARE = (("/usr/share/edk2/x64/OVMF_CODE.4m.fd", "/usr/share/edk2/x64/OVMF_VARS.4m.fd"),
            ("/usr/share/edk2/x64/OVMF_CODE.fd", "/usr/share/edk2/x64/OVMF_VARS.fd"),
            ("/usr/share/OVMF/OVMF_CODE_4M.fd", "/usr/share/OVMF/OVMF_VARS_4M.fd"),
            ("/usr/share/OVMF/OVMF_CODE.fd", "/usr/share/OVMF/OVMF_VARS.fd"))


def report():
    system = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            key, separator, value = line.partition("=")
            if separator and key in ("ID", "VERSION_ID", "PRETTY_NAME"): system[key] = value.strip('"')
    except OSError: pass
    code, variables = os.environ.get("OVMF_CODE"), os.environ.get("OVMF_VARS")
    if not code or not variables:
        code, variables = next(((c, v) for c, v in FIRMWARE if Path(c).is_file() and Path(v).is_file()), (code, variables))
    tools = {tool: shutil.which(tool) for tool in TOOLS}
    return {"schema_version": 1, "system": system, "architecture": platform.machine(),
            "tools": tools, "missing_tools": [tool for tool, path in tools.items() if path is None],
            "image_host_supported": system.get("ID") == "manjaro" and platform.machine() == "x86_64",
            "kvm_usable": os.access("/dev/kvm", os.R_OK | os.W_OK),
            "ovmf_code": code, "ovmf_variables": variables,
            "uefi_vm_dependencies_available": bool(tools["qemu-system-x86_64"] and tools["qemu-img"] and code and variables and Path(code).is_file() and Path(variables).is_file()),
            "graphical_display_configured": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
            "workspace_free_bytes": shutil.disk_usage(Path.cwd()).free,
            "tests_executed": [], "hardware_validated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(); result = report()
    if args.json: print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
        print("\nDisposable Manjaro setup (instructions only):\nsudo pacman -S --needed archiso libisoburn cdrtools qemu-desktop edk2-ovmf mtools squashfs-tools rust base-devel python")
