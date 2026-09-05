#!/usr/bin/env python3
"""Inventory a working CM5, then render its explicit migration scripts.

This prepares files only. It does not stage an OS, arm boot, or reboot.
"""
import argparse
import json
import os
from pathlib import Path
import pwd
import grp
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent

def run(*args):
    return subprocess.check_output(args, text=True).strip()

def render(values, destination):
    destination.mkdir(mode=0o700)
    for template in (HERE/'templates').glob('*.in'):
        body = template.read_text()
        for name, value in values.items(): body = body.replace('@'+name+'@', str(value))
        unresolved = re.findall(r'@[A-Z_]+@', body)
        if unresolved: raise ValueError(f'{template.name}: unresolved fields {unresolved}')
        out = destination/template.name.removesuffix('.in')
        out.write_text(body)
        out.chmod(0o755 if out.suffix != '.py' else 0o644)
    shutil.copytree(HERE/'hardware', destination/'hardware')
    (destination/'manifest.json').write_text(json.dumps(values, indent=2)+'\n')

def inventory(owner):
    if os.geteuid() != 0: raise ValueError('Run preparation with sudo; it must inspect root/boot files.')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', owner): raise ValueError('Unsupported account name')
    account = pwd.getpwnam(owner)
    if account.pw_uid != 1000: raise ValueError('This reference currently supports a desktop owner with UID 1000 only.')
    group = grp.getgrgid(account.pw_gid).gr_name
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', group): raise ValueError('Unsupported group name')
    if group != owner or account.pw_gid != 1000: raise ValueError('This reference requires the desktop owner to have a matching private group with GID 1000.')
    home = Path(account.pw_dir)
    if home != Path('/home')/owner: raise ValueError('This reference requires /home/<owner>.')
    model = Path('/proc/device-tree/model').read_text().strip('\0\n')
    if 'Compute Module 5' not in model: raise ValueError('This guide is restricted to the verified CM5 architecture.')
    if run('uname', '-m') != 'aarch64': raise ValueError('A running ARM64 system is required.')
    if run('getconf', 'PAGE_SIZE') != '16384': raise ValueError('This reference requires the tested 16 KiB CM5 kernel configuration.')
    kernel = run('uname', '-r')
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+_-]+', kernel): raise ValueError('Unsupported kernel version string')
    if run('findmnt', '-n', '-o', 'SOURCE', '/') != '/dev/mmcblk0p2': raise ValueError('Expected eMMC root /dev/mmcblk0p2; no disk substitution is performed.')
    if run('findmnt', '-n', '-o', 'FSTYPE', '/') != 'ext4': raise ValueError('Only the tested ext4 root transition is supported.')
    if run('findmnt', '-n', '-o', 'SOURCE', '/boot/firmware') != '/dev/mmcblk0p1': raise ValueError('Expected boot on /dev/mmcblk0p1.')
    if run('findmnt', '-n', '-o', 'FSTYPE', '/boot/firmware') != 'vfat': raise ValueError('Expected FAT boot filesystem.')
    for path in ['/omarchy-stage','/debian-recovery','/.omarchy-switch-ready']:
        if Path(path).exists(): raise ValueError(f'{path} exists. Resolve the previous migration first.')
    if not Path('/etc/debian_version').exists(): raise ValueError('Start from the working Debian/Raspberry Pi OS CM5 installation.')
    for tool in ['rsync','xz','dd','losetup','mount','umount','chroot','busybox','cpio','gzip','zstd','sha256sum','pinctrl','sshd','getent']:
        if not shutil.which(tool): raise ValueError(f'Install missing preparation dependency: {tool}')
    for path in [home/'.ssh/authorized_keys',Path('/lib/modules')/kernel,Path('/boot')/('config-'+kernel),Path('/boot/firmware/kernel_2712.img'),Path('/boot/firmware/bcm2712-rpi-cm5-cm5io.dtb'),Path('/boot/firmware/overlays/clockworkpi-uconsole-cm5.dtbo')]:
        if not path.exists(): raise ValueError(f'Missing required source artifact: {path}')
    if not (home/'.ssh/authorized_keys').read_text().strip(): raise ValueError('Install and test an SSH public key first.')
    connections = Path('/etc/NetworkManager/system-connections')
    if not connections.is_dir() or not any(connections.iterdir()): raise ValueError('Persist the working network connection in NetworkManager system-connections first.')
    boot = Path('/boot/firmware/config.txt').read_text()
    if 'clockworkpi-uconsole-cm5' not in boot: raise ValueError('Missing working CM5 uConsole overlay configuration.')
    if any(re.match(r'\s*(initramfs\s|auto_initramfs\s*=\s*1)', line) for line in boot.splitlines()): raise ValueError('Existing initramfs setup needs a separate review; this reference preserves a direct-boot kernel.')
    if shutil.disk_usage('/').free < 24*1024**3: raise ValueError('At least 24 GiB free is required for this conservative staging preflight.')
    hostname = run('hostname')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', hostname): raise ValueError('Unsupported hostname')
    zone = str(Path('/etc/localtime').resolve()).removeprefix('/usr/share/zoneinfo/')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]+', zone) or zone.startswith('/'): raise ValueError('Expected /etc/localtime to link into /usr/share/zoneinfo.')
    ids = {name:run('blkid','-s',field,'-o','value',device) for name,field,device in [('ROOT_UUID','UUID','/dev/mmcblk0p2'),('ROOT_PARTUUID','PARTUUID','/dev/mmcblk0p2'),('BOOT_PARTUUID','PARTUUID','/dev/mmcblk0p1')]}
    if not all(re.fullmatch(r'[A-Fa-f0-9-]+', value) for value in ids.values()): raise ValueError('Missing or unsupported partition identity')
    return dict(ids, OWNER=owner,GROUP=group,HOME=str(home),WORKDIR=str(home/'omarchy-install'),KERNEL=kernel,PKGVER=kernel.split('-')[0]+'.local-1',HOSTNAME=hostname,TIMEZONE=zone,MODEL=model)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--user',required=True,help='Existing UID-1000 desktop owner whose SSH access will be preserved')
    p.add_argument('--check',action='store_true',help='Validate and print inventory without writing files')
    args=p.parse_args()
    values=inventory(args.user)
    print(json.dumps(values,indent=2))
    if args.check: return
    target=Path(values['WORKDIR'])
    if target.exists(): raise ValueError(f'Refusing to overwrite {target}')
    render(values,target)
    account=pwd.getpwnam(args.user)
    os.chown(target,account.pw_uid,account.pw_gid)
    print(f'Prepared {target}. Follow docs/INSTALL.md; no boot changes were made.')

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,subprocess.CalledProcessError) as error: raise SystemExit(str(error))
