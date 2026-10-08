"""v3 tests: same acceptance bands, history intact, fail-closed certificate."""
import copy
import json
import unittest
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s.v2 import runtime as rt2
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as cert
from echoai.nexus0.sim3.canon import report_sha256


def fixture():
    """Structural fixture only, never flight evidence."""
    p=c.configuration('delay')
    lock={'configuration':p,'configuration_sha256':report_sha256(p)}
    lock['sha256']=report_sha256(lock)
    assignments=[{'package_id':str(i)} for i in range(12)]
    rows=[];order=c.condition_order(20260915,24)
    for i,g in enumerate(assignments):
        for repeat in (1,2):
            slot=i*2+repeat-1
            for cond in order[2*slot:2*slot+2]:
                rows.append(dict(label=f'{i}-{repeat}-{cond}',package_id=str(i),repeat=repeat,
                    condition=cond,order_slot=slot,lock_sha256=lock['sha256'],
                    protocol_sha256=lock['configuration_sha256']))
    r=dict(lock=lock,episodes=rows,assignment=assignments,protocol_version=3,
        agent_in_gazebo=False,cortex_calls=0,wsp_writes=0,hardware_status='not_available',
        groups={k:{'status':'pass','cases':[{'ok':True}]} for k in cert.GROUPS},
        group_status={k:'pass' for k in cert.GROUPS},flight1s_green=True)
    r['sha256']=report_sha256(r)
    return r


class TestConfiguration(unittest.TestCase):
    def test_every_candidate_keeps_acceptance(self):
        base=c.protocol.load().data
        for candidate in c.CANDIDATES:
            p=c.configuration(candidate)
            for key in ('challenge','recovery','hover_bands','tolerances'):
                self.assertEqual(p[key],base[key])
            self.assertEqual(p['stimulus']['min_impulse_ratio_ppk'],500)
            self.assertEqual(p['stimulus']['max_impulse_ratio_ppk'],1500)
            self.assertEqual(p['stimulus']['commanded_impulse_mn_s'],
                             c.protocol.commanded_impulse_mn_s(p['disturbance']['force_mn']))
            self.assertTrue(c.validate_configuration(p))
            self.assertEqual(len(c.report_sha256(p)),64)

    def test_cannot_relax_nominal_to_make_it_green(self):
        p=c.configuration('delay');p['challenge']['exit_margin_mm']=100
        with self.assertRaises(ValueError): c.validate_configuration(p)

    def test_cannot_extend_recovery(self):
        p=c.configuration('delay');p['stages']['recover_ms']=13000
        with self.assertRaises(ValueError): c.validate_configuration(p)

    def test_cannot_add_sensor_or_privileged_parameter(self):
        p=c.configuration('delay');p['px4_parameters']['SIM_GPS_USED']=50
        with self.assertRaises(ValueError): c.validate_configuration(p)

    def test_v2_inventory_is_unchanged(self):
        lock=rt2.load_lock()
        self.assertEqual(rt2.code_inventory()[1],lock.lock['code']['code_sha256'])
        self.assertTrue(rt2.check_v1_undisturbed()['ok'])

    def test_v2_red_trajectories_still_fail(self):
        labels=['nominal-fbfb2f3b01be4f00-r2','perturbed-e6da9ac91abd450b-r2']
        for label in labels:
            raw=json.loads((c.ECHOAI/'lab/flight1s-v2/episodes'/(label+'.json')).read_text())
            ep=Episode(**{k:v for k,v in raw.items() if k in {f.name for f in fields(Episode)}})
            m=c.evaluate.episode_metrics(ep,c.configuration('delay'))
            key='challenge' if ep.condition=='nominal' else 'recovery_verdict'
            self.assertFalse(m[key]['ok'], label)

    def test_missing_ulog_fails_configuration(self):
        self.assertFalse(c.parameters_observed(Path('/missing-ulg'),[],{'EKF2_GPS_DELAY':0})['ok'])

    def test_readback_disagreement_fails(self):
        class Log:
            initial_parameters={'EKF2_GPS_DELAY':110}
            changed_parameters=[]
        with patch.object(Path,'exists',return_value=True),patch.object(c,'ULog',return_value=Log()):
            result=c.parameters_observed(Path('/fixture'),[dict(event='param_set',name='EKF2_GPS_DELAY',value=0)],{'EKF2_GPS_DELAY':0})
        self.assertFalse(result['ok'])

    def test_structural_positive_and_mutants(self):
        r=fixture()
        self.assertTrue(cert.audit_report(r,files=False)['evidence_valid'])
        self.assertTrue(cert.mutation_test(r)['ok'])

    def test_empty_report_cannot_be_green(self):
        r=fixture();r['episodes']=[]
        r['sha256']=report_sha256({k:v for k,v in r.items() if k!='sha256'})
        self.assertFalse(cert.audit_report(r,files=False)['evidence_valid'])

    def test_failure_cannot_hide_in_passing_group(self):
        r=fixture();r['groups']['recovery']['cases'][0]['ok']=False
        r['sha256']=report_sha256({k:v for k,v in r.items() if k!='sha256'})
        self.assertIn('group_cases/recovery',cert.audit_report(r,files=False)['findings'])


if __name__=='__main__': unittest.main()
