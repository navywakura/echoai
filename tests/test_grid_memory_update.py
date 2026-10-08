import copy
import unittest
from echoai.seed import sandbox
from echoai.seed.refinement import RefinementLibrary
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from seed.arc_memory import ArcMemory,sha
from seed.grid_memory_update import acquire
from tests.test_arc_integration import task


class Acquisition(unittest.TestCase):
    def setUp(self):
        sandbox._set_level('S2v')
        self.lib=RefinementLibrary();self.memory=ArcMemory();self.guide=SparsePrimitiveGuide(640)
        self.payload={'memory':self.memory.state(),'guides':{'640':{'examples':0,'weights':''}},
          'search':{'max_trials':200,'max_depth':4,'beam_width':12,'verification_window':96}}

    def test_no_private_output_and_parent_is_preserved(self):
        class Forbidden:
            def __iter__(self):raise AssertionError('test output read')
            def __deepcopy__(self,memo):raise AssertionError('test output copied')
        private=task();private['test'][0]['output']=Forbidden()
        before=sha(self.payload),bytes(self.guide.weights),sha(self.memory.state())
        result=acquire((self.payload,self.lib,self.memory,{640:self.guide}),private,'custom-demonstrations')
        self.assertEqual(before,(sha(self.payload),bytes(self.guide.weights),sha(self.memory.state())))
        next_memory=ArcMemory.restore(result['payload']['memory'],self.lib)
        self.assertEqual(len(next_memory.actor.diary),1)
        self.assertEqual(result['payload']['guides']['640']['examples'],1)
        self.assertFalse(result['payload']['acquisition']['test_outputs_used'])

    def test_no_solution_cannot_become_a_memory(self):
        private=task();private['train'][0]['output']=[[9]*4]
        self.payload['search']['max_trials']=1;self.payload['search']['verification_window']=0
        with self.assertRaises(ValueError):acquire((self.payload,self.lib,self.memory,{}),private,'unsolved')
        self.assertEqual(self.memory.actor.diary,[])


if __name__=='__main__':unittest.main()
