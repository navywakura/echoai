"""Regression for single ingestion and independently varied school factors."""
import copy
import unittest
from unittest.mock import patch

from echoai.nexus0.transfer3 import policy
from echoai.nexus0.transfer3.school_v3 import Student, reward, episode, VARIANTS
from echoai.nexus0.transfer3.rehearsal_v2 import Space, episode as old_episode
from echoai.nexus0.transfer3.rehearsal_v3 import compare, audit


class TransferV3Tests(unittest.TestCase):
    def student(self, **kwargs):
        world = Space(20264401)
        return world, Student(policy.restore(policy.scratch()).snapshot(), world.goal, **kwargs)

    def test_same_capture_has_no_second_evidence_or_visit(self):
        world, agent = self.student()
        frame = world.scan()
        agent.update(frame)
        visits = dict(agent.visits)
        records = {p: copy.deepcopy(m.records) for p,m in agent.cells.items()}
        fingerprint = agent.model.fingerprint()
        agent.update(copy.deepcopy(frame))
        self.assertEqual(agent.visits, visits)
        self.assertEqual({p:m.records for p,m in agent.cells.items()}, records)
        self.assertEqual(agent.model.fingerprint(), fingerprint)
        self.assertEqual(agent.ingestions, 1)

    def test_update_then_decide_does_not_reingest(self):
        world, agent = self.student()
        frame = world.scan()
        agent.update(frame)
        agent.decide(frame)
        self.assertEqual(sum(agent.visits.values()), 1)

    def test_new_capture_same_position_counts(self):
        world, agent = self.student()
        frame = world.scan()
        agent.update(frame)
        frame = dict(frame, now_ns=frame['now_ns']+1)
        agent.update(frame)
        self.assertEqual(agent.ingestions, 2)
        self.assertEqual(sum(agent.visits.values()), 2)

    def test_changed_duplicate_and_stale_are_rejected_without_mutation(self):
        world, agent = self.student()
        frame = dict(world.scan(), now_ns=100)
        agent.update(frame)
        for changed in (dict(frame, energy=200), dict(frame, now_ns=99)):
            with self.assertRaises(ValueError):
                agent.update(changed)
        self.assertEqual(agent.ingestions, 1)
        self.assertEqual(sum(agent.visits.values()), 1)

    def test_correction_does_not_change_fresh_frame_decisions_without_learning(self):
        from echoai.nexus0.compose1_v3.controller import Composer
        world, student = self.student()
        original = Composer(policy.restore(policy.scratch()).snapshot(), world.goal)
        for _ in range(20):
            frame = world.scan()
            a, b = student.decide(frame), original.decide(frame)
            self.assertEqual(a, b)
            if a['status'] not in ('moving', 'returning'):
                break
            world.step(bytes.fromhex(a['wsp'])[13])

    def test_old_bug_and_fixed_whole_episode(self):
        # V2's historical episode is retained; new counts cover the final observation.
        row, payload = episode(policy.scratch(), 20264401, 'corrected', {})
        self.assertEqual(row['ingestions'], row['moves']+1)
        self.assertEqual(row['visit_count'], row['unique_captures'])
        self.assertEqual(len([r for r in row['rows'] if 'learning' in r]), row['moves'])
        self.assertEqual(row['collisions'], 0)
        self.assertEqual(row['reserve_violations'], 0)
        self.assertTrue(payload['q'])

    def test_reward_changes_only_distance_term(self):
        for before, after, goal, observed in (((0,0,0),(-1,0,0),(4,0,0),False),
                                               ((0,0,0),(1,0,0),(1,0,0),True)):
            a = reward('progress',before,after,goal,observed)
            b = reward('step_and_arrival',before,after,goal,observed)
            from echoai.nexus0.compose1.controller import distance
            self.assertEqual(a-b, 8*(distance(before,goal)-distance(after,goal)))
        self.assertEqual(reward('step_and_arrival',(0,0,0),(1,0,0),(1,0,0),False), -1)
        self.assertEqual(reward('step_and_arrival',(0,0,0),(1,0,0),(1,0,0),True), 31)

    def test_variants_change_one_factor(self):
        base = VARIANTS['corrected']
        self.assertEqual([k for k in base if base[k] != VARIANTS['reward_only'][k]], ['reward'])
        self.assertEqual([k for k in base if base[k] != VARIANTS['coverage_only'][k]], ['coverage'])

    def test_coverage_chooses_least_sampled_admissible_not_oracle(self):
        _, agent = self.student(coverage=True)
        agent.pos=(0,0,0);agent.energy=240;agent.turns=4
        feature = b'x'*16
        agent.counts[feature.hex()] = [10, 0, 3, 2]
        with patch.object(agent, 'feature', return_value=feature), \
             patch.object(agent, 'free', side_effect=lambda p: p != (-1,0,0)), \
             patch.object(agent, 'route_home', return_value=[1]):
            path, _ = agent.search((4,0,0))
        self.assertEqual(path, [3])  # unseen action 1 is blocked

    def test_coverage_never_proposes_when_reserve_is_insufficient(self):
        from echoai.nexus0.compose1_v3.controller import Composer
        _, agent = self.student(coverage=True)
        agent.pos=(0,0,0);agent.energy=10;agent.turns=4
        with patch.object(agent, 'feature', return_value=b'x'*16), \
             patch.object(agent, 'free', return_value=True), \
             patch.object(agent, 'route_home', return_value=[0]), \
             patch.object(Composer, 'search', return_value=([],0)):
            self.assertEqual(agent.search((4,0,0)), ([],0))
        self.assertEqual(agent.exploration_proposals, 0)

    def test_counts_are_executions_and_not_exported(self):
        counts = {}
        row, payload = episode(policy.scratch(), 20264401, 'coverage_only', counts)
        self.assertEqual(sum(sum(v) for v in counts.values()), row['moves'])
        self.assertEqual(set(payload), {'schema','q'})
        self.assertEqual(row['collisions'], 0)
        self.assertEqual(row['reserve_violations'], 0)

    def test_comparison_never_rewards_cheap_failure(self):
        a=[dict(seed=1,reached=False,moves=1)]
        b=[dict(seed=1,reached=True,moves=20)]
        self.assertEqual(compare(a,b)['losses'], 1)
        b[0]['reached']=False
        self.assertEqual(compare(a,b)['ties'], 1)
        b[0]['seed']=2
        with self.assertRaises(ValueError):compare(a,b)

    def test_audit_rejects_changed_outcome_and_missing_traces(self):
        expected=dict(isolated=False, totals={'reached': 1}, exams=[1,2], transfer3_green=False)
        with patch('echoai.nexus0.transfer3.rehearsal_v3.run', return_value=expected):
            self.assertTrue(audit(expected)['replay_valid'])
            for changed in (dict(expected, exams=[]), dict(expected, transfer3_green=True),
                            dict(expected, totals={'reached': 2})):
                with self.assertRaises(ValueError):audit(changed)


if __name__ == '__main__':
    unittest.main()
