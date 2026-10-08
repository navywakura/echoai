"""Scientific boundaries for B3; stdlib-only checks before launch."""
import json
from pathlib import Path
import tempfile
import unittest

from seed import game_selfimprove_b3 as s
from echo_arc import temporal_policy as policy


def result(levels=3, score=12.0):
    return {"rows": [{"levels_completed": levels, "score": score, "resets": 0,
                      "actions_per_level": [40] * levels, "actions": [["C", 6, [22, 12]]],
                      "seed": 98765, "family": "SECRET", "baseline": [99],
                      "model": {"temporal": {"orders": [{"supports": 2, "conflicts": 0,
                                                        "colors": [11, 12]}],
                                              "thresholds": [{"entries": 3, "supports": 2,
                                                              "conflicts": 0, "kind": "SECRET"}]}}}]}


class CampaignBoundary(unittest.TestCase):
    def test_prompt_evidence_does_not_export_hidden_metadata_or_coordinates(self):
        public = s.public_rows(result())
        encoded = json.dumps(public)
        for forbidden in ("seed", "family", "baseline", "colors", "SECRET", "98765", "[22, 12]"):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(public[0]["last_actions"], [["C", 6]])
        self.assertEqual(public[0]["order_evidence"], [{"supports": 2, "conflicts": 0}])

    def test_aggregate_gains_do_not_hide_an_individual_regression(self):
        old = {"rows": result(3, 12)["rows"] + result(1, 2)["rows"]}
        improved_total = {"rows": result(2, 12)["rows"] + result(5, 99)["rows"]}
        self.assertFalse(s.no_regressions(old, improved_total))
        self.assertFalse(s.no_regressions(result(), result(4, 11)))
        self.assertTrue(s.no_regressions(result(), result(4, 13)))

    def test_echo_requests_use_available_evidence_and_p3_requires_an_acceptance(self):
        stats = {t: [0, 0] for t in s.TYPES}
        echo = s.requests("echo", 0, policy.EMPTY, stats, result(), [])
        fixed = s.requests("fijo", 0, policy.EMPTY, stats, result(), [])
        self.assertNotIn("P3", {r["type"] for r in echo})
        self.assertGreater(len({r["type"] for r in echo}), 1)
        self.assertEqual(len({r["prompt"] for r in fixed}), 1)
        self.assertEqual(stats, {t: [0, 0] for t in s.TYPES})

    def test_unfiltered_reconstruction_keeps_valid_rejected_proposals(self):
        candidate = {"defaults": {"PROBE_STRATEGY": 1}, "rules": []}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "journal.jsonl"
            s.journal(path, {"kind": "verdict", "id": 0, "type": "P1", "verdict": "V3",
                             "answer": json.dumps(candidate)})
            s.journal(path, {"kind": "verdict", "id": 1, "type": "P2", "verdict": "V2",
                             "answer": "invalid"})
            current, stats, accepted = s.reconstruct(path)
            self.assertEqual(current, policy.EMPTY)
            self.assertEqual(stats["P1"], [1, 0])
            self.assertEqual(accepted, [])
            self.assertEqual(s.unfiltered(path), candidate)


if __name__ == "__main__":
    unittest.main()
