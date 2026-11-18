#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
cd "$root"
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo 'Native ISO components require an x86_64 Linux build host.' >&2
  exit 2
fi
command -v cargo >/dev/null || { echo 'Rust is required: install rust and a C linker, then run make native-check native.' >&2; exit 2; }
cargo build --workspace --release --locked --offline
