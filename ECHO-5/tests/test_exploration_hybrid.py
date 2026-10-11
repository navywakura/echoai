"""Small observation-contract tests; no scientific campaign is run here."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echo5.budget import Budget, BudgetExceeded
from echo5.exploration_study import (
    audit_benchmark, case_specs, normalize_config, run_benchmark, summarize,
)
from echo5.sandbox import EXPLORATION_MODES, MODES, ObservationActor, Session
from echo5.sandbox_eval import normalize_spec, replay_episode
from echo5.trace import Recorder, verify_journal
from test_sandbox import native_available, observed


HYBRID = 'frontier_hybrid'
FOUR_MODES = ['frontier_information', 'frontier_nearest', 'frontier_random', HYBRID]


def blocked_view(**kwargs):
    # Only supplied partial cells: locked red door ahead, red ball beyond it.
    return observed(cells=[(2, 3, [4, 0, 2]), (2, 2, [6, 0, 0])], **kwargs)


class HybridActorTests(unittest.TestCase):
    def actor(self, observation=None):
        actor, budget = ObservationActor(mode=HYBRID), Budget(100000)
        actor.observe(observed() if observation is None else observation, budget=budget)
        return actor, budget

    def test_opt_in_leaves_historical_defaults_and_costs_unchanged(self):
        self.assertEqual(MODES, ('informative', 'fixed', 'passive', 'no_memory', 'no_planning'))
        self.assertEqual(EXPLORATION_MODES,
                         ('frontier_information', 'frontier_nearest', 'frontier_random'))
        self.assertEqual(normalize_spec({})['mode'], 'informative')
        self.assertEqual(normalize_spec({'mode': HYBRID})['mode'], HYBRID)
        for mode, plan, work in (('frontier_information', [1], 161),
                                 ('frontier_nearest', [1], 161),
                                 ('frontier_random', [2, 0], 155)):
            actor, budget = ObservationActor(mode=mode), Budget(10000)
            actor.observe(observed(), budget=budget)
            self.assertEqual(actor.choose(budget=budget)['plan'], plan)
            self.assertEqual(budget.used, work)

    def test_ordinary_selection_is_nearest_without_information_scoring(self):
        actor, budget = self.actor()
        with patch.object(actor, '_frontier_candidates', side_effect=AssertionError('costly scorer called')):
            choice = actor.choose(budget=budget)
        self.assertEqual(choice['plan'], [1])
        trace = choice['exploration']
        self.assertEqual(trace['phase'], 'nearest')
        self.assertIsNone(trace['trigger'])
        self.assertFalse(trace['information_scored'])
        self.assertIsNone(trace['predicted_unknown_cells'])
        self.assertEqual(trace['relative_target_pose'], [0, 0, 1])
        self.assertNotIn('information_ray', budget.counts)
        self.assertNotIn('information_candidate', budget.counts)
        self.assertGreater(budget.counts['frontier_visibility_probe'], 0)
        self.assertGreater(budget.counts['planning_expand'], 0)

    def test_unrelated_locked_door_is_not_mission_blockage(self):
        actor, budget = self.actor(observed(cells=[(2, 3, [4, 0, 2])]))
        choice = actor.choose(budget=budget)
        self.assertEqual(choice['exploration']['phase'], 'nearest')
        self.assertIsNone(choice['exploration']['trigger'])
        self.assertNotIn('information_ray', budget.counts)

    def test_observed_active_target_without_plan_triggers_information(self):
        actor, budget = self.actor(blocked_view())
        before = copy.deepcopy(actor.evidence)
        choice = actor.choose(budget=budget)
        trace = choice['exploration']
        self.assertEqual(trace['phase'], 'information')
        self.assertEqual(trace['trigger'], 'observed_mission_blockage')
        self.assertEqual(trace['trigger_evidence']['subgoal'], 0)
        self.assertEqual(trace['trigger_evidence']['required_role'], 'target')
        self.assertEqual(trace['trigger_evidence']['positions'], [[2, 0]])
        self.assertEqual(trace['trigger_evidence']['basis'], 'no_plan_on_observed_map')
        self.assertTrue(trace['information_scored'])
        self.assertGreater(budget.counts['information_ray'], 0)
        self.assertEqual(choice['hypotheses']['exploration'], trace)
        self.assertEqual(actor.evidence, before)

    def test_same_goal_and_door_key_skills_take_priority_in_all_arms(self):
        fixtures = [
            (observed(cells=[(2, 2, [6, 0, 0]), (3, 4, [4, 2, 2])]), 'mission_target'),
            (observed(cells=[(2, 3, [4, 0, 1]), (2, 2, [6, 0, 0])]), 'mission_target'),
            (observed(mission='get to the goal', cells=[
                (2, 3, [4, 0, 2]), (3, 4, [5, 0, 0]), (2, 1, [8, 1, 0])]),
             'observed_key_door_prerequisite'),
        ]
        for observation, reason in fixtures:
            answers, memories, planning = [], [], []
            for mode in FOUR_MODES:
                actor, budget = ObservationActor(mode=mode), Budget(100000)
                actor.observe(observation, budget=budget)
                memory = actor.memory_snapshot()
                memory.pop('mode')
                memories.append(memory)
                choice = actor.choose(budget=budget)
                answers.append((choice['action'], choice['plan'], choice['reason']))
                planning.append({k: v for k, v in budget.counts.items()
                                 if not k.startswith('hybrid_')})
                self.assertNotIn('information_ray', budget.counts)
                if mode == HYBRID:
                    self.assertEqual(choice['exploration']['phase'], 'goal')
                    self.assertIsNone(choice['exploration']['trigger'])
            self.assertTrue(all(a == answers[0] for a in answers))
            self.assertTrue(all(m == memories[0] for m in memories))
            self.assertTrue(all(p == planning[0] for p in planning))
            self.assertEqual(answers[0][2], reason)

    def test_sequence_ignores_blocked_future_target(self):
        actor, budget = self.actor(observed(
            mission='go to the blue ball, then go to the red ball',
            cells=[(2, 3, [4, 0, 2]), (2, 2, [6, 0, 0])]))
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['phase'], 'nearest')
        self.assertIsNone(trace['trigger'])

    def test_carried_relational_target_requires_observed_reference_for_blockage(self):
        mission = 'put the red ball next to the blue box'
        actor, budget = self.actor(observed(mission=mission, cells=[
            (2, 4, [6, 0, 0]), (2, 3, [4, 0, 2])]))
        self.assertIsNone(actor.choose(budget=budget)['exploration']['trigger'])
        actor, budget = self.actor(observed(mission=mission, cells=[
            (2, 4, [6, 0, 0]), (2, 3, [4, 0, 2]), (2, 2, [7, 2, 0])]))
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['trigger'], 'observed_mission_blockage')
        self.assertEqual(trace['trigger_evidence']['required_role'], 'reference')

    def test_eight_observed_stagnant_steps_trigger_and_new_evidence_resets(self):
        actor, budget = self.actor()
        for _ in range(7):
            actor.observe(observed(), action=6, budget=budget)
        self.assertIsNone(actor.choose(budget=budget)['exploration']['trigger'])
        actor.observe(observed(), action=6, budget=budget)
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['trigger'], 'observation_stagnation')
        self.assertEqual(trace['trigger_evidence']['stagnant_observations'], 8)
        self.assertEqual(trace['phase'], 'information')
        # Existing target remains valid: triggering does not justify reranking.
        self.assertTrue(trace['continued_target'])
        self.assertFalse(trace['information_scored'])
        actor.observe(observed(cells=[(1, 4, [1, 0, 0])]), action=6, budget=budget)
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['phase'], 'nearest')
        self.assertIsNone(trace['trigger'])

    def test_choose_and_snapshot_reads_do_not_count_as_stagnant_observations(self):
        actor, budget = self.actor()
        for _ in range(12):
            choice = actor.choose(budget=budget)
            actor.hypotheses()
            actor.memory_snapshot()
            self.assertIsNone(choice['exploration']['trigger'])
        self.assertNotIn('information_ray', budget.counts)

    def test_commitment_survives_trigger_and_new_competing_targets(self):
        actor, budget = self.actor()
        first = actor.choose(budget=budget)['exploration']['relative_target_pose']
        actor.observe(blocked_view(), action=6, budget=budget)
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['trigger'], 'observed_mission_blockage')
        self.assertEqual(trace['relative_target_pose'], first)
        self.assertTrue(trace['continued_target'])
        self.assertFalse(trace['information_scored'])
        self.assertNotIn('information_ray', budget.counts)

    def test_information_selection_quota_and_observation_cooldown(self):
        actor, budget = self.actor(blocked_view())
        for _ in range(2):
            trace = actor.choose(budget=budget)['exploration']
            self.assertTrue(trace['information_scored'])
            x, y, direction = trace['relative_target_pose']
            # Planner fixture: the destination has now been visited.
            actor.visits[((x, y), direction)] += 1
        rays = budget.counts['information_ray']
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['phase'], 'nearest')
        self.assertEqual(trace['trigger'], 'observed_mission_blockage')
        self.assertFalse(trace['information_scored'])
        self.assertEqual(budget.counts['information_ray'], rays)
        for _ in range(11):
            actor.observe(blocked_view(), action=6, budget=budget)
        self.assertEqual(actor.choose(budget=budget)['exploration']['phase'], 'nearest')
        actor.observe(blocked_view(), action=6, budget=budget)
        self.assertEqual(actor.choose(budget=budget)['exploration']['phase'], 'information')

    def test_information_phase_expires_after_four_observed_steps(self):
        actor, budget = self.actor(blocked_view())
        actor.choose(budget=budget)
        for _ in range(4):
            actor.observe(blocked_view(), action=6, budget=budget)
        trace = actor.choose(budget=budget)['exploration']
        self.assertEqual(trace['phase'], 'nearest')
        self.assertFalse(trace['information_scored'])
        self.assertTrue(trace['continued_target'])

    def test_unscored_eligibility_matches_historical_ray_predicate(self):
        for observation in (observed(), blocked_view(), observed(cells=[
                (1, 3, [2, 0, 0]), (3, 3, [4, 2, 1]), (2, 2, [1, 0, 0])])):
            actor, budget = self.actor(observation)
            paths = actor._paths(budget)
            unscored = actor._unscored_frontier_candidates(paths, budget)
            scored = actor._frontier_candidates(paths, budget)
            self.assertEqual([(c[0], c[2]) for c in unscored], [(c[0], c[2]) for c in scored])
            self.assertTrue(all(c[1] is None for c in unscored))
            for x, y, d in paths:
                actor.visits[((x, y), d)] += 1
            self.assertEqual(actor._unscored_frontier_candidates(paths, budget), [])

    def test_budget_is_enforced_and_actor_has_no_privileged_inputs(self):
        actor, budget = self.actor(blocked_view())
        before = copy.deepcopy(actor.cells)
        with self.assertRaises(BudgetExceeded):
            actor.choose(budget=Budget(1))
        self.assertEqual(actor.cells, before)
        for name in ('seed', 'env', 'grid', 'reward', 'success'):
            self.assertFalse(hasattr(actor, name))
            malicious = observed()
            malicious[name] = 'privileged'
            with self.assertRaises(ValueError):
                actor.observe(malicious, action=6, budget=budget)

    def test_manual_decision_does_not_repeat_previous_automatic_trigger(self):
        actor, budget = self.actor(blocked_view())
        self.assertEqual(actor.choose(budget=budget)['exploration']['phase'], 'information')
        manual = actor._decision([6], 'manual_public_action')['exploration']
        self.assertEqual(manual['phase'], 'manual')
        self.assertIsNone(manual['trigger'])
        self.assertFalse(manual['information_scored'])

    def test_exhausted_scoring_exports_attempt_instead_of_completed_score(self):
        actor, budget = self.actor(blocked_view())

        class StopOnRay(Budget):
            def consume(self, kind, amount=1):
                if kind == 'information_ray':
                    raise BudgetExceeded('information ray reservation refused')
                super().consume(kind, amount)

        with self.assertRaises(BudgetExceeded):
            actor.choose(budget=StopOnRay(100000))
        trace = actor.hypotheses()['exploration']
        self.assertEqual(trace['phase'], 'information')
        self.assertEqual(trace['trigger'], 'observed_mission_blockage')
        self.assertTrue(trace['information_scoring_attempted'])
        self.assertFalse(trace['information_scored'])


class HybridStudyTests(unittest.TestCase):
    def test_four_arms_keep_pairing_and_original_world_identities(self):
        old = case_specs({})
        self.assertEqual(len(old), 84)
        self.assertEqual(old[0]['id'], 'objects_small:1400000')
        self.assertEqual(old[-1]['id'], 'put_next:1406003')
        expanded = case_specs({'modes': FOUR_MODES})
        self.assertEqual([c for c in expanded if c['spec']['mode'] != HYBRID], old)
        planned = case_specs({'seed': 1440000, 'modes': FOUR_MODES})
        self.assertEqual(len(planned), 112)
        self.assertEqual(len({c['id'] for c in planned}), 28)
        self.assertEqual(planned[-1]['id'], 'put_next:1446003')
        for i in range(0, len(planned), 4):
            specs = [{k: v for k, v in c['spec'].items() if k != 'mode'}
                     for c in planned[i:i + 4]]
            self.assertTrue(all(s == specs[0] for s in specs))
            self.assertIsNone(specs[0]['mission'])
        self.assertEqual(normalize_config({})['modes'], list(EXPLORATION_MODES))

    def test_four_arm_summary_requires_complete_pairs_and_three_comparisons(self):
        config = {'seed': 1440000, 'modes': FOUR_MODES,
                  'cases_per_profile': 1, 'profiles': ['objects_small']}
        rows = [{'id': c['id'], 'profile': c['profile'], 'mode': c['spec']['mode'],
                 'success': False, 'actions': 2, 'work': 100, 'status': 'action_limit'}
                for c in case_specs(config)]
        summary = summarize(rows, config)
        self.assertEqual(list(summary['groups']['all']['arms']), FOUR_MODES)
        self.assertEqual(set(summary['groups']['all']['comparisons']), set(FOUR_MODES[1:]))
        self.assertFalse(summary['promotion'])
        for broken in (rows[:-1], rows + [rows[0]]):
            with self.assertRaises(ValueError):
                summarize(broken, config)
        for modes in ([], [HYBRID], [HYBRID, HYBRID], [HYBRID, 'omniscient'], 'frontier_hybrid',
                      ['frontier_nearest', HYBRID], FOUR_MODES[1:], FOUR_MODES[:2],
                      list(reversed(EXPLORATION_MODES)), [[], *FOUR_MODES[1:]]):
            with self.assertRaises(ValueError):
                normalize_config({'modes': modes})
        reordered = [HYBRID, *EXPLORATION_MODES]
        self.assertEqual(normalize_config({'modes': reordered})['modes'], reordered)

    def test_four_arm_intervals_allow_for_three_planned_comparisons(self):
        config = {'modes': FOUR_MODES}
        rows = [{'id': c['id'], 'profile': c['profile'], 'mode': c['spec']['mode'],
                 'success': False, 'actions': 2, 'work': 100, 'status': 'action_limit'}
                for c in case_specs(config)]
        groups = summarize(rows, config)['groups']
        for comparison in groups['all']['comparisons'].values():
            # 28 paired differences in [-1, 1], family alpha .05 / 3 contrasts.
            low, high = comparison['difference_interval']
            self.assertLess(low, -0.58)
            self.assertGreater(high, 0.58)
            self.assertLess(high, 0.59)


@unittest.skipUnless(native_available(), 'requires pinned MiniGrid profile')
class HybridNativeSmokeTests(unittest.TestCase):
    def test_existing_thought_journal_contains_actual_trigger_phase_and_replays(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'thought.jsonl'
            with Recorder(path) as journal:
                with Session({'scenario': 'door_key', 'seed': 101, 'mode': HYBRID,
                              'budget': {'actions': 9, 'work': 100000}}, journal=journal) as session:
                    for _ in range(8):
                        session.step('done')
                    session.step()
                    episode = session.result()
            self.assertTrue(replay_episode(episode)['verified'])
            self.assertGreater(verify_journal(path)['events'], 0)
            events = [json.loads(line) for line in path.read_text().splitlines()]
            step = [e for e in events if e['kind'] == 'sandbox_step'][-1]
            trace = step['hypotheses']['exploration']
            self.assertEqual(trace['phase'], 'information')
            self.assertEqual(trace['trigger'], 'observation_stagnation')
            self.assertTrue(trace['information_scored'])
            self.assertEqual(trace, episode['receipt']['payload']['transcript'][-1]
                             ['decision']['exploration'])

    def test_run_and_audit_accept_explicit_four_modes_on_one_tiny_world(self):
        report = run_benchmark({'seed': 1480000, 'modes': FOUR_MODES,
                                'profiles': ['objects_small'], 'cases_per_profile': 1,
                                'actions': 1, 'work': 10000})
        self.assertEqual(len(report['rows']), 4)
        initial = [r['episode']['receipt']['payload']['initial_observation'] for r in report['rows']]
        self.assertTrue(all(o == initial[0] for o in initial))
        audit = audit_benchmark(report)
        self.assertTrue(audit['valid'])
        self.assertEqual(audit['episodes_replayed'], 4)
        self.assertFalse(audit['promotion'])


if __name__ == '__main__':
    unittest.main()
