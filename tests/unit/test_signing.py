"""Signing policy tests; never modify a real keychain or sign real files."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('sign_app', ROOT / 'scripts/sign-app.py')
signing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(signing)
IDENTITY = 'A' * 40


class SigningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / 'private' / 'identity.json'
        self.keychain = self.root / 'fake.keychain-db'
        self.keychain.touch()
        self.patch = patch.object(signing, 'CONFIG', self.config)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.identity = {'identity': IDENTITY, 'keychain': str(self.keychain)}
        self.valid = types.SimpleNamespace(stdout=f'  1) {IDENTITY} "Synthetic test certificate"\n')

    def save(self, content):
        self.config.parent.mkdir()
        self.config.write_text(json.dumps(content))

    def test_unconfigured_build_remains_adhoc(self):
        with patch.object(signing.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            signing.sign(self.root / 'test.app')
        command = run.call_args_list[0].args[0]
        self.assertEqual(command[command.index('--sign') + 1], '-')
        self.assertIn('--timestamp=none', command)
        self.assertIn('--verify', run.call_args_list[1].args[0])

    def test_configured_build_uses_pinned_identity_and_keychain(self):
        self.save(self.identity)
        with patch.object(signing.subprocess, 'run', return_value=self.valid) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            signing.sign(self.root / 'test.app')
        command = run.call_args_list[1].args[0]
        self.assertEqual(command[command.index('--sign') + 1], IDENTITY)
        self.assertEqual(command[command.index('--keychain') + 1], str(self.keychain))
        self.assertNotIn('-', command)
        self.assertIn('--verify', run.call_args_list[2].args[0])

    def test_unavailable_identity_never_falls_back(self):
        self.save(self.identity)
        with patch.object(signing.subprocess, 'run', return_value=types.SimpleNamespace(stdout='0 valid identities found')) as run:
            with self.assertRaises(ValueError):
                signing.sign(self.root / 'test.app')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], '/usr/bin/security')

    def test_invalid_fingerprint_rejected_without_keychain_access(self):
        with patch.object(signing.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                signing.validate({'identity': 'Certificate name', 'keychain': str(self.keychain)})
        run.assert_not_called()

    def test_missing_keychain_rejected(self):
        with patch.object(signing.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                signing.validate({'identity': IDENTITY, 'keychain': str(self.root / 'absent')})
        run.assert_not_called()

    def test_configure_writes_private_metadata_only(self):
        with patch.object(signing.subprocess, 'run', return_value=self.valid) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            signing.configure(IDENTITY.lower(), str(self.keychain))
        self.assertEqual(json.loads(self.config.read_text()), self.identity)
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.config.parent.stat().st_mode), 0o700)
        self.assertEqual(run.call_count, 1)
        self.assertIn('find-identity', run.call_args.args[0])

    def test_symlink_config_rejected(self):
        self.config.parent.mkdir()
        self.config.symlink_to(self.root / 'absent')
        with patch.object(signing.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                signing.sign(self.root / 'test.app')
        run.assert_not_called()

    def test_invalid_config_reports_error_without_signing(self):
        self.save(['not a configuration'])
        with patch.object(signing.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(signing.main(['--check']), 1)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
