#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
mkdir -p "$root/logs" "$root/output"
install -Dm755 "$root/apps/fetian-control-center/fetian_control_center.py" "$root/profile/sway/airootfs/usr/share/fetian-control-center/fetian_control_center.py"
install -Dm644 "$root/apps/fetian-control-center/theme.css" "$root/profile/sway/airootfs/usr/share/fetian-control-center/theme.css"
install -Dm755 "$root/apps/fetian-hardware/fetian-hardware-report" "$root/profile/sway/airootfs/usr/bin/fetian-hardware-report"
install -Dm755 "$root/apps/fetian-health/fetian-health" "$root/profile/sway/airootfs/usr/bin/fetian-health"
install -Dm755 "$root/apps/fetian-desktop/fetian-power-profile" "$root/profile/sway/airootfs/usr/bin/fetian-power-profile"
install -Dm755 "$root/apps/fetian-desktop/fetian-power-status" "$root/profile/sway/airootfs/usr/bin/fetian-power-status"
install -Dm755 "$root/apps/fetian-desktop/fetian-calendar.py" "$root/profile/sway/airootfs/usr/share/fetian-calendar/fetian-calendar.py"
install -Dm755 "$root/apps/fetian-desktop/fetian-calendar.py" "$root/profile/sway/airootfs/usr/bin/fetian-calendar"
install -Dm755 "$root/apps/fetian-desktop/fetian-apps" "$root/profile/sway/airootfs/usr/bin/fetian-apps"
install -Dm644 "$root/apps/fetian-desktop/online.fetian.Calendar.desktop" "$root/profile/sway/airootfs/usr/share/applications/online.fetian.Calendar.desktop"
install -Dm644 "$root/apps/fetian-desktop/online.fetian.Apps.desktop" "$root/profile/sway/airootfs/usr/share/applications/online.fetian.Apps.desktop"
install -Dm644 "$root/apps/fetian-control-center/online.fetian.ControlCenter.desktop" "$root/profile/sway/airootfs/usr/share/applications/online.fetian.ControlCenter.desktop"
chmod 755 "$root/profile/sway/airootfs/usr/bin/fetian-control-center"
mkdir -p "$root/profile/sway/airootfs/etc/systemd/system/multi-user.target.wants"
ln -sf ../fetian-health.service "$root/profile/sway/airootfs/etc/systemd/system/multi-user.target.wants/fetian-health.service"
log="$root/logs/build.log"
exec > >(tee -a "$log") 2>&1
"$root/scripts/inspect-host.sh"
"$root/scripts/install-dependencies.sh"
if [[ $EUID -ne 0 ]]; then echo 'mkarchiso needs root. Re-run with: sudo ./build.sh'; exit 3; fi
stamp=$(date +%Y%m%d%H%M%S)
work="$root/work/$stamp"
mkdir -p "$work"
mkarchiso -v -w "$work" -o "$root/output" "$root/profile/sway"
iso=$(find "$root/output" -maxdepth 1 -type f -name '*.iso' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
[[ -n "$iso" && -s "$iso" ]]
sha256sum "$iso" | tee "$iso.sha256"
cp "$root/manifests/kernels.json" "$root/output/kernel-manifest.json"
cp "$root/manifests/ai-runtimes.json" "$root/output/ai-compatibility.json"
find "$root/profile/sway/airootfs" -type f -printf '%P\n' | sort > "$root/output/package-manifest.txt"
