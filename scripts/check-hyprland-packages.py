#!/usr/bin/env python3
"""Validate candidate pins against isolated sync metadata, cache and installed DB."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile


def desc(text):
    result = {}
    for section in text.strip().split("\n\n"):
        fields = section.splitlines()
        if fields and fields[0].startswith("%"):
            result[fields[0].strip("%")] = fields[1:]
    return result


def metadata(database):
    packages = {}
    with tarfile.open(database, "r:*") as archive:
        for entry in archive:
            if entry.isfile() and entry.name.endswith("/desc"):
                fields = desc(archive.extractfile(entry).read().decode())
                packages[fields["NAME"][0]] = fields
    return packages


def verify(lock, packages, cache=None):
    for name, expected in lock["packages"].items():
        actual = packages.get(name, {})
        for field, key in (("VERSION", "version"), ("FILENAME", "filename"), ("SHA256SUM", "sha256")):
            if actual.get(field) != [expected[key]]:
                raise ValueError(f"{name}: pinned {key} mismatch; refresh the candidate explicitly or use a matching repository snapshot")
        if cache is not None:
            path = cache / expected["filename"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
                raise ValueError(f"{name}: package archive checksum mismatch")


def verify_installed(lock, database):
    packages = {}
    for path in database.glob("*/desc"):
        fields = desc(path.read_text())
        packages[fields["NAME"][0]] = fields
    for name, expected in lock["packages"].items():
        if packages.get(name, {}).get("VERSION") != [expected["version"]]:
            raise ValueError(f"{name}: installed version does not match the candidate pin")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--installed", type=Path)
    args = parser.parse_args()
    if not args.database and not args.installed:
        parser.error("--database or --installed is required")
    root = Path(__file__).resolve().parents[1]
    try:
        lock = json.loads((root / "manifests/hyprland.json").read_text())
        if args.database:
            verify(lock, metadata(args.database), args.cache)
        if args.installed:
            verify_installed(lock, args.installed)
        print("Hyprland candidate pins verified; this is not a compositor runtime test.")
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        parser.exit(1, f"Hyprland pin check failed: {error}\n")
