"""MEMORIA-X (ECHO-5.8 track A) invariants.

    cd /home/user/REALRXOS/RXos && PYTHONPATH=. python3 -m echoai.tests.test_echo58_memx
"""
import ast
import json
import tempfile
import unittest
from pathlib import Path

from echoai.echo58.memx import bench
from echoai.echo58.memx.agent import Marginal, signature
from echoai.echo58.memx.memory import Memory
from echoai.echo58.memx.world import SECRET_A1, UNIVERSE, bijection, episode_seed

PKG = Path(__file__).resolve().parents[1] / "echo58" / "memx"
NAMES = ("lava", "door",   # GOAL/HURT/... are consequence classes, not things
         "key", "ball", "box", "wall", "water", "minigrid", "gymnasium",
         "ai_safety", "OBJECT_TO_IDX", "COLOR_TO_IDX")


class NoNames(unittest.TestCase):
    def test_agent_and_memory_never_see_names(self):
        """No string constant or import in the agent/memory names a thing in the world."""
        import re
        for name in ("agent.py", "memory.py"):
            tree = ast.parse((PKG / name).read_text())
            words = set()
            docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
            for n in ast.walk(tree):
                if id(n) in docs:
                    continue
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    words.update(re.findall(r"[a-z_]+", n.value.lower()))
                elif isinstance(n, ast.Import):
                    words.update(a.name.lower() for a in n.names)
                elif isinstance(n, ast.ImportFrom):
                    words.add((n.module or "").lower())
                    words.update(a.name.lower() for a in n.names)
            for word in NAMES:
                self.assertNotIn(word.lower(), words, f"{name} mentions {word}")

    def test_no_floats_in_fast_path(self):
        for name in ("agent.py", "memory.py"):
            tree = ast.parse((PKG / name).read_text())
            for n in ast.walk(tree):
                self.assertFalse(isinstance(n, ast.Constant) and isinstance(n.value, float), f"float literal in {name}")
                self.assertFalse(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div), f"true division in {name}")


class Ids(unittest.TestCase):
    def test_a1_fixed_a2_per_episode(self):
        a = bijection(SECRET_A1)
        self.assertEqual(a, bijection(SECRET_A1))
        self.assertEqual(len(set(a.values())), len(UNIVERSE))
        self.assertTrue(all(1 <= v <= 255 for v in a.values()))
        self.assertNotEqual(bijection(episode_seed("DynObs16", 900000)), bijection(episode_seed("DynObs16", 900001)))


class Rules(unittest.TestCase):
    def test_lower_bound_and_contradiction(self):
        m = Memory(3, 85)
        for _ in range(2):
            m.observe(7, 5, "ENTER", 0, "HURT")
        self.assertIsNone(m.recall(7, 5, "ENTER", 0))          # 2 < n_min
        m.observe(7, 5, "ENTER", 0, "HURT")
        self.assertEqual(m.recall(7, 5, "ENTER", 0), "HURT")
        m.observe(7, 5, "ENTER", 0, "PASS")                     # 3/4 = 75 % < 85 %
        self.assertIsNone(m.recall(7, 5, "ENTER", 0))
        self.assertEqual(len(m.records), 4)                     # nothing erased
        self.assertEqual(m.destroyed, 0)

    def test_layer2_answers_unseen_ids(self):
        m = Memory(3, 85)
        for i in (10, 11, 12):
            m.observe(i, 17, "ENTER", 0, "HURT")
        self.assertEqual(m.recall(99, 17, "ENTER", 0), "HURT")  # new id, same signature
        self.assertIsNone(m.recall(99, 18, "ENTER", 0))

    def test_shuffle_keeps_entries(self):
        m = Memory()
        for i, s in ((1, 2), (3, 4), (5, 6), (1, 2)):
            m.observe(i, s, "ENTER", 0, "NOOP")
        sh = m.shuffled(1)
        self.assertEqual(sorted(map(sum, m.l1.values())), sorted(map(sum, sh.l1.values())))
        self.assertEqual(sorted(map(sum, m.l2.values())), sorted(map(sum, sh.l2.values())))

    def test_shuffled_layer1_keys_stay_reachable(self):
        """Every permuted layer-1 key is size-free, so recall can still find it."""
        m = Memory()
        for i, s in ((1, 2 | 4), (3, 8 | 1), (5, 16 | 12)):
            for _ in range(3):
                m.observe(i, s, "ENTER", 0, "HURT")
        sh = m.shuffled(7)
        for (i, s, a, h) in sh.l1:
            self.assertEqual(s & 0b1100, 0)
            self.assertEqual(sh.recall(i, s, a, h), "HURT")

    def test_without_auto_drops_only_moving_things(self):
        m = Memory()
        for _ in range(3):
            m.observe(1, 16 | 4, "ENTER", 0, "HURT")
            m.observe(2, 1, "ENTER", 0, "NOOP")
        na = m.without_auto()
        self.assertIsNone(na.recall(9, 16 | 8, "ENTER", 0))
        self.assertEqual(m.recall(9, 16 | 8, "ENTER", 0), "HURT")   # layer 2 ignores size of moving things
        self.assertEqual(na.recall(2, 1, "ENTER", 0), "NOOP")

    def test_postcards_are_16_bytes(self):
        m = Memory()
        for _ in range(4):
            m.observe(1, 21, "ENTER", 0, "HURT")
        cards = list(m.postcards())
        self.assertTrue(cards)
        self.assertTrue(all(len(c) == 16 for c in cards))


class Disk(unittest.TestCase):
    def test_roundtrip_append_only_and_tamper(self):
        m = Memory()
        for k in range(5):
            m.observe(k, k, "PICK", 0, "PICK")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.jsonl"
            head = m.save(p)
            self.assertEqual(Memory.load(p).head, head)
            with self.assertRaises(FileExistsError):
                m.save(p)
            lines = p.read_text().splitlines()
            r = json.loads(lines[2])
            r["o"] = "HURT"
            lines[2] = json.dumps(r, sort_keys=True)
            p.write_text("\n".join(lines) + "\n")
            with self.assertRaises(ValueError):
                Memory.load(p)


class Marginals(unittest.TestCase):
    def test_marginal_matches_frequency_not_keys(self):
        mg = Marginal({"HURT": 250, "NOOP": 250}, seed=3)
        ans = [mg.recall(i, 0, "ENTER", 0) for i in range(4000)]
        self.assertAlmostEqual(ans.count("HURT") / 4000, 0.25, delta=0.03)
        self.assertAlmostEqual(ans.count(None) / 4000, 0.5, delta=0.03)

    def test_marginal_only_vetoes_and_changes_per_episode(self):
        a = Marginal({"HURT": 300, "NOOP": 300, "GOAL": 400}, seed=1)
        b = Marginal({"HURT": 300, "NOOP": 300}, seed=2)
        ans_a = [a.recall(i, 0, "ENTER", 0) for i in range(500)]
        self.assertTrue(set(ans_a) <= {"HURT", "NOOP", None})
        self.assertNotEqual(ans_a, [b.recall(i, 0, "ENTER", 0) for i in range(500)])

    def test_frozen_freq_is_veto_only(self):
        freq = json.loads((bench.LAB / "marginal-freq.json").read_text())
        self.assertEqual(sorted(freq), sorted(str(m) for m in bench.MACROS))
        self.assertTrue(all(set(v) == {"HURT", "NOOP"} for v in freq.values()))


class Report(unittest.TestCase):
    def test_evaluate_runs_on_every_arm_and_splits_harm(self):
        """Synthetic exam: aprendida never harmed, every other arm always; P1 and P3 pass."""
        from echoai.echo58.memx import report
        from echoai.echo58.memx.agent import RandomAgent
        from echoai.echo58.memx.world import make_world
        keys = ("success", "harm", "harm_probe", "harm_auto", "harm_other", "wasted", "steps")
        try:
            rnd = RandomAgent(0).run(make_world("DoorKey6", 1, "A1"), max_steps=50)
            self.assertTrue(all(k in rnd for k in keys))
        except ImportError:                     # system python has no MiniGrid; the sandbox venv checks it
            pass
        eps = []
        for m in bench.MACROS:
            for arm in bench.ARMS:
                for regime in ("A1", "A2"):
                    for f in bench.EXAM:
                        for i in range(3):
                            bad = arm != "aprendida" and arm != "techo"
                            eps.append({"arm": arm, "macro": m, "regime": regime, "family": f,
                                        "success": int(not bad), "harm": int(bad), "harm_probe": int(bad),
                                        "harm_auto": 0, "harm_other": 0, "wasted": 2 * bad, "steps": 10})
        res = report.evaluate(eps)
        self.assertTrue(res["P1"]["pass"] and res["P2"]["pass"] and res["P3"]["pass"] and res["green"])
        self.assertIn("A1|ShiftTest|aleatorio", res["table"])


class Stats(unittest.TestCase):
    def test_wilcoxon_exact(self):
        self.assertAlmostEqual(bench.wilcoxon_greater([1] * 10), 1 / 1024)
        self.assertEqual(bench.wilcoxon_greater([0] * 10), 1.0)
        self.assertGreater(bench.wilcoxon_greater([1, -1] * 5), 0.4)

    def test_signature_buckets(self):
        self.assertEqual(signature(1, {1: 1}, {}, set()), 0)
        self.assertEqual(signature(1, {1: 20}, {1: 20}, {1}), 16 + 12 + 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
