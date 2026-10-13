import json
from pathlib import Path
import tempfile
import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.accounting import DurableBudget, LIMITS
from echoai.pcworld.accounting import BudgetExceeded
from echoai.pcworld.receipts import ReceiptStore
from echoai.repoworld.provider import generate_repo, ContextOverflow


class ProtocolTests(unittest.TestCase):
    def test_crash_after_generation_reservation_does_not_lose_remaining_budget(self):
        class Provider:
            is_llm=False
            def prepare(self,*a):return 'prompt',[1]*100
            def complete(self,*a,**kw):
                return dict(content='{}',tokens_evaluated=100,tokens_predicted=10)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r=ReceiptStore(p/'r',p/'a');limits={**LIMITS,'tokens':500}
            b=DurableBudget(r,limits);original=b.reserve_for
            def die_after_reserve(key,cost):
                original(key,cost)
                raise SystemExit('simulated process death before provider-intent')
            b.reserve_for=die_after_reserve
            kw=dict(provider=Provider(),deadline=10**20,request_id='stable',receipts=r)
            with self.assertRaises(SystemExit):generate_repo([],{},budget=b,**kw)
            b=DurableBudget(r,limits)
            self.assertEqual(generate_repo([],{},budget=b,**kw),{})
            self.assertEqual(b.report()['used']['tokens'],110)
            self.assertFalse(b.report()['pending'])

    def test_budget_survives_pending_and_settlement_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);store=ReceiptStore(p/'r',p/'a')
            b=DurableBudget(store,LIMITS)
            t=b.reserve_for('request-1',{'tokens':3968,'llm_calls':1})
            b=DurableBudget(store,LIMITS)
            self.assertEqual(b.reserve_for('request-1',{'tokens':3968,'llm_calls':1}),t)
            self.assertEqual(b.report()['reserved']['tokens'],3968)
            b.settle(t,{'tokens':1200,'llm_calls':1})
            b=DurableBudget(store,LIMITS)
            self.assertEqual(b.report()['used']['tokens'],1200)
            self.assertEqual(b.report()['remaining']['tokens'],23800)
            with self.assertRaises(ValueError): b.reserve_for('request-1',{'tokens':3000})

    def test_context_overflow_never_generates(self):
        class Provider:
            is_llm=False
            def prepare(self,messages,request_id,deadline): return 'prompt',list(range(3201))
            def complete(self,*a,**kw): raise AssertionError('must not generate')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r=ReceiptStore(p/'r',p/'a');b=DurableBudget(r,LIMITS)
            with self.assertRaises(ContextOverflow):
                generate_repo([{'role':'user','content':'large'}],{},budget=b,provider=Provider(),deadline=10**20,
                              request_id='x',receipts=r)
            self.assertEqual(b.report()['used']['llm_calls'],0)

    def test_response_replay_does_not_generate_or_charge_twice(self):
        class Provider:
            is_llm=False
            count=0
            def prepare(self,messages,request_id,deadline): return 'prompt',[1]*100
            def complete(self,prompt,**kw):
                self.count+=1
                return {'content':'{"action":"finish","arguments":{}}','tokens_evaluated':100,'tokens_predicted':10}
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);r=ReceiptStore(p/'r',p/'a');b=DurableBudget(r,LIMITS);provider=Provider()
            kwargs=dict(budget=b,provider=provider,deadline=10**20,request_id='x',receipts=r)
            self.assertEqual(generate_repo([],{},**kwargs),generate_repo([],{},**kwargs))
            self.assertEqual(provider.count,1)
            self.assertEqual(b.report()['used']['tokens'],110)

    def test_guard_rejects_regression_then_repairs_and_replays_completed_episode(self):
        from echoai.repoworld.protocol import run_episode
        from echoai.repoworld.environment import repo_store
        from echoai.repoworld.types import RepoBase,PublicTask,EnvironmentRef
        from echoai.repoworld.checks import PublicCheckReport
        import difflib
        def diff(old,new):return ''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/a.py',tofile='b/a.py'))
        class Provider:
            is_llm=False
            index=0
            actions=[{'action':'patch_apply','arguments':{'diff':diff('value = 1\n','value = 0\n')}},
                     {'action':'patch_apply','arguments':{'diff':diff('value = 1\n','value = 2\n')}},
                     {'action':'finish','arguments':{}}]
            def prepare(self,*a):return 'prompt',[1]*100
            def complete(self,*a,**kw):
                answer=self.actions[self.index];self.index+=1
                return dict(content=json.dumps(answer),tokens_evaluated=100,tokens_predicted=10)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'src';src.mkdir();(src/'a.py').write_text('value = 1\n')
            snap=repo_store(p/'store').capture(src)
            base=RepoBase(PublicTask('fixture__repo-1','fixture/repo','a'*40,'Repair value'),snap,EnvironmentRef('b'*64,'c'*64,p/'runtime'))
            def checks(base,candidate,plan,*,receipts):
                snap=candidate.snapshot if hasattr(candidate,'snapshot') else candidate
                states={'public::positive':'FAILED' if 'value = 0' in (snap.root/'a.py').read_text() else 'PASSED'}
                r=receipts.append(dict(event='repoworld.public-check',candidate=snap.id,states=states,valid=True))
                return PublicCheckReport(snap.id,'d'*64,states,'e'*64,r['sha256'],True,'observed fixture',1)
            provider=Provider();kwargs=dict(provider=provider,output=p/'episode',check_plan={'public_targets':['public']},check_fn=checks)
            result=run_episode(base,'E',73,**kwargs)
            self.assertIn('+value = 2',result['model_patch'])
            self.assertEqual(result['budget']['used']['llm_calls'],3)
            self.assertFalse(result['task_success'])
            self.assertEqual(result,run_episode(base,'E',73,**kwargs))
            self.assertEqual(provider.index,3)
            # A crash after the authenticated final receipt but before export
            # must reconstruct the missing export without generating again.
            (p/'episode/submission.json').unlink()
            self.assertEqual(result,run_episode(base,'E',73,**kwargs))
            self.assertTrue((p/'episode/submission.json').is_file())
            records=ReceiptStore(p/'episode/main/receipts',p/'episode/main/authority').records
            decisions=[r['body'] for r in records if r['body'].get('event')=='repoworld.public-decision']
            self.assertEqual([r['retain'] for r in decisions],[False,True])

    def test_pending_generation_resumes_with_original_prompt_and_same_request_id(self):
        from echoai.repoworld.protocol import run_episode
        from echoai.repoworld.provider import InferencePending
        from echoai.repoworld.environment import repo_store
        from echoai.repoworld.types import RepoBase,PublicTask,EnvironmentRef
        from echoai.repoworld.checks import PublicCheckReport
        class Provider:
            is_llm=False
            broken=True
            ids=[]
            def prepare(self,messages,*a):return json.dumps(messages),[1]*100
            def complete(self,prompt,**kw):
                self.ids.append(kw['request_id'])
                if self.broken:raise InferencePending('lost connection')
                return dict(content='{"action":"finish","arguments":{}}',tokens_evaluated=100,tokens_predicted=10)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);src=p/'src';src.mkdir();(src/'a.py').write_text('value=1\n')
            snap=repo_store(p/'store').capture(src);base=RepoBase(PublicTask('fixture__repo-1','fixture/repo','a'*40,'Issue'),snap,EnvironmentRef('b'*64,'c'*64,p/'runtime'))
            def checks(base,snap,plan,*,receipts):
                r=receipts.append(dict(event='repoworld.public-check',states={'test':'PASSED'}))
                return PublicCheckReport(snap.id,'d'*64,{'test':'PASSED'},'e'*64,r['sha256'],True,'ok',1)
            provider=Provider();kw=dict(provider=provider,output=p/'run',check_plan={'public_targets':['test']},check_fn=checks)
            with self.assertRaises(InferencePending):run_episode(base,'S',73,**kw)
            provider.broken=False
            result=run_episode(base,'S',73,**kw)
            self.assertEqual(provider.ids,[provider.ids[0]]*2)
            self.assertEqual(result['budget']['used']['llm_calls'],1)
            self.assertEqual(result['budget']['used']['tests'],2)

    def test_expired_pending_generation_is_charged_and_frozen_without_rerun(self):
        from unittest.mock import patch
        from tests.test_repoworld_arms import fixture,checks
        from echoai.repoworld.protocol import run_episode
        from echoai.repoworld.provider import InferencePending
        from echoai.repoworld.audit import audit_episode
        class Provider:
            is_llm=False
            calls=0
            def prepare(self,*a):return 'prompt',[1]*100
            def complete(self,*a,**kw):
                self.calls+=1
                raise InferencePending('response lost')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);base=fixture(p);provider=Provider()
            kw=dict(provider=provider,output=p/'episode',check_plan={'public_targets':['positive']},check_fn=checks)
            with self.assertRaises(InferencePending):run_episode(base,'S',73,**kw)
            store=ReceiptStore(p/'episode/receipts',p/'episode/authority')
            started=next(r['body']['started'] for r in store.records if r['body'].get('event')=='repoworld.episode-start')
            with patch('echoai.repoworld.protocol.time.time',return_value=started+2000):
                result=run_episode(base,'S',73,**kw)
            self.assertEqual(provider.calls,1)
            self.assertFalse(result['budget']['pending'])
            self.assertEqual(result['budget']['used']['tokens'],868)
            self.assertTrue(audit_episode(p/'episode')['valid'])
            self.assertFalse(audit_episode(p/'episode')['token_usage_complete'])
