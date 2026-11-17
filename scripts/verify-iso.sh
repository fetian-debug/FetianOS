#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
iso=$(find "$root/output" -maxdepth 1 -type f -name '*.iso' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
[[ -n "$iso" && -s "$iso" ]] || { echo 'No ISO found.'; exit 1; }
sha256sum -c "$iso.sha256"
isoinfo -d -i "$iso" | tee "$root/logs/iso-descriptor.txt"
isoinfo -f -i "$iso" | grep -Eq 'vmlinuz|initramfs' || { echo 'Kernel/initramfs not found in ISO'; exit 1; }
echo "ISO integrity checks passed: $iso"
