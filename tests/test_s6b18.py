import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echo_arc import guard_search as s, stale_transition as rules
from seed import s6b18 as r


def features(**kw):
    f={k:lo for k,(lo,hi) in rules.FEATURES.items()}
    f.update(reset_known=1,level=7,world_events=32,**kw)
    return f


def fixture():
    current=r.engine.strategy()
    normal=features();late=features(pred_error=1)
    rows=[dict(origin='DEVELOPMENT_A',diagnostics=dict(consumers=[dict(parameter='HOLD',features=normal,count=1,value=40)]))
          for _ in range(2)]
    broad={'patches':[{'set':{'HOLD':3},'when':{'reset_known':['eq',1]}}]}
    narrow={'patches':[{'set':{'HOLD':3},'when':{'reset_known':['eq',1],'pred_error':['eq',0]}}]}
    event=dict(id=11,base_sha256=r.sha(current),target_id=None,proposal=broad,verdict='V3',
        development=dict(origin='DEVELOPMENT_A',consumer_parameter='HOLD',
            gross_level_gain=3,gross_level_loss=0,losses=1,score_loss=0.4,
            candidate_consumers=[[dict(features=normal,count=1,value=3)],
                                 [dict(features=normal,count=1,value=3),dict(features=late,count=2,value=3)]],
            case_effects=[dict(case_index=0,level_delta=3,score_delta=1),
                          dict(case_index=1,level_delta=0,score_delta=-0.4)]))
    schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[
        dict(parameter='HOLD',value=3,guards=[broad['patches'][0]['when'],narrow['patches'][0]['when']])])
    return current,rows,event,schema,broad,narrow


class SearchTests(unittest.TestCase):
    def test_late_candidate_state_separates_guards_indistinguishable_on_base(self):
        current,rows,event,schema,broad,narrow=fixture()
        ranked=s.rank(schema,rows,event,[event],current)
        self.assertEqual(ranked[0]['proposal'],narrow)
        self.assertFalse(s.consumption_equivalent(narrow,event,current))
        self.assertTrue(s.consumption_equivalent(broad,event,current))

    def test_irrelevant_syntactic_change_is_certified_without_replaying(self):
        current,rows,event,schema,broad,narrow=fixture()
        same=copy.deepcopy(broad);same['patches'][0]['when']['level']=['le',8]
        self.assertTrue(s.consumption_equivalent(same,event,current))
        same['patches'][0]['set']['HOLD']=4
        self.assertFalse(s.consumption_equivalent(same,event,current))

    def test_foreign_base_and_operator_cannot_authorize_skip(self):
        current,rows,event,schema,broad,narrow=fixture()
        event['base_sha256']='foreign';self.assertFalse(s.consumption_equivalent(broad,event,current))
        event['base_sha256']=r.sha(current);event['development']['consumer_parameter']='COOLDOWN_CAP'
        self.assertFalse(s.consumption_equivalent(broad,event,current))

    def test_incomplete_reads_are_an_instrument_failure(self):
        current,rows,event,schema,broad,narrow=fixture()
        event['development']['candidate_consumers'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):s.consumption_equivalent(broad,event,current)
        with self.assertRaisesRegex(ValueError,'complete'):s.rank(schema,rows,event,[event],current)

    def test_protected_evidence_never_enters_search_or_feedback(self):
        current,rows,event,schema,broad,narrow=fixture()
        event['development']['origin']='PROTECTED_B'
        for fn in (lambda:s.rank(schema,rows,event,[event],current),lambda:s.feedback(event),
                   lambda:s.consumption_equivalent(narrow,event,current)):
            with self.assertRaises(ValueError):fn()

    def test_late_varying_feature_survives_feedback(self):
        current,rows,event,schema,broad,narrow=fixture()
        shown=s.feedback(event)
        self.assertTrue(any(x['features']['pred_error']==1 for e in shown for x in e['observed_candidate_consumptions']))
        self.assertTrue(all('case_index' not in e for e in shown))

    def test_candidate_memory_retains_earlier_loss_after_child_fixes_it(self):
        current,rows,event,schema,broad,narrow=fixture()
        child=copy.deepcopy(event);child.update(id=12,target_id=11)
        child['development']['case_effects'][1]['score_delta']=0
        child['development']['candidate_consumers'][1]=[dict(features=features(),count=1,value=3)]
        # The previous late counterexample must still contribute to the burden.
        with patch.object(s,'consumption_equivalent',return_value=False):
            ranking=s.rank(schema,rows,child,[event,child],current)
        self.assertEqual(ranking[0]['proposal'],narrow)
        self.assertGreater(ranking[1]['loss_read_burden'],ranking[0]['loss_read_burden'])

    def test_exhaustion_is_not_success_or_an_extra_model_call(self):
        current,rows,event,schema,broad,narrow=fixture();schema['groups']=[]
        self.assertEqual(s.rank(schema,rows,event,[event],current),[])
        self.assertEqual(s.deterministic_answer({'shortlist':[]}),'{'+'"patches":[]}')

    def test_permuting_input_guards_preserves_search_order(self):
        current,rows,event,schema,broad,narrow=fixture()
        first=s.rank(schema,rows,event,[event],current)
        schema['groups'][0]['guards'].reverse()
        self.assertEqual(s.rank(schema,rows,event,[event],current),first)

    def test_frequencies_sum_within_case_and_do_not_accumulate_duplicate_attempts(self):
        current,rows,event,schema,broad,narrow=fixture()
        event['development']['candidate_consumers'][1].append(dict(features=features(pred_error=1),count=3,value=3))
        duplicate=copy.deepcopy(event);duplicate.update(id=12,target_id=11)
        with patch.object(s,'consumption_equivalent',return_value=False):
            first=s.rank(schema,rows,event,[event],current)
            second=s.rank(schema,rows,duplicate,[event,duplicate],current)
        self.assertEqual(first,second)
        self.assertEqual(first[1]['loss_read_burden'],6)


class RunnerTests(unittest.TestCase):
    def test_full_micro_shares_only_initial_model_call_and_audit_detects_tampering(self):
        req=dict(id=1,type='WAIT',target_id=None,requested_operator='HOLD',shortlist=[],
                 guard_schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[]))
        response=dict(answer='{"patches":[]}',usage=dict(input_tokens=0,max_output_tokens=160))
        base=dict(rows=[],levels=378,score=0.,trace_digest=r.sha([]))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'results';inputs=Path(d)/'input'
            r.atomic(inputs/'baseline.json',dict(policy=r.engine.strategy(),history=[],legacy_trace_sha256=r.sha([])))
            def propose(call,*args,**kwargs):
                folder=root/'calls'/call;folder.mkdir(parents=True,exist_ok=True)
                (folder/'stderr.txt').write_text('test fixture: offloaded 37/37 layers')
                r.atomic(folder/'result.json',response);return response
            from unittest.mock import Mock
            proposing=Mock(side_effect=propose);loading=Mock(return_value=response)
            model={'propose':proposing,'load':loading}
            with patch.object(r,'ROOT',root),patch.object(r,'INPUT',inputs),patch.object(r,'ROUNDS',1), \
                    patch.object(r,'integrity',return_value={}),patch.object(r,'status'), \
                    patch.object(r.s6b18_model,'environment_model',return_value=model), \
                    patch.object(r.controller,'request',return_value=req), \
                    patch.object(r,'reproduced',return_value=base),patch.object(r,'measure',return_value=base):
                first=r.run();self.assertEqual(proposing.call_count,1)
                self.assertEqual(loading.call_count,1);self.assertEqual(first['passed'],{})
                audit=r.run(True);self.assertEqual(audit['cells'],first['cells'])
                self.assertEqual(proposing.call_count,1);self.assertEqual(loading.call_count,3)
                path=root/'steps/micro/hybrid/000.json';changed=r.read(path)
                changed['event']['verdict']='A_ONLY_PASS';r.atomic(path,changed)
                with self.assertRaisesRegex(RuntimeError,'verdict mismatch'):r.run(True)

    def test_protected_policy_selection_cannot_change_after_opening(self):
        before=dict(rows=[dict(levels_completed=5,score=1.)],levels=5,score=1.,trace_digest='base')
        after=dict(rows=[dict(levels_completed=5,score=.9)],levels=5,score=.9,trace_digest='candidate')
        base=r.engine.strategy();candidate=r.engine.strategy(program={'patches':[{'set':{'HOLD':3},'when':{'reset_known':['eq',1]}}]})
        micro=dict(passed={'hybrid':dict(policy=candidate,slot=1)})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'out';inputs=Path(d)/'input'
            r.atomic(inputs/'baseline.json',dict(policy=base))
            r.atomic(root/'micro.json',micro);r.atomic(root/'micro-audit.json',dict(valid=True,micro_sha256=r.sha(micro)))
            with patch.object(r,'ROOT',root),patch.object(r,'INPUT',inputs),patch.object(r,'integrity',return_value={}), \
                    patch.object(r,'reproduced',side_effect=[before,after]):
                self.assertFalse(r.retention()['hybrid_conserved'])
                changed=copy.deepcopy(micro);changed['passed']['hybrid']['policy']=base
                r.atomic(root/'micro.json',changed);r.atomic(root/'micro-audit.json',dict(valid=True,micro_sha256=r.sha(changed)))
                with self.assertRaisesRegex(RuntimeError,'selection changed'):r.retention()

    def test_score_regression_blocks_even_large_level_gains(self):
        before={'levels':10,'score':2.,'rows':[dict(levels_completed=5,score=1.),dict(levels_completed=5,score=1.)]}
        after={'levels':14,'score':3.,'rows':[dict(levels_completed=9,score=2.1),dict(levels_completed=5,score=.9)]}
        self.assertFalse(r.a_pass(r.difference(before,after)))
        after['rows'][1]['score']=1.;self.assertTrue(r.a_pass(r.difference(before,after)))

    def test_unknown_games_and_protected_observation_are_rejected_before_execution(self):
        with patch.object(r,'_play',side_effect=AssertionError('must not execute')):
            for spec,path in [((2,999999,0,2000),None),(r.B[0],'visible')]:
                with self.assertRaises(ValueError):r.play_one((r.engine.strategy(),spec,path))

    def test_discrepant_replay_stops_instrument(self):
        with patch.object(r,'measure',side_effect=[{'rows':[1]},{'rows':[2]}]):
            with self.assertRaisesRegex(RuntimeError,'replay discrepancy'):
                r.reproduced('primary','test',r.engine.strategy(),r.A)

    def test_retention_requires_audited_hybrid(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.atomic(Path(d)/'micro.json',dict(passed={}))
            r.atomic(Path(d)/'micro-audit.json',dict(valid=True,micro_sha256=r.sha(dict(passed={}))))
            with self.assertRaisesRegex(RuntimeError,'audited hybrid'):r.retention()

    def test_budget_exhaustion_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.reserve(r.MAX_GAMES)
            with self.assertRaisesRegex(RuntimeError,'cap'):r.reserve(1)
            self.assertEqual(r.read(Path(d)/'budget.json')['scheduled_games'],r.MAX_GAMES)

    def test_micro_cannot_authorize_exam(self):
        config=r.config()
        self.assertEqual(config['exam'],[])
        self.assertEqual(config['per_arm_candidate_slots'],8)
        self.assertEqual(len(config['protected_B']),40)
        self.assertFalse(config['paid'])


if __name__=='__main__':unittest.main()
