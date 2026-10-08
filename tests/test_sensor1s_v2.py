"""SENSOR-1S v2: only the process boundary and the pipe change.

The adapter logic must be v1's word for word; session and coordinator must
differ from v1 only where declared; v1's lock must stay intact. Real v2
development flights are read, never written.
"""
import ast
import json
import unittest
from pathlib import Path

from echoai.nexus0.sensor1s import campaign as v1, contract, evaluate as ev, session as v1s
from echoai.nexus0.sensor1s_v2 import campaign as v2, session as v2s
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy

V1_RUNNER = v1s.TAP
V2_RUNNER = v2s.TAP
DEV = c.ECHOAI/'lab/sensor1s-v2/dev'


def methods(path, cls):
    tree = ast.parse(Path(path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    return {m.name: ast.dump(m) for m in node.body if isinstance(m, ast.FunctionDef)}


class StructureTests(unittest.TestCase):
    def test_tap_logic_is_v1s(self):
        a, b = methods(V1_RUNNER, 'Tap'), methods(V2_RUNNER, 'Tap')
        for name in ('write', 'callback', 'ingest', 'adapt', 'close'):
            self.assertEqual(a[name], b[name], name)
        src = V2_RUNNER.read_text()
        self.assertIn('F_SETPIPE_SZ, PIPE_BYTES', src)
        self.assertIn("'--channel'", src)
        self.assertNotIn('TapBackend', src)          # nothing of the channel runs in the flight process

    def test_session_is_v1_with_three_references(self):
        a = v1s.__file__ and Path(v1s.__file__).read_text()
        b = Path(v2s.__file__).read_text()
        a_lines, b_lines = a.splitlines(), b.splitlines()
        extra = [x for x in b_lines if x not in a_lines]
        self.assertEqual(sorted(x.strip() for x in extra if x.strip()), sorted([
            '"""SENSOR-1S v2 episode: v1\'s session, copied with three references changed',
            '(runner, consumer, model); the runner now starts the sensor channel in its',
            'own process.', 'One SENSOR-1S episode: the v6 flight with a sensor tap on the private',
            'from echoai.nexus0.sensor1s import model', "CONSUMER = model.HERE/'assets/consumer.py'"]))
        self.assertEqual(v2s.CONSUMER, v1s.CONSUMER)
        self.assertEqual(V2_RUNNER, c.ECHOAI/'nexus0/sensor1s_v2/assets/sensor_runner.py')

    def test_protocol_changes_only_version_seeds_and_channel(self):
        a, b = v2.protocol(), v1.protocol()
        self.assertEqual(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                         ['channel', 'pipe_bytes', 'stages', 'version'])
        self.assertEqual((a['version'], a['channel'], a['pipe_bytes']), (2, 'separate_process', 1 << 20))
        for stage, seed in (('validation', 20261011), ('bench', 20261012)):
            self.assertEqual(dict(a['stages'][stage], seed=0), dict(b['stages'][stage], seed=0))
            self.assertEqual(a['stages'][stage]['seed'], seed)
        self.assertEqual(a['limits']['wait_max_ns'], 30_000_000)
        self.assertIs(v2.evaluate, ev)
        self.assertIs(v2.mutant_caught, v1.mutant_caught)

    def test_v1_lock_and_history_are_untouched(self):
        lock = json.loads((c.ECHOAI/'lab/sensor1s/lock.json').read_text())
        self.assertEqual(v1.inventory(), lock['inventory'])
        self.assertEqual(v1.history()['sha256'], lock['history_sha256'])
        self.assertFalse(any('sensor1s_v2' in f or 'sensor1s-v2' in f for f in v1.inventory()['files']))
        hist = v2.history()['files']
        self.assertIn('lab/echo3_sensor1s_report.json', hist)
        self.assertIn('lab/sensor1s/lock.json', hist)


class EvidenceTests(unittest.TestCase):
    """Development flights under v2: the stall is gone and liars are still caught."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, pk = legacy.generate_suite_unique()
        cls.byid = {g.package_id: g for g in pk}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def evaluate(self, label):
        d = DEV/label
        s = json.loads((d/'sensors.json').read_text())
        P = ev.load_private(d/'private'/(label+'.jsonl'))
        g = ev.episode(json.loads((d/'episode.json').read_text()), P,
                       ev.load_transcript(d/'transcript'/(label+'.jsonl')), s['consumer'],
                       s['forwarder'], self.byid[s['package_id']].package, s['spec'],
                       condition='perturbed', bounds=contract.LATENCY_P99_BOUND_NS)
        return ev.summarize(g), P

    def test_honest_flights_pass_with_short_waits(self):
        labels = sorted(p.name for p in DEV.glob('v2dev*') if (p/'sensors.json').exists())
        self.assertGreaterEqual(len(labels), 2)
        for label in labels:
            summary, P = self.evaluate(label)
            self.assertEqual({k: v['status'] for k, v in summary.items() if v['status'] != 'pass'}, {}, label)
            self.assertIn(dict(k='diag', what='pipe', bytes=1 << 20),
                          [e for e in P['other'] if e['k'] == 'diag'], label)
            waits = [x['wait_max_ns'] for x in summary['latency']['cases']]
            self.assertLessEqual(max(waits), 30_000_000, label)

    def test_mutants_are_still_caught(self):
        for name, target in v1.TARGET.items():
            if not (DEV/f'v2M-{name}'/'sensors.json').exists():
                self.skipTest('v2 development mutants not flown yet')
            summary, _ = self.evaluate(f'v2M-{name}')
            self.assertTrue(v1.mutant_caught(name, summary[target]['cases']), name)
            self.assertEqual(summary['execution']['status'], 'pass', name)


if __name__ == '__main__':
    unittest.main()
