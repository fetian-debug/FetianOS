#!/usr/bin/env bash
set -euo pipefail
# Archiso 91 runs this after ALPM finishes and before copying /boot or compressing.
# Retry guarded image-only helpers if an ALPM hook failed; abort before packing
# any unfinished image. This file is removed by mkarchiso after success.
/usr/bin/python3 /usr/lib/fetian/build_live_initramfs.py
/usr/bin/python3 /usr/lib/fetian/image_policy.py
for marker in /etc/fetian/image-build /etc/fetian/application-image-build; do
  [[ ! -e "$marker" && ! -L "$marker" ]] || { echo "Unfinished image customization: $marker" >&2; exit 1; }
done
for artifact in /boot/vmlinuz-fetian /boot/initramfs-fetian.img; do
  [[ -f "$artifact" && -s "$artifact" ]] || { echo "Missing image boot artifact: $artifact" >&2; exit 1; }
done
