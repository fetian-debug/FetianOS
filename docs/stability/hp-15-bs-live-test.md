# HP 15-bs0xx: first physical live-USB test

This is a test plan for the user's laptop, not hardware certification.
User-reported hardware: Intel Core i5-7200U (x86-64, two cores/four threads),
Intel HD Graphics 620 and AMD Radeon whose exact PCI model is unknown.
RAM and storage capacity/model are not yet verified. UEFI support is reported.

## Select the verified Sway candidate

Start with **FETIANOS — Sway recovery**. The stabilization Sway image at source
`4b41effbc9451c05aac19ea52c346e52df414a1c` passed UEFI/QEMU userspace and
live-account checks; graphical sign-in and this HP's devices remain untested.

[Download its candidate artifact](https://github.com/fetian-debug/FetianOS/actions/runs/44505284369/artifacts/14519783617)
from [the identified workflow](https://github.com/fetian-debug/FetianOS/actions/runs/44505284369).
GitHub sign-in may be required. These are temporary CI artifacts, not a new
published release. Preview-7-1 has not been replaced. The source ZIP and
diagnostics artifacts are not bootable ISO downloads.

Extract the artifact ZIP and keep all numbered ISO parts, manifest and assembly
helper together. With Python 3 installed, run from that directory:

```sh
python3 sway-assemble-iso.py sway-downloads.json
```

On Windows use `python` or `py -3` if that is the installed Python command.
The helper verifies every part and the complete ISO and refuses to overwrite
an existing result. Stop on any mismatch. Complete candidate ISO SHA-256:

```text
fe476ab1b14ed5b88e9ebd30088c20cca178e9dada1d0a973c18a707b24b6802
```

## Prepare and boot the USB

Use a spare USB stick with at least 8 GB capacity. Image writing erases the
selected USB: confirm its identity/capacity and back up its contents first.
Use the [official Rufus download](https://rufus.ie/) and its
[image-writing documentation](https://github.com/pbatard/rufus/wiki/FAQ).
No USB or internal drive is selected or written by this repository's test tools.
Physical USB boot of this candidate remains an acceptance test.

Connect AC power. Open the HP startup/boot-device menu with Esc/F9 and choose
the USB's **UEFI** entry; see [HP's instructions](https://www.hp.com/sg-en/tech-takes/desktops/how-to/how-to-boot-from-usb-drive-on-windows-10-pcs.html).
Legacy BIOS is not configured. Secure Boot compatibility is unverified: a
firmware rejection is a stop-and-diagnose condition. Record current settings
and know the disk-encryption recovery method before changing firmware security.

Choose normal live boot, then Sway recovery if the greeter appears. The
disposable live credential is **fetian / fetian**. Keep the installer disabled;
do not launch Calamares manually, partition disks or mount internal filesystems
read-write during this first test. The live home is temporary across reboot.
This is not yet an installed daily-use system.

## Record actual results

Open a terminal with Super+Enter. These commands inspect the running machine:

```sh
lspci -nnk
free -h
lsblk -o NAME,MODEL,SIZE,TYPE,FSTYPE,MOUNTPOINTS
fetian-health-rs --json
systemctl --failed
systemctl --user --failed
```

Record AMD's PCI ID and driver, actual RAM and disk identity before changing
graphics configuration. Keep automatic driver selection; an AMD vendor name
alone does not justify a forced module or third-party GPU installer. A working
Intel desktop does not validate AMD offload.

Test display, keyboard/touchpad, network, audio/microphone, brightness, battery
reading and a disposable USB device. Then save work and test manual lock/unlock
and logout/relogin. Attempt suspend/resume only after manual locking succeeds.
Device enumeration and installed packages do not prove hardware functionality.

For a black screen, choose text recovery and inspect:

```sh
journalctl -b -u fetian-live-user.service -u sddm.service
journalctl -b -p err
```

Follow the existing [recovery boundaries](../recovery.md). End the trial with
normal shutdown, remove the USB, and confirm the original system still boots.
Those physical results must be observed on the laptop. Share only relevant
device IDs/errors: reports may contain local network and filesystem names.
