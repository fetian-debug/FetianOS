#!/usr/bin/env bash
set -euo pipefail
root=$(dirname "$(dirname "$(readlink -f "$0")")")
cd "$root"
[[ ${GITHUB_ACTIONS:-} == true && ${RUNNER_OS:-} == Linux && ${RUNNER_ENVIRONMENT:-} == github-hosted ]] || { echo 'This wrapper is for disposable Linux GitHub-hosted runners.' >&2; exit 2; }
desktop=${FETIAN_DESKTOP:-sway}
case "$desktop" in sway|hyprland) ;; *) exit 2 ;; esac
command -v docker >/dev/null
mkdir -p logs
python3 - <<'PY'
import json, pathlib, shutil
config = json.loads(pathlib.Path('ci/manjaro.json').read_text())
available = shutil.disk_usage('.').free / 1024**3
print(f'Free space: {available:.1f} GiB; required: {config["minimum_free_gib"]} GiB')
if available < config['minimum_free_gib']: raise SystemExit('Insufficient disposable runner space; see docs/ci-cd.md.')
PY
image=$(python3 -c 'import json; print(json.load(open("ci/manjaro.json"))["image"])')
docker pull --platform linux/amd64 "$image"
resolved=$(docker image inspect --format '{{index .RepoDigests 0}}' "$image")
printf '%s\n' "$resolved" > logs/ci-container-digest.txt
export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export FETIAN_DESKTOP="$desktop"
# No GitHub credential or Docker socket is passed. Privileged mode has broad
# access to this disposable runner; no host disk is selected as a build/VM target.
docker run --rm --privileged --platform linux/amd64 \
  --mount "type=bind,source=$root,target=/workspace" --workdir /workspace \
  --env FETIAN_DESKTOP --env SOURCE_DATE_EPOCH \
  --env FETIAN_ISO_COMPRESSION=zstd \
  --env GITHUB_ACTIONS --env GITHUB_SHA --env GITHUB_REPOSITORY \
  --env GITHUB_RUN_ID --env GITHUB_RUN_ATTEMPT --env GITHUB_SERVER_URL \
  --env FETIAN_BUILD_CONTAINER="$resolved" \
  "$resolved" /bin/bash scripts/ci-in-container.sh
