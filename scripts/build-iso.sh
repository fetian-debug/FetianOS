#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
desktop=${FETIAN_DESKTOP:-sway}
case "$desktop" in sway|hyprland) ;; *) echo 'FETIAN_DESKTOP must be sway or hyprland.' >&2; exit 2 ;; esac
if [[ $EUID -ne 0 ]]; then echo 'mkarchiso needs root. Re-run with sudo make build or sudo make build-hyprland.' >&2; exit 3; fi
source /etc/os-release
[[ ${ID:-} == manjaro ]] || { echo 'Use a disposable x86_64 Manjaro build host; this host is not Manjaro.' >&2; exit 2; }
mkdir -p "$root/logs" "$root/output" "$root/work"
exec > >(tee -a "$root/logs/build.log") 2>&1
"$root/scripts/inspect-host.sh"
"$root/scripts/install-dependencies.sh"
bash "$root/scripts/build-native.sh"
work=$(mktemp -d "$root/work/build-${desktop}-XXXXXXXX")
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(date +%s)}
profile="$work/profile"
python3 "$root/scripts/stage-profile.py" --desktop "$desktop" --compression "${FETIAN_ISO_COMPRESSION:-xz}" "$profile"
pacman_configuration="$profile/pacman.conf"
if [[ $desktop == hyprland ]]; then
  mkdir -p "$work/pacman/local" "$work/packages"
  # Isolated sync DB: never refresh or modify the host's installed package DB.
  pacman_args=(--config "$profile/pacman.conf" --dbpath "$work/pacman" --cachedir "$work/packages" --gpgdir /etc/pacman.d/gnupg --logfile "$work/pacman.log")
  pacman "${pacman_args[@]}" -Sy --noconfirm
  python3 "$root/scripts/check-hyprland-packages.py" --database "$work/pacman/sync/extra.db"
  mapfile -t pinned < <(python3 -c 'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["packages"]))' "$root/manifests/hyprland.json")
  pacman "${pacman_args[@]}" -Sw --noconfirm "${pinned[@]}"
  python3 "$root/scripts/check-hyprland-packages.py" --database "$work/pacman/sync/extra.db" --cache "$work/packages"
  cp "$profile/pacman.conf" "$work/pacman-build.conf"
  pacman_configuration="$work/pacman-build.conf"
  python3 - "$pacman_configuration" "$work/packages" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text(path.read_text().replace('[options]', '[options]\nCacheDir = ' + sys.argv[2], 1))
PY
fi
mkdir -p "$work/out"
mkarchiso -v -C "$pacman_configuration" -w "$work/image" -o "$work/out" "$profile"
mapfile -t databases < <(find "$work/image" -type d -path '*/airootfs/var/lib/pacman/local')
[[ ${#databases[@]} == 1 ]] || { echo 'Cannot verify the built root filesystem; image will not be published.' >&2; exit 1; }
rootfs=${databases[0]%/var/lib/pacman/local}
if [[ $desktop == hyprland ]]; then
  python3 "$root/scripts/check-hyprland-packages.py" --installed "${databases[0]}"
fi
mapfile -t images < <(find "$work/out" -maxdepth 1 -type f -name '*.iso')
[[ ${#images[@]} == 1 && -s ${images[0]} ]] || { echo 'Expected exactly one nonempty ISO.' >&2; exit 1; }
python3 "$root/scripts/release-artifacts.py" publish --iso "${images[0]}" --output "$root/output" --source "$root" --profile "$profile" --rootfs "$rootfs" --desktop "$desktop"
echo 'Verified image bundle generated. Independent byte comparison, VM boot, GUI and installation remain separate acceptance gates.'
