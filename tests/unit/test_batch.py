"""Lotes de imágenes: sin capturas reales ni llamadas al SDK."""
from dataclasses import asdict
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from claude_shot import core, desktop, cli
from test_local import png


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime_patch = patch.object(core, 'RUNTIME', Path(self.tmp.name) / 'runtime')
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.source = Path(self.tmp.name) / 'test image.png'
        self.source.write_bytes(png())
        self.target = core.Target('panel', 'ttys999', 123, 'today')

    def prepare(self, op=None):
        request = {'action': 'prepare', 'path': str(self.source)}
        if op is not None:
            request['operation'] = op
        return desktop.handle(request)

    def test_all_paths_in_one_message_and_one_send(self):
        reply = self.prepare()
        for _ in range(2):
            reply = self.prepare(reply['operation'])
        self.assertEqual(reply['count'], 3)
        def deliver(target, prompt, op):
            core.receipt(op, 'submitted')
        with patch.object(desktop, 'revalidate'), patch.object(desktop, 'send', side_effect=deliver) as send:
            desktop.handle({'action': 'send', 'operation': reply['operation'],
                            'target': asdict(self.target), 'text': 'Compara estas tres'})
        send.assert_called_once()
        prompt = send.call_args.args[1]
        positions = [prompt.index(json.dumps(path)) for path in reply['image_paths']]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(prompt.count('Compara estas tres'), 1)
        self.assertNotIn('\n', prompt)

    def test_cancel_new_selection_preserves_previous_captures(self):
        reply = self.prepare()
        with patch.object(desktop.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)):
            cancelled = desktop.handle({'action': 'capture', 'operation': reply['operation']})
        self.assertEqual(cancelled['state'], 'capture_cancelled')
        self.assertEqual(cancelled['image_paths'], reply['image_paths'])
        self.assertTrue(Path(reply['image_path']).exists())
        self.assertEqual(desktop.operation_state(desktop.get_operation(reply['operation'])), 'preparing')

    def test_maximum_rejects_before_another_capture(self):
        reply = self.prepare()
        for _ in range(5):
            reply = self.prepare(reply['operation'])
        with patch.object(desktop.subprocess, 'run') as capture:
            with self.assertRaises(desktop.DesktopError):
                desktop.handle({'action': 'capture', 'operation': reply['operation']})
        capture.assert_not_called()
        self.assertEqual(len(core.image_paths(desktop.get_operation(reply['operation']))), 6)

    def test_remove_one_preserves_order_and_remove_last_cancels(self):
        reply = self.prepare()
        reply = self.prepare(reply['operation'])
        first, second = reply['image_paths']
        removed = desktop.handle({'action': 'remove', 'operation': reply['operation'], 'index': 0})
        self.assertEqual(removed['image_paths'], [second])
        self.assertFalse(Path(first).exists())
        cancelled = desktop.handle({'action': 'remove', 'operation': reply['operation'], 'index': 0})
        self.assertEqual(cancelled['state'], 'cancelled')
        self.assertFalse(Path(second).exists())

    def test_failed_append_does_not_destroy_previous_images(self):
        reply = self.prepare()
        self.source.write_bytes(b'not png')
        with self.assertRaises(core.ShotError):
            self.prepare(reply['operation'])
        self.assertTrue(Path(reply['image_path']).exists())
        self.assertEqual(list(map(str, core.image_paths(desktop.get_operation(reply['operation'])))), reply['image_paths'])

    def test_total_size_limit_rolls_back_new_copy(self):
        with patch.object(core, 'MAX_BATCH', len(png()) * 2 - 1):
            reply = self.prepare()
            with self.assertRaises(core.ShotError):
                self.prepare(reply['operation'])
        op = desktop.get_operation(reply['operation'])
        self.assertEqual(len(core.image_paths(op)), 1)
        self.assertEqual(len(list(op.glob('*.png'))), 1)

    def test_attempted_batch_cannot_be_modified(self):
        reply = self.prepare()
        op = desktop.get_operation(reply['operation'])
        (op / 'attempted').touch()
        with self.assertRaises(desktop.DesktopError):
            self.prepare(reply['operation'])
        with self.assertRaises(desktop.DesktopError):
            desktop.handle({'action': 'remove', 'operation': reply['operation'], 'index': 0})

    def test_manifest_rejects_escape_and_duplicates(self):
        reply = self.prepare()
        op = desktop.get_operation(reply['operation'])
        for names in (['../outside.png'], ['image.png', 'image.png']):
            core.atomic_json(op / 'images.json', names)
            with self.assertRaises(core.ShotError):
                core.image_paths(op)
        (op / 'images.json').unlink()
        (op / 'images.json').symlink_to(op / 'nonexistent')
        with self.assertRaises(core.ShotError):
            core.image_paths(op)

    def test_cleanup_removes_completed_batch(self):
        reply = self.prepare()
        reply = self.prepare(reply['operation'])
        op = desktop.get_operation(reply['operation'])
        (op / 'attempted').touch()
        core.receipt(op, 'submitted')
        os.utime(op / 'receipt.json', (time.time() - 90_000,) * 2)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cleanup(24)
        self.assertFalse(op.exists())

    def test_cli_repeated_images_send_once(self):
        args = types.SimpleNamespace(command='send', session='panel', image=[str(self.source)] * 2, text=None)
        with patch.object(cli.sys.stdin, 'isatty', return_value=True), \
                patch.object(cli, 'discover', return_value=[self.target]), \
                patch.object(cli, 'revalidate'), patch.object(cli, 'send') as send, \
                patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()):
            cli.workflow(args)
        send.assert_called_once()
        self.assertIn('Describe las imágenes.', send.call_args.args[1])
        self.assertEqual(send.call_args.args[1].count('.png"'), 2)

    def test_cli_capture_count_cancel_discards_entire_batch(self):
        args = types.SimpleNamespace(command='capture', session='panel', count=2, text=None)
        count = 0
        def capture(command, **kwargs):
            nonlocal count
            count += 1
            if count == 1:
                Path(command[-1]).write_bytes(png())
            return types.SimpleNamespace(returncode=0 if count == 1 else 1)
        with patch.object(cli.sys.stdin, 'isatty', return_value=True), \
                patch.object(cli, 'discover', return_value=[self.target]), \
                patch.object(cli.subprocess, 'run', side_effect=capture), \
                patch.object(cli, 'send') as send, contextlib.redirect_stdout(io.StringIO()):
            cli.workflow(args)
        send.assert_not_called()
        op = next((core.RUNTIME / 'operations').iterdir())
        self.assertEqual(desktop.operation_state(op), 'cancelled')
        self.assertEqual(list(op.glob('*.png')), [])


if __name__ == '__main__':
    unittest.main()
