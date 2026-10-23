"""ACUMULA (ECHO-5.8 track B) invariants.

    cd /home/user/REALRXOS/RXos && PYTHONPATH=. python3 -m echoai.tests.test_echo58_acumula
"""
import ast
import re
import unittest
from pathlib import Path

from echoai.echo58.acumula.config import RANK0, RANK1, Config, ConfMemory, rule
from echoai.echo58.acumula.diagnose import best_split, candidates, menu
from echoai.echo58.memx.memory import Memory

PKG = Path(__file__).resolve().parents[1] / "echo58" / "acumula"
NAMES = ("lava", "door", "key", "ball", "box", "wall", "water", "minigrid", "gymnasium", "ai_safety")


def feed(mem, rows):
    for r in rows:
        mem.observe(*r)


class Invariants(unittest.TestCase):
    def test_no_names_no_floats(self):
        for name in ("agent.py", "config.py", "diagnose.py"):
            tree = ast.parse((PKG / name).read_text())
            docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
            for n in ast.walk(tree):
                self.assertFalse(isinstance(n, ast.Constant) and isinstance(n.value, float), name)
                self.assertFalse(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div), name)
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                    for w in NAMES:
                        self.assertNotIn(w, re.findall(r"[a-z_]+", n.value.lower()), f"{name}: {w}")

    def test_base_config_reads_like_track_a(self):
        a, b = Memory(), ConfMemory(Config(), Memory())
        rows = [(7, 4 | RANK1, "ENTER", 0, "HURT")] * 3 + [(9, 16 | 8 | RANK0, "ENTER", 0, "HURT")] * 3
        for i, s, act, h, o in rows:
            a.observe(i, s & 31, act, h, o)
            b.observe(i, s, act, h, o)
        self.assertEqual(a.l1, b.l1)
        self.assertEqual(a.l2, b.l2)
        for i, s, act, h, _ in rows + [(50, 4 | RANK0, "ENTER", 0, None), (51, 16 | RANK1, "ENTER", 0, None)]:
            self.assertEqual(a.recall(i, s & 31, act, h), b.recall(i, s, act, h))


class Edits(unittest.TestCase):
    def setUp(self):
        self.mem = ConfMemory(Config(), Memory())
        feed(self.mem, [(1, 4 | RANK1, "ENTER", 0, "HURT")] * 4 + [(2, 4, "ENTER", 0, "PASS")] * 4)

    def test_refine_separates_and_keeps_observations(self):
        self.assertIsNone(self.mem.recall(99, 4 | RANK1, "ENTER", 0))      # mixed: no rule
        cfg = Config().apply(("refine", (4, "ENTER", 0), RANK1))
        m2 = self.mem.reconfigure(cfg)
        self.assertEqual(m2.recall(99, 4 | RANK1, "ENTER", 0), "HURT")
        self.assertEqual(m2.recall(98, 4, "ENTER", 0), "PASS")
        self.assertEqual(len(m2.raw), 8)
        self.assertEqual(m2.chain.head, self.mem.chain.head)
        self.assertEqual(m2.destroyed, 0)

    def test_best_split_finds_the_separating_bit(self):
        self.assertEqual(best_split((4, "ENTER", 0), Config(), self.mem.raw), RANK1)

    def test_silence_and_verify(self):
        feed(self.mem, [(3, 8, "ENTER", 0, "PASS")] * 4 + [(4, 12, "ENTER", 0, "HURT")] * 4)
        c = Config().apply(("silence", (8, "ENTER", 0))).apply(("verify", (12, "ENTER", 0)))
        m2 = self.mem.reconfigure(c)
        self.assertIsNone(m2.recall(70, 8, "ENTER", 0))
        self.assertEqual(m2.recall(71, 12, "ENTER", 0), "HURT")         # verify keeps warnings

    def test_candidates_come_from_blamed_keys(self):
        fails = [(2, (4, "ENTER", 0), "HURT")] * 3
        c = candidates(fails, Config(), self.mem.raw)
        self.assertEqual(c[0], ("refine", (4, "ENTER", 0), RANK1))
        self.assertTrue(all(e[0] != "order" for e in c))
        self.assertEqual(candidates([], Config(), self.mem.raw), [])

    def test_menu_only_valid_and_unique(self):
        cfg = Config().apply(("silence", (4, "ENTER", 0)))
        full = menu(cfg, self.mem.l2)
        self.assertEqual(len(full), len(set(full)))
        self.assertNotIn(("silence", (4, "ENTER", 0)), full)
        self.assertTrue(all(cfg.valid(e) for e in full))

    def test_surprises_are_prediction_errors(self):
        self.mem.surprises = []
        feed(self.mem, [(5, 12, "ENTER", 0, "PASS")] * 3)
        self.mem.observe(6, 12, "ENTER", 0, "HURT")
        self.assertEqual(self.mem.surprises, [(2, (12, "ENTER", 0), "HURT")])

    def test_probe_copy_is_isolated(self):
        cp = self.mem.probe_copy()
        cp.observe(1, 4, "ENTER", 0, "GOAL")
        self.assertEqual(len(self.mem.raw), 8)
        self.assertIsNone(cp.chain)


class Rules(unittest.TestCase):
    def test_rule_matches_track_a(self):
        m = Memory()
        for counts in ([3, 0, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0], [0, 2, 2, 0, 0, 0], [5, 1, 0, 0, 0, 0], [3, 0, 1, 0, 0, 0]):
            self.assertEqual(rule(counts, 3, 85), m._rule(counts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
