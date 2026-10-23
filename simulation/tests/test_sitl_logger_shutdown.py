"""Post-flight evidence shutdown: preserve the mission and finish ULog writes."""
import ast
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from echo5 import sitl_recovery as recovery
from echo5 import sitl

RUNNER = Path(__file__).resolve().parents[2] / 'nexus0/drone3/assets/runner.py'


class LoggerShutdownTests(unittest.TestCase):
    def test_adapted_finalizer_stops_logger_before_px4_and_gazebo(self):
        source = recovery.adapt_runner_source(RUNNER.read_text())
        main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        final = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody).finalbody
        # Execute real finalization through process teardown; omit result file I/O.
        end = next(i for i, n in enumerate(final) if isinstance(n, ast.For))
        code = compile(ast.fix_missing_locations(ast.Module(body=final[:end+1], type_ignores=[])), '<shutdown>', 'exec')
        events = []
        class Process:
            def __init__(self, name): self.name = name
            def poll(self): return None
            def terminate(self): events.append(self.name+'_terminate')
            def wait(self, timeout=None): events.append(self.name+'_wait')
        def command(argv, **kwargs):
            events.append('logger_stop')
            self.assertEqual(argv[-1], 'stop')
            self.assertTrue(argv[0].endswith('/px4-logger'))
            self.assertGreater(kwargs['timeout'], 0)
            return subprocess.CompletedProcess(argv, 0, '', '')
        namespace = dict(stop_pump=SimpleNamespace(set=lambda: events.append('cancel_pump')),
            pump=SimpleNamespace(join=lambda timeout: events.append('pump_join')),
            result=dict(ok=False,error='original failure'), cfg={'timeouts': {'episode_s': 880}},
            driver=SimpleNamespace(events=[]), lines=[], started=0,
            time=SimpleNamespace(monotonic=lambda: 1), ledger=SimpleNamespace(close=lambda: events.append('ledger_close')),
            private=SimpleNamespace(close=lambda: events.append('private_close')), px4=Process('px4'), gz=Process('gz'),
            work=Path('/out/wd'), pxenv={}, subprocess=subprocess,
            log=lambda kind, **kw: events.append(kind))
        with patch.dict('sys.modules', sitl_recovery=recovery), patch('subprocess.run', side_effect=command):
            exec(code, namespace)
        self.assertLess(events.index('logger_stop'), events.index('px4_terminate'))
        self.assertLess(events.index('pump_join'), events.index('logger_stop'))
        self.assertLess(events.index('logger_stop'), events.index('ledger_close'))
        self.assertLess(events.index('px4_wait'), events.index('gz_terminate'))
        self.assertFalse(namespace['result']['ok'])
        self.assertEqual(namespace['result']['error'], 'original failure')
        self.assertTrue(namespace['result']['logger_shutdown']['complete'])
        # The real finalizer must still clean up when shutdown/logging fails.
        events.clear()
        namespace['log'] = lambda *a, **kw: (_ for _ in ()).throw(OSError('ledger full'))
        with patch.dict('sys.modules', sitl_recovery=recovery), patch('subprocess.run', side_effect=subprocess.TimeoutExpired([], 8)):
            exec(code, namespace)
        self.assertIn('gz_wait', events)
        self.assertFalse(namespace['result']['logger_shutdown']['complete'])
        self.assertEqual(namespace['result']['error'], 'original failure')

    def test_remaining_budget_caps_shutdown_and_expiry_does_not_start_client(self):
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')) as command:
            receipt = recovery.stop_logger(SimpleNamespace(poll=lambda: None), Path('/out/wd'), {}, {},
                                           lambda *a, **kw: None, wall_timeout_s=.125)
        self.assertTrue(receipt['complete'])
        self.assertEqual(command.call_args.kwargs['timeout'], .125)
        for timeout in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(timeout=timeout), patch('subprocess.run') as command:
                receipt = recovery.stop_logger(SimpleNamespace(poll=lambda: None), Path('/out/wd'), {}, {},
                                               lambda *a, **kw: None, wall_timeout_s=timeout)
                self.assertFalse(receipt['complete'])
                command.assert_not_called()

    def test_auditor_requires_matching_receipt_after_disarm(self):
        payload = dict(schema='echo5.sitl.logger-shutdown.v1',
            command=['/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4-logger', 'stop'],
            complete=True, returncode=0, timeout_s=8, wall_s=.5, stdout='', stderr='')
        disarm = dict(kind='disarmed', now_ns=100, mono_ns=200)
        shutdown = dict(kind='logger_shutdown', now_ns=101, mono_ns=201, **payload)
        result = dict(disarmed=True, logger_shutdown=payload)
        self.assertTrue(sitl._logger_shutdown_valid([disarm, shutdown], result))
        for trace, final in (([shutdown, disarm], result),
                             ([disarm, shutdown, shutdown], result),
                             ([shutdown], result),
                             ([disarm, dict(shutdown, mono_ns=199)], result),
                             ([disarm, shutdown], dict(result, logger_shutdown=dict(payload, complete=False))),
                             ([disarm, shutdown], dict(result, disarmed=False))):
            self.assertFalse(sitl._logger_shutdown_valid(trace, final))

    def test_failed_or_timed_out_flush_retains_original_error_and_returns_for_cleanup(self):
        for outcome in (subprocess.CompletedProcess([], 1, '', 'failed'),
                        subprocess.CompletedProcess([], 0, 'timeout, forcing stop', ''),
                        subprocess.TimeoutExpired(['px4-logger','stop'], 8),
                        OSError('missing logger client')):
            with self.subTest(outcome=outcome):
                result = dict(ok=False, error='original failure')
                run = patch('subprocess.run', side_effect=outcome) if isinstance(outcome, Exception) else patch('subprocess.run', return_value=outcome)
                with run:
                    receipt = recovery.stop_logger(SimpleNamespace(poll=lambda: None), Path('/out/wd'), {}, result,
                                                   lambda *a, **kw: None)
                self.assertFalse(receipt['complete'])
                self.assertFalse(result['ok'])
                self.assertEqual(result['error'], 'original failure')

    def test_exited_px4_cannot_claim_flush(self):
        with patch('subprocess.run') as command:
            receipt = recovery.stop_logger(SimpleNamespace(poll=lambda: 0), Path('/out/wd'), {}, {}, lambda *a, **kw: None)
        self.assertFalse(receipt['complete'])
        command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
