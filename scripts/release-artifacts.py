#!/usr/bin/env python3
"""Create verified evidence bundles and compare real artifact bytes, not claims."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): value.update(block)
    return value.hexdigest()


def tree_manifest(root, selected=None):
    result = {}
    paths = [root / value for value in selected] if selected else [root]
    def scan(path):
        if path.is_symlink(): result[path.relative_to(root).as_posix()] = {"link": os.readlink(path)}
        elif path.is_dir():
            for child in sorted(path.iterdir()):
                if child.name not in ("__pycache__", ".git"): scan(child)
        elif path.is_file(): result[path.relative_to(root).as_posix()] = {"sha256": digest(path)}
    for path in paths:
        if path.exists() or path.is_symlink(): scan(path)
    return result


def installed_packages(root):
    packages = {}
    for path in sorted((root / "var/lib/pacman/local").glob("*/desc")):
        fields = {}
        for section in path.read_text().strip().split("\n\n"):
            lines = section.splitlines()
            if len(lines) > 1: fields[lines[0].strip("%")] = lines[1:]
        packages[fields["NAME"][0]] = {"version": fields["VERSION"][0], "licenses": fields.get("LICENSE", [])}
    if not packages: raise ValueError("Installed package inventory is empty")
    missing = [name for name, package in packages.items() if not package["licenses"]]
    if missing: raise ValueError("Package license metadata missing; review before publication: " + ", ".join(missing))
    return packages


def tool_versions():
    result = {}
    queries = {"mkarchiso": "-V", "pacman": "--version", "cargo": "--version", "rustc": "--version", "xorriso": "-version", "mksquashfs": "-version"}
    for tool, option in queries.items():
        try:
            value = subprocess.run([tool, option], text=True, capture_output=True, timeout=10, check=False)
            result[tool] = {"query": [tool, option], "exit_code": value.returncode, "banner": (value.stdout or value.stderr).strip().splitlines()[:4]}
        except (OSError, subprocess.TimeoutExpired): result[tool] = None
    return result


def validate_image(iso, rootfs):
    spec = importlib.util.spec_from_file_location("verify_image", Path(__file__).with_name("verify-boot-artifacts.py"))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.verify_iso(iso); module.verify_rootfs(rootfs, complete=True)
    # Validate the actual compressed payload as well as the build tree. Never
    # infer embedded-image correctness solely from the staging directory.
    with tempfile.TemporaryDirectory(prefix="fetian-verify-") as temporary:
        temporary = Path(temporary); squash = temporary / "airootfs.sfs"
        with squash.open("wb") as stream:
            subprocess.run(["isoinfo", "-R", "-i", str(iso), "-x", "/fetianos/x86_64/airootfs.sfs"], stdout=stream, check=True)
        extracted = temporary / "rootfs"
        subprocess.run(["unsquashfs", "-no-progress", "-d", str(extracted), str(squash)], check=True)
        module.verify_rootfs(extracted, complete=True)
        if installed_packages(extracted) != installed_packages(rootfs):
            raise ValueError("Embedded and staged package inventories disagree")
    return "image"


def publish(iso, output, source, profile, rootfs, desktop, validator=validate_image):
    if iso.is_symlink() or not iso.is_file() or iso.stat().st_size == 0: raise ValueError("A real nonempty ISO file is required")
    validation_kind = validator(iso, rootfs)
    output.mkdir(parents=True, exist_ok=True)
    checksum = digest(iso); build_id = uuid.uuid4().hex
    source_files = tree_manifest(source, ["apps", "desktop", "system", "scripts", "profile", "manifests", "installer", "tests", "docs", "ci", "website", "licenses", ".github", ".gitattributes", "Cargo.toml", "Cargo.lock", "Makefile", "build.sh", "validate.sh", "LICENSE", "THIRD_PARTY_NOTICES"])
    metadata = {"schema_version": 1, "build_id": build_id, "desktop": desktop,
                "created_utc": datetime.now(timezone.utc).isoformat(), "source_date_epoch": os.environ.get("SOURCE_DATE_EPOCH"),
                "ci": {"repository": os.environ.get("GITHUB_REPOSITORY"), "commit": os.environ.get("GITHUB_SHA"),
                       "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                       "container": os.environ.get("FETIAN_BUILD_CONTAINER")},
                "source_inputs": source_files, "profile_inputs": tree_manifest(profile),
                "packages": installed_packages(rootfs), "tool_versions": tool_versions(),
                "iso": {"file": iso.name, "sha256": checksum, "size": iso.stat().st_size},
                "verification": {"image_static_checks": validation_kind == "image", "validation_kind": validation_kind, "vm_boot": False, "graphical_login": False,
                                 "installation": False, "hardware": False, "reproducible": False}}
    # Nothing is discoverable as a release until the complete directory is renamed.
    destination = output / (iso.stem + "-" + build_id[:12])
    with tempfile.TemporaryDirectory(prefix=".candidate-", dir=output) as temporary:
        temporary = Path(temporary)
        shutil.copyfile(iso, temporary / iso.name)
        if digest(temporary / iso.name) != checksum: raise ValueError("Copied artifact checksum changed")
        (temporary / (iso.name + ".sha256")).write_text(f"{checksum}  {iso.name}\n")
        (temporary / "build.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
        (temporary / "packages.json").write_text(json.dumps(metadata["packages"], indent=2, sort_keys=True) + "\n")
        os.rename(temporary, destination)
    return destination


def compare(first, second):
    if first.resolve() == second.resolve(): raise ValueError("Select two distinct build records")
    a, b = json.loads(first.read_text()), json.loads(second.read_text())
    if a["build_id"] == b["build_id"]: raise ValueError("These records belong to the same build")
    for record, path in ((a, first), (b, second)):
        if Path(record["iso"]["file"]).name != record["iso"]["file"]: raise ValueError("Unsafe artifact filename")
        if digest(path.parent / record["iso"]["file"]) != record["iso"]["sha256"]: raise ValueError("Artifact does not match its build record")
    fields = ("source_inputs", "profile_inputs", "packages", "source_date_epoch", "tool_versions")
    differences = [field for field in fields if a[field] != b[field]]
    identical = a["iso"]["sha256"] == b["iso"]["sha256"]
    return {"iso_bytes_identical": identical, "recorded_inputs_match": not differences,
            "differing_inputs": differences, "independent_execution_attestation_required": True,
            "production_ready": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("publish")
    for name in ("iso", "output", "source", "profile", "rootfs"): command.add_argument("--" + name, type=Path, required=True)
    command.add_argument("--desktop", choices=("sway", "hyprland"), required=True)
    command = commands.add_parser("compare"); command.add_argument("first", type=Path); command.add_argument("second", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "compare": print(json.dumps(compare(args.first, args.second), indent=2))
        else: print(publish(args.iso, args.output, args.source, args.profile, args.rootfs, args.desktop))
    except (OSError, ValueError, KeyError) as error: parser.exit(1, str(error) + "\n")
