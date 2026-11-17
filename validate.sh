#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$(readlink -f "$0")")/scripts/verify-iso.sh" "$@"
