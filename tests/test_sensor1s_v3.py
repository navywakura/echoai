"""SENSOR-1S v3: only the LiDAR bias judgement changes.

Every evaluator function except noise/noise_verdict is v1's; the protocol
changes only where declared; on v2's evidence the two worlds that failed
now pass and every mutant is still caught; v1 and v2 locks stay intact.
Reads real evidence; writes nothing into lab.
"""
import ast
import json
import math
import unittest
from pathlib import Path

from echoai.nexus0.sensor1s import campaign as v1, contract, evaluate as ev1
from echoai.nexus0.sensor1s_v2 import campaign as v2
from echoai.nexus0.sensor1s_v3 import campaign as v3, evaluate as ev3
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy

V2LAB = c.ECHOAI/'lab/sensor1s-v2'


def functions(module):
    tree = ast.parse(Path(module.__file__).read_text())
    return {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}


class StructureTests(unittest.TestCase):
    def test_only_the_noise_judgement_changes(self):
        a, b = functions(ev1), functions(ev3)
        self.assertEqual(set(b) - set(a), {'insensitive'})
        self.assertEqual(set(a) - set(b), set())
        changed = {k for k in a if a[k] != b[k]}
        self.assertEqual(changed, {'noise', 'noise_verdict'})
        extra = {k: v for k, v in ev3.LIMITS.items() if ev1.LIMITS.get(k) != v}
        self.assertEqual(set(extra), {'angle_tol_rad', 'sensitivity_max_m'})
        self.assertAlmostEqual(math.degrees(ev3.LIMITS['angle_tol_rad']), 0.5)
        self.assertEqual(ev3.LIMITS['sensitivity_max_m'], 0.010)
        self.assertEqual(ev3.LIMITS['wait_max_ns'], 30_000_000)

    def test_protocol_changes_only_where_declared(self):
        a, b = v3.protocol(), v2.protocol()
        self.assertEqual(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                         ['evaluator', 'limits', 'stages', 'version'])
        self.assertEqual({k for k in a['limits'] if a['limits'][k] != b['limits'].get(k)},
                         {'angle_tol_rad', 'sensitivity_max_m'})
        for stage, seed in (('validation', 20261021), ('bench', 20261022)):
            self.assertEqual(dict(a['stages'][stage], seed=0), dict(b['stages'][stage], seed=0))
            self.assertEqual(a['stages'][stage]['seed'], seed)
        self.assertIs(v3.session, v2.session)
        self.assertIs(v3.evaluate, ev3)

    def test_earlier_locks_are_untouched(self):
        for mod, lab in ((v1, 'lab/sensor1s/lock.json'), (v2, 'lab/sensor1s-v2/lock.json')):
            lock = json.loads((c.ECHOAI/lab).read_text())
            self.assertEqual(mod.inventory(), lock['inventory'], lab)
            self.assertEqual(mod.history()['sha256'], lock['history_sha256'], lab)
            self.assertFalse(any('sensor1s_v3' in f or 'sensor1s-v3' in f for f in mod.inventory()['files']))
        hist = v3.history()['files']
        for need in ('lab/echo3_sensor1s_v2_report.json', 'lab/sensor1s-v2/lock.json',
                     'docs/SENSOR1S-V2-RESULTS.md'):
            self.assertIn(need, hist)


class RetrospectiveTests(unittest.TestCase):
    """v2's own evidence judged by v3's evaluator. Post hoc and declared so:
    this is how the filter was chosen, not a confirmation of it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, pk = legacy.generate_suite_unique()
        cls.byid = {g.package_id: g for g in pk}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def judge(self, stage, rec):
        d = V2LAB/stage
        return ev3.summarize(v3.evaluate_record(rec, self.byid[rec['package_id']], v3.protocol()))

    def test_v2_honest_flights_pass_every_group(self):
        for stage in ('validation', 'bench'):
            r = json.loads((V2LAB/stage/'report.json').read_text())
            for rec in r['records']:
                if rec['arm'] == 'mutant':
                    continue
                s = self.judge(stage, rec)
                self.assertEqual({k: v['status'] for k, v in s.items() if v['status'] != 'pass'}, {},
                                 rec['label'])
                lidar = next(x for x in s['noise']['cases'] if x['name'] == 'lidar')
                if lidar['bias_m'] is not None:
                    self.assertLessEqual(abs(lidar['bias_m']), 0.0075, rec['label'])

    def test_v2_bench_mutants_are_still_caught(self):
        r = json.loads((V2LAB/'bench/report.json').read_text())
        mutants = [rec for rec in r['records'] if rec['arm'] == 'mutant']
        self.assertEqual(len(mutants), 7)
        for rec in mutants:
            s = self.judge('bench', rec)
            target = v1.TARGET[rec['mutant']]
            self.assertTrue(v1.mutant_caught(rec['mutant'], s[target]['cases']), rec['mutant'])
            self.assertEqual(s['execution']['status'], 'pass', rec['mutant'])


if __name__ == '__main__':
    unittest.main()
