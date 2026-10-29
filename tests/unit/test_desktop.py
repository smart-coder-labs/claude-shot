"""Protocolo de escritorio simulado: no captura ni conecta al SDK real."""
from dataclasses import asdict
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from claude_shot import core, desktop
from test_local import png


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime_patch = patch.object(core, 'RUNTIME', Path(self.tmp.name) / 'runtime')
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.target = core.Target('panel', 'ttys999', 123, 'today', 'Proyecto', '1')

    def prepare(self):
        source = Path(self.tmp.name) / 'source.png'
        source.write_bytes(png())
        return desktop.handle({'action': 'prepare', 'path': str(source)})

    def test_prepare_and_cancel_never_send(self):
        with patch.object(desktop, 'send') as send:
            reply = self.prepare()
            image = Path(reply['image_path'])
            self.assertTrue(image.exists())
            self.assertEqual(reply['state'], 'prepared')
            cancelled = desktop.handle({'action': 'cancel', 'operation': reply['operation']})
            self.assertEqual(cancelled['state'], 'cancelled')
            self.assertFalse(image.exists())
            send.assert_not_called()

    def test_send_once_no_duplicate_delivery(self):
        reply = self.prepare()
        request = {'action': 'send', 'operation': reply['operation'], 'target': asdict(self.target), 'text': 'hola'}
        def deliver(target, text, op):
            core.receipt(op, 'submitted')
        with patch.object(desktop, 'revalidate'), patch.object(desktop, 'send', side_effect=deliver) as send:
            result = desktop.handle(request)
            self.assertEqual(result['state'], 'submitted')
            with self.assertRaises(desktop.DesktopError):
                desktop.handle(request)
            send.assert_called_once()
            self.assertIn('hola', send.call_args.args[1])

    def test_closed_target_never_sends(self):
        reply = self.prepare()
        request = {'action': 'send', 'operation': reply['operation'], 'target': asdict(self.target)}
        with patch.object(desktop, 'revalidate', side_effect=core.ShotError('closed')), \
                patch.object(desktop, 'send') as send:
            with self.assertRaises(core.ShotError):
                desktop.handle(request)
            send.assert_not_called()
        self.assertFalse((desktop.get_operation(reply['operation']) / 'attempted').exists())

    def test_uncertain_delivery_cannot_be_cancelled_or_retried(self):
        reply = self.prepare()
        request = {'action': 'send', 'operation': reply['operation'], 'target': asdict(self.target)}
        def fail(target, text, op):
            core.receipt(op, 'uncertain')
            raise TimeoutError()
        with patch.object(desktop, 'revalidate'), patch.object(desktop, 'send', side_effect=fail) as send:
            with self.assertRaises(TimeoutError):
                desktop.handle(request)
            with self.assertRaises(desktop.DesktopError):
                desktop.handle(request)
            with self.assertRaises(desktop.DesktopError):
                desktop.handle({'action': 'cancel', 'operation': reply['operation']})
            send.assert_called_once()
        self.assertTrue(Path(reply['image_path']).exists())

    def test_capture_cancelled_without_send(self):
        with patch.object(desktop.subprocess, 'run', return_value=types.SimpleNamespace(returncode=1)), \
                patch.object(desktop, 'send') as send:
            reply = desktop.handle({'action': 'capture'})
        self.assertEqual(reply['state'], 'cancelled')
        send.assert_not_called()

    def test_invalid_action_and_operation_path_rejected(self):
        with self.assertRaises(desktop.DesktopError):
            desktop.handle({'action': 'shell', 'command': 'anything'})
        for value in ('../outside', '/tmp/file', '', None):
            with self.assertRaises(desktop.DesktopError):
                desktop.get_operation(value)

    def test_cancel_cannot_race_with_operation_lock(self):
        reply = self.prepare()
        with core.target_lock(core.Target('operation:' + reply['operation'], '', 0, '')):
            with self.assertRaises(core.ShotError):
                desktop.handle({'action': 'cancel', 'operation': reply['operation']})
        self.assertTrue(Path(reply['image_path']).exists())

    def test_json_stdout_stays_parseable_despite_sdk_notice(self):
        payload = {'action': 'sessions'}
        def notice(request):
            print('SDK notice')
            return {'sessions': []}
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(desktop.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))), \
                patch.object(desktop, 'handle', side_effect=notice), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(desktop.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {'ok': True, 'sessions': []})
        self.assertIn('SDK notice', errors.getvalue())

    def test_protocol_rejects_oversized_input_without_dispatch(self):
        output = io.StringIO()
        with patch.object(desktop.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(b'x' * 65537))), \
                patch.object(desktop, 'handle') as handle, contextlib.redirect_stdout(output):
            self.assertEqual(desktop.main(), 1)
        handle.assert_not_called()
        self.assertFalse(json.loads(output.getvalue())['ok'])

    def test_receipt_symlink_is_rejected(self):
        reply = self.prepare()
        op = desktop.get_operation(reply['operation'])
        (op / 'receipt.json').unlink()
        (op / 'receipt.json').symlink_to(Path(self.tmp.name) / 'outside')
        with self.assertRaises(OSError):
            desktop.operation_state(op)

    def test_attempted_marker_is_uncertain_even_if_receipt_was_not_written(self):
        reply = self.prepare()
        op = desktop.get_operation(reply['operation'])
        (op / 'attempted').touch()
        payload = {'action': 'send', 'operation': reply['operation'], 'target': asdict(self.target)}
        output = io.StringIO()
        with patch.object(desktop.sys, 'stdin', types.SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))), \
                patch.object(desktop, 'revalidate'), patch.object(desktop, 'send') as send, \
                contextlib.redirect_stdout(output):
            self.assertEqual(desktop.main(), 1)
        self.assertEqual(json.loads(output.getvalue())['state'], 'uncertain')
        send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
