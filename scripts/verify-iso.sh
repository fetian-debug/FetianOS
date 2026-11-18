#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
iso=${FETIAN_ISO:-$(python3 "$root/scripts/select-iso.py")}
[[ -n "$iso" && -s "$iso" ]] || { echo 'No ISO found.'; exit 1; }
(cd "$(dirname "$iso")" && sha256sum -c "$(basename "$iso").sha256")
mkdir -p "$root/logs"
isoinfo -d -i "$iso" | tee "$root/logs/iso-descriptor.txt"
python3 "$root/scripts/verify-boot-artifacts.py" "$iso"
echo "ISO integrity checks passed: $iso"
