# FetianOS

FetianOS 0.1.0 Developer Preview is a Manjaro-compatible, Sway-first Linux distribution for developers. It is authored for **fetian.online** and is not affiliated with Manjaro or Arch Linux.

## Build

```sh
make inspect
make setup
make profile-check
make build
make validate
make test
```

The build requires root privileges for `mkarchiso` and uses signed Manjaro repositories. It never formats disks or changes the host bootloader.

See [docs/product.md](docs/product.md) for the product charter and release criteria. Installed tools include `fetian-control-center`, `fetian-hardware-report`, and `fetian-health`.

For live UI, theme, Sway, and desktop development without rebuilding or rebooting, see [docs/development.md](docs/development.md) and run `make dev`.

## Scope

The first image contains Sway, Waybar, Foot, Wofi, Mako, PipeWire, NetworkManager, Calamares, development essentials, English/Arabic locale support, and FetianOS branding. AI, Flutter/Android, and GPU-specific stacks are optional post-install profiles and do not download models during ISO creation.

## License

FetianOS project files are licensed under MIT. Third-party packages retain their upstream licenses.
