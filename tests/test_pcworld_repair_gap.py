"""Repair control tests: real sandbox outcomes, scripted model outputs only."""
import tempfile
import unittest
from pathlib import Path

from echoai.pcworld.pilot import Episode
from echoai.pcworld.repairs import repair_tasks
from echoai.pcworld.tasks import FixtureProvider

FIXED = "import json,sys\nx=json.load(sys.stdin)\nseen=set();result=[]\nfor r in x:\n if r['id'] not in seen:\n  seen.add(r['id']);result.append(r)\nprint(json.dumps(result))\n"
REGRESSION = "import json,sys\nx=json.load(sys.stdin)\nprint(json.dumps([{'id':'b','value':2}]))\n"

class RepairProvider(FixtureProvider):
    def __init__(self, repairs):
        self.repairs=iter(repairs);self.contexts=[];self.critics=0;self.categories=[]
    def call(self, role, task, context, **kwargs):
        usage={'tokens':0,'llm_calls':0,'fixture_calls':1}
        if role=='critic':
            self.critics+=1
            category=context.get('probe',{}).get('category')
            self.categories.append(category)
            if category=='empty-singleton':
                return {'claim_id':task['property'],'input':[],
                        'preconditions':task['preconditions'],'oracle_reference':task['checker']},usage
            return {'claim_id':task['property'],'input':[{'id':'b','value':2},{'id':'b','value':3}],
                    'preconditions':task['preconditions'],'oracle_reference':task['checker']},usage
        self.contexts.append(context)
        content=task['initial'] if len(self.contexts)==1 else next(self.repairs)
        return {'content':content},usage

class RepairGap(unittest.TestCase):
    def test_counterexample_feedback_is_exact_and_never_includes_hidden_checks(self):
        with tempfile.TemporaryDirectory() as d:
            provider=RepairProvider([FIXED]);task=repair_tasks()[1]
            ep=Episode(Path(d)/'run',task,'E',provider)
            result=ep.run()
            feedback=provider.contexts[1]['repair_feedback']
            c=feedback['failures'][0]
            self.assertEqual(c['input'],[{'id':'b','value':2},{'id':'b','value':3}])
            self.assertEqual(c['observed'],[{'id':'b','value':3}])
            self.assertEqual(c['expected'],[{'id':'b','value':2}])
            self.assertTrue(c['receipt'])
            self.assertEqual(feedback['public_examples'][0]['input'],task['public_inputs'][0])
            self.assertTrue(result['counterexamples_repaired'])
            self.assertTrue(result['final_cases_passed'])
            self.assertTrue(result['development_accepted'])
            self.assertEqual(provider.categories,['duplicate-keys','empty-singleton'])
            self.assertEqual(provider.critics,2)
            self.assertEqual(len(provider.contexts),2)
            self.assertEqual(result['destroyed'],0)
            self.assertNotIn('development_inputs',feedback)

    def test_regressive_patch_does_not_replace_parent_and_second_attempt_gets_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            provider=RepairProvider([REGRESSION,FIXED]);task=repair_tasks()[1]
            ep=Episode(Path(d)/'run',task,'E',provider)
            result=ep.run()
            self.assertEqual(provider.contexts[2]['source'],task['initial'])
            feedback=provider.contexts[2]['repair_feedback']
            self.assertEqual(feedback['feedback_code'],'REJECTED_REGRESSION')
            self.assertEqual(feedback['rejected_source'],REGRESSION)
            self.assertTrue(result['counterexamples_repaired'])
            self.assertTrue(result['final_cases_passed'])
            events=[x['body'] for x in ep.memory.events]
            rejected=[x for x in events if x.get('operation')=='repair_rejected']
            self.assertEqual(len(rejected),1)
            self.assertEqual(provider.critics,2)

    def test_two_failed_repairs_keep_old_candidate_and_never_reopen_critic(self):
        with tempfile.TemporaryDirectory() as d:
            provider=RepairProvider([REGRESSION,REGRESSION]);task=repair_tasks()[1]
            ep=Episode(Path(d)/'run',task,'E',provider)
            result=ep.run()
            self.assertEqual(len(provider.contexts),3)
            self.assertEqual(provider.critics,1)
            self.assertEqual(ep.store.read(ep.store.get(result['candidate']),'solution.py').decode(),task['initial'])
            self.assertFalse(result['counterexamples_repaired'])
            self.assertFalse(result['development_accepted'])

    def test_runtime_error_is_exposed_as_execution_evidence_for_second_repair(self):
        with tempfile.TemporaryDirectory() as d:
            provider=RepairProvider(['print(undefined_name)',FIXED]);task=repair_tasks()[1]
            ep=Episode(Path(d)/'run',task,'E',provider)
            result=ep.run()
            feedback=provider.contexts[2]['repair_feedback']
            errors=[f for f in feedback['failures'] if f['status']=='unknown']
            self.assertEqual(len(errors),1)
            self.assertIn('NameError',errors[0]['execution_error']['stderr'])
            self.assertNotIn('expected',errors[0])
            self.assertEqual(feedback['public_examples'][0]['expected'],task['public_inputs'][0])
            self.assertEqual(feedback['feedback_code'],'REJECTED_REGRESSION')
            self.assertTrue(result['counterexamples_repaired'])

    def test_second_gate_refutation_is_repaired_before_acceptance(self):
        class PathProvider(FixtureProvider):
            def __init__(self): self.proposals=0;self.categories=[]
            def call(self,role,task,context,**kwargs):
                usage={'tokens':0,'llm_calls':0,'fixture_calls':1}
                if role=='critic':
                    category=context['probe']['category'];self.categories.append(category)
                    value='/c/../d' if category=='dotdot-cancellation' else '/../../j'
                    return {'claim_id':task['property'],'input':value,
                            'preconditions':task['preconditions'],'oracle_reference':task['checker']},usage
                self.proposals+=1
                if self.proposals==1: code=task['initial']
                elif self.proposals==2:
                    code="import json,sys,posixpath\nx=json.load(sys.stdin)\nprint(json.dumps(x if x.startswith('/../') else posixpath.normpath(x)))"
                else: code="import json,sys,posixpath\nprint(json.dumps(posixpath.normpath(json.load(sys.stdin))))"
                return {'content':code},usage
        with tempfile.TemporaryDirectory() as d:
            provider=PathProvider();ep=Episode(Path(d)/'run',repair_tasks()[2],'E',provider)
            result=ep.run()
            self.assertEqual(provider.categories,['dotdot-cancellation','root-boundary'])
            self.assertEqual(result['repair_attempts'],2)
            self.assertTrue(result['development_accepted'],result['error'])
            self.assertEqual(result['probe_categories'],['dotdot-cancellation','root-boundary'])

    def test_invalid_second_probe_does_not_satisfy_coverage(self):
        class DuplicateProvider(RepairProvider):
            def call(self,role,task,context,**kwargs):
                if role=='critic':
                    context=dict(context,probe={'category':'duplicate-keys'})
                return super().call(role,task,context,**kwargs)
        with tempfile.TemporaryDirectory() as d:
            ep=Episode(Path(d)/'run',repair_tasks()[1],'E',DuplicateProvider([FIXED]))
            result=ep.run()
            self.assertTrue(result['development_accepted'])
            self.assertIsNone(result['error'])
            self.assertEqual(result['graduation']['status'],'GRADUADO_POR_SUPERVIVENCIA')
            self.assertFalse(result['graduation']['verified'])
            self.assertFalse(result['coverage_complete'])
            self.assertEqual(result['probe_categories'],['duplicate-keys'])
            self.assertLessEqual(result['budget']['used']['critic_calls'],6)

    def test_graduation_never_substitutes_for_failing_final_oracle(self):
        class DuplicateProvider(RepairProvider):
            def call(self,role,task,context,**kwargs):
                if role=='critic':context=dict(context,probe={'category':'duplicate-keys'})
                return super().call(role,task,context,**kwargs)
        with tempfile.TemporaryDirectory() as d:
            task=repair_tasks()[1]
            task['development_inputs'].append([{'id':c,'value':i} for i,c in enumerate('wxyz')])
            incomplete=FIXED.replace('print(json.dumps(result))','print(json.dumps([] if len(x)>3 else result))')
            result=Episode(Path(d)/'run',task,'E',DuplicateProvider([incomplete])).run()
            self.assertIsNone(result['error'])
            self.assertTrue(result['counterexamples_repaired'])
            self.assertEqual(result['graduation']['status'],'GRADUADO_POR_SUPERVIVENCIA')
            self.assertFalse(result['development_accepted'])
            self.assertFalse(result['final_cases_passed'])
            self.assertTrue(result['final_properties'])

    def test_final_oracle_acceptance_is_identical_for_all_four_arms(self):
        for arm in ('S','I2','F','E'):
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as d:
                ep=Episode(Path(d)/'run',repair_tasks()[1],arm,FixtureProvider())
                candidate=ep.apply_content(ep.base,FIXED)
                result=ep.finish(candidate)
                self.assertTrue(result['development_accepted'])
                self.assertFalse(result['coverage_complete'])
                self.assertFalse(result['graduation']['verified'])
                self.assertEqual(result['acceptance_policy'],'common-final-oracle-v1')

    def test_probe_stops_before_seventh_call_in_both_critic_arms(self):
        for arm in ('F','E'):
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as d:
                provider=RepairProvider([])
                ep=Episode(Path(d)/'run',repair_tasks()[1],arm,provider)
                ticket=ep.budget.reserve({'critic_calls':5});ep.budget.settle(ticket,{'critic_calls':5})
                outcome=ep._probe(ep.base,'first-occurrence-order')
                self.assertEqual(outcome['reason'],'critic_calls_exhausted')
                self.assertEqual(provider.critics,1)
                self.assertEqual(ep.budget.report()['used']['critic_calls'],6)

    def test_explicit_wall_budget_controls_admission_and_still_expires(self):
        from echoai.pcworld.accounting import BudgetExceeded
        with tempfile.TemporaryDirectory() as d:
            ep=Episode(Path(d)/'run',repair_tasks()[1],'E',FixtureProvider(),episode_wall_seconds=900)
            ep.start-=301
            ep.transition('read_snapshot')
            ep.start-=600
            with self.assertRaises(BudgetExceeded): ep.transition('read_snapshot')

