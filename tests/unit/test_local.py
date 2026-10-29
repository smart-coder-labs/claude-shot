"""Pruebas simuladas: nunca conectan al SDK ni envían a paneles reales."""
import asyncio
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest.mock import AsyncMock, patch
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from claude_shot import core, iterm_adapter, cli


def png():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(b'\x00\xff\x00\x00')) + chunk(b'IEND', b''))


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime_patch = patch.object(core, 'RUNTIME', Path(self.tmp.name) / 'runtime')
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.target = core.Target('panel-1', 'ttys999', 123, 'Wed Oct 28 12:00:00 2026')

    def test_it2_subprocess_does_not_inherit_sdk_credentials(self):
        with patch.dict(os.environ, {'ITERM2_COOKIE': 'secret-cookie', 'ITERM2_KEY': 'secret-key'}), \
                patch.object(core.subprocess, 'run', return_value=types.SimpleNamespace(stdout='[]')) as run:
            self.assertEqual(core.command('it2', 'session', 'list', '--json'), '[]')
            env = run.call_args.kwargs['env']
            self.assertNotIn('ITERM2_COOKIE', env)
            self.assertNotIn('ITERM2_KEY', env)
            self.assertEqual(os.environ['ITERM2_COOKIE'], 'secret-cookie')

    def test_callback_failure_propagates_only_after_sdk_cleanup(self):
        cleaned = []
        async def fail(connection):
            raise core.ShotError('expected failure')
        def runner(callback, retry=False):
            asyncio.run(callback(None))  # No excepción hacia el SDK.
            cleaned.append(True)
        sdk = types.SimpleNamespace(run_until_complete=runner)
        with patch.dict(sys.modules, {'iterm2': sdk}):
            with self.assertRaisesRegex(core.ShotError, 'expected failure'):
                iterm_adapter.with_connection(fail)
        self.assertEqual(cleaned, [True])

    def test_discovery_ignores_titles_background_and_tmux(self):
        panels = [{'id': 'panel-1', 'tty': r'\/dev\/ttys999', 'title': 'ssh'},
                  {'id': 'background', 'tty': '/dev/ttys998'},
                  {'id': 'tmux', 'tty': '/dev/ttys999', 'is_tmux': True}]
        ps = ('123 123 123 ttys999 Wed Oct 28 12:00:00 2026 claude\n'
              '124 124 125 ttys998 Wed Oct 28 12:00:00 2026 claude\n')
        with patch.object(core, 'command', side_effect=[json.dumps(panels), ps]):
            self.assertEqual(core.discover(), [self.target])

    def test_selector_accepts_index_pid_and_session_id(self):
        for value in ('1', '123', 'panel-1'):
            with self.subTest(value=value), patch('builtins.input', return_value=value), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.choose([self.target], None), self.target)

    def test_selector_reprompts_after_invalid_input(self):
        with patch('builtins.input', side_effect=['invalid', '123']), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.choose([self.target], None), self.target)

    def test_selector_ambiguous_number_requires_explicit_id(self):
        other = core.Target('panel-2', 'ttys998', 1, 'today')
        with patch('builtins.input', side_effect=['1', 'panel-2']), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.choose([self.target, other], None), other)
        self.assertIn('ambigua', output.getvalue())

    def test_selector_empty_cancels(self):
        with patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(cli.choose([self.target], None))

    def test_title_is_display_only_and_sanitized(self):
        renamed = core.Target('panel-1', 'ttys999', 123, self.target.started, 'Nuevo título', '3')
        self.assertEqual(self.target, renamed)
        with patch.object(core, 'discover', return_value=[renamed]):
            core.revalidate(self.target)
        self.assertEqual(core.display_title('Proyecto\x1b\n\u202e prueba'), 'Proyecto prueba')
        with patch('builtins.input', return_value='1'), contextlib.redirect_stdout(io.StringIO()) as output:
            cli.choose([renamed], None)
        self.assertIn('Nuevo título', output.getvalue())

    def test_enter_at_text_sends_without_extra_confirmation(self):
        source = Path(self.tmp.name) / 'image.png'
        source.write_bytes(png())
        args = types.SimpleNamespace(command='send', session='panel-1', image=str(source), text='predefinido')
        with patch.object(cli.sys.stdin, 'isatty', return_value=True), \
                patch.object(cli, 'discover', return_value=[self.target]), \
                patch('builtins.input', return_value='') as ask, \
                patch.object(cli, 'revalidate'), patch.object(cli, 'send') as send, \
                contextlib.redirect_stdout(io.StringIO()):
            cli.workflow(args)
        self.assertEqual(ask.call_count, 1)
        send.assert_called_once()
        self.assertIn('predefinido', send.call_args.args[1])

    def test_capture_starts_without_confirmation_and_enter_sends(self):
        args = types.SimpleNamespace(command='capture', session='panel-1', text=None)
        def capture(command, **kwargs):
            Path(command[-1]).write_bytes(png())
            return types.SimpleNamespace(returncode=0)
        with patch.object(cli.sys.stdin, 'isatty', return_value=True), \
                patch.object(cli, 'discover', return_value=[self.target]), \
                patch.object(cli.subprocess, 'run', side_effect=capture) as capture_run, \
                patch('builtins.input', return_value='describe') as ask, \
                patch.object(cli, 'revalidate'), patch.object(cli, 'send') as send, \
                contextlib.redirect_stdout(io.StringIO()):
            cli.workflow(args)
        capture_run.assert_called_once()
        self.assertEqual(ask.call_count, 1)
        send.assert_called_once()
        self.assertIn('describe', send.call_args.args[1])

    def test_changed_process_is_rejected(self):
        with patch.object(core, 'discover', return_value=[]):
            with self.assertRaises(core.ShotError):
                core.revalidate(self.target)

    def test_valid_png_staged_privately(self):
        source = Path(self.tmp.name) / 'with spaces.png'
        source.write_bytes(png())
        op = core.operation()
        image = core.stage_image(source, op)
        self.assertEqual(image.read_bytes(), png())
        self.assertEqual(image.stat().st_mode & 0o777, 0o600)
        self.assertEqual(op.stat().st_mode & 0o777, 0o700)

    def test_bad_pngs(self):
        for data in (b'not png', png()[:-1], png() + b'extra', png()[:40] + b'corrupt' + png()[47:]):
            with self.assertRaises(core.ShotError):
                core.validate_png(data)

    def test_image_symlink_rejected(self):
        source = Path(self.tmp.name) / 'source'
        source.write_bytes(png())
        link = source.with_name('link')
        link.symlink_to(source)
        with self.assertRaises(OSError):
            core.read_image(link)

    def test_message_has_no_automatic_analysis_prefix(self):
        image = Path('/tmp/image with spaces.png')
        self.assertEqual(core.message(image, 'Corrige este diseño'),
                         '"/tmp/image with spaces.png" Corrige este diseño')
        self.assertEqual(core.message(image, ''),
                         '"/tmp/image with spaces.png" Describe lo que ves.')

    def test_control_text_rejected(self):
        for text in ('line\nline', '\r', '\x1b[31m', '\x00', '\u0085', '\u2028'):
            with self.assertRaises(core.ShotError):
                core.message(Path('/tmp/image.png'), text)
        self.assertIn('hola ñ', core.message(Path('/tmp/image.png'), 'hola ñ'))

    def test_per_session_lock(self):
        with core.target_lock(self.target):
            with self.assertRaises(core.ShotError):
                with core.target_lock(self.target):
                    self.fail('No puede adquirir el mismo bloqueo')

    def fake_sdk(self, send_side_effect=None):
        session = types.SimpleNamespace(async_send_text=AsyncMock(side_effect=send_side_effect))
        app = types.SimpleNamespace(get_session_by_id=lambda _: session, async_refresh=AsyncMock())
        connection = types.SimpleNamespace(websocket=types.SimpleNamespace(close=AsyncMock()))
        def runner(callback, retry=False):
            self.assertFalse(retry)
            asyncio.run(callback(connection))
        sdk = types.SimpleNamespace(run_until_complete=runner,
                                    async_get_app=AsyncMock(return_value=app))
        return sdk, session, app

    def test_send_separate_and_suppress_broadcast(self):
        sdk, session, _ = self.fake_sdk()
        op = core.operation()
        with patch.dict(sys.modules, {'iterm2': sdk}), patch.object(iterm_adapter, 'revalidate'):
            iterm_adapter.send(self.target, 'test', op, delay=0)
        calls = session.async_send_text.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args, ('test',))
        self.assertEqual(calls[1].args, ('\r',))
        self.assertTrue(all(c.kwargs == {'suppress_broadcast': True} for c in calls))
        self.assertEqual(json.loads((op / 'receipt.json').read_text())['state'], 'submitted')

    def test_uncertain_delivery_never_retries(self):
        sdk, session, _ = self.fake_sdk(TimeoutError())
        op = core.operation()
        with patch.dict(sys.modules, {'iterm2': sdk}), patch.object(iterm_adapter, 'revalidate'):
            with self.assertRaises(TimeoutError):
                iterm_adapter.send(self.target, 'test', op, delay=0)
        self.assertEqual(session.async_send_text.call_count, 1)
        self.assertEqual(json.loads((op / 'receipt.json').read_text())['state'], 'uncertain')

    def test_changed_target_after_text_never_sends_enter(self):
        sdk, session, _ = self.fake_sdk()
        op = core.operation()
        with patch.dict(sys.modules, {'iterm2': sdk}), \
                patch.object(iterm_adapter, 'revalidate', side_effect=[None, core.ShotError('closed')]):
            with self.assertRaises(core.ShotError):
                iterm_adapter.send(self.target, 'test', op, delay=0)
        self.assertEqual(session.async_send_text.call_count, 1)
        self.assertEqual(json.loads((op / 'receipt.json').read_text())['state'], 'uncertain')

    def test_cleanup_keeps_recent_and_incomplete_operations(self):
        import time
        old = core.operation()
        recent = core.operation()
        incomplete = core.operation()
        core.receipt(old, 'submitted')
        core.receipt(recent, 'uncertain')
        (old / 'image.png').write_bytes(png())
        for op in (old, incomplete):
            os.utime(op / 'receipt.json', (time.time() - 90_000,) * 2)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cleanup(24)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertTrue(incomplete.exists())

    def test_sdk_connection_failure_does_not_attempt_delivery(self):
        sdk, session, _ = self.fake_sdk()
        def fail_connect(callback, retry=False):
            raise TimeoutError()
        sdk.run_until_complete = fail_connect
        op = core.operation()
        with patch.dict(sys.modules, {'iterm2': sdk}):
            with self.assertRaises(TimeoutError):
                iterm_adapter.send(self.target, 'test', op, delay=0)
        session.async_send_text.assert_not_called()
        self.assertEqual(json.loads((op / 'receipt.json').read_text())['state'], 'failed')

    def test_no_tty_no_discovery_or_delivery(self):
        args = types.SimpleNamespace(command='send', session=None, image='unused', text='test')
        with patch.object(cli.sys.stdin, 'isatty', return_value=False), patch.object(cli, 'discover') as discover:
            with self.assertRaises(core.ShotError):
                cli.workflow(args)
            discover.assert_not_called()

    def test_cancel_never_connects_or_writes_terminal(self):
        source = Path(self.tmp.name) / 'image.png'
        source.write_bytes(png())
        args = types.SimpleNamespace(command='send', session='panel-1', image=str(source), text='test')
        with patch.object(cli.sys.stdin, 'isatty', return_value=True), \
                patch.object(cli, 'discover', return_value=[self.target]), \
                patch('builtins.input', side_effect=KeyboardInterrupt), patch.object(cli, 'send') as send, \
                contextlib.redirect_stdout(io.StringIO()):
            cli.workflow(args)
            send.assert_not_called()
        ops = list((core.RUNTIME / 'operations').iterdir())
        self.assertEqual(len(ops), 1)
        self.assertFalse((ops[0] / 'image.png').exists())
        self.assertEqual(json.loads((ops[0] / 'receipt.json').read_text())['state'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
