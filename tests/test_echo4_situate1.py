"""SITUATE-1: substrate facts, own world proof, unknowns, claims, change detection."""
import unittest

from echoai.echo4 import situate as S
from echoai.echo4 import tribe as T


def ready(sensors=True, seed=5):
    s = T.TribeSession(seed)
    for _ in range(40):
        s.step()
    me = S.SelfKnowledge(s.agents[T.ECHO].cam, sensors=sensors)
    me.observe(S.sense(s.agents))
    me.prove_world(S.replay_proof(seed))
    return s, me


class Situate(unittest.TestCase):
    def test_answers_are_verified_facts(self):
        _, me = ready()
        status, value = S.answer(me, 1)
        self.assertEqual((status, value["human"]), (S.VERIFIED, False))
        self.assertEqual(S.answer(me, 5)[0], S.VERIFIED)
        self.assertEqual(S.answer(me, 6)[1]["persons"], False)
        self.assertTrue(all(s.has_fact and s.extract for s in me.cam.slot
                            if s.occupied and s.source == S.SOURCE_FACT))

    def test_no_sensors_means_unknown(self):
        _, me = ready(sensors=False)
        for q in S.SUBSTRATE_QUESTIONS:
            self.assertEqual(S.answer(me, q)[0], S.UNKNOWN)

    def test_world_is_simulated_only_after_own_proof(self):
        s = T.TribeSession(5)
        me = S.SelfKnowledge(s.agents[T.ECHO].cam)
        me.observe(S.sense(s.agents))
        self.assertEqual(S.answer(me, 5)[0], S.UNKNOWN)
        noisy = S.replay_proof(5, noise=lambda x: x.knower.__setitem__(0, (x.knower[0] + 1) % 3))
        self.assertFalse(me.prove_world(noisy))
        self.assertEqual(S.answer(me, 5)[0], S.UNKNOWN)

    def test_claims_are_hypotheses(self):
        _, me = ready()
        before = S.answer(me, 1)
        me.claim("eres humano")
        self.assertEqual(S.answer(me, 1), before)
        self.assertTrue(all(not s.has_fact for s in me.cam.slot if s.occupied and s.source == S.SOURCE_TESTIMONY))

    def test_detects_other_process_and_version(self):
        _, me = ready()
        old = me.export()
        s = T.TribeSession(6)
        new = S.SelfKnowledge(s.agents[T.ECHO].cam)
        moved = [dict(r) for r in old]
        for r in moved:
            if r["code"] == "process":
                r["value"] = {"pid": r["value"]["pid"] + 1}
        new.load_history(moved)
        new.observe(S.sense(s.agents))
        self.assertEqual(S.answer(new, 9, history_end=len(moved))[1]["verdict"], "same_program_other_process")
        other = [dict(r) for r in moved]
        for r in other:
            if r["code"] == "program":
                r["value"] = dict(r["value"], sha256="0" * 64)
        v = S.SelfKnowledge(T.TribeSession(7).agents[T.ECHO].cam)
        v.load_history(other)
        v.observe(S.sense())
        self.assertEqual(S.answer(v, 9, history_end=len(other))[1]["verdict"], "other_version")

    def test_corrupt_fact_and_stop(self):
        _, me = ready()
        slot = me.cam.get(me._key(0))
        me.cam.slot[slot].extract += " "
        with self.assertRaises(ValueError):
            S.answer(me, 2)
        _, me2 = ready()
        me2.stop()
        with self.assertRaises(RuntimeError):
            S.answer(me2, 1)

    def test_host_only_as_fingerprint_and_render_is_labelled(self):
        import platform
        _, me = ready()
        self.assertNotIn(platform.node(), repr(me.export()))
        status, value = S.answer(me, 3)
        self.assertTrue(S.render(3, status, value).startswith("[representación]"))
        self.assertEqual(S.render(5, S.UNKNOWN, None), "[representación] No lo sé: no tengo evidencia.")


if __name__ == "__main__":
    unittest.main()
