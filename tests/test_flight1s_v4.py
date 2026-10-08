"""Acceptance boundaries and reconstruction from real historical evidence.

Fixtures are never written into lab or counted as v4 flight evidence.
"""
import copy
import json
import math
import unittest

from echoai.nexus0.flight1s_v4 import contract as k, campaign as v
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy


def rows(good=12, repeats=2):
    result=[]
    for world in range(12):
        for repeat in range(1,repeats+1):
            for cond in ('nominal','perturbed'):
                # A nominal outlier above the old ceiling is explicitly present.
                value=280 if cond=='nominal' else (550 if world<good else 300)
                result.append(dict(package_id=str(world),repeat=repeat,
                                   condition=cond,disturb_excursion_mm=value))
    return result


class ContractTests(unittest.TestCase):
    def test_distribution_replaces_only_old_nominal_guarantee(self):
        p=k.protocol()
        self.assertEqual(p['configuration'],c.configuration('noaid_7n'))
        self.assertEqual(p['configuration']['recovery']['radius_mm'],200)
        self.assertEqual(p['configuration']['recovery']['hold_ms'],3000)
        self.assertEqual(p['configuration']['recovery']['timeout_ms'],10000)
        result=k.separation(rows(), 'bench',p)
        self.assertEqual(result['status'],'pass')
        self.assertEqual(result['nominal_above_250mm'],24)
        self.assertEqual(result['world_count'],12)
        self.assertAlmostEqual(result['one_sided_sign_p'],1/4096)

    def test_sign_test_boundary(self):
        p=k.protocol()
        self.assertEqual(k.separation(rows(10),'bench',p)['status'],'pass')
        self.assertEqual(k.separation(rows(9),'bench',p)['status'],'fail')
        self.assertAlmostEqual(k.sign_tail(10,12),79/4096)
        self.assertAlmostEqual(k.lower_bound(12,12),.05**(1/12))

    def test_no_pose_pseudoreplication(self):
        p=k.protocol(); p['stages']['bench']['repeats']=10
        a=k.separation(rows(10),'bench',k.protocol())
        b=k.separation(rows(10,repeats=10),'bench',p)
        self.assertEqual(a['one_sided_sign_p'],b['one_sided_sign_p'])
        self.assertEqual(a['positive_world_fraction_lower95'],b['positive_world_fraction_lower95'])

    def test_missing_duplicate_nonfinite_pairs_fail(self):
        for change in ('missing','duplicate','nan','inf'):
            r=rows()
            if change=='missing': r.pop()
            elif change=='duplicate': r.append(r[0])
            else: r[0]['disturb_excursion_mm']=float(change)
            self.assertEqual(k.separation(r,'bench',k.protocol())['status'],'fail')

    def test_ties_do_not_count_positive(self):
        r=rows()
        for m in r:
            if m['condition']=='perturbed': m['disturb_excursion_mm']=330
        result=k.separation(r,'bench',k.protocol())
        self.assertEqual(result['positive_worlds'],0)
        self.assertEqual(result['status'],'fail')

    def test_large_shared_drift_is_not_safe_because_arms_separate(self):
        self.assertEqual(k.separation(rows(),'bench',k.protocol())['status'],'pass')
        self.assertFalse(k.displacement({'samples':[[0,0,0],[1,1_000_001,0]]})['ok'])
        self.assertTrue(k.displacement({'samples':[[0,100,200],[1,1000100,200]]})['ok'])
        self.assertFalse(k.displacement({'samples':[]})['ok'])

    def test_protocol_cannot_relax_recovery_or_change_candidate(self):
        for change in ('recovery','candidate','denominator'):
            p=k.protocol()
            if change=='recovery':p['configuration']['recovery']['radius_mm']=500
            elif change=='candidate':p['configuration']=c.configuration('gpsfix_7n')
            else:p['stages']['bench']['repeats']=1
            with self.assertRaises(ValueError):k.validate(p)

    def test_historical_inventories_do_not_include_v4(self):
        self.assertFalse(any('flight1s_v4' in name for name in c.inventory()['files']))

    def test_real_trace_reconstruction_and_rehashed_measurement_mutant(self):
        tmp,packages=legacy.generate_suite_unique()
        try:
            g=packages[0]
            old=c.ECHOAI/'lab/flight1s-v3/validation-noaid_7n-r2/metrics'
            lock={'protocol':k.protocol()}
            for prefix in ('nominal','perturbed','negative'):
                label=(f'{prefix}-{g.package_id}-r1' if prefix!='negative'
                       else f'negative-{g.package_id}')
                m=json.loads((old/(label+'.json')).read_text())
                meta={name:m[name] for name in ('label','condition','trace')}
                findings=[]
                check=lambda name,ok: findings.append(name) if not ok else None
                v.reconstruct(m,g,meta,lock,check)
                self.assertEqual(findings,[],prefix)
                mutant=copy.deepcopy(m);mutant['disturb_excursion_mm']+=100
                v.reconstruct(mutant,g,meta,lock,check)
                self.assertIn('measurements/'+label,findings)
        finally:tmp.cleanup()


if __name__=='__main__':unittest.main()
