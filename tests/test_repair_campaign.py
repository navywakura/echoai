import json
import tempfile
from pathlib import Path
import unittest

from echo_arc import local_patch
from seed import game_selfimprove_b4 as b4


class CampaignBoundary(unittest.TestCase):
    def test_strategy_and_prompt_evidence_keep_reserved_metadata_out(self):
        self.assertEqual(b4.Execution.validate(b4.strategy("local")), b4.strategy("local"))
        with self.assertRaises(ValueError):
            b4.Execution.validate({"format": "untrusted", "program": local_patch.EMPTY})
        record = {"levels_completed": 4, "score": 12.5, "actions_per_level": [1, 2, 3, 4],
                  "seed": 18999, "game": "PRIVATE", "family": "K4", "baseline": [99],
                  "episodes": [{"action": ["K", 1], "moved": False, "features": {"motor_ready": 1}}]}
        public = b4.public_rows({"rows": [record]})
        raw = json.dumps(public)
        for token in ("seed", "18999", "PRIVATE", "K4", "baseline", "99"):
            self.assertNotIn(token, raw)
        self.assertEqual(public[0]["episodes"][0]["action"], ["K", 1])

    def test_counterexample_is_from_A_and_has_no_hidden_identifiers(self):
        before = {"rows": [{"levels_completed": 4, "score": 10, "seed": 0,
                            "family": "SECRET", "episodes": [{"step": 1}]}]}
        after = {"rows": [{"levels_completed": 3, "score": 8, "seed": 0,
                           "family": "SECRET", "episodes": [{"step": 2}]}]}
        out = b4.counterexamples(before, after)
        self.assertEqual(out[0]["index"], 0)
        self.assertNotIn("SECRET", json.dumps(out))
        self.assertTrue(out[0]["score_regression"])
        self.assertNotIn("before_score", out[0])
        self.assertEqual(out[0]["after_episodes"], [{"step": 2}])

    def test_selector_uses_training_episode_similarity_and_p3_gate(self):
        cases = {"rows": [{"levels_completed": n, "score": 0, "actions_per_level": [],
                           "episodes": [{"features": {"motor_ready": 1 if i < 3 else 0}}]}
                          for i, n in enumerate((0, 1, 2, 3, 4))]}
        stats = {k: [0, 0] for k in b4.old.TYPES}
        adaptive = b4.requests("local-echo", 0, 0, 6, b4.strategy("local"), stats, cases, [], [])
        generic = b4.requests("local-fijo", 0, 0, 6, b4.strategy("local"), stats, cases, [], [])
        self.assertNotIn("P3", {r["type"] for r in adaptive})
        self.assertGreater(len({r["type"] for r in adaptive}), 1)
        self.assertEqual(len({r["prompt"] for r in generic}), 1)
        self.assertIn('"motor_ready":0', adaptive[0]["prompt"])
        self.assertNotIn("K4", adaptive[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
