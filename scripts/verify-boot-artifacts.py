#!/usr/bin/env python3
"""Reject an image whose UEFI entries reference absent or unsafe boot files."""
import argparse
import configparser
from pathlib import Path, PurePosixPath
import subprocess
import stat
import json
import shlex
import struct


def validate(entries, files):
    if not entries:
        raise ValueError("No UEFI loader entries found")
    for name, text in entries.items():
        kernel = False
        initrd = False
        options = []
        for line in text.splitlines():
            fields = line.strip().split(None, 1)
            if len(fields) != 2 or fields[0].startswith("#"):
                continue
            key, value = fields
            if key in ("linux", "initrd"):
                path = PurePosixPath(value)
                if not path.is_absolute() or ".." in path.parts or "%" in value or value not in files:
                    raise ValueError(f"{name}: missing or unsafe {key} artifact: {value}")
                kernel |= key == "linux"
                initrd |= key == "initrd"
            if key == "options":
                options = value.split()
        if not kernel or not initrd or "archisobasedir=fetianos" not in options or any("%" in option for option in options):
            raise ValueError(f"{name}: incomplete live boot entry")
        if "recovery" in name and "systemd.unit=multi-user.target" not in options:
            raise ValueError("Recovery must remain independent of graphical startup")


def verify_iso(iso, run=subprocess.run):
    listing = run(["isoinfo", "-R", "-f", "-i", str(iso)], text=True, capture_output=True, check=True).stdout
    files = set(listing.splitlines())
    names = sorted(name for name in files if name.startswith("/loader/entries/") and name.endswith(".conf"))
    entries = {name: run(["isoinfo", "-R", "-i", str(iso), "-x", name], text=True, capture_output=True, check=True).stdout for name in names}
    validate(entries, files)
    firmware = next((name for name in files if name.casefold() == "/efi/boot/bootx64.efi"), None)
    if not firmware or "/fetianos/x86_64/airootfs.sfs" not in files:
        raise ValueError("EFI fallback executable or live root filesystem is missing")
    image = run(["isoinfo", "-R", "-i", str(iso), "-x", firmware], capture_output=True, check=True).stdout
    if len(image) < 64 or not image.startswith(b"MZ"):
        raise ValueError("EFI fallback executable is not a PE image")
    offset = struct.unpack_from("<I", image, 0x3c)[0]
    if offset + 26 > len(image) or image[offset:offset + 4] != b"PE\0\0" or struct.unpack_from("<H", image, offset + 4)[0] != 0x8664:
        raise ValueError("EFI fallback executable lacks an x86_64 PE header")


def rooted(root, value):
    pending = list(PurePosixPath(value).parts); current = []; links = 0
    while pending:
        part = pending.pop(0)
        if part in ("/", "."): continue
        if part == "..":
            if not current: raise ValueError("Target symlink escapes the image")
            current.pop(); continue
        candidate = root.joinpath(*current, part)
        if candidate.is_symlink():
            links += 1
            if links > 40: raise ValueError("Target symlink loop")
            target = PurePosixPath(candidate.readlink().as_posix())
            if target.is_absolute(): current = []
            pending = list(target.parts) + pending
        else: current.append(part)
    return root.joinpath(*current)


def verify_rootfs(root, complete=False):
    for name in ("etc/fetian/image-build", "etc/pacman.d/hooks/99-zz-fetian-live-boot.hook",
                 "etc/fetian/application-image-build", "etc/pacman.d/hooks/99-zzyy-fetian-applications.hook",
                 "etc/mkinitcpio.conf.d/fetian-live.conf", "etc/sudoers.d/90-fetian-live"):
        path = root / name
        if path.exists() or path.is_symlink():
            raise ValueError(f"Image has unfinished build or prematurely provisioned live state: {name}")
    if (root / 'root/customize_airootfs.sh').exists(): raise ValueError('Image customization gate was not removed')
    for name in ("usr/bin/fetian-health-rs", "usr/bin/fetian-control-center",
                 "usr/bin/fetian-sway-session", "usr/lib/fetian/display-manager"):
        path = root / name
        if not path.is_file() or not path.stat().st_mode & stat.S_IXUSR:
            raise ValueError(f"Required image executable is missing or not executable: {name}")
    preferences = configparser.ConfigParser(interpolation=None)
    preferences.optionxform = str
    preferences.read(root / "etc/xdg/mimeapps.list")
    if not preferences.has_section("Default Applications"):
        raise ValueError("Image default application preferences are missing")
    for value in preferences["Default Applications"].values():
        for desktop in filter(None, value.split(";")):
            if "/" in desktop or not (root / "usr/share/applications" / desktop).is_file():
                raise ValueError(f"Default application desktop entry missing: {desktop}")
    if not complete: return
    accounts = [line.split(":") for line in (root / "etc/passwd").read_text().splitlines() if line]
    if any(len(row) != 7 or row[0] in ("fetian", "live") for row in accounts):
        raise ValueError("Image must not ship a preprovisioned live account")
    shadow = [line.split(":") for line in (root / "etc/shadow").read_text().splitlines() if line]
    if not any(len(row) == 9 and row[0] == "root" and row[1].startswith(("!", "*")) for row in shadow):
        raise ValueError("Image root account must be locked")
    if any(len(row) != 9 or (row[1] and not row[1].startswith(("!", "*"))) or not row[1] for row in shadow):
        raise ValueError("Image must not ship usable or empty account passwords")
    machine = root / "etc/machine-id"
    if machine.is_file() and machine.read_text().strip() not in ("", "uninitialized"):
        raise ValueError("Image contains a build-host machine identity")
    if list((root / "etc/ssh").glob("ssh_host_*_key")):
        raise ValueError("Image contains shared SSH host private keys")
    policy = json.loads((root / "usr/share/fetian/applications.json").read_text())
    audit = json.loads((root / "usr/share/fetian/applications-audit.json").read_text())
    if policy["installer"]["enabled"] or audit["packages_removed"]:
        raise ValueError("Installer or package-removal promotion has not been validated")
    if policy["file_manager"]["primary"] != audit["file_manager_primary"]:
        raise ValueError("Application audit does not match policy")
    if policy["file_manager"]["primary"] != "thunar" or policy["file_manager"]["candidate_verified"]:
        raise ValueError("FetianFiles promotion requires a separate acceptance milestone")
    if preferences["Default Applications"].get("inode/directory") != policy["file_manager"]["desktop"]:
        raise ValueError("File-manager policy and MIME default disagree")
    for value in ("etc/systemd/system/display-manager.service", "etc/systemd/system/multi-user.target.wants/NetworkManager.service",
                  "etc/systemd/system/multi-user.target.wants/fetian-live-user.service",
                  "etc/systemd/system/timers.target.wants/fetian-health.timer",
                  "usr/share/licenses/fetianos/LICENSE", "usr/share/licenses/fetianos/THIRD_PARTY_NOTICES"):
        if not rooted(root, value).is_file(): raise ValueError(f"Essential image integration is missing: {value}")
    sessions = ["fetianos-sway.desktop"]
    if (root / "usr/bin/Hyprland").is_file(): sessions.append("fetianos-hyprland.desktop")
    for session in sessions:
        config = configparser.ConfigParser(interpolation=None)
        config.read(root / "usr/share/wayland-sessions" / session)
        command = shlex.split(config["Desktop Entry"]["Exec"])[0]
        if not command.startswith("/") or not rooted(root, command).is_file():
            raise ValueError(f"Session executable missing: {session}")
    for desktop in (root / "usr/share/applications").glob("*.desktop"):
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(desktop, encoding="utf-8")
        if not config.has_section("Desktop Entry"): continue
        arguments = shlex.split(config["Desktop Entry"].get("Exec", ""))
        if any(Path(arg).name in ("calamares", "calamares-oem") for arg in arguments):
            shadow = configparser.ConfigParser(interpolation=None)
            shadow.read(root / "usr/local/share/applications" / desktop.name)
            if not shadow.getboolean("Desktop Entry", "Hidden", fallback=False):
                raise ValueError("Unverified installer is still exposed in the default launcher")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("--rootfs", type=Path)
    args = parser.parse_args()
    try:
        verify_iso(args.iso)
        if args.rootfs:
            verify_rootfs(args.rootfs)
        print("UEFI entry/artifact consistency passed; boot remains a separate test.")
    except (OSError, ValueError, KeyError, configparser.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f"Boot artifact validation failed: {error}\n")
