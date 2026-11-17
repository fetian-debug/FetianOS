#!/usr/bin/env bash
set -u
root=$(dirname "$(dirname "$(readlink -f "$0")")")
mkdir -p "$root/logs"
out="$root/logs/host-inspection.txt"
{ date -Is; uname -a; cat /etc/os-release; lscpu; free -h; df -h "$root"; findmnt -no SOURCE,FSTYPE,OPTIONS "$root"; lspci 2>/dev/null | grep -Ei 'vga|3d|display|network|audio' || true; command -v qemu-system-x86_64 || true; command -v mkarchiso || true; command -v xorriso || true; } | tee "$out"
