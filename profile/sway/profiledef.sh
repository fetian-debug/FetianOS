#!/usr/bin/env bash
# Archiso 91 profile definition for FetianOS.
# Packages are resolved from the selected Manjaro stable repositories.
iso_name="fetianOS"
iso_label="FETIANOS_0_1_0"
iso_publisher="FetianOS / fetian.online"
iso_application="FetianOS Developer Preview"
iso_version="0.1.0"
install_dir="fetianos"
buildmodes=('iso')
bootmodes=('uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
)
