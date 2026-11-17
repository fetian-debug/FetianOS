# Building

Run `make inspect`, then install the missing host dependencies with the command printed by `make setup`. Build with `sudo make build`; the ISO is written to `output/`. `make validate` checks the checksum, ISO descriptor, and kernel/initramfs entries. `make test` performs a disposable QEMU boot probe when the ISO exists.
