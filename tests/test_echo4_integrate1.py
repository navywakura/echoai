"""INTEGRATE-1: one memory, energy receipts, firewall ablation, resume, SITUATE, cortex off."""
import unittest

from echoai.echo4 import integrate as I
from echoai.echo4 import tribe as T

SEED = 811


class OneMemory(unittest.TestCase):
    def test_body_and_tribe_share_cam_t_q(self):
        life = I.start(SEED, "integrated")
        echo, body = life["tribe"].agents[T.ECHO], life["body"]
        self.assertIs(echo.cam, body.cam)
        self.assertIs(echo.t, body.t)
        self.assertIs(echo.q, body.q)
        self.assertIs(life["tribe"].memories[T.ECHO].cam, body.cam)

    def test_unknown_arm_rejected(self):
        with self.assertRaises(ValueError):
            I.start(SEED, "no_such_arm")


class Credit(unittest.TestCase):
    def test_credit_is_a_known_receipt_and_never_kills(self):
        life = I.start(SEED, "integrated")
        body = life["body"]
        h = body.env.body.h
        self.assertEqual(I.credit(body, 5), min(127, h + 5) - h)
        before_used = body.env.resource_used
        applied = I.credit(body, -127)
        self.assertEqual(body.env.body.h, 1)
        self.assertEqual(body.env.resource_used - before_used, -applied)
        self.assertEqual(body.H, 1)
        self.assertEqual(body.maintenance.current, body.observation(body.env.cell()))

    def test_credit_rejects_non_integer(self):
        life = I.start(SEED, "integrated")
        with self.assertRaises((ValueError, TypeError)):
            I.credit(life["body"], 1.5)


class Life(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lives = {arm: I.run(SEED, arm, pause_digest=True) for arm in ("integrated", "no_firewall")}

    def test_integrated_life_invariants(self):
        s = I.summary(self.lives["integrated"][0])
        self.assertEqual(s["survived"], I.HORIZON)
        self.assertEqual(s["false_facts"], 0)
        self.assertTrue(s["situate_ok"])
        self.assertEqual(s["cortex_calls"], 0)
        self.assertEqual(s["cam_destroyed"], 0)
        self.assertTrue(s["tribe_invariant"])

    def test_without_firewall_the_harm_appears(self):
        s = I.summary(self.lives["no_firewall"][0])
        self.assertGreater(s["false_facts"], 0)

    def test_deterministic(self):
        again, digest = I.run(SEED, "integrated", pause_digest=True)
        self.assertEqual(digest, self.lives["integrated"][1])
        self.assertEqual(I.summary(again)["trace_sha256"], I.summary(self.lives["integrated"][0])["trace_sha256"])

    def test_resume_in_fresh_process_is_identical_and_checks_digest(self):
        life, digest = self.lives["integrated"]
        self.assertEqual(I.resume_fresh_process(SEED, "integrated", digest), I.summary(life)["trace_sha256"])
        with self.assertRaises(RuntimeError):
            I.resume_fresh_process(SEED, "integrated", "0" * 64)


if __name__ == "__main__":
    unittest.main()
