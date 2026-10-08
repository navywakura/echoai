import unittest
from echo_arc.repair_evidence import Recorder


class DummyJournal:
    def __init__(self):
        self.rows = []
    def write(self, **row):
        self.rows.append(row)


class Evidence(unittest.TestCase):
    def test_evidence_renames_objects_and_discards_coordinates(self):
        recorder = Recorder(DummyJournal())
        beliefs = {"me": [12, 4], "pos": [37, 18], "pred": [3, 1],
                   "temporal_state": {"orders": [{"sequence": [9, 13], "supports": 2, "conflicts": 0}],
                                      "thresholds": [{"kind": 13, "entries": 3, "supports": 1, "conflicts": 0}]}}
        out = recorder.view(beliefs)
        self.assertNotIn("pos", out)
        self.assertEqual(out["orders"][0]["sequence"], ["object1", "object2"])
        self.assertEqual(out["counts"][0]["object"], "object2")
        self.assertTrue(out["body_known"])

    def test_only_executed_events_produce_bounded_episodes(self):
        journal = DummyJournal()
        recorder = Recorder(journal)
        for step in range(10):
            recorder.write(kind="result", step=step, action=["K", 1, None], before={}, after={},
                           changed=False, game_over=step == 0, level_up=False)
        self.assertEqual(len(journal.rows), 10)
        self.assertEqual(len(recorder.episodes()), 3)
        self.assertEqual(recorder.episodes()[0]["step"], 0)
