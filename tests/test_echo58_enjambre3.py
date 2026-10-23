"""Behavioral tests for C3's testimony-to-action contract; no old exams."""
import unittest
from echoai.echo58.enjambre2.memory import Private
from echoai.echo58.enjambre.team import L1, RM
from echoai.echo58.memx.memory import OUTCOMES
try:
    from echoai.echo58.enjambre3.memory import Reader
    from echoai.echo58.enjambre3.agent import Agent
except ImportError:
    Reader = Agent = None

class TestC3(unittest.TestCase):
    def reader(self, entries, arm='v3_n1', layer=L1):
        self.assertIsNotNone(Reader, 'C3 reader not implemented')
        p=Private(0);p.world=0
        key=p.mem.cfg.l1_key(42,0,'ENTER',0) if layer==L1 else (42,43)
        claims={(layer,key):{a:(OUTCOMES.index(out),n,n) for a,out,n in entries}}
        return Reader(arm,p,claims,{},[],{},world=0,round=1),key

    def test_single_alarm_is_retained_then_eligible_for_fallback(self):
        rd,key=self.reader([(1,'HURT',3)])
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertIn((42,'ENTER',0),rd.provisional_requests)

    def test_role_layer_alarm_can_also_be_released(self):
        rd,key=self.reader([(1,'HURT',3)])
        from echoai.echo58.enjambre.team import L2
        key2=rd.cfg.l2_key(0,'ENTER',0)
        rd.claims={(L2,key2):rd.claims[(L1,key)]}
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertIn((42,'ENTER',0),rd.provisional_requests)

    def test_two_authors_alarm_cannot_be_released(self):
        rd,key=self.reader([(1,'HURT',3),(2,'HURT',3)])
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertNotIn((42,'ENTER',0),rd.provisional_requests)

    def test_duplicate_counts_do_not_create_authors(self):
        rd,key=self.reader([(1,'HURT',255)])
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertIn((42,'ENTER',0),rd.provisional_requests)

    def test_safe_conflict_does_not_invent_effect(self):
        rd,key=self.reader([(1,'PASS',3),(2,'GOAL',3)])
        self.assertIsNone(rd.resolve(L1,key))

    def test_alarm_over_safe_is_provisional(self):
        rd,key=self.reader([(1,'HURT',3),(2,'PASS',3)])
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertIn((42,'ENTER',0),rd.provisional_requests)

    def test_discredited_alarm_does_not_block(self):
        rd,key=self.reader([(1,'HURT',3),(2,'PASS',3)])
        rd.trust.bad[1]=1
        self.assertEqual(rd.recall(42,0,'ENTER',0),'PASS')

    def test_private_evidence_keeps_precedence(self):
        rd,key=self.reader([(1,'HURT',3)])
        for _ in range(3):rd.private.observe(42,0,'ENTER',0,'PASS')
        self.assertEqual(rd.recall(42,0,'ENTER',0),'PASS')
        self.assertFalse(rd.provisional_requests)

    def test_threshold_candidates_are_distinct(self):
        rd,key=self.reader([(1,'PASS',1)],'v3_n1')
        self.assertEqual(rd.resolve(L1,key),'PASS')
        rd,key=self.reader([(1,'PASS',1)],'v3_n3')
        self.assertIsNone(rd.resolve(L1,key))

    def test_remote_requires_two_distinct_authors(self):
        rd,key=self.reader([(1,'PASS',3)],layer=RM)
        self.assertIsNone(rd.resolve(RM,key))
        rd,key=self.reader([(1,'PASS',3),(2,'PASS',3)],layer=RM)
        self.assertEqual(rd.resolve(RM,key),'LINK')

    def test_release_only_in_verify_and_without_episode_evidence(self):
        rd,key=self.reader([(1,'HURT',3)])
        self.assertIsNotNone(Agent,'C3 policy missing')
        ag=Agent(source=rd,learn=rd.private,private=rd.private)
        ag.E={};ag.ban={};ag.cur_hand=0;ag.repick_ban={};ag.belief_cache={};ag.recalled={};ag.sig_cache={42:0};ag.why={};ag.release_queries=0
        self.assertEqual(ag._believed(42,'ENTER',0,False),'HURT')
        self.assertIsNone(ag._believed(42,'ENTER',0,True))
        ag.E[(42,'ENTER',0)]=[0,0,1,0,0,0];ag.belief_cache={}
        self.assertEqual(ag._believed(42,'ENTER',0,True),'HURT')

    def test_ablations_change_only_its_target(self):
        rd,key=self.reader([(1,'HURT',3)],'sin_alarma_n1')
        self.assertIsNone(rd.recall(42,0,'ENTER',0))
        rd,key=self.reader([(1,'HURT',3)],'sin_liberacion_n1')
        self.assertEqual(rd.recall(42,0,'ENTER',0),'HURT')
        self.assertFalse(rd.provisional_requests)

if __name__=='__main__':unittest.main()

class TestStudy(unittest.TestCase):
    def test_new_partitions_do_not_overlap_and_counts_fixed(self):
        from echoai.echo58.enjambre3 import bench
        self.assertEqual(len(bench.jobs('development')),63)
        self.assertEqual(len(bench.jobs('validation',1)),210)
        dev={w['seed'] for m in bench.MACROS['development'] for w in bench.mission(m,'development')}
        valid={w['seed'] for m in bench.MACROS['validation'] for w in bench.mission(m,'validation')}
        self.assertFalse(dev & valid)
        with self.assertRaises(ValueError):bench.mission(4,'development')

    def test_independent_reader_matches_declarative_examples(self):
        from echoai.echo58.enjambre3.verify import resolved
        o=OUTCOMES.index('HURT')
        self.assertEqual(resolved('v3_n1',{1:(o,1,1)},0,{}, {},L1),'HURT')
        self.assertIsNone(resolved('sin_alarma_n1',{1:(o,1,1)},0,{}, {},L1))
        self.assertIsNone(resolved('v3_n3',{1:(o,1,1)},0,{}, {},L1))

    def test_exact_signed_rank_and_holm(self):
        try:from echoai.echo58.enjambre3.report import exact_signed_rank,holm
        except ImportError:self.fail('statistical contract not implemented')
        self.assertEqual(exact_signed_rank([1,1,1,1]),1/16)
        self.assertEqual(exact_signed_rank([0,0]),1)
        self.assertEqual(exact_signed_rank([-1,-2]),1)
        self.assertEqual(holm({'a':.01,'b':.02,'c':.04}),{'a':True,'b':True,'c':True})
        self.assertEqual(holm({'a':.02,'b':.03,'c':.04}),{'a':False,'b':False,'c':False})

    def test_offline_audit_rejects_changed_action_and_postcard(self):
        import copy,json
        from unittest.mock import patch
        from echoai.echo58.enjambre3 import bench,verify
        class FixtureWorld:
            def __init__(self,kind,seed,n,ids):self.solved_by=0;self.needs_help=False;self.ids=ids
        def fixture_play(world,agents):
            rows=[]
            for agent in agents:
                ident=min(world.ids.values());prior=agent.source.recall(ident,0,'ENTER',0)
                agent.learn.observe(ident,0,'ENTER',0,'PASS')
                action={'step':1,'act':'ENTER','cell':[1,1],'ident':ident,'sig':0,'hand':0,
                        'prior':prior,'provisional_alarm':False,'outcome':'PASS'}
                rows.append({'harm':0,'harm_probe':0,'steps':1,'asked':0,'held':0,
                             'actions':[action],'release_queries':0})
            return rows
        with patch.object(bench,'CoopWorld',FixtureWorld),patch.object(bench,'play_together',fixture_play):
            for arm in bench.arms('validation',1):
                job=(arm,'false_alarm',1)
                row=json.loads(json.dumps(bench.run_team(*job,'validation',1)))
                audited=verify.validate_job(job,row)
                self.assertEqual(audited['score'],12)
                self.assertEqual(audited['physical']['actions'],8)
                changed=copy.deepcopy(row);changed['rounds'][0]['episodes'][0]['result']['actions'][0]['outcome']='HURT'
                with self.assertRaises(ValueError):verify.validate_job(job,changed)
                changed=copy.deepcopy(row);changed['publications'][0]['sent']='00'*16
                with self.assertRaises(ValueError):verify.validate_job(job,changed)
