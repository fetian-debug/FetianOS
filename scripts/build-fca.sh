#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
cd "$root"
cargo build --manifest-path system/fetian-fca/Cargo.toml --locked "${@}"
profile=debug
for arg in "$@"; do [[ "$arg" != --release ]] || profile=release; done
install -m 644 system/fetian-fca/executors/fetian-executor-python.py "system/fetian-fca/target/$profile/fetian-executor-python.py"
