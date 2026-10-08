import unittest

from seed.echo45_completion import outcome


class CompletionTests(unittest.TestCase):
    def test_every_gate_is_required(self):
        self.assertTrue(outcome(True, {"green": True}, {"s6_green": True})["all_green"])
        for validation, cap, s6 in ((False, {"green": True}, {"s6_green": True}),
                                   (True, None, {"s6_green": True}),
                                   (True, {"green": False}, {"s6_green": True}),
                                   (True, {"green": True}, {"s6_green": False}),
                                   (True, {"green": True}, None)):
            self.assertFalse(outcome(validation, cap, s6)["all_green"])


if __name__ == "__main__":
    unittest.main()
