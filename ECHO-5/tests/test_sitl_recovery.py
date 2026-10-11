"""Passive recovery contracts; no simulator, MAVLink package or campaign."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from echo5 import sitl_recovery as recovery


RUNNER = Path(__file__).resolve().parents[2] / "nexus0/drone3/assets/runner.py"


class Rig:
    def __init__(self):
        self.sim = 100_000_000_000
        self.wall = 0.0
        self.calls = 0
        self.events = []
        self.driver = SimpleNamespace(conn=SimpleNamespace(messages={}), heartbeat_received=-1)
        self.result = dict(ok=False, error="TimeoutError('settled sensor observation')", disarmed=False)
        self.initial_error = self.result['error']
        self.backend = SimpleNamespace(now_ns=lambda: self.sim)

    def heartbeat(self, armed=False, received=None):
        self.driver.conn.messages['HEARTBEAT'] = SimpleNamespace(base_mode=128 if armed else 0)
        self.driver.heartbeat_received = self.sim if received is None else received

    def poll(self):
        self.calls += 1

    def sleep(self, seconds):
        self.wall += seconds

    def log(self, kind, **fields):
        self.events.append((kind, fields))

    def recover(self, poll=None, **kwargs):
        receipt = recovery.recover_exception(self.backend, self.driver, self.log, poll or self.poll,
                                             self.result, monotonic=lambda: self.wall,
                                             sleep=self.sleep, **kwargs)
        assert self.result['ok'] is False
        assert self.result['error'] == self.initial_error
        return receipt


class RecoveryTests(unittest.TestCase):
    def test_already_disarmed_requires_an_observed_heartbeat(self):
        rig = Rig()
        def poll():
            rig.poll()
            rig.heartbeat()
        receipt = rig.recover(poll)
        self.assertTrue(rig.result['disarmed'])
        self.assertEqual(rig.calls, 1)
        self.assertEqual(receipt['reason'], 'fresh_disarm')
        self.assertEqual(rig.events[-1], ('exceptional_recovery', receipt))

    def test_delayed_disarm_is_passive_and_keeps_original_failure(self):
        rig = Rig()
        def poll():
            rig.poll()
            rig.sim += 1_000_000_000
            rig.heartbeat(armed=rig.calls < 4)
        receipt = rig.recover(poll)
        self.assertTrue(rig.result['disarmed'])
        self.assertEqual(rig.calls, 4)
        self.assertEqual(receipt['heartbeat_received_ns'], 104_000_000_000)
        self.assertEqual(receipt['sim_elapsed_ns'], 4_000_000_000)

    def test_stale_missing_future_and_unreceived_heartbeats_cannot_claim_disarm(self):
        for stamp in (None, -1, 90_000_000_000, 200_000_000_000):
            with self.subTest(stamp=stamp):
                rig = Rig()
                def poll():
                    rig.poll()
                    rig.sim += 1_000_000_000
                    if stamp is not None:
                        rig.heartbeat(received=stamp)
                receipt = rig.recover(poll)
                self.assertFalse(rig.result['disarmed'])
                self.assertEqual(receipt['reason'], 'simulation_deadline')
                self.assertEqual(rig.calls, 35)

    def test_fresh_cached_disarm_is_not_new_independent_evidence(self):
        rig = Rig()
        rig.heartbeat()
        receipt = rig.recover(wall_timeout_s=.05)
        self.assertFalse(rig.result['disarmed'])
        self.assertEqual(receipt['reason'], 'wall_deadline')

    def test_frozen_simulation_clock_stops_at_wall_deadline(self):
        rig = Rig()
        receipt = rig.recover(wall_timeout_s=.05)
        self.assertEqual(receipt['reason'], 'wall_deadline')
        self.assertAlmostEqual(rig.wall, .05)
        self.assertEqual(rig.calls, 3)
        self.assertFalse(rig.result['disarmed'])

    def test_poll_exception_is_recorded_without_masking_original_error(self):
        rig = Rig()
        def poll():
            raise RuntimeError('PX4 exited')
        receipt = rig.recover(poll)
        self.assertEqual(receipt['reason'], 'recovery_error')
        self.assertEqual(receipt['error'], "RuntimeError('PX4 exited')")
        self.assertFalse(rig.result['disarmed'])

    def test_log_exception_does_not_mask_failure_or_observation(self):
        rig = Rig()
        def log(*args, **kwargs):
            raise OSError('ledger full')
        rig.log = log
        receipt = rig.recover(lambda: rig.heartbeat())
        self.assertTrue(rig.result['disarmed'])
        self.assertEqual(receipt['log_error'], "OSError('ledger full')")
        self.assertIs(rig.result['exceptional_recovery'], receipt)

    def test_no_budget_does_not_poll(self):
        rig = Rig()
        receipt = rig.recover(wall_timeout_s=0)
        self.assertEqual(receipt['reason'], 'wall_deadline')
        self.assertEqual(rig.calls, 0)

    def test_late_heartbeat_cannot_override_either_deadline(self):
        for clock in ('sim', 'wall'):
            with self.subTest(clock=clock):
                rig = Rig()
                def poll():
                    if clock == 'sim':
                        rig.sim += 35_000_000_000
                    else:
                        rig.wall += 35
                    rig.heartbeat()
                receipt = rig.recover(poll)
                self.assertFalse(rig.result['disarmed'])
                self.assertEqual(receipt['reason'], 'simulation_deadline' if clock == 'sim' else 'wall_deadline')

    def test_clock_regression_is_not_a_disarm(self):
        rig = Rig()
        def poll():
            rig.sim -= 1
            rig.heartbeat()
        receipt = rig.recover(poll)
        self.assertFalse(rig.result['disarmed'])
        self.assertEqual(receipt['reason'], 'clock_regressed')

    def test_stale_post_start_heartbeat_is_not_disarm_evidence(self):
        rig = Rig()
        def poll():
            rig.poll()
            rig.sim += 3_000_000_000
            rig.heartbeat(received=rig.sim-2_000_000_001)
        receipt = rig.recover(poll)
        self.assertFalse(rig.result['disarmed'])
        self.assertEqual(receipt['reason'], 'simulation_deadline')

    def test_wall_budget_cannot_exceed_outer_episode_maximum(self):
        rig = Rig()
        rig.sleep = lambda seconds: setattr(rig, 'wall', rig.wall+100)
        receipt = rig.recover(wall_timeout_s=100_000)
        self.assertEqual(receipt['reason'], 'wall_deadline')
        self.assertEqual(rig.wall, 900)
        self.assertEqual(rig.calls, 9)

    def test_invalid_budget_or_backend_does_not_mask_original_failure(self):
        for budget in (float('nan'), float('inf'), True, '35'):
            with self.subTest(budget=budget):
                rig = Rig()
                receipt = rig.recover(wall_timeout_s=budget)
                self.assertEqual(receipt['reason'], 'recovery_error')
                self.assertEqual(rig.calls, 0)
        rig = Rig()
        rig.backend.now_ns = lambda: None
        receipt = rig.recover()
        self.assertEqual(receipt['reason'], 'recovery_error')

    def test_recovery_never_preserves_a_success_flag(self):
        rig = Rig()
        rig.result['ok'] = True
        receipt = rig.recover(lambda: rig.heartbeat())
        self.assertEqual(receipt['reason'], 'fresh_disarm')
        self.assertFalse(rig.result['ok'])


class RunnerAdapterTests(unittest.TestCase):
    @staticmethod
    def outer(source):
        main = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        return next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)

    def test_only_recovery_and_logger_finalization_change_and_frozen_bytes_are_preserved(self):
        original = RUNNER.read_bytes()
        before = ast.parse(original)
        after = ast.parse(recovery.adapt_runner_source(original.decode()))
        old = self.outer(original)
        new = self.outer(ast.unparse(after))
        # The original teardown is intact around the new post-flight logger stop.
        self.assertEqual(ast.dump(ast.Module(body=old.finalbody, type_ignores=[])),
                         ast.dump(ast.Module(body=new.finalbody[:2]+new.finalbody[4:], type_ignores=[])))
        # Restore the two authorized adaptations: every other AST node must match.
        main = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        outer = next(n for n in main.body if isinstance(n, ast.Try) and n.finalbody)
        self.assertNotEqual(ast.dump(old.handlers[0]), ast.dump(outer.handlers[0]))
        outer.handlers = old.handlers
        outer.finalbody = old.finalbody
        self.assertEqual(ast.dump(before), ast.dump(after))
        self.assertEqual(RUNNER.read_bytes(), original)

    def test_failure_recovers_before_teardown_and_keeps_failure(self):
        rig = Rig()
        outer = self.outer(recovery.adapt_runner_source(RUNNER.read_text()))
        outer.body = ast.parse("raise TimeoutError('settled sensor observation')").body
        outer.finalbody = ast.parse("log('teardown')").body
        code = compile(ast.fix_missing_locations(ast.Module(body=[outer], type_ignores=[])), '<recovery-test>', 'exec')
        namespace = dict(result=rig.result, backend=rig.backend, driver=rig.driver, log=rig.log,
                         poll=lambda: rig.heartbeat(), cancel=lambda reason: rig.log('heartbeat_cut', reason=reason),
                         cfg={'timeouts': {'episode_s': 880}}, started=0,
                         time=SimpleNamespace(monotonic=lambda: 0))
        with patch.dict('sys.modules', sitl_recovery=recovery):
            exec(code, namespace)
        self.assertEqual([kind for kind, _ in rig.events],
                         ['heartbeat_cut', 'failure', 'exceptional_recovery', 'teardown'])
        self.assertFalse(rig.result['ok'])
        self.assertEqual(rig.result['error'], rig.initial_error)
        self.assertTrue(rig.result['disarmed'])

    def test_rejects_changed_handler_and_double_application(self):
        source = RUNNER.read_text()
        changed = source.replace("cancel('failure')", "renew()")
        for candidate in (changed, source.replace('def main():', 'def other():'),
                          recovery.adapt_runner_source(source)):
            with self.subTest(candidate=candidate[-100:]), self.assertRaises(ValueError):
                recovery.adapt_runner_source(candidate)

    def test_adapter_passes_only_remaining_episode_wall_time(self):
        rig = Rig()
        outer = self.outer(recovery.adapt_runner_source(RUNNER.read_text()))
        outer.body = ast.parse("raise TimeoutError('settled sensor observation')").body
        outer.finalbody = ast.parse("log('teardown')").body
        code = compile(ast.fix_missing_locations(ast.Module(body=[outer], type_ignores=[])), '<recovery-test>', 'exec')
        namespace = dict(result=rig.result, backend=rig.backend, driver=rig.driver, log=rig.log,
                         poll=rig.poll, cancel=lambda reason: None,
                         cfg={'timeouts': {'episode_s': 880}}, started=20,
                         time=SimpleNamespace(monotonic=lambda: 900))
        with patch.dict('sys.modules', sitl_recovery=recovery):
            exec(code, namespace)
        self.assertEqual(rig.calls, 0)
        self.assertEqual(rig.result['exceptional_recovery']['reason'], 'wall_deadline')
        self.assertFalse(rig.result['ok'])
        self.assertEqual(rig.result['error'], rig.initial_error)


if __name__ == '__main__':
    unittest.main()
