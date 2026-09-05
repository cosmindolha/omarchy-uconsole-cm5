#!/usr/bin/env python3
"""Preview or explicitly remove the old Debian root after verifying Omarchy."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

RECOVERY = Path('/debian-recovery')
REPORT = Path('/var/lib/omarchy/cm5-old-os-removed.json')


def inside(path, directory):
    return path == directory or directory in path.parents


def mount_paths(text):
    # mountinfo escapes spaces, tabs, newlines and backslashes as octal bytes.
    return [Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), line.split()[4]))
            for line in text.splitlines() if line.strip()]


def check_tree(path, mounts, references):
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Recovery must be a real directory, not a symlink.')
    if not (path/'etc/debian_version').is_file():
        raise ValueError('Expected Debian recovery metadata is missing.')
    if any(inside(mount, path) for mount in mounts):
        raise ValueError('A filesystem is mounted in the recovery tree; unmount it first.')
    if any(inside(reference, path) for reference in references):
        raise ValueError('A running process uses the recovery tree; stop it or leave that directory first.')


def process_references():
    for process in Path('/proc').glob('[0-9]*'):
        for entry in [process/'cwd', process/'root', process/'exe', *list((process/'fd').glob('*'))]:
            try:
                target = os.readlink(entry).removesuffix(' (deleted)')
                if target.startswith('/'): yield Path(target)
            except FileNotFoundError:
                pass  # Processes and descriptors can disappear during inspection.
            except PermissionError as error:
                raise ValueError(f'Cannot inspect active process reference: {entry}') from error


def validate():
    if os.geteuid() != 0: raise ValueError('Run with sudo so recovery files and active processes can be inspected.')
    if Path('/var/lib/omarchy/cm5-root-switch').read_text().strip() != 'cm5-root-switch-complete':
        raise ValueError('The completed CM5 migration marker is required.')
    os_release = Path('/etc/os-release').read_text()
    if not re.search(r'^ID=["\']?omarchy["\']?$', os_release, re.M):
        raise ValueError('Run cleanup from the active Omarchy system.')
    if Path('/.omarchy-switch-ready').exists(): raise ValueError('The migration is still armed.')
    boot = Path('/boot/firmware/config.txt').read_text()
    if any('omarchy-migration.img' in line and not line.lstrip().startswith('#') for line in boot.splitlines()):
        raise ValueError('Finish the first boot before cleanup; migration initramfs is still configured.')
    subprocess.run(['pacman', '-Q', 'linux-uconsole-cm5'], check=True, stdout=subprocess.DEVNULL)
    for active in [Path('/usr/lib/modules')/os.uname().release,
                   Path('/boot/firmware/kernel_2712.img'), Path('/usr/lib/systemd/systemd')]:
        if not active.exists() or inside(active.resolve(), RECOVERY):
            raise ValueError(f'Active system dependency is missing or points into recovery: {active}')
    check_tree(RECOVERY, mount_paths(Path('/proc/self/mountinfo').read_text()), process_references())
    if not shutil.rmtree.avoids_symlink_attacks:
        raise ValueError('This Python build lacks descriptor-based safe directory removal.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument('--preview', action='store_true', help='Show space to reclaim; the default. Deletes nothing.')
    options.add_argument('--remove-old-os', action='store_true', help='Permanently delete /debian-recovery, including old home files and staging images.')
    args = parser.parse_args()
    if not RECOVERY.exists() and not RECOVERY.is_symlink():
        print('No /debian-recovery directory remains. Nothing to remove.')
        return
    validate()
    allocated = int(subprocess.check_output(['du', '-sx', '--block-size=1', str(RECOVERY)], text=True).split()[0])
    print(f'Old Debian root and staging files: {allocated / 1024**3:.2f} GiB allocated.')
    print('Removal includes the old home directories and eliminates local OS rollback.')
    if not args.remove_old_os:
        print('Preview only. After a successful normal reboot, use --remove-old-os to delete it.')
        return
    validate()  # Repeat dependency, process and mount checks immediately before deleting.
    shutil.rmtree(RECOVERY)
    REPORT.write_text(json.dumps({'removed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                 'allocated_bytes_before_removal': allocated}, indent=2)+'\n')
    os.sync()
    print('Old Debian root removed. Active Omarchy and its CM5 kernel are retained.')


if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Cleanup stopped: {error}')
