#!/usr/bin/env python3
"""Read-only, fail-closed installed-root policy checks; never modifies a target."""
import argparse
import configparser
import importlib.util
import json
from pathlib import Path
import re


def validate(root, username):
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username) or username in ("root", "fetian", "live"):
        raise ValueError("Choose a normal installed username distinct from live accounts")
    root = root.resolve(strict=True)
    spec = importlib.util.spec_from_file_location("image_paths", Path(__file__).with_name("verify-boot-artifacts.py"))
    paths = importlib.util.module_from_spec(spec); spec.loader.exec_module(paths)
    def target(name): return paths.rooted(root, name)
    def text(name): return target(name).read_text()
    marker = json.loads(text("etc/fetian/installed.json"))
    if marker.get("kind") != "fetian-installed" or marker.get("username") != username:
        raise ValueError("Installed target provenance is missing or inconsistent")
    forbidden = ("etc/fetian/image-build", "etc/fetian/application-image-build", "etc/sudoers.d/90-fetian-live",
                 "etc/mkinitcpio.conf.d/fetian-live.conf", "run/fetian", "run/fetian-health", "run/archiso",
                 "etc/systemd/system/fetian-live-user.service", "etc/systemd/system/multi-user.target.wants/fetian-live-user.service",
                 "usr/bin/fetian-live-setup", "usr/lib/fetian/live_setup.py",
                 "etc/systemd/system/sddm.service.d/10-fetian-live.conf", "usr/lib/fetian/display-manager",
                 "home/fetian", "home/live",
                 "etc/pacman.d/hooks/99-zz-fetian-live-boot.hook", "etc/pacman.d/hooks/99-zzyy-fetian-applications.hook")
    for name in forbidden:
        path = root / name
        if path.exists() or path.is_symlink(): raise ValueError("Live/build state remains: " + name)
    passwd = [line.split(":") for line in text("etc/passwd").splitlines() if line]
    if any(len(row) != 7 for row in passwd): raise ValueError("Malformed account database")
    if len({row[0] for row in passwd}) != len(passwd): raise ValueError("Duplicate account names")
    if any(row[0] in ("fetian", "live") or (row[0] != "root" and row[2] == "0") for row in passwd):
        raise ValueError("Live account or extra UID-0 account remains")
    users = [row for row in passwd if row[0] == username]
    roots = [row for row in passwd if row[0] == "root"]
    if len(roots) != 1 or roots[0][2] != "0": raise ValueError("Invalid root account")
    if len(users) != 1 or not users[0][2].isdigit() or int(users[0][2]) < 1000 or users[0][6] not in text("etc/shells").splitlines():
        raise ValueError("Installed user or login shell is invalid")
    if users[0][6].endswith(("nologin", "false")): raise ValueError("Installed user cannot log in")
    shadow_rows = [line.split(":") for line in text("etc/shadow").splitlines() if line]
    if any(len(row) != 9 for row in shadow_rows): raise ValueError("Malformed shadow database")
    if any(row[0] in ("fetian", "live") for row in shadow_rows): raise ValueError("Live shadow credentials remain")
    if len({row[0] for row in shadow_rows}) != len(shadow_rows): raise ValueError("Duplicate shadow records")
    if target("etc/shadow").stat().st_mode & 0o007: raise ValueError("Shadow database is readable by other users")
    shadow = {row[0]: row[1] for row in shadow_rows}
    if not shadow.get("root", "").startswith(("!", "*")): raise ValueError("Root must be locked")
    if not re.fullmatch(r"\$(?:y|6|2[aby])\$[^\s:]{16,}", shadow.get(username, "")):
        raise ValueError("Installed user requires a supported nonempty password hash")
    # Shape checks cannot prove password strength or successful authentication.
    group = [row.split(":") for row in text("etc/group").splitlines() if row]
    if not any(len(row) == 4 and row[0] == "wheel" and username in row[3].split(",") for row in group):
        raise ValueError("Installed user is missing wheel membership")
    sudo_files = [target("etc/sudoers")] + sorted(target("etc/sudoers.d").glob("*"))
    sudo_main = text("etc/sudoers")
    if "%wheel ALL=(ALL:ALL) ALL" not in sudo_main and not re.search(r"(?m)^\s*(?:#|@)includedir\s+/etc/sudoers\.d\s*$", sudo_main):
        raise ValueError("Sudo drop-in directory is not enabled")
    rules = []
    for path in sudo_files:
        path = target(path.relative_to(root).as_posix())
        if not path.is_file(): continue
        if path.stat().st_mode & 0o022: raise ValueError("Sudo configuration is writable by non-owner")
        rules += [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if any("NOPASSWD" in line or re.search(r"\b(?:fetian|live)\b", line) for line in rules):
        raise ValueError("Unsafe or live sudo rule remains")
    if "%wheel ALL=(ALL:ALL) ALL" not in rules: raise ValueError("Passworded wheel rule missing")
    configs = [target("etc/sddm.conf")] + list(target("etc/sddm.conf.d").glob("*.conf")) + list(target("usr/lib/sddm/sddm.conf.d").glob("*.conf"))
    for path in configs:
        path = target(path.relative_to(root).as_posix())
        if not path.is_file(): continue
        config = configparser.ConfigParser(interpolation=None, strict=False); config.read(path)
        if config.get("Autologin", "User", fallback="").strip(): raise ValueError("Installed autologin must be disabled")
    init = text("etc/mkinitcpio.conf")
    init += "\n" + "\n".join(target(path.relative_to(root).as_posix()).read_text() for path in target("etc/mkinitcpio.conf.d").glob("*.conf"))
    active = "\n".join(line for line in init.splitlines() if not line.lstrip().startswith("#"))
    if re.search(r"\barchiso\w*\b|\bfetian-live\b", active): raise ValueError("Live initramfs hooks remain")
    fstab = text("etc/fstab")
    if not any(len(line.split()) >= 3 and line.split()[1] == "/" and line.split()[0].startswith(("UUID=", "PARTUUID=")) for line in fstab.splitlines() if not line.lstrip().startswith("#")):
        raise ValueError("Persistent UUID-based root mount missing")
    machine_id = text("etc/machine-id").strip()
    if not re.fullmatch("[0-9a-f]{32}", machine_id) or machine_id == "0" * 32: raise ValueError("Installed machine identity missing")
    for name in ("usr/share/wayland-sessions/fetianos-sway.desktop", "usr/bin/fetian-sway-session",
                 "etc/systemd/system/display-manager.service", "boot/grub/grub.cfg"):
        if not target(name).is_file(): raise ValueError("Installed boot/session integration missing: " + name)
    return {"static_policy_passed": True, "password_authentication_tested": False, "sudo_syntax_checked": False,
            "initramfs_contents_checked": False, "bootloader_boot_tested": False, "installed_reboot_tested": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True); parser.add_argument("--username", required=True)
    args = parser.parse_args()
    try: print(json.dumps(validate(args.root, args.username), indent=2))
    except (OSError, ValueError, KeyError, configparser.Error) as error: parser.exit(1, "Installed policy failed: " + str(error) + "\n")
