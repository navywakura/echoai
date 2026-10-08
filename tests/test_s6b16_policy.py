import copy
import json
import unittest

from echo_arc import repair_outcomes as o
from seed import s6b16_prompt as p, s6b13 as engine
from tests.test_s6b14_policy import measured_row


def pair():
    rows=[measured_row(i) for i in range(4)]
    for i,row in enumerate(rows):
        row.update(frames=['f'],actions_per_level=[1],resets=0,automatic_reset_indices=[],score=10)
        row['levels_completed']=[5,5,1,4][i]
        row['diagnostics']['trajectory']['steps'][0]['outcome']=[False,False,False]
    after=copy.deepcopy(rows)
    for i,row in enumerate(after):
        row['actions']=[['K',2,None]]
        row['levels_completed']=[5,0,5,5][i]
        row['score']=[100,0,11,11][i]
    def wrap(rs):
        return dict(rows=rs,levels=sum(r['levels_completed'] for r in rs),score=sum(r['score'] for r in rs),trace_digest=engine.sha(rs))
    return wrap(rows),wrap(after)


def target(current):
    before,after=pair()
    return dict(id=1,target_id=None,base_sha256=engine.sha(current),type='WAIT',verdict='V3',
        proposal={'patches':[{'set':{'HOLD':1},'when':{'reset_known':['eq',1]}}]},
        A=dict(gain=-4),development=o.comparison(before,after),equivalent_calls=[])


class OutcomeTests(unittest.TestCase):
    def test_largest_level_gain_cannot_be_displaced_by_score_only_gain(self):
        before,after=pair()
        old=o.original.comparison(before,after)
        new=o.comparison(before,after)
        self.assertNotIn(2,[c['case_index'] for c in old['contrasts'][:2]])
        self.assertIn(2,[c['case_index'] for c in new['contrasts'][:2]])
        self.assertEqual((new['gross_level_gain'],new['gross_level_loss']),(5,5))
        self.assertEqual(new['behavior_sha256'],old['behavior_sha256'])

    def test_negative_aggregate_can_be_refined_but_not_accepted(self):
        current=engine.strategy()
        t=target(current)
        before,_=pair()
        selection=o.select(before['rows'],'echo',current,[t],2)
        self.assertEqual(selection['focus'],'REFINE')
        self.assertEqual(selection['target']['id'],1)
        self.assertEqual(selection['parameter'],'HOLD')
        self.assertEqual(t['verdict'],'V3')

    def test_target_bound_of_three_descendants_and_base_hash(self):
        current=engine.strategy(); t=target(current)
        history=[t]
        for i in (2,3,4):
            child=copy.deepcopy(t); child.update(id=i,target_id=1)
            history.append(child)
        self.assertIsNone(o.target_for(current,history,['HOLD']))
        t['base_sha256']='another base'
        self.assertIsNone(o.target_for(current,[t],['HOLD']))

    def test_same_named_features_are_losslessly_reconstructed(self):
        current=engine.strategy(); t=target(current)
        pair_item=t['development']['contrasts'][0]['sequence'][-1]
        pair_item['candidate']['features']['world_events']=27
        public=o.contrasts(t,2)[0]['sequence'][0]
        restored=dict(public['before']['features'],**public['candidate']['feature_changes'])
        self.assertEqual(restored,pair_item['candidate']['features'])
        self.assertEqual(public['candidate']['action'],pair_item['candidate']['action'])

    def test_all_variants_keep_target_patch_and_latest(self):
        current=engine.strategy(); t=target(current)
        before,_=pair()
        req=p.context('echo',2,current,before,[t])
        self.assertEqual(req['type'],'REFINE')
        for text in req['prompt_variants']:
            data=json.loads(text.split('DATA=',1)[1].split('\nJSON only.',1)[0])
            self.assertEqual(data['repair_target_json'],t['proposal'])
            self.assertEqual(data['latest_attempt'],p.receipt(t))
            self.assertEqual(data['target']['gross_level_gain'],5)
            self.assertEqual(len(data['target_contrasts']),2)
            self.assertTrue(any(c['levels'][1]>c['levels'][0] for c in data['target_contrasts']))
            self.assertTrue(any(c['effect']=='loss' for c in data['target_contrasts']))

    def test_protected_evidence_is_rejected(self):
        before,after=pair(); before['rows'][0]['origin']='PROTECTED_B'
        with self.assertRaises(ValueError): o.comparison(before,after)
        t=target(engine.strategy()); t['development']['origin']='PROTECTED_B'
        with self.assertRaises(ValueError): o.contrasts(t)

    def test_fixed_operator_schedule_is_preserved(self):
        before,_=pair()
        self.assertEqual([o.select(before['rows'],'fijo',engine.strategy(),[],i)['parameter']
                          for i in range(3)],['REVALIDATE_NOOP','HOLD','COOLDOWN_CAP'])


if __name__=='__main__': unittest.main()
