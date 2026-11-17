# Troubleshooting

Build logs are under `logs/`. If `mkarchiso` is missing, install `archiso` from the configured Manjaro repositories. If the package resolver rejects a package, remove or replace only that package after checking its availability with `pacman -Si`; do not mix Arch and Manjaro repositories.
## gtk-nocsd and gtk3-nocsd conflict

Some older Manjaro Sway installations contain `gtk3-nocsd`. The current `gtk-nocsd` package replaces it and intentionally declares a conflict because it supports GTK3, GTK4, libhandy, and libadwaita.

FetianOS does not include either package in its ISO profile. If an existing installation reports this conflict during an update, migrate the old package:

```bash
sudo pacman -S gtk-nocsd
```

When pacman asks to replace `gtk3-nocsd`, confirm the replacement. Alternatively, use the repository helper:

```bash
./scripts/migrate-gtk-nocsd.sh
```

Verify that only the new package remains:

```bash
pacman -Q gtk-nocsd gtk3-nocsd
```

The expected result is `gtk-nocsd` installed and `gtk3-nocsd` not found. Do not force-install both packages with `--overwrite`; they are mutually exclusive.
