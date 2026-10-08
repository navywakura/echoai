import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from itertools import product

from echo_arc import s6b20_search as s
from seed import s6b20 as r
from tests.test_s6b18 import fixture,features


def event_fixture():
    current,rows,event,schema,broad,narrow=fixture()
    event['proposal']['patches'][0]['set']['HOLD']=1
    for case in event['development']['candidate_consumers']:
        for x in case:x['value']=1
    schema['groups'][0]['value']=1
    return current,rows,event,schema


class SearchTests(unittest.TestCase):
    def test_unanchored_conjunction_is_in_language(self):
        g={'level':['ge',1],'pending_effect':['eq',0],'world_events':['le',16]}
        self.assertTrue(s.legal(g));self.assertNotIn(g,s.precise_patch_grammar.conditions())
        self.assertEqual(s.precise_patch.validate({'patches':[{'set':{'HOLD':1},'when':g}]})['patches'][0]['when'],g)

    def test_three_children_expire_parent(self):
        current,rows,e,schema=event_fixture();history=[e]
        for i in range(3):
            child=copy.deepcopy(e);child.update(id=20+i,target_id=e['id']);child['development']['gross_level_gain']=0;history.append(child)
        self.assertIsNone(s.target_for(current,history))

    def test_complementary_branch_survives_low_loss_branch(self):
        current,rows,e,schema=event_fixture();other=copy.deepcopy(e);other['id']=12
        other['development']['losses']=0;other['development']['gross_level_gain']=1
        other['development']['case_effects'][0]['level_delta']=1
        child=copy.deepcopy(other);child.update(id=13,target_id=12);child['development']['gross_level_gain']=0
        self.assertEqual(s.target_for(current,[e,other,child])['id'],11)

    def test_plus_one_cannot_monopolize_forever(self):
        current,rows,e,schema=event_fixture();e['development']['gross_level_gain']=1
        history=[e]
        for i in range(6):
            child=copy.deepcopy(e);child.update(id=30+i,target_id=11 if i<3 else 30);history.append(child)
        self.assertIsNone(s.target_for(current,history))

    def test_protected_history_and_rows_rejected(self):
        current,rows,e,schema=event_fixture();e['development']['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):s.points_for(rows,[e],current)
        rows[0]['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):s.points_for(rows,[],current)

    def test_candidate_late_features_are_in_pool_evidence(self):
        current,rows,e,schema=event_fixture()
        self.assertTrue(any(x['pred_error']==1 for x in s.points_for(rows,[e],current)))
        e['development']['candidate_consumers'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):s.points_for(rows,[e],current)

    def test_dose_keeps_exact_guard(self):
        current,rows,e,schema=event_fixture();history=[e]
        for i in range(2):
            child=copy.deepcopy(e);child.update(id=20+i,target_id=11);history.append(child)
        schema['groups'].append(dict(parameter='HOLD',value=2,guards=[{'pred_error':['eq',0]},e['proposal']['patches'][0]['when']]))
        ranking=s.rank_new(schema,rows,current,history,e,3)
        self.assertEqual(ranking[0]['proposal']['patches'][0]['when'],e['proposal']['patches'][0]['when'])
        self.assertEqual(ranking[0]['contrast'],'fixed-scope-dose')

    def test_guard_scope_change_keeps_dose(self):
        current,rows,e,schema=event_fixture()
        ranking=s.rank_new(schema,rows,current,[e],e,1)
        self.assertTrue(ranking)
        self.assertTrue(all(x['proposal']['patches'][0]['set']=={'HOLD':1} for x in ranking))

    def test_zero_burden_is_not_an_acceptance(self):
        current,rows,e,schema=event_fixture()
        ranking=s.rank_new(schema,rows,current,[e],e,1)
        self.assertTrue(all('fresh execution required' in x['causal_status'] for x in ranking))
        self.assertTrue(all('accepted' not in x for x in ranking))

    def test_old_and_new_use_common_pool(self):
        current,rows,e,schema=event_fixture();measured={'rows':rows}
        with patch.object(s,'pool',return_value=([{'reset_known':['eq',1]}],{'mock':True})):
            old=s.request('old',0,current,measured,[]);new=s.request('new',0,current,measured,[])
        self.assertEqual(old['guard_schema'],new['guard_schema'])

    def test_library_budget_and_order_are_reproducible(self):
        current,rows,e,schema=event_fixture()
        a,meta=s.pool(rows,[e],current);b,other=s.pool(list(reversed(rows)),[e],current)
        self.assertEqual(a,b);self.assertEqual(meta,other)
        self.assertLessEqual(len(a),s.POOL_LIMIT)
        self.assertGreater(meta['syntax'],1205)

    def test_three_independent_conditions_have_a_distinguishable_scope(self):
        current,_,_,_=event_fixture();rows=[]
        for level,pending,events in product((0,1),(0,1),(0,32)):
            f=features();f.update(level=level,pending_effect=pending,world_events=events)
            rows.append(dict(origin='DEVELOPMENT_A',diagnostics=dict(consumers=[dict(parameter='HOLD',features=f,count=1,value=40)])))
        guards,meta=s.pool(rows,[],current)
        expected=[r['diagnostics']['consumers'][0]['features']['level']==1 and r['diagnostics']['consumers'][0]['features']['pending_effect']==0 and r['diagnostics']['consumers'][0]['features']['world_events']==0 for r in rows]
        self.assertTrue(any([s.matches(g,r['diagnostics']['consumers'][0]['features']) for r in rows]==expected for g in guards))


class RunnerTests(unittest.TestCase):
    def test_no_partition_overlap_and_no_exam(self):
        self.assertTrue(set(r.A)<=set(r.DEVELOPMENT));self.assertFalse(set(r.B)&set(r.DEVELOPMENT))
        self.assertFalse(r.config()['exam_allowed']);self.assertEqual(len(r.CELLS),8)

    def test_protected_observation_rejected_before_execution(self):
        with patch.object(r,'_play',side_effect=AssertionError('must not execute')):
            with self.assertRaises(ValueError):r.play_one((r.engine.strategy(),r.B[0],'viewer'))

    def test_bad_origin_cannot_use_publication_or_hidden_case(self):
        with patch.object(r,'_play',side_effect=AssertionError('must not execute')):
            with self.assertRaises(ValueError):r.play_one((r.engine.strategy(),(3,999999,0,2000),None))

    def test_budget_accounts_failed_reserved_work(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.reserve(r.MAX_GAMES,'test','first')
            with self.assertRaises(RuntimeError):r.reserve(1,'test','retry')

    def test_pair_mismatch_rejected(self):
        row=dict(version=3,seed=1,rep=0,budget=2000,levels_completed=1,score=1)
        base=dict(rows=[row],levels=1,score=1);after=copy.deepcopy(base);after['rows'][0]['seed']=2
        with self.assertRaises(ValueError):r.difference(base,after)

    def test_gain_cannot_hide_score_regression(self):
        row=dict(version=3,seed=1,rep=0,budget=2000,levels_completed=1,score=1)
        base=dict(rows=[row],levels=1,score=1);after=copy.deepcopy(base)
        after.update(levels=5,score=.9);after['rows'][0].update(levels_completed=5,score=.9)
        self.assertFalse(r.previous.a_pass(r.difference(base,after)))

    def test_replay_mismatch_blocks(self):
        with patch.object(r,'measure',side_effect=[{'levels':1},{'levels':2}]):
            with self.assertRaisesRegex(RuntimeError,'replay'):r.reproduced('test','x',{},r.A)

    def test_protection_cannot_open_without_audit(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.atomic(Path(d)/'qualification.json',dict(winners={'H1-1':{}},valid=True))
            r.atomic(Path(d)/'qualification-audit.json',dict(valid=True,qualification_sha256='wrong'))
            with self.assertRaisesRegex(RuntimeError,'audit'):r.qualify('retention')
            self.assertFalse((Path(d)/'retention-opened.json').exists())

    def test_capacity_budget_is_separate_and_stricter(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)/'root'),patch.object(r,'INPUT',Path(d)/'input'):
            r.atomic(r.INPUT/'manifest.json',dict(stage='capacity'))
            r.reserve(2928,'capacity','all')
            with self.assertRaises(RuntimeError):r.reserve(1,'capacity','extra')

    def test_viewer_accepts_real_verdict_shape(self):
        from observe import render
        row=dict(kind='verdict',id=0,arm='C1',verdict='V3',A=dict(before_levels=52,after_levels=53,gain=1,loss_indices=[]))
        self.assertIn('52', '\n'.join(render(row)))


if __name__=='__main__':unittest.main()
