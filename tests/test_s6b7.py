import unittest
from seed import s6b7 as s


class ProtectedFeedback(unittest.TestCase):
    def test_no_protected_fields_or_arbitrary_error_details_reach_prompt(self):
        event = {"verdict":"V4", "proposal":{"patches":[{"when":{"reset_pending":["eq",1]},"set":{"HOLD":0}}]},
                 "A":{"gain":8,"changed_action_games":6,"activated_games":6,"loss_indices":[1]},
                 "B":{"secret_grid":[[9]],"loss_indices":[12],"score":0.1},"reason":"private-secret-marker"}
        value=s.public_feedback([event])[0]
        self.assertTrue(value["protected_rejection"])
        self.assertEqual(value["training"]["gain"],8)
        self.assertNotIn("loss_indices",str(value))
        self.assertNotIn("secret",str(value))
        self.assertNotIn("score",str(value))

    def test_budget_and_one_extra_proposal_are_equal(self):
        self.assertEqual(s.config()["new_calls_with_calibration"],8)
        self.assertEqual(s.config()["new_proposals_per_arm_per_seed"],1)
        self.assertFalse(s.config()["exam_opened"])
        rows=[{"index":0,"levels":4,"sites":{},"site_counts":{},"remaining_wait_histogram":{}}]
        parent={"finals":[{"arm":arm,"seed":1,"strategy":s.strategy()} for arm in ("fijo","echo")],"verdicts":[]}
        for arm in ("fijo","echo"):
            self.assertEqual(s.requests(arm,1,rows,parent)["id"],2)


if __name__ == "__main__":
    unittest.main()
