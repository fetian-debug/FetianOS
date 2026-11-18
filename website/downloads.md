# Preview downloads

Published ISO downloads appear here after the CI image checks and disposable
UEFI serial/live-account boot probe pass. These are developer previews for VM
evaluation. Installation remains disabled; graphical login and hardware
acceptance are separate checks.

<section id="releases" aria-live="polite" aria-label="Published preview downloads"><p>Checking published releases…</p></section>

<noscript><p>JavaScript is disabled. Open <a href="https://github.com/fetian-debug/FetianOS/releases">GitHub Releases</a> to see actual published assets.</p></noscript>

## First verified Sway preview — 18 November 2026

[Preview 7-1](https://github.com/fetian-debug/FetianOS/releases/tag/preview-7-1)
passed image validation and an actual disposable UEFI/live-account boot.
Download all four files below into one folder, then run the assembly command
shown below. Installation remains disabled.

- [ISO part 1](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/fetianOS-0.1.0-x86_64.iso.part001)
- [ISO part 2](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/fetianOS-0.1.0-x86_64.iso.part002)
- [Download manifest](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/sway-downloads.json)
- [Python 3 assembly helper](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/sway-assemble-iso.py)

[All checksums](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/SHA256SUMS-sway)
and [boot evidence](https://github.com/fetian-debug/FetianOS/releases/download/preview-7-1/sway-vm-evidence.json)
are included with the release. Its full ISO SHA-256 is
`bf400ab7801805d6375511d07f4c605667d73e539b1e70a06843fc33514ea11f`.
Experimental FCA is available in source and is excluded from this default image.

## Verify before using an image

Download the ISO and its `.sha256` sidecar. On Linux:

```bash
sha256sum -c IMAGE.iso.sha256
```

On PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\IMAGE.iso
```

Compare the complete digest with the sidecar. Checksums detect corruption; use
the project's own release page and recorded source commit to identify a build.

## If the ISO is split into parts

GitHub release assets must each be smaller than 2 GiB. Large images are provided
as numbered `.partNNN` files. Download every part for your chosen variant, its
`downloads.json` manifest and `assemble-iso.py` helper into the same folder.
The helper checks every part and the full ISO and refuses to replace an existing
output file. With Python 3:

```bash
python3 sway-assemble-iso.py sway-downloads.json
# For the opt-in candidate instead:
python3 hyprland-assemble-iso.py hyprland-downloads.json
```

On Windows, `py -3` can replace `python3`. Read the included `DOWNLOAD.txt`.
`SHA256SUMS-VARIANT` also covers metadata, evidence, helpers and parts.

## Choose the appropriate image

| Variant | Purpose | Default status |
|---|---|---|
| Sway | Main development image and recovery desktop | Default build |
| Hyprland | Experimental opt-in desktop candidate; Sway retained | Manual candidate build |

No matching release means no downloadable ISO has been published yet. A failed
build leaves diagnostics in Actions rather than creating a download link.

[All published releases](https://github.com/fetian-debug/FetianOS/releases) · [Build runs](https://github.com/fetian-debug/FetianOS/actions/workflows/iso-release.yml) · [Source ZIP — not an ISO](https://github.com/fetian-debug/FetianOS/archive/refs/heads/main.zip)

[UEFI VM instructions](../docs/vm-testing.md) · [CI/CD workflow](../docs/ci-cd.md) · [Build your own ISO](../docs/iso-build.md)
