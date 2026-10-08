"""Repair regressions, not sealed transfer acceptance."""
import copy
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from echoai.nexus0.transfer3 import policy
from echoai.nexus0.transfer3.repair_v5 import (
    CheckedEffects, restore, episode, reserve_violation, FAILURES,
)
from echoai.nexus0.transfer3.custody_v2 import seal_fixture, open_verified_fixture
from echoai.nexus0.transfer3.diagnostic_v5 import intervene, action, conflicting_rankings
from echoai.nexus0.transfer3.rehearsal_v2 import Space
from echoai.nexus0.compose1_v3.space import Space as DynamicSpace
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1.model import state_packet
from echoai.nexus0.sim3.canon import sha256_bytes, Sim3Error
from echoai.nexus0.sim3.seal import (
    inventory_bytes, inventory_commitment, REHEARSAL_SALT, read_seal,
    open_once, protocol_commitment, REHEARSAL_SECRET,
)


class RepairTests(unittest.TestCase):
    def test_terminal_has_no_bootstrap(self):
        m = CheckedEffects()
        a, b = state_packet(1, 3), state_packet(2, 3)
        slot = m.slot(b, True)
        m.q.set(slot, 0, 100)
        delta = m.learn_reward(a, 0, 31, b, terminal=True)
        self.assertEqual(delta, 31)
        self.assertEqual(m.values(a)[0], 7)

    def test_nonterminal_bootstraps(self):
        m = CheckedEffects()
        a, b = state_packet(1, 3), state_packet(2, 3)
        m.q.set(m.slot(b, True), 0, 100)
        self.assertEqual(m.learn_reward(a, 0, -1, b), 86)

    def test_full_cam_does_not_alias_last_q_row(self):
        m = CheckedEffects()
        for i in range(4096):
            m.slot(state_packet(i, 7), True)
        m.q.set(4095, 0, 99)
        before = m.fingerprint()
        with self.assertRaisesRegex(ValueError, 'CAM capacity'):
            m.learn_reward(state_packet(0, 3), 0, -10, state_packet(1, 3))
        self.assertEqual(m.fingerprint(), before)
        self.assertEqual(m.q.get(4095, 0), 99)

    def test_existing_rows_still_learn_when_full(self):
        m = CheckedEffects()
        for i in range(4096):
            m.slot(state_packet(i, 3), True)
        m.learn_reward(state_packet(0, 3), 0, 32, state_packet(1, 3), terminal=True)
        self.assertEqual(m.values(state_packet(0, 3))[0], 8)

    def test_restore_refuses_allocation_failure(self):
        payload = dict(schema=policy.SCHEMA, q=[dict(feature=112, values=[1,0,0,0,0,0,0])])
        from echoai.core.cam import Cam
        with patch.object(Cam, 'put', return_value=-1):
            with self.assertRaises(ValueError):
                restore(payload)

    def test_roundtrip(self):
        payload = dict(schema=policy.SCHEMA, q=[dict(feature=112, values=[1,0,0,0,0,0,0])])
        self.assertEqual(policy.export(restore(payload)), payload)

    def test_schema_maximum_fits_fresh_cam(self):
        p = dict(schema=policy.SCHEMA, q=[dict(feature=i, values=[1,0,0,0,0,0,0])
                                       for i in range(1728)])
        m = restore(p)
        self.assertEqual(m.cam.used, 1733)
        self.assertEqual(policy.export(m), p)

    def test_missing_prediction_never_enters_reserve_adjudicator(self):
        world = Space(20264401)
        # Independent of any learner or predict() return value.
        with patch.object(CheckedEffects, 'predict', return_value=None):
            self.assertIsInstance(reserve_violation(world, 0), bool)

    def test_bad_options_fail_before_world_changes(self):
        for options in (dict(move_budget=True), dict(move_budget=0),
                        dict(failure_bonus=True), dict(reward_kind='unknown')):
            w = Space(20264401)
            with self.assertRaises(ValueError):
                episode(w, policy.scratch(), **options)
            self.assertEqual(w.steps, 0)

    def test_arrival_terminal_and_exact_capture_count(self):
        result = episode(Space(20264401), policy.scratch())
        self.assertEqual(result['status'], 'reached')
        self.assertTrue(result['rows'][-1]['learning']['terminal'])
        self.assertEqual(result['visits'], result['moves']+1)
        self.assertEqual(result['reserve_violations'], 0)

    def test_budget_cut_is_not_terminal(self):
        r = episode(Space(20264401), policy.scratch(), move_budget=1)
        self.assertEqual(r['moves'], 1)
        self.assertEqual(r['status'], 'training_budget_cut')
        self.assertFalse(r['rows'][-1]['learning']['terminal'])

    def test_failure_updates_last_real_transition_once(self):
        for energy, status in ((240, 'abandoned_at_home'), (1000, 'budget_exhausted')):
            with self.subTest(energy=energy):
                world = DynamicSpace(20264401, 'closed')
                world.energy = energy
                a = episode(world, policy.scratch(), reward_kind='step_and_arrival')
                self.assertEqual(a['status'], status)
                self.assertIn(a['status'], FAILURES)
                self.assertTrue(a['rows'][-1]['learning']['terminal'])
                self.assertEqual(a['rows'][-1]['learning']['reward'], -33)
                self.assertEqual(sum(sum(v) for v in a['counts'].values()), a['moves'])

    def test_initial_failure_no_fabricated_learning(self):
        w = Space(20264401)
        w.energy = 0
        r = episode(w, policy.scratch())
        self.assertEqual(r['status'], 'abandoned_at_home')
        self.assertEqual(r['moves'], 0)
        self.assertEqual(r['payload'], policy.scratch())

    def test_dynamic_scan_once(self):
        class Once(DynamicSpace):
            def scan(self):
                if getattr(self, 'last_scan', -1) == self.steps:
                    raise AssertionError('second scan at same timestamp')
                self.last_scan = self.steps
                return super().scan()
        w = Once(20264401, 'dynamic')
        r = episode(w, policy.scratch())
        self.assertTrue(w.moved)
        self.assertEqual(r['ingestions'], r['moves']+1)
        self.assertEqual(r['collisions'], 0)

    def test_exam_does_not_learn_and_uses_same_adjudicator(self):
        with patch('echoai.nexus0.transfer3.repair_v5.reserve_violation',
                   wraps=reserve_violation) as judge:
            a = episode(Space(20264401), policy.scratch(), learn=False)
            self.assertEqual(judge.call_count, a['moves'])
        self.assertTrue(a['model_unchanged'])
        self.assertTrue(all(r['learning'] is None for r in a['rows']))

    def test_intervention_does_not_change_source_agent(self):
        w = Space(20264401)
        a = Composer(restore(policy.scratch()).snapshot(), w.goal)
        before = a.model.fingerprint()
        f = w.scan()
        zero = intervene(a, f, [0]*7)
        self.assertEqual(a.turns, 0)
        self.assertEqual(a.visits, {})
        self.assertEqual(a.model.fingerprint(), before)
        self.assertEqual(action(a.decide(f)), action(zero))

    def test_different_choice_sets_not_mislabelled_alias_conflict(self):
        rows = [dict(feature='x', oracle_distances={'0':1,'2':2}),
                dict(feature='x', oracle_distances={'1':1,'3':2})]
        self.assertEqual(conflicting_rankings(rows), [])
        rows.append(dict(feature='x', oracle_distances={'0':3,'2':1}))
        self.assertEqual(conflicting_rankings(rows), [dict(feature='x', action_pair=[0,2])])

    def test_fast_probes_match_full_private_copy(self):
        w = Space(20264401)
        a = Composer(restore(policy.scratch()).snapshot(), w.goal)
        for _ in range(8):
            frame = w.scan()
            before = copy.deepcopy(a.visits)
            for preferred in range(4):
                values = [-127]*4+[0]*3
                values[preferred] = 127
                slow = copy.deepcopy(a, {id(a.model):a.model})
                slow.model = copy.copy(a.model)
                slow.model.values = lambda feature:list(values)
                self.assertEqual(intervene(a, frame, values), slow.decide(frame))
            self.assertEqual(a.visits, before)
            d = a.decide(frame)
            if d['status'] not in ('moving', 'returning'):
                break
            w.step(action(d))


class BoundCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'public-dummy-C.json'
        self.entries = [dict(split='C', index=0, package_sha256='1'*64)]
        self.sha = sha256_bytes(inventory_bytes(self.entries))
        self.notice = dict(schema='transfer3-custody-v1', kind='rehearsal',
            protocol_sha256='2'*64,
            protocol_commitment=protocol_commitment('2'*64, REHEARSAL_SECRET),
            custodian='public test fixture', publication_reference='not a publication',
            splits={s:dict(count=1, inventory_commitment=inventory_commitment(
                REHEARSAL_SALT, inventory_bytes(self.entries))) for s in ('B','C')})

    def create(self, sha=None):
        seal_fixture(self.path, self.notice, 'C', sha or self.sha)

    def reveal(self):
        self.assertEqual(read_seal(self.path).state, 'opened')
        return self.entries, REHEARSAL_SALT

    def test_order_binding_and_once(self):
        self.create()
        self.assertEqual(read_seal(self.path).state, 'sealed')
        with open_verified_fixture(self.path, self.notice, 'C', self.reveal) as verified:
            self.assertEqual(verified['inventory_sha256'], self.sha)
            with self.assertRaises(Sim3Error):
                with open_verified_fixture(self.path, self.notice, 'C', self.reveal):
                    self.fail('concurrent open')
        self.assertEqual(read_seal(self.path).state, 'consumed')
        with self.assertRaises(Sim3Error):
            with open_verified_fixture(self.path, self.notice, 'C', self.reveal):
                self.fail('second open')

    def test_wrong_latch_hash_consumes_without_yield(self):
        self.create('0'*64)
        with self.assertRaisesRegex(ValueError, 'inventory/latch'):
            with open_verified_fixture(self.path, self.notice, 'C', self.reveal):
                self.fail('unverified inventory yielded')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_notice_mutation_rejected_before_loader(self):
        self.create()
        for field in ('protocol_sha256',):
            notice = copy.deepcopy(self.notice)
            notice[field] = '3'*64
            with self.assertRaisesRegex(ValueError, 'binding'):
                with open_verified_fixture(self.path, notice, 'C', lambda:self.fail('loader called')):
                    self.fail('yielded')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_wrong_salt_consumes(self):
        self.create()
        with self.assertRaises(ValueError):
            with open_verified_fixture(self.path, self.notice, 'C', lambda:(self.entries, bytes(32))):
                self.fail('wrong salt accepted')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_wrong_inventory_consumes(self):
        self.create()
        rows = copy.deepcopy(self.entries)
        rows[0]['package_sha256'] = '9'*64
        with self.assertRaises(ValueError):
            with open_verified_fixture(self.path, self.notice, 'C', lambda:(rows, REHEARSAL_SALT)):
                self.fail('wrong inventory accepted')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_wrong_split_never_calls_loader(self):
        self.create()
        with self.assertRaises(ValueError):
            with open_verified_fixture(self.path, self.notice, 'B', lambda:self.fail('loader called')):
                self.fail('wrong split accepted')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_crash_is_consumed_on_next_attempt(self):
        self.create()
        pid = os.fork()
        if pid == 0:
            with open_verified_fixture(self.path, self.notice, 'C', self.reveal):
                os._exit(0)
            os._exit(1)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(status, 0)
        self.assertEqual(read_seal(self.path).state, 'opened')
        with self.assertRaises(Sim3Error) as caught:
            with open_verified_fixture(self.path, self.notice, 'C', lambda:self.fail('loader called')):
                self.fail('crashed exam reopened')
        self.assertEqual(caught.exception.code, 'seal_crash_consumed')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_loader_failure_consumes(self):
        self.create()
        def fail():
            raise RuntimeError('loader died')
        with self.assertRaises(RuntimeError):
            with open_verified_fixture(self.path, self.notice, 'C', fail):
                self.fail('yielded')
        self.assertEqual(read_seal(self.path).state, 'consumed')

    def test_campaign_placeholder_or_real_string_still_disabled(self):
        self.notice['kind'] = 'campaign'
        with self.assertRaisesRegex(ValueError, 'campaign disabled'):
            self.create()
        self.assertFalse(self.path.exists())

    def test_seal_cannot_replace_existing_or_active_latch(self):
        self.create()
        original = self.path.read_bytes()
        with self.assertRaises(Sim3Error):
            self.create()
        self.assertEqual(self.path.read_bytes(), original)
        with open_once(self.path):
            with self.assertRaises(BlockingIOError):
                self.create()


if __name__ == '__main__':
    unittest.main()
