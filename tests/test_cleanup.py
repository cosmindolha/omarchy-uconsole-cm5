import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cleanup', Path(__file__).resolve().parents[1]/'cleanup-old-os.py')
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def test_default_preview_keeps_files_and_explicit_remove_preserves_external_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            recovery = base/'recovery'
            (recovery/'etc').mkdir(parents=True)
            (recovery/'etc/debian_version').write_text('12')
            outside = base/'active-system'
            outside.mkdir()
            (outside/'kernel').write_text('keep')
            (recovery/'linked-active-system').symlink_to(outside, target_is_directory=True)
            with patch.object(cleanup, 'RECOVERY', recovery), patch.object(cleanup, 'validate'), patch('sys.argv', ['cleanup']), patch.object(cleanup.subprocess, 'check_output', return_value='1024 /recovery'):
                cleanup.main()
                self.assertTrue(recovery.exists())
            with patch.object(cleanup, 'RECOVERY', recovery), patch.object(cleanup, 'REPORT', base/'report.json'), patch.object(cleanup, 'validate', side_effect=lambda: cleanup.check_tree(recovery, [], [])), patch('sys.argv', ['cleanup', '--remove-old-os']), patch.object(cleanup.subprocess, 'check_output', return_value='1024 /recovery'), patch.object(cleanup.os, 'sync', create=True):
                cleanup.main()
            self.assertTrue((base/'report.json').exists())
            self.assertFalse(recovery.exists())
            self.assertEqual((outside/'kernel').read_text(), 'keep')

    def test_mounted_or_in_use_recovery_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'etc').mkdir()
            (root/'etc/debian_version').write_text('12')
            for mounts, refs in [([root], []), ([root/'dev'], []), ([], [root/'home/user'])]:
                with self.assertRaises(ValueError): cleanup.check_tree(root, mounts, refs)
            cleanup.check_tree(root, [Path('/elsewhere')], [Path(str(root)+'-other')])

    def test_symlink_and_non_debian_target_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            link = root/'alias'
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError): cleanup.check_tree(link, [], [])
            with self.assertRaises(ValueError): cleanup.check_tree(root, [], [])

    def test_mountinfo_decoding(self):
        text = '12 1 0:1 / /debian-recovery/a\\040b rw - tmpfs tmpfs rw\n'
        self.assertEqual(cleanup.mount_paths(text), [Path('/debian-recovery/a b')])
