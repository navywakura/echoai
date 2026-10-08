import copy
import unittest
from types import SimpleNamespace

from echo_arc import consumption_timeline as t, stale_transition as patch
from echo_arc.contrastive_evidence import FEATURE_ORDER


def row(index=0,value=40,delay=6):
    f={k:lo for k,(lo,_) in patch.FEATURES.items()}
    f.update(reset_known=1,reset_pending=1,world_events=47,pending_effect=0)
    states=[dict(f)]+[dict(f,pending_effect=1,reset_pending=0,hold_remaining=max(0,value-i)) for i in range(delay)]
    read=dict(parameter='HOLD',value=value,remaining_before=0,features=f,
              decision_index=0,action_index=0,immediate_outcome=dict(changed=False,game_over=False,level_up=False))
    return dict(origin='DEVELOPMENT_A',version=2,seed=index,rep=0,budget=2000,
        actions=[['K',1,None] for _ in states],frames=['f' for _ in states],automatic_reset_indices=[],
        resets=0,actions_per_level=[len(states)],score=1.0,levels_completed=1,
        diagnostics=dict(control_timeline=dict(version=1,reads=[read]),
            consumers=[dict({k:read[k] for k in ('parameter','value','remaining_before','features')},count=1)],
            trajectory=dict(features=list(FEATURE_ORDER),steps=[dict(f=[s[k] for k in FEATURE_ORDER],outcome=[False,False,False]) for s in states])))


class TimelineTests(unittest.TestCase):
    def test_delayed_gain_reports_actual_read_features_including_zero(self):
        before=row(value=40);after=row(value=0)
        after['actions'][-1]=['K',5,None];after['levels_completed']=4
        for r in (before,after): t.validate(r)
        linked=t.links({'rows':[before]},{'rows':[after]},'HOLD')[0]
        self.assertEqual(linked['consumed_values'],[40,0])
        self.assertEqual(linked['features']['pending_effect'],0)
        self.assertEqual(before['diagnostics']['trajectory']['steps'][-1]['f'][FEATURE_ORDER.index('pending_effect')],1)
        self.assertEqual(linked['steps_until_action_divergence'],6)
        self.assertIn('association only',linked['causal_status'])

    def test_lost_game_does_not_label_every_control_read_harmful(self):
        before=row();after=row(value=2)
        after['actions'][-1]=['K',5,None];after['score']=0.5
        linked=t.links({'rows':[before]},{'rows':[after]},'HOLD')[0]
        self.assertEqual(linked['score'],[1.0,0.5])
        self.assertNotIn('harmful',linked)
        self.assertIn('association only',linked['causal_status'])

    def test_reset_alignment_and_corrupt_aggregates(self):
        r=row(delay=1)
        r['actions'].insert(0,['R',0,None]);r['automatic_reset_indices']=[0];r['resets']=1
        t.align_steps(r)
        self.assertEqual(r['diagnostics']['control_timeline']['reads'][0]['action_index'],1)
        self.assertIsNone(r['diagnostics']['trajectory']['steps'][0])
        r['diagnostics']['consumers'][0]['count']=2
        with self.assertRaisesRegex(ValueError,'aggregate'):t.validate(r)

    def test_no_pairing_after_behavior_has_already_diverged(self):
        before=row();after=row(value=1)
        after['actions'][0]=['K',2,None]
        for r in (before,after):r['diagnostics']['control_timeline']['reads'][0]['action_index']=3
        self.assertEqual(t.links({'rows':[before]},{'rows':[after]},'HOLD'),[])

    def test_protected_input_is_refused(self):
        r=row();r['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):t.validate(r)
        with self.assertRaises(ValueError):t.links({'rows':[r]},{'rows':[row()]},'HOLD')

    def test_real_actor_control_read_uses_existing_journal_and_is_passive(self):
        from echo_arc.repair_loop_observe import traced_agent_class
        from echo_arc.precise_observe import PreciseObservedAgent
        from echo_arc.observe import snapshot
        from echo_arc.contrastive_evidence import Recorder as OldRecorder
        records=[]
        policy={'patches':[{'set':{'HOLD':0},'when':{'body_known':['eq',0]}}]}
        for cls in (OldRecorder,t.Recorder):
            events=[]
            rec=cls(SimpleNamespace(write=lambda **e:events.append(e),close=lambda:None),origin='DEVELOPMENT_A',program=policy)
            actor=traced_agent_class(policy,rec)([1,2,3,4,5],19)
            actor.to_try.append(5);actor.reset_keys.add(5);rec.bind_actor(actor)
            wrapper=PreciseObservedAgent(actor,rec)
            action=wrapper.choose('synthetic-state')
            rec.write(kind='result',step=1,action=list(action),before=snapshot(actor),after=snapshot(actor),
                      changed=False,game_over=False,level_up=False)
            records.append((action,snapshot(actor),rec.summary()))
        new=records[1][2].pop('control_timeline')
        self.assertEqual(records[0],records[1])
        self.assertEqual(new['reads'][0]['value'],0)
        self.assertEqual(new['reads'][0]['decision_index'],0)
        self.assertEqual(new['reads'][0]['features']['pending_effect'],0)


if __name__=='__main__':unittest.main()
