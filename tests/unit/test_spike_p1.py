"""Pruebas del arnés, NO evidencia de viabilidad de las APIs reales."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('spike_p1', ROOT / 'scripts/spike-p1.py')
spike = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spike)


class SpikeTests(unittest.TestCase):
    def test_split_and_refuse_duplicate_trial(self):
        calls = []

        def fake_run(*args):
            calls.append(args)
            if args[:3] == ('it2', 'session', 'list'):
                return json.dumps([{'id': 'test-panel', 'tty': '/dev/ttys999'}])
            if args[0] == 'ps':
                return '123 ttys999 claude\n'
            return ''

        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            trial = Path(tmp) / 'trial'
            argv = ['spike-p1.py', '--session', 'test-panel', '--tty', 'ttys999',
                    '--pid', '123', '--trial', str(trial), '--split-submit',
                    '--confirmed-empty-idle-broadcast-off']
            with patch.object(sys, 'argv', argv), patch.object(spike, 'run', fake_run), \
                    patch.object(spike.time, 'sleep'):
                spike.main()
                sends = [c for c in calls if c[:3] == ('it2', 'session', 'send')]
                self.assertEqual(len(sends), 2)
                self.assertNotIn('\r', sends[0][3])
                self.assertEqual(sends[1][3], '\r')
                self.assertEqual(sends[1][-1], 'test-panel')
                self.assertTrue((trial / 'visual sample.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertEqual(json.loads((trial / 'receipt.json').read_text())['state'], 'submitted')
                with self.assertRaises(FileExistsError):
                    spike.main()
                self.assertEqual(len([c for c in calls if c[:3] == ('it2', 'session', 'send')]), 2)

    def test_closed_panel_never_sends(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            argv = ['spike-p1.py', '--session', 'missing', '--tty', 'ttys999',
                    '--pid', '123', '--trial', str(Path(tmp) / 'trial'),
                    '--confirmed-empty-idle-broadcast-off']
            with patch.object(sys, 'argv', argv), patch.object(spike, 'run', return_value='[]') as run:
                with self.assertRaises(RuntimeError):
                    spike.main()
                self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
