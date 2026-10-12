"""New families: independent oracle, seeded defect, held-out actor inputs."""
import tempfile
from pathlib import Path
import unittest
from echoai.pcworld.repairs import repair_tasks, repair_reference, repair_domain
from echoai.pcworld.verifier import check_observation, validate_challenge
from echoai.pcworld.runner import execute

class RepairCorpus(unittest.TestCase):
    def test_six_independent_families(self):
        tasks=repair_tasks()
        self.assertEqual(len(tasks),6)
        self.assertEqual(len({t['family'] for t in tasks}),6)
        for task in tasks:
            for x in task['public_inputs']+task['development_inputs']:
                self.assertTrue(repair_domain(task['property'],x),(task['id'],x))
                self.assertEqual(validate_challenge(task['property'],{
                    'claim_id':task['property'],'input':x,'preconditions':task['preconditions'],
                    'oracle_reference':task['checker']})['status'],'eligible')
    def test_reference_edge_cases(self):
        self.assertEqual(repair_reference('repair.intervals',[[1,4],[2,3],[4,5]]),[[1,5]])
        self.assertEqual(repair_reference('repair.csv','"a,b",c,"d""e"'),['a,b','c','d"e'])
        self.assertEqual(repair_reference('repair.path','/a/../../b//./c/'),'/b/c')
        self.assertEqual(repair_reference('repair.pagination',{'items':[1,2,3],'offset':-1,'limit':2}),[1,2])
        self.assertEqual(repair_reference('repair.records',[{'id':'a','value':1},{'id':'a','value':2}]),[{'id':'a','value':1}])
        self.assertEqual(repair_reference('repair.dependencies',{'nodes':['a','b'],'edges':[['b','a']]}),['b','a'])
        self.assertIsNone(repair_reference('repair.dependencies',{'nodes':['a'],'edges':[['a','a']]}))
    def test_initial_programs_have_real_induced_failures(self):
        from echoai.pcworld.receipts import canonical
        with tempfile.TemporaryDirectory() as d:
            work=Path(d)
            for task in repair_tasks():
                (work/'solution.py').write_text(task['initial'])
                results=[]
                for x in task['public_inputs']+task['development_inputs']:
                    r=execute(work,['/usr/bin/python3','-I','/workspace/solution.py'],stdin=canonical(x))
                    results.append(check_observation(task['property'],x,r)['status'])
                self.assertEqual(results[0],'supported',task['id'])
                self.assertIn('contradicted',results[1:],task['id'])
    def test_invalid_domain_and_invented_oracle(self):
        self.assertFalse(repair_domain('repair.path','relative/path'))
        self.assertFalse(repair_domain('repair.intervals',[[4,1]]))
        self.assertFalse(repair_domain('repair.dependencies',{'nodes':['a'],'edges':[['b','a']]}))
        task=repair_tasks()[0]
        self.assertEqual(validate_challenge(task['property'],{
            'claim_id':task['property'],'input':task['public_inputs'][0],
            'preconditions':task['preconditions'],'oracle_reference':'invented'})['status'],'unknown')
    def test_cycle_wrong_union_variant_is_a_counterexample(self):
        observation={'status':'EXITED','exit_code':0,'snapshot':'a'*64,'stdout':'["a"]'}
        prop=check_observation('repair.dependencies',{'nodes':['a'],'edges':[['a','a']]},observation)
        self.assertEqual(prop['status'],'contradicted')
        bad={**observation,'stdout':'true'}
        self.assertEqual(check_observation('repair.dependencies',{'nodes':['a'],'edges':[]},bad)['status'],'unknown')
