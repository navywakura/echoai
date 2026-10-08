import copy
import unittest

from echo_arc import guard_synthesis as s
from seed import s6b17 as r, s6b17_prompt as p
from tests.test_s6b14_policy import measured_row


def event(current,index=1,parent=None,gain=4,loss=7,verdict='V3'):
    return dict(id=index,target_id=parent,base_sha256=r.sha(current),verdict=verdict,type='WAIT',
        proposal={'patches':[{'set':{'HOLD':1},'when':{'reset_known':['eq',1]}}]},
        A=dict(gain=gain-loss),equivalent_calls=[],development=dict(origin='DEVELOPMENT_A',
            gross_level_gain=gain,gross_level_loss=loss,losses=int(loss>0),score_loss=1.0,
            changed_games=2,behavior_sha256='behavior-'+str(index),contrasts=[{'case_index':0},{'case_index':1}],
            case_effects=[dict(case_index=0,level_delta=gain,score_delta=1),dict(case_index=1,level_delta=-loss,score_delta=-1)]))


def readings():
    rows=[measured_row(i,contradictions=0) for i in range(3)]
    for i,row in enumerate(rows):
        row['diagnostics']['consumers'][0]['features'].update(reset_known=1,world_events=[47,80,128][i])
        row['diagnostics']['consumers'][0]['count']=1
    return rows


class SynthesisTests(unittest.TestCase):
    def test_best_descendant_can_continue_despite_negative_aggregate(self):
        current=r.core.strategy(); root=event(current);child=event(current,2,1,loss=3)
        self.assertIs(s.target_for(current,[root,child],['HOLD']),child)
        selection=s.select(readings(),'echo',current,[root,child],3)
        self.assertEqual(selection['target']['id'],2)
        self.assertEqual(selection['lineage_root'],1)
        self.assertIsNone(selection['paused_family'])

    def test_budget_is_per_lineage_not_reset_at_each_descendant(self):
        current=r.core.strategy();history=[event(current)]
        for i in range(2,9):history.append(event(current,i,i-1,loss=3))
        self.assertIsNone(s.target_for(current,history,['HOLD']))

    def test_a_pass_closes_its_lineage_without_claiming_protected_acceptance(self):
        current=r.core.strategy();history=[event(current,loss=1),event(current,2,1,loss=0,verdict='A_ONLY_PASS')]
        self.assertIsNone(s.target_for(current,history,['HOLD']))
        self.assertNotEqual(history[-1]['verdict'],'accepted')
        # Force the legacy fallback to expose the root it would otherwise reuse.
        old=dict(target=history[0],parameter='HOLD',selected=[1,0],focus='REFINE')
        from unittest.mock import patch
        with patch.object(s.experiments,'select',return_value=old):
            selection=s.select(readings(),'echo',current,history,3)
        self.assertIsNone(selection['target'])
        self.assertEqual(selection['focus'],'WAIT')

    def test_ranking_uses_other_numeric_values_and_is_order_invariant(self):
        current=r.core.strategy();target=event(current)
        guards=[{'reset_known':['eq',1]},{'world_events':['ge',32]},{'world_events':['le',64]}]
        schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[dict(parameter='HOLD',value=1,guards=guards)])
        ranked=s.ranked(schema,readings(),target,[target])
        self.assertEqual(ranked[0]['proposal']['patches'][0]['when'],{'world_events':['le',64]})
        self.assertEqual(ranked[0]['gain_case_coverage'],1)
        self.assertEqual(ranked[0]['loss_read_burden'],0)
        schema['groups'][0]['guards']=list(reversed(guards))
        self.assertEqual(ranked,s.ranked(schema,readings(),target,[target]))

    def test_old_counterexamples_survive_when_better_child_repairs_them(self):
        current=r.core.strategy();root=event(current);child=event(current,2,1,loss=1)
        child['development']['case_effects']=[dict(case_index=0,level_delta=4,score_delta=1),dict(case_index=2,level_delta=-1,score_delta=-1)]
        schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[dict(parameter='HOLD',value=1,guards=[{'reset_known':['eq',1]}])])
        result=s.ranked(schema,readings(),child,[root,child])[0]
        self.assertEqual(result['loss_read_burden'],2)

    def test_no_guards_is_exhaustion_and_does_not_switch_value(self):
        current=r.core.strategy();target=event(current)
        schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[dict(parameter='HOLD',value=2,guards=[{'reset_known':['eq',1]}])])
        self.assertEqual(s.ranked(schema,readings(),target,[target]),[])
        self.assertEqual(p.deterministic_answer({'shortlist':[]}),'{"patches":[]}')

    def test_feedback_receipt_uses_named_controls_without_implicit_legend(self):
        target=event(r.core.strategy())
        receipt=p.receipt(target)
        self.assertEqual(receipt['proposal'],target['proposal'])
        self.assertEqual(receipt['gross_level_loss'],7)

    def test_origin_base_and_privacy_boundaries(self):
        current=r.core.strategy();target=event(current);target['base_sha256']='other'
        self.assertIsNone(s.target_for(current,[target],['HOLD']))
        rows=readings();rows[0]['origin']='RESERVED_EXAM'
        with self.assertRaises(ValueError):s.ranked({},rows,None,[])
        target=event(current);target['development']['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):s.temporal_feedback(target)


if __name__=='__main__':unittest.main()
