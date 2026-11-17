#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
iso=$(find "$root/output" -maxdepth 1 -type f -name '*.iso' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
[[ -n "$iso" ]] || { echo 'No ISO found.'; exit 1; }
if [[ -e /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then accel=(-enable-kvm); else accel=(); echo 'KVM unavailable; using software emulation.'; fi
timeout 45 qemu-system-x86_64 "${accel[@]}" -m 2048 -smp 2 -cdrom "$iso" -boot d -display none -serial stdio -no-reboot -no-shutdown > "$root/logs/qemu-boot.log" 2>&1 || true
grep -Eqi 'kernel|boot|isolinux|grub' "$root/logs/qemu-boot.log" && echo 'VM boot probe produced boot output.' || { echo 'VM boot probe did not produce expected output; inspect logs/qemu-boot.log'; exit 1; }
