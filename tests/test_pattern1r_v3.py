"""One new estimator covariance; the frozen perception contract stays intact."""
import ast
import json
import math
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from echoai.nexus0.pattern1r_v2 import contract as old, session as old_session
from echoai.nexus0.pattern1r_v3 import contract as ct, session, campaign as cp
from echoai.nexus0.pattern1r_v3.memory import AbstainingPatternMemory
from echoai.nexus0.pattern1 import InvariantPatternMemory


class AmbiguityTests(unittest.TestCase):
    def test_ambiguous_observations_cannot_create_a_mature_phantom(self):
        old_mem=InvariantPatternMemory(min_hits=4)
        new=AbstainingPatternMemory(min_hits=4)
        for mem in (old_mem,new):
            for _ in range(40):mem.observe(0,0);mem.observe(15,0)
        for _ in range(80):
            old_mem.observe(3,0)
            self.assertIsNone(new.observe(3,0))
        self.assertIsNotNone(old_mem.predict(3))
        self.assertIsNone(new.predict(3))
        self.assertEqual(new.size,2)
        self.assertEqual(new.observations,160)
        self.assertEqual(new.dropped,80)
        self.assertEqual(new.prototype[:2],[0,15])
        before=new.snapshot_hash();new.predict(3);self.assertEqual(new.snapshot_hash(),before)

    def test_tie_outside_radius_is_still_novel(self):
        mem=AbstainingPatternMemory()
        mem.observe(0,0);mem.observe(65535,0)
        self.assertEqual(mem.observe(255,0),2)
        self.assertEqual(mem.dropped,0)

    def test_no_tie_preserves_original_learning_and_consequences(self):
        old_mem=InvariantPatternMemory();new=AbstainingPatternMemory()
        for sig,outcome in [(0,16),(15,-16),(1,16),(14,-16)]*40:
            self.assertEqual(new.observe(sig,outcome),old_mem.observe(sig,outcome))
            self.assertEqual(new.snapshot_hash(),old_mem.snapshot_hash())
        with self.assertRaises(ValueError):new.observe(True,0)

    def test_evaluator_changes_only_the_memory_import(self):
        a=cp.previous.HERE/'evaluate.py';b=cp.HERE/'evaluate.py'
        self.assertEqual(b.read_text(),a.read_text().replace(
            'from echoai.nexus0.pattern1 import InvariantPatternMemory',
            'from .memory import AbstainingPatternMemory as InvariantPatternMemory'))


class BarometerTests(unittest.TestCase):
    def test_parameter_readback_decodes_types_without_writing(self):
        import struct,time
        from unittest.mock import Mock
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Driver')
        node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='read_param')
        ns=dict(struct=struct,time=time,mavutil=SimpleNamespace(mavlink=SimpleNamespace(MAV_PARAM_TYPE_INT32=6)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),ns)
        for name,value,ptype in [('EKF2_HGT_REF',1,6),('EKF2_BARO_NOISE',0.01,9)]:
            wire=struct.unpack('<f',struct.pack('<i',value))[0] if ptype==6 else value
            conn=SimpleNamespace(target_system=1,target_component=1,mav=SimpleNamespace(param_request_read_send=Mock()),
                recv_match=Mock(return_value=SimpleNamespace(param_id=name,param_value=wire,param_type=ptype)))
            driver=SimpleNamespace(conn=conn,log=Mock())
            self.assertEqual(ns['read_param'](driver,name,ptype),value)
            conn.mav.param_request_read_send.assert_called_once_with(1,1,name.encode(),-1)
            conn.recv_match.return_value.param_type=0
            with self.assertRaises(RuntimeError):ns['read_param'](driver,name,ptype)

    def test_covariance_comes_from_sensor_with_documented_floor(self):
        b=ct.barometer_uncertainty()
        self.assertEqual(b['pressure_sigma_pa'],0.01)
        self.assertGreater(b['altitude_sigma_m'],0.0008)
        self.assertLess(b['altitude_sigma_m'],0.001)
        self.assertEqual(b['configured_sigma_m'],0.01)
        prior=old.configuration();new=ct.configuration()
        for key in ('candidate','profile'): prior.pop(key);new.pop(key)
        self.assertEqual(new['px4_parameters'].pop('EKF2_BARO_NOISE'),0.01)
        self.assertEqual(prior,new)

    def test_driver_accepts_and_reads_new_covariance(self):
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ConfiguredDriver')
        class Driver:
            def __init__(self):self.events=[]
            def connect(self,timeout):return True
            def read_param(self,name,ptype):
                if ptype!=(6 if name=='EKF2_HGT_REF' else 9):return None
                value=ct.configuration()['px4_parameters'][name]
                self.events.append(dict(name=name,value=value));return value
        ns=dict(Driver=Driver,json=json,math=math,os=os,
                mavutil=SimpleNamespace(mavlink=SimpleNamespace(MAV_PARAM_TYPE_INT32=6,MAV_PARAM_TYPE_REAL32=9)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),ns)
        with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(ct.configuration()['px4_parameters'])):
            driver=ns['ConfiguredDriver']();self.assertTrue(driver.connect(10))
        self.assertEqual(next(x['value'] for x in driver.events if x['name']=='EKF2_BARO_NOISE'),0.01)
        with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(ct.configuration()['px4_parameters'])), \
                patch.object(Driver,'read_param',return_value=99):
            with self.assertRaises(RuntimeError):ns['ConfiguredDriver']().connect(10)

    def test_startup_hook_preserves_stock_then_sets_only_valid_parameters(self):
        import tempfile,hashlib
        from pathlib import Path
        tree=ast.parse(session.SURVEY_RUNNER.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_px4_parameters')
        allowed=set(ct.configuration()['px4_parameters'])
        ns=dict(json=json,math=math,os=os,Path=Path,hashlib=hashlib,PX4_ETC='/pinned/etc',
                ConfiguredDriver=SimpleNamespace(ALLOWED=allowed))
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(session.SURVEY_RUNNER),'exec'),ns)
        with tempfile.TemporaryDirectory() as tmp:
            env={'PATH':'/usr/bin'}
            with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(ct.configuration()['px4_parameters'])):
                evidence=ns['prepare_px4_parameters'](env,Path(tmp))
            body=(Path(tmp)/'px4-rc.params').read_text()
            self.assertEqual(body.splitlines()[0],'. "/pinned/etc/init.d-posix/px4-rc.params"')
            self.assertIn('param set EKF2_HGT_REF 0\n',body)
            self.assertIn('param set EKF2_BARO_NOISE 0.01\n',body)
            self.assertTrue(env['PATH'].startswith(tmp+os.pathsep))
            self.assertEqual(evidence['hook_sha256'],hashlib.sha256(body.encode()).hexdigest())
            for bad in ({'UNKNOWN':1},{'EKF2_HGT_REF':'0; echo invalid'},{'EKF2_BARO_NOISE':float('nan')}):
                with patch.dict(os.environ,FLIGHT1S_PARAMETERS=json.dumps(bad)):
                    with self.assertRaises(ValueError):ns['prepare_px4_parameters'](env,Path(tmp))

    def test_perception_and_acceptance_limits_are_unchanged(self):
        from echoai.nexus0.pattern1r_v2 import campaign as before
        self.assertEqual(session.CONSUMER.read_bytes(),old_session.CONSUMER.read_bytes())
        p,q=cp.protocol(),before.protocol()
        for key in ('pattern_limits','survey','school_poses','exam_poses','mutants','mutant_cases','limits','grounding'):
            self.assertEqual(p[key],q[key],key)
        self.assertNotEqual(p['stages'],q['stages'])


class AuditReuseTests(unittest.TestCase):
    def test_only_verified_identical_inputs_reuse_independent_recalculation(self):
        from copy import deepcopy
        record=dict(consumer={'sightings':[[1,7]]},trace_sha256='first')
        world=SimpleNamespace(package_id='world-a');protocol=dict(version=3)
        result={'identity':[dict(name='same_object',ok=True)]}
        with patch.object(cp,'_AUDIT_CACHE',{}), patch.object(cp,'_AUDIT_STATS',dict(recomputed=0,cache_hits=0)), \
                patch.object(cp,'evaluate_record',return_value=deepcopy(result)) as evaluate:
            first=cp.audited_evaluation(record,world,protocol,inputs_verified=True)
            first['identity'][0]['ok']=False
            second=cp.audited_evaluation(record,world,protocol,inputs_verified=True)
            self.assertTrue(second['identity'][0]['ok'])
            self.assertEqual(evaluate.call_count,1)
            # Failed current raw-file/code verification forbids a cached result.
            cp.audited_evaluation(record,world,protocol,inputs_verified=False)
            self.assertEqual(evaluate.call_count,2)
            for changed,other_world,other_protocol in (
                    (dict(record,consumer={'sightings':[[1,8]]}),world,protocol),
                    (dict(record,trace_sha256='changed'),world,protocol),
                    (record,SimpleNamespace(package_id='world-b'),protocol),
                    (record,world,dict(version=4))):
                cp.audited_evaluation(changed,other_world,other_protocol,inputs_verified=True)
            self.assertEqual(evaluate.call_count,6)
            self.assertEqual(cp._AUDIT_STATS,dict(recomputed=6,cache_hits=1))

    def test_unverified_evaluation_never_seeds_the_cache(self):
        with patch.object(cp,'_AUDIT_CACHE',{}), patch.object(cp,'_AUDIT_STATS',dict(recomputed=0,cache_hits=0)), \
                patch.object(cp,'evaluate_record',return_value={}) as evaluate:
            cp.audited_evaluation({},SimpleNamespace(package_id='a'),{},inputs_verified=False)
            cp.audited_evaluation({},SimpleNamespace(package_id='a'),{},inputs_verified=True)
            self.assertEqual(evaluate.call_count,2)


if __name__=='__main__':unittest.main()
