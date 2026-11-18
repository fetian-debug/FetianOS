#!/usr/bin/env bash
set -euo pipefail
need=(mkarchiso pacman pacman-key xorriso qemu-system-x86_64 qemu-img isoinfo unsquashfs mcopy cargo rustc cc python3)
missing=(); for x in "${need[@]}"; do command -v "$x" >/dev/null || missing+=("$x"); done
if ((${#missing[@]})); then
  echo "Missing tools: ${missing[*]}"
  echo "Install dependencies on a disposable Manjaro host with: sudo pacman -S --needed archiso libisoburn qemu-desktop cdrtools edk2-ovmf mtools squashfs-tools rust base-devel python"
  exit 2
fi
echo 'Build dependencies are available.'
