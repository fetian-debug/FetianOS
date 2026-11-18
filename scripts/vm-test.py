#!/usr/bin/env python3
"""Bounded OVMF boot probe; attaches only a disposable qcow2, never host disks."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "work/vm"


def module(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), Path(__file__).with_name(name + ".py"))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def checked_iso(path):
    path = path.absolute()
    if path.is_symlink() or not path.is_file(): raise ValueError("Select a regular ISO file")
    checksum = path.with_name(path.name + ".sha256").read_text().split()
    if len(checksum) != 2 or not re.fullmatch("[0-9a-f]{64}", checksum[0]) or checksum[1] != path.name:
        raise ValueError("Expected a relative single-file SHA-256 sidecar")
    if module("release-artifacts").digest(path) != checksum[0]: raise ValueError("ISO checksum mismatch")
    return path, checksum[0]


def disk_path(run):
    run = run.absolute()
    # Resolve and compare every parent: a resumed run cannot escape through links.
    if run.resolve() != run or run.parent != RUNS.resolve(): raise ValueError("Resume only a direct, non-symlink run under work/vm")
    disk = run / "disk.qcow2"
    info = disk.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid(): raise ValueError("Disposable disk must be a regular file owned by this user")
    record = json.loads((run / "disposable.json").read_text())
    if record.get("kind") != "fetian-disposable-vm" or record.get("disk") != "disk.qcow2": raise ValueError("Missing disposable-disk provenance")
    details = json.loads(subprocess.run(["qemu-img", "info", "--output=json", str(disk)], text=True, capture_output=True, check=True).stdout)
    if details.get("format") != "qcow2" or details.get("backing-filename"):
        raise ValueError("Only self-contained qcow2 disks are accepted")
    return disk


def command(run, firmware, variables, iso, display, acceleration):
    for value in (run, firmware, variables, iso):
        if value and "," in str(value): raise ValueError("QEMU drive paths must not contain commas")
    arguments = ["qemu-system-x86_64", "-machine", "q35", "-accel", acceleration, "-m", "4096", "-smp", "2",
                 "-drive", f"if=pflash,format=raw,readonly=on,file={firmware}",
                 "-drive", f"if=pflash,format=raw,file={variables}",
                 "-drive", f"file={run / 'disk.qcow2'},format=qcow2,if=virtio",
                 "-nic", "user,model=virtio-net-pci", "-device", "virtio-vga", "-display", display,
                 "-serial", f"file:{run / 'serial.log'}", "-monitor", "none", "-no-reboot"]
    if iso: arguments += ["-drive", f"file={iso},media=cdrom,format=raw,readonly=on", "-boot", "order=d"]
    else: arguments += ["-boot", "order=c"]
    return arguments


def qmp(path, execute, arguments=None):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(3); client.connect(str(path))
        with client.makefile("rwb") as stream:
            stream.readline()
            for request in ({"execute": "qmp_capabilities", "id": "cap"}, {"execute": execute, "arguments": arguments or {}, "id": "cmd"}):
                stream.write((json.dumps(request) + "\n").encode()); stream.flush()
                while True:
                    line = stream.readline()
                    if not line: raise OSError("QMP connection closed")
                    response = json.loads(line)
                    if response.get("id") == request["id"]:
                        if "error" in response: raise OSError(str(response["error"]))
                        break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path)
    parser.add_argument("--resume-installed", type=Path, help="Reboot a previous disposable disk without ISO; this does not install an OS")
    parser.add_argument("--display", choices=("none", "gtk"), default="none")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--expect", choices=("userspace", "live-account"), default="userspace")
    args = parser.parse_args()
    if not 10 <= args.seconds <= 3600: parser.error("seconds must be between 10 and 3600")
    if args.iso and args.resume_installed: parser.error("Installed reboot must not attach an ISO")
    if args.resume_installed and args.expect == "live-account": parser.error("Installed reboot must never expect a live account")
    capabilities = module("build-environment").report()
    if not capabilities["uefi_vm_dependencies_available"]:
        parser.exit(2, "QEMU/qemu-img and paired OVMF CODE/VARS required. Run scripts/build-environment.py.\n")
    firmware = Path(capabilities["ovmf_code"])
    checksum = None; iso = None
    RUNS.mkdir(parents=True, exist_ok=True)
    if args.resume_installed:
        run = args.resume_installed.absolute(); disk_path(run)
        if (run / "OVMF_VARS.fd").is_symlink() or not (run / "OVMF_VARS.fd").is_file(): raise ValueError("Missing private OVMF variables")
        # Preserve earlier live-boot evidence.
        run_log = Path(tempfile.mkdtemp(prefix="installed-", dir=run))
    else:
        iso, checksum = checked_iso(args.iso or Path(module("select-iso").select(ROOT / "output")))
        run = Path(tempfile.mkdtemp(prefix="uefi-", dir=RUNS)).resolve(); run_log = run
        subprocess.run(["qemu-img", "create", "-f", "qcow2", str(run / "disk.qcow2"), "32G"], check=True)
        (run / "disposable.json").write_text(json.dumps({"kind": "fetian-disposable-vm", "disk": "disk.qcow2", "id": uuid.uuid4().hex}))
        shutil.copyfile(capabilities["ovmf_variables"], run / "OVMF_VARS.fd")
        (run / "OVMF_VARS.fd").chmod(0o600)
        disk_path(run)
    arguments = command(run, firmware, run / "OVMF_VARS.fd", iso, args.display, "kvm" if capabilities["kvm_usable"] else "tcg")
    arguments[arguments.index("-serial") + 1] = f"file:{run_log / 'serial.log'}"
    evidence = {"schema_version": 1, "started_utc": datetime.now(timezone.utc).isoformat(), "environment": capabilities,
                "iso_sha256": checksum, "command": arguments, "disposable_disk": str(run / "disk.qcow2"),
                "installed_reboot_attempt": bool(args.resume_installed), "uefi_firmware_configured": True,
                "linux_userspace_observed": False, "live_account_reported_ready": False,
                "uefi_menu_validated": False, "graphical_login_validated": False, "installation_validated": False,
                "hardware_validated": False, "shutdown_validated": False}
    process = None; stopped_at_deadline = False
    print(f"VM artifacts: {run_log}", flush=True)
    try:
        # Short socket path avoids AF_UNIX path-length failures in deep checkouts.
        with tempfile.TemporaryDirectory(prefix="fetian-qmp-") as temporary, (run_log / "qemu.log").open("wb") as log:
            sock = Path(temporary) / "qmp.sock"
            process = subprocess.Popen(arguments + ["-qmp", f"unix:{sock},server=on,wait=off"], stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + args.seconds
            while process.poll() is None and time.monotonic() < deadline: time.sleep(0.25)
            if process.poll() is None:
                stopped_at_deadline = True
                try: qmp(sock, "screendump", {"filename": str(run_log / "screen.ppm")})
                except (OSError, ValueError) as error: evidence["screenshot_error"] = str(error)
                try: qmp(sock, "system_powerdown")
                except (OSError, ValueError): pass
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.terminate()
            try: evidence["qemu_exit"] = process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); evidence["qemu_exit"] = process.wait()
        serial = (run_log / "serial.log").read_text(errors="replace") if (run_log / "serial.log").exists() else ""
        evidence["linux_userspace_observed"] = bool(re.search(r"systemd\[\d+\]:|Reached target .*Multi-User|login:", serial))
        evidence["live_account_reported_ready"] = "FETIANOS_LIVE_LOGIN_READY" in serial
        evidence["stopped_at_deadline"] = stopped_at_deadline
        passed = (evidence["qemu_exit"] == 0 or stopped_at_deadline) and evidence["linux_userspace_observed"] and (args.expect != "live-account" or evidence["live_account_reported_ready"])
        evidence["probe_passed"] = passed
    finally:
        if process is not None and process.poll() is None: process.kill(); process.wait()
        (run_log / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("Serial boot probe passed; graphical login and installation remain separate checks." if passed else "Boot evidence missing; inspect serial.log and qemu.log.")
    return 0 if passed else 1


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error: raise SystemExit(str(error))
