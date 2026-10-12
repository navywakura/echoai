import importlib
import json
from pathlib import Path
import tempfile
import unittest

class Reasoning(unittest.TestCase):
    def test_T09_similarity_is_retrieval_not_rejection(self):
        m=importlib.import_module('echoai.pcworld.memory').EpisodeMemory('task','S')
        m.record({'sha256':'1'*64,'body':{'kind':'observation','claim_status':'contradicted','error':'ValueError'}},kind='failure')
        self.assertTrue(m.recall('failure'));self.assertIsNone(m.reuse('new-corrected-key',{},cacheable=True))
        self.assertEqual(m.cam.destroyed,0)
    def test_T10_exact_cache_requires_all_preconditions_and_explicit_hermetic_scope(self):
        m=importlib.import_module('echoai.pcworld.memory').EpisodeMemory('task','S')
        m.cache('key',{'seed':1},{'status':'supported'},cacheable=True)
        self.assertEqual(m.reuse('key',{'seed':1},cacheable=True)['status'],'supported')
        self.assertIsNone(m.reuse('key',{'seed':2},cacheable=True))
        self.assertIsNone(m.reuse('key',{'seed':1},cacheable=False))
        self.assertGreater(m.lookup_work,0)
    def test_T15_T19_WSP_identifiers_do_not_wrap_at_256(self):
        m=importlib.import_module('echoai.pcworld.memory').EpisodeMemory('task','E')
        keys=[]
        for n in range(260):
            event=m.record({'sha256':f'{n:064x}','body':{'kind':'observation'}},kind='observation')
            keys.append(event['wsp'])
        self.assertEqual(len(set(keys)),260);self.assertTrue(all(len(bytes.fromhex(k))==16 for k in keys))
        self.assertEqual(m.cam.destroyed,0);self.assertEqual(m.cortex_calls,0)
    def test_T16_barrier_and_fuel_replay(self):
        c=importlib.import_module('echoai.pcworld.controller')
        responses=[{'role':'critic','dispatch_id':2,'payload':{}},{'role':'proposer','dispatch_id':1,'payload':{}}]
        self.assertEqual(c.barrier(responses),c.barrier(list(reversed(responses))))
        self.assertEqual(c.choose('E',has_candidate=True,property_status='contradicted',critic_used=False),'propose')
        self.assertEqual(c.choose('F',has_candidate=True,property_status='contradicted',critic_used=False),'critic')
    def test_T18_same_contract_across_arms(self):
        c=importlib.import_module('echoai.pcworld.controller')
        profiles=[c.arm_profile(arm) for arm in ('S','I2','F','E')]
        for p in profiles[1:]: self.assertEqual(p['tools'],profiles[0]['tools']);self.assertEqual(p['limits'],profiles[0]['limits']);self.assertEqual(p['checker'],profiles[0]['checker'])
    def test_T11_critic_cannot_invent_property_or_out_of_domain_case(self):
        v=importlib.import_module('echoai.pcworld.verifier')
        self.assertEqual(v.validate_challenge('sum_positive',{'claim_id':'lie','input':[1]})['status'],'unknown')
        self.assertEqual(v.validate_challenge('sum_positive',{'claim_id':'sum_positive','input':['bad']})['status'],'unknown')
    def test_critic_requires_the_declared_oracle_and_preconditions(self):
        from echoai.pcworld.verifier import validate_challenge, VERSION
        valid={'claim_id':'sum_positive','input':[1], 'oracle_reference':VERSION,
               'preconditions':['integer-list']}
        self.assertEqual(validate_challenge('sum_positive',valid)['status'],'eligible')
        for field in ('oracle_reference','preconditions'):
            missing=dict(valid);missing.pop(field)
            self.assertEqual(validate_challenge('sum_positive',missing)['status'],'unknown')
        self.assertEqual(validate_challenge('sum_positive',{**valid,'oracle_reference':'invented'})['status'],'unknown')
        self.assertEqual(validate_challenge('sum_positive',{**valid,'preconditions':['always true']})['status'],'unknown')
    def test_nonfinite_deep_and_duplicate_json_outputs_are_unknown(self):
        from echoai.pcworld.verifier import check_observation
        for prop,text in [('mean_fraction','{"numerator":NaN,"denominator":1}'),
                          ('mean_fraction','{"numerator":0,"numerator":2,"denominator":1}'),
                          ('unique_sorted','['*1500+']'*1500)]:
            result=check_observation(prop,[2],{'status':'EXITED','exit_code':0,'stdout':text})
            self.assertEqual(result['status'],'unknown')
    def test_T12_true_counterexample_rechecked_on_new_candidate(self):
        v=importlib.import_module('echoai.pcworld.verifier')
        bad={'status':'EXITED','exit_code':0,'stdout':'-1','snapshot':'old'}
        good={'status':'EXITED','exit_code':0,'stdout':'2','snapshot':'new'}
        self.assertEqual(v.check_observation('sum_positive',[-3,2],bad)['status'],'contradicted')
        self.assertEqual(v.check_observation('sum_positive',[-3,2],good)['status'],'supported')
    def test_T06_untrusted_pass_flag_and_timeout_are_unknown(self):
        v=importlib.import_module('echoai.pcworld.verifier')
        for execution in ({'status':'EXITED','exit_code':0,'stdout':'{"valid":true}'},{'status':'TIMEOUT','exit_code':None,'stdout':'2'}):
            self.assertEqual(v.check_observation('sum_positive',[2],execution)['status'],'unknown')
    def test_T20_scope_and_quarantine(self):
        m=importlib.import_module('echoai.pcworld.memory').ConceptShelf()
        m.add('c','sum_positive','recipe',supports=['dev1','dev2'])
        self.assertEqual(m.get('c','unique_sorted')['status'],'inapplicable')
        self.assertEqual(m.get('c','sum_positive')['status'],'candidate')
        m.correct('c',{'status':'contradicted','scope':'sum_positive','receipt':'abc'})
        self.assertEqual(m.get('c','sum_positive')['status'],'quarantined')

class ProviderBoundary(unittest.TestCase):
    def test_credentials_are_not_accepted_as_manifest_fields(self):
        from echoai.pcworld.provider import HTTPProvider
        with self.assertRaisesRegex(ValueError,'credential'):
            HTTPProvider({'api_key':'never-save-me'})
    def test_incomplete_model_identity_is_rejected(self):
        from echoai.pcworld.provider import HTTPProvider
        with self.assertRaises(ValueError): HTTPProvider({'endpoint':'http://localhost:9000','model':'moving-name'})
