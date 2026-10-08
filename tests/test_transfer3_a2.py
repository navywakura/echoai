"""Plan A2: extended generator, isolation-safe planner, prospective confirmation."""
import unittest
from pathlib import Path

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import confirm_a2, costs_a2, policy, space_a2, transport_a2
from echoai.nexus0.transfer3.planner_a2 import CostPlanner
from echoai.nexus0.transfer3.rehearsal import ROOT
from echoai.nexus0.transfer3.rehearsal_v2 import shape

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


def spent_shapes():
    history = loads_strict(HISTORY.read_bytes())
    v8 = loads_strict((ROOT/'lab/transfer3/rooms-v8.json').read_bytes())
    return [r['shape'] for r in history['school_rooms']+history['exam_rooms']
            + history['excluded_rooms']]+[r['shape'] for r in v8['new_rooms']]


class Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spent = spent_shapes()
        cls.rooms, cls.ledger = space_a2.suite(confirm_a2.SCHOOL_SEED, 12, cls.spent)

    def test_every_room_has_two_walls(self):
        for room in self.rooms:
            self.assertEqual(len(space_a2.Room(room['seed'], self._body()).walls), 2)

    def _body(self):
        return space_a2.Body((4, 4, 4, 4), 4)

    def test_rooms_are_disjoint_from_every_public_shape_spent(self):
        self.assertTrue({r['shape'] for r in self.rooms}.isdisjoint(self.spent))

    def test_rooms_are_disjoint_from_each_other(self):
        shapes = [r['shape'] for r in self.rooms]
        self.assertEqual(len(set(shapes)), len(shapes))

    def test_every_accepted_room_is_feasible(self):
        for room in self.rooms:
            self.assertIsNone(space_a2.feasible(space_a2.Room(room['seed'], self._body())))

    def test_ledger_records_every_attempt_with_a_reason(self):
        for row in self.ledger:
            self.assertIn(row['reason'], ('accepted', 'duplicate', 'unreachable',
                                          'domain_capacity', 'outside_energy_budget'))

    def test_geometry_does_not_depend_on_the_body(self):
        cheap, dear = space_a2.Body((2, 2, 2, 2), 0), space_a2.Body((6, 6, 6, 6), 8)
        seed = self.rooms[0]['seed']
        self.assertEqual(shape(space_a2.Room(seed, cheap)),
                         shape(space_a2.Room(seed, dear)))

    def test_rooms_stay_inside_spatial_capacity(self):
        for room in self.rooms:
            self.assertLessEqual(room['cells'], space_a2.MAX_CELLS)

    def test_turn_is_charged_only_on_a_heading_change(self):
        room = space_a2.Room(self.rooms[0]['seed'], space_a2.Body((4, 4, 4, 4), 5))
        self.assertEqual(room.step(0)['cost'], 4)
        self.assertEqual(room.step(0)['cost'], 4)
        self.assertEqual(room.step(2)['cost'], 9)


class Candidate(unittest.TestCase):
    def test_turn_only_keeps_the_learned_turn_and_the_nominal_base(self):
        learned = dict(costs_a2.nominal(), base=[3, 5, 4, 4], turn=6)
        candidate = costs_a2.turn_only(learned)
        self.assertEqual(candidate['base'], [costs_a2.NOMINAL_BASE]*4)
        self.assertEqual(candidate['turn'], 6)
        costs_a2.validate(candidate)

    def test_turn_only_is_the_nominal_prior_when_no_turn_was_learned(self):
        self.assertEqual(costs_a2.turn_only(costs_a2.nominal()), costs_a2.nominal())

    def test_payload_carries_no_map_or_geometry_channel(self):
        self.assertEqual(set(costs_a2.nominal()), {'schema', 'base', 'turn', 'samples'})
        with self.assertRaises(ValueError):
            costs_a2.validate(dict(costs_a2.nominal(), rooms=[1, 2]))


class Isolation(unittest.TestCase):
    def test_the_agent_module_graph_never_reaches_a_simulator(self):
        """Walks real imports, not prose: a docstring may name what it avoids."""
        import ast
        here = Path(space_a2.__file__).parent
        forbidden = {'space_a2', 'body_a1', 'rehearsal_v2', 'rehearsal', 'screen_a1',
                     'confirm_a2', 'transport_a2'}
        seen, queue = set(), ['planner_a2', 'costs_a2']
        while queue:
            name = queue.pop()
            if name in seen:
                continue
            seen.add(name)
            tree = ast.parse((here/f'{name}.py').read_text())
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.ImportFrom):
                    targets = [(node.module or '').split('.')[-1]]
                    targets += [alias.name for alias in node.names]
                elif isinstance(node, ast.Import):
                    targets = [alias.name.split('.')[-1] for alias in node.names]
                for target in targets:
                    self.assertNotIn(target, forbidden, f'{name} imports {target}')
                    if (here/f'{target}.py').exists():
                        queue.append(target)
        self.assertEqual(seen, {'planner_a2', 'costs_a2'})

    def test_mounted_tree_excludes_every_forbidden_module(self):
        for forbidden in transport_a2.FORBIDDEN:
            self.assertFalse(any(m.endswith(forbidden) for m in transport_a2.MODULES),
                             forbidden)

    def test_mounted_transfer3_modules_are_exactly_the_agent_ones(self):
        mounted = [m for m in transport_a2.MODULES if m.startswith('transfer3/')]
        self.assertEqual(sorted(mounted), ['transfer3/__init__.py',
                                           'transfer3/costs_a2.py',
                                           'transfer3/planner_a2.py'])

    def test_planner_refuses_a_calibration_outside_the_declared_ranges(self):
        model = policy.restore(policy.scratch()).snapshot()
        with self.assertRaises(ValueError):
            CostPlanner(model, (1, 0, 0), dict(costs_a2.nominal(), turn=99))

    def test_frozen_calibration_does_not_move_without_learning(self):
        model = policy.restore(policy.scratch()).snapshot()
        agent = CostPlanner(model, (1, 0, 0), dict(costs_a2.nominal(), turn=5))
        self.assertIsNone(agent.calibration)
        self.assertEqual(agent.frozen(), ([4, 4, 4, 4], 5))


class Protocol(unittest.TestCase):
    def test_alpha_is_not_loosened_relative_to_the_previous_amendment(self):
        from echoai.nexus0.transfer3 import screen_a1_v2
        self.assertEqual(confirm_a2.ALPHA_DENOMINATOR, screen_a1_v2.ALPHA_DENOMINATOR)

    def test_negative_control_has_no_turn_to_learn(self):
        self.assertEqual(confirm_a2.CONDITIONS['negative_control']['turn'], 0)

    def test_protocol_declares_level_two_not_a_campaign(self):
        self.assertFalse(confirm_a2.PROTOCOL['learning_in_exam'])
        self.assertFalse(confirm_a2.PROTOCOL['campaign_ready'])
        self.assertTrue(confirm_a2.PROTOCOL['isolated'])
        self.assertTrue(confirm_a2.PROTOCOL['room_seeds_declared_before_execution'])

    def test_a_gain_under_the_negative_control_invalidates_the_run(self):
        clean = dict(joint_success_energy_saved=0)
        dirty = dict(joint_success_energy_saved=10)
        primary = dict(new_failures=0, joint_success_energy_saved=100,
                       p_one_sided=dict(numerator=1, denominator=10**9))
        ok = dict(collisions=0, reserve_violations=0, false_facts=0, imagined_writes=0,
                  calibrations_unchanged=True, energy=10)
        taught = dict(energy=1)
        nominal = dict(energy=1000)
        self.assertTrue(confirm_a2.judge(primary, clean, taught, nominal, ok)
                        ['plan_a2_confirmation_pass'])
        self.assertFalse(confirm_a2.judge(primary, dirty, taught, nominal, ok)
                         ['plan_a2_confirmation_pass'])

    def test_audit_refuses_a_report_without_a_verdict(self):
        with self.assertRaises(ValueError):
            confirm_a2.audit({'campaigns': {}})


if __name__ == '__main__':
    unittest.main()
