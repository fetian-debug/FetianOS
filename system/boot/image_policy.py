#!/usr/bin/env python3
"""Image-only application audit. Never remove packages or touch user preferences."""
import configparser
import json
from pathlib import Path
import shlex
import sys


def installer_command(value):
    return any(Path(token).name in ("calamares", "calamares-oem") for token in shlex.split(value))


def apply_policy(root):
    marker = root / "etc/fetian/application-image-build"
    if not marker.is_file(): return False
    policy = json.loads((root / "usr/share/fetian/applications.json").read_text())
    if policy["installer"]["enabled"] or policy["installer"]["vm_install_verified"]:
        raise ValueError("Installer promotion requires a separately reviewed, tested implementation")
    if policy["file_manager"]["primary"] != "thunar" and not policy["file_manager"]["candidate_verified"]:
        raise ValueError("File-manager replacement cannot be promoted without acceptance evidence")
    hidden = []
    for path in sorted((root / "usr/share/applications").glob("*.desktop")):
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(path, encoding="utf-8")
        if config.has_section("Desktop Entry") and installer_command(config["Desktop Entry"].get("Exec", "")):
            shadow = root / "usr/local/share/applications" / path.name
            shadow.parent.mkdir(parents=True, exist_ok=True)
            shadow.write_text("[Desktop Entry]\nType=Application\nName=Installer (disabled pending VM validation)\nHidden=true\n")
            hidden.append(path.name)
    audit = {"schema_version": 1, "packages_removed": [], "installer_entries_hidden": hidden,
             "file_manager_primary": policy["file_manager"]["primary"], "candidate_verified": False}
    (root / "usr/share/fetian/applications-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (root / "etc/pacman.d/hooks/99-zzyy-fetian-applications.hook").unlink()
    marker.unlink()
    return True


if __name__ == "__main__":
    try: apply_policy(Path("/"))
    except (OSError, ValueError, KeyError) as error:
        print(f"Application image policy failed: {error}", file=sys.stderr)
        sys.exit(1)
