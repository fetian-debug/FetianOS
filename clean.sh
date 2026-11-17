#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(readlink -f "$0")")
rm -rf "$root/work" "$root/profile/sway/airootfs/var/cache/pacman/pkg"
printf 'Removed disposable build state under %s/work\n' "$root"
