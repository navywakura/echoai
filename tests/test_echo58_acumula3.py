"""ACUMULA-3 (ECHO-5.8 track B v3) invariants.

    cd /home/user/REALRXOS/RXos && PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.tests.test_echo58_acumula3
"""
import ast
import re
import unittest
from collections import Counter
from pathlib import Path

from echoai.echo58.acumula import bench as B1
from echoai.echo58.acumula2 import bench as B2
from echoai.echo58.acumula3 import bench as B3
from echoai.echo58.acumula3.report import evaluate
from echoai.echo58.b3.policy import PIECES, SIGNAL_PIECE, PAgent

ROOT = Path(__file__).resolve().parents[1] / "echo58"
NAMES = ("lava", "door", "key", "ball", "box", "wall", "water", "minigrid", "gymnasium", "ai_safety")


class Invariants(unittest.TestCase):
    def test_policy_has_no_names_no_floats(self):
        tree = ast.parse((ROOT / "b3" / "policy.py").read_text())
        docs = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}
        for n in ast.walk(tree):
            self.assertFalse(isinstance(n, ast.Constant) and isinstance(n.value, float))
            self.assertFalse(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
                for w in NAMES:
                    self.assertNotIn(w, re.findall(r"[a-z_]+", n.value.lower()), w)

    def test_pconfig(self):
        c = B3.PConfig().apply(("order",)).apply(("piece", ("commit", "no_repick")))
        self.assertIsInstance(c, B3.PConfig)
        self.assertEqual(c.pieces, frozenset({"commit", "no_repick"}))
        self.assertTrue(c.l2_first)
        self.assertFalse(c.valid(("piece", ("commit",))))
        self.assertTrue(c.valid(("piece", ("clear",))))
        self.assertEqual(c.copy().pieces, c.pieces)
        self.assertEqual(B3.PConfig().pieces, frozenset())

    def test_piece_candidates_follow_signals(self):
        got = B3.piece_candidates(Counter({"pickdrop": 3, "retoggle": 1}), B3.PConfig())
        self.assertEqual(got, [("piece", ("commit",)), ("piece", ("commit", "no_repick")), ("piece", ("no_retoggle",))])
        self.assertEqual(B3.piece_candidates(Counter(), B3.PConfig()), [])
        self.assertEqual(set(SIGNAL_PIECE.values()) | {"no_repick"}, set(PIECES))
        self.assertEqual(len(B3.piece_menu(B3.PConfig())), len(PIECES) + len(B3.PAIRS))

    def test_exam_seeds_fresh_and_disjoint(self):
        exam = set()
        for m in B3.MACROS:
            s = B3.seeds("exam", m)
            exam |= {x for r in s["round"].values() for x in r} | {x for r in s["val"].values() for x in r}
            exam |= set(s["probe"]) | set(s["q3"])
        self.assertTrue(all(8_000_000 <= x < 9_100_000 for x in exam))
        for m in B3.MACROS:
            for old in (B1.seeds("dev", m), B1.seeds("exam", m), B2.seeds("dev", m), B2.seeds("exam", m),
                        B3.seeds("dev", m)):
                olds = {x for r in old["round"].values() for x in r} | {x for r in old["val"].values() for x in r}
                olds |= set(old["probe"]) | set(old.get("q3", []))
                self.assertFalse(exam & olds)

    def test_exam_probe_unseen(self):
        exam = set(B3.PROBE["exam"])
        self.assertFalse(exam & set(B3.PROBE["dev"]))
        self.assertFalse(exam & set(B3.MIX))
        self.assertFalse(exam & {"ObstructedMaze2Dl", "DynObsRandom6", "ObstructedMaze1Dlh"})   # traced in dev
        for f in exam | set(B3.PROBE["dev"]):
            self.assertIn(f, B3.W.MINIGRID)

    def test_agent_plays_and_reports_signals(self):
        mem = B1.start_memory(1).reconfigure(B3.PConfig())
        r = B3.play(B3.agent(mem), "KeyCorridorS3R2", 5_000_001)
        self.assertIn("signals", r)
        self.assertIsInstance(B3.agent(mem), PAgent)
        self.assertEqual(mem.destroyed, 0)

    def test_report_on_synthetic_runs(self):
        def run(arm, m, curve):
            pr = {str(r): {"F": {"failed": f, "harm": 0, "success": 30 - f}} for r, f in enumerate(curve)}
            x = {"arm": arm, "macro": m, "probe": pr, "rounds": [{"round": 1, "accepted": []}],
                 "late_after_reject": [], "destroyed": 0}
            if arm == "recursiva":
                x["q3"] = {k: {"A": {"harm": 0, "success": 5}} for k in ("base", "final")}
            return x
        runs = {a: {m: run(a, m, [30, 20, 10, 5, 3, 3] if a == "recursiva" else [30] * 6) for m in B3.MACROS}
                for a in ("recursiva", "azar", "sin_acumular", "fija", "lote_final", "vacia_online", "piezas_dadas")}
        res = evaluate(runs)
        self.assertTrue(res["Q1"]["pass"])
        self.assertTrue(res["Q2"]["pass"])
        self.assertTrue(res["green"])

    def test_frozen_state_is_stable(self):
        a, b = B3.frozen_state(), B3.frozen_state()
        self.assertEqual(a, b)
        self.assertIn("b3_policy", a)
        self.assertIn("acumula3", a)


if __name__ == "__main__":
    unittest.main()
