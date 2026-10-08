"""Counterexamples to percentage-only budgets and unjustified viability."""
import copy
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from echoai.nexus0.power1.core import Guard, Model, TTL, RESERVE
from echoai.nexus0.power1.world import calibration, World, episode, audit_episode
from echoai.nexus0.power1.telemetry import battery_sample


def model():
    return Model.fit(calibration()).snapshot()


def frame(energy=150, out=2, home=0, goal_home=2):
    return dict(now_ns=1_000_000_000, battery=dict(capture_ns=1_000_000_000,
                remaining=energy, capacity=1000, unit='sim_u'),
                routes=dict(out=[0]*out, home=[1]*home, goal_home=[1]*goal_home),
                at_home=home == 0, goal_reached=out == 0)


class PowerTests(unittest.TestCase):
    def test_fitted_costs(self):
        data = model()
        self.assertEqual([data['costs'][p]['upper'] for p in ('0', '1', 'land')], [15, 20, 29])
        self.assertTrue(all(v['n'] == 32 for v in data['costs'].values()))

    def test_low_percentage_can_be_viable(self):
        self.assertEqual(Guard(model()).decide(frame())['reason'], 'continue')
        self.assertEqual(Guard(model(), 'fixed').decide(frame())['reason'], 'land_home')

    def test_high_percentage_can_be_infeasible(self):
        f = frame(230, out=12, goal_home=12)
        self.assertEqual(Guard(model()).decide(f)['reason'], 'land_home')
        self.assertEqual(Guard(model(), 'fixed').decide(f)['reason'], 'continue')

    def test_same_battery_different_route(self):
        self.assertEqual(Guard(model()).decide(frame(170, 1, 0, 1))['reason'], 'continue')
        self.assertEqual(Guard(model()).decide(frame(170, 8, 0, 8))['reason'], 'land_home')

    def test_return_cost_cannot_be_omitted(self):
        self.assertEqual(Guard(model()).decide(frame(180, out=1, home=5, goal_home=6))['reason'], 'return')

    def test_landing_cost_cannot_be_omitted(self):
        self.assertEqual(Guard(model()).decide(frame(80, out=1, goal_home=1))['reason'], 'land_home')

    def test_reserve_cannot_be_omitted(self):
        self.assertEqual(Guard(model()).decide(frame(90, out=1, goal_home=1))['reason'], 'land_home')

    def test_margin_cannot_be_omitted(self):
        self.assertEqual(Guard(model()).decide(frame(145, out=3, goal_home=3))['reason'], 'land_home')

    def test_exact_boundary(self):
        self.assertEqual(Guard(model()).decide(frame(139))['reason'], 'continue')
        self.assertEqual(Guard(model()).decide(frame(138))['reason'], 'land_home')

    def test_stale_future_and_extra_fields(self):
        stale, future = frame(), frame()
        stale['battery']['capture_ns'] -= TTL+1
        future['battery']['capture_ns'] += 1
        for f in (dict(frame(), oracle=1), stale, future):
            self.assertEqual(Guard(model()).decide(f)['reason'], 'unknown_evidence')

    def test_bad_scalars(self):
        for key, value in [('remaining', True), ('remaining', -1), ('remaining', 1001),
                           ('capacity', 0), ('capture_ns', 1.0), ('unit', 'joules')]:
            f = frame()
            f['battery'][key] = value
            self.assertEqual(Guard(model()).decide(f)['reason'], 'unknown_evidence')

    def test_unknown_route_or_landing(self):
        f = frame()
        f['routes']['goal_home'] = None
        self.assertEqual(Guard(model()).decide(f)['reason'], 'land_home')
        data = model()
        del data['costs']['land']
        self.assertEqual(Guard(data).decide(frame())['reason'], 'unknown_landing')

    def test_unaffordable_return_lands_locally(self):
        result = Guard(model()).decide(frame(80, 5, 4, 9))
        self.assertEqual(result['reason'], 'land_local')
        self.assertTrue(result['viable'])

    def test_no_false_landing_guarantee(self):
        result = Guard(model()).decide(frame(20, 5, 4, 9))
        self.assertEqual(result['reason'], 'land_local')
        self.assertFalse(result['viable'])

    def test_return_latches(self):
        guard = Guard(model())
        self.assertEqual(guard.decide(frame(210, 8, 4, 12))['reason'], 'return')
        f = frame(200, 1, 3, 4)
        f['now_ns'] += 1_000_000_000
        f['battery']['capture_ns'] = f['now_ns']
        self.assertEqual(guard.decide(f)['reason'], 'return')

    def test_goal_triggers_return(self):
        self.assertEqual(Guard(model()).decide(frame(400, 0, 3, 3))['reason'], 'return')

    def test_no_silent_recharge_or_clock_replay(self):
        for change in ('recharge', 'clock', 'capacity'):
            guard = Guard(model())
            guard.decide(frame())
            f = frame()
            if change != 'clock':
                f['now_ns'] += 1_000_000_000
                f['battery']['capture_ns'] = f['now_ns']
                f['battery']['remaining' if change == 'recharge' else 'capacity'] += 1
            self.assertEqual(guard.decide(f)['reason'], 'battery_discontinuity')

    def test_terminal_does_not_restart(self):
        guard = Guard(model())
        guard.decide(frame(50))
        self.assertEqual(guard.decide(frame(400))['reason'], 'session_closed')

    def test_invalid_routes(self):
        for route in [[2], [True], [0]*65, 'north']:
            f = frame()
            f['routes']['out'] = route
            self.assertEqual(Guard(model()).decide(f)['reason'], 'unknown_evidence')

    def test_no_input_or_model_mutation(self):
        data, f = model(), frame()
        before = copy.deepcopy((data, f))
        guard = Guard(data)
        guard.decide(f)
        self.assertEqual((data, f), before)
        returned = guard.model.snapshot()
        returned['costs']['0']['upper'] = 999
        self.assertEqual(guard.model.snapshot(), data)

    def test_unconfirmed_calibration_rejected(self):
        for key, value in [('confirmed', False), ('before', 0), ('seq', -1), ('unit', 'mC')]:
            rows = calibration()
            rows[0][key] = value
            with self.assertRaises(ValueError):
                Model.fit(rows)

    def test_model_units_do_not_mix(self):
        f = frame()
        f['battery']['unit'] = 'mC'
        self.assertFalse(Guard(model()).decide(f)['viable'])

    def test_world_never_supplies_oracle_fields(self):
        f = World(20263101, 'margin').observe()
        self.assertEqual(set(f), {'now_ns', 'battery', 'routes', 'at_home', 'goal_reached'})

    def test_counterfactual_bank_and_no_death_on_abort(self):
        for condition in ('short_low', 'long_high', 'return_now', 'margin', 'comfortable'):
            full = episode(20263101, condition, 'cost', model())
            self.assertTrue(full['result']['safe'])
            self.assertEqual(full['result']['mission_permission_violations'], 0)
            self.assertEqual(full['result']['reserve_violations'], 0)
            self.assertEqual(full['result']['successful'], full['result']['initial_feasible'])
            self.assertTrue(audit_episode(full, model()))
            self.assertTrue(all(len(bytes.fromhex(r['decision']['wsp'])) == 16 for r in full['trace']))

    def test_corrupt_trace_is_not_self_certifying(self):
        record = episode(20263101, 'comfortable', 'cost', model())
        record['result']['remaining'] += 1
        self.assertFalse(audit_episode(record, model()))

    def test_battery_missing_values_abstain(self):
        for key, value in [('current_a', -1), ('capacity_mah', 0), ('voltage_v', float('nan')),
                           ('remaining_fraction', 1.1), ('stamp_ns', True)]:
            data = dict(stamp_ns=1, remaining_fraction=.5, capacity_mah=1000, current_a=2, voltage_v=16)
            data[key] = value
            self.assertFalse(battery_sample(**data)['known'])

    def test_adapter_charge_units_not_joules(self):
        value = battery_sample(stamp_ns=1, remaining_fraction=.5, capacity_mah=1000, current_a=2, voltage_v=16)
        self.assertEqual(value['battery'], dict(capture_ns=1, remaining=1800000, capacity=3600000, unit='mC'))

    def test_observer_clock_must_not_regress(self):
        guard = Guard(model())
        first = frame()
        first['now_ns'] += 100
        guard.decide(first)
        second = frame()
        second['battery']['capture_ns'] += 1
        second['now_ns'] += 2
        self.assertEqual(guard.decide(second)['reason'], 'battery_discontinuity')

    def test_denominators_and_safety_are_required(self):
        from echoai.nexus0.power1.bench import schedule, statistics
        records = [episode(s, c, p, model()) for s, c, p in schedule('development')]
        self.assertTrue(statistics(records, 'development')['green'])
        self.assertFalse(statistics(records[:-1], 'development')['green'])
        duplicated = copy.deepcopy(records)
        duplicated[-1] = copy.deepcopy(duplicated[0])
        self.assertFalse(statistics(duplicated, 'development')['green'])
        records[0]['result']['reserve_violations'] = 1
        self.assertFalse(statistics(records, 'development')['green'])

    def test_model_and_receipts_are_bound(self):
        from echoai.nexus0.power1 import bench
        with tempfile.TemporaryDirectory(prefix='power1-model-test-') as directory:
            root = Path(directory)
            (root/'calibration.json').write_text(json.dumps(calibration()))
            (root/'model.json').write_text(json.dumps(model()))
            with patch.object(bench, 'ROOT', root):
                self.assertEqual(bench.model(), model())
                wrong = model()
                wrong['costs']['0'] = copy.deepcopy(wrong['costs']['1'])
                (root/'model.json').write_text(json.dumps(wrong))
                with self.assertRaises(ValueError):
                    bench.model()
                (root/'model.json').write_text(json.dumps(model()))
                receipts = calibration()
                receipts[0]['after'] -= 1
                (root/'calibration.json').write_text(json.dumps(receipts))
                with self.assertRaises(ValueError):
                    bench.model()


if __name__ == '__main__':
    unittest.main()
