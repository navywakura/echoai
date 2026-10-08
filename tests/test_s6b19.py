import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echo_arc import cost_guard_search as c
from seed import s6b19 as r
from tests.test_s6b18 import fixture


class CostSearchTests(unittest.TestCase):
    def test_acceptance_threshold_allows_sacrificing_extra_gain_to_avoid_loss(self):
        current,rows,event,schema,broad,narrow=fixture()
        gain=copy.deepcopy(rows[0]);gain['diagnostics']['consumers'][0]['features']['pred_error']=1
        rows.append(gain)
        event['development']['candidate_consumers'].append(copy.deepcopy(event['development']['candidate_consumers'][1]))
        event['development']['case_effects'].append(dict(case_index=2,level_delta=1,score_delta=1))
        with patch.object(c.old,'consumption_equivalent',return_value=False):
            ranking=c.rank(schema,rows,event,[event],current)
        self.assertEqual(ranking[0]['proposal'],narrow)
        self.assertEqual(ranking[0]['predicted_gain_coverage'],3)
        self.assertEqual(ranking[1]['predicted_gain_coverage'],4)

    def test_value_is_not_permanently_locked(self):
        current,rows,event,schema,broad,narrow=fixture()
        history=[copy.deepcopy(event) for _ in range(3)]
        for i,e in enumerate(history):e['id']=11+i
        schema['groups'].append(dict(parameter='HOLD',value=4,guards=[narrow['patches'][0]['when']]))
        found=c.rank(schema,rows,history[-1],history,current)
        self.assertEqual(found[0]['proposal']['patches'][0]['set'],{'HOLD':4})
        self.assertTrue(found[0]['changed_value'])

    def test_target_reduces_losses_after_gain_requirement_is_met(self):
        current,rows,event,schema,broad,narrow=fixture()
        child=copy.deepcopy(event);child['id']=12
        event['development'].update(gross_level_gain=8,losses=2,score_loss=1.)
        child['development'].update(gross_level_gain=4,losses=1,score_loss=.2)
        self.assertEqual(c.target_for(current,[event,child],['HOLD'])['id'],12)

    def test_protected_and_incomplete_evidence_refused(self):
        current,rows,event,schema,broad,narrow=fixture()
        event['development']['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):c.rank(schema,rows,event,[event],current)
        event['development']['origin']='DEVELOPMENT_A';event['development']['candidate_consumers'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):c.rank(schema,rows,event,[event],current)

    def test_input_order_does_not_change_ranking(self):
        current,rows,event,schema,broad,narrow=fixture()
        first=c.rank(schema,rows,event,[event],current)
        schema['groups'][0]['guards'].reverse()
        self.assertEqual(c.rank(schema,rows,event,[event],current),first)

    def test_ordinary_late_reads_are_not_mislabelled_as_patch_interventions(self):
        current,rows,event,schema,broad,narrow=fixture()
        first=c.rank(schema,rows,event,[event],current)
        untouched=dict(features=copy.deepcopy(rows[0]['diagnostics']['consumers'][0]['features']),count=1000,value=40)
        event['development']['candidate_consumers'][1].append(untouched)
        self.assertEqual(c.rank(schema,rows,event,[event],current),first)


class QualificationTests(unittest.TestCase):
    def test_micro_shares_only_first_call_and_independent_audit_detects_tampering(self):
        from unittest.mock import Mock
        req=dict(id=1,type='WAIT',target_id=None,requested_operator='HOLD',shortlist=[],
                 guard_schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[]))
        answer=dict(answer='{"patches":[]}',usage=dict(input_tokens=0,max_output_tokens=160))
        base=dict(rows=[],levels=0,score=0.,trace_digest=r.sha([]))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'out';inputs=Path(d)/'input'
            r.atomic(inputs/'baseline.json',dict(policy=r.engine.strategy(),history=[],screen_trace_sha256=r.sha([])))
            r.atomic(root/'primary/measurements/baseline/A.json',base)
            def propose(call,*args):
                folder=root/'calls'/call;folder.mkdir(parents=True)
                (folder/'stderr.txt').write_text('test: offloaded 37/37 layers')
                r.atomic(folder/'result.json',answer);return answer
            generate=Mock(side_effect=propose);load=Mock(return_value=answer)
            with patch.object(r,'ROOT',root),patch.object(r,'INPUT',inputs),patch.object(r,'ROUNDS',1), \
                    patch.object(r,'integrity',return_value={}),patch.object(r,'status'), \
                    patch.object(r.old.s6b18_model,'environment_model',return_value=dict(propose=generate,load=load)), \
                    patch.object(r.controller,'request',return_value=req),patch.object(r,'reproduced',return_value=base), \
                    patch.object(r,'measure',return_value=base):
                first=r.run();self.assertEqual(generate.call_count,1);self.assertEqual(load.call_count,1)
                audit=r.run(True);self.assertEqual(audit['cells'],first['cells']);self.assertEqual(generate.call_count,1)
                path=root/'steps/micro/hybrid/000.json';value=r.read(path);value['event']['verdict']='A_ONLY_PASS';r.atomic(path,value)
                with self.assertRaisesRegex(RuntimeError,'verdict mismatch'):r.run(True)

    def test_partitions_disjoint_and_consumed_cases_declared_development(self):
        self.assertEqual(len(r.A),12);self.assertEqual(len(r.DEVELOPMENT),160);self.assertEqual(len(r.B),80)
        self.assertTrue(set(r.A)<=set(r.DEVELOPMENT))
        self.assertFalse(set(r.DEVELOPMENT)&set(r.B))
        self.assertFalse(r.config()['exam_allowed'])

    def test_protected_observation_is_rejected_before_a_game(self):
        with patch.object(r,'_play',side_effect=AssertionError('must not play')):
            for spec,path in [(r.B[0],'visible'),((3,99999,0,2000),None),(r.DEVELOPMENT[0],'visible')]:
                with self.assertRaises(ValueError):r.play_one((r.engine.strategy(),spec,path))

    def test_replay_mismatch_blocks(self):
        with patch.object(r,'measure',side_effect=[dict(rows=[1]),dict(rows=[2])]):
            with self.assertRaisesRegex(RuntimeError,'replay discrepancy'):r.reproduced('primary','case',{},r.A)

    def test_score_loss_cannot_be_offset_by_more_levels(self):
        b=dict(rows=[dict(levels_completed=1,score=10)],levels=1,score=10)
        a=dict(rows=[dict(levels_completed=5,score=9)],levels=5,score=9)
        self.assertFalse(r.a_pass(r.difference(b,a)))

    def test_protected_requires_broad_independent_qualification(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            q=dict(valid=True,passed=['hybrid'])
            r.atomic(Path(d)/'qualification.json',q)
            r.atomic(Path(d)/'qualification-audit.json',dict(valid=True,qualification_sha256='tampered'))
            with self.assertRaisesRegex(RuntimeError,'independently qualified'):r.retention()

    def test_budget_includes_rejected_candidates(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.reserve(r.MAX_GAMES)
            with self.assertRaisesRegex(RuntimeError,'cap'):r.reserve(1)

if __name__=='__main__':unittest.main()
