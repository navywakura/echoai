"""v5 changes only the fixed physical configuration; v4 acceptance is inherited.

No flight here. Fixtures are never written into lab.
"""
import ast
import copy
import unittest
from pathlib import Path
from unittest import mock

from echoai.nexus0.flight1s_v5 import contract as k, campaign as v
from echoai.nexus0.flight1s_v4 import contract as v4, campaign as v4c
from echoai.nexus0.flight1s.v3 import campaign as c


class ContractTests(unittest.TestCase):
    def test_only_configuration_and_seeds_differ_from_v4(self):
        p, q = k.protocol(), v4.protocol()
        self.assertEqual({x for x in p if p[x]!=q[x]}, {'version','configuration','stages'})
        for stage in ('validation','bench'):
            a, b = dict(p['stages'][stage]), dict(q['stages'][stage])
            self.assertEqual((a.pop('seed'), b.pop('seed')),
                             ({'validation':20260923,'bench':20260924}[stage],
                              {'validation':20260921,'bench':20260922}[stage]))
            self.assertEqual(a, b)
        self.assertIs(k.verdict, v4.verdict)
        self.assertIs(k.separation, v4.separation)

    def test_configuration_is_the_preregistered_intervention(self):
        cfg, old = k.protocol()['configuration'], c.configuration('noaid_7n')
        self.assertEqual(cfg['px4_parameters'], {
            'EKF2_GPS_DELAY':0, 'EKF2_GPS_P_NOISE':0.2, 'EKF2_GPS_V_NOISE':0.158,
            'MPC_XY_VEL_P_ACC':3.0, 'MPC_XY_VEL_D_ACC':.4, 'MPC_XY_VEL_I_ACC':0})
        self.assertNotIn('EKF2_NOAID_NOISE', cfg['px4_parameters'])
        self.assertEqual(cfg['image'], 'localhost/echoai-flight1s-px4:v1.15.4-gpsaccuracy')
        self.assertEqual(cfg['disturbance'], old['disturbance'])
        self.assertEqual(cfg['stimulus'], old['stimulus'])
        for same in ('recovery','stages','timeouts','body','rates'):
            self.assertEqual(cfg[same], old[same], same)

    def test_protocol_cannot_relax_or_swap(self):
        for change in ('recovery','noise','seed','denominator'):
            p = k.protocol()
            if change=='recovery': p['configuration']['recovery']['radius_mm'] = 500
            elif change=='noise': p['configuration']['px4_parameters']['EKF2_GPS_V_NOISE'] = 0.5
            elif change=='seed': p['stages']['validation']['seed'] = 20260921
            else: p['stages']['bench']['repeats'] = 1
            with self.assertRaises(ValueError): k.validate(p)

    def test_runner_admits_every_parameter(self):
        tree = ast.parse(v.RUNNER.read_text())
        allowed = next(ast.literal_eval(n.value) for n in ast.walk(tree)
                       if isinstance(n, ast.Assign) and getattr(n.targets[0],'id','')=='ALLOWED')
        self.assertLessEqual(set(k.protocol()['configuration']['px4_parameters']), allowed)
        self.assertNotIn('EKF2_GPS_V_NOISE', ast.literal_eval(next(
            n.value for n in ast.walk(ast.parse(c.RUNNER.read_text()))
            if isinstance(n, ast.Assign) and getattr(n.targets[0],'id','')=='ALLOWED')))

    def test_source_patch_is_exactly_two_labels(self):
        text = (v.HERE/'container/patch_source.py').read_text()
        tree = ast.parse(text)
        repl = next(ast.literal_eval(n.value) for n in ast.walk(tree)
                    if isinstance(n, ast.Assign) and getattr(n.targets[0],'id','')=='replacements')
        self.assertEqual(repl, {'sensor_gps.eph = 0.9f;':'sensor_gps.eph = 0.2f;',
                                'sensor_gps.s_variance_m_s = 0.4f;':'sensor_gps.s_variance_m_s = 0.158f;'})
        counts = dict(v.PATCH_FACTS)
        self.assertEqual(counts['generate_wgn() * 0.2'], 2)
        self.assertEqual(counts['noiseGauss3f(0.06f, 0.077f, 0.158f)'], 1)

    def test_flights_and_mutants_use_the_v5_runner(self):
        seen = []
        def fake(*a, **kw):
            seen.append(kw['runner_path']); raise RuntimeError('stop')
        g = mock.Mock()
        with mock.patch.object(c.session, 'run_episode', fake):
            with self.assertRaises(RuntimeError):
                v.fly(mock.Mock(), g, k.protocol()['configuration'], 'nominal', 'x', Path('/nonexistent'))
        self.assertEqual(seen, [v.RUNNER])

    def test_inventories_and_history(self):
        self.assertFalse(any('flight1s_v5' in f for f in c.inventory()['files']))
        self.assertFalse(any('flight1s_v5' in f for f in v4c.inventory()['files']))
        files = v.inventory()['files']
        for need in ('nexus0/flight1s_v5/campaign.py','nexus0/flight1s_v5/assets/flightrunner_configured.py',
                     'nexus0/flight1s_v5/container/patch_source.py','nexus0/flight1s_v5/container/Containerfile',
                     'docs/flight1s-v5/DESIGN.md','tests/test_flight1s_v5.py'):
            self.assertIn(need, files)
        hist = v.history()['files']
        self.assertIn('lab/echo3_flight1s_v4_report.json', hist)
        self.assertFalse(any('v5' in f.lower() for f in hist))


if __name__=='__main__': unittest.main()
