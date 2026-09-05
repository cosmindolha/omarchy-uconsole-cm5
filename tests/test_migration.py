import importlib.util
from pathlib import Path
import py_compile
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare', ROOT/'prepare.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def values(owner='alex'):
    return dict(OWNER=owner, GROUP=owner, HOME=f'/home/{owner}',
                WORKDIR=f'/home/{owner}/omarchy-install',
                KERNEL='6.12.87-v8-16k+', PKGVER='6.12.87.local-1',
                ROOT_UUID='11111111-2222-3333-4444-555555555555',
                ROOT_PARTUUID='1234abcd-02', BOOT_PARTUUID='1234abcd-01',
                HOSTNAME='test-console', TIMEZONE='Etc/UTC', MODEL='Raspberry Pi Compute Module 5')


class MigrationTests(unittest.TestCase):
    def test_render_and_exact_root_switch(self):
        for owner in ['alex', 'dev_user']:
            with self.subTest(owner=owner), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp)/'rendered'
                prepare.render(values(owner), dest)
                for script in dest.iterdir():
                    if script.suffix == '.sh' or script.name == 'cm5-migration-init':
                        self.assertIsNone(re.search(r'@[A-Z_]+@', script.read_text()))
                        subprocess.run(['bash', '-n', str(script)], check=True)
                    if script.suffix == '.py': py_compile.compile(str(script), doraise=True)
                subprocess.run(['python3', str(dest/'test-migration.py')], check=True)

    def test_guards_leave_original_root_untouched(self):
        source = (ROOT/'templates/cm5-migration-init.in').read_text()
        body = source[source.index('if [ -f /newroot/.omarchy-switch-ready ]; then'):source.index('[ -x /newroot/sbin/init ]')]
        for failure in ['systemd_missing', 'preflight_missing', 'recovery_exists']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)/'root'
                root.mkdir()
                (root/'.omarchy-switch-ready').touch()
                (root/'original').write_text('retain')
                stage = root/'omarchy-stage'
                (stage/'usr/lib/systemd').mkdir(parents=True)
                if failure != 'systemd_missing':
                    systemd = stage/'usr/lib/systemd/systemd'
                    systemd.write_text('#!/bin/sh\n')
                    systemd.chmod(0o755)
                if failure != 'preflight_missing': (stage/'.cm5-preflight-passed').touch()
                if failure == 'recovery_exists': (root/'debian-recovery').mkdir()
                script = 'set -e\nfail() { exit 13; }\n' + body.replace('/newroot', str(root))
                result = subprocess.run(['/bin/sh', '-c', script])
                self.assertEqual(result.returncode, 13)
                self.assertEqual((root/'original').read_text(), 'retain')

    def test_render_refuses_existing_work_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileExistsError): prepare.render(values(), Path(temp))

    def test_unresolved_template_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError): prepare.render({}, Path(temp)/'new')


if __name__ == '__main__': unittest.main()
