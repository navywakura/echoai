from collections import deque
import copy
import importlib.util
from types import SimpleNamespace
import unittest

from echo_arc import stale_transition as p


class Revision(unittest.TestCase):
    def setUp(self):
        self.action=('K',1,None)
        self.actor=SimpleNamespace(T={('a',self.action):'b'},adj={'a':{self.action:'b'}},
                                   path=deque([self.action]),facts=[('immutable','journal')])

    def test_only_repeated_observed_contradiction_revises_prediction(self):
        evidence={}
        args=(self.actor,evidence,2,'a',self.action,'a','b',False,False)
        self.assertIsNone(p.revise(*args))
        self.assertEqual(self.actor.T[('a',self.action)],'b')
        receipt=p.revise(*args)
        self.assertEqual(receipt['observations'],2)
        self.assertEqual(self.actor.T[('a',self.action)],'a')
        self.assertEqual(self.actor.adj['a'][self.action],'a')
        self.assertFalse(self.actor.path)
        self.assertEqual(self.actor.facts,[('immutable','journal')])

    def test_disabled_changing_terminal_and_unpredicted_events_never_revise(self):
        for limit,next_state,predicted,over,up in [(0,'a','b',False,False),(1,'b','b',False,False),
             (1,'a',None,False,False),(1,'a','a',False,False),(1,'a','b',True,False),(1,'a','b',False,True)]:
            before=copy.deepcopy(vars(self.actor))
            self.assertIsNone(p.revise(self.actor,{},limit,'a',self.action,next_state,predicted,over,up))
            self.assertEqual(vars(self.actor),before)

    def test_new_operation_is_bounded_and_preserves_existing_dsl(self):
        for value in (0,1,8):
            p.parse('{"patches":[{"set":{"REVALIDATE_NOOP":'+str(value)+'},"when":{"stagnation":["ge",8]}}]}')
        for value in (-1,9,True,'code'):
            with self.assertRaises(ValueError):p.validate({'patches':[{'set':{'REVALIDATE_NOOP':value},'when':{'level':['ge',0]}}]})
        with self.assertRaises(ValueError):p.validate({'patches':[{'set':{'REVALIDATE_NOOP':1},'when':{'seed':['eq',11]}}]})


@unittest.skipUnless(importlib.util.find_spec('numpy'),'managed ARC runtime')
class Native(unittest.TestCase):
    def test_integrated_repair_and_later_successful_transition(self):
        policy={'patches':[{'when':{'level':['ge',0]},'set':{'REVALIDATE_NOOP':2}}]}
        actor=p.agent_class(policy)([1,2,3,4],123)
        act=('K',1,None)
        actor.T[('a',act)]='b';actor.adj['a']={act:'b'}
        actor.patch_pending={'REVALIDATE_NOOP':2}
        actor.learn('a',act,'a',False,False)
        self.assertEqual(actor.T[('a',act)],'b')
        actor.learn('a',act,'a',False,False)
        self.assertEqual(actor.T[('a',act)],'a')
        self.assertEqual(len(actor.noop_revisions),1)
        actor.learn('a',act,'c',False,False)
        self.assertEqual(actor.T[('a',act)],'c')


if __name__=='__main__':unittest.main()
