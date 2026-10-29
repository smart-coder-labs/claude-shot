import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('spike_p3', ROOT / 'scripts/spike-p3.py')
p3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p3)


class P3Tests(unittest.TestCase):
    def test_content_is_not_logged(self):
        payload = {key: 'SECRET' for key in ('prompt', 'message', 'cwd', 'transcript_path',
                   'tool_input', 'tool_response', 'last_assistant_message')}
        payload.update(hook_event_name='Stop', session_id='private-session')
        record = p3.safe_record(payload)
        self.assertEqual(set(record), {'kind', 'event', 'session_fingerprint'})
        self.assertNotIn('SECRET', json.dumps(record))
        self.assertNotIn('private-session', json.dumps(record))

    def test_exit_reason_allowlist(self):
        for reason in ('clear', 'resume', 'logout', 'prompt_input_exit', 'other'):
            record = p3.safe_record({'hook_event_name': 'SessionEnd', 'reason': reason})
            self.assertEqual(record['reason'], reason)
        record = p3.safe_record({'hook_event_name': 'SessionEnd', 'reason': 'SECRET'})
        self.assertEqual(record['reason'], 'other')
        self.assertNotIn('SECRET', json.dumps(record))

    def test_notification_allowlist(self):
        record = p3.safe_record({'hook_event_name': 'Notification', 'notification_type': 'SECRET'})
        self.assertEqual(record['notification_type'], 'other')
        with self.assertRaises(ValueError):
            p3.safe_record({'hook_event_name': 'SECRET'})

    def test_no_hook_can_mark_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for event in p3.EVENTS:
                p3.append_record(run, p3.safe_record({'hook_event_name': event,
                                 'notification_type': 'idle_prompt'}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                p3.status_report(run)
            report = json.loads(output.getvalue())
            self.assertEqual(report['state'], 'unknown')
            self.assertFalse(report['safe_to_submit'])
            self.assertEqual(os.stat(run / 'events.jsonl').st_mode & 0o777, 0o600)

    def test_log_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            victim = run / 'victim'
            victim.write_text('untouched')
            (run / 'events.jsonl').symlink_to(victim)
            with self.assertRaises(OSError):
                p3.append_record(run, {'kind': 'test'})
            self.assertEqual(victim.read_text(), 'untouched')

    def test_run_name_cannot_escape(self):
        for name in ('../outside', '/tmp/outside', 'p3-../../outside'):
            with self.assertRaises(ValueError):
                p3.checked_run(name)

    def test_existing_launch_has_actionable_error_and_never_executes(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'launched').touch()
            with patch.object(p3, 'checked_run', return_value=run), \
                    patch.object(p3.sys.stdin, 'isatty', return_value=True), \
                    patch.object(p3.sys.stdout, 'isatty', return_value=True), \
                    patch.object(p3.os, 'execvp') as execute:
                with self.assertRaisesRegex(p3.DiagnosticError, 'ya tiene un intento'):
                    p3.launch('p3-test')
                execute.assert_not_called()

    def test_launch_without_tty_does_not_start_claude(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(p3, 'checked_run', return_value=Path(tmp)), \
                    patch.object(p3.sys.stdin, 'isatty', return_value=False), \
                    patch.object(p3.os, 'execvp') as execute:
                with self.assertRaises(p3.DiagnosticError):
                    p3.launch('p3-test')
                execute.assert_not_called()
            self.assertFalse((Path(tmp) / 'launched').exists())


if __name__ == '__main__':
    unittest.main()
