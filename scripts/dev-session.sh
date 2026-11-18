#!/usr/bin/env bash
set -euo pipefail

root=$(dirname "$(dirname "$(readlink -f "$0")")")
mode="${1:---app}"
desktop=sway
[[ -z ${HYPRLAND_INSTANCE_SIGNATURE:-} ]] || desktop=hyprland
app_pid=""
waybar_pid=""

cleanup() {
  trap - EXIT INT TERM
  [ -n "$app_pid" ] && kill "$app_pid" 2>/dev/null || true
  [ -n "$waybar_pid" ] && kill "$waybar_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

command -v python3 >/dev/null || { echo 'python3 is required'; exit 1; }
export PYTHONPATH="$root/apps/fetian-control-center${PYTHONPATH:+:$PYTHONPATH}"
export FETIAN_DEV_ROOT="$root"
export FETIAN_CONTROL_CENTER_THEME="$root/apps/fetian-control-center/theme.css"
export PATH="$root/target/release:$root/apps/fetian-dev-bin:$PATH"

start_app() {
  [ -n "$app_pid" ] && kill "$app_pid" 2>/dev/null || true
  python3 "$root/apps/fetian-control-center/fetian_control_center.py" &
  app_pid=$!
  echo "Fetian Control Center running from source (PID $app_pid)"
}

start_waybar() {
  command -v waybar >/dev/null || return 0
  [ -n "$waybar_pid" ] && kill "$waybar_pid" 2>/dev/null || true
  if [[ $desktop == hyprland ]]; then
    assets="$root/desktop/hyprland/airootfs/usr/share/fetian/hyprland"
    effects=$(cat "${XDG_CONFIG_HOME:-$HOME/.config}/fetian/effects" 2>/dev/null || true)
    style=glass
    [[ $effects != accessible && $effects != performance ]] || style=solid
    waybar -c "$assets/waybar/config.json" -s "$assets/waybar/$style.css" &
  else
    waybar -c "$root/profile/sway/airootfs/etc/xdg/waybar/config" -s "$root/profile/sway/airootfs/etc/xdg/waybar/style.css" &
  fi
  waybar_pid=$!
  echo "Waybar running from source (PID $waybar_pid)"
}

reload_desktop() {
  if [[ $desktop == hyprland ]]; then
    hyprctl reload >/dev/null 2>&1 || true
  else
    command -v swaymsg >/dev/null && swaymsg reload >/dev/null 2>&1 || true
  fi
  [ "$mode" = "--desktop" ] && start_waybar
}

start_app
[ "$mode" = "--desktop" ] && reload_desktop
echo "Hot reload active. Edit apps/, profile/sway/airootfs/etc/xdg/, or Sway config."
echo "Press Ctrl-C to stop the development processes. The installed system is unchanged."
watch_paths=("$root/apps" "$root/profile/sway/airootfs/etc/xdg" "$root/profile/sway/airootfs/etc/sway" "$root/desktop/hyprland")

if command -v inotifywait >/dev/null; then
  while inotifywait -qq -r -e close_write,create,delete,move \
    "${watch_paths[@]}"; do
    start_app
    [ "$mode" = "--desktop" ] && reload_desktop
  done
else
  echo 'inotifywait not found; using 1-second polling. Install inotify-tools for lower latency.'
  snapshot() { find "${watch_paths[@]}" -type f -printf '%T@ %p\n' 2>/dev/null | sort; }
  last=$(snapshot)
  while sleep 1; do
    current=$(snapshot)
    if [ "$current" != "$last" ]; then
      last=$current
      start_app
      [ "$mode" = "--desktop" ] && reload_desktop
    fi
  done
fi
