"""GROUND-1 v2: only the channel's sender changes.

The race that turned v1 red is forced deterministically on the host, with
Gazebo's modules stubbed: a message arrives one tick after the sender read
its clock and before it takes the queue lock. SENSOR-1S v2's channel stamps
it 1 ms before its arrival; v2's does not. Besides: the runner and the
session differ only where declared, the protocol only in version, seeds and
channel, v1's evaluator and consumer are imported, earlier locks stay intact,
and the kept v2 dev flights rejudge as recorded. Reads real evidence; writes
nothing into lab.
"""
import difflib
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.sensor1s import contract
from echoai.nexus0.sensor1s_v3 import campaign as v3
from echoai.nexus0.ground1 import campaign as g1, evaluate as ev, session as s1
from echoai.nexus0.ground1_v2 import campaign as g2, session as s2

OLD_RUNNER = c.ECHOAI/'nexus0/sensor1s_v2/assets/sensor_runner.py'
DEV = c.ECHOAI/'lab/ground1-v2/dev'
TICK = 1_000_000


def red(groups):
    return {k for k, v in groups.items() if not (v and all(x['ok'] for x in v))}


def code(path):
    """Lines after the module docstring."""
    return Path(path).read_text().split('"""', 2)[2].splitlines()


def changed(a, b):
    return [x for x in difflib.unified_diff(code(a), code(b), n=0, lineterm='')
            if x[:1] in '+-' and not x.startswith(('+++', '---'))]


def stub_gazebo():
    """Just enough of gz for the runner module to import on the host."""
    names = ('gz', 'gz.math7', 'gz.msgs10', 'gz.msgs10.clock_pb2', 'gz.msgs10.image_pb2',
             'gz.msgs10.imu_pb2', 'gz.msgs10.laserscan_pb2', 'gz.msgs10.pose_v_pb2', 'gz.transport13')
    for n in names:
        sys.modules.setdefault(n, types.ModuleType(n))
    for mod, attr in (('gz.msgs10.clock_pb2', 'Clock'), ('gz.msgs10.image_pb2', 'Image'),
                      ('gz.msgs10.imu_pb2', 'IMU'), ('gz.msgs10.laserscan_pb2', 'LaserScan'),
                      ('gz.msgs10.pose_v_pb2', 'Pose_V'), ('gz.transport13', 'Node')):
        if not hasattr(sys.modules[mod], attr):
            setattr(sys.modules[mod], attr, type(attr, (), {}))


def load_runner(path, spec_path):
    stub_gazebo()
    spec = importlib.util.spec_from_file_location('runner_%s' % abs(hash(str(path))), path)
    mod = importlib.util.module_from_spec(spec)
    real_open = open
    mod.open = lambda p, *a, **k: real_open(spec_path if p == '/flight/sensor1s.json' else p, *a, **k)
    spec.loader.exec_module(mod)
    return mod


def imu_msg(stamp):
    t = SimpleNamespace(sec=stamp // 1_000_000_000, nsec=stamp % 1_000_000_000)
    return SimpleNamespace(header=SimpleNamespace(stamp=t),
                           linear_acceleration=SimpleNamespace(x=0.0, y=0.0, z=9.8),
                           angular_velocity=SimpleNamespace(x=0.0, y=0.0, z=0.0))


class Backend:
    """A controllable sim clock. When armed, the sender's next clock read lets
    one IMU message arrive a tick later, from another thread, before returning."""

    def __init__(self):
        self.world, self.clock, self.armed, self.blocked = 'w', 10_000_000_000, None, None
        self.callbacks = {}
        self.node = SimpleNamespace(subscribe=self.subscribe)

    def subscribe(self, typ, topic, cb):
        self.callbacks[topic] = cb
        return True

    def snapshot(self):
        return None, self.clock, 0

    def now_ns(self):
        t = self.clock
        if self.armed is not None and threading.current_thread() is self.armed:
            self.armed = None

            def arrive():
                self.clock += TICK
                self.callbacks[self.imu_topic](imu_msg(self.clock - 4 * TICK))
            th = threading.Thread(target=arrive)
            th.start()
            th.join(0.3)          # returns at once unless the queue lock is held
            self.blocked = th.is_alive()   # proof the interleaving happened
        return t


def race(runner_path):
    """(delivered_ns - arrive, whether the arriving thread hit the queue lock)
    for the one message forced into the race."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = contract.spec(contract.schedule(1, False))
        spec.update(fifo=str(d/'sensors.fifo'), private_log=str(d/'private.jsonl'))
        (d/'sensor1s.json').write_text(json.dumps(spec))
        os.mkfifo(d/'sensors.fifo')
        runner = load_runner(runner_path, str(d/'sensor1s.json'))
        backend = Backend()
        backend.imu_topic = spec['sources']['imu']['topic'].format(world='w', instance='x')
        def drain():
            with open(d/'sensors.fifo', 'rb') as f:
                f.read()
        drained = threading.Thread(target=drain, daemon=True)
        drained.start()
        tap = runner.Tap(backend, 'x')
        time.sleep(0.05)
        backend.armed = tap.sender
        deadline = time.monotonic() + 3
        while tap.adapter['imu']['seq'] < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        tap.close()
        log = [json.loads(x) for x in (d/'private.jsonl').read_text().splitlines()]
        raw = [e for e in log if e['k'] == 'raw' and e['src'] == 'imu']
        sent = [e for e in log if e['k'] == 'send' and e['src'] == 'imu']
        assert len(raw) == 1 and len(sent) == 1, (raw, sent)
        return sent[0]['header']['delivered_ns'] - raw[0]['arrive'], backend.blocked


class RaceTests(unittest.TestCase):
    def test_v1_channel_stamps_before_arrival(self):
        self.assertEqual(race(OLD_RUNNER), (-TICK, False))

    def test_v2_channel_does_not(self):
        self.assertEqual(race(s2.TAP), (0, True))


class StructureTests(unittest.TestCase):
    def test_runner_differs_only_in_the_sender_clock(self):
        lines = {x[1:].strip() for x in changed(OLD_RUNNER, s2.TAP)}
        self.assertIn('now = self.backend.now_ns()', lines)
        self.assertEqual({x for x in lines if not x.startswith('#')}, {'now = self.backend.now_ns()'})
        self.assertEqual(len(changed(OLD_RUNNER, s2.TAP)), 4)   # moved line + two comments

    def test_session_differs_only_in_its_paths(self):
        for line in changed(s1.__file__, s2.__file__):
            self.assertTrue(line[1:].startswith(('TAP =', 'CONSUMER =')), line)
        self.assertEqual(s2.CONSUMER, s1.CONSUMER)
        self.assertEqual(s2.TAP, c.ECHOAI/'nexus0/ground1_v2/assets/sensor_runner.py')

    def test_protocol_changes_only_where_declared(self):
        a, b = g2.protocol(), g1.protocol()
        self.assertEqual(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                         ['channel_runner', 'sender_clock', 'stages', 'version'])
        for stage, seed in (('validation', 20261111), ('bench', 20261112)):
            self.assertEqual(dict(a['stages'][stage], seed=0), dict(b['stages'][stage], seed=0))
            self.assertEqual(a['stages'][stage]['seed'], seed)
        self.assertIs(g2.evaluate, ev)
        self.assertEqual((g2.MUTANTS, g2.TARGET, g2.TARGET_CASE), (g1.MUTANTS, g1.TARGET, g1.TARGET_CASE))
        g2.validate(a)

    def test_earlier_locks_are_untouched(self):
        for mod, lab in ((g1, 'lab/ground1/lock.json'), (v3, 'lab/sensor1s-v3/lock.json')):
            lock = json.loads((c.ECHOAI/lab).read_text())
            self.assertEqual(mod.inventory(), lock['inventory'], lab)
            self.assertEqual(mod.history()['sha256'], lock['history_sha256'], lab)
            self.assertFalse(any('ground1_v2' in f or 'ground1-v2' in f for f in mod.inventory()['files']), lab)
        hist = g2.history()['files']
        for need in ('lab/ground1/lock.json', 'lab/echo3_ground1_report.json', 'lab/ground1-run.log',
                     'docs/GROUND1-RESULTS.md', 'lab/sensor1s-v3/lock.json'):
            self.assertIn(need, hist)
        inv = g2.inventory()['files']
        for need in ('nexus0/ground1_v2/assets/sensor_runner.py', 'nexus0/ground1/evaluate.py',
                     'nexus0/ground1/assets/consumer.py', 'docs/GROUND1-DESIGN.md', 'docs/GROUND1-V2-DESIGN.md',
                     'nexus0/loop.py', 'core/cam.py', 'tests/test_ground1_v2.py', 'tests/test_ground1.py'):
            self.assertIn(need, inv)


class DevTests(unittest.TestCase):
    """The kept v2 dev flights: rejudged from their files, as recorded."""

    def test_dev_flights(self):
        dirs = sorted(p for p in DEV.iterdir() if p.is_dir())
        self.assertGreaterEqual(len(dirs), 10)
        tmp, pk = legacy.generate_suite_unique()
        byid = {g.package_id: g for g in pk}
        try:
            seen = set()
            for d in dirs:
                s = json.loads((d/'sensors.json').read_text())
                trace = json.loads((d/'episode.json').read_text())
                groups = ev.episode(trace, ev.load_private(c.ECHOAI/s['private']),
                                    ev.load_transcript(c.ECHOAI/s['transcript']), s['consumer'], s['forwarder'],
                                    byid[s['package_id']].package, s['spec'], condition=s['condition'],
                                    bounds=contract.LATENCY_P99_BOUND_NS, cable=s.get('cable'))
                self.assertEqual(json.loads(json.dumps(ev.summarize(groups))),
                                 json.loads((d/'evaluation.json').read_text()), d.name)
                mutant = s['spec'].get('ground_mutant')
                if mutant:
                    seen.add(mutant)
                    self.assertTrue(g2.sound(groups), d.name)
                    self.assertTrue(g2.mutant_caught(mutant, groups[g2.TARGET[mutant]]), d.name)
                else:
                    self.assertEqual(red(groups), set(), d.name)
            self.assertEqual(seen, set(g2.MUTANTS))
        finally:
            tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
