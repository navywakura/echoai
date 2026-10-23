"""Matched controls: skills, eligibility and observation boundary are shared."""
import copy
import unittest
from unittest.mock import patch
from echo5.budget import Budget
from echo5.sandbox import EXPLORATION_MODES, ObservationActor
from echo5.sandbox_eval import normalize_spec
from test_sandbox import observed, native_available


class ExplorationControlsTests(unittest.TestCase):
    def test_goal_skill_and_cost_identical_when_target_is_visible(self):
        answers = []
        for mode in EXPLORATION_MODES:
            actor, budget = ObservationActor(mode=mode), Budget(100000)
            actor.observe(observed(cells=[(2, 2, [6, 0, 0])]), budget=budget)
            result = actor.choose(budget=budget)
            answers.append((result['action'], result['plan'], result['reason'], budget.used))
        self.assertEqual(len(set((a, tuple(p), r, b) for a,p,r,b in answers)), 1)
        self.assertEqual(answers[0][2], 'mission_target')

    def test_controls_share_candidates_and_charge_enumeration(self):
        candidates, costs = [], []
        for mode in EXPLORATION_MODES:
            actor, budget = ObservationActor(mode=mode), Budget(100000)
            actor.observe(observed(), budget=budget)
            paths = actor._paths(budget)
            candidates.append(actor._frontier_candidates(paths, budget))
            costs.append(copy.deepcopy(budget.counts))
        self.assertEqual(candidates[0], candidates[1])
        self.assertEqual(candidates[0], candidates[2])
        self.assertEqual(costs[0], costs[1])
        self.assertEqual(costs[0], costs[2])
        self.assertGreater(costs[0]['information_ray'], 0)

    def test_selector_is_the_only_mode_dependent_frontier_operation(self):
        # path, predicted unknowns, pose. Equal inputs, different objectives.
        candidates = [((2,), 1, (1, 0, 0)), ((1, 2, 2), 10, (2, 1, 1))]
        info = ObservationActor(mode='frontier_information')
        near = ObservationActor(mode='frontier_nearest')
        self.assertEqual(info._select_frontier(candidates, Budget(1000))[0], (1, 2, 2))
        self.assertEqual(near._select_frontier(candidates, Budget(1000))[0], (2,))
        a = ObservationActor(mode='frontier_random')
        b = ObservationActor(mode='frontier_random')
        self.assertEqual([a._select_frontier(candidates, Budget(1000)) for _ in range(10)],
                         [b._select_frontier(candidates, Budget(1000)) for _ in range(10)])

    def test_all_selectors_keep_a_valid_destination_across_steps(self):
        first = [((2, 2), 3, (2, 0, 0))]
        later = [((2,), 3, (2, 0, 0)), ((1,), 100, (1, 1, 1))]
        for mode in EXPLORATION_MODES:
            actor, budget = ObservationActor(mode=mode), Budget(10000)
            with patch.object(actor, '_frontier_candidates', side_effect=[first, later]):
                self.assertEqual(actor._explore({}, budget), [2, 2])
                self.assertEqual(actor._explore({}, budget), [2])
                self.assertTrue(actor._frontier_trace['continued_target'])
            with patch.object(actor, '_frontier_candidates', return_value=later[1:]):
                self.assertEqual(actor._explore({}, budget), [1])
                self.assertFalse(actor._frontier_trace['continued_target'])

    def test_visited_poses_are_excluded_equally_without_hidden_world(self):
        actor, budget = ObservationActor(mode='frontier_nearest'), Budget(100000)
        actor.observe(observed(), budget=budget)
        paths = actor._paths(budget)
        for x,y,d in paths:
            actor.visits[((x,y),d)] += 1
        self.assertEqual(actor._frontier_candidates(paths, budget), [])
        self.assertIsNone(actor._explore(paths, budget))
        for name in ('seed', 'env', 'grid'):
            self.assertFalse(hasattr(actor, name))

    def test_new_modes_are_opt_in_and_normalized(self):
        from echo5.sandbox import MODES
        self.assertFalse(set(MODES) & set(EXPLORATION_MODES))
        for mode in EXPLORATION_MODES:
            self.assertEqual(normalize_spec({'mode': mode})['mode'], mode)

    @unittest.skipUnless(native_available(), 'requires pinned MiniGrid profile')
    def test_new_modes_run_and_replay_on_the_same_native_world(self):
        from echo5.sandbox import Session
        from echo5.sandbox_eval import replay_episode
        initial = []
        for mode in EXPLORATION_MODES:
            with Session({'scenario': 'objects', 'seed': 173, 'mode': mode,
                          'environment_options': {'room_size': 5, 'num_dists': 3},
                          'budget': {'actions': 12, 'work': 50000}}) as session:
                initial.append(session.snapshot()['observation'])
                while not session.done:
                    session.step()
                receipt = session.result()
            self.assertTrue(replay_episode(receipt)['verified'])
        self.assertEqual(initial[0], initial[1])
        self.assertEqual(initial[0], initial[2])
