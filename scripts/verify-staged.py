#!/usr/bin/env python3
"""Stage both desktops and validate unit syntax using disposable source copies."""
import importlib.util
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    spec = importlib.util.spec_from_file_location("stage", ROOT / "scripts/stage-profile.py")
    stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
    binary = ROOT / "target/release/fetian-health-rs"
    with tempfile.TemporaryDirectory(prefix="fetian-stage-check-") as temporary:
        temporary = Path(temporary)
        for desktop in ("sway", "hyprland"):
            profile = temporary / desktop; stage.stage(ROOT, profile, desktop, binary)
            subprocess.run(["bash", "-n", str(profile / "profiledef.sh")], check=True)
            units = temporary / (desktop + "-user-units"); units.mkdir()
            for source in (profile / "airootfs/usr/lib/systemd/user").iterdir():
                text = re.sub(r"^ExecStart=.*$", "ExecStart=/usr/bin/true", source.read_text(), flags=re.MULTILINE)
                (units / source.name).write_text(text)
            subprocess.run(["systemd-analyze", "--user", "verify", *map(str, units.iterdir())], check=True)
            print(f"{desktop}: staged; {len(list(units.iterdir()))} user-unit syntax checks (temporary ExecStart=/usr/bin/true)")
            audit = profile / "airootfs/usr/share/fetian-files/preferences.py"
            if not audit.is_file(): raise ValueError("FetianFiles preferences were not staged")
        metrics = temporary / "metrics"; metrics.mkdir()
        for name in ("fetian-health.service", "fetian-health.timer"):
            text = (ROOT / "profile/sway/airootfs/etc/systemd/system" / name).read_text()
            (metrics / name).write_text(text.replace("/usr/bin/fetian-health-rs", str(binary)))
        subprocess.run(["systemd-analyze", "verify", *map(str, metrics.iterdir())], check=True)
        live = temporary / "fetian-live-user.service"
        live.write_text((ROOT / "system/boot/airootfs/etc/systemd/system/fetian-live-user.service").read_text())
        live.chmod(0o644)
        subprocess.run(["systemd-analyze", "verify", str(live)], check=True)
    print("Metrics and live-user unit syntax passed. No services installed or started; runtime sandbox/session behavior remains unverified.")


if __name__ == "__main__": main()
