import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest

from echo_arc import consumer_observe as c, precise_patch as p


def program(parameter='HOLD', value=0):
    return {'patches':[{'when':{'body_known':['eq',0]},'set':{parameter:value}}]}


class Boundary(unittest.TestCase):
    def test_no_private_observation_or_unsupported_claim(self):
        with self.assertRaises(ValueError):c.ConsumptionRecorder(None,origin='PROTECTED_B',program=p.EMPTY)
        with self.assertRaises(ValueError):c.assess(program(),[{'origin':'RESERVED_EXAM'}])
        with self.assertRaises(ValueError):c.assess(program('BABBLE',3),[])

    def test_consumed_values_and_clamped_results_are_compared(self):
        rows=[{'origin':'DEVELOPMENT_A','diagnostics':{'consumers':[
            {'parameter':'HOLD','value':0,'remaining_before':0,'features':{'body_known':0},'count':2},
            {'parameter':'COOLDOWN_CAP','value':40,'remaining_before':8,'features':{'body_known':0},'count':3}]}}]
        self.assertEqual(c.assess(program(),rows)['would_change_consumed_value'],0)
        self.assertEqual(c.assess(program(value=5),rows)['would_change_consumed_value'],2)
        self.assertEqual(c.assess(program('COOLDOWN_CAP',10),rows)['would_change_consumed_value'],0)
        self.assertEqual(c.assess(program('COOLDOWN_CAP',4),rows)['would_change_consumed_value'],3)
        self.assertEqual(c.assess(program(),rows)['action_improvement'],'UNMEASURED')


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('arcengine'),'managed ARC runtime')
class Native(unittest.TestCase):
    def test_zero_assignment_and_early_temporal_return_are_distinct(self):
        for policy,expected in [(p.EMPTY,40),(program(value=0),0),(program(value=20),20)]:
            recorder=c.ConsumptionRecorder(None,origin='DEVELOPMENT_A',program=policy)
            cls=c.traced_agent_class(policy,recorder);actor=cls([1,2,3,4,5],7)
            actor.to_try.append(5);actor.reset_keys.add(5)
            action=actor.choose('test')
            self.assertEqual(action,('K',5,None))
            self.assertEqual(actor.hold,expected)
            self.assertEqual(recorder.reads,[{'parameter':'HOLD','value':expected,'remaining_before':0}])
            recorder.reads=[];actor.to_try.append(5);actor._temporal_step=lambda:5
            actor.choose('test')
            self.assertFalse(recorder.reads)
            self.assertIsNone(sys.gettrace())

    def test_clamp_reads_are_recorded_and_existing_tracer_preserved(self):
        policy=program('COOLDOWN_CAP',3)
        recorder=c.ConsumptionRecorder(None,origin='DEVELOPMENT_A',program=policy)
        actor=c.traced_agent_class(policy,recorder)([1,2,3,4,5],7)
        actor.hold=10;actor._temporal_step=lambda:1
        actor.choose('test')
        self.assertEqual(recorder.reads,[{'parameter':'COOLDOWN_CAP','value':3,'remaining_before':10}])
        self.assertEqual(actor.hold,3)
        def existing(*_):return None
        sys.settrace(existing)
        try:
            with self.assertRaises(RuntimeError):actor.choose('test')
            self.assertIs(sys.gettrace(),existing)
        finally:sys.settrace(None)

    def test_trace_restored_when_actor_raises(self):
        recorder=c.ConsumptionRecorder(None,origin='DEVELOPMENT_A',program=p.EMPTY)
        actor=c.traced_agent_class(p.EMPTY,recorder)([1,2,3,4,5],7)
        def fail():raise RuntimeError('synthetic failure')
        actor._temporal_step=fail
        with self.assertRaises(RuntimeError):actor.choose('test')
        self.assertIsNone(sys.gettrace())

    def test_full_actions_and_results_are_identical_with_observation(self):
        from echo_arc import agent
        from echo_arc.observe import Journal
        from echo_arc.temporal_bench import _gym_env
        from seed.s6_precise_capacity import Execution
        for policy in (p.EMPTY,program(value=0),program('COOLDOWN_CAP',10)):
            agent._COMP_CACHE.clear()
            native=Execution.play(_gym_env(3,19),240,12345,{'format':'local','program':policy})
            with tempfile.TemporaryDirectory() as directory:
                recorder=c.ConsumptionRecorder(Journal(Path(directory)/'arc-decisions.jsonl'),
                                               origin='DEVELOPMENT_A',program=policy)
                agent._COMP_CACHE.clear()
                try:observed=c.play(_gym_env(3,19),240,12345,policy,recorder)
                finally:recorder.close()
                self.assertEqual(native,observed)
                self.assertEqual(recorder.summary()['consumer_sites']['HOLD']['function'],'Arc3EchoV57.choose')


if __name__=='__main__':unittest.main()
