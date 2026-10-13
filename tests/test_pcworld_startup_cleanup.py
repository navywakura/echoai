"""Bounded real-systemd startup cancellation regressions; synthetic data only."""
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from .repoworld_support import ROOT
from echoai.pcworld import runner


class StartupCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pcworld-startup-test-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.units = []
        self.frontends = []
        self.registrars = []
        self.timers = []
        self.addCleanup(self.cleanup_owned_jobs)

    def cleanup_owned_jobs(self):
        for timer in self.timers:
            timer.join(timeout=2)
        for frontend in self.frontends + self.registrars:
            if frontend.poll() is None:
                frontend.kill()
            frontend.wait(timeout=3)
        for unit in self.units:
            runner._stop(unit)
            subprocess.run(['/usr/bin/systemctl', '--user', 'reset-failed', unit],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3)
    def delayed_frontend(self, *, queued=False):
        original = subprocess.Popen

        def launch(argv, *args, **kwargs):
            if not isinstance(argv, list) or argv[0] != '/usr/bin/systemd-run':
                return original(argv, *args, **kwargs)
            self.units.append(next(a.split('=', 1)[1] for a in argv if a.startswith('--unit=')))
            if queued:
                # Model an already-forwarded manager request: registration can
                # finish independently of the frontend's subsequent death.
                def register():
                    self.registrars.append(original(argv, stdin=subprocess.DEVNULL,
                                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                timer = threading.Timer(.25, register)
                self.timers.append(timer)
                timer.start()
                script = 'import time; time.sleep(10)'
            else:
                script = 'import os,sys,time; time.sleep(.25); os.execv(sys.argv[1],sys.argv[1:])'
            frontend = original([sys.executable, '-B', '-c', script, *argv], *args, **kwargs)
            self.frontends.append(frontend)
            return frontend

        return patch.object(runner.subprocess, 'Popen', side_effect=launch)

    def run_timeout(self):
        return runner.execute(self.work, ['/usr/bin/python3', '-I', '-c', 'import time; time.sleep(10)'],
                              limits={'wall_ms':60, 'cpu_ms':100})

    def test_unobserved_startup_cancellation_cannot_claim_an_empty_job(self):
        with self.delayed_frontend():
            with self.assertRaisesRegex(RuntimeError, 'ISOLATION_FAILURE.*startup cancellation'):
                self.run_timeout()
        self.assertIsNotNone(self.frontends[0].returncode)
        time.sleep(.3)  # Beyond the delayed exec, so a late registration is visible.
        state = runner._show(self.units[0])
        self.assertEqual(state.get('LoadState'), 'not-found', state)

    def test_registration_after_frontend_death_is_stopped_and_observed(self):
        with self.delayed_frontend(queued=True):
            result = self.run_timeout()
        self.assertEqual(result['status'], 'TIMEOUT', result)
        self.assertTrue(result['isolation']['job_empty'], result)
        self.assertGreater(result['resources']['cpu_us'], 0, result)
        state = runner._show(self.units[0])
        self.assertIn(state.get('ActiveState'), ('inactive', 'failed'), state)
        if state.get('ControlGroup'):
            group = Path('/sys/fs/cgroup' + state['ControlGroup'])
            self.assertFalse(group.exists() and (group/'cgroup.procs').read_text().strip(), state)
