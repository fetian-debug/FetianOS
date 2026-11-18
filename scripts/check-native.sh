#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
cd "$root"
python=${PYTHON:-python3}
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked --offline -- -D warnings
cargo test --workspace --locked --offline
if [[ $(uname -s) == Linux ]]; then
  "$python" -m unittest discover -s tests -p 'test_*.py'
  cargo run --quiet --locked --offline --bin fetian-health-rs -- --json | "$python" -c '
import json, sys
data = json.load(sys.stdin)
assert data["schema_version"] == 1
assert data["memory"]["total_bytes"] > 0
assert 0 <= data["memory"]["used_bytes"] <= data["memory"]["total_bytes"]
assert data["cpu_usage_percent"] is None or 0 <= data["cpu_usage_percent"] <= 100
print("Live Linux telemetry JSON verified.")
'
fi
