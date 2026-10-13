import difflib
import json
from pathlib import Path
import tempfile
import unittest

from .repoworld_support import ROOT
from echoai.repoworld.accounting import DurableBudget, LIMITS
from echoai.repoworld.checks import PublicCheckReport
from echoai.repoworld.environment import repo_store
from echoai.repoworld.protocol import run_episode
from echoai.repoworld.types import RepoBase, PublicTask, EnvironmentRef
from echoai.repoworld.memory import SharedConceptLibrary
from echoai.pcworld.receipts import ReceiptStore


def fixture(path,identifier='fixture__repo-1'):
    src=path/'src';src.mkdir(exist_ok=True);(src/'a.py').write_text('value = 1\n')
    snapshot=repo_store(path/'store').capture(src)
    return RepoBase(PublicTask(identifier,'fixture/repo','a'*40,'Repair the value'),snapshot,
                    EnvironmentRef('b'*64,'c'*64,path/'runtime'))


def checks(base,candidate,plan,*,receipts):
    snap=candidate.snapshot if hasattr(candidate,'snapshot') else candidate
    states={'positive':'FAILED' if 'value = 0' in (snap.root/'a.py').read_text() else 'PASSED'}
    receipt=receipts.append(dict(event='repoworld.public-check',candidate=snap.id,states=states,valid=True))
    return PublicCheckReport(snap.id,'d'*64,states,'e'*64,receipt['sha256'],True,'public fixture',1)


class FiniteProvider:
    is_llm=False
    def __init__(self,actions):self.actions=iter(actions);self.seeds=[]
    def prepare(self,messages,*args):return json.dumps(messages),[1]*100
    def complete(self,*args,**kw):
        self.seeds.append(kw['sample_seed'])
        return dict(content=json.dumps(next(self.actions)),tokens_evaluated=100,tokens_predicted=10)


class ArmsTests(unittest.TestCase):
    def test_guard_ablation_changes_retention_with_identical_public_checks(self):
        diff=''.join(difflib.unified_diff(['value = 1\n'],['value = 0\n'],fromfile='a/a.py',tofile='b/a.py'))
        results=[]
        for arm in ('E','E_no_guard'):
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);base=fixture(p)
                provider=FiniteProvider([{'action':'patch_apply','arguments':{'diff':diff}},
                    {'action':'finish','arguments':{}}])
                results.append(run_episode(base,arm,73,provider=provider,output=p/'episode',
                    check_plan={'public_targets':['positive']},check_fn=checks))
        self.assertEqual(results[0]['model_patch'],'')
        self.assertIn('+value = 0',results[1]['model_patch'])
        for dimension in ('tests','tools','patches','tokens','llm_calls'):
            self.assertEqual(results[0]['budget']['used'][dimension],results[1]['budget']['used'][dimension])

    def test_invalid_repairs_also_consume_the_two_attempt_limit(self):
        bad=''.join(difflib.unified_diff(['value = 1\n'],['value = 0\n'],fromfile='a/a.py',tofile='b/a.py'))
        actions=[{'action':'patch_apply','arguments':{'diff':bad}},
                 {'action':'patch_apply','arguments':{'diff':'not a diff'}},
                 {'action':'patch_apply','arguments':{'diff':'still invalid'}},
                 {'action':'finish','arguments':{}}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=fixture(p);provider=FiniteProvider(actions)
            result=run_episode(base,'E',73,provider=provider,output=p/'episode',
                check_plan={'public_targets':['positive']},check_fn=checks)
            self.assertEqual(result['status'],'repair_exhausted')
            self.assertEqual(result['budget']['used']['llm_calls'],3)

    def test_i2_freezes_second_branch_when_shared_tests_are_exhausted(self):
        actions=[{'action':'patch_apply','arguments':{'diff':''.join(difflib.unified_diff(
            [f'value = {i}\n'],[f'value = {i+1}\n'],fromfile='a/a.py',tofile='b/a.py'))}} for i in range(1,9)]
        actions += [{'action':'finish','arguments':{}},{'action':'select','arguments':{'branch':0}}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=fixture(p)
            result=run_episode(base,'I2',73,provider=FiniteProvider(actions),output=p/'episode',
                check_plan={'public_targets':['positive']},check_fn=checks)
            self.assertEqual(result['budget']['used']['tests'],10)
            self.assertIn('+value = 9',result['model_patch'])
            self.assertFalse(result['budget']['pending'])

    def test_single_agent_cannot_spend_all_calls_on_localization(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=fixture(p)
            actions=[{'action':'file_view','arguments':{'path':'a.py'}}]*5+[{'action':'finish','arguments':{}}]
            run_episode(base,'S',73,provider=FiniteProvider(actions),output=p/'episode',
                check_plan={'public_targets':['positive']},check_fn=checks)
            rows=ReceiptStore(p/'episode/main/receipts',p/'episode/main/authority').records
            outcomes=[r['body']['result'] for r in rows if r['body'].get('event')=='repoworld.operation-result']
            self.assertTrue(any(r.get('error')=='ValueError' and 'localization quota' in r.get('detail','') for r in outcomes))

    def test_all_roles_and_i2_share_one_budget_with_distinct_generation_seeds(self):
        finish={'action':'finish','arguments':{}}
        for arm,count in [('S',1),('I2',3),('F',4),('E',2),('E_no_guard',2)]:
            with self.subTest(arm=arm),tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp);base=fixture(p)
                actions=[finish]*count
                if arm=='I2':actions[-1]={'action':'select','arguments':{'branch':1}}
                provider=FiniteProvider(actions)
                result=run_episode(base,arm,73,provider=provider,output=p/'episode',
                    check_plan={'public_targets':['positive']},check_fn=checks)
                self.assertEqual(result['budget']['limits'],LIMITS)
                self.assertEqual(result['budget']['used']['tokens'],110*count)
                self.assertEqual(result['budget']['used']['tests'],4 if arm=='I2' else 2)
                if arm=='I2':
                    self.assertEqual(provider.seeds,[73,74,73])
                    self.assertEqual(result['selected_branch'],1)

    def test_shared_public_lesson_requires_recheck_and_costs_lookup(self):
        def diff(value):return ''.join(difflib.unified_diff(['value = 1\n'],[f'value = {value}\n'],fromfile='a/a.py',tofile='b/a.py'))
        actions=[{'action':'patch_apply','arguments':{'diff':diff(0)}},
                 {'action':'patch_apply','arguments':{'diff':diff(2)}},
                 {'action':'finish','arguments':{}}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=fixture(p);library=SharedConceptLibrary(p/'library')
            run_episode(base,'E',73,provider=FiniteProvider(actions),output=p/'donor',
                check_plan={'public_targets':['positive']},check_fn=checks,library=library)
            self.assertEqual(len(library.receipts.records),1)
            lesson=library.receipts.records[0]['body']
            self.assertEqual(lesson['status'],'PUBLIC_EVIDENCE_SCOPED')
            self.assertTrue(lesson['requires_recheck'])
            self.assertNotIn('official_raw_resolved',lesson)
            fresh=SharedConceptLibrary(p/'library')
            recipient=RepoBase(PublicTask('fixture__repo-2',base.task.repo,'f'*40,'New public issue'),base.snapshot,base.environment)
            receipts=ReceiptStore(p/'recipient/receipts',p/'recipient/authority');budget=DurableBudget(receipts,LIMITS)
            hints=fresh.retrieve(recipient,budget=budget)
            self.assertEqual(len(hints),1)
            self.assertEqual(hints[0]['status'],'unvalidated-on-current-commit')
            self.assertTrue(hints[0]['requires_recheck'])
            self.assertEqual(budget.report()['used']['tools'],1)
            self.assertGreater(budget.report()['used']['output_tokens'],0)
