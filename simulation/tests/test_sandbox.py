"""Written during closure programming; run after implementation is complete.

Observation fixtures below exercise actor contracts only. Every integration test
uses the real pinned MiniGrid dependency; there is no stand-in external simulator.
The stdlib base environment can discover this module without third-party imports.
"""

import copy
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from echo5.budget import Budget
from echo5.interaction import _seal
from echo5.sandbox import (
    MODES, OBS_SCHEMA, PINS, ObservationActor, Session, UnsupportedMission,
    catalogue, parse_mission, validate_observation,
)
from echo5.sandbox_eval import (
    audit_benchmark, case_specs, compute_gates, load_contract, normalize_config,
    normalize_spec, replay_episode, run_benchmark,
)
from echo5.trace import Recorder, verify_journal


def native_available():
    """Metadata only: optional suite discovery must not construct an environment."""
    if platform.python_version() != '3.12.13':
        return False
    try:
        return all(importlib.metadata.version(name) == pin for name, pin in PINS.items())
    except importlib.metadata.PackageNotFoundError:
        return False


def observed(*, direction=0, mission='go to the red ball', cells=()):
    image = [[[0, 0, 0] for _ in range(5)] for _ in range(5)]
    image[2][4] = [1, 0, 0]
    image[2][3] = [1, 0, 0]
    for x, y, cell in cells:
        image[x][y] = list(cell)
    return {'schema': OBS_SCHEMA, 'image': image,
            'direction': direction, 'mission': mission}


class MissionContractTests(unittest.TestCase):
    def test_basic_goal_types(self):
        for text, verb in [('go to the red ball', 'goto'), ('pick up a key', 'pickup'),
                           ('open the blue door', 'open'),
                           ('put the red box next to a blue ball', 'putnext'),
                           ('get to the green goal square', 'reach'),
                           ('use the key to open the door and then get to the goal', 'reach')]:
            with self.subTest(text=text):
                self.assertEqual(parse_mission(text)['steps'][0]['verb'], verb)

    def test_after_reverses_order_and_locations_are_bounded(self):
        mission = parse_mission('open the blue door after you open the red door')
        self.assertEqual([s['target']['color'] for s in mission['steps']], ['red', 'blue'])
        self.assertEqual(mission['order'], 'sequence')
        self.assertEqual(parse_mission('pick up a grey object behind you')['steps'][0]['target'],
                         {'type': 'object', 'color': 'grey', 'location': 'behind'})

    def test_structured_mission_has_same_meaning_as_text(self):
        spec = {'order': 'single', 'steps': [{'verb': 'pickup', 'target':
                {'type': 'ball', 'color': 'red', 'location': 'left'}}]}
        self.assertEqual(parse_mission(spec), parse_mission('pick up the red ball on your left'))

    def test_rejects_unbounded_text_and_code(self):
        for text in ('go anywhere you want', 'open the red ball', 'pick up the blue door',
                     'open the red door then open the blue door then open the grey door',
                     '__import__("os").system("echo bad")', 'x' * 513):
            with self.subTest(text=text[:40]), self.assertRaises((ValueError, UnsupportedMission)):
                parse_mission(text)

    def test_rejects_hidden_keys_and_bool_encoded_ids(self):
        for key in ('seed', 'grid', 'position', 'info', 'reward', 'success'):
            value = observed()
            value[key] = 'privileged'
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_observation(value)
        value = observed()
        value['image'][2][3][0] = True
        with self.assertRaises(ValueError):
            validate_observation(value)

    def test_validated_observation_is_detached(self):
        value = observed()
        result = validate_observation(value)
        result['image'][2][3][0] = 2
        self.assertEqual(value['image'][2][3][0], 1)

    def test_static_catalogue_and_options(self):
        rows = catalogue()
        self.assertEqual(rows[0]['id'], 'door_key')
        self.assertTrue({'id', 'name', 'environment', 'defaults'} <= set(rows[0]))
        for row in rows:
            spec = normalize_spec(row['defaults'])
            self.assertEqual(spec['environment'], row['environment'])
        for spec in ({'environment': 'made-up'}, {'seed': True},
                     {'environment_options': {'grid': []}}, {'mode': 'omniscient'},
                     {'budget': {'actions': 0, 'work': 200}},
                     {'environment_options': {'agent_view_size': 4}}):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                normalize_spec(spec)

    def test_holdouts_are_disjoint_and_include_new_rules(self):
        dev = normalize_config({'split': 'development'})
        confirm = normalize_config({'split': 'confirmation'})
        development, confirmation = case_specs(dev), case_specs(confirm)
        self.assertFalse({c['spec']['seed'] for c in development} &
                         {c['spec']['seed'] for c in confirmation})
        self.assertIn('new_rule_put_next', confirm['families'])
        self.assertIn('new_rule_ordered_doors', confirm['families'])
        self.assertNotIn('new_rule_put_next', dev['families'])
        with self.assertRaises(ValueError):
            normalize_config({'split': 'confirmation', 'seed': dev['seed']})
        with self.assertRaises(ValueError):
            normalize_config({'seed': 999999, 'cases_per_family': 2})

    def test_normalized_configuration_can_be_reused(self):
        config = normalize_config({})
        self.assertEqual(normalize_config(config), config)

    def test_unmeasured_or_empty_rows_cannot_close(self):
        config = normalize_config({})
        gates = compute_gates([], config)
        self.assertFalse(gates['closure'])
        self.assertFalse(gates['complete_paired_cases'])
        self.assertFalse(gates['external_adjudication_and_replay'])
        self.assertGreaterEqual(load_contract()['thresholds']['confirmation_cases_per_family'], 8)


class ObservationActorTests(unittest.TestCase):
    def test_map_is_acquired_from_visible_cells_only(self):
        actor = ObservationActor()
        actor.observe(observed(cells=[(2, 2, [6, 0, 0])]), budget=Budget(10000))
        self.assertEqual(actor.cells[(2, 0)]['cell'], [6, 0, 0])
        self.assertNotIn((0, 0), actor.cells)  # underfoot is overwritten with inventory
        self.assertEqual(len(actor.cells), 2)
        self.assertFalse(hasattr(actor, 'seed'))
        self.assertFalse(hasattr(actor, 'env'))
        self.assertFalse(hasattr(actor, 'grid'))

    def test_turn_retains_observed_map_but_no_memory_forgets(self):
        first = observed(cells=[(2, 2, [6, 0, 0])])
        after = observed(direction=3)
        for mode in ('informative', 'no_memory'):
            actor = ObservationActor(mode=mode)
            b = Budget(10000)
            actor.observe(first, budget=b)
            actor.observe(after, action=0, budget=b)
            self.assertEqual((2, 0) in actor.cells, mode == 'informative')

    def test_goal_directed_move_and_prediction_are_not_observed_facts(self):
        actor, b = ObservationActor(), Budget(100000)
        actor.observe(observed(cells=[(2, 2, [6, 0, 0])]), budget=b)
        evidence = copy.deepcopy(actor.evidence)
        answer = actor.choose(budget=b)
        self.assertEqual(answer['action'], 2)
        self.assertEqual(answer['reason'], 'mission_target')
        self.assertEqual(answer['prediction']['status'], 'hypothesis')
        self.assertEqual(actor.evidence, evidence)
        self.assertGreater(b.counts['planning_expand'], 0)

    def test_object_change_revises_memory_and_replans(self):
        actor, b = ObservationActor(), Budget(100000)
        actor.observe(observed(cells=[(2, 2, [6, 0, 0])]), budget=b)
        actor.choose(budget=b)
        actor.observe(observed(cells=[(2, 2, [1, 0, 0])]), action=6, budget=b)
        actor.choose(budget=b)
        self.assertEqual(actor.cells[(2, 0)]['cell'][0], 1)
        self.assertGreater(actor.conflicts, 0)
        self.assertEqual(actor.replans, 2)
        self.assertTrue(actor.evidence[-1]['map_changes'])

    def test_ambiguous_object_matches_remain_labelled_hypotheses(self):
        actor = ObservationActor()
        actor.observe(observed(cells=[(1, 2, [6, 0, 0]), (3, 2, [6, 0, 0])]), budget=Budget(10000))
        h = actor.hypotheses()['targets'][0]
        self.assertEqual(h['status'], 'multiple_observed_matches')
        self.assertTrue(h['unseen_alternatives_possible'])
        self.assertEqual(len(h['candidate_positions']), 2)

    def test_locked_door_precondition_uses_observed_key(self):
        actor, b = ObservationActor(), Budget(100000)
        obs = observed(mission='get to the goal', cells=[
            (2, 3, [4, 0, 2]), (3, 4, [5, 0, 0]), (2, 1, [8, 1, 0])])
        actor.observe(obs, budget=b)
        choice = actor.choose(budget=b)
        self.assertEqual(choice['reason'], 'observed_key_door_prerequisite')
        self.assertEqual(choice['plan'][-1], 3)

    def test_no_planning_ablation_does_not_search(self):
        actor, b = ObservationActor(mode='no_planning'), Budget(100000)
        actor.observe(observed(cells=[(2, 2, [6, 0, 0])]), budget=b)
        actor.choose(budget=b)
        self.assertNotIn('planning_expand', b.counts)
        self.assertNotIn('information_ray', b.counts)

    def test_door_blocker_is_cleared_before_collecting_key(self):
        actor, b = ObservationActor(), Budget(100000)
        actor.observe(observed(mission='pick up the purple box', cells=[
            (2, 1, [4, 0, 2]), (2, 2, [6, 2, 0]), (3, 4, [5, 0, 0])]), budget=b)
        choice = actor.choose(budget=b)
        self.assertEqual(choice['reason'], 'clear_observed_door_blocker')
        self.assertEqual(choice['plan'][-1], 3)

    def test_relational_target_is_retained_while_reference_is_unseen(self):
        actor, b = ObservationActor(), Budget(100000)
        actor.observe(observed(mission='put the red ball next to the blue box',
                               cells=[(2, 3, [6, 0, 0])]), budget=b)
        actor.observe(observed(mission='put the red ball next to the blue box',
                               cells=[(2, 4, [6, 0, 0])]), action=3, budget=b)
        self.assertNotEqual(actor.choose(budget=b)['action'], 4)

    def test_determinism_is_independent_of_environment_seed(self):
        actors = [ObservationActor(mode='passive') for _ in range(2)]
        for actor in actors:
            actor.observe(observed(), budget=Budget(10000))
        choices = [[a.choose(budget=Budget(10000))['action'] for _ in range(8)] for a in actors]
        self.assertEqual(choices[0], choices[1])


@unittest.skipUnless(native_available(), 'Optional native suite needs pinned .venv-sandbox; no fallback')
class NativeSandboxTests(unittest.TestCase):
    def spec(self, **overrides):
        return dict({'scenario': 'door_key', 'seed': 101,
                     'budget': {'actions': 32, 'work': 200000}}, **overrides)

    def test_native_backend_partial_snapshot_and_public_boundary(self):
        with Session(self.spec()) as session:
            state = session.snapshot()
            self.assertEqual(session._environment.env.spec.id, 'MiniGrid-DoorKey-8x8-v0')
            self.assertEqual(session._environment.env.unwrapped.__class__.__module__,
                             'minigrid.envs.doorkey')
            self.assertTrue({'done', 'step', 'observation', 'objects', 'hypotheses',
                             'prediction', 'action', 'consequence', 'memory', 'budget'} <= set(state))
            self.assertEqual(set(state['observation']), {'schema', 'image', 'direction', 'mission'})
            self.assertTrue(any(cell[0] == 0 for column in state['visible_grid'] for cell in column))
            self.assertEqual(state['agent_position']['relative'], [0, 0])
            self.assertNotIn('seed', state)
            self.assertNotIn('success', state)
            self.assertNotIn('reward', state)
            json.dumps(state, allow_nan=False)

    def test_snapshot_polling_is_detached_and_cost_free(self):
        with Session(self.spec()) as session:
            first = session.snapshot()
            second = session.snapshot()
            self.assertEqual(first, second)
            first['visible_grid'][0][0] = [10, 0, 0]
            first['memory']['cells'].clear()
            self.assertEqual(session.snapshot(), second)

    def test_manual_native_trace_replays_and_tampering_is_rejected(self):
        with Session(self.spec()) as session:
            for action in (0, 1, 0, 0):
                session.step(action)
            result = session.result()
        self.assertTrue(replay_episode(result)['verified'])
        self.assertFalse(result['receipt']['payload']['adjudication']['actor_claim_used'])
        tampered = copy.deepcopy(result)
        tampered['receipt']['payload']['transcript'][0]['after']['direction'] ^= 1
        tampered['receipt'] = _seal(tampered['receipt']['payload'])
        with self.assertRaises(ValueError):
            replay_episode(tampered)

    def test_actor_completion_does_not_adjudicate_success(self):
        with Session(self.spec()) as session:
            session._actor.completed = {0, 1}
            result = session.result()['receipt']['payload']
            self.assertFalse(result['adjudication']['success'])

    def test_actual_step_is_retained_if_learning_budget_exhausts(self):
        with Session(self.spec()) as session:
            session._budget.limit = session._budget.used + 2
            state = session.step(0)
            self.assertTrue(state['done'])
            self.assertEqual(state['status'], 'budget_exhausted')
            self.assertEqual(state['step'], 1)
            receipt = session.result()['receipt']['payload']
            self.assertEqual(receipt['actions'], 1)
            self.assertEqual(receipt['external_calls']['steps'], 1)
            self.assertLessEqual(receipt['work']['used'], receipt['work']['limit'])

    def test_native_dynamic_replay_is_deterministic(self):
        with Session(self.spec(scenario='dynamic')) as session:
            for _ in range(6):
                session.step(0)
            result = session.result()
        self.assertTrue(replay_episode(result)['verified'])

    def test_user_mission_is_bound_to_native_babyai_verifier(self):
        with Session(self.spec(scenario='objects', environment_options={'room_size': 6, 'num_dists': 3})) as first:
            mission = first.snapshot()['observation']['mission']
        # Same generated object, new task verb: an operator-defined problem.
        custom = mission.replace('go to ', 'pick up ', 1)
        with Session(self.spec(scenario='objects', environment_options={'room_size': 6, 'num_dists': 3},
                               mission={'text': custom})) as session:
            self.assertEqual(session.snapshot()['observation']['mission'], custom)
            self.assertEqual(session._environment.env.unwrapped.instrs.__class__.__name__, 'PickupInstr')

    def test_minigrid_does_not_silently_relabel_the_goal(self):
        with self.assertRaises(UnsupportedMission):
            Session(self.spec(mission='pick up the red ball'))

    def test_native_babyai_navigation_is_goal_directed(self):
        spec = {'scenario': 'objects', 'seed': 101,
                'environment_options': {'room_size': 5, 'num_dists': 1},
                'budget': {'actions': 128, 'work': 2000000}}
        with Session(spec) as session:
            while not session.done:
                session.step()
            result = session.result()
        self.assertTrue(result['receipt']['payload']['adjudication']['success'])
        self.assertTrue(replay_episode(result)['success'])

    def test_recorder_contains_factual_per_step_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'thought.jsonl'
            with Recorder(path) as journal:
                with Session(self.spec(), journal=journal) as session:
                    session.step(0)
                    session.step(1)
            self.assertEqual(verify_journal(path)['events'], 3)
            events = [json.loads(line) for line in path.read_text().splitlines()]
            steps = [e for e in events if e['kind'] == 'sandbox_step']
            self.assertEqual(len(steps), 2)
            self.assertEqual(steps[0]['observation']['schema'], OBS_SCHEMA)
            self.assertIn('learning', steps[0]['consequence'])
            self.assertIn('prediction', steps[0])

    def test_equal_budget_paired_report_and_independent_audit(self):
        config = {'families': ['key_door'], 'cases_per_family': 1,
                  'budget': {'actions': 4, 'work': 20000}}
        report = run_benchmark(config)
        self.assertEqual(set(report) & {'schema', 'config', 'rows', 'summary', 'gates'},
                         {'schema', 'config', 'rows', 'summary', 'gates'})
        self.assertEqual({r['condition'] for r in report['rows']}, set(MODES))
        self.assertTrue(report['gates']['equal_action_and_work_limits'])
        self.assertFalse(report['gates']['closure'])
        self.assertTrue(audit_benchmark(report)['verified'])
        corrupt = copy.deepcopy(report)
        corrupt['rows'][0]['costs']['execution_work']['used'] += 1
        with self.assertRaises(ValueError):
            audit_benchmark(corrupt)
        corrupt = copy.deepcopy(report)
        corrupt['rows'].pop()
        with self.assertRaises(ValueError):
            audit_benchmark(corrupt)

    def test_reset_close_and_invalid_manual_actions(self):
        session = Session(self.spec())
        initial = session.snapshot()
        with self.assertRaises(ValueError):
            session.step(True)
        self.assertEqual(session.snapshot(), initial)
        session.step(0)
        self.assertEqual(session.reset(), initial)
        session.close()
        session.close()
        with self.assertRaises(RuntimeError):
            session.step()


if __name__ == '__main__':
    unittest.main()
