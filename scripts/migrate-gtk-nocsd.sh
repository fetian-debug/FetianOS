#!/usr/bin/env bash
set -euo pipefail

if ! command -v pacman >/dev/null; then
  echo 'pacman is required.' >&2; exit 1
fi

if pacman -Q gtk3-nocsd >/dev/null 2>&1; then
  echo 'Replacing obsolete gtk3-nocsd with repository gtk-nocsd.'
  sudo pacman -S gtk-nocsd
else
  echo 'gtk3-nocsd is not installed; checking gtk-nocsd.'
  sudo pacman -S --needed gtk-nocsd
fi

echo 'GTK NoCSD migration complete.'
