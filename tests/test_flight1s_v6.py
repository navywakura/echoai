"""v6: aggregation identical to v4 when every flight is measured and never
raising; one preregistered pre-treatment relaunch; restarts audited.

Reads real v3/v4/v5 evidence; writes nothing into lab.
"""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from echoai.nexus0.flight1s_v6 import contract as k, campaign as v
from echoai.nexus0.flight1s_v4 import contract as v4
from echoai.nexus0.flight1s_v5 import contract as v5, campaign as v5c
from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy

FAILED = 'nominal-02083ef67737f6d9-r1'
V5 = c.ECHOAI/'lab/flight1s-v5/validation'


def completed(version):
    root = c.ECHOAI/f'lab/flight1s-{version}/validation/completed'
    return [json.loads(p.read_text()) for p in sorted(root.glob('*.json'))]


def trace(path):
    return json.loads(Path(path).read_text())


def episode(t):
    return Episode(**{x: t[x] for x in t if x in Episode.__dataclass_fields__})


class AggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, packages = legacy.generate_suite_unique()
        cls.packages = packages[:4]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_identical_to_v4_when_every_flight_is_measured(self):
        rows = completed('v4')
        self.assertEqual(len(rows), 44)
        self.assertTrue(all(m['ok'] for m in rows))
        p = v4.protocol()
        self.assertEqual(k.verdict(rows, 'validation', p, self.packages),
                         v4.verdict(rows, 'validation', p, self.packages))

    def test_unmeasured_flight_fails_its_case_instead_of_raising(self):
        rows = completed('v5')
        p = v5.protocol()
        with self.assertRaises(KeyError):
            v4.verdict(rows, 'validation', p, self.packages)
        gs = k.verdict(rows, 'validation', p, self.packages)
        rep = gs['repetition']
        self.assertEqual(rep['status'], 'fail')
        self.assertIn(dict(label=FAILED, ok=False, why='missing measurement'), rep['cases'])
        self.assertIn(dict(package_id='02083ef67737f6d9', condition='nominal', ok=False,
                           why='missing repeat'), rep['cases'])
        self.assertFalse(any(x.get('why') == 'aggregator_error'
                             for g in gs.values() for x in g['cases']))
        self.assertEqual(list(gs), list(k.verdict(completed('v4'), 'validation',
                                                   v4.protocol(), self.packages)))

    def test_exception_row_is_counted_and_fails(self):
        rows = completed('v4')
        meta = {x: rows[0][x] for x in ('label', 'condition', 'package_id', 'split', 'repeat',
                                        'order_slot', 'protocol_version', 'lock_sha256',
                                        'protocol_sha256', 'trace')}
        rows[0] = k.failed_row(meta, RuntimeError('podman vanished'))
        gs = k.verdict(rows, 'validation', v4.protocol(), self.packages)
        self.assertEqual(gs['denominator']['cases'][0]['observed'], 44)
        for name in ('episodes', 'hygiene', 'configuration', 'physical_envelope', 'repetition'):
            self.assertEqual(gs[name]['status'], 'fail', name)
        self.assertEqual(v.negative_group([rows[0]])['status'], 'fail')

    def test_raising_aggregator_fails_only_its_group(self):
        rows = completed('v4')
        with mock.patch.object(k, 'separation', side_effect=ZeroDivisionError('boom')):
            gs = k.verdict(rows, 'validation', v4.protocol(), self.packages)
        self.assertEqual(gs['separation']['cases'][0]['why'], 'aggregator_error')
        self.assertEqual(gs['repetition'], v4.verdict(rows, 'validation', v4.protocol(),
                                                      self.packages)['repetition'])


class BootTests(unittest.TestCase):
    def test_protocol_changes_only_the_chain(self):
        p, q = k.protocol(), v5.protocol()
        self.assertEqual({x for x in p if p.get(x) != q.get(x)},
                         {'version', 'boot', 'aggregation', 'stages'})
        self.assertEqual(p['boot'], dict(heartbeat_s=30, restarts=1))
        self.assertEqual(p['configuration'], q['configuration'])
        for stage, seed in (('validation', 20260925), ('bench', 20260926)):
            self.assertEqual(dict(p['stages'][stage], seed=0), dict(q['stages'][stage], seed=0))
            self.assertEqual(p['stages'][stage]['seed'], seed)
        for change in ('restarts', 'heartbeat'):
            bad = k.protocol()
            bad['boot']['restarts' if change == 'restarts' else 'heartbeat_s'] = 3
            with self.assertRaises(ValueError): k.validate(bad)

    def test_hang_criterion_on_real_traces(self):
        self.assertTrue(k.boot_hung(trace(V5/f'episodes/{FAILED}.json')))
        self.assertTrue(k.boot_hung(trace(c.ECHOAI/'lab/flight1s-v3/validation-noaid_7n/'
                                          'episodes/perturbed-02083ef67737f6d9-r2.json')))
        ok = trace(V5/'episodes/perturbed-02083ef67737f6d9-r1.json')
        self.assertFalse(k.boot_hung(ok))
        late = dict(trace(V5/f'episodes/{FAILED}.json'), driver_events=[{'event': 'heartbeat'}])
        self.assertFalse(k.boot_hung(late))

    def test_plan_rule(self):
        cfg = v5.protocol()['configuration']
        self.assertTrue(k.plan_ok(episode(trace(V5/f'episodes/{FAILED}.json')), cfg))
        ok = episode(trace(V5/'episodes/perturbed-02083ef67737f6d9-r1.json'))
        self.assertTrue(k.plan_ok(ok, cfg))
        ok.stage_marks = dict(ok.stage_marks, plan=ok.stage_marks['plan'][:3])
        self.assertFalse(k.plan_ok(ok, cfg))

    def _launch(self, outcomes):
        hung = trace(V5/f'episodes/{FAILED}.json')
        good = trace(V5/'episodes/perturbed-02083ef67737f6d9-r1.json')
        calls = []
        def fake(runtime, package, cfg, *, condition, label, ulog_dir, runner_path, extra_env):
            calls.append(dict(runner=runner_path, env=extra_env))
            t = hung if outcomes[len(calls)-1] == 'hung' else good
            Path(ulog_dir).mkdir(parents=True, exist_ok=True)
            (Path(ulog_dir)/(label+'.ulg')).write_bytes(b'ulog%d' % len(calls))
            ep = episode(dict(t, label=label))
            ep.ulog_sha256 = v.sha256_bytes(b'ulog%d' % len(calls))
            return ep
        with tempfile.TemporaryDirectory(dir=c.ECHOAI) as tmp, \
                mock.patch.object(c.session, 'run_episode', fake):
            root = Path(tmp)
            ep, restarts = v.launch(None, mock.Mock(), v5.protocol()['configuration'], 'nominal',
                                    'x', root, k.protocol()['boot'])
            findings = []
            check = lambda name, ok: findings.append(name) if not ok else None
            v.check_restarts(restarts, 'x', root, k.protocol()['boot'], check)
            files = sorted(p.name for p in (root/'boots').glob('*')) if (root/'boots').exists() else []
            return ep, restarts, calls, findings, files

    def test_hung_boot_is_set_aside_and_relaunched_once(self):
        ep, restarts, calls, findings, files = self._launch(['hung', 'ok'])
        self.assertTrue(ep.ok)
        self.assertEqual(len(calls), 2)
        self.assertEqual([r['attempt'] for r in restarts], [1])
        self.assertEqual(files, ['x-boot1.json', 'x-boot1.ulg'])
        self.assertEqual(findings, [])
        self.assertTrue(all(x['runner'] == v.RUNNER and x['env']['FLIGHT1S_HEARTBEAT_S'] == '30'
                            for x in calls))

    def test_second_hang_is_final_and_healthy_boot_is_untouched(self):
        ep, restarts, calls, _, _ = self._launch(['hung', 'hung', 'ok'])
        self.assertEqual(len(calls), 2)
        self.assertTrue(k.boot_hung(ep.trace()))
        self.assertEqual(len(restarts), 1)
        ep, restarts, calls, _, files = self._launch(['ok'])
        self.assertEqual((len(calls), restarts, files), (1, [], []))

    def test_forged_restart_is_caught(self):
        good = trace(V5/'episodes/perturbed-02083ef67737f6d9-r1.json')
        with tempfile.TemporaryDirectory(dir=c.ECHOAI) as tmp:
            root = Path(tmp); (root/'boots').mkdir()
            path = root/'boots'/'x-boot1.json'
            v.dump_report(path, dict(good, label='x'))
            record = dict(attempt=1, trace=v.relative(path), trace_sha256=v.sha256_bytes(path.read_bytes()),
                          ulog=None, ulog_sha256=good['ulog_sha256'], cause=good['cause'])
            findings = []
            v.check_restarts([record], 'x', root, k.protocol()['boot'],
                             lambda name, ok: findings.append(name) if not ok else None)
        self.assertIn('boot_restart/x-boot1', findings)

    def test_runner_is_v5_plus_heartbeat_deadline(self):
        a, b = v5c.RUNNER.read_text(), v.RUNNER.read_text()
        allowed = lambda text: next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(text))
                                    if isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == 'ALLOWED')
        self.assertEqual(allowed(a), allowed(b))
        self.assertIn("min(timeout_s, HEARTBEAT_S)", b)
        self.assertNotIn('HEARTBEAT_S', a)

    def test_inventories_and_history(self):
        from echoai.nexus0.flight1s_v4 import campaign as v4c
        for inv in (c.inventory(), v4c.inventory(), v5c.inventory()):
            self.assertFalse(any('flight1s_v6' in f or 'flight1s-v6' in f for f in inv['files']))
        lock = json.loads((c.ECHOAI/'lab/flight1s-v5/lock.json').read_text())
        self.assertEqual(v5c.inventory(), lock['inventory'])
        files = v.inventory()['files']
        for need in ('nexus0/flight1s_v6/campaign.py', 'nexus0/flight1s_v6/contract.py',
                     'nexus0/flight1s_v6/assets/flightrunner_configured.py',
                     'docs/flight1s-v6/DESIGN.md', 'tests/test_flight1s_v6.py',
                     'nexus0/flight1s_v5/container/Containerfile'):
            self.assertIn(need, files)
        hist = v.history()['files']
        for need in ('lab/echo3_flight1s_v5_report.json', 'lab/flight1s-v5-run.log',
                     'lab/flight1s-v5/lock.json', 'docs/FLIGHT1S-V5-RESULTS.md'):
            self.assertIn(need, hist)
        self.assertFalse(any('v6' in f.lower() for f in hist))


if __name__ == '__main__':
    unittest.main()
