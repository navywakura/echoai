import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.calibration import check_probe, calibration_verdict, audit_local


class CalibrationTests(unittest.TestCase):
    def observation(self):
        return {'status':'EXITED','exit_code':0,'stdout':'calibration-ok\n',
                'isolation':{'job_empty':True,'host_usr_mounted':False,'network_disabled':True},
                'task_success':False,'claim_status':'unknown'}

    def test_clean_exit_is_not_enough_for_timeout_or_sandbox(self):
        value=self.observation()
        self.assertTrue(check_probe('isolation',value))
        self.assertFalse(check_probe('timeout',value))
        value['isolation']['host_usr_mounted']=True
        self.assertFalse(check_probe('isolation',value))

    def test_lingering_processes_and_fake_success_never_calibrate(self):
        value=self.observation();value['status']='TIMEOUT';value['isolation']['job_empty']=False
        self.assertFalse(check_probe('timeout',value))
        value=self.observation();value['task_success']=True
        self.assertFalse(check_probe('isolation',value))

    def test_missing_probe_and_duplicate_issue_do_not_pass(self):
        with self.assertRaises(ValueError): calibration_verdict([dict(instance_id='one')],['one','two'])
        with self.assertRaises(ValueError): calibration_verdict([dict(instance_id='one'),dict(instance_id='one')],['one','two'])
        r=calibration_verdict([dict(instance_id='one',valid=False)],['one'])
        self.assertFalse(r['valid'])
        self.assertEqual(r['llm_calls'],0)
        self.assertIsNone(r['swe_resolved'])

    def test_audit_does_not_initialize_missing_authorities(self):
        from pathlib import Path
        import tempfile,json
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            (path/'result.json').write_text(json.dumps({'issues':[{'instance_id':'fake'}]}))
            with self.assertRaises((ValueError,KeyError)): audit_local(path)
            self.assertFalse((path/'fake/session/authority').exists())
