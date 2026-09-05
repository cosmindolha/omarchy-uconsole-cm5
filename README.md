# Omarchy on the uConsole CM5, over SSH

A working ARM64 Omarchy desktop on a ClockworkPi uConsole with Raspberry Pi Compute Module 5. This repository documents the installation performed on real hardware and supplies scripts that preserve the working CM5 kernel while replacing the Debian userland with Omarchy.

The desktop booted successfully, then passed a second normal reboot. Display rotation, accelerated graphics, keyboard, trackball, backlight controls, speaker routing, Wi-Fi, SSH and the readable handheld interface were checked on the device.

**Start with [the installation guide](docs/INSTALL.md).** The matching [uConsole Clear theme and utilities](https://github.com/cosmindolha/omarchy-uconsole-clear-theme) provide large text, dark backgrounds, accent presets/editor, a physical keyboard guide, volume chords and honest battery readings.

## What this uses

| Component | Verified configuration |
| --- | --- |
| Hardware | uConsole, CM5, 16 GB RAM, 64 GB eMMC |
| Starting system | Working Debian-based CM5/uConsole installation |
| ARM userland | [Omarchy 4 Pi v0.1.0-rc.1](https://github.com/pkyanam/omarchy-4-pi/releases/tag/v0.1.0-rc.1), minimal image |
| Desktop | Omarchy 4.0.2, Hyprland 0.56.1, Quickshell 0.3.1 |
| Kernel | Existing uConsole CM5 `6.12.87-v8-16k+`, matching modules, firmware, DTBs and overlays |
| Storage | Existing FAT boot partition + ext4 root; no repartitioning |
| Display | Native 720×1280 DSI, transform 3 → landscape 1280×720 |

The stock PC Omarchy ISO is not used. The Pi 4 image contributes ARM applications and desktop configuration; its generic kernel and U-Boot are removed before the transition.

## Scope and verification

This is an experimental **reference migration**, verified on one CM5. The original migration ran on hardware. The public parameterized scripts have additional disposable root-switch tests and syntax checks; a fresh installation using the generalized public renderer has not been repeated on a second device.

Preparation explicitly requires a working ARM64 Debian CM5 installation with a 16 KiB kernel, `/dev/mmcblk0p1` as FAT boot, `/dev/mmcblk0p2` as ext4 root, a UID/GID 1000 owner with a matching private group, saved NetworkManager connections, SSH keys and at least 24 GiB free. Different storage layouts, CM4, encrypted roots and newer Omarchy releases require adaptation. They are not silently selected.

`prepare.py --check` only inventories. Preparation renders explicit scripts; it does not change the OS or reboot. The root switch runs from a small RAM environment on the first boot, moving the old root into `/debian-recovery` before activating the staged root. That directory is useful for recovery but is not an independent backup.

## Contents

- [Installation](docs/INSTALL.md): prerequisites, pinned image/checksums, staging, preflight, boot and validation.
- [Recovery](docs/RECOVERY.md): disarm before reboot, recover interrupted transitions, restore the previous root offline.
- [Hardware and maintenance](docs/HARDWARE.md): display, input, audio, power, kernel and package limitations.
- `prepare.py`: read actual device identities and render the scripts in `templates/`.
- `cleanup-old-os.py`: preview recovery space or explicitly remove the old Debian root after validation. Keeping recovery is the default; see [cleanup options](docs/INSTALL.md#8-keep-or-remove-the-old-os).
- `hardware/`: small GPIO audio and evdev trackball helpers.
- `tests/`: render portability, shell syntax, root preservation, and failed-preflight protection.

```bash
python3 -m unittest discover -s tests -v
```

No OS images, kernel binaries, SSH credentials, Wi-Fi profiles or personal machine backups are distributed here. MIT applies to this repository's original scripts and documentation. Omarchy is MIT licensed; the Linux kernel has its own GPL licensing. See the upstream [Omarchy](https://github.com/basecamp/omarchy), [Omarchy 4 Pi](https://github.com/pkyanam/omarchy-4-pi), [ClockworkPi](https://github.com/clockworkpi/uConsole), and [CM5 kernel source](https://github.com/ak-rex/ClockworkPi-linux/tree/rpi-6.12.y).
