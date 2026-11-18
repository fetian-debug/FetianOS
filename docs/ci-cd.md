# CI/CD, ISO downloads and documentation publishing

Repository: [fetian-debug/FetianOS](https://github.com/fetian-debug/FetianOS).
[Downloads](https://fetian-debug.github.io/FetianOS/downloads.html) ·
[Documentation](https://fetian-debug.github.io/FetianOS/docs/index.html) ·
[ISO builds](https://github.com/fetian-debug/FetianOS/actions/workflows/iso-release.yml) ·
[Releases](https://github.com/fetian-debug/FetianOS/releases).

## What runs

| Event | Checks | ISO / publication | Documentation |
|---|---|---|---|
| Pull request | Rust, Python, GTK, profiles, units, application entries | No privileged build or release token | Site builds; no deployment |
| Push to main | Reusable source checks | Sway ISO → embedded-image checks → real OVMF serial/live-account probe → developer prerelease | Build and deploy Pages |
| Version tag `v*` | Same checks | Same required gates; prerelease uses the existing version tag | Existing main documentation remains available |
| Manual ISO run | Same checks | Choose Sway, Hyprland or both; choose whether to publish | Separate manual Pages workflow available |

The workflow files are `.github/workflows/source-checks.yml`, `iso-release.yml`
and `docs-pages.yml`. Official GitHub actions are pinned to inspected commit
SHAs. Checkout does not persist credentials. Pull requests do not receive a
privileged build container, deployment permissions or release write token.

## ISO builder

The first published image is [preview-7-1](https://github.com/fetian-debug/FetianOS/releases/tag/preview-7-1),
from [successful run 44327200378](https://github.com/fetian-debug/FetianOS/actions/runs/44327200378).
Its two uploaded ISO-part digests and downloaded metadata checksums were verified
against the release manifest; its own VM evidence identifies the tested image.
The root build container returns only public output bundles to the checkout
owner before host-side packaging. Atomic bundle directories remain private;
the embedded OS root filesystem is not part of that ownership transfer.

CI stages Zstandard-compressed SquashFS for faster image construction and
decompression. Native builds default to XZ; `FETIAN_ISO_COMPRESSION=zstd` selects
the explicit CI option locally. The staged profile records the actual choice.
Documentation-only pushes deploy the site without rebuilding an unchanged OS.

The disposable Ubuntu hosted runner provides Docker; the ISO is built inside
the official Manjaro base image described by
[Manjaro's container project](https://github.com/manjaro/manjaro-docker).
`ci/manjaro.json` selects image/platform, free-space threshold, boot deadline and
release part size. The resolved image digest is recorded before execution.

`scripts/ci-build-iso.sh` receives no GitHub token inside the privileged build
container. Only the checkout is explicitly bind-mounted; no Docker socket or
personal user directory is mounted. Privileged mode grants broad device access
on this disposable runner, but no host disk is selected as a build or VM target.
Privileges permit Archiso's chroot/mount operations. An earlier guarded step removes only
named, unused SDK directories on a GitHub-hosted runner to make disk space.

Inside the container, `ci-in-container.sh` initializes the supplied distribution
keyrings, performs a full signed package upgrade, installs build/test tools,
records builder packages/capabilities and invokes the existing ISO builder.
Signature checks are not disabled. Manjaro repositories still move, so recording
a container digest and commit timestamp does not establish reproducibility.

Both stage and embedded squashfs must pass the existing static validators.
The existing disposable VM runner then boots the actual ISO under paired OVMF
firmware, using KVM if accessible or software emulation otherwise. It must
observe Linux userspace and the live-user readiness marker. `record-vm-evidence.py`
matches the ISO digest, serial log and evidence before marking only serial
boot/live-account observation as passed. GUI/login, installation, hardware and
reproducibility flags stay false. No installation or disk formatting occurs.

Hyprland stays opt-in and its package cohort remains pinned. If mirrors no
longer provide that exact signed cohort, the candidate build fails visibly;
update/retest the manifest or provide a matching snapshot rather than silently
switching versions. Sway remains the default image and recovery session.

## Download publication

Successful runs retain the ISO/checksum/metadata assets for 14 days in Actions.
Diagnostics are uploaded even after build/boot failure. The separate publisher
has `contents:write` but no privileged container. It verifies every asset against
checksums and checks repository/commit/run identity before creating a draft.
Only after every upload succeeds does it expose a developer prerelease.
There is no force-push or asset overwrite. Interrupted publication leaves a
draft for diagnosis rather than a partial public download.

Main builds create unique `preview-RUNNUMBER-ATTEMPT` tags; `v*` builds use their
existing tag. Manual publication is permitted only from main or a version tag.
Both-image runs publish only if the entire requested matrix succeeds.

Each variant includes build.json, packages.json, VM evidence, serial log, the
ISO checksum, a downloads.json manifest, assembly helper and SHA256SUMS list.
Files are variant-prefixed where necessary to avoid collisions.

[GitHub limits individual release assets to less than 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
Larger ISOs are split into 1,900 MiB parts. The Python standard-library assembly
helper verifies each part and the full ISO, uses a temporary file and refuses
to replace an existing output. Parts are data, never shell commands. See the
[download instructions](../website/downloads.md). SHA-256 is integrity evidence,
not a claim that the ISO has a signing identity or Secure Boot chain.

## Hosted docs and downloads

The Pages workflow uses Python-Markdown from Ubuntu's signed package repositories
and `scripts/build-docs.py` to render the existing documentation, tables and code
blocks. Local document/image links are rewritten for project Pages paths; links
to implementation files point at the deployed source commit. The source Markdown
and public JSON audits remain accessible. No site generator runs inside the ISO.

The download page queries actual published GitHub releases. It includes
prereleases, ignores drafts, validates download URL origins and renders release
names as text. Until a completed release exists it says so, with build logs and
source ZIP linked separately. It never invents an ISO URL or calls a source ZIP
an image. API/network/rate-limit failure leaves a link to the releases page.

Pages must use GitHub Actions as its publishing source. The repository owner can
enable it in Settings → Pages, or with:

```bash
gh api --method POST repos/fetian-debug/FetianOS/pages -f build_type=workflow
```

No PAT or extra secret is required in workflows: ordinary read permission for
checks, `contents:write` only for release publishing, and `pages:write` plus
`id-token:write` only for deployment.

## Run and inspect

```bash
gh workflow run iso-release.yml --repo fetian-debug/FetianOS -f desktop=sway -F publish=true
gh workflow run iso-release.yml --repo fetian-debug/FetianOS -f desktop=hyprland -F publish=false
gh run list --repo fetian-debug/FetianOS --workflow iso-release.yml
gh run view RUN_ID --repo fetian-debug/FetianOS --log-failed
gh release list --repo fetian-debug/FetianOS
```

Local site build, with Python-Markdown installed in a development environment:

```bash
python3 scripts/build-docs.py --output .build-tools/site-review
python3 -m http.server --directory .build-tools/site-review 8000
```

Do not run the privileged CI wrapper on a personal host. Existing native Manjaro
build commands remain in [ISO construction](iso-build.md). A failed gate must be
fixed and rerun; it must not be relabeled as a successful build or installation.
