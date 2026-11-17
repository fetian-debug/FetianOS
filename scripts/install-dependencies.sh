#!/usr/bin/env bash
set -euo pipefail
need=(mkarchiso xorriso qemu-system-x86_64 isoinfo)
missing=(); for x in "${need[@]}"; do command -v "$x" >/dev/null || missing+=("$x"); done
if ((${#missing[@]})); then
  echo "Missing tools: ${missing[*]}"
echo "Install archiso, libisoburn, qemu-desktop, and cdrtools with: sudo pacman -S --needed archiso libisoburn qemu-desktop cdrtools"
  exit 2
fi
echo 'Build dependencies are available.'
