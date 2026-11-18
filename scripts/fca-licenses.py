#!/usr/bin/env python3
"""Collect source license files from the locked, already fetched FCA crate graph."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def collect(destination):
    if destination.exists():
        raise FileExistsError("Choose a fresh license destination")
    metadata = json.loads(subprocess.check_output([
        "cargo", "metadata", "--manifest-path", str(ROOT / "system/fetian-fca/Cargo.toml"),
        "--locked", "--offline", "--format-version", "1"]))
    destination.mkdir(parents=True)
    records = []
    for package in sorted(metadata["packages"], key=lambda p: (p["name"], p["version"])):
        if package["source"] is None:
            continue
        source = Path(package["manifest_path"]).parent
        target = destination / (package["name"] + "-" + package["version"])
        paths = [path for path in source.iterdir() if path.is_file() and
                 path.name.upper().startswith(("LICENSE", "COPYING", "NOTICE", "UNLICENSE", "COPYRIGHT", "AUTHORS"))]
        if package.get("license_file"):
            path = source / package["license_file"]
            if path.resolve().is_relative_to(source.resolve()) and path.is_file():
                paths.append(path)
        target.mkdir()
        override = ROOT / 'system/fetian-fca/license-overrides' / (package['name'] + '-' + package['version'])
        if override.is_dir():
            paths.extend(path for path in override.iterdir() if path.is_file())
        for path in set(paths):
            shutil.copyfile(path, target / path.name)
        records.append(dict(name=package["name"], version=package["version"],
                            spdx=package["license"], source=package["source"],
                            files=sorted({p.name for p in paths})))
    (destination / "index.json").write_text(json.dumps(records, indent=2) + "\n")
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(collect(args.destination)))
