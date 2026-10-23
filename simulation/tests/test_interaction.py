import copy
import json
import tempfile
import unittest
from pathlib import Path

from echo5.budget import Budget, BudgetExceeded
from echo5.interaction import (
    DiscreteWorld, HypothesisAgent, replay_episode, run_benchmark,
    run_episode, validate_observation,
)
from echo5.trace import Recorder, verify_journal


EAST_SOUTH_WEST_NORTH = ((0, 1), (1, 0), (0, -1), (-1, 0))


def world(**kw):
    params = dict(width=5, height=5, walls=(), position=(2, 2),
                  goal=(0, 4), effects=EAST_SOUTH_WEST_NORTH)
    params.update(kw)
    return DiscreteWorld(**params)


def train(agent, env, budget):
    # Hand-specified reversible probes: each effect observed twice, no wall.
    for action in (0, 2, 1, 3, 0, 2, 1, 3):
        before = env.observation()
        after = env.step(action, budget=budget)
        agent.observe(before, action, after, budget=budget)


class InteractionTests(unittest.TestCase):
    def test_disagreement_probes_an_unknown_action(self):
        agent, env, b = HypothesisAgent(), world(), Budget(10000)
        for _ in range(2):
            before = env.observation()
            after = env.step(0, budget=b)
            agent.observe(before, 0, after, budget=b)
        decision = agent.choose(world().observation(), budget=b, explore=True)
        self.assertNotEqual(decision['action'], 0)
        self.assertGreater(decision['disagreement'], 0)
        self.assertEqual(agent.hypotheses[0], ((0, 1),))
        self.assertEqual(len(agent.evidence), 2)

    def test_blocked_actions_do_not_identify_a_unique_effect(self):
        agent, env, b = HypothesisAgent(), world(position=(0, 0),
            effects=((-1, 0), (0, 1), (1, 0), (0, -1))), Budget(10000)
        for _ in range(2):
            before = env.observation()
            agent.observe(before, 0, env.step(0, budget=b), budget=b)
        self.assertEqual(set(agent.hypotheses[0]), {(-1, 0), (0, -1), (0, 0)})
        self.assertEqual(agent.plan(env.observation(), budget=b)['status'], 'abstain')

    def test_backward_plan_transfers_to_new_walls_and_reaches_goal(self):
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        env = world(walls=((1, 2),), goal=(0, 2))
        plan = agent.plan(env.observation(), budget=b)
        self.assertEqual(plan['status'], 'planned')
        self.assertEqual(len(plan['actions']), 4)
        self.assertIn('inferred', plan['edge_sources'])
        for action in plan['actions']:
            env.step(action, budget=b)
        self.assertEqual(env.observation()['position'], [0, 2])
        self.assertGreater(b.counts['graph_prediction'], 0)
        self.assertGreater(b.counts['bfs_expand'], 0)

    def test_plan_depth_is_bounded_and_does_not_write_evidence(self):
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        before = agent.checkpoint()
        result = agent.plan(world().observation(), budget=b, max_depth=1)
        self.assertEqual(result['status'], 'abstain')
        self.assertEqual(agent.evidence, before['payload']['evidence'])

    def test_no_planning_ablation_never_builds_graph(self):
        agent, b = HypothesisAgent(mode='no_planning'), Budget(10000)
        train(agent, world(), b)
        answer = agent.choose(world().observation(), budget=b)
        self.assertIsNotNone(answer['action'])
        self.assertEqual(agent.plan(world().observation(), budget=b)['reason'],
                         'planning_disabled')
        self.assertNotIn('graph_prediction', b.counts)

    def test_contradiction_invalidates_skill_then_replans_from_new_evidence(self):
        changed = ((1, 0), (0, -1), (-1, 0), (0, 1))
        env = world(change_at=8, changed_effects=changed)
        agent, b = HypothesisAgent(), Budget(20000)
        train(agent, env, b)
        old = agent.plan(env.observation(), budget=b)
        self.assertEqual(old['status'], 'planned')
        before = env.observation()
        outcome = agent.observe(before, 0, env.step(0, budget=b), budget=b)
        self.assertTrue(outcome['contradiction'])
        self.assertEqual(agent.epoch, old['epoch'] + 1)
        self.assertIsNone(agent.skill)
        self.assertEqual(agent.plan(env.observation(), budget=b)['status'], 'abstain')
        fresh = world(effects=changed)
        train(agent, fresh, b)
        revised = agent.plan(fresh.observation(), budget=b)
        self.assertEqual(revised['status'], 'planned')
        for action in revised['actions']:
            fresh.step(action, budget=b)
        self.assertEqual(fresh.observation()['position'], [0, 4])
        self.assertEqual(len(agent.evidence), 17)

    def test_out_of_class_transition_is_recorded_but_forces_abstention(self):
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        before = world().observation()
        after = copy.deepcopy(before)
        after['tick'] += 1
        after['position'] = [4, 2]
        outcome = agent.observe(before, 0, after, budget=b)
        self.assertTrue(outcome['out_of_model'])
        self.assertEqual(agent.evidence[-1]['after']['position'], [4, 2])
        decision = agent.choose(after, budget=b)
        self.assertIsNone(decision['action'])
        self.assertEqual(decision['reason'], 'out_of_model')

    def test_public_schema_rejects_hidden_fields_labels_and_malformed_values(self):
        obs = world().observation()
        mutants = []
        for key in ('effects', 'mapping', 'solution', 'case_id', 'split', 'label'):
            mutants.append(dict(obs, **{key: 'secret'}))
        for key, value in [('width', True), ('tick', -1), ('height', 1000000),
                           ('position', [1.0, 2]), ('goal', [8, 8]),
                           ('walls', [[2, 2]]), ('actions', [0, 1, 1, 3])]:
            mutants.append(dict(obs, **{key: value}))
        for mutant in mutants:
            with self.subTest(mutant=mutant), self.assertRaises(ValueError):
                HypothesisAgent().choose(mutant, budget=Budget(10000))
        self.assertEqual(validate_observation(obs), obs)

    def test_world_secrets_and_input_mutation_cannot_change_initial_decision(self):
        a, b = world(), world(effects=tuple(reversed(EAST_SOUTH_WEST_NORTH)))
        self.assertEqual(a.observation(), b.observation())
        left = HypothesisAgent().choose(a.observation(), budget=Budget(10000))
        right = HypothesisAgent().choose(b.observation(), budget=Budget(10000))
        self.assertEqual(left, right)
        public = a.observation()
        public['position'][0] = 4
        self.assertEqual(a.observation()['position'], [2, 2])

    def test_invalid_transition_envelope_cannot_modify_agent(self):
        agent, b = HypothesisAgent(), Budget(10000)
        before = world().observation()
        for field, value in [('tick', 4), ('goal', [1, 1]), ('width', 6)]:
            after = dict(before, tick=1)
            after[field] = value
            with self.assertRaises(ValueError):
                agent.observe(before, 0, after, budget=b)
        for action in (True, -1, 4, '0'):
            with self.assertRaises(ValueError):
                agent.observe(before, action, dict(before, tick=1), budget=b)
        self.assertEqual(agent.evidence, [])

    def test_repeated_or_discontinuous_tick_cannot_inflate_evidence(self):
        agent, env, b = HypothesisAgent(), world(), Budget(10000)
        train(agent, env, b)
        record = agent.evidence[-1]
        checkpoint = agent.checkpoint()
        with self.assertRaises(ValueError):
            agent.observe(record['before'], record['action'], record['after'], budget=b)
        self.assertEqual(agent.checkpoint(), checkpoint)

    def test_first_tick_zero_receipt_cannot_gain_credit_twice(self):
        agent, env, b = HypothesisAgent(), world(), Budget(10000)
        before = env.observation()
        after = env.step(0, budget=b)
        agent.observe(before, 0, after, budget=b)
        checkpoint = agent.checkpoint()
        self.assertEqual(checkpoint['payload']['model']['support'], [1, 0, 0, 0])
        with self.assertRaises(ValueError):
            agent.observe(before, 0, after, budget=b)
        self.assertEqual(agent.checkpoint(), checkpoint)
        self.assertEqual(agent.evidence, [dict(before=before, action=0, after=after)])

    def test_tick_zero_replay_stays_rejected_after_later_evidence_and_restore(self):
        agent, env, b = HypothesisAgent(), world(), Budget(10000)
        train(agent, env, b)
        first = agent.evidence[0]
        restored = HypothesisAgent.restore(agent.checkpoint(), budget=b)
        for actor in (agent, restored):
            checkpoint = actor.checkpoint()
            with self.assertRaises(ValueError):
                actor.observe(first['before'], first['action'], first['after'], budget=b)
            self.assertEqual(actor.checkpoint(), checkpoint)

    def test_distinct_new_world_tick_zero_receipt_is_accepted_and_restored(self):
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        reset = world(goal=(4, 0))
        before = reset.observation()
        after = reset.step(0, budget=b)
        agent.observe(before, 0, after, budget=b)
        self.assertEqual(len(agent.evidence), 9)
        self.assertEqual(agent.checkpoint()['payload']['model']['support'], [3, 2, 2, 2])
        restored = HypothesisAgent.restore(agent.checkpoint(), budget=b)
        self.assertEqual(restored.checkpoint(), agent.checkpoint())

    def test_rehashed_checkpoint_cannot_change_integer_model_fields_to_booleans(self):
        import hashlib
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        checkpoint = agent.checkpoint()
        checkpoint['payload']['model']['epoch'] = False
        raw = json.dumps(checkpoint['payload'], sort_keys=True,
                         separators=(',', ':'), allow_nan=False)
        checkpoint['sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaises(ValueError):
            HypothesisAgent.restore(checkpoint, budget=Budget(10000))

    def test_budget_exhaustion_precedes_world_mutation_and_abstains(self):
        env, agent = world(), HypothesisAgent()
        checkpoint = env.checkpoint()
        with self.assertRaises(BudgetExceeded):
            env.step(0, budget=Budget(0))
        self.assertEqual(env.checkpoint(), checkpoint)
        decision = agent.choose(env.observation(), budget=Budget(0))
        self.assertIsNone(decision['action'])
        self.assertEqual(decision['reason'], 'budget_exhausted')
        before = agent.checkpoint()
        with self.assertRaises(BudgetExceeded):
            agent.observe(env.observation(), 0, env.step(0, budget=Budget(1)),
                          budget=Budget(0))
        self.assertEqual(agent.checkpoint(), before)

    def test_checkpoint_round_trip_replays_evidence_and_future_decisions(self):
        agent, env, b = HypothesisAgent(seed=7), world(), Budget(10000)
        train(agent, env, b)
        raw = json.loads(json.dumps(agent.checkpoint()))
        clone = HypothesisAgent.restore(raw, budget=Budget(10000))
        restored_world = DiscreteWorld.restore(env.checkpoint(), budget=Budget(10000))
        self.assertEqual(clone.hypotheses, agent.hypotheses)
        self.assertEqual(clone.checkpoint(), agent.checkpoint())
        for _ in range(3):
            first = agent.choose(env.observation(), budget=Budget(10000))
            second = clone.choose(restored_world.observation(), budget=Budget(10000))
            self.assertEqual(first, second)
            if first['action'] is None:
                break
            previous = env.observation()
            after = env.step(first['action'], budget=b)
            replayed = restored_world.step(second['action'], budget=b)
            self.assertEqual(after, replayed)
            agent.observe(previous, first['action'], after, budget=b)
            clone.observe(previous, second['action'], replayed, budget=b)

    def test_checkpoint_rejects_tampering_even_with_recomputed_hash(self):
        import hashlib
        agent, b = HypothesisAgent(), Budget(10000)
        train(agent, world(), b)
        checkpoint = agent.checkpoint()
        checkpoint['payload']['evidence'][0]['after']['tick'] = 99
        raw = json.dumps(checkpoint['payload'], sort_keys=True,
                         separators=(',', ':'), allow_nan=False)
        checkpoint['sha256'] = hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaises(ValueError):
            HypothesisAgent.restore(checkpoint, budget=Budget(10000))
        broken = world().checkpoint()
        broken['payload']['effects'][0] = [9, 9]
        with self.assertRaises(ValueError):
            DiscreteWorld.restore(broken, budget=Budget(10000))
        with self.assertRaises(BudgetExceeded):
            HypothesisAgent.restore(agent.checkpoint(), budget=Budget(0))

    def test_episode_exact_replay_rejects_fabricated_observation(self):
        agent, env, b = HypothesisAgent(), world(), Budget(10000)
        train(agent, world(), b)
        initial = env.checkpoint()
        result = run_episode(agent, env, budget=b, action_limit=12)
        checked = replay_episode(initial, result['transcript'], budget=Budget(10000))
        self.assertTrue(checked['success'])
        self.assertEqual(checked['actions'], result['actions'])
        fake = copy.deepcopy(result['transcript'])
        fake[0]['after']['position'] = [4, 4]
        with self.assertRaises(ValueError):
            replay_episode(initial, fake, budget=Budget(10000))

    def test_trace_records_actual_evidence_without_affecting_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'thought.jsonl'
            with Recorder(path) as journal:
                traced = run_episode(HypothesisAgent(journal=journal), world(),
                    budget=Budget(10000), action_limit=12)
            plain = run_episode(HypothesisAgent(), world(), budget=Budget(10000),
                                action_limit=12)
            self.assertEqual(traced, plain)
            self.assertGreater(verify_journal(path)['events'], 0)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            evidence = [r for r in rows if r['kind'] == 'interaction_transition']
            self.assertEqual(len(evidence), traced['actions'])
            self.assertEqual(evidence[0]['after'], traced['transcript'][0]['after'])

    def test_small_fixture_benchmark_pairs_caps_and_charges_all_phases(self):
        # A unit fixture, not confirmation seed 30791 or its 24 cases.
        report = run_benchmark(seed=19, cases=3, budget=10000)
        self.assertEqual(report, run_benchmark(seed=19, cases=3, budget=10000))
        self.assertEqual(len(report['cases']), 3)
        self.assertEqual({r['split'] for r in report['cases']},
                         {'novel_layout', 'novel_goal', 'changed_dynamics'})
        for case in report['cases']:
            self.assertEqual(set(case['arms']), {'passive', 'active', 'no_planning'})
            for result in case['arms'].values():
                self.assertLessEqual(result['actions'], 64)
                self.assertLessEqual(result['work']['used'], 10000)
                self.assertEqual(sum(result['costs'].values()), result['work']['used'])
                self.assertEqual(result['actions'], len(result['transcript']))
                self.assertGreater(result['costs']['acquisition'], 0)
                self.assertGreater(result['costs']['audit'], 0)
                self.assertEqual(result['success'], result['audit']['success'])
                self.assertEqual(result['final_position'], result['audit']['final']['position'])
                self.assertEqual(result['goal'], result['audit']['final']['goal'])
                self.assertEqual(sum(result['actions_by_phase'].values()), result['actions'])
                for phase in ('acquisition', 'evaluation'):
                    rows = [r for r in result['transcript'] if r['phase'] == phase]
                    audit = replay_episode(result['initial_worlds'][phase], rows,
                                           budget=Budget(10000))
                    if phase == 'evaluation':
                        self.assertEqual(audit['success'], result['success'])
        json.dumps(report, allow_nan=False)

    def test_environment_seed_is_not_passed_to_actor_or_public_input(self):
        report = run_benchmark(seed=19, cases=3, budget=10000)
        self.assertEqual(report['config']['policy_seed'], 0)
        expected_first = HypothesisAgent(mode='passive', seed=0).choose(
            world(goal=(4, 4)).observation(), budget=Budget(100), explore=True)
        for case in report['cases']:
            self.assertEqual(case['arms']['passive']['transcript'][0]['decision'],
                             expected_first)
            for result in case['arms'].values():
                self.assertEqual(result['policy_seed'], 0)
                for step in result['transcript']:
                    self.assertNotIn('seed', step['before'])
                    self.assertNotIn('effects', step['before'])

    def test_checkpoint_resume_across_a_dynamics_change_is_exact(self):
        env = world(change_at=8, changed_effects=tuple(reversed(EAST_SOUTH_WEST_NORTH)))
        actor, b = HypothesisAgent(), Budget(10000)
        train(actor, env, b)
        clone = HypothesisAgent.restore(actor.checkpoint(), budget=Budget(10000))
        restored = DiscreteWorld.restore(env.checkpoint(), budget=Budget(10000))
        left = run_episode(actor, env, budget=Budget(10000), action_limit=20)
        right = run_episode(clone, restored, budget=Budget(10000), action_limit=20)
        self.assertEqual(left, right)
        self.assertGreater(actor.epoch, 0)

    def test_empty_or_exhausted_benchmark_never_claims_success(self):
        empty = run_benchmark(seed=19, cases=0, budget=0)
        self.assertEqual(empty['cases'], [])
        report = run_benchmark(seed=19, cases=3, budget=0)
        for case in report['cases']:
            for arm in case['arms'].values():
                self.assertFalse(arm['success'])
                self.assertEqual(arm['actions'], 0)
                self.assertEqual(arm['work']['used'], 0)
        for kw in ({'seed': True}, {'cases': -1}, {'budget': True}):
            with self.assertRaises(ValueError):
                run_benchmark(**kw)


if __name__ == '__main__':
    unittest.main()
