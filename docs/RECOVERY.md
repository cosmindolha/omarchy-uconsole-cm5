# Recovery

The migration keeps the old root on the same ext4 filesystem. This protects against many configuration mistakes, but not eMMC failure. Keep your independent backup and a way to access eMMC without relying on the newly installed system's SSH.

## Before arming

The original OS still runs normally. A failed stage does not change boot. Inspect the failure, unmount the stage's chroot mounts before cleaning it up, and preserve logs. Do not delete `/omarchy-stage` while `/dev`, `/proc` or `/sys` are bind-mounted inside it.

## Armed, but not rebooted

On the original system, disarm by restoring the boot files saved by the arming script and removing the activation marker:

```bash
sudo cp /boot/firmware/config.pre-omarchy.txt /boot/firmware/config.txt
sudo cp /boot/firmware/cmdline.pre-omarchy.txt /boot/firmware/cmdline.txt
sudo rm /.omarchy-switch-ready
sync
```

These commands apply only before the root switch. Verify those backup files exist first. Keep the staged data for diagnosis.

## Boot stops in the migration shell

The script prints its reason and starts a local recovery shell. A missing device, wrong UUID, absent systemd or missing preflight marker stops before moving root entries. The marker checks happen before the first rename. A failure during either rename loop can leave a **partial transition**, requiring inspection from an independent Linux recovery boot or eMMC reader.

Record the last error and inspect the ext4 root, `omarchy-stage` and `debian-recovery`. Do not bypass the preflight guard or repeatedly force the marker. The existing recovery directory intentionally prevents an automatic destructive retry.

## Restore after a completed transition

Do this from an independent Linux environment with the target's normal OS stopped. Identify the correct eMMC partitions from your saved manifest before mounting anything writable.

1. Mount the target ext4 root and FAT boot separately. Ensure no target `/dev`, `/proc`, `/sys` or runtime mounts are active beneath the root mount.
2. Confirm `/var/lib/omarchy/cm5-root-switch` says `cm5-root-switch-complete` and `/debian-recovery` contains the original `etc`, `usr`, `home` and boot mount directory. This procedure assumes a completed transition.
3. Create a new directory for the failed Omarchy root. Move the current top-level entries into it, preserving hidden entries and symlinks, while excluding that new directory, `debian-recovery` and `lost+found`.
4. Move the original top-level entries out of `debian-recovery` into the ext4 root. Inspect every collision; never overwrite blindly.
5. Remove the restored `.omarchy-switch-ready` marker. Restore `config.pre-omarchy.txt` and `cmdline.pre-omarchy.txt` to `config.txt` and `cmdline.txt` on the actual FAT boot partition, or restore them from the off-device backup. The migration initramfs directive must be absent.
6. Sync, unmount both filesystems and boot the original system. Verify SSH, networking and the display before removing any failed-install data.

For a partial transition, compare each top-level directory against both stage and recovery first. A generic rollback command cannot infer which rename failed safely. Preserve the interrupted tree until you have reconciled it.

## Desktop starts but SSH does not

Use the physical terminal to inspect `systemctl status sshd NetworkManager`, `journalctl -b -u sshd -u NetworkManager`, saved NetworkManager profiles and the firewall's port 22 rule. An IP change or mDNS failure can leave IP-based SSH working even when the hostname is unavailable. Use the router's client list to determine the actual address.

## SSH works but the GUI does not

Inspect `systemctl status sddm`, `journalctl -b -u sddm`, user service failures, Hyprland configuration errors and DSI connector state. Keep the preserved CM5 kernel, matching modules, DTB and overlays together. A generic Pi kernel replacement can remove the hardware support this installation depends on.
