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

## kvantum-theme-matcha and kvantum-theme-matchama conflict

Manjaro Sway repositories may migrate the old `kvantum-theme-matcha` package to `kvantum-theme-matchama` (`20191119-1`). These packages provide the same Matcha Kvantum theme and intentionally conflict.

Repair the migration with:

```bash
sudo pacman -S kvantum-theme-matchama
```

Or use the Fetian Control Center under **Software → Repair theme package conflicts**. Verify the result with:

```bash
pacman -Q kvantum-theme-matchama kvantum-theme-matcha
```

Only one of the two packages should remain installed. Do not use `--overwrite` to force both packages together.
