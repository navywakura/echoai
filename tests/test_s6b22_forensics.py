"""Checks of the postmortem instrument, without game execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from seed.s6b22_forensics import Reader, category, delta, matches, score_parts, sha


class ForensicsTests(unittest.TestCase):
    def test_individual_loss_overrides_aggregate_gain(self):
        self.assertEqual(category(dict(gain=8,loss_indices=[1])), 'individual_loss')
        self.assertEqual(category(dict(gain=1,loss_indices=[])), 'conservative_plus_one')
        self.assertEqual(category(dict(gain=2,loss_indices=[])), 'pass')

    def test_fewer_total_actions_can_lower_weighted_score(self):
        before=dict(baseline=[1,1],actions_per_level=[100,1])
        after=dict(baseline=[1,1],actions_per_level=[5,2])
        self.assertLess(sum(after['actions_per_level']),sum(before['actions_per_level']))
        self.assertLess(sum(score_parts(after)),sum(score_parts(before)))

    def test_comparison_rejects_different_case_identity(self):
        row=dict(version=3,seed=1,rep=0,budget=2000,levels_completed=1,score=1)
        before=dict(rows=[row],levels=1,score=1)
        after=copy.deepcopy(before);after['rows'][0]['seed']=2
        with self.assertRaisesRegex(ValueError,'identity'):
            delta(before,after)

    def test_replay_mismatch_is_instrument_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m=dict(rows=[],levels=0,score=0,trace_digest=sha([]))
            for name,value in [('s/measurements/base.json',m),
                               ('s/measurements/base/replay.json',dict(m,levels=1)),
                               ('s-audit/measurements/base.json',m)]:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'replay or audit mismatch'):
                Reader(root).triple('s','base')

    def test_guard_boundaries_and_unknown_operator(self):
        self.assertTrue(matches({'world_events':['le',8]}, {'world_events':8}))
        self.assertFalse(matches({'world_events':['le',8]}, {'world_events':9}))
        with self.assertRaises(ValueError):
            matches({'world_events':['lt',8]}, {'world_events':8})


if __name__ == '__main__':
    unittest.main()
