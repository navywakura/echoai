import unittest
from types import SimpleNamespace
from echoai.echo58.wspfiles.play import RecordingWorld


class RecordingTests(unittest.TestCase):
    def test_records_only_actual_world_results(self):
        class World:
            absolute=True
            def reset(self):return SimpleNamespace(grid=((3,),),reward=0)
            def step(self,action):return SimpleNamespace(grid=((4,),),reward=-1)
            def close(self):pass
        w=RecordingWorld(World())
        self.assertTrue(w.absolute);w.reset();w.step('M0')
        self.assertEqual(w.records,[{'event':'reset','observation':{'grid':[[3]],'reward':0}},
            {'event':'step','action':'M0','observation':{'grid':[[4]],'reward':-1}}])


if __name__=='__main__':unittest.main()
