"""DYNAMIC-1: what moves, and where it will be in half a second.

Consumer: on synthetic scans, a wall that closes in is called moving and its
predicted displacement matches what it is doing; a still wall is left alone,
and the records are integers.
Structure: the runner, channel, session and consumer differ from their sources
only where declared; the protocol validates; earlier locks stay intact.
Truth: the mover's published poses interpolate.
Reads real evidence; writes nothing into lab.
"""
import difflib
import json
import math
import unittest
from pathlib import Path

from echoai.nexus0.flight1s.v3 import campaign as c
from echoai.nexus0.ground1_v2 import campaign as g2
from echoai.nexus0.sensor1s_v3 import campaign as v3
from echoai.nexus0.pattern1r import session as ps
from echoai.nexus0.dynamic1 import campaign as d, contract as d1, evaluate as ev, session as ds

G = ev.G
DEV = c.ECHOAI/'lab/dynamic1/dev'


def code(path):
    return Path(path).read_text().split('"""', 2)[2].splitlines()


def changed(a, b):
    return [x for x in difflib.unified_diff(code(a), code(b), n=0, lineterm='')
            if x[:1] in '+-' and not x.startswith(('+++', '---'))]


def wall_scan(distance_m, half_width_deg=12):
    """A flat wall straight ahead, at this distance."""
    out = []
    for i in range(len(G.COS)):
        a = math.radians(-180 + i)
        out.append(distance_m / math.cos(a) if abs(math.degrees(a)) < half_width_deg else float('inf'))
    return out


class ConsumerTests(unittest.TestCase):
    def feed(self, distances, mutant=''):
        g = G.Ground(mutant)
        for k, dist in enumerate(distances):
            g.record('lidar', k * 100_000_000, 'ok', 0, True, wall_scan(dist))
        return g.motion

    def test_a_still_wall_is_left_alone(self):
        motion = self.feed([5.0] * 10)
        self.assertTrue(motion)
        self.assertEqual({r[3] for r in motion}, {0})
        for r in motion:
            self.assertTrue(all(isinstance(v, int) for v in r))

    def test_a_closing_wall_is_called_moving(self):
        # 0.5 m/s towards the body, one scan every 100 ms
        motion = self.feed([5.0 - 0.05*k for k in range(10)])
        self.assertEqual(motion[-1][3], 1)
        # the prediction is half a second of that speed: about 250 mm nearer
        moved = motion[-1][4] - motion[-1][1]
        self.assertLess(abs(moved + 250), 80)

    def test_lies_are_lies(self):
        closing = [5.0 - 0.05*k for k in range(10)]
        self.assertEqual({r[3] for r in self.feed(closing, 'no_motion')}, {0})
        self.assertEqual({r[3] for r in self.feed([5.0]*10, 'always_motion')}, {1})
        copy = self.feed(closing, 'copy_current')
        self.assertTrue(all(r[4] == r[1] and r[5] == r[2] for r in copy))
        replay = self.feed(closing, 'replay')
        self.assertTrue(all(a[1:] == b[1:] for a, b in zip(replay, replay[1:])))


class TruthTests(unittest.TestCase):
    def test_positions_interpolate(self):
        steps = [(0, [0, 0, 0]), (1_000_000_000, [1000, 0, 0])]
        self.assertEqual(ev.position_at(steps, 500_000_000)[0], 500)
        self.assertEqual(ev.position_at(steps, -5)[0], 0)
        self.assertEqual(ev.position_at(steps, 10**10)[0], 1000)


class StructureTests(unittest.TestCase):
    def test_runner_and_channel_are_declared_copies(self):
        runner = changed(ps.SURVEY_RUNNER, ds.SURVEY_RUNNER)
        self.assertTrue(any('set_pose' in x or 'move_model' in x for x in runner))
        self.assertTrue(any('mover' in x for x in runner))
        for line in changed(ps.TAP, ds.TAP):
            self.assertIn('flightrunner', line)

    def test_session_is_pattern1rs_with_the_mover(self):
        lines = changed(ps.__file__, ds.__file__)
        self.assertLessEqual(len(lines), 12, lines)
        text = Path(ds.__file__).read_text()
        self.assertIn('flightrunner_mover.py', text)
        self.assertIn('mover=cfg.get', text)
        self.assertIn('dynamic_mutant', text)

    def test_consumer_says_where_what_and_where_next(self):
        for line in changed(ps.CONSUMER, ds.CONSUMER):
            if line[1:].strip().startswith('#'):        # comments explain, they do not act
                continue
            self.assertTrue(any(t in line for t in (
                'motion', 'moving', 'HISTORY', 'MOVE_MM', 'PREDICT', 'hist', 'record', 'px', 'py',
                'sightings', 'signature', 'TRACK_SETTLED', 'best[', 'best =', 'self.tracks',
                'x =', 'y =', 'mutant', 'dt >', 'EMIT_MIN_BEAMS', 'size =', 'sig =')), line)

    def test_protocol_and_lock_scope(self):
        p = d.protocol()
        d.validate(p)
        self.assertEqual(p['slice'], 'DYNAMIC-1')
        self.assertEqual(p['mover']['velocity_mm_s'][1], 0)     # across the face, not along it
        self.assertEqual(p['predict_ms'], 500)
        inv = d.inventory()['files']
        for need in ('nexus0/dynamic1/assets/flightrunner_mover.py', 'nexus0/dynamic1/assets/consumer.py',
                     'nexus0/dynamic1/evaluate.py', 'docs/DYNAMIC1-DESIGN.md', d1.FAMILY_PATH,
                     'tests/test_dynamic1.py', 'nexus0/loop.py'):
            self.assertIn(need, inv)
        hist = d.history()['files']
        self.assertIn('docs/PATTERN1R-RESULTS.md', hist)

    def test_earlier_locks_are_untouched(self):
        for mod, lab in ((g2, 'lab/ground1-v2/lock.json'), (v3, 'lab/sensor1s-v3/lock.json')):
            lock = json.loads((c.ECHOAI/lab).read_text())
            self.assertEqual(mod.inventory(), lock['inventory'], lab)
            self.assertEqual(mod.history()['sha256'], lock['history_sha256'], lab)


class DevTests(unittest.TestCase):
    """The kept dev flights, rejudged from their files."""

    def test_honest_flights_and_every_lie(self):
        import tempfile
        from echoai.nexus0.sim3.generate import generate_suite
        from echoai.nexus0.sim3.pkg import load_protocol
        from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
        flights = sorted(x for x in DEV.iterdir() if x.is_dir() and (x/'sensors.json').exists()
                         and not x.name.startswith('probe'))
        self.assertGreaterEqual(len(flights), 14)
        with tempfile.TemporaryDirectory() as tmp:
            pk = generate_suite(Path(tmp), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                                [(d1.WORLD_SPLIT, i, s) for i, s in zip(d1.WORLD_INDEX, d1.WORLD_SEEDS)],
                                family_path=c.ECHOAI/d1.FAMILY_PATH)
            byid = {r.package_id: r.package for r in pk}
            seen = set()
            for f in flights:
                s = json.loads((f/'sensors.json').read_text())
                t = json.loads((f/'episode.json').read_text())
                P = ev.load_private(c.ECHOAI/s['private'])
                T = ev.load_transcript(c.ECHOAI/s['transcript'])
                out = ev.dynamics(t, ev.rebuild(T, P), byid[s['package_id']], s['consumer'])
                red = {k for k, v in out.items() if not all(x['ok'] for x in v)}
                mutant = s['spec'].get('dynamic_mutant')
                if mutant:
                    seen.add(mutant)
                    if d.TARGET[mutant] in out:
                        self.assertTrue(d.mutant_caught(mutant, out[d.TARGET[mutant]])
                                        or mutant == 'extra_channel', f.name)
                else:
                    self.assertEqual(red, set(), f.name)
            self.assertEqual(seen, set(d1.MUTANTS))

    def test_the_batch_fixed_the_thresholds(self):
        lim = ev.DYNAMIC_LIMITS
        self.assertLessEqual(lim['detect'], 0.873)        # under the worst flight measured
        self.assertGreaterEqual(lim['quiet'], 0.241)
        self.assertGreaterEqual(lim['predict_mm'], 58)     # over the worst honest median
        self.assertLess(lim['predict_mm'], 118)            # under a prediction of stillness


if __name__ == '__main__':
    unittest.main()
