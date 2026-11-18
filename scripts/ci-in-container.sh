#!/usr/bin/env bash
set -euo pipefail
[[ ${GITHUB_ACTIONS:-} == true && $EUID == 0 && -f /.dockerenv ]] || { echo 'Run only inside the disposable CI build container.' >&2; exit 2; }
source /etc/os-release
[[ ${ID:-} == manjaro && $(uname -m) == x86_64 ]] || exit 2
mkdir -p logs
# Return only build diagnostics to the runner user, including private VM dirs.
# Do not change permissions on the build rootfs or generated ISO contents.
trap 'find logs work/vm -type d -exec chmod a+rx {} + 2>/dev/null || true; find logs work/vm -type f ! -name disk.qcow2 ! -name OVMF_VARS.fd -exec chmod a+r {} + 2>/dev/null || true' EXIT
exec > >(tee -a logs/ci-container.log) 2>&1
pacman-key --init
pacman-key --populate archlinux manjaro
# A complete upgrade keeps the rolling builder coherent; normal signatures stay on.
pacman -Syu --needed --noconfirm archlinux-keyring manjaro-keyring archiso \
  libisoburn cdrtools qemu-desktop edk2-ovmf mtools squashfs-tools rust base-devel python git
pacman -Q > logs/ci-builder-packages.txt
python3 scripts/build-environment.py --json > logs/ci-build-environment.json
bash scripts/validate-profile.sh
bash scripts/build-iso.sh
iso=$(python3 scripts/select-iso.py)
seconds=$(python3 -c 'import json; print(json.load(open("ci/manjaro.json"))["boot_seconds"])')
python3 scripts/vm-test.py --iso "$iso" --expect live-account --seconds "$seconds"
python3 scripts/record-vm-evidence.py "$iso"
python3 scripts/ci-artifact-handoff.py
