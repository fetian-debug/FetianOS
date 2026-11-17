#!/usr/bin/env bash
set -euo pipefail

if ! command -v pacman >/dev/null; then echo 'pacman is required.' >&2; exit 1; fi
if pacman -Q kvantum-theme-matcha >/dev/null 2>&1; then
  echo 'Replacing kvantum-theme-matcha with Manjaro Sway kvantum-theme-matchama.'
  sudo pacman -S kvantum-theme-matchama
else
  echo 'kvantum-theme-matcha is not installed; nothing to migrate.'
fi
