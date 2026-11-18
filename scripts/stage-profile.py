#!/usr/bin/env python3
"""Create a fresh image profile; never modify either source profile or user config."""
import argparse
import json
from pathlib import Path
import shutil


def install(source, destination, mode=0o755):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode)


def stage(root, destination, desktop, native_binary, compression="xz"):
    if destination.exists():
        raise ValueError("Staging destination already exists; choose a fresh directory")
    if desktop not in ("sway", "hyprland"):
        raise ValueError("Unknown desktop")
    if compression not in ("xz", "zstd"): raise ValueError("Unsupported image compression")
    if not native_binary.is_file():
        raise ValueError("Rust release binary missing; run make native")
    shutil.copytree(root / "profile/sway", destination, symlinks=True)
    tree = destination / "airootfs"
    shutil.copytree(root / "system/boot/airootfs", tree, dirs_exist_ok=True, symlinks=True)
    for name in ("live_setup.py", "build_live_initramfs.py", "image_policy.py", "session_audit.py"):
        install(root / "system/boot" / name, tree / "usr/lib/fetian" / name, 0o644)
    install(root / "apps/fetian-desktop/fetian_daily.py", tree / "usr/share/fetian-desktop/fetian_daily.py", 0o644)
    for source in (root / "apps/fetian-files").iterdir():
        if source.is_file() and source.suffix in (".py", ".css"):
            install(source, tree / "usr/share/fetian-files" / source.name, 0o644)
    install(root / "apps/fetian-files/online.fetian.Files.desktop", tree / "usr/share/applications/online.fetian.Files.desktop", 0o644)
    install(root / "manifests/applications.json", tree / "usr/share/fetian/applications.json", 0o644)
    notices = tree / "usr/share/licenses/fetianos"
    install(root / "LICENSE", notices / "LICENSE", 0o644)
    install(root / "THIRD_PARTY_NOTICES", notices / "THIRD_PARTY_NOTICES", 0o644)
    shutil.copytree(root / "licenses", notices / "licenses", dirs_exist_ok=True)
    sources = {
        "apps/fetian-control-center/fetian_control_center.py": "usr/share/fetian-control-center/fetian_control_center.py",
        "apps/fetian-hardware/fetian-hardware-report": "usr/bin/fetian-hardware-report",
        "apps/fetian-health/fetian-health": "usr/bin/fetian-health",
        "apps/fetian-desktop/fetian-power-profile": "usr/bin/fetian-power-profile",
        "apps/fetian-desktop/fetian-power-status": "usr/bin/fetian-power-status",
        "apps/fetian-desktop/fetian-calendar.py": "usr/bin/fetian-calendar",
        "apps/fetian-desktop/fetian-apps": "usr/bin/fetian-apps",
        "scripts/migrate-kvantum-matcha.sh": "usr/lib/fetian/migrate-kvantum-matcha.sh",
    }
    for source, target in sources.items():
        install(root / source, tree / target)
    # Preserve the legacy path while keeping it synchronized with the real source.
    install(root / "apps/fetian-control-center/fetian_control_center.py", tree / "usr/lib/fetian-control-center/fetian_control_center.py")
    install(native_binary, tree / "usr/bin/fetian-health-rs")
    install(root / "apps/fetian-control-center/theme.css", tree / "usr/share/fetian-control-center/theme.css", 0o644)
    install(root / "apps/fetian-desktop/fetian-calendar.py", tree / "usr/share/fetian-calendar/fetian-calendar.py")
    for app, file in (("fetian-control-center", "online.fetian.ControlCenter.desktop"),
                      ("fetian-desktop", "online.fetian.Calendar.desktop"),
                      ("fetian-desktop", "online.fetian.Editor.desktop"),
                      ("fetian-desktop", "online.fetian.Apps.desktop")):
        install(root / "apps" / app / file, tree / "usr/share/applications" / file, 0o644)
    (tree / "usr/bin/fetian-control-center").chmod(0o755)
    timer = tree / "etc/systemd/system/timers.target.wants/fetian-health.timer"
    timer.parent.mkdir(parents=True, exist_ok=True)
    if not timer.is_symlink():
        timer.symlink_to("../fetian-health.timer")
    if desktop == "hyprland":
        overlay = root / "desktop/hyprland"
        shutil.copytree(overlay / "airootfs", tree, dirs_exist_ok=True, symlinks=True)
        for executable in (overlay / "bin").iterdir():
            install(executable, tree / "usr/bin" / executable.name)
        for name in ("fetian_desktop.py", "fetian_shell.py"):
            install(overlay / name, tree / "usr/share/fetian-desktop" / name, 0o644)
        lock = json.loads((root / "manifests/hyprland.json").read_text())
        package_file = destination / "packages.x86_64"
        packages = package_file.read_text().splitlines()
        packages.extend(name for name in lock["packages"] if name not in packages)
        package_file.write_text("\n".join(packages) + "\n")
        # Distinct artifacts prevent a candidate from overwriting the Sway ISO.
        with (destination / "profiledef.sh").open("a") as definition:
            definition.write('\niso_name="fetianOS-hyprland-candidate"\n')
        for name in ("hyprland.json",):
            install(root / "manifests" / name, tree / "usr/share/fetian" / name, 0o644)
    units = tree / "etc/systemd/system"
    (units / "display-manager.service").symlink_to("/usr/lib/systemd/system/sddm.service")
    (units / "default.target").symlink_to("/usr/lib/systemd/system/graphical.target")
    for target, service, destination_unit in (
        ("multi-user.target", "fetian-live-user.service", "../fetian-live-user.service"),
        ("multi-user.target", "NetworkManager.service", "/usr/lib/systemd/system/NetworkManager.service"),
        ("bluetooth.target", "bluetooth.service", "/usr/lib/systemd/system/bluetooth.service"),
    ):
        link = units / (target + ".wants") / service
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(destination_unit)
    for name in ("pipewire.socket", "pipewire-pulse.socket"):
        link = tree / "etc/systemd/user/sockets.target.wants" / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("/usr/lib/systemd/user/" + name)
    link = tree / "etc/systemd/user/pipewire.service.wants/wireplumber.service"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to("/usr/lib/systemd/user/wireplumber.service")
    link = units / "sockets.target.wants/cups.socket"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to("/usr/lib/systemd/system/cups.socket")
    # Archiso deliberately discards copied file modes. Explicitly preserve every
    # first-party executable, including the native Rust collector.
    executables = list((tree / "usr/bin").iterdir()) + [tree / "usr/lib/fetian/display-manager"]
    with (destination / "profiledef.sh").open("a") as definition:
        if compression == "zstd":
            definition.write("\n# Fast CI compression, supported by the distribution kernel.\n")
            definition.write("airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15' '-b' '1M')\n")
        definition.write("\n# Executable payload permissions required by mkarchiso.\n")
        for executable in sorted(executables):
            if executable.is_file():
                executable.chmod(0o755)
                relative = "/" + executable.relative_to(tree).as_posix()
                definition.write(f'file_permissions["{relative}"]="0:0:755"\n')
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--desktop", choices=("sway", "hyprland"), default="sway")
    parser.add_argument("--compression", choices=("xz", "zstd"), default="xz")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        stage(root, args.destination.resolve(), args.desktop, root / "target/release/fetian-health-rs", args.compression)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Profile staging failed: {error}\n")
