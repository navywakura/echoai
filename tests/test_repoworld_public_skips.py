"""Exact public skip evidence passes through parsing, receipts and retention."""
import base64
from dataclasses import asdict, replace
import hashlib
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from .repoworld_support import ROOT
from echoai.pcworld.receipts import ReceiptStore
from echoai.repoworld.checks import (PublicCheckReport, catalog_for, validate_plan,
                                    collect_public_baseline, run_public_checks,
                                    public_regressions, decide_candidate)

SKIP_ID='testing.test_assertion::test_python2_only'
PASS_ID='testing.test_assertion::test_public'
REASON='requires Python 2'


class PublicSkipTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='public-skip-test-')
        self.addCleanup(temp.cleanup)
        root=Path(temp.name)
        self.receipts=ReceiptStore(root/'receipts',root/'authority')
        self.base=SimpleNamespace(snapshot=SimpleNamespace(id='a'*64))
        self.candidate=SimpleNamespace(snapshot=SimpleNamespace(id='f'*64))
        self.states={SKIP_ID:'SKIPPED',PASS_ID:'PASSED'}

    def plan(self):
        value=catalog_for('pytest-dev/pytest')
        value.update(schema='repoworld.public-plan.v2',expected_skips={SKIP_ID:REASON})
        return value

    def observation(self, states, reasons=None):
        reasons={SKIP_ID:REASON} if reasons is None else reasons
        suite=ET.Element('testsuite',tests=str(len(states)))
        for identity,state in states.items():
            classname,name=identity.split('::',1)
            node=ET.SubElement(suite,'testcase',classname=classname,name=name)
            if state=='SKIPPED':
                skip=ET.SubElement(node,'skipped')
                if reasons.get(identity) is not None:
                    skip.set('message',reasons[identity])
            elif state in ('FAILED','ERROR'):
                ET.SubElement(node,'failure' if state=='FAILED' else 'error')
        raw=ET.tostring(suite)
        return dict(status='EXITED',isolation={'job_empty':True},
            exit_code=int(any(v in ('FAILED','ERROR') for v in states.values())),
            stdout='',stderr='',resources={'cpu_us':1},
            artifacts={'public.xml':dict(data_b64=base64.b64encode(raw).decode(),
                                        sha256=hashlib.sha256(raw).hexdigest())})

    def baseline(self, plan, states, second=None, *, reasons=None, second_reasons=None):
        observations=iter([self.observation(states,reasons),
            self.observation(states if second is None else second,
                             reasons if second_reasons is None else second_reasons)])
        return collect_public_baseline(self.base,plan,receipts=self.receipts,
                                       execute_fn=lambda *a,**k:next(observations))

    def report(self, states, reasons=None, *, plan=None):
        observed=self.observation(states,reasons)
        return run_public_checks(self.base,self.candidate,self.plan() if plan is None else plan,
                                 receipts=self.receipts,execute_fn=lambda *a,**k:observed)

    def decision(self, baseline, after, guard):
        workspace=SimpleNamespace(receipts=self.receipts,current=self.base.snapshot)
        def retain(candidate,**kwargs):
            workspace.current=candidate.snapshot
        workspace.retain=retain
        return decide_candidate(workspace,self.candidate,baseline,after,guard=guard)

    def test_expected_platform_skip_preserved_and_hash_bound(self):
        plan=self.plan()
        result=self.baseline(plan,self.states)
        self.assertTrue(result.valid)
        self.assertEqual(result.states,self.states)
        self.assertEqual(getattr(result,'skip_reasons',None),{SKIP_ID:REASON})
        self.assertEqual(PublicCheckReport(**asdict(result)),result)
        for record in self.receipts.records:
            self.assertEqual(record['body']['skip_reasons'],{SKIP_ID:REASON})
        changed=self.plan();changed['expected_skips'][SKIP_ID]='Different public capability'
        self.assertNotEqual(validate_plan(plan),validate_plan(changed))
        after=self.report(self.states)
        for guard in (True,False):
            self.assertTrue(self.decision(result,after,guard)['retained'])
        after=replace(result,states={**self.states,PASS_ID:'SKIPPED'})
        self.assertEqual(public_regressions(result,after),(PASS_ID,))

    def test_unlisted_missing_flaky_and_all_skipped_are_invalid(self):
        for states in ({SKIP_ID:'SKIPPED'},
                       {**self.states,'public::extra':'SKIPPED'},
                       {PASS_ID:'PASSED'}, {SKIP_ID:'FAILED',PASS_ID:'PASSED'}):
            with self.subTest(states=states):
                self.assertFalse(self.baseline(self.plan(),states).valid)
        self.assertFalse(self.baseline(self.plan(),self.states,
                                       {**self.states,PASS_ID:'FAILED'}).valid)

    def test_reason_must_match_plan_and_both_baseline_runs(self):
        for reason in ('missing dependency','',None,REASON+' '):
            with self.subTest(reason=reason):
                self.assertFalse(self.report(self.states,{SKIP_ID:reason}).valid)

    def test_baseline_requires_stable_plan_matched_reasons(self):
        for reason in ('missing dependency','',None,REASON+' '):
            with self.subTest(reason=reason):
                self.assertFalse(self.baseline(self.plan(),self.states,
                    second_reasons={SKIP_ID:reason}).valid)
                self.assertFalse(self.baseline(self.plan(),self.states,
                    reasons={SKIP_ID:reason},second_reasons={SKIP_ID:reason}).valid)

    def test_invalid_skip_evidence_cannot_retain_in_either_guard_mode(self):
        baseline=self.baseline(self.plan(),self.states)
        variants=[
            ('missing test',{PASS_ID:'PASSED'},None),
            ('now failed',{**self.states,SKIP_ID:'FAILED'},None),
            ('now passed',{**self.states,SKIP_ID:'PASSED'},None),
            ('unexpected skip',{**self.states,'public::extra':'SKIPPED'},
             {SKIP_ID:REASON,'public::extra':'unexpected'}),
            ('reason changed',self.states,{SKIP_ID:'missing dependency'}),
            ('reason missing',self.states,{}),
            ('passed to skipped',{**self.states,PASS_ID:'SKIPPED'},
             {SKIP_ID:REASON,PASS_ID:'unexpected'}),
        ]
        for label,states,reasons in variants:
            after=self.report(states,reasons)
            for guard in (True,False):
                with self.subTest(case=label,guard=guard):
                    decision=self.decision(baseline,after,guard)
                    self.assertFalse(decision['retained'],decision)
                    self.assertNotEqual(decision['status'],'PUBLIC_CHECKS_PASSED')
                    self.assertFalse(after.valid)
                    if label=='passed to skipped':
                        self.assertEqual(decision['regressions'],[PASS_ID])

    def test_v1_still_requires_no_skips(self):
        plan=catalog_for('pytest-dev/pytest')
        self.assertFalse(self.report(self.states,plan=plan).valid)
        self.assertFalse(self.baseline(plan,self.states).valid)
        self.assertTrue(self.baseline(plan,{PASS_ID:'PASSED'}).valid)
        native=catalog_for('django/django')
        observed=dict(status='EXITED',isolation={'job_empty':True},exit_code=0,
            stdout="test_good (public) ... ok\ntest_skip (public) ... skipped 'requires Python 2'\nRan 2 tests in 0.001s\n",
            stderr='',resources={'cpu_us':1})
        result=run_public_checks(self.base,self.candidate,native,receipts=self.receipts,
                                 execute_fn=lambda *a,**k:observed)
        self.assertFalse(result.valid)

    def test_legacy_report_constructor_defaults_reasons_independently(self):
        first=PublicCheckReport('a'*64,'b'*64,{},'c'*64,'d'*64,True)
        second=PublicCheckReport(**asdict(first))
        self.assertEqual(getattr(first,'skip_reasons',None),{})
        first.skip_reasons[SKIP_ID]=REASON
        self.assertEqual(second.skip_reasons,{})

    def test_allowlist_requires_new_schema_and_concrete_reasons(self):
        for value in ({'x':''}, {'x':42}, ['x'], {}):
            plan=self.plan();plan['expected_skips']=value
            with self.assertRaises(ValueError):validate_plan(plan)
        plan=self.plan();plan['schema']='repoworld.public-plan.v1'
        with self.assertRaises(ValueError):validate_plan(plan)


if __name__=='__main__':unittest.main()
