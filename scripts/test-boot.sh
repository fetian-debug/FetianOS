#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
iso=${FETIAN_ISO:-$(python3 "$root/scripts/select-iso.py")}
[[ -n "$iso" ]] || { echo 'No ISO found.'; exit 1; }
mkdir -p "$root/logs"
# This profile is UEFI-only. QEMU's default BIOS cannot boot it.
firmware="${OVMF_CODE:-}"
if [[ -z "$firmware" ]]; then
  for candidate in /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/edk2/x64/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE.fd; do
    if [[ -r "$candidate" ]]; then firmware="$candidate"; break; fi
  done
fi
[[ -n "$firmware" && -r "$firmware" ]] || { echo 'UEFI firmware missing. Install edk2-ovmf or set OVMF_CODE.' >&2; exit 2; }
if [[ -e /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then accel=(-enable-kvm); else accel=(); echo 'KVM unavailable; using software emulation.'; fi
status=0
timeout 90 qemu-system-x86_64 "${accel[@]}" -bios "$firmware" -m 2048 -smp 2 -cdrom "$iso" -boot d -display none -serial stdio -no-reboot -no-shutdown > "$root/logs/qemu-boot.log" 2>&1 || status=$?
if [[ $status != 0 && $status != 124 ]]; then
  echo "QEMU failed (exit $status); inspect logs/qemu-boot.log" >&2
  exit 1
fi
# Require Linux userspace evidence rather than matching generic firmware 'boot' text.
grep -Eq 'systemd\[[0-9]+\]:|Welcome to .*Fetian|Reached target .*Multi-User|login:' "$root/logs/qemu-boot.log" || {
  echo 'No Linux userspace evidence; inspect logs/qemu-boot.log. Desktop and installer remain unverified.' >&2
  exit 1
}
echo 'Linux userspace boot evidence found. This does not validate the graphical desktop or installation.'
if [[ ${FETIAN_EXPECT_LIVE_ACCOUNT:-0} == 1 ]]; then
  grep -q '^.*FETIANOS_LIVE_LOGIN_READY' "$root/logs/qemu-boot.log" || {
    echo 'Live account readiness marker missing; inspect fetian-live-user.service in the VM.' >&2
    exit 1
  }
  echo 'Live account provisioning reported ready. Graphical login and unlock still need interactive testing.'
fi
