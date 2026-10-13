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
        self.repairs=iter(repairs);self.contexts=[];self.critics=0
    def call(self, role, task, context, **kwargs):
        usage={'tokens':0,'llm_calls':0,'fixture_calls':1}
        if role=='critic':
            self.critics+=1
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
            self.assertFalse(result['development_accepted'])  # single category stays insufficient
            self.assertEqual(provider.critics,1)
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
            self.assertEqual(provider.critics,1)

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

    def test_explicit_wall_budget_controls_admission_and_still_expires(self):
        from echoai.pcworld.accounting import BudgetExceeded
        with tempfile.TemporaryDirectory() as d:
            ep=Episode(Path(d)/'run',repair_tasks()[1],'E',FixtureProvider(),episode_wall_seconds=900)
            ep.start-=301
            ep.transition('read_snapshot')
            ep.start-=600
            with self.assertRaises(BudgetExceeded): ep.transition('read_snapshot')

