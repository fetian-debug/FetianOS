#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
python3 -m json.tool "$root/manifests/kernels.json" >/dev/null
python3 -m json.tool "$root/manifests/ai-runtimes.json" >/dev/null
python3 -m json.tool "$root/manifests/hyprland.json" >/dev/null
python3 "$root/scripts/application-audit.py" >/dev/null
python3 -m json.tool "$root/installer/plan.json" >/dev/null
awk 'NF { if (seen[$0]++) { print "Duplicate package: " $0; bad=1 } } END { exit bad }' "$root/profile/sway/packages.x86_64"
for required in linux72 linux-firmware mkinitcpio-archiso sddm gtk4 libadwaita python-gobject pciutils usbutils fwupd gammastep xdg-user-dirs pacman-contrib gvfs blueman libnotify; do
  grep -qx "$required" "$root/profile/sway/packages.x86_64" || { echo "Missing package: $required"; exit 1; }
done
for file in "$root/apps/fetian-control-center/fetian_control_center.py" "$root/apps/fetian-control-center/theme.css" "$root/apps/fetian-hardware/fetian-hardware-report" "$root/apps/fetian-health/fetian-health" "$root/Cargo.toml" "$root/Cargo.lock" "$root/system/fetian-system/src/main.rs" "$root/profile/sway/airootfs/etc/systemd/system/fetian-health.timer"; do
  test -s "$file" || { echo "Missing or empty: $file"; exit 1; }
done
echo "FetianOS profile validation passed."
