"""ENJAMBRE-1 (ECHO-5.8 track C v1) invariants.

    cd /home/roger/REALRXOS/RXos && PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.tests.test_echo58_enjambre
"""
import ast
import unittest
from pathlib import Path

from echoai.echo58.enjambre import bench as B
from echoai.echo58.enjambre import coop as C
from echoai.echo58.enjambre.cagent import CAgent
from echoai.echo58.enjambre.report import evaluate
from echoai.echo58.enjambre.team import L1, L2, RM, Board, Private, Reader, card, read

ROOT = Path(__file__).resolve().parents[1] / "echo58" / "enjambre"
IDS = C.language()


def solo(kind, seed, p):
    cw = C.CoopWorld(kind, seed, 1, IDS)
    x = C.play_together(cw, [CAgent(source=Reader(p.mem.cfg, p, None, {}, world=0), learn=p, private=p)])[0]
    return cw, x


class Invariants(unittest.TestCase):
    def test_no_floats_in_memory_and_agent(self):
        for name in ("team.py", "cagent.py", "coop.py"):
            for n in ast.walk(ast.parse((ROOT / name).read_text())):
                self.assertFalse(isinstance(n, ast.Constant) and isinstance(n.value, float), name)
                self.assertFalse(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div), name)

    def test_postcards_are_16_bytes_and_round_trip(self):
        for layer, key in ((L2, (21, "ENTER", 0)), (L1, (77, 3, "TOGGLE", 12)), (RM, (40, 91))):
            raw = card(layer, 2, key, [5, 0, 1, 0, 0, 0] if layer != RM else [3, 4])
            self.assertEqual(len(raw), 16)
            got = read(raw)
            self.assertEqual((got[0], got[1], got[2]), (layer, 2, key))

    def test_board_keeps_latest_per_sender(self):
        b = Board()
        b.post(card(L2, 0, (21, "ENTER", 0), [3, 0, 0, 0, 0, 0]))
        b.post(card(L2, 0, (21, "ENTER", 0), [4, 0, 0, 0, 0, 0]))     # resend: replaces, adds nothing
        b.post(card(L2, 1, (21, "ENTER", 0), [2, 0, 0, 0, 0, 0]))
        self.assertEqual(sum(b.view()[(L2, (21, "ENTER", 0))]), 6)
        self.assertEqual(len(b.log), 3)
        self.assertEqual(b.destroyed, 0)

    def test_shuffled_view_same_entries_other_keys(self):
        b = Board()
        for i, s in enumerate((5, 9, 17)):
            b.post(card(L2, 0, (s, "ENTER", 0), [i + 1, 0, 0, 0, 0, 0]))
        for i, k in enumerate(((10, 11), (12, 13))):
            b.post(card(RM, 0, k, [i + 2, 9]))
        v, s = b.view(), b.view(shuffle_seed=3)
        self.assertEqual(sorted(map(tuple, v.values())), sorted(map(tuple, s.values())))
        self.assertNotEqual(v, s)

    def test_plate_world_needs_two(self):
        seed = B.mission("dev", 1)[[w["kind"] for w in B.mission("dev", 1)].index("plate")]["seed"]
        p = Private()
        p.world = 0
        for _ in range(3):
            cw, _ = solo("plate", seed, p)
            self.assertIsNone(cw.solved_by)                 # alone the gate never stays open
        self.assertTrue(cw.needs_help)                       # it learnt how, and said it was alone
        p2 = Private()
        p2.world = 0
        cw = C.CoopWorld("plate", seed, 2, IDS)
        xs = C.play_together(cw, [CAgent(source=Reader(q.mem.cfg, q, None, {}, world=0), learn=q, me=i, private=q)
                                  for i, q in enumerate((p, p2))])
        self.assertIsNotNone(cw.solved_by)
        self.assertGreater(xs[0]["asked"] + xs[1]["asked"], 0)

    def test_local_tile_burns_only_in_local_worlds(self):
        for kind in C.KINDS:
            L = C.layout(kind, 9_100_123)
            self.assertEqual(L["hot"], {C.TILE} if kind == "local" else set())
            self.assertTrue(any(C.TILE in row for row in L["cells"]))

    def test_every_layout_has_a_way_out_and_plates_need_two(self):
        for seed in range(9_100_000, 9_100_400):
            for kind in C.KINDS:
                L = C.layout(kind, seed)
                self.assertGreaterEqual(len(L["starts"]), 4, (kind, seed))
                c, gap = L["gate"]
                self.assertNotIn(L["cells"][gap][c - 1], (C.TILE, C.PLATE), (kind, seed))
                self.assertNotIn(L["cells"][gap][c + 1], (C.TILE, C.PLATE), (kind, seed))

    def test_reader_asks_here_first(self):
        p = Private()
        p.world = 4
        for _ in range(3):
            p.observe(50, 0, "ENTER", 0, "HURT")
        glob = {(L1, p.mem.cfg.l1_key(50, 0, "ENTER", 0)): [9, 0, 0, 0, 0, 0, 0]}
        rd = Reader(p.mem.cfg, p, glob, {}, world=4)
        self.assertEqual(rd.recall(50, 0, "ENTER", 0), "HURT")
        self.assertEqual(rd.by_source["here"], 1)
        rd = Reader(p.mem.cfg, None, glob, {}, world=4)          # sin_privada: only the global answers
        self.assertEqual(rd.recall(50, 0, "ENTER", 0), "PASS")

    def test_exam_missions_fresh(self):
        dev = {w["seed"] for m in B.MACROS for w in B.mission("dev", m)}
        exam = {w["seed"] for m in B.MACROS for w in B.mission("exam", m)}
        self.assertFalse(dev & exam)
        self.assertTrue(all(9_500_000 <= s < 9_600_000 for s in exam))
        self.assertTrue(all(9_100_000 <= s < 9_200_000 for s in dev))
        for m in B.MACROS:
            kinds = [w["kind"] for w in B.mission("exam", m)]
            self.assertEqual(sorted(kinds), sorted(C.KINDS * 2))

    def test_report_on_synthetic_runs(self):
        def run(arm, m, score, failed):
            ws = [{"kind": k, "seed": i} for i, k in enumerate(C.KINDS * 2)]
            x = {"arm": arm, "macro": m, "worlds": ws, "solved_round": [score // 8] * 8, "score": score,
                 "solved": 8, "failed": failed, "harm": 0, "destroyed": 0, "card_bytes": [16], "episodes": 9,
                 "postcards": 1, "notes_cards": 0, "helps": 0, "asked": 0, "held": 0,
                 "answers": {"here": 0, "private": 0, "notes": 0, "global": 0},
                 "by_kind": {k: {"harm": 0, "episodes": 1} for k in C.KINDS}}
            return x
        runs = {a: {m: run(a, m, 40 if a == "enjambre" else 80 + m, 10 if a == "enjambre" else 20 + m)
                    for m in B.MACROS} for a in B.ARMS if a != "uno_solo"}
        runs["uno_solo"] = {m: {"solved": 1, "episodes": 120, "failed": 119, "harm": 0, "destroyed": 0} for m in B.MACROS}
        res = evaluate(runs)
        self.assertTrue(res["E1"] and res["E2"] and res["E3"] and res["E4"])
        self.assertTrue(res["green"])

    def test_frozen_state_is_stable(self):
        a, b = B.frozen_state(), B.frozen_state()
        self.assertEqual(a, b)
        self.assertIn("enjambre", a)
        self.assertIn("b3_policy", a)


if __name__ == "__main__":
    unittest.main()
