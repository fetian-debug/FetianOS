#!/usr/bin/env python3
"""Provision the disposable live account only after three independent live checks.

No account database is shipped or overwritten. No installed-system provisioning
is performed. The public live-media password is deliberately not an install password.
"""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

USER = "fetian"
HOME = "/home/fetian"
SDDM = "[Autologin]\nUser=fetian\nSession=fetianos-sway.desktop\nRelogin=false\n"


def is_live(root=Path("/")):
    if "archisobasedir=fetianos" not in (root / "proc/cmdline").read_text().split():
        return False
    mounts = [line.split() for line in (root / "proc/mounts").read_text().splitlines()]
    return (any(len(m) >= 3 and m[1] == "/" and m[2] == "overlay" for m in mounts)
            and any(len(m) >= 3 and m[1] == "/run/archiso/bootmnt" for m in mounts))


def command(arguments, input=None):
    return subprocess.run(arguments, input=input, text=True, capture_output=True, timeout=30, check=False)


def checked(run, arguments, input=None):
    result = run(arguments, input=input)
    if result.returncode:
        # Never include stdin/passwords or command output in service logs.
        raise RuntimeError(f"{Path(arguments[0]).name} failed (exit {result.returncode})")
    return result.stdout


def safe_regular(path, owner):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != owner:
        raise RuntimeError(f"Refusing untrusted state: {path}")


def write_state(path, text, owner, mode=0o600):
    if path.exists() or path.is_symlink():
        safe_regular(path, owner)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".fetian-", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def account(run):
    result = run(["/usr/bin/getent", "passwd", USER], input=None)
    if result.returncode == 2:
        return None
    if result.returncode:
        raise RuntimeError("Cannot query the account database")
    fields = result.stdout.strip().split(":")
    if len(fields) != 7 or fields[0] != USER or not fields[2].isdigit():
        raise RuntimeError("Invalid live account record")
    if int(fields[2]) < 1000 or fields[5] != HOME or fields[6] != "/bin/bash":
        raise RuntimeError("Refusing to modify an unexpected existing account")
    return int(fields[2])


def provision(root=Path("/"), run=command, owner=0):
    if not is_live(root):
        return False
    state = root / "run/fetian"
    state.mkdir(mode=0o700 if os.name == "posix" else 0o755, exist_ok=True)
    info = state.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != owner or (os.name == "posix" and info.st_mode & 0o077):
        raise RuntimeError("Live state directory must be private, owned by the service user and not a symlink")
    marker = state / "live-user.json"
    uid = account(run)
    recorded = None
    if marker.exists() or marker.is_symlink():
        safe_regular(marker, owner)
        recorded = json.loads(marker.read_text())
        if not isinstance(recorded, dict) or type(recorded.get("uid")) is not int or type(recorded.get("ready")) is not bool:
            raise RuntimeError("Invalid live provisioning state; refusing to guess")
    if uid is not None:
        if not recorded or recorded.get("uid") != uid:
            raise RuntimeError("Existing fetian account is not owned by this live boot; leaving it unchanged")
    else:
        if recorded or (root / HOME.lstrip("/")).exists():
            raise RuntimeError("Existing live state/home needs manual recovery; refusing to overwrite it")
        checked(run, ["/usr/bin/useradd", "--create-home", "--user-group", "--shell", "/bin/bash",
                      "--groups", "wheel", "--comment", "FetianOS Live Session", USER])
        uid = account(run)
        if uid is None:
            raise RuntimeError("Live account was not created")
        recorded = {"uid": uid, "ready": False}
        write_state(marker, json.dumps(recorded), owner)
    if not recorded.get("ready"):
        checked(run, ["/usr/bin/chpasswd"], input="fetian:fetian\n")
        checked(run, ["/usr/bin/passwd", "--lock", "root"])
        sudoers = root / "etc/sudoers.d/90-fetian-live"
        sudoers.parent.mkdir(parents=True, exist_ok=True)
        rule = "# Disposable live media only; remove during installation.\nfetian ALL=(ALL:ALL) ALL\n"
        if sudoers.exists() or sudoers.is_symlink():
            safe_regular(sudoers, owner)
            if sudoers.read_text() != rule:
                raise RuntimeError("Refusing to overwrite existing sudo configuration")
        else:
            write_state(sudoers, rule, owner, 0o440)
        try:
            checked(run, ["/usr/bin/visudo", "--check", "--file", str(sudoers)])
        except Exception:
            sudoers.unlink()
            raise
        recorded["ready"] = True
        write_state(marker, json.dumps(recorded), owner)
    config = state / "sddm-live.conf"
    if config.exists() or config.is_symlink():
        safe_regular(config, owner)
        if config.read_text() != SDDM:
            raise RuntimeError("Refusing to overwrite a changed live login configuration")
    else:
        write_state(config, SDDM, owner)
    return True


def main():
    if sys.argv[1:] == ["--is-live"]:
        return 0 if is_live() else 1
    if sys.argv[1:]:
        raise ValueError("Usage: fetian-live-setup [--is-live]")
    if not is_live():
        print("FetianOS live provisioning skipped on a non-live system.")
        return 0
    if os.name != "posix" or os.geteuid() != 0:
        raise RuntimeError("Live account provisioning requires the root boot service")
    provision()
    print("FETIANOS_LIVE_LOGIN_READY")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"fetian-live-setup: {error}", file=sys.stderr)
        sys.exit(1)
