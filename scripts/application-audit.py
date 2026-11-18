#!/usr/bin/env python3
"""Audit declared applications and source desktop/MIME entries; remove nothing."""
import argparse
import configparser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = {"mesa", "vulkan-intel", "vulkan-radeon", "gtk4", "libadwaita", "python-gobject", "networkmanager-qt", "libnotify", "hwdata"}
DEVELOPER = {"base-devel", "git", "python-pip", "nodejs", "npm", "docker", "vim"}


def audit(root=ROOT):
    policy = json.loads((root / "manifests/applications.json").read_text())
    packages = (root / "profile/sway/packages.x86_64").read_text().split()
    if len(packages) != len(set(packages)): raise ValueError("Duplicate base package")
    tasks = policy["tasks"]
    rows = []
    for package in packages:
        primary = [name for name, task in tasks.items() if package in task.get("packages", [])]
        backend = [name for name, task in tasks.items() if package in task.get("backends", [])]
        optional = [name for name, task in tasks.items() if package in task.get("optional", [])]
        kind = "library_or_data" if package in LIBRARIES else "primary_application" if primary else "optional_application" if optional else "delegated_backend" if backend else "developer_tool" if package in DEVELOPER else "system_utility_or_service"
        rows.append({"package": package, "classification": kind, "primary_for": primary, "backend_for": backend,
                     "optional_for": optional, "removal_eligible": False, "removal_risk": "unverified replacement or dependency closure"})
    missing = {package for task in tasks.values() for package in task.get("packages", []) if package not in packages}
    if missing: raise ValueError("Primary application absent from base profile: " + ", ".join(sorted(missing)))
    desktop_entries = []
    for folder in ("apps", "system/boot/airootfs", "desktop/hyprland/airootfs", "profile/sway/airootfs"):
        for path in sorted((root / folder).rglob("*.desktop")):
            config = configparser.ConfigParser(interpolation=None, strict=False); config.read(path, encoding="utf-8")
            if config.has_section("Desktop Entry"):
                entry = config["Desktop Entry"]
                desktop_entries.append({"source": path.relative_to(root).as_posix(), "id": path.name, "name": entry.get("Name"),
                                        "exec": entry.get("Exec"), "mime": entry.get("MimeType", "").split(";"), "hidden": entry.get("NoDisplay", "false")})
    mime = configparser.ConfigParser(interpolation=None); mime.optionxform = str
    mime.read(root / "system/boot/airootfs/etc/xdg/mimeapps.list")
    defaults = dict(mime["Default Applications"])
    if any(len(list(filter(None, value.split(";")))) != 1 for value in defaults.values()): raise ValueError("More than one primary MIME handler")
    candidate = json.loads((root / "manifests/hyprland.json").read_text())
    cohort = []
    for package, metadata in candidate["packages"].items():
        kind = "compositor" if package == "hyprland" else "session_backend" if package in ("hypridle", "hyprlock", "sddm") or package.startswith("xdg-desktop-portal-") else "library_or_runtime"
        cohort.append({"package": package, "classification": kind, "already_in_base": package in packages,
                       "recorded_version": metadata["version"], "recorded_dependencies": metadata.get("depends", []),
                       "recorded_licenses": metadata.get("license", []), "removal_eligible": False,
                       "status": "opt-in pinned cohort; not an installed-image inventory"})
    return {"schema_version": 1, "scope": "declared source inventory, not an installed image inventory",
            "policy": policy, "base_packages": rows, "source_desktop_entries": desktop_entries, "mime_defaults": defaults,
            "hyprland_cohort": cohort, "optional_post_install_runtimes": json.loads((root / "manifests/ai-runtimes.json").read_text()),
            "first_party_source_folders": sorted(path.name for path in (root / "apps").iterdir() if path.is_dir() and path.name != "__pycache__"),
            "packages_removed": [], "dependency_resolution": "Transitive dependencies and exact licenses are recorded from the real image pacman database at build time"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.parse_args()
    try: print(json.dumps(audit(), indent=2, ensure_ascii=False))
    except (OSError, ValueError, KeyError, configparser.Error) as error: parser.exit(1, str(error) + "\n")
