# Install over SSH

This is the staged migration used for the working CM5, with device-specific values now rendered from the target. It replaces the OS on the existing root partition. Keep the uConsole powered and retain a physical recovery route to its eMMC; SSH cannot recover a machine that never starts networking.

## 1. Start from working hardware

Use a Debian/Raspberry Pi OS installation that already boots this CM5 uConsole with its screen, keyboard, Wi-Fi and vendor kernel working. Test SSH public-key login and `sudo` before proceeding. Use the UID/GID 1000 desktop account, with its normal `/home/<name>` directory and matching private group.

Commands below run **on the uConsole as that account**, except where marked computer-side. Replace `YOUR_USER@YOUR_HOST.local` with your real SSH destination. Do not copy another machine's partition UUIDs.

```bash
sudo apt update
sudo apt install git curl rsync xz-utils cpio gzip zstd busybox util-linux openssh-server
git clone https://github.com/cosmindolha/omarchy-uconsole-cm5.git
cd omarchy-uconsole-cm5
sudo python3 prepare.py --user "$USER" --check
```

The existing distribution must also provide `pinctrl`, the vendor kernel config, modules, CM5 DTB and `clockworkpi-uconsole-cm5.dtbo`. A failed prerequisite needs resolving in the starting system. The script rejects other block-device layouts rather than guessing a destination.

## 2. Save recovery material off the device

Before rendering or staging, save the current boot files and essential access settings:

```bash
sudo tar -C / -czf /var/tmp/uconsole-before-omarchy.tgz \
  boot/firmware etc/fstab etc/ssh etc/NetworkManager \
  etc/passwd etc/group etc/shadow etc/gshadow \
  "home/$USER/.ssh"
sudo chown "$USER:$(id -gn)" /var/tmp/uconsole-before-omarchy.tgz
chmod 600 /var/tmp/uconsole-before-omarchy.tgz
```

From your **computer**, copy it off the uConsole:

```bash
scp YOUR_USER@YOUR_HOST.local:/var/tmp/uconsole-before-omarchy.tgz ./
chmod 600 ./uconsole-before-omarchy.tgz
```

This archive contains authentication and Wi-Fi secrets. Keep it private. It is a boot/access backup, not a full disk backup. If you need a complete restore image, make and verify one through your existing eMMC recovery route before continuing. Read [recovery](RECOVERY.md) now, including the partial-transition case.

## 3. Render and download the pinned image

Back on the uConsole, in the cloned repository:

```bash
sudo python3 prepare.py --user "$USER"
cd "$HOME/omarchy-install"
curl -fL --retry 3 \
  https://github.com/pkyanam/omarchy-4-pi/releases/download/v0.1.0-rc.1/omarchy-4-pi-20260904-bd0e85fc-minimal.img.xz \
  -o omarchy.img.xz
```

Preparation creates a new private work directory and refuses to overwrite one. `manifest.json` records the actual username, kernel and partition identities. Review it and the rendered scripts. Keep the working connection profile saved in NetworkManager; a temporary/manual wireless connection will not survive by magic.

Pinned compressed image SHA-256:

```text
288dc0db84348e1689909777084735f8297460ad0f92b067cc80e199e7f4b5f4
```

Uncompressed image SHA-256:

```text
607d4396a376c183c6c890e300e9fb5b76fc263dd858d4b1252362d656c935f7
```

The staging script checks both. A different image needs a fresh compatibility review; changing the checksum alone is insufficient.

## 4. Stage, configure and test

Run each step in order. Stop on a nonzero exit; do not continue to arming after an incomplete stage.

```bash
sudo bash stage-image.sh
sudo bash configure-stage.sh
sudo bash register-cm5-kernel.sh
sudo bash build-migration-ramfs.sh
python3 test-migration.py
sudo bash cm5-final-preflight.sh
```

Staging expands the image to a sparse file and reads its root partition through a read-only loop device. It copies ARM userspace into `/omarchy-stage`. Configuration preserves your SSH keys, SSH host identity, existing password hash and NetworkManager settings locally. It enables SSH through the image's firewall and provisions the existing owner using Omarchy's own finalizer.

The kernel package is built from the target's existing working kernel/modules/DTBs. No replacement CM5 kernel is downloaded. The scripts enable display rotation, audio routing, trackball click correction and the native desktop. The owner receives normal password-authenticated sudo access; root password login is locked. SDDM autologin is enabled to match the handheld setup. Remove `/etc/sddm.conf.d/autologin.conf` after installation if you want the login screen on every boot.

The exact root-switch body is tested in temporary directories. Final preflight checks partition identities, preserved boot payload, libraries, SSH configuration, firewall rules, Hyprland configuration and the RAM shell. Success ends with `CM5_PREFLIGHT_PASSED`.

## 5. Arm the one-time transition

This is the step that changes the next boot. Keep the charger connected and your recovery material available.

```bash
sudo bash arm-first-boot.sh
sudo reboot
```

The temporary initramfs runs with the existing CM5 kernel. It checks the root UUID and preflight marker, renames the old root entries into `/debian-recovery`, and activates the staged Arch root. It does not format either partition. An interrupted transition needs offline inspection; it does not automatically retry a partial move.

Reconnect using the same SSH account and hostname after networking starts. The SSH host keys were retained, so an unexpected host-key change warrants inspection rather than deleting the old trust record.

## 6. Finish and verify the first boot

```bash
cat /etc/os-release
uname -r
cat /var/lib/omarchy/cm5-root-switch
sudo bash /var/lib/omarchy/cm5-install/finish-live.sh
systemctl --failed
export XDG_RUNTIME_DIR=/run/user/$(id -u)
hyprctl -i 0 configerrors
hyprctl -i 0 monitors
systemctl --user --failed
```

The root-switch marker must say `cm5-root-switch-complete`. `finish-live.sh` checks the stable mouse device and removes the migration initramfs boot directive, so subsequent boots use the normal direct CM5 boot path. The old work directory is now under `/debian-recovery/home/<your-user>/omarchy-install`; the finish script is also copied into `/var/lib/omarchy/cm5-install` during preflight.

Confirm the physical screen is landscape and upright, keyboard and trackball work, and SSH remains reachable. If a DSI connector is named differently from the tested `DSI-2`, inspect `hyprctl` output and update the monitor entry. Do not change rotation blindly.

## 7. Install the handheld interface

As the desktop user:

```bash
cd "$HOME"
git clone https://github.com/cosmindolha/omarchy-uconsole-clear-theme.git
cd omarchy-uconsole-clear-theme
./install.sh --check
./install.sh
```

This supplies the readable scale/fonts, dark accents, keyboard-first color editor, physical key guide, speaker+D-pad volume controls, battery measurement panel and one-hour idle lock. Test **Left Alt + Enter**, **Left Alt + K**, and **Alt + Space**. See the theme repository for its complete controls and screenshots.

Finally, reboot normally once more and repeat the service, display and SSH checks. Keep `/debian-recovery` until the system has passed your own hardware and application checks. It consumes disk space but is valuable while validating the adaptation.

## 8. Keep or remove the old OS

The new system is **Arch Linux ARM userspace with Omarchy**, using the preserved CM5 kernel. Debian is retained only as a recovery copy; it is not the active userspace.

Choose either option after testing a second normal reboot:

- **Keep it:** do nothing. `/debian-recovery` retains the old system, old home directories and staging image for local rollback.
- **Remove it:** preview its allocated space, then explicitly request removal. This permanently removes everything in that directory, including old personal files and image downloads. Local rollback will no longer be possible; retain any independent backups you need.

```bash
sudo python3 /var/lib/omarchy/cm5-install/cleanup-old-os.py --preview
sudo python3 /var/lib/omarchy/cm5-install/cleanup-old-os.py --remove-old-os
```

For existing installations made before this utility was included, update this repository and run `sudo python3 cleanup-old-os.py --preview` from its directory instead. The removal flag is the same. With no arguments, the utility only previews; installation never automatically deletes recovery.

Cleanup requires the completed migration marker, active Omarchy, a preserved kernel package and an unarmed migration. It refuses a symlinked recovery directory, mounted filesystems within it, or processes using it. The running Omarchy system and current boot files are retained. The original test unit had approximately 33 GiB allocated to recovery and staging; actual reclaimed space varies.

## Updates

See [maintenance](HARDWARE.md). The locally packaged CM5 kernel has no automatic update channel. ARM userland updates are separate from kernel/DTB updates, and newer Omarchy releases may change the Lua, shell or theme contracts. Retain a recoverable working system before testing those changes.
