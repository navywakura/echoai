"""B24 custody and budget checks; simulation functions remain mocked here."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from seed import s6b24 as r

class RunnerTests(unittest.TestCase):
    def test_equal_per_arm_caps(self):
        self.assertEqual(len(r.CELLS),5)
        self.assertEqual(r.MAX_GAMES,8310)
        self.assertTrue(all(r.CAPS['S-'+arm]==798 for arm in r.CELLS))
    def test_regression_not_hidden_by_aggregate_gain(self):
        self.assertFalse(r.passes(dict(gain=4,loss_indices=[2])))
        self.assertTrue(r.passes(dict(gain=2,loss_indices=[])))
        self.assertFalse(r.passes(dict(gain=1,loss_indices=[])))
    def test_reserved_partition_requires_permit(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'ROOT',Path(tmp)):
            with self.assertRaisesRegex(ValueError,'closed'):r.check_permit({},r.V_NEW)
    def test_unknown_game_not_played(self):
        with self.assertRaises(ValueError):r.play_one(({},(3,999999,0,2000),None,'x',{}))
    def test_checkpoint_is_transport_boundary(self):
        with patch.dict(os.environ,{'ECHO_B24_DEADLINE_EPOCH':'1'}):
            with self.assertRaises(r.SliceComplete):r.checkpoint('slot')
        with patch.dict(os.environ,{},clear=True):r.checkpoint('slot')
    def test_cross_attempts_pay_their_own_games(self):
        class Captured(Exception):pass
        batches=[]
        def reserve(tasks,*args):
            batches.append(tasks)
            raise Captured()
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'ROOT',Path(tmp)),patch.object(r,'integrity',return_value={}),patch.object(r,'reserve_tasks',side_effect=reserve):
            for label in ('candidate/000','candidate/001','candidate/000'):
                with self.assertRaises(Captured):r.measure('s-B24-I',label,{},r.A)
        self.assertNotEqual(batches[0][0]['key'],batches[1][0]['key'])
        self.assertEqual(batches[0][0]['key'],batches[2][0]['key'])
    def test_time_is_accumulated_when_a_slot_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'ROOT',Path(tmp)):
            with patch.object(r.time,'monotonic',side_effect=[1,103]),patch.object(r.time,'process_time',side_effect=[1,3]):
                with self.assertRaises(r.SliceComplete):
                    with r.slot_timing('B24-S',0):raise r.SliceComplete('test cut')
            with patch.object(r.time,'monotonic',side_effect=[104,107]),patch.object(r.time,'process_time',side_effect=[3,4]):
                with r.slot_timing('B24-S',0):pass
            saved=r.timing_totals('B24-S',0)
            self.assertEqual(saved['seconds'],105)
            self.assertEqual(saved['cpu_seconds'],3)
            self.assertEqual(saved['segments'],2)
    def test_allocation_scopes(self):
        for arm in r.CELLS:
            self.assertEqual(r.allocation('s-'+arm+'-audit'),'S-'+arm)
        with self.assertRaises(ValueError):r.allocation('exam')

if __name__=='__main__':unittest.main()
