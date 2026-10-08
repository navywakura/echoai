import hashlib
import json
import unittest

import observe_b5 as viewer


class B5ViewerTests(unittest.TestCase):
    def signed(self, **event):
        row = dict(schema=viewer.previous.ARC_SCHEMA, **event)
        row["hash"] = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        return row

    def test_real_records_render_and_tampering_fails(self):
        row = self.signed(kind="refinement_result", status="AMBIGUOUS", trials=10, verified=2, prediction_groups=2)
        self.assertIn("AMBIGUOUS", viewer.render(row)[0])
        row["verified"] = 3
        with self.assertRaises(ValueError):
            viewer.render(row)

    def test_no_invented_mission_or_thoughts(self):
        row = self.signed(kind="start", origin="DEVELOPMENT", agent="s6b5", budget=2000)
        self.assertEqual(viewer.render(row), ["INICIO DEVELOPMENT · s6b5 · presupuesto 2000"])
        row = {"kind": "verdict", "id": 0, "verdict": "V4", "A": {"before_levels": 178, "after_levels": 181, "loss_indices": []}}
        self.assertIn("178→181", viewer.render(row)[1])


if __name__ == "__main__":
    unittest.main()
