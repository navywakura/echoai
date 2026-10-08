import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from seed import s6b13_audit_recovery1 as recovery


class RecoveryTests(unittest.TestCase):
    def test_transport_redirects_stderr_in_real_child(self):
        original = recovery.r.b.subprocess
        self.addCleanup(setattr, recovery.r.b, 'subprocess', original)
        recovery.install_transport()
        with patch.object(recovery.r, 'ORIGINAL_RUN', wraps=subprocess.run) as run:
            with tempfile.TemporaryFile(mode='w+') as log:
                # Check the exact dispatcher/STDOUT call shape used by frozen follow.
                with patch.object(recovery.r, 'ORIGINAL_RUN', side_effect=lambda cmd, **kw:
                                  run([sys.executable, '-c',
                                       'import sys; print("out"); print("err", file=sys.stderr)'], **kw)):
                    recovery.r.b.subprocess.run(
                        [sys.executable, '-u', '-m', 'seed.s6b13', 'audit', 'pilot'],
                        stdout=log, stderr=recovery.r.b.subprocess.STDOUT, check=True)
                log.seek(0)
                self.assertEqual(set(log.read().splitlines()), {'out', 'err'})

    def test_follow_reuses_frozen_entrypoint(self):
        with patch.object(recovery, 'prepare') as check, \
                patch.object(recovery, 'install_transport') as install, \
                patch.object(recovery.r.b, 'main') as main:
            recovery.follow()
        self.assertEqual(check.call_count, 2)
        install.assert_called_once_with()
        main.assert_called_once_with(['follow'])

    def test_recovery_rejects_changed_input(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(recovery, 'ROOT', Path(directory)), \
                patch.object(recovery, 'identity', return_value={'pilot': 'changed'}):
            (Path(directory) / 'prepared.json').write_text(json.dumps({'identity': {'pilot': 'original'}}))
            with self.assertRaisesRegex(RuntimeError, 'completed pilot changed'):
                recovery.prepare()


if __name__ == '__main__':
    unittest.main()
