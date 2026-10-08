"""CONT-B tests. A passing component does not close CONTINUITY-1."""
import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from echoai.echo4 import continuity as a
from echoai.echo4 import continuity_active as c
from echoai.echo4 import continuity_active_bench as bench
from echoai.echo4.self_final import SelfSession
from echoai.echo4.self_recovery import RecoveryStop
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent, _LearningPermission
from echoai.echo4.self_recovery_audit import sensory_hash
from echoai.echo4.self_reuse_audit import task_memory_hash


def roundtrip(run):
    raw = run.dumps()
    return c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


def rehash(data):
    raw = a.canonical(data)
    return c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


class TestActiveContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial = bench.new_run()
        cls.confirmed = copy.deepcopy(cls.initial)
        bench.finish_diagnosis(cls.confirmed)
        cls.active = copy.deepcopy(cls.confirmed)
        cls.active.start_recovery(restored=True, same_context=True)
        cls.active.step()
        cls.raw = cls.active.dumps()
        cls.digest = hashlib.sha256(cls.raw).hexdigest()

    def restored(self):
        return c.loads(self.raw, expected_sha256=self.digest)

    def changed(self, tag, field, value):
        data = json.loads(self.raw)
        record = next(r for r in data['state']['objects'] if r['type'] == tag)
        record['fields'][field] = value
        return data

    def test_full_roundtrip_and_live_permission_cycle(self):
        r = self.restored()
        self.assertEqual(r.dumps(), self.raw)
        self.assertIs(r.agent.self_model.agent, r.agent)
        self.assertIs(r.agent.cam, r.agent.sensation.cam)
        self.assertIs(r.agent.cam, r.agent.boundary.cam)
        self.assertIs(r.agent.t, r.agent.sensation.world)
        self.assertIs(r.agent.boundary, r.agent.self_change.boundary)
        self.assertIsNot(r.agent, self.active.agent)

    def test_every_supported_case_roundtrips(self):
        for case in bench.CASES:
            with self.subTest(case=case):
                r = bench.prepared(case)
                self.assertEqual(roundtrip(r).dumps(), r.dumps())

    def test_pending_plan_preserves_forecasts_and_token(self):
        r = copy.deepcopy(self.initial)
        p = r.choose_probe(18)
        loaded = roundtrip(r)
        self.assertEqual(loaded.session.model.pending, r.session.model.pending)
        self.assertEqual(loaded.session.model.pending[0], p)
        with self.assertRaises(ValueError):
            loaded.choose_probe(18)
        self.assertEqual(r.dumps(), loaded.dumps())

    def test_received_receipt_is_consumed_once(self):
        r = bench.prepared('inbox')
        loaded = roundtrip(r)
        self.assertEqual(r.consume_receipt(), loaded.consume_receipt())
        self.assertEqual(r.dumps(), loaded.dumps())
        before = loaded.dumps()
        with self.assertRaises(ValueError):
            loaded.consume_receipt()
        self.assertEqual(loaded.dumps(), before)

    def test_inbox_cannot_overwrite_evidence(self):
        r = bench.prepared('inbox')
        before = r.dumps()
        with self.assertRaises(ValueError):
            r.queue_receipt(r.inbox)
        with self.assertRaises(ValueError):
            r.cancel()
        self.assertEqual(r.dumps(), before)

    def test_invalid_receipt_stays_invalid_after_resume(self):
        r = bench.prepared('pending')
        receipt = replace(bench.physical_receipt(r), same_context=False)
        r.queue_receipt(receipt)
        r = roundtrip(r)
        result = r.consume_receipt()
        self.assertEqual(result['label'], 'unknown')
        self.assertFalse(result['confirmed'])
        with self.assertRaises(ValueError):
            r.start_recovery(restored=True, same_context=True)

    def test_cancel_preserves_abstention_and_cannot_authorize(self):
        r = roundtrip(bench.prepared('cancelled'))
        self.assertEqual(r.session.diagnosis()['reason'], 'session_cancelled')
        self.assertIsNone(r.session.model.pending)
        with self.assertRaises(ValueError):
            r.start_recovery(restored=True, same_context=True)

    def test_preconfirmation_cannot_act(self):
        r = roundtrip(self.initial)
        before = r.dumps()
        with self.assertRaises(ValueError):
            r.start_recovery(restored=True, same_context=True)
        with self.assertRaises(RuntimeError):
            r.step()
        self.assertEqual(r.dumps(), before)

    def test_selective_learning_hold_and_allow_preserved(self):
        left = copy.deepcopy(self.confirmed)
        left.start_recovery(restored=True, same_context=True)
        right = roundtrip(left)
        decisions = []
        for _ in range(5):
            before = (copy.deepcopy(vars(left.agent.t)), sensory_hash(left.agent.sensation))
            self.assertEqual(left.step(), right.step())
            decisions.append(left.agent.recovery.last['allowed'])
            if not decisions[-1]:
                self.assertEqual(before, (vars(left.agent.t), sensory_hash(left.agent.sensation)))
            self.assertEqual(left.dumps(), right.dumps())
        self.assertIn(False, decisions)
        self.assertIn(True, decisions)

    def test_fresh_process_recovery(self):
        r = copy.deepcopy(self.active)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'active.json'
            digest = r.save(path)
            self.assertEqual(bench.trajectory(r, 4), bench.resumed(path, digest, 4))

    def test_fresh_process_pending_receipt_then_confirmation(self):
        r = bench.prepared('inbox')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'pending.json'
            digest = r.save(path)
            self.assertEqual(bench.trajectory(r, 2), bench.resumed(path, digest, 2))

    def test_reuse_arm_preserves_global_and_life_clocks(self):
        r = bench.prepared('reuse_armed')
        self.assertEqual((r.next_turn, r.life_origin, r.agent.life_turns), (24, 24, 0))
        loaded = roundtrip(r)
        before = task_memory_hash(loaded.agent)
        self.assertEqual(r.step(greedy=True), loaded.step(greedy=True))
        self.assertEqual(loaded.agent.reuse_decision.source, 't')
        self.assertEqual(task_memory_hash(loaded.agent), before)
        self.assertEqual(loaded.dumps(), r.dumps())
        self.assertEqual((loaded.next_turn, loaded.agent.life_turns), (25, 1))

    def test_no_t_ablation_is_not_silently_reenabled(self):
        r = roundtrip(bench.prepared('reuse_no_t'))
        r.step(greedy=True)
        self.assertEqual(r.agent.reuse_decision.source, 'q_ablation')
        self.assertFalse(r.agent.reuse_use_t)

    def test_completed_trial_cannot_execute_twice(self):
        for case in ('reuse_done', 'exposure_done'):
            r = roundtrip(bench.prepared(case))
            before = r.dumps()
            with self.assertRaises(RuntimeError):
                r.step()
            self.assertEqual(before, r.dumps())

    def test_veto_stop_survives_resume(self):
        r = roundtrip(bench.prepared('veto'))
        self.assertEqual(r.agent.last_gate_decision, 2)
        self.assertEqual(r.agent.recovery.stopped, 'gate_veto')
        before = r.dumps()
        with self.assertRaises(RecoveryStop):
            r.step()
        self.assertEqual(r.dumps(), before)

    def test_normal_stop_is_serializable_without_a_fictitious_step(self):
        r = roundtrip(bench.prepared('stopped'))
        self.assertEqual(r.agent.recovery.stopped, 'no_safe_action')
        self.assertFalse(r.agent.episode_terminal)
        self.assertEqual(r.next_turn, r.agent.env.total_steps)
        with self.assertRaises(RecoveryStop):
            r.step()

    def test_terminal_does_not_revive(self):
        r = roundtrip(bench.prepared('terminal'))
        self.assertTrue(r.agent.episode_terminal)
        before = r.dumps()
        with self.assertRaises(RuntimeError):
            r.step()
        self.assertEqual(r.dumps(), before)

    def test_snapshot_readonly_and_restoration_isolated(self):
        before = self.active.dumps()
        r = self.restored()
        r.step()
        self.assertEqual(before, self.active.dumps())
        self.assertNotEqual(r.dumps(), before)

    def test_original_digest_detects_corruption(self):
        for raw in (self.raw[:-1], self.raw + b' ', b'{}', b''):
            with self.assertRaises(ValueError):
                c.loads(raw, expected_sha256=self.digest)

    def test_external_digest_required(self):
        with self.assertRaises(TypeError):
            c.loads(self.raw)
        for digest in (None, '', 1, '0' * 64):
            with self.assertRaises(ValueError):
                c.loads(self.raw, expected_sha256=digest)

    def test_schema_profile_source_fail_closed(self):
        for key in ('schema', 'profile', 'sources'):
            data = json.loads(self.raw)
            data[key] = 'different'
            with self.assertRaises(ValueError):
                rehash(data)

    def test_cont_a_and_b_are_not_silent_migrations(self):
        with self.assertRaises(ValueError):
            a.loads(self.raw, expected_sha256=self.digest)
        with self.assertRaises(ValueError):
            a.ContinuityRun(self.active.agent)

    def test_pending_physical_forecast_rejected(self):
        for attr in ('sensation', 'recovery'):
            r = copy.deepcopy(self.active)
            getattr(r.agent, attr).pending = ('incomplete',)
            with self.assertRaises(ValueError):
                r.dumps()

    def test_false_confirmation_is_rejected_even_with_new_digest(self):
        data = copy.deepcopy(self.initial.snapshot())
        session = next(r for r in data['state']['objects'] if r['type'] == 'session')
        session['fields']['finished'] = True
        with self.assertRaises(ValueError):
            rehash(data)

    def test_forecast_mutation_detected_from_public_inputs(self):
        r = bench.prepared('pending')
        r.session.model.pending = (replace(r.session.model.pending[0], worst_states=999), *r.session.model.pending[1:])
        with self.assertRaises(ValueError):
            r.dumps()

    def test_journal_order_and_budget_fail_closed(self):
        for events in ([('consume', self.initial.nominal)], [('unknown', 18)], [('choose', 18)] * 15):
            r = copy.deepcopy(self.initial)
            r.events = events
            with self.assertRaises((ValueError, RuntimeError)):
                r.dumps()

    def test_clock_mutants_rejected(self):
        for field, value in (('next_turn', 0), ('life_origin', 1), ('next_turn', True)):
            r = copy.deepcopy(self.active)
            setattr(r, field, value)
            with self.assertRaises(ValueError):
                r.dumps()
        data = json.loads(self.raw)
        data['diagnostic_clock']['reported_ticks'] += 1
        with self.assertRaises(ValueError):
            rehash(data)

    def test_permission_alias_cannot_point_elsewhere(self):
        r = copy.deepcopy(self.active)
        r.agent.self_model = _LearningPermission(copy.deepcopy(r.agent))
        with self.assertRaises(ValueError):
            r.dumps()

    def test_resource_body_and_learning_counter_mutants(self):
        for tag, field, value in (('recovery_agent','H',0), ('recovery_env','resource_in',999),
                                  ('recovery','held',999), ('recovery','steps',0),
                                  ('recovery_agent','cortex_enabled',True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                rehash(self.changed(tag, field, value))

    def test_no_unknown_classes_fields_or_references(self):
        for mode in ('class','field','ref'):
            data = json.loads(self.raw)
            rec = data['state']['objects'][0]
            if mode == 'class':
                rec['type'] = 'os.system'
            elif mode == 'field':
                rec['fields']['callback'] = 'untrusted'
            else:
                rec['fields']['cam'] = {'ref':999999}
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                rehash(data)

    def test_extra_runtime_hooks_and_mutable_aliases(self):
        for location in ('agent','env','array','run'):
            r = copy.deepcopy(self.active)
            if location == 'agent':
                r.agent.custom = 1
            elif location == 'env':
                r.agent.env.step_homeostatic = lambda *_: None
            elif location == 'run':
                r.external = 1
            else:
                r.agent.q.q[1] = r.agent.q.q[0]
            with self.subTest(location=location), self.assertRaises(ValueError):
                r.dumps()

    def test_interrupted_turn_stays_poisoned(self):
        r = copy.deepcopy(self.active)
        with (patch.object(SelfRecoveryAgent, 'turn', side_effect=RuntimeError('interrupted')),
              self.assertRaises(RuntimeError)):
            r.step()
        with self.assertRaises(ValueError):
            r.dumps()
        with self.assertRaises(RuntimeError):
            r.step()

    def test_interrupted_consumption_stays_poisoned(self):
        r = bench.prepared('inbox')
        with (patch.object(SelfSession, 'consume', side_effect=RuntimeError('interrupted')),
              self.assertRaises(RuntimeError)):
            r.consume_receipt()
        with self.assertRaises(ValueError):
            r.dumps()

    def test_unrecorded_stop_is_an_interruption_not_a_clean_checkpoint(self):
        r = copy.deepcopy(self.active)
        with (patch.object(SelfRecoveryAgent, 'turn', side_effect=RecoveryStop('external interruption')),
              self.assertRaises(RecoveryStop)):
            r.step()
        with self.assertRaises(ValueError):
            r.dumps()

    def test_keyboard_interrupt_poisoned_before_leaving_operation(self):
        for phase in ('turn', 'consume'):
            r = copy.deepcopy(self.active) if phase == 'turn' else bench.prepared('inbox')
            cls = SelfRecoveryAgent if phase == 'turn' else SelfSession
            with patch.object(cls, phase, side_effect=KeyboardInterrupt()), self.assertRaises(KeyboardInterrupt):
                r.step() if phase == 'turn' else r.consume_receipt()
            with self.assertRaises(ValueError):
                r.dumps()

    def test_busy_capture_and_no_overwrite(self):
        r = copy.deepcopy(self.active)
        r._busy = True
        with self.assertRaises(ValueError):
            r.dumps()
        r._busy = False
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            digest = r.save(path)
            r.step()
            with self.assertRaises(FileExistsError):
                r.save(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_json_floats_duplicates_depth_and_byte_budget(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":1.2}', b'['*2000+b']'*2000):
            with self.assertRaises(ValueError):
                c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        with patch.object(a, 'MAX_BYTES', len(self.raw)-1), self.assertRaises(ValueError):
            self.restored()


if __name__ == '__main__':
    unittest.main()
