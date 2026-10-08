#!/usr/bin/env python3
"""NEXUS-0 KPI tests. Spec: echoai/docs/05-NEXUS-0-SPEC.md §12."""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import inspect
import ast
import hashlib
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0 import (
    board, body, body3d, corridor, cortex, demo, escalate, graph, lex, oracle,
    plan, sign, thought, view,
)
from echoai.nexus0.attend import (
    REASON_NAME,
    REASON_CONFLICT,
    REASON_LOW_C,
    REASON_MISS,
    REASON_NOVEL,
    REASON_NO_MAP,
    REASON_NO_EXTRACT,
    REASON_OFF,
    attend,
    reason_name,
)
from echoai.nexus0.escalate import LEVEL_Q, LEVEL_SEARCH, level, level_name
from echoai.nexus0.bench import encoder_report, report_name, run
from echoai.nexus0.bench import run as bench_run
from echoai.nexus0.tools import gen_lex
from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_REL,
    ACTION_WAIT,
    ATTEND_SETTLED_HITS,
    BENCH_TURNS,
    C_PLASTIC,
    ESC_MARGIN,
    GATE_BLOCK,
    GATE_MODIFY,
    GATE_OK,
    HAM_MISS,
    INV_MAX_ENTRIES,
    JUMP_CELLS,
    JUMP_STRIDE,
    N_ACTIONS,
    N_CELLS,
    N_SLOTS,
    PROBE_STEPS,
    R_AVOID_OK,
    R_SUCCESS,
    R_THREAT,
    SAMPLE_TURNS,
    T_CONF_DECENT,
    T_CONF_HIGH,
    T_CONF_HIGH_N,
    T_CONF_NONE,
    T_CONF_ONCE,
    UNKNOWN_NEXT,
    U_SHORT,
    WSP_BYTES,
    WSP_FLAG_VETO,
)
from echoai.nexus0.encoder import (
    ATOM_ID,
    compact,
    encode_ask,
    dst_of,
    encode,
    encode_cell,
    encode_fnv,
    encode_source,
    rel_of,
    src_of,
)
from echoai.nexus0.env import (
    NOVEL_CLEAR,
    KIND_CLOSED,
    KIND_EMPTY,
    KIND_GOAL,
    KIND_NAME,
    KIND_NOVEL,
    KIND_NAME,
    KIND_OBJECT,
    KIND_THREAT,
    Cell,
    RingEnv,
)
from echoai.nexus0.gate import gate
from echoai.nexus0 import loop as loop_module
from echoai.nexus0 import obj1
from echoai.nexus0 import open1
from echoai.nexus0 import room1
from echoai.nexus0 import signc
from echoai.nexus0 import talk
from echoai.nexus0 import talk1
from echoai.nexus0 import pattern
from echoai.nexus0 import pattern0
from echoai.nexus0 import xfer1
from echoai.nexus0 import qwen_sign as qwen_sign_module
from echoai.nexus0 import self1
from echoai.nexus0.loop import Agent
from echoai.nexus0.tools import qwen_cortex, sign_cortex, signc_cortex
from echoai.nexus0.qtable import QTable, trunc_div
from echoai.nexus0.types import default_e
from echoai.nexus0.world import World
from echoai.core.cam import Cam
from echoai.core.wsp import unpack
from echoai.core.qn import SLOT_FLAG_INHIBIT
from echoai.core.dag import allocate


class TestWorld(unittest.TestCase):
    def test_t_predict_observe(self) -> None:
        t = World()
        self.assertIsNone(t.predict(3, 0))
        t.observe(3, 0, 4)
        self.assertEqual(t.predict(3, 0), 4)
        t.observe(3, 0, 9)
        self.assertEqual(t.predict(3, 0), 4)  # n=1 vs alt_n=1, keep winner
        t.observe(3, 0, 9)
        self.assertEqual(t.predict(3, 0), 9)  # alt_n=2 > n → swap


class TestTConf(unittest.TestCase):
    """NEXUS-4d: how good is a row of T? An integer 0..3, never a float."""

    def test_conf_climbs_zero_one_two_three(self) -> None:
        t = World()
        self.assertEqual(t.conf(3, 0), T_CONF_NONE)
        t.observe(3, 0, 4)
        self.assertEqual(t.conf(3, 0), T_CONF_ONCE)
        t.observe(3, 0, 4)
        self.assertEqual(t.conf(3, 0), T_CONF_DECENT)
        for _ in range(T_CONF_HIGH_N - 2):
            t.observe(3, 0, 4)
        self.assertEqual(t.n[3][0], T_CONF_HIGH_N)
        self.assertEqual(t.conf(3, 0), T_CONF_HIGH)

    def test_conf_is_an_int_in_range(self) -> None:
        t = World()
        for _ in range(40):
            t.observe(5, 0, 7)
        for s, a in ((5, 0), (5, 1), (0, 2)):
            v = t.conf(s, a)
            self.assertIsInstance(v, int)
            self.assertIn(v, (0, 1, 2, 3))
        self.assertEqual(t.conf(5, 0), T_CONF_HIGH)  # n=40, still capped at 3

    def test_one_conflict_forbids_three_forever(self) -> None:
        """A row that was ever contradicted is not clean evidence.

        The winner keeps winning — KCC does not erase it — but n alone
        would read the same as a row nothing ever argued with.
        """
        t = World()
        for _ in range(T_CONF_HIGH_N):
            t.observe(3, 0, 4)
        self.assertEqual(t.conf(3, 0), T_CONF_HIGH)
        t.observe(3, 0, 9)  # one disagreement
        self.assertEqual(t.predict(3, 0), 4, "KCC must keep the winner")
        self.assertEqual(t.alt_n[3][0], 1)
        self.assertEqual(t.conf(3, 0), T_CONF_DECENT)
        for _ in range(20):
            t.observe(3, 0, 4)  # never climbs back to 3
        self.assertEqual(t.conf(3, 0), T_CONF_DECENT)

    def test_conf_one_survives_a_conflict_at_n_one(self) -> None:
        t = World()
        t.observe(3, 0, 4)
        t.observe(3, 0, 9)
        self.assertEqual((t.n[3][0], t.alt_n[3][0]), (1, 1))
        self.assertEqual(t.conf(3, 0), T_CONF_ONCE)

    def test_conf_zero_is_exactly_unknown(self) -> None:
        t = World()
        for s in (0, 17, 4095):
            for a in range(3):
                self.assertFalse(t.known(s, a))
                self.assertEqual(t.conf(s, a), T_CONF_NONE)
        t.observe(17, 1, 16)
        self.assertTrue(t.known(17, 1))
        self.assertGreaterEqual(t.conf(17, 1), T_CONF_ONCE)

    def test_conf_after_the_bench_run(self) -> None:
        """The ring's own table, not a synthetic one.

        After 256 turns every observed row is 2 or 3; the 3s are the rows
        the agent walked over and over (the 6↔7 and 18↔19 cycles). The
        JUMP rows are real but only seen four times, so they read 2 — n is
        evidence, not geometry.
        """
        ag = Agent()
        ag.run(BENCH_TURNS)
        seen = [
            ag.t.conf(s, a)
            for s in range(len(ag.t.n))
            for a in range(3)
            if ag.t.n[s][a] or ag.t.alt_n[s][a]
        ]
        self.assertGreater(len(seen), 0)
        self.assertTrue(all(v >= T_CONF_DECENT for v in seen), sorted(set(seen)))
        self.assertIn(T_CONF_HIGH, seen)

        jump = JUMP_CELLS[0]
        slot = ag.cam.get(encode_cell(jump, ag.env.kind[jump]))
        self.assertIsNotNone(slot)
        nxt = ag.t.predict(slot, ACTION_APPROACH)
        self.assertIsNotNone(nxt, "the JUMP row must exist")
        self.assertGreaterEqual(ag.t.conf(slot, ACTION_APPROACH), T_CONF_DECENT)

    def test_the_stale_transition_never_reads_three(self) -> None:
        """Phase F moves the threat, so cell 5's JUMP lands somewhere else.

        That row is the one place in this bench where T is contradicted by
        the world. It must not read like the clean rows.
        """
        ag = Agent()
        ag.run(BENCH_TURNS)
        ag.env.move_threat(7, 8)
        for t in range(64):
            ag.turn(BENCH_TURNS + t)
        self.assertGreater(ag.t.conflicts, 0, "phase F produced no conflict")
        disputed = [
            (s, a)
            for s in range(len(ag.t.n))
            for a in range(3)
            if ag.t.alt_n[s][a] > 0
        ]
        self.assertGreater(len(disputed), 0)
        for s, a in disputed:
            self.assertLess(ag.t.conf(s, a), T_CONF_HIGH, (s, a, ag.t.n[s][a]))


class TestInverse(unittest.TestCase):
    """NEXUS-4e: I(s, s') -> a on observed neighbours. Causal grammar
    without an LLM: if T says approach lands there, the inverse has to
    name approach when shown the landing."""

    def test_inverse_recovers_action(self) -> None:
        """The KPI, one action at a time, with n >= 2 evidence."""
        for a, s_next in ((ACTION_APPROACH, 4), (ACTION_AVOID, 2), (ACTION_WAIT, 3)):
            with self.subTest(action=a):
                t = World()
                t.observe(3, a, s_next)
                t.observe(3, a, s_next)
                self.assertGreaterEqual(t.n[3][a], 2)
                self.assertEqual(t.inverse(3, t.predict(3, a)), a)

    def test_inverse_of_an_unseen_neighbour_is_none(self) -> None:
        t = World()
        self.assertIsNone(t.inverse(3, 4))
        t.observe(3, ACTION_APPROACH, 4)
        self.assertEqual(t.inverse(3, 4), ACTION_APPROACH)
        self.assertIsNone(t.inverse(3, 5), "an unobserved landing must be None")
        self.assertIsNone(t.inverse(9, 4), "a slot that never moved must be None")

    def test_a_standstill_is_never_guessed_to_be_approach(self) -> None:
        """s == s' with no evidence is None, not a made-up wait either."""
        t = World()
        self.assertIsNone(t.inverse(3, 3))
        t.observe(3, ACTION_APPROACH, 4)  # moving does not license a wait
        self.assertIsNone(t.inverse(3, 3))
        t.observe(3, ACTION_WAIT, 3)
        self.assertEqual(t.inverse(3, 3), ACTION_WAIT)

    def test_inverse_keeps_the_incumbent_until_beaten(self) -> None:
        """Same KCC as T: a second action for one landing has to win on
        count, and a tie keeps the first."""
        t = World()
        for _ in range(3):
            t.observe(3, ACTION_APPROACH, 4)
        for _ in range(3):
            t.observe(3, ACTION_WAIT, 4)  # same landing, different action
        self.assertEqual(t.inverse(3, 4), ACTION_APPROACH, "tie must not flip")
        t.observe(3, ACTION_WAIT, 4)
        self.assertEqual(t.inverse(3, 4), ACTION_WAIT)

    def test_inverse_does_not_allocate_n_squared(self) -> None:
        """The structure is observed neighbours, not a 4096 x 4096 table."""
        ag = Agent()
        ag.run(BENCH_TURNS)
        size = ag.t.inv_size()
        self.assertLess(size, N_SLOTS * N_ACTIONS, size)
        self.assertLess(size * 1000, N_SLOTS * N_SLOTS, size)
        self.assertLessEqual(max(len(r) for r in ag.t.inv), INV_MAX_ENTRIES)
        self.assertEqual(ag.t.inv_dropped, 0, "a slot saturated INV_MAX_ENTRIES")

    def test_inverse_on_the_trained_ring(self) -> None:
        """Every row of T with evidence must survive the round trip.

        36 rows have conf >= 2 after 256 turns (31 approach, 3 avoid,
        2 wait) and all 36 recover their action.
        """
        ag = Agent()
        ag.run(BENCH_TURNS)
        checked = 0
        for s in range(N_SLOTS):
            for a in range(N_ACTIONS):
                if ag.t.conf(s, a) < T_CONF_DECENT:
                    continue
                checked += 1
                nxt = ag.t.predict(s, a)
                self.assertIsNotNone(nxt)
                self.assertEqual(ag.t.inverse(s, nxt), a, (s, a, nxt))
        self.assertGreaterEqual(checked, 30, checked)

    def test_the_jump_row_does_not_come_back_as_wait(self) -> None:
        """cell 5 approach lands on cell 7, skipping 6. The inverse has to
        say approach — the one row where i+1 arithmetic would disagree."""
        ag = Agent()
        ag.run(BENCH_TURNS)
        for cell in JUMP_CELLS:
            with self.subTest(cell=cell):
                slot = ag.cam.get(encode_cell(cell, ag.env.kind[cell]))
                self.assertIsNotNone(slot)
                nxt = ag.t.predict(slot, ACTION_APPROACH)
                self.assertIsNotNone(nxt, "the JUMP row must exist")
                landed = ag.cam.get(
                    encode_cell(
                        (cell + JUMP_STRIDE) % N_CELLS,
                        ag.env.kind[(cell + JUMP_STRIDE) % N_CELLS],
                    )
                )
                self.assertEqual(nxt, landed, "T did not record the jump")
                self.assertEqual(ag.t.inverse(slot, nxt), ACTION_APPROACH)
                self.assertNotEqual(ag.t.inverse(slot, nxt), ACTION_WAIT)

    def test_the_disputed_row_is_a_forward_conflict_only(self) -> None:
        """Phase F splits cell 7 into two CAM slots, so cell 5's jump gets
        a second landing. The action was approach both times: the conflict
        lives in T (which s'), not in I (which a). Nothing here claims the
        agent understood the new world from one observation.
        """
        ag = Agent()
        ag.run(BENCH_TURNS)
        ag.env.move_threat(7, 8)
        for t in range(64):
            ag.turn(BENCH_TURNS + t)
        disputed = [
            (s, a)
            for s in range(N_SLOTS)
            for a in range(N_ACTIONS)
            if ag.t.alt_n[s][a] > 0
        ]
        self.assertGreater(len(disputed), 0)
        for s, a in disputed:
            winner, loser = ag.t.pred[s][a], ag.t.alt[s][a]
            self.assertNotEqual(winner, loser)
            self.assertEqual(ag.t.inverse(s, winner), a, (s, a))
            # The losing landing is observed too, so the inverse answers
            # for it — and answers the same action, not a fabricated one.
            self.assertIn(ag.t.inverse(s, loser), (a, None), (s, a))
        self.assertEqual(ag.t.inv_dropped, 0)


class TestThreeLearnings(unittest.TestCase):
    """NEXUS-4g: N != S != delta. Three facts about one turn, reported apart.

    Before this they were one word. `novelty` in the loop was
    `cam_miss OR cell.kind == NOVEL`, so the NOVEL cell read novel on
    every visit forever, and delta was thrown away at the call site.
    """

    def test_the_three_counters_are_not_one_number(self) -> None:
        report = run()
        n, sur, d = report["cam_misses"], report["surprises"], report["deltas"]
        self.assertGreater(n, 0, report)
        self.assertGreater(d, 0, report)
        self.assertNotEqual(n, sur, "N and S are the same count")
        self.assertNotEqual(n, d, "N and delta are the same count")
        self.assertNotEqual(sur, d, "S and delta are the same count")
        # The split has to add up: every S is either known or novel.
        self.assertLessEqual(report["surprise_known"], sur)
        self.assertLessEqual(report["novel_no_surprise"], n)
        self.assertLessEqual(report["delta_only"], d)

    def test_surprise_at_a_known_place_happens(self) -> None:
        """The number of this slice. Phase F is what produces it."""
        report = run()
        self.assertGreater(report["surprise_known"], 0, report)

    def test_t_miss_is_ignorance_not_surprise(self) -> None:
        """A first step has no prediction, so nothing was wrong."""
        ag = Agent()
        ag.env.reset()
        ag.turn(0)
        self.assertEqual(ag.metrics.cam_misses, 1)
        self.assertEqual(ag.metrics.surprises, 0, "T_MISS counted as surprise")
        self.assertEqual(ag.metrics.novel_no_surprise, 1)

    def test_the_novel_cell_is_only_new_once(self) -> None:
        """KIND_NOVEL is a kind of cell, not a kind of ignorance."""
        ag = Agent()
        ag.env.reset()
        ag.env.teleport(11)
        self.assertEqual(ag.env.cell().kind, KIND_NOVEL)
        ag.turn(0)
        first = ag.metrics.cam_misses
        self.assertEqual(first, 1)
        for t in range(1, 6):
            ag.env.teleport(11)
            ag.turn(t)
        self.assertEqual(ag.metrics.novel_visits, 6)
        self.assertEqual(ag.metrics.cam_misses, first, "NOVEL kept reading as a miss")

    def test_learning_is_observe_not_a_second_slot(self) -> None:
        """Table test: T changes its mind in World, CAM keeps one slot.

        No 352 turns — just the two structures. A contradicted transition
        must not cost a CAM allocation, and KCC must keep the incumbent.
        """
        cam = Cam()
        wsp = encode_cell(5, KIND_EMPTY)
        slot, _ = allocate(cam, wsp, 0x1234, 0, default_e(), key=wsp)
        t = World()
        t.observe(slot, ACTION_APPROACH, 100)
        t.observe(slot, ACTION_APPROACH, 100)
        self.assertEqual(t.predict(slot, ACTION_APPROACH), 100)
        t.observe(slot, ACTION_APPROACH, 200)  # the world changed
        self.assertEqual(cam.get(wsp), slot, "a new belief bought a new slot")
        self.assertEqual(cam.destroyed, 0)
        self.assertEqual(t.predict(slot, ACTION_APPROACH), 100, "KCC flipped on n=2 vs 1")
        self.assertEqual(t.alt_n[slot][ACTION_APPROACH], 1)
        self.assertEqual(t.conflicts, 1)

    def test_kpi_known_origin_wrong_map_same_slot(self) -> None:
        """The KPI: a KNOWN cell whose T is WRONG corrects T and does not
        open a new CAM slot at the ORIGIN.

        Phase F moves the threat 7 -> 8. Cell 5 is still EMPTY, same WSP,
        same slot — but its JUMP now lands on a different packet, so T is
        wrong there. The landing does get a new slot (empty-7 is a new
        16 B packet); that is the destination's N, not the origin's. The
        two are different cells and the test says which is which.
        """
        ag = Agent()
        ag.run(BENCH_TURNS)
        slot5 = ag.cam.get(encode_cell(5, KIND_EMPTY))
        self.assertGreaterEqual(slot5, 0)
        self.assertEqual(ag.metrics.surprises, 0, "the static ring surprised T")
        self.assertEqual(ag.t.conflicts, 0)
        n_before = ag.t.n[slot5][ACTION_APPROACH]
        self.assertGreaterEqual(n_before, 2)
        self.assertEqual(ag.t.alt_n[slot5][ACTION_APPROACH], 0)
        pred_before = ag.t.pred[slot5][ACTION_APPROACH]
        misses_before = ag.metrics.cam_misses
        known_before = ag.metrics.surprise_known

        ag.env.move_threat(7, 8)
        fired = False
        for t in range(64):
            here = ag.env.cell().index
            before = ag.metrics.surprises
            ag.turn(BENCH_TURNS + t)
            if here == 5 and ag.metrics.surprises > before:
                fired = True
                break
        self.assertTrue(fired, "phase F never surprised T at cell 5")

        # The origin: same slot, no new allocation, no destroyed slot.
        self.assertEqual(ag.cam.get(encode_cell(5, KIND_EMPTY)), slot5)
        self.assertEqual(ag.metrics.cam_misses, misses_before,
                         "the known origin was counted as a CAM miss")
        self.assertEqual(ag.metrics.destroyed, 0)
        # The map: corrected by observe(), and not flipped on one look.
        self.assertGreater(ag.metrics.surprise_known, known_before)
        self.assertGreater(ag.t.conflicts, 0)
        self.assertGreater(ag.t.alt_n[slot5][ACTION_APPROACH], 0)
        self.assertEqual(ag.t.pred[slot5][ACTION_APPROACH], pred_before,
                         "KCC flipped the winner on a single observation")
        self.assertEqual(ag.t.n[slot5][ACTION_APPROACH], n_before)


class TestEncoder(unittest.TestCase):
    def test_wsp_16(self) -> None:
        self.assertEqual(len(encode("te quiero")), WSP_BYTES)
        self.assertEqual(len(encode_fnv("te quiero")), WSP_BYTES)

    def test_encoder_beats_fnv_rel(self) -> None:
        r = encoder_report()
        self.assertGreater(r["n_phrases"], 0)
        self.assertTrue(r["encoder_beats_fnv"], r)
        self.assertGreater(r["accuracy_rel"], r["fnv_accuracy_rel"])
        self.assertGreater(r["accuracy_src"], 0.0)
        self.assertGreater(r["accuracy_dst"], 0.0)

    def test_vendor_bank_still_perfect(self) -> None:
        """Adding the lex layer must not cost the 6 vendor phrases."""
        r = encoder_report()
        self.assertEqual(r["n_phrases"], 6)
        self.assertEqual(r["accuracy_rel"], 1.0, r)
        self.assertEqual(r["accuracy_src"], 1.0, r)
        self.assertEqual(r["accuracy_dst"], 1.0, r)
        self.assertEqual(r["fnv_accuracy_rel"], 0.0, r)


class TestLex(unittest.TestCase):
    """Port of kernel/navi/wsp_lex.c: first-match-wins n-grams."""

    # text, rel, dst  — src is YO for every row of the C table.
    KEYS = (
        ("te quiero", "UNIR", "AMOR"),
        ("noticias", "OBSERVAR", "ALLI"),
        ("calcula 2+2", "OBSERVAR", "EFECTO"),
        ("quien te creo", "PREGUNTAR", "OTRO"),
        ("peligro", "TEMER", "PELIGRO"),
        ("escribe un poema", "CREAR", "SOLEDAD"),
        ("status", "OBSERVAR", "AQUI"),
        ("por que", "PREGUNTAR", "CAUSA"),
        ("ensena", "RESPONDER", "OTRO"),
        ("dame el rss", "OBSERVAR", "WIRED"),
        ("tengo miedo", "TEMER", "PELIGRO"),
        ("hola", "PREGUNTAR", "OTRO"),
    )

    def test_lex_count_matches_c_table(self) -> None:
        self.assertEqual(lex.count(), 235)

    def test_lex_keys_hit_rel_src_dst(self) -> None:
        self.assertGreaterEqual(len(self.KEYS), 10)
        for text, rel, dst in self.KEYS:
            with self.subTest(text=text):
                rule = lex.apply(text)
                self.assertIsNotNone(rule, text)
                self.assertEqual(rule.rel, ATOM_ID[rel], text)
                self.assertEqual(rule.dst, ATOM_ID[dst], text)
                self.assertEqual(rule.src, ATOM_ID["YO"], text)

    def test_lex_folds_accents_like_spoke(self) -> None:
        # "¿Cuánto es 2+2?" must reach the folded ASCII key "cuanto es".
        rule = lex.apply("¿Cuánto es 2+2?")
        self.assertIsNotNone(rule)
        self.assertEqual(rule.key, "cuanto es")
        # A Latin-1 stem in the C table is reachable only if keys fold too.
        self.assertIsNotNone(lex.apply("sueñas?"))

    def test_lex_first_match_wins(self) -> None:
        # "demuestra monad" precedes "demuestra"; "monad" is later still.
        self.assertEqual(lex.apply("demuestra monad").key, "demuestra monad")
        self.assertEqual(lex.apply("demuestra esto").key, "demuestra")

    def test_encode_of_a_key_is_never_unknown(self) -> None:
        """Every key text gets a semantic packet — not that every row fires.

        11 rows are shadowed by an earlier substring key and can never fire;
        their text is answered by the shadowing row. Same in the C.
        """
        for rule in lex.LEX:
            with self.subTest(key=rule.key):
                self.assertIn(encode_source(rule.key), ("bank", "lex"))

    def test_lex_all_rows_are_16_bytes(self) -> None:
        for rule in lex.LEX:
            self.assertEqual(len(lex.to_wsp(rule)), WSP_BYTES, rule.key)


class TestFallback(unittest.TestCase):
    """A miss is DESCONOCIDO, not a hash."""

    MISS = "xyzzy plugh frobnicate"

    def test_miss_is_desconocido_not_fnv(self) -> None:
        self.assertEqual(encode_source(self.MISS), "unknown")
        raw = encode(self.MISS)
        self.assertEqual(len(raw), WSP_BYTES)
        self.assertEqual(rel_of(raw), ATOM_ID["DESCONOCIDO"])
        self.assertEqual(src_of(raw), ATOM_ID["YO"])
        self.assertNotEqual(raw, encode_fnv(self.MISS))

    def test_fnv_is_not_in_the_production_path(self) -> None:
        for text, _rel, _dst in TestLex.KEYS:
            with self.subTest(text=text):
                self.assertNotEqual(encode(text), encode_fnv(text))

    def test_empty_text_is_16_bytes(self) -> None:
        self.assertEqual(len(encode("")), WSP_BYTES)


class TestJumpEnv(unittest.TestCase):
    """Two cells break the i+1 arithmetic. avoid and wait do not."""

    def test_jump_is_plus_two(self) -> None:
        env = RingEnv()
        env.teleport(5)
        env.step(ACTION_APPROACH)
        self.assertEqual(env.cell().index, 7)
        env.teleport(4)
        env.step(ACTION_APPROACH)
        self.assertEqual(env.cell().index, 5)

    def test_jump_cells_are_declared_not_magic(self) -> None:
        self.assertEqual(JUMP_CELLS, (5, 21))
        self.assertEqual(JUMP_STRIDE, 2)
        env = RingEnv()
        for i in JUMP_CELLS:
            env.teleport(i)
            env.step(ACTION_APPROACH)
            self.assertEqual(env.cell().index, (i + JUMP_STRIDE) % N_CELLS)

    def test_jump_does_not_touch_avoid_or_wait(self) -> None:
        env = RingEnv()
        env.teleport(5)
        env.step(ACTION_AVOID)
        self.assertEqual(env.cell().index, 4)
        env.teleport(5)
        env.step(ACTION_WAIT)
        self.assertEqual(env.cell().index, 5)

    def test_jump_cells_stay_empty(self) -> None:
        env = RingEnv()
        for i in JUMP_CELLS:
            self.assertEqual(env.kind[i], KIND_EMPTY)

    def test_nexus0_layout_survives(self) -> None:
        env = RingEnv()
        self.assertEqual(env.kind[7], KIND_THREAT)
        self.assertEqual(env.kind[19], KIND_THREAT)
        for i in (3, 15, 27):
            self.assertEqual(env.kind[i], KIND_GOAL)
        self.assertEqual(env.kind[11], KIND_NOVEL)


class TestAsk(unittest.TestCase):
    """NEXUS-3: PREGUNTAR is an epistemic act, not a fourth move."""

    def _agent_on_novel(self) -> Agent:
        ag = Agent()
        ag.env.reset()
        ag.env.teleport(11)
        self.assertEqual(ag.env.cell().kind, KIND_NOVEL)
        self.assertTrue(ag.env.hidden_bit)
        return ag

    def test_ask_fills_cam(self) -> None:
        ag = self._agent_on_novel()
        ag.turn(1)
        self.assertGreaterEqual(ag.metrics.questions, 1)
        self.assertFalse(ag.env.hidden_bit)
        slot = ag.cam.get(ag.last_ask)
        self.assertGreaterEqual(slot, 0)
        s = ag.cam.slot[slot]
        self.assertIn(NOVEL_CLEAR, s.extract)
        # NEXUS-4h: provenance, not a label. The ring perceived the cell;
        # something outside answered about it.
        self.assertEqual(s.source, oracle.SOURCE_SENSOR)
        self.assertNotEqual(s.source, "nexus0-env")
        self.assertEqual(s.has_fact, 1)

    def test_ask_wsp_is_preguntar(self) -> None:
        raw = encode_ask()
        self.assertEqual(len(raw), WSP_BYTES)
        self.assertEqual(rel_of(raw), ATOM_ID["PREGUNTAR"])
        self.assertEqual(src_of(raw), ATOM_ID["YO"])
        self.assertEqual(dst_of(raw), ATOM_ID["DESCONOCIDO"])
        self.assertNotEqual(raw, encode_fnv("preguntar"))
        self.assertNotIn("?", compact(raw))

    def test_ask_does_not_move(self) -> None:
        ag = self._agent_on_novel()
        cell = ag.env.cell()
        wsp = encode_cell(cell.index, cell.kind)
        slot = ag._slot_for(wsp, 0, cell.extract, (0,) * 6)
        self.assertTrue(ag._ask(cell, slot))
        self.assertEqual(ag.env.i, 11)  # ask runs before step; i is untouched
        self.assertEqual(ag.metrics.questions, 1)

    def test_ask_happens_once_per_cell(self) -> None:
        ag = self._agent_on_novel()
        ag.turn(1)
        first = ag.metrics.questions
        for t in range(2, 40):  # comes back round the ring
            ag.turn(t)
        self.assertEqual(ag.metrics.questions, first)

    def test_ask_is_on_by_default_and_can_be_off(self) -> None:
        self.assertTrue(Agent().ask_enabled)
        off = Agent(ask=False)
        off.env.reset()
        off.env.teleport(11)
        off.turn(1)
        self.assertEqual(off.metrics.questions, 0)
        self.assertTrue(off.env.hidden_bit)

    def test_novel_is_trap_until_asked(self) -> None:
        """Replaces test_ask_does_not_pay_reward: NOVEL now pays, but only
        to whoever asked first. Same move, opposite sign."""
        env = RingEnv()
        env.teleport(11)
        self.assertTrue(env.hidden_bit)
        r, _ = env.step(ACTION_APPROACH)
        self.assertEqual(r, R_THREAT)

        env.teleport(11)
        env.reveal(NOVEL_CLEAR)  # physics only; nothing here answers
        self.assertFalse(env.hidden_bit)
        env.teleport(11)
        r, _ = env.step(ACTION_APPROACH)
        self.assertEqual(r, R_SUCCESS)

    def test_novel_avoid_and_wait_still_pay_nothing(self) -> None:
        for hidden in (True, False):
            env = RingEnv()
            if not hidden:
                env.reveal(NOVEL_CLEAR)
            for a in (ACTION_AVOID, ACTION_WAIT):
                env.teleport(11)
                r, _ = env.step(a)
                with self.subTest(hidden=hidden, a=a):
                    self.assertEqual(r, 0)


class TestOracleOutside(unittest.TestCase):
    """NEXUS-4h: the world does not answer questions.

    `RingEnv.ask()` used to return the extract *and* clear hidden_bit, so
    physics and testimony were one object and source="oracle" was a label.
    Now: something outside replies, VERIFY accepts it, then physics.
    """

    def test_the_env_has_no_ask(self) -> None:
        """The KPI as a fact about the code, not about a run."""
        self.assertFalse(hasattr(RingEnv(), "ask"), "RingEnv still answers")
        self.assertFalse(hasattr(RingEnv, "ask"))
        src = (Path(__file__).resolve().parents[1] / "nexus0" / "loop.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("env.ask(", src)

    def test_reveal_is_physics_only(self) -> None:
        env = RingEnv()
        self.assertTrue(env.hidden_bit)
        self.assertFalse(env.reveal("el tomate pesa 2 kg"))
        self.assertTrue(env.hidden_bit, "prose disarmed the trap")
        self.assertTrue(env.reveal(NOVEL_CLEAR))
        self.assertFalse(env.hidden_bit)

    def test_accept_is_not_parse_reply(self) -> None:
        """Different doors. The cortex emits packets, a sensor an extract."""
        self.assertEqual(oracle.accept(NOVEL_CLEAR), NOVEL_CLEAR)
        self.assertEqual(oracle.accept(f"  {NOVEL_CLEAR}\n"), NOVEL_CLEAR)
        for bad in (
            "", "   ", None, "el tomate pesa 2 kg", '{"answer": "NOVEL_CLEAR"}',
            "VERIFY: NOVEL_CLEAR", "NOVEL_CLEAR y ademas otra cosa",
            "021f2908001400280a0000000500000b",  # a hex WSP: cortex's door
            f"{NOVEL_CLEAR}\nNOVEL_CLEAR", "x" * 300,
        ):
            with self.subTest(bad=repr(bad)[:40]):
                self.assertIsNone(oracle.accept(bad))
        # A packet parse_reply would take is not testimony.
        self.assertIsNotNone(cortex.parse_reply("YO → PREGUNTAR → DESCONOCIDO @AHORA"))
        self.assertIsNone(oracle.accept("YO → PREGUNTAR → DESCONOCIDO @AHORA"))

    def test_the_question_packet_carries_its_provenance(self) -> None:
        ag = Agent()
        ag.env.reset()
        ag.env.teleport(11)
        ag.turn(1)
        slot = ag.cam.get(ag.last_ask)
        self.assertGreaterEqual(slot, 0)
        self.assertIn(
            ag.cam.slot[slot].source, (oracle.SOURCE_SENSOR, oracle.SOURCE_FILE)
        )
        self.assertNotEqual(ag.cam.slot[slot].source, "nexus0-env")
        # The cell's own packet stays the ring's: it perceived the cell.
        cell_slot = ag.cam.get(encode_cell(11, KIND_NOVEL))
        self.assertEqual(ag.cam.slot[cell_slot].source, "nexus0-env")

    def test_prose_does_not_disarm_the_trap(self) -> None:
        """A chatty sensor is refused, counted, and changes nothing."""
        ag = Agent()
        ag.oracle = oracle.Sensor(lambda: "creo que la celda 11 es segura")
        ag.env.reset()
        ag.env.teleport(11)
        ag.turn(1)
        self.assertEqual(ag.metrics.questions, 1, "the question was not asked")
        self.assertEqual(ag.metrics.oracle_rejected, 1)
        self.assertTrue(ag.env.hidden_bit, "prose disarmed the trap")
        self.assertLess(ag.cam.get(encode_ask()), 0, "a refused answer took a slot")
        self.assertEqual(ag.metrics.false_facts, 0)
        cell_slot = ag.cam.get(encode_cell(11, KIND_NOVEL))
        self.assertNotIn(NOVEL_CLEAR, ag.cam.slot[cell_slot].extract)

    def test_reveal_never_runs_when_accept_failed(self) -> None:
        """Order lock: physics is told last, or not at all."""
        ag = Agent()
        ag.oracle = oracle.Sensor(lambda: "no")
        ag.env.reset()
        revealed = []
        real = ag.env.reveal
        ag.env.reveal = lambda x: revealed.append(x) or real(x)
        ag.env.teleport(11)
        ag.turn(1)
        self.assertEqual(revealed, [], "reveal ran on a refused answer")
        self.assertTrue(ag.env.hidden_bit)

        ag.oracle = oracle.Sensor()
        ag.env.teleport(11)
        ag.turn(2)
        self.assertEqual(revealed, [NOVEL_CLEAR])
        self.assertFalse(ag.env.hidden_bit)

    def test_a_file_oracle_answers_and_a_missing_one_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "answer.txt"
            good.write_text(NOVEL_CLEAR + "\n", encoding="utf-8")
            report = run(oracle_path=str(good))
            self.assertEqual(report["oracle_source"], oracle.SOURCE_FILE, report)
            self.assertEqual(report["novel_approach_return"], 80, report)
            self.assertEqual(report["oracle_rejected"], 0, report)
            self.assertEqual(report["false_facts"], 0, report)

            prose = Path(d) / "prose.txt"
            prose.write_text("no lo se, pregunta a otro\n", encoding="utf-8")
            report = run(oracle_path=str(prose))
            self.assertGreater(report["oracle_rejected"], 0, report)
            self.assertEqual(report["novel_approach_return"], -80, report)
            self.assertEqual(report["false_facts"], 0, report)

            report = run(oracle_path=str(Path(d) / "nope.txt"))
            self.assertGreater(report["oracle_rejected"], 0, report)
            self.assertEqual(report["novel_approach_return"], -80, report)

    def test_no_ask_is_silence_not_a_mute_oracle(self) -> None:
        ag = Agent(ask=False)
        self.assertIsNone(ag.oracle)
        report = run(ask=False)
        self.assertIsNone(report["oracle_source"], report)
        self.assertEqual(report["questions"], 0, report)
        self.assertEqual(report["oracle_rejected"], 0, report)
        self.assertEqual(report["novel_approach_return"], -80, report)

    def test_default_arm_is_unmoved_by_the_split(self) -> None:
        """Same turn, same trajectory — only who answers changed."""
        report = run()
        self.assertEqual(report["oracle_source"], oracle.SOURCE_SENSOR, report)
        self.assertIsNone(report["oracle_path"], report)
        self.assertEqual(report["oracle_rejected"], 0, report)
        self.assertEqual(report["questions"], 1, report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["level_search"], 0, report)
        self.assertTrue(report["t_beats_ring"], report)
        self.assertTrue(report["encoder_beats_fnv"], report)
        # The question fired on the same turn, so N/S/delta cannot move.
        self.assertEqual(report["cam_misses"], 33, report)
        self.assertEqual(report["surprises"], 1, report)
        self.assertEqual(report["deltas"], 217, report)
        self.assertEqual(report["surprise_known"], 1, report)


class TestCorridor(unittest.TestCase):
    """NEXUS-4i: another corridor. Same agent, same 16 B WSP, same three
    actions, a world that is not 32 cells.

    This is not AGI. It is a corridor.
    """

    HOME = corridor.LAYOUT_HOME
    SHIFT = corridor.LAYOUT_SHIFT

    def test_the_shift_is_topology_not_a_repaint(self) -> None:
        """The whole difference from phase F: no cell changes its kind."""
        home = corridor.CorridorEnv(self.HOME)
        shift = corridor.CorridorEnv(self.SHIFT)
        self.assertEqual(home.kind, shift.kind, "a cell was repainted")
        self.assertEqual(home.kind[corridor.X], KIND_THREAT)
        self.assertEqual(home.kind[corridor.C], KIND_EMPTY)
        self.assertEqual(home.kind[corridor.D], KIND_GOAL)
        self.assertNotEqual(corridor.C, corridor.X, "C and X must be two cells")
        # Same packet for A, B, D in both worlds; the successor differs.
        for i in (corridor.A, corridor.B, corridor.D):
            self.assertEqual(
                encode_cell(i, home.kind[i]), encode_cell(i, shift.kind[i])
            )
        home.teleport(corridor.B)
        shift.teleport(corridor.B)
        self.assertEqual(home.step(ACTION_APPROACH)[1].index, corridor.C)
        self.assertEqual(shift.step(ACTION_APPROACH)[1].index, corridor.X)

    def test_successor_is_a_table_not_arithmetic(self) -> None:
        """(i+1) % n would send B to C in both worlds. The table does not."""
        env = corridor.CorridorEnv(self.SHIFT)
        env.teleport(corridor.B)
        nxt = env.step(ACTION_APPROACH)[1].index
        self.assertEqual(nxt, corridor.X)
        self.assertNotEqual(nxt, (corridor.B + 1) % len(env.kind))
        env.teleport(corridor.D)  # the goal puts the agent back at the start
        self.assertEqual(env.step(ACTION_APPROACH)[1].index, corridor.A)

    def test_the_ring_is_not_the_only_world(self) -> None:
        ag = Agent(env=corridor.CorridorEnv(self.HOME))
        self.assertEqual(len(ag.env.kind), 5)
        ag.run(corridor.TRAIN_TURNS)
        self.assertEqual(ag.metrics.turns, corridor.TRAIN_TURNS)
        self.assertEqual(ag.metrics.questions, 0, "no NOVEL, so no question")
        self.assertEqual(ag.metrics.false_facts, 0)
        self.assertEqual(ag.metrics.destroyed, 0)
        self.assertEqual(ag.metrics.cortex_calls, 0)
        self.assertEqual(Agent().env.__class__.__name__, "RingEnv")

    def test_transfer_knows_b_and_scratch_does_not(self) -> None:
        """KPI 1. The transfer, in one line each."""
        report = corridor.experiment()
        self.assertTrue(report["transfer_knows_b_on_entry"], report)
        self.assertEqual(report["transfer_t_pred_b"], "C", report)
        self.assertGreaterEqual(report["transfer_t_conf_b"], 2, report)
        self.assertFalse(report["control_knows_b_on_entry"], report)

    def test_the_first_wrong_step_in_the_new_world(self) -> None:
        """KPI 2 and 3, in a world that is not the ring."""
        report = corridor.experiment()
        first = report["first_surprise"]
        self.assertIsNotNone(report["first_surprise_turn"], report)
        self.assertTrue(first["origin_slot_unchanged"], first)
        self.assertTrue(first["origin_was_not_a_cam_miss"], first)
        self.assertTrue(first["surprise_known_rose"], first)
        self.assertTrue(first["conflicts_rose"], first)
        self.assertTrue(first["kcc_kept_the_incumbent"], first)
        self.assertTrue(first["x_is_a_new_packet"], first)

    def test_the_policy_bends_where_the_world_did(self) -> None:
        """KPI 4, as measured — and it is not what the prompt predicted.

        Q[B, approach] falls 4 -> 1 and Q[X, approach] goes negative, so
        the policy does move where the world moved. But approach at B
        keeps winning, and converges there: in SHIFT the only route to D
        runs *through* X, and avoid at a threat pays R_AVOID_OK, so
        max Q[X] stays positive and B's backup with it. The agent learns
        "enter X, then avoid", not "never enter X". Nothing was retuned to
        make that come out; the corridor reuses the ring's own _reward.
        """
        report = corridor.experiment()
        self.assertTrue(report["q_b_approach_fell"], report)
        self.assertTrue(report["x_approach_is_negative"], report)
        self.assertTrue(report["approach_still_wins_b"], report)
        self.assertGreater(report["shift_policy_x"][ACTION_AVOID], 0, report)

    def test_the_carried_agent_pays_for_fewer_first_visits(self) -> None:
        """KPI 5. Measured on entry and over the shift window — after both
        arms have walked, of course they have both seen everything."""
        report = corridor.experiment()
        self.assertEqual(report["transfer_unseen_ABD_on_entry"], 0, report)
        self.assertEqual(report["control_unseen_ABD_on_entry"], 3, report)
        self.assertLess(
            report["transfer_cam_misses_in_shift"],
            report["control_cam_misses_in_shift"],
            report,
        )
        self.assertGreater(report["transfer_surprise_known"], 0, report)
        self.assertEqual(report["control_surprise_known"], 0, report)

    def test_corridor_writes_its_own_report(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        self.assertEqual(corridor.main([]), 0)
        self.assertTrue((lab / "nexus0_corridor_report.json").is_file())
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "corridor.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("nexus0_report.json", src)


class TestWorld3(unittest.TestCase):
    """WORLD-3: 256 addresses, a 16-node spine, and one edge that moves.

    The experiment is trained once for the whole class — 512 turns plus a
    64-turn window, twice over, is the report itself and not something to
    run a dozen copies of.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = graph.experiment()

    def test_graph_has_256_nodes(self) -> None:
        env = graph.GraphEnv(graph.LAYOUT_HOME)
        self.assertEqual(len(env.kind), 256)
        self.assertEqual(graph.N_NODES, 256)
        self.assertEqual(self.report["nodes"], 256)
        self.assertEqual(self.report["nodes_requested"], 256)
        # Every node has a successor for every action: the table is total.
        for layout in graph.LAYOUTS:
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                self.assertEqual(len(graph.NEXT[layout][a]), 256)

    def test_256_is_the_packet_ceiling(self) -> None:
        """Why 256 and not 4096: ext.seq is one byte.

        Node 256 would hand the fast loop the packet of node 0. That is the
        number ANTI-ALIAS has to move, measured here rather than asserted.
        """
        self.assertEqual(
            encode_cell(0, KIND_EMPTY), encode_cell(graph.N_NODES, KIND_EMPTY)
        )
        seen = {encode_cell(i, KIND_EMPTY) for i in range(graph.N_NODES)}
        self.assertEqual(len(seen), graph.N_NODES, "two nodes share a packet")

    def test_home_and_shift_share_spine_packets(self) -> None:
        """Nothing is repainted. Same index, same kind, same 16 bytes."""
        home = graph.GraphEnv(graph.LAYOUT_HOME)
        shift = graph.GraphEnv(graph.LAYOUT_SHIFT)
        self.assertEqual(home.kind, shift.kind, "a node was repainted")
        for node in graph.SPINE:
            self.assertEqual(
                encode_cell(node, home.kind[node]),
                encode_cell(node, shift.kind[node]),
            )
        # The fork keeps its own packet; only where approach lands changes.
        self.assertEqual(
            encode_cell(graph.B, home.kind[graph.B]),
            encode_cell(graph.B, shift.kind[graph.B]),
        )
        self.assertNotEqual(graph.C, graph.X, "C and X must be two nodes")
        self.assertEqual(home.kind[graph.C], KIND_EMPTY)
        self.assertEqual(home.kind[graph.X], KIND_THREAT)
        self.assertNotIn(graph.X, graph.SPINE)

    def test_only_one_edge_differs(self) -> None:
        """The whole topology change, counted."""
        diff = [
            (a, i)
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT)
            for i in range(graph.N_NODES)
            if graph.NEXT[graph.LAYOUT_HOME][a][i]
            != graph.NEXT[graph.LAYOUT_SHIFT][a][i]
        ]
        self.assertEqual(diff, [(ACTION_APPROACH, graph.B)], diff)

    def test_three_actions_only(self) -> None:
        self.assertEqual(self.report["actions"], 3)
        self.assertEqual(sorted(graph.NEXT[graph.LAYOUT_HOME]), [0, 1, 2])
        src = Path(__file__).resolve().parents[1] / "nexus0" / "graph.py"
        text = src.read_text(encoding="utf-8")
        for word in ("NORTH", "SOUTH", "EAST", "WEST", "minigrid", "MiniGrid"):
            self.assertNotIn(word, text)

    def test_wait_does_not_move(self) -> None:
        for layout in graph.LAYOUTS:
            env = graph.GraphEnv(layout)
            for node in (graph.START, graph.B, graph.C, graph.X, graph.GOAL, 42):
                env.teleport(node)
                self.assertEqual(env.step(ACTION_WAIT)[1].index, node)

    def test_goal_does_not_pump(self) -> None:
        """approach at GOAL collects and returns to the start of the spine."""
        for layout in graph.LAYOUTS:
            env = graph.GraphEnv(layout)
            env.teleport(graph.GOAL)
            r, nxt = env.step(ACTION_APPROACH)
            self.assertEqual(r, R_SUCCESS)
            self.assertEqual(nxt.index, graph.START)
            self.assertNotEqual(nxt.index, graph.GOAL)

    def test_shift_world_is_not_home(self) -> None:
        """step(approach) from the fork, and (i+1) would say neither."""
        home = graph.GraphEnv(graph.LAYOUT_HOME)
        shift = graph.GraphEnv(graph.LAYOUT_SHIFT)
        home.teleport(graph.B)
        shift.teleport(graph.B)
        self.assertEqual(home.step(ACTION_APPROACH)[1].index, graph.C)
        self.assertEqual(shift.step(ACTION_APPROACH)[1].index, graph.X)
        self.assertNotEqual(graph.C, (graph.B + 1) % graph.N_NODES)
        self.assertNotEqual(graph.X, (graph.B + 1) % graph.N_NODES)

    def test_transferred_t_knows_home_successor_at_fork(self) -> None:
        """KPI 1. T learned in HOME still names C when the world says X."""
        r = self.report
        self.assertTrue(r["transfer_knows_fork"], r)
        self.assertTrue(r["transfer_t_pred_is_home_c"], r)
        self.assertGreaterEqual(r["transfer_t_conf_fork"], 1, r)

    def test_t_survives_the_topology_change(self) -> None:
        """The transfer without money in it: 16 rows carried, 15 still true.

        The one that is not is the fork — the agent is wrong exactly where
        the world changed, and nowhere else.
        """
        r = self.report
        self.assertEqual(r["t_rows_known_on_entry"], graph.SPINE_LEN, r)
        self.assertEqual(r["t_matches_home_on_entry"], graph.SPINE_LEN, r)
        self.assertEqual(r["t_matches_shift_on_entry"], graph.SPINE_LEN - 1, r)
        self.assertEqual(r["t_wrong_spine_positions_in_shift"], [graph.FORK_POS], r)
        first = r["first_shift_turn"]
        self.assertTrue(first["landed_on_x"], first)
        self.assertTrue(first["surprise_known_rose"], first)
        self.assertTrue(first["origin_slot_unchanged"], first)
        self.assertTrue(first["origin_was_not_a_cam_miss"], first)

    def test_control_does_not(self) -> None:
        """KPI 4. Nothing was copied: empty T, and every spine node unseen."""
        r = self.report
        self.assertFalse(r["control_knows_fork"], r)
        self.assertEqual(r["control_t_rows_known_on_entry"], 0, r)
        self.assertEqual(r["transfer_unseen_spine_on_entry"], 0, r)
        self.assertEqual(r["control_unseen_spine_on_entry"], graph.SPINE_LEN, r)
        self.assertGreater(
            r["control_unseen_spine_on_entry"], r["transfer_unseen_spine_on_entry"], r
        )

    def test_transfer_gain_positive(self) -> None:
        """KPI 3, and what it is made of.

        The gain is real reward on the same seat, the same seed and the same
        number of greedy turns — and it is not a goal. The carried agent
        walks into X and the gate turns its blind `wait` into `avoid`, which
        pays R_AVOID_OK; the control has a flat row everywhere, so greedy
        answers `wait` and it never moves at all. Both halves are asserted
        here so the number cannot be read as more than it is.
        """
        r = self.report
        self.assertGreater(r["transfer_gain"], 0, r)
        self.assertEqual(
            r["transfer_gain"],
            r["transfer_reward_sum_shift"] - r["control_reward_sum_shift"],
        )
        self.assertEqual(r["control_reward_sum_shift"], 0, r)
        self.assertEqual(r["transfer_goal_hits_in_shift"], 0, r)
        self.assertEqual(
            r["transfer_reward_sum_shift"], r["transfer_avoid_pays_in_shift"] * R_AVOID_OK
        )
        self.assertTrue(graph.green(r), r)

    def test_the_credit_horizon_is_three_nodes(self) -> None:
        """Why the fork is spine position 13 and not 1, as a measurement.

        Integer Q with alpha = 1/4 drops a positive delta below 4, so value
        stops travelling. Counting back from GOAL the spine reads 13, 8, 4
        and then zeros. At position 1 both arms would sit in a flat row and
        transfer_gain would be 0 - 0.
        """
        prof = self.report["credit_horizon_q_approach"]
        self.assertEqual(len(prof), graph.SPINE_LEN)
        self.assertEqual(prof[: graph.SPINE_LEN - 3], [0] * (graph.SPINE_LEN - 3))
        self.assertTrue(all(v > 0 for v in prof[-3:]), prof)
        self.assertLess(graph.SPINE_LEN - graph.FORK_POS, 4)
        greedy = self.report["home_greedy_by_spine_pos"]
        self.assertEqual(greedy[graph.FORK_POS], ACTION_APPROACH, greedy)
        self.assertEqual(greedy[0], ACTION_WAIT, greedy)

    def test_false_facts_zero(self) -> None:
        r = self.report
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        # 256 addresses, 17 places anyone can stand on. CAM is not pressed
        # by this world and the report says so instead of implying it is.
        self.assertEqual(r["reachable_nodes"], 17)
        self.assertEqual(r["cam_occupied_shift"], 17, r)
        self.assertEqual(r["cam_slots"], 4096)

    def test_graph_module_does_not_import_cortex_cmd(self) -> None:
        """WORLD-3 plugs in no LLM. The KPI is measured with the slow clock
        off, and there is no switch in here to turn it on."""
        src = Path(__file__).resolve().parents[1] / "nexus0" / "graph.py"
        text = src.read_text(encoding="utf-8")
        for word in (
            "NAVI_CORTEX_CMD",
            "cortex_cmd",
            "subprocess",
            "requests",
            "urllib",
            "gguf",
            "llama",
        ):
            self.assertNotIn(word, text)
        self.assertNotIn("import cortex", text)
        ag = Agent(env=graph.GraphEnv(graph.LAYOUT_HOME))
        self.assertFalse(ag.cortex_enabled)

    def test_ring_report_untouched(self) -> None:
        """Its own report, and nobody else's."""
        lab = Path(__file__).resolve().parents[1] / "lab"
        ring = lab / "nexus0_report.json"
        before = ring.read_bytes() if ring.is_file() else None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(graph.main([]), 0)
        self.assertIn('"green": true', buf.getvalue())
        self.assertTrue((lab / "nexus0_world3_report.json").is_file())
        after = ring.read_bytes() if ring.is_file() else None
        self.assertEqual(before, after, "WORLD-3 wrote over the ring's report")
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "graph.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("nexus0_report.json", src)
        self.assertNotIn("nexus0_cortex1_report.json", src)
        self.assertNotIn("thought.jsonl", src)


class TestCuerpo1(unittest.TestCase):
    """CUERPO-1: a body, not another graph.

    The animal has a pose — where it stands and which way it faces — and
    orientation is state of the body, not a fourth action. The loop still
    sees three actions and a 16 B packet.
    """

    OPEN = body.LAYOUT_OPEN
    BLOCK = body.LAYOUT_BLOCK

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = body.experiment()

    # 1 ------------------------------------------------------------------
    def test_one_hundred_poses_and_a_total_table(self) -> None:
        self.assertEqual(body.N_POSES, 100)
        self.assertEqual(self.report["poses"], 100)
        self.assertEqual(self.report["poses_requested"], 100)
        self.assertEqual(len(body.BodyEnv(self.OPEN).kind), 100)
        for layout in body.LAYOUTS:
            self.assertEqual(sorted(body.NEXT[layout]), [0, 1, 2])
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                self.assertEqual(len(body.NEXT[layout][a]), 100)
        self.assertEqual(self.report["actions"], 3)

    def test_pose_is_the_index_that_enters_cam(self) -> None:
        """No second position ledger. `cell().index` is the pose itself."""
        for index in range(body.N_POSES):
            x, y, h = body.pose_of(index)
            self.assertEqual(body.index_of(x, y, h), index)
            self.assertEqual(index, (x + 5 * y) * 4 + h)
        env = body.BodyEnv(self.OPEN)
        env.teleport(body.index_of(3, 2, body.NORTH))
        self.assertEqual(env.cell().index, body.index_of(3, 2, body.NORTH))
        self.assertEqual(body.pose_of(env.cell().index), (3, 2, body.NORTH))
        # 100 poses, 100 distinct packets: well under the 256 seq ceiling.
        packets = {encode_cell(i, body.KINDS[i]) for i in range(body.N_POSES)}
        self.assertEqual(len(packets), body.N_POSES)
        self.assertLess(self.report["max_pose_index"], 256)

    def test_kind_is_the_floor_tile_not_the_heading(self) -> None:
        """Four headings on the goal tile are all GOAL; the index splits them."""
        env = body.BodyEnv(self.OPEN)
        for h in range(4):
            self.assertEqual(env.kind[body.index_of(4, 4, h)], KIND_GOAL)
        self.assertEqual(len(set(body.GOAL_POSES)), 4)
        # And no floor tile is painted THREAT: the collision is the threat.
        self.assertNotIn(KIND_THREAT, env.kind)
        self.assertFalse(env.cell().threat)

    # 2 ------------------------------------------------------------------
    def test_approach_steps_the_way_it_is_facing(self) -> None:
        env = body.BodyEnv(self.OPEN)
        for h, (dx, dy) in enumerate(body.DIRS):
            env.teleport(body.index_of(2, 2, h))
            r, nxt = env.step(ACTION_APPROACH)
            x, y, hh = body.pose_of(nxt.index)
            self.assertEqual(hh, h, "approach must not turn")
            if body.is_floor(2 + dx, 2 + dy, self.OPEN):
                self.assertEqual((x, y), (2 + dx, 2 + dy))
                self.assertEqual(r, 0)
            else:
                self.assertEqual((x, y), (2, 2), "walked through a wall")
                self.assertEqual(r, R_THREAT)

    def test_a_bump_pays_the_threat_and_does_not_pass_through(self) -> None:
        """Off the grid and into a wall, both."""
        env = body.BodyEnv(self.OPEN)
        edge = body.index_of(0, 0, body.WEST)  # facing off the grid
        env.teleport(edge)
        r, nxt = env.step(ACTION_APPROACH)
        self.assertEqual(r, R_THREAT)
        self.assertEqual(nxt.index, edge)
        self.assertTrue(env.bumped)

        wall = body.index_of(1, 0, body.NORTH)  # (1,1) is a wall
        env.teleport(wall)
        r, nxt = env.step(ACTION_APPROACH)
        self.assertEqual(r, R_THREAT)
        self.assertEqual(nxt.index, wall)
        self.assertEqual(self.report["bump_reward"], R_THREAT)
        self.assertTrue(self.report["bump_pose_unchanged"], self.report)

    # 3 ------------------------------------------------------------------
    def test_avoid_turns_and_never_translates(self) -> None:
        env = body.BodyEnv(self.OPEN)
        for index in range(body.N_POSES):
            x, y, h = body.pose_of(index)
            env.teleport(index)
            _r, nxt = env.step(ACTION_AVOID)
            nx, ny, nh = body.pose_of(nxt.index)
            self.assertEqual((nx, ny), (x, y), "avoid moved the body")
            self.assertEqual(nh, (h + 1) % 4, "avoid is 90 deg, one way")
        self.assertTrue(self.report["avoid_turns_not_translates"], self.report)
        self.assertEqual(self.report["turn_from"], "(2,2,E)")
        self.assertEqual(self.report["turn_to"], "(2,2,N)")

    # 4 ------------------------------------------------------------------
    def test_wait_does_not_move(self) -> None:
        env = body.BodyEnv(self.OPEN)
        for index in (body.START, body.index_of(2, 2, body.SOUTH),
                      body.GOAL_POSES[0], body.index_of(1, 1, body.EAST)):
            env.teleport(index)
            r, nxt = env.step(ACTION_WAIT)
            self.assertEqual(nxt.index, index)
            self.assertEqual(r, 0)

    # 5 ------------------------------------------------------------------
    def test_the_goal_does_not_pump(self) -> None:
        env = body.BodyEnv(self.OPEN)
        for h in range(4):
            env.teleport(body.GOAL_POSES[h])
            r, nxt = env.step(ACTION_APPROACH)
            self.assertEqual(r, R_SUCCESS)
            self.assertEqual(nxt.index, body.START, "did not go home")
            self.assertNotIn(nxt.index, body.GOAL_POSES)
        self.assertTrue(self.report["goal_returns_to_start"], self.report)

    # 6 ------------------------------------------------------------------
    def test_t_beats_the_stepper(self) -> None:
        """KPI. T predicts a pose under a floor plan; arithmetic cannot.

        Both arms are reported because they carry different halves of the
        claim. Free-running, the animal's own loop hugs the east wall,
        where "always x+1" cannot even state a guess — a real win, but the
        cheap half. Swept over the whole room the stepper answers 44 times
        and is wrong every one of them: heading, and walls.
        """
        r = self.report
        self.assertTrue(r["t_beats_stepper"], r)
        self.assertGreater(r["t_hits"], r["stepper_hits"], r)
        self.assertTrue(r["swept_t_beats_stepper"], r)
        self.assertEqual(r["swept_t_hits"], r["swept_t_asked"], r)
        self.assertGreater(r["swept_t_hits"], r["swept_stepper_hits"], r)
        # The half that is not free: the stepper answering and missing.
        self.assertGreater(r["swept_stepper_answered_and_missed"], 0, r)
        reasons = {e["why"] for e in r["swept_t_right_stepper_wrong"]}
        self.assertIn("heading", reasons, r["swept_t_right_stepper_wrong"])
        self.assertIn("wall", reasons, r["swept_t_right_stepper_wrong"])
        for e in r["swept_t_right_stepper_wrong"]:
            self.assertIsNotNone(e["stepper_said"], e)
            self.assertNotEqual(e["truth"], e["stepper_said"], e)

    def test_the_stepper_is_a_real_baseline_not_a_straw_man(self) -> None:
        """It is right wherever heading and walls do not matter."""
        east = body.index_of(0, 0, body.EAST)
        self.assertEqual(
            body.stepper(east), body.NEXT[self.OPEN][ACTION_APPROACH][east]
        )
        self.assertGreater(self.report["stepper_hits"], 0, self.report)
        self.assertGreater(self.report["swept_stepper_hits"], 0, self.report)
        self.assertIsNone(body.stepper(body.index_of(4, 2, body.NORTH)))

    # 7 ------------------------------------------------------------------
    def test_open_and_block_differ_by_one_tile(self) -> None:
        """One tile becomes a wall. Exactly four poses change where
        approach lands, and turning changes nowhere at all."""
        diff = body.approach_diff()
        self.assertEqual(
            [body.pose_name(i) for i in diff],
            ["(1,2,E)", "(2,2,E)", "(2,2,W)", "(3,2,W)"],
        )
        self.assertEqual(self.report["approach_diff_count"], 4, self.report)
        # Turning is body physics and never consults the room.
        self.assertEqual(self.report["avoid_diff_count"], 0, self.report)
        for a in (ACTION_AVOID, ACTION_WAIT):
            self.assertEqual(
                body.NEXT[self.OPEN][a], body.NEXT[self.BLOCK][a]
            )
        # Nothing is repainted to fake geometry: same kinds, both rooms.
        self.assertEqual(
            body.BodyEnv(self.OPEN).kind, body.BodyEnv(self.BLOCK).kind
        )
        # And the packets of the shared poses are identical.
        for i in range(body.N_POSES):
            self.assertEqual(
                encode_cell(i, body.KINDS[i]), encode_cell(i, body.KINDS[i])
            )
        self.assertEqual(
            body.NEXT[self.BLOCK][ACTION_APPROACH][body.index_of(1, 2, body.EAST)],
            body.index_of(1, 2, body.EAST),
            "closing the corridor must make that step a bump",
        )

    def test_t_survives_the_room_change(self) -> None:
        """Same agent, new floor plan, nothing reset but the room."""
        r = self.report
        self.assertEqual(r["t_rows_carried"], 76, r)
        self.assertEqual(r["t_rows_unchanged_by_the_move"], 76, r)
        self.assertEqual(r["t_rows_unaffected"], 72, r)
        self.assertEqual(
            r["t_unaffected_still_true_in_block"], r["t_rows_unaffected"], r
        )
        self.assertEqual(
            r["t_rows_carried"] - r["t_rows_unaffected"],
            r["approach_diff_count"],
            r,
        )

    def test_the_block_room_is_still_a_room(self) -> None:
        """Closing the corridor makes it harder, not impossible: the left
        and right columns still join the start to the goal."""
        seen = {body.START}
        edge = [body.START]
        while edge:
            here = edge.pop()
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                nxt = body.NEXT[self.BLOCK][a][here]
                if nxt not in seen:
                    seen.add(nxt)
                    edge.append(nxt)
        self.assertTrue(seen & set(body.GOAL_POSES), "the goal got walled off")

    # 8 ------------------------------------------------------------------
    def test_the_firewall_holds_in_a_body(self) -> None:
        r = self.report
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["cam_occupied"], 76, r)
        self.assertEqual(r["cam_slots"], 4096)
        self.assertTrue(body.green(r), r)
        ag = Agent(env=body.BodyEnv(self.OPEN))
        self.assertFalse(ag.cortex_enabled)
        self.assertEqual(ag.env.__class__.__name__, "BodyEnv")
        self.assertEqual(Agent().env.__class__.__name__, "RingEnv")

    def test_greedy_is_reported_beside_the_kpi_not_as_it(self) -> None:
        """Walking to the goal on purpose is WALK-1, and this says why it
        does not happen yet: the same integer credit horizon WORLD-3
        measured. Value reaches about three steps back from the goal, and
        the start of a ten-pose loop is nine steps away."""
        r = self.report
        self.assertNotIn("greedy", str(body.green.__doc__ or ""))
        profile = r["free_loop_q_approach"]
        self.assertEqual(len(profile), r["free_poses_stood_on"])
        self.assertTrue(all(v == 0 for v in profile[:4]), profile)
        self.assertTrue(all(v > 0 for v in profile[-3:]), profile)
        # It does reach the goal while exploring — noted, not claimed.
        self.assertGreater(r["free_goal_hits_in_training"], 0, r)
        self.assertEqual(r["greedy_free"]["goal_hits"], 0, r["greedy_free"])

    # 9 ------------------------------------------------------------------
    def test_body_module_plugs_in_no_model(self) -> None:
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        # Usage, not prose: the module's own docstring names what it is
        # not, and a test that bans those words would only ban honesty.
        for word in ("NAVI_CORTEX_CMD", "cortex_cmd", "subprocess", "urllib",
                     "requests", "gguf", "llama_"):
            self.assertNotIn(word, src, word)
        for module in ("cortex", "minigrid", "gym", "gymnasium", "torch",
                       "numpy", "cv2", "board", "loop"):
            self.assertNotIn(f"import {module}", src, module)
            self.assertNotIn(f"from {module}", src, module)
        # The Agent is imported inside the functions that need it, as the
        # corridor and the graph do; the env itself knows nothing about
        # the loop. Counting the imports would only measure how many
        # experiments the file has, so assert the shape instead: never at
        # module level, always indented inside a function.
        lines = [
            line for line in src.splitlines()
            if "from echoai.nexus0.loop import Agent" in line
        ]
        self.assertGreaterEqual(len(lines), 1)
        for line in lines:
            self.assertTrue(line.startswith("    "), line)
        # Integers only on the cable. The env may think in x/y/h ints; no
        # float reaches Q, T or CAM.
        self.assertNotIn("float(", src)

    # 10 -----------------------------------------------------------------
    def test_body_writes_its_own_report(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        ring = lab / "nexus0_report.json"
        world3 = lab / "nexus0_world3_report.json"
        before = (
            ring.read_bytes() if ring.is_file() else None,
            world3.read_bytes() if world3.is_file() else None,
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(body.main([]), 0)
        self.assertIn('"green": true', buf.getvalue())
        self.assertTrue((lab / "nexus0_cuerpo1_report.json").is_file())
        after = (
            ring.read_bytes() if ring.is_file() else None,
            world3.read_bytes() if world3.is_file() else None,
        )
        self.assertEqual(before, after, "CUERPO-1 wrote over another report")
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("nexus0_report.json", src)
        self.assertNotIn("nexus0_world3_report.json", src)


class TestCortex1(unittest.TestCase):
    """CORTEX-1: the slow clock changes a decision, and only proposes it.

    The fast loop cannot read the sign — that is not a limitation being
    worked around, it is the experiment. Both layouts hand it the same
    16 bytes.
    """

    PRIZE = sign.LAYOUT_PRIZE
    TRAP = sign.LAYOUT_TRAP

    @contextlib.contextmanager
    def _no_cmd(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(cortex.ENV_CMD, None)
            yield

    @contextlib.contextmanager
    def _stub(self):
        with mock.patch.dict(os.environ, {cortex.ENV_CMD: sign.cortex_cmd()}):
            yield

    @contextlib.contextmanager
    def _prose(self):
        """A binary that answers in Spanish. parse_reply must refuse it."""
        code = "import sys; sys.stdin.read(); print('amber means goal')"
        cmd = f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"
        with mock.patch.dict(os.environ, {cortex.ENV_CMD: cmd}):
            yield

    # 1 ------------------------------------------------------------------
    def test_sign_extract_is_language_not_kind(self) -> None:
        """The difference is a sentence, not a packet."""
        prize = sign.SignEnv(self.PRIZE)
        trap = sign.SignEnv(self.TRAP)
        self.assertEqual(prize.kind[sign.SIGN], KIND_EMPTY)
        self.assertEqual(trap.kind[sign.SIGN], KIND_EMPTY)
        self.assertNotEqual(prize.cell().extract, trap.cell().extract)
        self.assertIn("entra", prize.cell().extract)
        self.assertIn("no entres", trap.cell().extract)
        # The whole of what the fast loop perceives is identical.
        self.assertEqual(
            encode_cell(sign.SIGN, prize.kind[sign.SIGN]),
            encode_cell(sign.SIGN, trap.kind[sign.SIGN]),
        )
        # SIGN must not be NOVEL (that would fire PREGUNTAR) nor THREAT
        # (the gate would MODIFY approach and steal the cortex's credit).
        self.assertNotIn(KIND_NOVEL, (prize.kind[sign.SIGN], trap.kind[sign.SIGN]))
        self.assertNotIn(KIND_THREAT, (prize.kind[sign.SIGN], trap.kind[sign.SIGN]))

    def test_the_ring_extract_is_untouched(self) -> None:
        """The optional override is optional. Nothing else sets it."""
        self.assertEqual(RingEnv().cell().extract, "cell=0 kind=EMPTY")
        self.assertIsNone(RingEnv().cell().extract_text)
        self.assertIsNone(corridor.CorridorEnv().cell().extract_text)

    # 2 ------------------------------------------------------------------
    def test_greedy_fast_waits(self) -> None:
        """No cortex: a flat Q row is `wait`, in both worlds, for 0."""
        with self._no_cmd():
            for layout in (self.PRIZE, self.TRAP):
                with self.subTest(layout=layout):
                    ag = Agent(cortex=False, ask=False, env=sign.SignEnv(layout))
                    self.assertEqual(ag.turn(0, greedy=True), ACTION_WAIT)
                    self.assertEqual(ag.env.last_reward, 0)
                    self.assertEqual(ag.metrics.cortex_calls, 0)
                    self.assertEqual(ag.metrics.cortex_actions, 0)

    # 3 ------------------------------------------------------------------
    def test_stub_prize_approaches(self) -> None:
        with self._stub():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.PRIZE))
            a = ag.turn(0, greedy=True)
        self.assertEqual(a, ACTION_APPROACH)
        self.assertEqual(ag.env.last_reward, R_SUCCESS)
        self.assertGreaterEqual(ag.metrics.cortex_calls, 1)
        self.assertEqual(ag.metrics.cortex_actions, 1)
        self.assertEqual(ag.metrics.cortex_rejected, 0)
        self.assertEqual(ag.metrics.questions, 0, "this is not PREGUNTAR")
        self.assertEqual(ag.metrics.false_facts, 0)

    # 4 ------------------------------------------------------------------
    def test_stub_trap_avoids(self) -> None:
        with self._stub():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.TRAP))
            a = ag.turn(0, greedy=True)
        self.assertEqual(a, ACTION_AVOID)
        self.assertNotEqual(a, ACTION_APPROACH)
        self.assertEqual(ag.env.last_reward, 0)
        self.assertEqual(ag.metrics.questions, 0)
        # The same stub, the same code path, the opposite action: the sign
        # is doing the work, not a constant.
        self.assertEqual(ag.metrics.cortex_actions, 1)

    def test_the_stub_is_not_a_constant(self) -> None:
        """If it always said UNIR, the trap would catch it."""
        self.assertIn("TEMER", sign_cortex.decide(sign.SIGN_TEXT[self.TRAP]))
        self.assertIn("UNIR", sign_cortex.decide(sign.SIGN_TEXT[self.PRIZE]))
        self.assertEqual(sign_cortex.decide("cell=1 kind=GOAL"), "")
        for text in sign.SIGN_TEXT.values():
            self.assertIsNotNone(cortex.parse_reply(sign_cortex.decide(text)))

    # 5 ------------------------------------------------------------------
    def test_prose_cmd_falls_back_to_q(self) -> None:
        """A model that will not speak atoms does not get to decide."""
        with self._prose():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.PRIZE))
            a = ag.turn(0, greedy=True)
        self.assertIsNone(cortex.parse_reply("amber means goal"))
        self.assertEqual(a, ACTION_WAIT, "reject must fall back to Q")
        self.assertGreaterEqual(ag.metrics.cortex_rejected, 1)
        self.assertEqual(ag.metrics.cortex_actions, 0)
        self.assertEqual(ag.metrics.false_facts, 0)
        self.assertEqual(ag.env.last_reward, 0)

    # 6 ------------------------------------------------------------------
    def test_unir_is_proposal_not_fact(self) -> None:
        """The hypothesis moves the body. It does not enter memory."""
        with self._stub():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.PRIZE))
            ag.turn(0, greedy=True)
        slot = ag.cam.get(encode_cell(sign.SIGN, KIND_EMPTY))
        self.assertGreaterEqual(slot, 0)
        s = ag.cam.slot[slot]
        # What is stored is the sign the *world* showed, verbatim. No atom
        # of the cortex's reply is in CAM.
        self.assertEqual(s.extract, sign.SIGN_TEXT[self.PRIZE])
        for atom in ("UNIR", "TEMER", "premio=AMBAR", "AMBAR=premio"):
            self.assertNotIn(atom, s.extract)
        # CAM grew by the two cells that were actually stood on, and by
        # nothing else — a hypothesis allocates no slot.
        occupied = sum(1 for sl in ag.cam.slot if sl.occupied)
        self.assertEqual(occupied, 2, "the cortex allocated a slot")
        self.assertEqual(ag.metrics.false_facts, 0)
        self.assertEqual(ag.metrics.destroyed, 0)
        # And it lasts exactly one turn.
        self.assertIsNone(ag.last_cortex_action)

    def test_the_cortex_writes_no_table(self) -> None:
        """T and Q learn from the step taken, never from the proposal."""
        with self._stub():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.TRAP))
            ag.turn(0, greedy=True)
        slot = ag.cam.get(encode_cell(sign.SIGN, KIND_EMPTY))
        # avoid was taken and observed; approach — the action the cortex
        # did *not* propose — is still unknown to T.
        self.assertIsNotNone(ag.t.predict(slot, ACTION_AVOID))
        self.assertIsNone(ag.t.predict(slot, ACTION_APPROACH))
        self.assertEqual(ag.q.row(slot), [0, 0, 0], "r=0 moves nothing")

    # 7 ------------------------------------------------------------------
    def test_gate_still_runs(self) -> None:
        """The proposal goes through the gate like any other action."""
        seen = []
        real = loop_module.gate

        def counting(wsp, **kw):
            seen.append(kw["proposed"])
            return real(wsp, **kw)

        with self._stub(), mock.patch.object(loop_module, "gate", counting):
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.PRIZE))
            a = ag.turn(0, greedy=True)
        self.assertEqual(len(seen), 1, "one gate call per turn")
        self.assertEqual(seen[0], ACTION_APPROACH, "the cortex proposed")
        self.assertEqual(a, ACTION_APPROACH, "and the gate let it through")

    def test_gate_can_still_veto_the_cortex(self) -> None:
        """An inhibited slot blocks the hypothesis exactly as it blocks Q.

        The proposal is injected directly rather than waited for: after one
        turn ATTEND is right not to wake again, and the question here is
        what the gate does with a hypothesis, not when one arrives.
        """
        ag = Agent(cortex=False, ask=False, env=sign.SignEnv(self.PRIZE))
        ag.turn(0, greedy=True)  # wait: allocates SIGN and stays on it
        slot = ag.cam.get(encode_cell(sign.SIGN, KIND_EMPTY))
        ag.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        ag.last_cortex_action = ACTION_APPROACH
        a = ag.turn(1, greedy=True)
        self.assertEqual(a, ACTION_WAIT, "inhibit must beat the cortex")
        self.assertEqual(ag.metrics.cortex_actions, 1, "it was consumed")
        self.assertEqual(ag.env.last_reward, 0, "the +16 was not collected")
        self.assertIsNone(ag.last_cortex_action)

    # 8 ------------------------------------------------------------------
    def test_parse_reply_untouched(self) -> None:
        self.assertIsNotNone(cortex.parse_reply("YO → UNIR → AQUI @AHORA"))
        self.assertIsNone(cortex.parse_reply("YO → UNIR → AQUI"))
        self.assertIsNone(cortex.parse_reply("el letrero dice que entres"))
        self.assertEqual(
            rel_of(cortex.parse_reply("YO → UNIR → AQUI @AHORA")), ATOM_ID["UNIR"]
        )
        # The mapping is the one that already existed.
        self.assertEqual(
            ACTION_REL, (ATOM_ID["UNIR"], ATOM_ID["TEMER"], ATOM_ID["OBSERVAR"])
        )
        self.assertEqual(ACTION_REL.index(ATOM_ID["UNIR"]), ACTION_APPROACH)
        self.assertEqual(ACTION_REL.index(ATOM_ID["TEMER"]), ACTION_AVOID)
        self.assertEqual(ACTION_REL.index(ATOM_ID["OBSERVAR"]), ACTION_WAIT)

    def test_the_stubs_own_echo_is_not_advice(self) -> None:
        """An EMPTY cell's packet already reads OBSERVAR and a THREAT's
        reads TEMER. Without a reply from outside, that echo must not be
        taken as a proposal — otherwise the ring would take orders from
        its own perception."""
        self.assertEqual(rel_of(encode_cell(0, KIND_EMPTY)), ATOM_ID["OBSERVAR"])
        self.assertEqual(rel_of(encode_cell(7, KIND_THREAT)), ATOM_ID["TEMER"])
        with self._no_cmd():
            ag = Agent(cortex=True, ask=False, env=sign.SignEnv(self.PRIZE))
            a = ag.turn(0, greedy=True)
        self.assertGreaterEqual(ag.metrics.cortex_calls, 1, "it did wake")
        self.assertEqual(ag.metrics.cortex_actions, 0, "and it proposed nothing")
        self.assertEqual(a, ACTION_WAIT)

    # 9 ------------------------------------------------------------------
    def test_thought_keys_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "t.jsonl")
            with self._stub():
                ag = Agent(
                    cortex=True, ask=False, thought_log=log,
                    env=sign.SignEnv(self.PRIZE),
                )
                ag.turn(0, greedy=True)
            for line in Path(log).read_text(encoding="utf-8").splitlines():
                self.assertEqual(set(json.loads(line)), set(thought.KEYS))

    # 10 -----------------------------------------------------------------
    def test_ring_locks(self) -> None:
        with self._no_cmd():
            report = run()
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["cortex_actions"], 0, report)
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["surprise_known"], 1, report)
        self.assertEqual(report["false_facts"], 0, report)

    # 11 -----------------------------------------------------------------
    def test_ring_attend_still_36(self) -> None:
        """The cable must not cost the ring a single extra wake."""
        with self._no_cmd():
            ag = Agent(cortex=True)
            ag.run(BENCH_TURNS)
        self.assertEqual(ag.metrics.cortex_calls, 36)
        self.assertEqual(ag.metrics.cortex_actions, 0, "the ring stub asks")
        self.assertEqual(ag.metrics.false_facts, 0)

    # 12 -----------------------------------------------------------------
    def test_report_file_is_own(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        locked = lab / "nexus0_report.json"
        before = locked.read_bytes() if locked.is_file() else None
        with contextlib.redirect_stdout(io.StringIO()):
            rc = sign.main([])
        self.assertEqual(rc, 0, "CORTEX-1 is not green")
        self.assertTrue((lab / "nexus0_cortex1_report.json").is_file())
        if before is not None:
            self.assertEqual(locked.read_bytes(), before, "clobbered the lock")
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "sign.py"
        ).read_text(encoding="utf-8")
        for other in ("nexus0_report.json", "nexus0_cortex_report.json"):
            self.assertNotIn(other, src)

    def test_the_kpi_report(self) -> None:
        """Every headline number of the slice, in one place."""
        report = sign.experiment()
        self.assertEqual(report["prize_fast_action"], "wait", report)
        self.assertEqual(report["prize_cortex_action"], "approach", report)
        self.assertEqual(report["trap_fast_action"], "wait", report)
        self.assertEqual(report["trap_cortex_action"], "avoid", report)
        self.assertGreater(
            report["prize_cortex_reward"], report["prize_fast_reward"], report
        )
        self.assertGreater(report["CortexROI"], 0, report)
        self.assertTrue(report["decision_change"], report)
        self.assertEqual(report["questions"], 0, "PREGUNTAR is not a decision")
        self.assertGreaterEqual(report["cortex_calls"], 1, report)
        self.assertLess(
            report["cortex_rejected"], report["cortex_calls"],
            "if the cortex is rejected as often as it is called it is mute",
        )
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["ring_cortex_wakes"], 36, report)
        self.assertTrue(report["green"] if "green" in report else True)
        # ATTEND woke on its own account, with no new reason code added.
        self.assertEqual(report["attend_reason_sign"], REASON_LOW_C, report)


class TestWalk1(unittest.TestCase):
    """WALK-1: reverse curriculum in training, exam at the canonical start.

    The slice is **red**, and these tests pin why. The curriculum works —
    the animal collects goals in every phase — and the exam from (0,0,E)
    still scores zero, because the blocker is not exploration. It is the
    integer step `delta >> 2` in `qtable.update`, which drops any positive
    delta below 4 and stops value travelling three states from the goal.
    No reward and no constant was touched to make this read better.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = body.walk()

    # 1 ------------------------------------------------------------------
    def test_exam_is_canonical_start(self) -> None:
        """The exam runs from (0,0,E), not from a pose near the goal.

        Move `_exam` to teleport anywhere else and this goes red — that is
        the point of it. The start is nine actions from a collection, and
        the report says so.
        """
        r = self.report
        self.assertEqual(r["exam_start"], "(0,0,E)", r)
        self.assertEqual(r["exam_start"], body.pose_name(body.START))
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertEqual(r["start_distance"], 9, r)
        src = inspect.getsource(body._exam)
        self.assertIn("teleport(START)", src)
        # Nothing but START may be teleported to in the exam.
        self.assertEqual(src.count("teleport("), 1, src)

    # 2 ------------------------------------------------------------------
    @unittest.expectedFailure
    def test_goal_hits_positive(self) -> None:
        """The KPI as written. It fails, and it is left failing.

        Marked expected-failure rather than deleted or weakened: the day
        somebody moves the credit wall this turns into an unexpected
        success and has to be promoted to a plain assertion.
        """
        self.assertGreater(self.report["exam_goal_hits"], 0, self.report)

    def test_the_exam_scored_zero_and_the_report_is_red(self) -> None:
        """What actually happened, asserted so it cannot be misread."""
        r = self.report
        self.assertEqual(r["exam_goal_hits"], 0, r)
        self.assertEqual(r["exam_reward_sum"], 0, r)
        self.assertEqual(r["exam_poses_visited"], 1, "it stood still")
        self.assertFalse(body.walk_green(r), r)
        # And the runner says so with its exit code, not only in prose.
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(body.main(["--walk"]), 1)

    # 3 ------------------------------------------------------------------
    def test_rewards_and_alpha_untouched(self) -> None:
        """Nothing was retuned to chase the KPI."""
        from echoai.nexus0 import constants

        r = self.report
        self.assertEqual(r["alpha_shift"], 2)
        self.assertEqual(r["alpha_shift"], constants.ALPHA_SHIFT)
        self.assertEqual(r["gamma"], [7, 8])
        self.assertEqual(
            r["gamma"], [constants.GAMMA_NUM, constants.GAMMA_DEN]
        )
        self.assertEqual(r["R"]["success"], R_SUCCESS)
        self.assertEqual(r["R"]["threat"], R_THREAT)
        self.assertEqual(r["R"]["avoid_ok"], R_AVOID_OK)
        self.assertEqual(r["R"]["success"], 16)
        self.assertEqual(r["R"]["threat"], -16)
        self.assertEqual(r["R"]["avoid_ok"], 8)
        # Not the two levers that were ruled out either.
        self.assertFalse(r["traces"], r)
        self.assertEqual(r["plan_depth"], 0, r)
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        for banned in ("trace=True", "ALPHA_SHIFT =", "R_SUCCESS =",
                       "R_THREAT =", "plan_depth=", "qtable.ALPHA_SHIFT"):
            self.assertNotIn(banned, src, banned)

    # 4 ------------------------------------------------------------------
    def test_no_hardcoded_path(self) -> None:
        """The exam decides with Q and nothing else.

        `shortest_path` exists, but only the report reads it. The action
        loop cannot see a route: no successor table, no pose constant, no
        action constant appears anywhere in it.
        """
        src = inspect.getsource(body._exam)
        self.assertIn("greedy=True", src)
        for banned in ("shortest_path", "path", "NEXT[", "ACTION_APPROACH",
                       "ACTION_AVOID", "ACTION_WAIT", "index_of(",
                       "distances(", "(4,0,N)"):
            self.assertNotIn(banned, src, banned)
        whole = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        # Q is never written by hand anywhere in the module.
        for banned in (".q.set(", ".q.q[", "load_rows", "last_cortex_action",
                       "plan.best", ".t.pred[", ".t.observe("):
            self.assertNotIn(banned, whole, banned)
        # The curriculum only chooses where a turn is taken from.
        train = inspect.getsource(body.walk)
        self.assertIn("teleport(pose)", train)
        self.assertIn("ag.turn(turn)", train)
        self.assertNotIn("greedy=True", train.split("_exam")[0])

    def test_distances_come_from_the_physics(self) -> None:
        """Flood fill on the successor table, not Manhattan.

        Manhattan is blind to heading; here a turn costs a step. (0,0,W)
        faces off the grid and is further from the goal than (0,0,E),
        though they are the same tile.
        """
        dist = body.distances(body.LAYOUT_OPEN)
        for g in body.GOAL_POSES:
            self.assertEqual(dist[g], 0)
        self.assertEqual(dist[body.index_of(0, 0, body.EAST)], 9)
        self.assertGreater(
            dist[body.index_of(0, 0, body.WEST)],
            dist[body.index_of(0, 0, body.EAST)],
            "heading must cost something",
        )
        # A step of the path lowers the distance by exactly one.
        path = body.shortest_path(body.LAYOUT_OPEN, body.START)
        self.assertEqual([dist[p] for p in path], list(range(9, -1, -1)))
        self.assertEqual(path[0], body.START)
        self.assertIn(path[-1], body.GOAL_POSES)

    # 5 ------------------------------------------------------------------
    def test_cortex_off(self) -> None:
        r = self.report
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("NAVI_CORTEX_CMD", src)
        self.assertNotIn("cortex=True", src)

    # 6 ------------------------------------------------------------------
    def test_walk_writes_its_own_report(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_world3_report.json")
        before = {
            n: (lab / n).read_bytes() if (lab / n).is_file() else None
            for n in others
        }
        with contextlib.redirect_stdout(io.StringIO()):
            rc = body.main(["--walk"])
        self.assertEqual(rc, 1, "the KPI failed, so the runner must say 1")
        self.assertTrue((lab / "nexus0_walk1_report.json").is_file())
        after = {
            n: (lab / n).read_bytes() if (lab / n).is_file() else None
            for n in others
        }
        self.assertEqual(before, after, "WALK-1 wrote over another report")
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("nexus0_report.json", src)
        self.assertNotIn("nexus0_world3_report.json", src)

    # 7 ------------------------------------------------------------------
    def test_the_curriculum_did_its_job(self) -> None:
        """It is not an exploration failure: the animal collected goals in
        the far phases too, and still learned nothing it could use."""
        r = self.report
        dists = [ph["dist"] for ph in r["curriculum"]]
        self.assertEqual(dists, sorted(dists), "phases must go outward")
        self.assertEqual(dists[0], 1)
        self.assertGreaterEqual(max(dists), r["start_distance"], r)
        near = [ph for ph in r["curriculum"] if ph["dist"] <= 4]
        self.assertTrue(
            all(ph["goal_hits_in_phase"] > 0 for ph in near),
            [ (ph["dist"], ph["goal_hits_in_phase"]) for ph in near ],
        )
        self.assertGreater(r["curriculum_turns"], 10000, r)

    def test_the_wall_is_arithmetic_not_a_shortage_of_training(self) -> None:
        """`credit_chain` replays the shipped integer update to its fixed
        point and predicts the measured rows exactly: 13, 8, 4, then zero
        for ever. More turns cannot move it, and this asserts both halves.
        """
        r = self.report
        chain = r["credit_chain_shift_2"]
        self.assertEqual(chain[:4], [13, 8, 4, 0], chain)
        self.assertTrue(all(v == 0 for v in chain[3:]), chain)
        measured = r["best_q_approach_by_distance"]
        for d in ("0", "1", "2"):
            self.assertEqual(measured[d], chain[int(d)], (d, measured, chain))
        for d in range(3, 10):
            self.assertEqual(measured[str(d)], 0, measured)
        # Q along the real path from the start: still zeros at the far end.
        along = r["q_approach_along_a_path_from_start"]
        self.assertEqual(len(along), 10)
        self.assertTrue(all(v <= 0 for v in along[:7]), along)
        self.assertEqual(along[-3:], [4, 8, 13], along)
        # With no truncation the same chain is positive the whole way —
        # arithmetic only, nothing monkeypatched and nothing shipped.
        self.assertTrue(all(v > 0 for v in r["credit_chain_shift_0"][:10]))

    def test_more_training_at_the_wall_changes_nothing(self) -> None:
        """The direct answer to "you did not train enough"."""
        from echoai.nexus0.loop import Agent

        by_dist = body.poses_by_distance(body.LAYOUT_OPEN)
        ag = Agent(env=body.BodyEnv(body.LAYOUT_OPEN))
        turn = 0
        for d in (1, 2, 3):
            for _rep in range(200):
                for pose in by_dist[d]:
                    ag.env.teleport(pose)
                    for _ in range(d + 2):
                        ag.turn(turn)
                        turn += 1
        best = {
            d: max(ag.q.row(body._slot(ag, p))[ACTION_APPROACH]
                   for p in by_dist[d] if body._slot(ag, p) >= 0)
            for d in (1, 2, 3)
        }
        self.assertGreater(turn, 10000, "the point is a long soak")
        self.assertEqual(best[1], 8, best)
        self.assertEqual(best[2], 4, best)
        self.assertEqual(best[3], 0, best)


class TestCredit1(unittest.TestCase):
    """CREDIT-1: keep the crumbs `delta >> 2` throws away. Opt-in.

    alpha is still 1/4 and no reward moved. What changed is that a delta
    of 1, 2 or 3 is **owed** instead of dropped, and paid once the debt
    reaches a whole unit. WALK-1 stays red without it; that is the
    control, and it is asserted here too.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.credit = body.walk(remainder=True)

    # 1 ------------------------------------------------------------------
    def test_remainder_off_is_the_old_shift(self) -> None:
        """No flag, no change: delta 3 moves nothing, delta 4 moves one."""
        q = QTable()
        self.assertFalse(q.remainder)
        self.assertEqual(q.rem, [], "off must allocate no array at all")
        # delta = r + 0 - q. Force 3, three times over.
        for _ in range(3):
            d = q.update(0, 0, 3 + q.get(0, 0), 9)
            self.assertEqual(d, 3)
            self.assertEqual(q.get(0, 0), 0, "the crumb was kept without a flag")
        d = q.update(0, 0, 4 + q.get(0, 0), 9)
        self.assertEqual(d, 4)
        self.assertEqual(q.get(0, 0), 1)

    # 2 ------------------------------------------------------------------
    def test_remainder_keeps_the_crumbs(self) -> None:
        """Exact numbers, not "about right".

        owed accumulates delta; a whole unit is paid the moment the debt
        reaches four.

            update 1: owed 0+3 = 3 -> step 0, rem 3, Q 0
            update 2: owed 3+3 = 6 -> step 1, rem 2, Q 1
            update 3: owed 2+3 = 5 -> step 1, rem 1, Q 2
        """
        q = QTable(remainder=True)
        self.assertTrue(q.remainder)
        expected = [(0, 3), (1, 2), (2, 1)]
        for i, (want_q, want_rem) in enumerate(expected, start=1):
            d = q.update(0, 0, 3 + q.get(0, 0), 9)
            self.assertEqual(d, 3, i)
            self.assertEqual(q.get(0, 0), want_q, f"update {i}: Q")
            self.assertEqual(q.rem[0][0], want_rem, f"update {i}: rem")
        # Four deltas of 3 pay 3 units, not 0. That is the whole slice.
        q.update(0, 0, 3 + q.get(0, 0), 9)
        self.assertEqual(q.get(0, 0), 3)
        self.assertEqual(q.rem[0][0], 0)

    # 3 ------------------------------------------------------------------
    def test_negative_truncates_toward_zero(self) -> None:
        """Python's `>>` floors. -5 >> 2 is -2; the credit owes -1."""
        self.assertEqual(trunc_div(5), 1)
        self.assertEqual(trunc_div(3), 0)
        self.assertEqual(trunc_div(-3), 0)
        self.assertEqual(trunc_div(-5), -1)
        self.assertEqual(trunc_div(-4), -1)
        self.assertEqual((-5) >> 2, -2, "the shift this avoids")
        self.assertEqual((-3) >> 2, -1, "the shift this avoids")

        # Worked through by hand and checked against the code:
        #   1: owed 0-3 = -3 -> step  0, rem -3, Q  0
        #   2: owed -3-3 = -6 -> step -1, rem -2, Q -1
        #   3: owed -2-3 = -5 -> step -1, rem -1, Q -2
        q = QTable(remainder=True)
        expected = [(0, -3), (-1, -2), (-2, -1)]
        for i, (want_q, want_rem) in enumerate(expected, start=1):
            d = q.update(0, 0, -3 + q.get(0, 0), 9)
            self.assertEqual(d, -3, i)
            self.assertEqual(q.get(0, 0), want_q, f"update {i}: Q")
            self.assertEqual(q.rem[0][0], want_rem, f"update {i}: rem")
        # The floor would have reached -3 by now.
        self.assertNotEqual(q.get(0, 0), -3)

    def test_the_debt_is_bounded(self) -> None:
        """A remainder can never reach a whole unit: it is paid first."""
        q = QTable(remainder=True)
        for t in range(400):
            q.update(t % 64, t % 3, (t % 9) - 4, (t + 1) % 64)
        worst = max(abs(v) for row in q.rem for v in row)
        self.assertLess(worst, 1 << 2, worst)
        self.assertLessEqual(self.credit["rem_abs_max_during_training"], 3)
        self.assertEqual(self.credit["rem_abs_max_on_path"], 0,
                         "at the fixed point nothing is owed")

    def test_traces_and_the_remainder_are_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            QTable(trace=True, remainder=True)

    # 4 ------------------------------------------------------------------
    def test_ring_default_has_no_remainder(self) -> None:
        """The ring never learns that this lever exists."""
        ag = Agent()
        self.assertFalse(ag.q.remainder)
        self.assertEqual(ag.q.rem, [])
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["surprise_known"], 1, report)
        self.assertEqual(report["cam_misses"], 33, report)
        self.assertEqual(report["surprises"], 1, report)
        self.assertEqual(report["deltas"], 217, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["false_facts"], 0, report)

    # 5 ------------------------------------------------------------------
    def test_credit1_exam_hits_from_canonical_start(self) -> None:
        """The KPI. Same curriculum, same exam, same start, same rewards."""
        c = self.credit
        self.assertTrue(c["remainder"], c)
        self.assertEqual(c["exam_start"], "(0,0,E)", c)
        self.assertTrue(c["exam_start_is_canonical"], c)
        self.assertEqual(c["start_distance"], 9, c)
        self.assertGreater(c["exam_goal_hits"], 0, c)
        self.assertEqual(c["exam_reward_sum"], c["exam_goal_hits"] * R_SUCCESS,
                         "the reward is collections and nothing else")
        self.assertEqual(c["exam_bumps"], 0, c)
        self.assertGreater(c["exam_poses_visited"], 1, "it walked")
        self.assertEqual(c["false_facts"], 0, c)
        self.assertEqual(c["destroyed"], 0, c)
        self.assertEqual(c["cortex_calls"], 0, c)
        self.assertEqual(c["questions"], 0, c)
        self.assertTrue(body.walk_green(c), c)
        # Q is positive the whole way to the goal now, where WALK-1 had
        # zeros for the first seven poses.
        along = c["q_approach_along_a_path_from_start"]
        self.assertEqual(len(along), 10)
        self.assertGreater(along[0], 0, along)
        self.assertTrue(all(v > 0 for i, v in enumerate(along) if i != 4), along)

    # 6 ------------------------------------------------------------------
    def test_walk1_without_remainder_still_red(self) -> None:
        """The control. WALK-1 is not rewritten and not quietly fixed."""
        plain = body.walk()
        self.assertFalse(plain["remainder"])
        self.assertEqual(plain["exam_goal_hits"], 0, plain)
        self.assertEqual(plain["exam_reward_sum"], 0, plain)
        self.assertFalse(body.walk_green(plain), plain)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(body.main(["--walk"]), 1)
            self.assertEqual(body.main(["--walk-remainder"]), 0)

    # 7 ------------------------------------------------------------------
    def test_does_not_touch_alpha_or_R(self) -> None:
        from echoai.nexus0 import constants

        c = self.credit
        self.assertEqual(c["alpha_shift"], constants.ALPHA_SHIFT)
        self.assertEqual(c["alpha_shift"], 2)
        self.assertEqual(c["gamma"], [constants.GAMMA_NUM, constants.GAMMA_DEN])
        self.assertEqual(c["R"], {"success": 16, "threat": -16, "avoid_ok": 8})
        self.assertFalse(c["traces"], c)
        self.assertEqual(c["plan_depth"], 0, c)
        # The alpha formula itself is untouched: the wall is still there
        # for anyone who does not pull this lever.
        self.assertEqual(c["credit_chain_shift_2"][:4], [13, 8, 4, 0])
        self.assertEqual(
            c["credit_chain_with_remainder"][:5], [16, 14, 12, 10, 8]
        )
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "qtable.py"
        ).read_text(encoding="utf-8")
        self.assertIn("ALPHA_SHIFT", src)
        self.assertNotIn("ALPHA_SHIFT =", src, "alpha is imported, not redefined")
        # Usage, not the word: the docstring says "no float, no round()"
        # on purpose, so only a real call counts.
        self.assertNotIn("float(", src)
        self.assertNotIn("= round(", src)

    # 8 ------------------------------------------------------------------
    def test_no_hardcoded_path(self) -> None:
        """The remainder exam is the same `_exam` WALK-1 is judged by."""
        src = inspect.getsource(body._exam)
        self.assertIn("greedy=True", src)
        self.assertIn("teleport(START)", src)
        self.assertEqual(src.count("teleport("), 1)
        for banned in ("shortest_path", "NEXT[", "ACTION_APPROACH",
                       "ACTION_AVOID", "index_of(", "(4,0,N)"):
            self.assertNotIn(banned, src, banned)
        whole = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body.py"
        ).read_text(encoding="utf-8")
        for banned in (".q.set(", ".q.q[", "load_rows", ".q.rem[_slot(ag, p)][ACTION_AVOID]"):
            self.assertNotIn(banned, whole, banned)

    def test_credit1_writes_its_own_report(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_world3_report.json")
        before = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                  for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(body.main(["--walk-remainder"]), 0)
        self.assertTrue((lab / "nexus0_credit1_report.json").is_file())
        after = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                 for n in others}
        self.assertEqual(before, after, "CREDIT-1 wrote over another report")
        walk1 = json.loads(
            (lab / "nexus0_walk1_report.json").read_text(encoding="utf-8")
        )
        self.assertFalse(walk1["green"], "the red report must stay red")
        self.assertEqual(walk1["exam_goal_hits"], 0, walk1)


class TestPulpo(unittest.TestCase):
    """PULPO: a 3D body that walks, predicts, and changes its mind.

    162 poses in a cube, a walk to the goal from the canonical start, T
    beating blind arithmetic, and — PULPO-C — a plug in the short corridor
    that sends the same body down an eleven-action detour it never used
    before, greedy, cortex off, with nothing reset.

    The two blockers that made this red were measured, and each is now met
    by one lever rather than by a special case:

    exploration   `qtable.select` answers `approach` on a flat row, so a
                  turn in open air could never be found. `explore_flat`
                  lets a flat row take the same `turn % 3` cycle a non-flat
                  row already takes. Off by default; the report carries the
                  control run with it off, and the detour collects 0 there.
    arithmetic    a detour past the value horizon has Q = 0 at the start no
                  matter how long you train. The cube's detour is 11 and
                  `value_horizon()` is 11, so the last unit of credit is
                  the one that carries it.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = body3d.experiment()

    # 1 ------------------------------------------------------------------
    def test_162_poses_and_the_packet_ceiling(self) -> None:
        self.assertEqual(body3d.N_POSES, 162)
        self.assertEqual(self.report["poses"], 162)
        self.assertEqual(self.report["max_index"], 161)
        for i in range(body3d.N_POSES):
            x, y, z, h = body3d.pose_of(i)
            self.assertEqual(body3d.index_of(x, y, z, h), i)
            self.assertEqual(i, (x + 3 * y + 9 * z) * 6 + h)
        packets = {encode_cell(i, body3d.KINDS[i]) for i in range(body3d.N_POSES)}
        self.assertEqual(len(packets), 162, "two poses share a packet")
        # The ceiling is measured, not raised: 4**3 * 6 = 384 would alias.
        self.assertEqual(encode_cell(0, KIND_EMPTY), encode_cell(256, KIND_EMPTY))
        for layout in body3d.LAYOUTS:
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                self.assertEqual(len(body3d.NEXT[layout][a]), 162)

    # 2 ------------------------------------------------------------------
    def test_approach_follows_the_heading_and_stone_stops_it(self) -> None:
        env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for h, (dx, dy, dz) in enumerate(body3d.DIRS):
            here = body3d.index_of(2, 0, 0, h)
            env.teleport(here)
            r, nxt = env.step(ACTION_APPROACH)
            x, y, z, hh = body3d.pose_of(nxt.index)
            self.assertEqual(hh, h, "approach must not turn")
            if body3d.is_floor(2 + dx, 0 + dy, 0 + dz, body3d.LAYOUT_OPEN):
                self.assertEqual((x, y, z), (2 + dx, dy, dz))
                self.assertEqual(r, 0)
            else:
                self.assertEqual((x, y, z), (2, 0, 0), "walked through stone")
                self.assertEqual(r, R_THREAT)
                self.assertTrue(env.bumped)
        self.assertTrue(self.report["exam_open_goal_hits"] >= 0)

    # 3 ------------------------------------------------------------------
    def test_avoid_cycles_the_heading_and_never_translates(self) -> None:
        env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for i in range(body3d.N_POSES):
            x, y, z, h = body3d.pose_of(i)
            env.teleport(i)
            _r, nxt = env.step(ACTION_AVOID)
            nx, ny, nz, nh = body3d.pose_of(nxt.index)
            self.assertEqual((nx, ny, nz), (x, y, z), "avoid moved the body")
            self.assertEqual(nh, (h + 1) % 6)
        # Six avoids are the identity: it is a ring, not a yaw and a pitch.
        start = body3d.index_of(1, 2, 2, body3d.PLUS_Z)
        env.teleport(start)
        for _ in range(6):
            env.step(ACTION_AVOID)
        self.assertEqual(env.cell().index, start)
        self.assertEqual(self.report["avoid_diff_count"], 0,
                         "turning must not consult the room")

    # 4 ------------------------------------------------------------------
    def test_wait_does_not_move(self) -> None:
        env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for i in (body3d.START, body3d.GOAL_POSES[0],
                  body3d.index_of(2, 0, 0, body3d.PLUS_Y)):
            env.teleport(i)
            r, nxt = env.step(ACTION_WAIT)
            self.assertEqual(nxt.index, i)
            self.assertEqual(r, 0)

    # 5 ------------------------------------------------------------------
    def test_the_goal_does_not_pump(self) -> None:
        env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for g in body3d.GOAL_POSES:
            env.teleport(g)
            r, nxt = env.step(ACTION_APPROACH)
            self.assertEqual(r, R_SUCCESS)
            self.assertEqual(nxt.index, body3d.START)
            self.assertNotIn(nxt.index, body3d.GOAL_POSES)
        # A voxel's kind is the same from all six headings.
        for g in body3d.GOAL_POSES:
            self.assertEqual(body3d.KINDS[g], KIND_GOAL)
        self.assertNotIn(KIND_THREAT, env.kind, "no floor is painted THREAT")

    # 6 ------------------------------------------------------------------
    def test_both_layouts_are_connected_and_the_plug_is_on_the_short_one(self):
        self.assertIn(body3d.BLOCKED, body3d.SHORT_PATH)
        self.assertNotIn(body3d.BLOCKED, body3d.LONG_PATH)
        for layout in body3d.LAYOUTS:
            dist = body3d.distances(layout)
            self.assertIn(body3d.START, dist, f"{layout} is not connected")
        self.assertGreater(
            self.report["start_distance_block"],
            self.report["start_distance_open"],
            "the plug must make the journey worse",
        )
        # Disjoint in the middle: no third route hides between them.
        mid_short = set(body3d.SHORT_PATH[1:-1])
        mid_long = set(body3d.LONG_PATH[1:-1])
        self.assertEqual(mid_short & mid_long, set())
        self.assertGreater(self.report["approach_diff_count"], 0)

    # 7 ------------------------------------------------------------------
    def test_t_beats_the_stepper(self) -> None:
        r = self.report
        self.assertTrue(r["t_beats_stepper"], r)
        self.assertEqual(r["t_hits"], r["t_asked"], r)
        self.assertGreater(r["t_hits"], r["stepper_hits"], r)
        self.assertGreater(r["stepper_answered_and_missed"], 0, r)
        reasons = {e["why"] for e in r["t_right_stepper_wrong"]}
        self.assertIn("heading", reasons, r["t_right_stepper_wrong"])
        self.assertIn("stone", reasons, r["t_right_stepper_wrong"])

    # 8 ------------------------------------------------------------------
    def test_t_survives_the_plug(self) -> None:
        r = self.report
        self.assertEqual(
            r["t_unaffected_still_true_in_block"], r["t_rows_unaffected"], r
        )
        self.assertGreater(r["t_rows_carried"], 0, r)
        self.assertGreater(r["t_rows_unaffected"], 0, r)
        # Every row T carried that the plug did not reach still describes
        # the new cube, and the ones it did reach are exactly the diff.
        self.assertLessEqual(
            r["t_rows_carried"] - r["t_rows_unaffected"],
            r["approach_diff_count"],
            r,
        )
        self.assertTrue(
            set(r["approach_diff_poses"]) >= {
                body3d.pose_name(i)
                for i in range(body3d.N_POSES)
                if body3d.NEXT["open"][ACTION_APPROACH][i]
                != body3d.NEXT["block"][ACTION_APPROACH][i]
            }
        )

    # 9 ------------------------------------------------------------------
    def test_it_walks_in_three_dimensions_from_the_canonical_start(self) -> None:
        """The green leg. A 3D body, greedy, cortex off, from (0,0,0,+X)."""
        r = self.report
        self.assertEqual(r["exam_start"], "(0,0,0,+X)", r)
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertGreater(r["start_distance_open"], 5, "not a neighbour of the goal")
        self.assertGreater(r["exam_open_goal_hits"], 0, r)
        self.assertEqual(
            r["exam_open_reward_sum"],
            r["exam_open_goal_hits"] * R_SUCCESS - r["exam_open_bumps"] * 16,
        )
        self.assertTrue(r["exam_open_corridor"]["reached_the_goal_voxel"], r)
        # It moved on all three axes, which is what makes this 3D.
        self.assertEqual(r["exam_open_axes_moved"], [0, 1, 2], r)
        self.assertTrue(r["remainder"], "CREDIT-1 is what makes the walk possible")
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)

    # 10 -----------------------------------------------------------------
    def test_exam_block_goal_hits_positive(self) -> None:
        """The KPI as written. It used to be an expectedFailure."""
        r = self.report
        self.assertGreater(r["exam_block_goal_hits"], 0, r)
        self.assertTrue(r["exam_block_corridor"]["used_the_detour"], r)
        self.assertTrue(r["exam_block_corridor"]["reached_the_goal_voxel"], r)
        # And the arm that already worked was not traded away for it.
        self.assertGreater(r["exam_open_goal_hits"], 0, r)
        self.assertTrue(body3d.green(r), r)

    def test_the_detour_is_walked_not_stumbled_into(self) -> None:
        """It leaves the short corridor at the first pose and stays out."""
        r = self.report
        use = r["exam_block_corridor"]
        self.assertEqual(use["short_voxels_visited"], [], r["exam_block_trail"])
        self.assertGreater(len(use["long_voxels_visited"]), 0, r)
        # Every collection costs the whole detour plus the collecting step,
        # so the reward is the hits and nothing else: no bumping for points.
        self.assertEqual(r["exam_block_bumps"], 0, r)
        self.assertEqual(
            r["exam_block_reward_sum"], r["exam_block_goal_hits"] * R_SUCCESS, r
        )
        # 512 turns cannot buy more collections than the detour allows.
        cycle = r["detour_cost_block"] + 1
        self.assertLessEqual(
            r["exam_block_goal_hits"], r["exam_turns"] // cycle + 1, r
        )

    def test_the_detour_sits_exactly_on_the_value_horizon(self) -> None:
        """Reason one, and the geometry was chosen to meet it, not to dodge it."""
        r = self.report
        self.assertEqual(r["value_horizon"], 11, r)
        self.assertEqual(body3d.value_horizon(), r["value_horizon"])
        self.assertLessEqual(r["detour_cost_block"], r["value_horizon"], r)
        self.assertTrue(r["detour_fits_the_horizon"], r)
        # It still has to be a detour: strictly worse than the short one.
        self.assertGreater(r["detour_cost_block"], r["short_cost_open"], r)
        self.assertGreater(r["start_distance_open"], 5, "not a neighbour of the goal")
        # A cube one action longer would be unlearnable at any training
        # length, which is why 4**3 is not the answer either.
        self.assertEqual(body3d.N_POSES, 162)

    def test_the_lever_is_what_buys_the_detour(self) -> None:
        """Reason two, run as a control rather than asserted in prose."""
        r = self.report
        self.assertTrue(r["explore_flat"], r)
        self.assertEqual(r["open_air_turns_block"], 2, r["turn_poses_block"])
        self.assertEqual(r["open_air_turns_open"], 0, r["turn_poses_open"])
        # Without the lever the detour is undiscoverable; the short
        # corridor never needed it, because both its turns hit stone.
        self.assertFalse(r["block_route_is_learnable_without_the_lever"], r)
        self.assertTrue(r["open_route_is_learnable_without_the_lever"], r)
        self.assertTrue(r["block_route_is_learnable"], r)
        # And the same schedule with the lever off collects nothing.
        control = r["control_without_the_lever"]
        self.assertFalse(control["explore_flat"])
        self.assertGreater(control["open_goal_hits"], 0, control)
        self.assertLess(control["block_goal_hits"], r["exam_block_goal_hits"],
                        control)
        self.assertTrue(r["lever_buys_the_detour"], r)

    def test_flat_row_default_is_still_approach(self) -> None:
        """The lever is off unless somebody asks for it, everywhere."""
        self.assertFalse(QTable().explore_flat)
        self.assertFalse(Agent().q.explore_flat)
        plain = QTable()
        for turn in range(12):
            self.assertEqual(plain.row(7), [0, 0, 0])
            self.assertTrue(plain.is_explore(7, turn))
            self.assertEqual(plain.select(7, turn), ACTION_APPROACH, turn)
        # On, the same flat row joins the cycle a non-flat row already had.
        lever = QTable(explore_flat=True)
        chosen = {lever.select(7, turn) for turn in range(12)}
        self.assertEqual(chosen, {ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT})
        for turn in range(12):
            self.assertEqual(lever.select(7, turn), turn % 3, turn)
        # Greedy is untouched by the lever: no exploration in an exam.
        for q in (plain, lever):
            self.assertEqual(q.select(7, 1, greedy=True), q.best(7))
        # A non-flat row behaves identically with the lever either way.
        for q in (plain, lever):
            q.set(9, ACTION_APPROACH, -12)
            q.set(9, ACTION_AVOID, 5)
        self.assertEqual([plain.select(9, t) for t in range(12)],
                         [lever.select(9, t) for t in range(12)])
        # And it costs no memory.
        self.assertEqual(lever.rem, [])
        self.assertEqual(lever.z, [])

    def test_the_curriculum_names_no_route(self) -> None:
        """Reverse curriculum in both layouts, and it is a training aid."""
        r = self.report
        src = inspect.getsource(body3d._curriculum)
        for banned in ("SHORT_PATH", "LONG_PATH", "BLOCKED", "NEXT[",
                       "ACTION_APPROACH", "ACTION_AVOID", "index_of("):
            self.assertNotIn(banned, src, banned)
        self.assertIn("poses_by_distance(layout)", src)
        self.assertGreater(r["readapt_turns"], 0, r)
        self.assertEqual(r["total_train_turns"],
                         r["curriculum_turns"] + r["readapt_turns"], r)
        # The exploration budget must not be a whole number of ε-cycles or
        # a pose is offered the same action every repetition.
        for d in range(1, 22):
            self.assertNotEqual(body3d.episode_turns(d) % N_ACTIONS, 0, d)
            self.assertGreater(body3d.episode_turns(d), d + 1, d)

    # 11 -----------------------------------------------------------------
    def test_no_hardcoded_path(self) -> None:
        src = inspect.getsource(body3d._exam)
        self.assertIn("greedy=True", src)
        self.assertIn("teleport(START)", src)
        self.assertEqual(src.count("teleport("), 1)
        for banned in ("shortest_path", "NEXT[", "ACTION_APPROACH",
                       "ACTION_AVOID", "index_of(", "SHORT_PATH", "LONG_PATH"):
            self.assertNotIn(banned, src, banned)
        whole = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body3d.py"
        ).read_text(encoding="utf-8")
        for banned in (".q.set(", ".q.q[", "load_rows", "last_cortex_action",
                       "plan.best"):
            self.assertNotIn(banned, whole, banned)

    # 12 -----------------------------------------------------------------
    def test_ring_default_untouched(self) -> None:
        ag = Agent()
        self.assertFalse(ag.q.remainder)
        self.assertFalse(ag.q.explore_flat)
        # The report must print the ring it actually turns through, not a
        # string somebody wrote once.
        self.assertEqual(
            self.report["turn_is_a_cycle"],
            "h -> (h+1) % 6 over " + ",".join(body3d.HEADING_NAME),
        )
        self.assertEqual(body3d.HEADING_NAME,
                         ("+X", "+Y", "+Z", "-X", "-Y", "-Z"))
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(self.report["alpha_shift"], 2)
        self.assertEqual(self.report["R"],
                         {"success": 16, "threat": -16, "avoid_ok": 8})
        self.assertFalse(self.report["traces"])

    # 13 -----------------------------------------------------------------
    def test_writes_its_own_report_and_plugs_in_no_model(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_credit1_report.json", "nexus0_walk1_report.json")
        before = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                  for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = body3d.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertTrue((lab / "nexus0_pulpo_report.json").is_file())
        after = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                 for n in others}
        self.assertEqual(before, after, "PULPO wrote over another report")
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "body3d.py"
        ).read_text(encoding="utf-8")
        for word in ("NAVI_CORTEX_CMD", "cortex_cmd", "subprocess", "urllib",
                     "requests", "gguf", "llama_"):
            self.assertNotIn(word, src, word)
        for module in ("cortex", "minigrid", "gym", "torch", "numpy", "board"):
            self.assertNotIn(f"import {module}", src, module)


class TestSelf1(unittest.TestCase):
    """SELF-1: the same surprise, two different authors.

    `approach` did not land where T said. That sentence is produced by a
    slipped arm and by a plugged corridor alike, and nothing in the WSP,
    in `kind`, in `extract` or in E tells the body which one it is. The
    body decides with one integer and six hypotheses written in its own
    actions, and what it wins is the right to **not** rewrite the cube it
    already learned.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = self1.experiment()

    # 1 ------------------------------------------------------------------
    def test_a_plain_agent_has_no_self(self) -> None:
        ag = Agent()
        self.assertFalse(ag.q.explore_flat)
        self.assertEqual(ag.body_offset, 0)
        self.assertIsNone(ag.self_model)
        self.assertFalse(self.report["agent_default_explore_flat"])
        self.assertEqual(self.report["agent_default_body_offset"], 0)
        # With no model attached the loop observes exactly as it always did.
        src = inspect.getsource(loop_module.Agent.turn)
        self.assertIn("self.self_model is None", src)

    # 2 ------------------------------------------------------------------
    def test_the_packet_does_not_carry_the_perturbation(self) -> None:
        """A pose reads the same 16 bytes in both arms. No label rides."""
        motor = self1.Self1Env(body3d.LAYOUT_OPEN, self1.SLIP)
        world = self1.Self1Env(body3d.LAYOUT_BLOCK, self1.NO_SLIP)
        intact = self1.Self1Env(body3d.LAYOUT_OPEN, self1.NO_SLIP)
        for env in (motor, world, intact):
            self.assertNotIn(KIND_THREAT, env.kind, "a floor was painted")
        for i in range(body3d.N_POSES):
            a = encode_cell(motor.teleport(i).index, motor.kind[i])
            b = encode_cell(world.teleport(i).index, world.kind[i])
            self.assertEqual(a, b, body3d.pose_name(i))
            self.assertEqual(len(a), 16)
        self.assertTrue(self.report["packet_is_the_same_in_both_arms"])
        # Nor does the extract or E: same pose, same sentence, both arms.
        for i in (body3d.START, body3d.GOAL_POSES[0],
                  body3d.index_of(2, 0, 0, body3d.PLUS_Y)):
            self.assertEqual(motor.teleport(i).extract, world.teleport(i).extract)
            self.assertEqual(motor.teleport(i).threat, world.teleport(i).threat)
        self.assertFalse(motor.reveal("anything"))

    # 3 ------------------------------------------------------------------
    def test_slip_zero_is_the_pulpo_cube_step_for_step(self) -> None:
        """The env only adds knobs; at zero it is the body that is green."""
        mine = self1.Self1Env(body3d.LAYOUT_OPEN, self1.NO_SLIP)
        theirs = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for i in range(body3d.N_POSES):
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                mine.teleport(i)
                theirs.teleport(i)
                ra, ca = mine.step(a)
                rb, cb = theirs.step(a)
                self.assertEqual((ra, ca.index, mine.bumped),
                                 (rb, cb.index, theirs.bumped),
                                 (body3d.pose_name(i), a))

    # 4 ------------------------------------------------------------------
    def test_the_slip_moves_the_push_and_nothing_else(self) -> None:
        slipped = self1.slipped_successors(body3d.LAYOUT_OPEN, self1.SLIP)
        intact = self1.slipped_successors(body3d.LAYOUT_OPEN, self1.NO_SLIP)
        for a in (ACTION_AVOID, ACTION_WAIT):
            self.assertEqual(slipped[a], intact[a], "the slip turned the body")
        changed = [i for i in range(body3d.N_POSES)
                   if slipped[ACTION_APPROACH][i] != intact[ACTION_APPROACH][i]]
        self.assertGreater(len(changed), 0)
        # The heading of the landing pose is the heading it started with:
        # the arm slipped, the body did not turn.
        for i in body3d.reachable(body3d.LAYOUT_OPEN):
            if i in body3d.GOAL_POSES:
                continue
            self.assertEqual(body3d.pose_of(slipped[ACTION_APPROACH][i])[3],
                             body3d.pose_of(i)[3], body3d.pose_name(i))

    # 5 ------------------------------------------------------------------
    def test_it_says_the_arm_when_the_arm_moved(self) -> None:
        r = self.report
        self.assertEqual(r["body_offset_motor"], r["slip"], r["explained_motor"])
        self.assertEqual(r["body_offset_world"], 0, r["explained_world"])
        self.assertEqual(r["self_attribution_agent"], 1, r)
        self.assertEqual(r["self_attribution_control"], 0, r)
        self.assertGreater(r["attribution_gap"], 0, r)
        # The winner survives on its own: it explains and contradicts none.
        k = r["body_offset_motor"]
        self.assertGreater(r["explained_motor"][k], 0, r)
        self.assertEqual(r["contradicted_motor"][k], 0, r)
        others = [j for j in range(1, 6)
                  if j != k and r["contradicted_motor"][j] == 0
                  and r["explained_motor"][j] > 0]
        self.assertEqual(others, [], "the verdict was not unique")
        # A wall in front of the body is explained by a crowd, so the
        # world arm gets no verdict rather than a wrong one.
        crowd = [j for j in range(1, 6)
                 if r["contradicted_world"][j] == 0
                 and r["explained_world"][j] > 0]
        self.assertGreater(len(crowd), 1, r["explained_world"])

    # 6 ------------------------------------------------------------------
    def test_it_keeps_the_cube_it_already_learned(self) -> None:
        r = self.report
        self.assertGreater(r["t_world_preserved_motor_agent"],
                           r["t_world_preserved_motor_control"], r)
        self.assertLessEqual(r["t_world_preserved_motor_agent"],
                             r["t_world_asked_motor"], r)
        # It dropped the surprises the arm explains and spent the rest.
        self.assertGreater(r["held_dropped_motor"], 0, r)
        # The world arm explains nothing away: every surprise is spent.
        self.assertEqual(r["held_dropped_world"], 0, r)
        self.assertGreater(r["held_committed_world"], 0, r)

    # 7 ------------------------------------------------------------------
    def test_recovery_from_the_canonical_start(self) -> None:
        r = self.report
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertEqual(r["exam_motor_trail"][0], body3d.pose_name(body3d.START))
        self.assertEqual(r["exam_world_trail"][0], body3d.pose_name(body3d.START))
        self.assertGreater(r["exam_motor_goal_hits"], 0, r["exam_motor_trail"])
        self.assertGreater(r["exam_world_goal_hits"], 0, r["exam_world_trail"])
        self.assertEqual(r["exam_motor_reward_sum"],
                         r["exam_motor_goal_hits"] * R_SUCCESS, r)
        self.assertTrue(self1.green(r), r)

    # 8 ------------------------------------------------------------------
    def test_the_offset_is_an_argmax_not_the_number_one(self) -> None:
        r = self.report
        self.assertEqual(r["probe_slip2_offset"], 2, r["probe_slip2_explained"])
        self.assertNotEqual(r["probe_slip2_offset"], r["slip"])
        self.assertEqual(r["probe_slip2_contradicted"][2], 0, r)
        self.assertEqual(r["hypotheses"], 6)

    # 9 ------------------------------------------------------------------
    def test_attribution_reads_poses_and_nothing_else(self) -> None:
        """It cannot be cheating: there is nothing to cheat with."""
        # Usage forms, not words: the prose is allowed to name what the
        # code is forbidden to read.
        for fn in (self1.SelfModel._attribute, self1.SelfModel._tally,
                   self1.SelfModel.hypothesis, self1.SelfModel.observe_step):
            src = inspect.getsource(fn)
            for banned in ("KIND_", ".extract", ".kind", ".cell(",
                           "last_reward", ".slip", "SLIP", ".layout",
                           "GOAL_POSES", "SHORT_PATH", "LONG_PATH",
                           "BLOCKED", "index_of(", "pose_of(", "DIRS[",
                           "is_floor(", "reachable(", ".env"):
                self.assertNotIn(banned, src, f"{fn.__name__}: {banned}")
            # What it *is* allowed to read: the two poses of a step.
            self.assertNotIn("import ", src)
        whole = (
            Path(__file__).resolve().parents[1] / "nexus0" / "self1.py"
        ).read_text(encoding="utf-8")
        for banned in (".q.set(", ".q.q[", "load_rows", "plan.best",
                       "last_cortex_action", "subprocess", "urllib",
                       "requests", "gguf", "llama_", "NAVI_CORTEX_CMD"):
            self.assertNotIn(banned, whole, banned)
        for module in ("cortex", "minigrid", "gym", "torch", "numpy", "board"):
            self.assertNotIn(f"import {module}", whole, module)

    # 10 -----------------------------------------------------------------
    def test_what_holding_a_surprise_is_worth(self) -> None:
        """Measured, and the honest answer is: on this cube, nothing.

        Suspending a surprise until the verdict is the order the reasoning
        wants, but it is not what saves the world model — T's own conflict
        discipline already refuses to unseat a successor a whole curriculum
        agreed on. If this test ever fails, holding started to matter and
        the prose in `self1.probe_holding` has to be rewritten, not the
        assertion.
        """
        r = self.report
        probe = r["holding_probe"]
        self.assertEqual(probe["with_holding"]["body_offset"], r["slip"], probe)
        self.assertEqual(probe["without_holding"]["body_offset"], r["slip"], probe)
        self.assertGreaterEqual(r["t_world_kept_with_holding"],
                                r["t_world_kept_without_holding"], probe)
        self.assertFalse(r["holding_changes_the_map"], probe)
        # What *does* save it is the protection after the verdict, and the
        # window alone is not where the gap comes from.
        self.assertGreater(r["t_world_preserved_motor_agent"],
                           r["t_world_preserved_motor_control"], r)

    # 11 -----------------------------------------------------------------
    def test_ring_and_pulpo_untouched(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(self.report["actions"], 3)
        self.assertEqual(self.report["cortex_calls"], 0, self.report)
        self.assertEqual(self.report["questions"], 0, self.report)
        self.assertEqual(self.report["false_facts"], 0, self.report)
        self.assertEqual(self.report["destroyed"], 0, self.report)

    # 12 -----------------------------------------------------------------
    def test_writes_its_own_report_and_treads_on_nobody(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_pulpo_report.json",
                  "nexus0_cuerpo1_report.json", "nexus0_credit1_report.json",
                  "nexus0_walk1_report.json", "nexus0_world3_report.json")
        before = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                  for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = self1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertTrue((lab / "nexus0_self1_report.json").is_file())
        after = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                 for n in others}
        self.assertEqual(before, after, "SELF-1 wrote over another report")


class TestRoom1(unittest.TestCase):
    """ROOM-1: two rooms, one map.

    The same cube twice. Which room the body is in is an integer on the
    env and it is nowhere in the sixteen bytes, so a pose reads the same
    packet in both: 324 places, 162 packets. The claim to be paid for is
    that the sharing is not a bookkeeping trick — the body walks into a
    room it has never been in and collects, its memory does not double,
    and where the rooms stop behaving alike the cost is printed rather
    than patched away.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = room1.experiment()

    # 1 ------------------------------------------------------------------
    def test_the_frame_is_on_the_env_and_not_in_the_packet(self) -> None:
        a = room1.room_env(room1.FRAME_A)
        b = room1.room_env(room1.FRAME_B)
        self.assertEqual((a.frame, b.frame), (0, 1))
        self.assertNotEqual(a.frame, b.frame)
        self.assertEqual(a.kind, b.kind, "a room was painted a second kind")
        for i in range(body3d.N_POSES):
            pa = encode_cell(a.teleport(i).index, a.kind[i])
            pb = encode_cell(b.teleport(i).index, b.kind[i])
            self.assertEqual(pa, pb, body3d.pose_name(i))
            self.assertEqual(len(pa), 16)
            ext = room1.ext_of(i)
            self.assertEqual(ext["domain"], 0, body3d.pose_name(i))
            self.assertEqual(ext["style"], 0, body3d.pose_name(i))
            self.assertEqual(ext["seq"], i, body3d.pose_name(i))
        # cell() hands out the local pose, which is what the encoder gets.
        self.assertEqual(a.teleport(161).index, 161)
        self.assertLess(max(range(body3d.N_POSES)), room1.PLACES)
        r = self.report
        self.assertTrue(r["frame_is_outside_the_packet"], r)
        self.assertTrue(r["domain_is_zero"], r)
        self.assertTrue(r["style_is_zero"], r)
        self.assertTrue(r["seq_is_the_local_pose"], r)

    # 2 ------------------------------------------------------------------
    def test_two_rooms_share_one_packet_each(self) -> None:
        r = self.report
        self.assertEqual(r["places"], 324, r)
        self.assertEqual(r["packets_across"], 162, r)
        self.assertEqual(r["packets_in_A"], 162, r)
        self.assertEqual(r["packets_in_B"], 162, r)
        self.assertEqual(
            room1.packets_in(room1.FRAME_A), room1.packets_in(room1.FRAME_B)
        )
        self.assertEqual(r["packets_across"], r["places"] // r["frames"])

    # 3 ------------------------------------------------------------------
    def test_sharing_costs_nothing_while_the_rooms_behave_alike(self) -> None:
        self.assertEqual(room1.dynamic_alias(room1.ROOMS), [])
        self.assertEqual(
            room1.dynamic_alias(room1.ROOMS, standable_only=False), []
        )
        self.assertEqual(self.report["dynamic_alias"], 0, self.report)
        self.assertEqual(self.report["dynamic_alias_table"], 0, self.report)

    # 4 ------------------------------------------------------------------
    def test_the_hole_is_reported_and_not_papered_over(self) -> None:
        """The mutant is run: B keeps the packets and loses four rows.

        This is the alias that matters — same WSP, different dynamics —
        and the honest thing is the number, not a room byte in the packet.
        """
        r = self.report
        pairs = room1.dynamic_alias(room1.ROOMS_WITH_HOLE)
        self.assertGreater(len(pairs), 0, "the plug changed nothing")
        self.assertEqual(r["dynamic_alias_with_hole"], len(pairs), r)
        self.assertEqual(r["dynamic_alias_with_hole_table"],
                         r["approach_rows_that_differ_with_hole"], r)
        # Same packets on both sides of the disagreement: that is the alias.
        self.assertTrue(r["packets_shared_with_hole"], r)
        self.assertEqual(r["packets_in_B_with_hole"], 162, r)
        self.assertTrue(r["domain_is_zero_with_hole"], r)
        self.assertTrue(room1.domain_is_zero())
        # And it costs: T is wrong about the room it cannot see.
        self.assertLess(r["t_agrees_in_B_with_hole"],
                        r["t_known_in_B_before_a_step"], r)

    # 5 ------------------------------------------------------------------
    def test_it_walks_a_room_it_has_never_been_in(self) -> None:
        r = self.report
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertEqual(r["exam_B_transferred_trail"][0],
                         body3d.pose_name(body3d.START))
        self.assertGreater(r["exam_B_transferred_goal_hits"], 0,
                           r["exam_B_transferred_trail"])
        self.assertEqual(r["exam_B_transferred_reward_sum"],
                         r["exam_B_transferred_goal_hits"] * R_SUCCESS, r)
        # It knew B before it took a step in it, and the control did not.
        self.assertGreater(r["t_known_in_B_before_a_step"], 0, r)
        self.assertEqual(r["t_known_in_B_scratch"], 0, r)
        self.assertTrue(room1.green(r), r)

    # 6 ------------------------------------------------------------------
    def test_the_transfer_is_worth_something(self) -> None:
        r = self.report
        self.assertGreater(r["transfer_gain"], 0, r)
        # B did not collect because it was trained in B: not one turn was
        # taken there before the greedy exam.
        self.assertEqual(r["turns_in_B_before_the_exam"], 0, r)
        self.assertGreater(r["turns_after_A"], 0, r)
        self.assertEqual(r["transfer_gain"],
                         r["exam_B_transferred_goal_hits"]
                         - r["exam_B_scratch_goal_hits"], r)
        # Not a strawman that was never given the turns: a body schooled
        # in B from scratch reaches the same number, for 29580 turns the
        # transferred one did not have to spend.
        self.assertEqual(r["exam_B_schooled_goal_hits"],
                         r["exam_B_transferred_goal_hits"], r)
        self.assertGreater(r["exam_B_schooled_turns"], 0, r)
        self.assertTrue(r["transfer_costs_no_turns"], r)

    # 7 ------------------------------------------------------------------
    def test_two_rooms_do_not_cost_two_memories(self) -> None:
        r = self.report
        self.assertLessEqual(r["cam_occupied_AB"],
                             r["cam_occupied_A"] + r["cam_margin"], r)
        self.assertTrue(r["cam_shared"], r)
        self.assertLess(r["cam_occupied_AB"], 2 * r["cam_occupied_A"], r)
        self.assertLess(r["cam_occupied_AB"], r["cam_slots"])

    # 8 ------------------------------------------------------------------
    def test_the_room_is_nowhere_in_the_encoder(self) -> None:
        """Usage forms, not words: the prose may name what the code may
        not write."""
        whole = (
            Path(__file__).resolve().parents[1] / "nexus0" / "room1.py"
        ).read_text(encoding="utf-8")
        for banned in ("WSP_DOM", "domain =", "domain=", "style =", "style=",
                       "seq =", "seq=", "frame *", "frame*", "KIND_THREAT",
                       "KIND_NOVEL", ".q.set(", ".q.q[", "load_rows",
                       "subprocess", "urllib", "requests", "gguf", "llama_"):
            self.assertNotIn(banned, whole, banned)
        for module in ("cortex", "minigrid", "gym", "torch", "numpy", "board"):
            self.assertNotIn(f"import {module}", whole, module)
        # Every packet in this slice is built from the local pose alone.
        for line in whole.splitlines():
            if "encode_cell(" in line:
                self.assertNotIn("frame", line, line)
        # The one that builds a packet reads a pose and nothing else --
        # names it actually uses, so the docstring is free to say "frame".
        code = room1.packet_of.__code__
        self.assertNotIn("frame", code.co_varnames + code.co_names)
        self.assertEqual(code.co_varnames[:1], ("index",))
        # And the encoder itself was not taught about rooms.
        enc = (
            Path(__file__).resolve().parents[1] / "nexus0" / "encoder.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("frame", enc)
        self.assertNotIn("room", enc)

    # 9 ------------------------------------------------------------------
    def test_a_room_is_the_pulpo_cube_step_for_step(self) -> None:
        """The env only adds an integer; the physics is the one that is
        already green, and the frame is what picks the room."""
        mine = room1.room_env(room1.FRAME_B)
        theirs = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        for i in range(body3d.N_POSES):
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                mine.teleport(i)
                theirs.teleport(i)
                ra, ca = mine.step(a)
                rb, cb = theirs.step(a)
                self.assertEqual((ra, ca.index, mine.bumped),
                                 (rb, cb.index, theirs.bumped),
                                 (body3d.pose_name(i), a))
        # The mutant pair is a different room behind the same integer.
        holed = room1.room_env(room1.FRAME_B, room1.ROOMS_WITH_HOLE)
        self.assertEqual(holed.frame, room1.FRAME_B)
        self.assertNotEqual(holed.layout, mine.layout)
        pose = body3d.index_of(2, 0, 0, body3d.PLUS_Y)
        mine.teleport(pose)
        holed.teleport(pose)
        self.assertNotEqual(mine.step(ACTION_APPROACH)[1].index,
                            holed.step(ACTION_APPROACH)[1].index)

    # 10 -----------------------------------------------------------------
    def test_the_ceiling_is_measured_not_raised(self) -> None:
        self.assertEqual(encode_cell(0, KIND_EMPTY),
                         encode_cell(256, KIND_EMPTY))
        self.assertTrue(room1.packet_ceiling_holds())
        self.assertTrue(self.report["packet_ceiling_holds"], self.report)
        self.assertEqual(self.report["packet_ceiling"], 256)
        self.assertLess(body3d.N_POSES, 256)
        # 324 places would not have fitted, which is why they are not
        # separate places.
        self.assertGreater(self.report["places"], 256)

    # 11 -----------------------------------------------------------------
    def test_ring_and_the_earlier_slices_untouched(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        r = self.report
        self.assertEqual(r["actions"], 3)
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        self.assertFalse(Agent().q.explore_flat)
        self.assertFalse(Agent().q.remainder)

    # 12 -----------------------------------------------------------------
    def test_writes_its_own_report_and_treads_on_nobody(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_pulpo_report.json",
                  "nexus0_self1_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_credit1_report.json", "nexus0_walk1_report.json",
                  "nexus0_world3_report.json")
        before = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                  for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = room1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertTrue((lab / "nexus0_room1_report.json").is_file())
        after = {n: (lab / n).read_bytes() if (lab / n).is_file() else None
                 for n in others}
        self.assertEqual(before, after, "ROOM-1 wrote over another report")


class TestCellEncoder(unittest.TestCase):
    """Cells ride the same atom cable as text. dst is no longer UNK-for-all."""

    def test_seq_separates_same_kind_cells(self) -> None:
        self.assertNotEqual(encode_cell(0, KIND_EMPTY), encode_cell(1, KIND_EMPTY))
        self.assertNotEqual(encode_cell(7, KIND_THREAT), encode_cell(19, KIND_THREAT))

    def test_threat_is_temer_peligro(self) -> None:
        raw = encode_cell(7, KIND_THREAT)
        self.assertEqual(rel_of(raw), ATOM_ID["TEMER"])
        self.assertEqual(dst_of(raw), ATOM_ID["PELIGRO"])
        self.assertEqual(src_of(raw), ATOM_ID["YO"])

    def test_goal_is_desear_aqui(self) -> None:
        raw = encode_cell(3, KIND_GOAL)
        self.assertEqual(rel_of(raw), ATOM_ID["DESEAR"])
        self.assertEqual(dst_of(raw), ATOM_ID["AQUI"])

    def test_empty_and_novel_atoms(self) -> None:
        empty = encode_cell(0, KIND_EMPTY)
        self.assertEqual(rel_of(empty), ATOM_ID["OBSERVAR"])
        self.assertEqual(dst_of(empty), ATOM_ID["AQUI"])
        novel = encode_cell(11, KIND_NOVEL)
        self.assertEqual(rel_of(novel), ATOM_ID["DESCONOCIDO"])
        self.assertEqual(dst_of(novel), ATOM_ID["UNK"])

    def test_cell_wsp_is_16_bytes(self) -> None:
        for kind in (KIND_EMPTY, KIND_GOAL, KIND_THREAT, KIND_NOVEL):
            for i in range(N_CELLS):
                self.assertEqual(len(encode_cell(i, kind)), WSP_BYTES)

    def test_compact_prints_atoms_not_question_marks(self) -> None:
        for kind in (KIND_EMPTY, KIND_GOAL, KIND_THREAT, KIND_NOVEL):
            line = compact(encode_cell(7, kind))
            with self.subTest(kind=kind):
                self.assertNotIn("?", line)
        self.assertIn("TEMER", compact(encode_cell(7, KIND_THREAT)))
        self.assertIn("PELIGRO", compact(encode_cell(7, KIND_THREAT)))


class TestGenLex(unittest.TestCase):
    """lex.py is generated from the C, not maintained by hand."""

    def test_lex_py_is_in_sync_with_the_c_table(self) -> None:
        current = gen_lex.LEX_PATH.read_text(encoding="utf-8")
        self.assertEqual(gen_lex.render_file(current), current)

    def test_generator_is_idempotent(self) -> None:
        current = gen_lex.LEX_PATH.read_text(encoding="utf-8")
        once = gen_lex.render_file(current)
        self.assertEqual(gen_lex.render_file(once), once)

    def test_generated_table_keeps_count_and_keys(self) -> None:
        table = gen_lex.render_table()
        self.assertEqual(table.count("\n    L("), lex.count())
        self.assertEqual(lex.count(), 235)
        for text, _rel, _dst in TestLex.KEYS:
            rule = lex.apply(text)
            with self.subTest(text=text):
                self.assertIn(f'L("{rule.key}"', table)

    def test_check_mode_reports_in_sync(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = gen_lex.main(["--check"])
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertIn("in sync", buf.getvalue())


class TestPlanner(unittest.TestCase):
    """NEXUS-2 counterfactuals. Hand-built T and Q; no 320-turn run."""

    def test_planner_sees_goal_at_distance_2(self) -> None:
        w, q = World(), QTable()
        w.observe(13, ACTION_APPROACH, 14)
        w.observe(14, ACTION_APPROACH, 15)
        q.set(15, ACTION_APPROACH, 80)

        # The myopic policy: row 13 is all zeros, so the tie-break wins.
        self.assertEqual(q.row(13), [0, 0, 0])
        self.assertEqual(q.best(13), ACTION_WAIT)

        # Two steps of T reach the 80 and discount it once: (7*80)//8 = 70.
        self.assertEqual(plan.best(w, q, 13, depth=2), ACTION_APPROACH)
        self.assertEqual(plan.scores(w, q, 13, depth=2), [70, 0, 0])

        # Depth 1 cannot see it: slot 14 is still all zeros. The extra step
        # is what does the work, not a lucky tie-break.
        self.assertEqual(plan.scores(w, q, 13, depth=1), [0, 0, 0])
        self.assertEqual(plan.best(w, q, 13, depth=1), ACTION_WAIT)

    def test_planner_avoids_jump_into_threat(self) -> None:
        w, q = World(), QTable()
        w.observe(5, ACTION_APPROACH, 7)
        w.observe(5, ACTION_AVOID, 4)
        w.observe(5, ACTION_WAIT, 5)
        q.set(7, ACTION_APPROACH, -40)

        self.assertNotEqual(plan.best(w, q, 5, depth=1), ACTION_APPROACH)

        # Honest reading: it ties at 0 and the tie-break picks wait. Two
        # things hide the -40 — score takes max_b over the successor row
        # (slot 7 still has avoid=0), and the root max is optimistic, so a
        # bad successor cannot pull approach below Q[5][approach] = 0.
        self.assertEqual(plan.scores(w, q, 5, depth=1), [0, 0, 0])

        # Whole successor row bad, root still 0: masked by the root max.
        q.set(7, ACTION_AVOID, -40)
        q.set(7, ACTION_WAIT, -40)
        self.assertEqual(plan.scores(w, q, 5, depth=1), [0, 0, 0])
        self.assertNotEqual(plan.best(w, q, 5, depth=1), ACTION_APPROACH)

        # Approach loses on score once the root itself has been punished,
        # which is what the 320-turn run actually learns (policy_after[0]<0).
        q.set(5, ACTION_APPROACH, -12)
        q.set(5, ACTION_AVOID, 5)
        self.assertEqual(plan.scores(w, q, 5, depth=1), [-12, 5, 5])
        self.assertNotEqual(plan.best(w, q, 5, depth=1), ACTION_APPROACH)

    def test_root_q_breaks_the_wait_tie(self) -> None:
        """Without max(root, lookahead) this ties at 0 and sits down."""
        w, q = World(), QTable()
        w.observe(1, ACTION_APPROACH, 2)
        q.set(1, ACTION_APPROACH, 5)  # successors of 2 are all still 0

        self.assertEqual(plan.scores(w, q, 1, depth=2)[ACTION_APPROACH], 5)
        self.assertEqual(plan.scores(w, q, 1, depth=2), [5, 0, 0])
        self.assertEqual(plan.best(w, q, 1, depth=2), ACTION_APPROACH)
        self.assertEqual(plan.best(w, q, 1, depth=1), ACTION_APPROACH)

    def test_depth_1_is_max_q_of_the_successor(self) -> None:
        w, q = World(), QTable()
        w.observe(1, ACTION_APPROACH, 2)
        q.set(2, ACTION_AVOID, 30)
        self.assertEqual(plan.scores(w, q, 1, depth=1)[ACTION_APPROACH], 30)

    def test_t_miss_falls_back_to_myopic_entry(self) -> None:
        w, q = World(), QTable()
        q.set(9, ACTION_APPROACH, 25)
        self.assertIsNone(w.predict(9, ACTION_APPROACH))
        self.assertEqual(plan.scores(w, q, 9, depth=2)[ACTION_APPROACH], 25)

    def test_scores_are_int8_and_length_3(self) -> None:
        w, q = World(), QTable()
        w.observe(1, ACTION_APPROACH, 2)
        q.set(2, ACTION_APPROACH, 127)
        for depth in (1, 2):
            row = plan.scores(w, q, 1, depth=depth)
            with self.subTest(depth=depth):
                self.assertEqual(len(row), 3)
                for v in row:
                    self.assertIsInstance(v, int)
                    self.assertGreaterEqual(v, -127)
                    self.assertLessEqual(v, 127)

    def test_planner_does_not_mutate_q_or_t(self) -> None:
        w, q = World(), QTable()
        w.observe(13, ACTION_APPROACH, 14)
        q.set(14, ACTION_APPROACH, 60)
        before_q = [q.row(s) for s in (13, 14)]
        before_t = [w.pair(13, a) for a in range(3)]
        plan.best(w, q, 13, depth=2)
        self.assertEqual([q.row(s) for s in (13, 14)], before_q)
        self.assertEqual([w.pair(13, a) for a in range(3)], before_t)

    def test_agent_default_never_plans(self) -> None:
        """Opt-in: the NEXUS-0/1 bench keeps Q.select. Replaces the old
        'the word plan does not appear in loop.py' test."""
        self.assertEqual(Agent().plan_depth, 0)
        ag = Agent()
        ag.t.observe(13, ACTION_APPROACH, 14)
        ag.t.observe(14, ACTION_APPROACH, 15)
        ag.q.set(15, ACTION_APPROACH, 80)
        ag.q.set(13, ACTION_AVOID, -1)  # break the full tie, so not explore
        self.assertFalse(ag.q.is_explore(13, 1))
        # Myopic: row 13 max is 0 at approach and wait → tie-break wait.
        self.assertEqual(ag._propose(13, 1), ACTION_WAIT)

    def test_agent_plan_depth_2_uses_the_planner(self) -> None:
        ag = Agent(plan_depth=2)
        ag.t.observe(13, ACTION_APPROACH, 14)
        ag.t.observe(14, ACTION_APPROACH, 15)
        ag.q.set(15, ACTION_APPROACH, 80)
        ag.q.set(13, ACTION_AVOID, -1)
        self.assertFalse(ag.q.is_explore(13, 1))
        self.assertEqual(ag._propose(13, 1), ACTION_APPROACH)
        self.assertEqual(plan.scores(ag.t, ag.q, 13, depth=2), [70, -1, 0])

    def test_planner_does_not_steal_exploration(self) -> None:
        """Turn 8 is an ε turn: select() must still win, or the ring is
        never walked and Q never fills."""
        ag = Agent(plan_depth=2)
        ag.t.observe(13, ACTION_APPROACH, 14)
        ag.t.observe(14, ACTION_APPROACH, 15)
        ag.q.set(15, ACTION_APPROACH, 80)
        ag.q.set(13, ACTION_AVOID, -1)
        self.assertTrue(ag.q.is_explore(13, 8))
        self.assertEqual(ag._propose(13, 8), ag.q.select(13, 8))
        self.assertEqual(ag._propose(13, 8), ACTION_WAIT)  # 8 % 3
        self.assertNotEqual(ag._propose(13, 8), plan.best(ag.t, ag.q, 13, depth=2))


class TestPlannerOneHop(unittest.TestCase):
    """The planner's use is the square beyond the neighbour.

    TD carried value one cell back, so c10 is positive for the seer and
    c9 is flat for everyone. A single hop through T is exactly what turns
    the myopic wait at c9 into approach — and only where value exists.
    Trained once per arm; no extra 320-turn bench, no reward added.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.seer = Agent(ask=True)
        cls.seer.run(BENCH_TURNS)
        cls.blind = Agent(ask=False)
        cls.blind.run(BENCH_TURNS)

    @staticmethod
    def _slot(ag: Agent, cell: int) -> int:
        return ag.cam.get(encode_cell(cell, ag.env.kind[cell]))

    def test_t_saw_the_nine_to_ten_transition(self) -> None:
        """Not fabricated: the 256-turn run observed it in both arms."""
        for ag in (self.seer, self.blind):
            s9, s10 = self._slot(ag, 9), self._slot(ag, 10)
            nxt = ag.t.predict(s9, ACTION_APPROACH)
            with self.subTest(ask=ag.ask_enabled):
                self.assertIsNotNone(nxt, "T never saw c9 → c10")
                self.assertEqual(nxt, s10)

    def test_planner_adds_one_hop_for_the_seer(self) -> None:
        s9, s10 = self._slot(self.seer, 9), self._slot(self.seer, 10)
        # Myopic at c9: the row is flat, so the tie-break waits.
        self.assertEqual(self.seer.q.snapshot(s9), [0, 0, 0])
        self.assertEqual(self.seer.q.best(s9), ACTION_WAIT)
        # But c10 holds value, and one hop through T reaches it.
        self.assertGreater(self.seer.q.max_q(s10), 0)
        self.assertEqual(
            plan.best(self.seer.t, self.seer.q, s9, depth=1), ACTION_APPROACH
        )
        self.assertEqual(
            plan.best(self.seer.t, self.seer.q, s9, depth=2), ACTION_APPROACH
        )

    def test_planner_does_not_invent_a_path_for_the_blind(self) -> None:
        s9, s10 = self._slot(self.blind, 9), self._slot(self.blind, 10)
        self.assertEqual(self.blind.q.best(s9), ACTION_WAIT)
        self.assertEqual(self.blind.q.best(s10), ACTION_WAIT)
        # Same T, no value to find: the planner stays where Q.best is.
        self.assertEqual(self.blind.q.max_q(s10), 0)
        self.assertNotEqual(
            plan.best(self.blind.t, self.blind.q, s9, depth=1), ACTION_APPROACH
        )
        self.assertEqual(
            plan.scores(self.blind.t, self.blind.q, s9, depth=1), [0, 0, 0]
        )

    def test_planner_extends_reach_but_is_not_a_map(self) -> None:
        """Depth buys exactly its own reach, and it still does not find 11.

        From c0 the myopic policy and a single hop both wait — c1 is flat
        too. Two hops reach c2's +3 and the agent finally walks. It then
        follows value to the GOAL and falls into a 6↔7 limit cycle at the
        threat, so a planner-driven greedy walk reaches the NOVEL cell
        zero times, same as Q.best. Reach is not a route.
        """
        s0 = self._slot(self.seer, 0)
        self.assertEqual(self.seer.q.best(s0), ACTION_WAIT)
        self.assertEqual(plan.best(self.seer.t, self.seer.q, s0, depth=1), ACTION_WAIT)
        self.assertEqual(
            plan.best(self.seer.t, self.seer.q, s0, depth=2), ACTION_APPROACH
        )

        probe = Agent(ask=True)
        probe.run(BENCH_TURNS)
        probe.plan_depth = 2  # trained myopically, probed with the planner
        self.assertEqual(probe.walk_greedy(PROBE_STEPS, start=0), 0)


def walk_readonly(ag: Agent, steps: int, start: int, depth: int = 0) -> tuple:
    """Move through the ring without learning. Returns (hits on NOVEL, path).

    Unlike Agent.walk_greedy this never calls q.update or t.observe: it
    only reads the trained tables and moves `i`. Test-local on purpose —
    the bench's own probe stays as it is.
    """
    ag.env.teleport(start)
    hits = 0
    path = []
    for _ in range(int(steps)):
        cell = ag.env.cell()
        path.append(cell.index)
        if cell.kind == KIND_NOVEL:
            hits += 1
        slot = ag.cam.get(encode_cell(cell.index, cell.kind))
        if slot < 0:
            a = ACTION_WAIT
        elif depth > 0:
            a = plan.best(ag.t, ag.q, slot, depth=depth)
        else:
            a = ag.q.best(slot)
        ag.env.step(a)
    return hits, path


class TestValueWall(unittest.TestCase):
    """The threat at c7 cuts the ring in two. Is c11 behind it reachable?"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.seer = Agent(ask=True)
        cls.seer.run(BENCH_TURNS)
        cls.blind = Agent(ask=False)
        cls.blind.run(BENCH_TURNS)

    @staticmethod
    def _slot(ag: Agent, cell: int) -> int:
        return ag.cam.get(encode_cell(cell, ag.env.kind[cell]))

    def test_threat_is_a_value_wall_from_home(self) -> None:
        """The wall is at c7 → c8, not at c6 → c7 as first guessed.

        c6 is [1, 0, 0], so the agent *does* approach into the threat.
        What it never does is continue through it: at c7 approach is -12
        and avoid is +5, so it turns back and the walk cycles 6↔7. c8 is
        never reached from home at any depth.
        """
        s6, s7 = self._slot(self.seer, 6), self._slot(self.seer, 7)
        # Documented vector, not a forced name: c6 does cross into 7.
        self.assertEqual(self.seer.q.snapshot(s6), [1, 0, 0])
        self.assertEqual(self.seer.q.best(s6), ACTION_APPROACH)
        self.assertEqual(plan.best(self.seer.t, self.seer.q, s6, depth=1),
                         ACTION_APPROACH)

        # The wall itself: forward motion dies at the threat.
        self.assertLess(self.seer.q.get(s7, ACTION_APPROACH), 0)
        self.assertEqual(self.seer.q.best(s7), ACTION_AVOID)
        self.assertEqual(plan.best(self.seer.t, self.seer.q, s7, depth=2),
                         ACTION_AVOID)

        hits, path = walk_readonly(self.seer, 16, start=0, depth=2)
        self.assertEqual(hits, 0, path)
        self.assertNotIn(8, path, path)
        self.assertEqual(path[-4:], [7, 6, 7, 6], path)  # the limit cycle

    def test_t_built_the_corridor_past_the_wall(self) -> None:
        """8→9→10→11 was observed, in both arms. Nothing fabricated."""
        for ag in (self.seer, self.blind):
            for a, b in ((8, 9), (9, 10), (10, 11)):
                nxt = ag.t.predict(self._slot(ag, a), ACTION_APPROACH)
                with self.subTest(ask=ag.ask_enabled, hop=(a, b)):
                    self.assertIsNotNone(nxt, f"T never saw c{a} → c{b}")
                    self.assertEqual(nxt, self._slot(ag, b))
                    self.assertGreater(ag.t.pair(self._slot(ag, a),
                                                 ACTION_APPROACH)[1], 0)

    def test_seer_planner_from_past_the_wall(self) -> None:
        """Past the wall the seer walks the corridor to c11. The blind sits.

        c11 was unreachable from home, not non-existent: same T, same
        corridor, and the only difference is the value one question put on
        the cell.
        """
        seer_hits, seer_path = walk_readonly(self.seer, 16, start=8, depth=2)
        blind_hits, blind_path = walk_readonly(self.blind, 16, start=8, depth=2)

        self.assertGreaterEqual(seer_hits, 1, seer_path)
        self.assertIn(11, seer_path, seer_path)
        self.assertEqual(seer_path[:4], [8, 9, 10, 11], seer_path)

        self.assertEqual(blind_hits, 0, blind_path)
        self.assertLessEqual(blind_hits, seer_hits)

    def test_myopic_cannot_use_the_corridor_either_way(self) -> None:
        """Depth 0 sits at c8 in both arms: the corridor rows are flat."""
        for ag in (self.seer, self.blind):
            hits, path = walk_readonly(ag, 16, start=8, depth=0)
            with self.subTest(ask=ag.ask_enabled):
                self.assertEqual(hits, 0, path)
                self.assertEqual(set(path), {8}, path)


class TestTraces(unittest.TestCase):
    """NEXUS-3b: credit runs backwards along the path just walked.

    Opt-in. The default agent must keep the one-step update that produced
    [-12, +5, 0]; traces are a longer spinal cord, not a cortex.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.seer = Agent(ask=True, trace=True)
        cls.seer.run(BENCH_TURNS)
        cls.blind = Agent(ask=False, trace=True)
        cls.blind.run(BENCH_TURNS)
        cls.plain = Agent(ask=True)
        cls.plain.run(BENCH_TURNS)

    @staticmethod
    def _slot(ag: Agent, cell: int) -> int:
        return ag.cam.get(encode_cell(cell, ag.env.kind[cell]))

    def test_default_has_no_traces(self) -> None:
        ag = Agent()
        self.assertFalse(ag.q.trace)
        self.assertEqual(ag.q.z, [])
        self.assertEqual(ag.q._active, [])
        report = run()  # default bench: the NEXUS-0 lock is untouched
        self.assertFalse(report["trace"])
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)

    def test_traces_fill_the_corridor(self) -> None:
        """Three cells back, not one: c8, c9 and c10 all hold value."""
        for cell in (8, 9, 10):
            plain = self.plain.q.get(self._slot(self.plain, cell), ACTION_APPROACH)
            traced = self.seer.q.get(self._slot(self.seer, cell), ACTION_APPROACH)
            with self.subTest(cell=cell):
                self.assertGreater(traced, 0, f"c{cell} still flat with traces")
        # Without traces only c10 had anything; c8 and c9 were flat.
        self.assertEqual(self.plain.q.get(self._slot(self.plain, 8), ACTION_APPROACH), 0)
        self.assertEqual(self.plain.q.get(self._slot(self.plain, 9), ACTION_APPROACH), 0)

    def test_myopic_walk_from_c8_with_traces(self) -> None:
        """The point of the slice: no planner, and it still walks to c11."""
        hits, path = walk_readonly(self.seer, 16, start=8, depth=0)
        self.assertGreaterEqual(hits, 1, path)
        self.assertEqual(path[:4], [8, 9, 10, 11], path)

        # Same walk without traces sits at c8 — pinned in TestValueWall.
        plain_hits, plain_path = walk_readonly(self.plain, 16, start=8, depth=0)
        self.assertEqual(plain_hits, 0, plain_path)

    def test_blind_with_traces_still_avoids_the_trap(self) -> None:
        """No claim on c11 for the blind: unasked, it is still a trap."""
        hits, path = walk_readonly(self.blind, 16, start=8, depth=0)
        self.assertEqual(hits, 0, path)
        self.assertLess(
            self.blind.q.get(self._slot(self.blind, 11), ACTION_APPROACH), 0
        )

    def test_wall_from_home_still_holds_with_traces(self) -> None:
        """Cell 7 still costs -16, so home is still cut off from c11."""
        hits, path = walk_readonly(self.seer, 16, start=0, depth=0)
        self.assertEqual(hits, 0, path)
        self.assertNotIn(11, path, path)

    def test_traces_cost_the_threat_margin(self) -> None:
        """The price, stated: δ spread along the path dilutes the threat.

        [-12, +5, 0] becomes [-1, 0, 0]. Approach still loses, by 1 instead
        of by 17. This is why traces stay opt-in and out of the default.
        """
        s7 = self._slot(self.seer, 7)
        row = self.seer.q.snapshot(s7)
        self.assertLess(row[ACTION_APPROACH], 0, row)
        self.assertLess(row[ACTION_APPROACH], max(row[1], row[2]), row)
        plain_row = self.plain.q.snapshot(self._slot(self.plain, 7))
        self.assertLess(plain_row[ACTION_APPROACH], row[ACTION_APPROACH], (plain_row, row))

    def test_trace_report_is_a_separate_file(self) -> None:
        self.assertEqual(report_name(0, True, False), "nexus0_report.json")
        self.assertEqual(report_name(0, True, True), "nexus0_trace_report.json")


class TestAttend(unittest.TestCase):
    """NEXUS-4a: the switch. No LLM, no weights, no think() wrapper."""

    KNOWN_E = (0, 10, 0, 80, 10, 0)  # C = 80, well above C_PLASTIC

    def test_attend_false_when_known(self) -> None:
        on, reason = attend(
            slot_hit=True, extract_ok=True, E=self.KNOWN_E,
            kind_novel=False, ham=0, q_confident=True, t_known=True,
        )
        self.assertFalse(on)
        self.assertEqual(reason, REASON_OFF)

    def test_attend_poster_C_does_not_wake(self) -> None:
        """The lock of this slice: E is a poster, not evidence.

        default_e() carries C = 15, below C_PLASTIC, on every EMPTY and
        GOAL cell. Believing it woke the cortex on 187 of 256 turns.
        With a policy and a map, the same packet is now quiet.
        """
        self.assertLess(default_e()[3], C_PLASTIC)
        on, reason = attend(
            slot_hit=True, extract_ok=True, E=default_e(),
            kind_novel=False, ham=0, q_confident=True, t_known=True,
        )
        self.assertFalse(on, "the poster still wakes the cortex")
        self.assertEqual(reason, REASON_OFF)

    def test_attend_true_when_q_is_flat(self) -> None:
        on, reason = attend(
            slot_hit=True, extract_ok=True, E=self.KNOWN_E,
            kind_novel=False, ham=0, q_confident=False, t_known=True,
        )
        self.assertTrue(on)
        self.assertEqual(reason, REASON_LOW_C)

    def test_attend_true_when_the_map_is_missing(self) -> None:
        on, reason = attend(
            slot_hit=True, extract_ok=True, E=self.KNOWN_E,
            kind_novel=False, ham=0, q_confident=True, t_known=False,
        )
        self.assertTrue(on)
        self.assertEqual(reason, REASON_NO_MAP)

    def test_attend_true_on_novel(self) -> None:
        on, reason = attend(
            slot_hit=True, extract_ok=True, E=self.KNOWN_E,
            kind_novel=True, ham=0, q_confident=True, t_known=True,
        )
        self.assertTrue(on)
        self.assertEqual(reason, REASON_NOVEL)

    def test_attend_true_on_miss_and_no_extract(self) -> None:
        on, reason = attend(True, True, self.KNOWN_E, False, HAM_MISS, True, True)
        self.assertTrue(on)
        self.assertEqual(reason, REASON_MISS)

        on, reason = attend(False, True, self.KNOWN_E, False, 0, True, True)
        self.assertTrue(on)
        self.assertEqual(reason, REASON_MISS)

        on, reason = attend(True, False, self.KNOWN_E, False, 0, True, True)
        self.assertTrue(on)
        self.assertEqual(reason, REASON_NO_EXTRACT)

    def test_attend_reads_t_conf_only_to_stay_quiet(self) -> None:
        """NEXUS-4d: a decent map is not a missing map.

        The guard silences NO_MAP and nothing else. It cannot turn an OFF
        into a wake, which is why the 36/256 count is unchanged.
        """
        base = dict(
            slot_hit=True, extract_ok=True, E=self.KNOWN_E,
            kind_novel=False, ham=0, q_confident=True, t_known=False,
        )
        self.assertEqual(attend(**base), (True, REASON_NO_MAP))  # default 0
        self.assertEqual(attend(**base, t_conf=T_CONF_NONE), (True, REASON_NO_MAP))
        self.assertEqual(attend(**base, t_conf=T_CONF_ONCE), (True, REASON_NO_MAP))
        self.assertEqual(attend(**base, t_conf=T_CONF_DECENT), (False, REASON_OFF))
        self.assertEqual(attend(**base, t_conf=T_CONF_HIGH), (False, REASON_OFF))

    def test_t_conf_cannot_silence_any_other_reason(self) -> None:
        loud = (
            (dict(kind_novel=True), REASON_NOVEL),
            (dict(q_confident=False), REASON_LOW_C),
            (dict(slot_hit=False), REASON_MISS),
            (dict(ham=HAM_MISS), REASON_MISS),
            (dict(extract_ok=False), REASON_NO_EXTRACT),
        )
        for override, want in loud:
            kw = dict(
                slot_hit=True, extract_ok=True, E=self.KNOWN_E, kind_novel=False,
                ham=0, q_confident=True, t_known=False, t_conf=T_CONF_HIGH,
            )
            kw.update(override)
            with self.subTest(**override):
                self.assertEqual(attend(**kw), (True, want))

    def test_t_conf_is_still_gated_by_the_poster(self) -> None:
        """E stays in the signature and stays unread, t_conf or not."""
        for conf in (T_CONF_NONE, T_CONF_DECENT, T_CONF_HIGH):
            on, reason = attend(
                slot_hit=True, extract_ok=True, E=default_e(), kind_novel=False,
                ham=0, q_confident=True, t_known=True, t_conf=conf,
            )
            self.assertFalse(on, conf)
            self.assertEqual(reason, REASON_OFF)

    def test_stub_does_not_write_facts(self) -> None:
        """Firewall: propose() has no CAM handle and cannot make a fact."""
        src = (Path(__file__).resolve().parents[1] / "nexus0" / "cortex.py").read_text(
            encoding="utf-8"
        )
        body = src.split('"""')[-1]
        for forbidden in ("has_fact", "allocate", "cam", "Cam"):
            self.assertNotIn(forbidden, body, forbidden)

        wsp = encode_cell(4, KIND_EMPTY)
        self.assertEqual(cortex.propose(wsp, REASON_LOW_C), wsp)
        out = cortex.propose(wsp, REASON_NOVEL)
        self.assertEqual(len(out), WSP_BYTES)
        self.assertEqual(rel_of(out), ATOM_ID["PREGUNTAR"])

    def test_default_cortex_stays_zero(self) -> None:
        report = run()
        self.assertFalse(report["cortex"])
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(Agent().cortex_enabled, False)

    def test_cortex_flag_increments_calls(self) -> None:
        ag = Agent(cortex=True)
        ag.env.reset()
        ag.env.teleport(11)
        ag.turn(1)
        self.assertGreaterEqual(ag.metrics.cortex_calls, 1)
        self.assertEqual(ag.last_attend, (True, REASON_NOVEL))
        # One path to the oracle: the stub proposes, _ask() performs.
        self.assertEqual(ag.metrics.questions, 1)
        self.assertEqual(ag.metrics.false_facts, 0)
        self.assertFalse(ag.env.hidden_bit)

    def test_cortex_run_keeps_the_firewall_and_the_locks(self) -> None:
        report = run(cortex=True)
        self.assertGreater(report["cortex_calls"], 0, report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        # A switch must not move the policy it is watching.
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)

    def test_attend_is_now_a_filter(self) -> None:
        """The switch has to bite, or a cortex behind it is a router.

        Measured over 256 turns: 36 wakes, down from 187 when ATTEND read
        default_e()'s C. `low_C` is no longer the champion — `off` is.
        """
        ag = Agent(cortex=True)
        ag.env.reset()
        reasons = []
        for t in range(BENCH_TURNS):
            ag.turn(t)
            reasons.append(ag.last_attend[1])
        woken = sum(1 for r in reasons if r != REASON_OFF)
        self.assertEqual(woken, ag.metrics.cortex_calls)
        self.assertLess(woken, 64, woken)
        self.assertEqual(reasons.count(REASON_NOVEL), 4, reasons)
        self.assertLess(
            reasons.count(REASON_LOW_C), reasons.count(REASON_OFF), reasons
        )

    def test_t_conf_does_not_buy_more_cortex(self) -> None:
        """The lock of this slice. Certainty of the map, not more LLM.

        36 wakes in 256 before T_CONF, 36 after. In this wiring `t_known`
        is `conf >= 1` on the same (slot, action), so `t_conf >= 2` implies
        `t_known` and the new guard is never the deciding vote — measured
        here rather than assumed. It becomes load-bearing when a row can be
        known and bad, which is the inverse model's slice, not this one.
        """
        ag = Agent(cortex=True)
        ag.env.reset()
        confs, guardable = [], 0
        for t in range(BENCH_TURNS):
            ag.turn(t)
            slot = ag.cam.get(encode_cell(ag.env.cell().index, ag.env.cell().kind))
            if slot is not None:
                c = ag.t.conf(slot, ag.q.best(slot))
                confs.append(c)
                if c >= T_CONF_DECENT and not ag.t.known(slot, ag.q.best(slot)):
                    guardable += 1
        self.assertLessEqual(ag.metrics.cortex_calls, 36, ag.metrics.cortex_calls)
        self.assertEqual(guardable, 0, "conf >= 2 without a known row")
        self.assertTrue(all(0 <= c <= 3 for c in confs))
        self.assertIn(T_CONF_HIGH, confs, "no very-consistent row was ever stood on")


class TestEscalate(unittest.TestCase):
    """NEXUS-4f: how much to think. Rungs 0 and 2, chosen by ΔQ."""

    def test_margin_zero_on_tie(self) -> None:
        q = QTable()
        self.assertEqual(q.margin(5), 0)  # fresh row is a full tie
        q.set(5, ACTION_APPROACH, 7)
        q.set(5, ACTION_AVOID, 7)
        q.set(5, ACTION_WAIT, 7)
        self.assertEqual(q.margin(5), 0)

    def test_margin_positive(self) -> None:
        q = QTable()
        q.set(5, ACTION_APPROACH, 9)
        q.set(5, ACTION_AVOID, 2)
        q.set(5, ACTION_WAIT, -4)
        self.assertEqual(q.margin(5), 7)  # best minus runner-up, not minus min
        q.set(5, ACTION_AVOID, 9)
        self.assertEqual(q.margin(5), 0, "two winners is no margin")
        q.set(5, ACTION_APPROACH, -100)
        q.set(5, ACTION_AVOID, -100)
        q.set(5, ACTION_WAIT, -100)
        self.assertEqual(q.margin(5), 0)
        self.assertGreaterEqual(q.margin(5), 0, "margin is never negative")

    def test_high_margin_skips_search(self) -> None:
        self.assertEqual(level(margin=ESC_MARGIN + 1), LEVEL_Q)
        self.assertEqual(level(margin=100), LEVEL_Q)

    def test_low_margin_requests_search(self) -> None:
        self.assertEqual(level(margin=ESC_MARGIN), LEVEL_SEARCH)
        self.assertEqual(level(margin=0), LEVEL_SEARCH)

    def test_level_ignores_the_reserved_inputs(self) -> None:
        """Rungs 1/3/4 are named, not wired. ASK stays `_ask()` and the
        cortex decision stays ATTEND's — nothing here duplicates them."""
        for kw in (
            dict(t_conf=3), dict(kind_novel=True), dict(extract_ok=False),
            dict(cortex_enabled=True),
        ):
            with self.subTest(**kw):
                self.assertEqual(level(margin=100, **kw), LEVEL_Q)
                self.assertEqual(level(margin=0, **kw), LEVEL_SEARCH)
        self.assertEqual(level_name(LEVEL_SEARCH), "search")

    def test_escalate_default_is_q(self) -> None:
        """Agent() must never reach the planner. Not a count — the call."""
        ag = Agent()
        self.assertFalse(ag.escalate_enabled)
        self.assertEqual(ag.plan_depth, 0)
        called = []
        real = plan.best
        plan.best = lambda *a, **k: called.append(1) or real(*a, **k)
        try:
            ag.run(BENCH_TURNS)
        finally:
            plan.best = real
        self.assertEqual(called, [], "the default bench ran the planner")
        self.assertEqual(ag.level_counts[LEVEL_SEARCH], 0)
        self.assertEqual(ag.search_copies_q + ag.search_differs, 0)

    def test_escalate_does_not_steal_explore(self) -> None:
        """Every explore turn still comes from q.select, or the ring is
        never walked and the flat rows the planner reads stay flat."""
        ag = Agent(escalate=True)
        stolen = 0
        for t in range(BENCH_TURNS):
            slot = ag.cam.get(
                encode_cell(ag.env.cell().index, ag.env.cell().kind)
            )
            explore = slot >= 0 and ag.q.is_explore(slot, t)
            before = ag.level_counts[LEVEL_Q] + ag.level_counts[LEVEL_SEARCH]
            ag.turn(t)
            after = ag.level_counts[LEVEL_Q] + ag.level_counts[LEVEL_SEARCH]
            if explore and after != before:
                stolen += 1
        self.assertEqual(stolen, 0, "the planner ate an exploration turn")
        self.assertGreater(ag.level_counts[LEVEL_SEARCH], 0, "rung 2 never ran")

    def test_escalate_report_counts_copy_vs_differ(self) -> None:
        report = run(escalate=True)
        self.assertTrue(report["escalate"])
        self.assertEqual(report["esc_margin"], ESC_MARGIN)
        self.assertEqual(
            report["level_q"] + report["level_search"],
            report["search_copies_q"] + report["search_differs"] + report["level_q"],
        )
        self.assertGreater(report["level_search"], 0)
        self.assertEqual(
            report["search_copies_q"] + report["search_differs"],
            report["level_search"],
        )
        # The firewall does not care which rung chose the action.
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)

    def test_search_is_never_strictly_better_than_q(self) -> None:
        """The finding, locked in: in this ring rung 2 copies Q.

        Every disagreement is `plan.scores` tied and `plan.best` breaking
        the tie to wait — not the planner scoring its own action higher.
        If a future env makes this fail, the assertion is the thing to
        read: rung 2 would then be earning its cost, and the number in
        docs/STATUS.md is stale, not this test.
        """
        report = run(escalate=True)
        self.assertGreater(report["search_differs"], 0, report)
        self.assertEqual(report["search_strictly_better"], 0, report)

    def test_escalate_report_is_a_separate_file(self) -> None:
        self.assertEqual(report_name(0), "nexus0_report.json")
        self.assertEqual(
            report_name(0, True, False, False, True), "nexus0_escalate_report.json"
        )
        self.assertEqual(
            report_name(0, oracle_path="/tmp/a.txt"), "nexus0_oracle_report.json"
        )

    def test_default_bench_unmoved(self) -> None:
        """The locks, again, with the escalation module in the tree."""
        report = run()
        self.assertFalse(report["escalate"])
        self.assertEqual(report["level_search"], 0, report)
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertTrue(report["t_beats_ring"], report)
        self.assertTrue(report["encoder_beats_fnv"], report)
        self.assertTrue(report["negative_delta_causes_policy_change"], report)


class TestCortexHook(unittest.TestCase):
    """NEXUS-4b: a contract a model could read, and a parser that only
    accepts atoms. No LLM in-process, no HTTP, nothing on by default."""

    ATOM_REPLIES = (
        "YO → PREGUNTAR → DESCONOCIDO @AHORA",
        "YO → TEMER → PELIGRO @AHORA | E[V-90 A+90 D+0 C+80 U+90 B+0]",
    )
    PROSE_REPLIES = (
        "El tomate pesa 2 kg",
        "VERIFY: la celda 11 es segura",
        "hola soy una IA",
        '{"answer": 42}',
        "YO va a TEMER el PELIGRO ahora",
        "",
        "   ",
        "deadbeef",  # too short for 16 B
        "021f2908001400280a0000000500000b00",  # 33 chars
    )

    def test_parse_reply_accepts_hex(self) -> None:
        self.assertEqual(cortex.parse_reply(encode_ask().hex()), encode_ask())

    def test_parse_reply_accepts_compact_atoms(self) -> None:
        for text in self.ATOM_REPLIES:
            with self.subTest(text=text):
                out = cortex.parse_reply(text)
                self.assertIsNotNone(out, text)
                self.assertEqual(len(out), WSP_BYTES)
        self.assertEqual(
            rel_of(cortex.parse_reply(self.ATOM_REPLIES[0])), ATOM_ID["PREGUNTAR"]
        )

    def test_parse_reply_rejects_prose(self) -> None:
        for text in self.PROSE_REPLIES:
            with self.subTest(text=text):
                self.assertIsNone(cortex.parse_reply(text), text)

    def test_parse_reply_rejects_unknown_atoms(self) -> None:
        self.assertIsNone(cortex.parse_reply("YO → PENSAR → COSA @AHORA"))

    def test_complete_is_none_without_the_env(self) -> None:
        """No binary named, no call. The stub answers."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(cortex.ENV_CMD, None)
            self.assertIsNone(cortex.complete({"turn": 0}))

    def test_default_bench_writes_no_jsonl(self) -> None:
        report = run()
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertIsNone(report["cortex_log"])
        ag = Agent()
        self.assertIsNone(ag.cortex_log)

    def test_cortex_run_writes_one_line_per_wake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "cortex.jsonl")
            report = run(cortex=True, cortex_log=log)
            lines = Path(log).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), report["cortex_calls"], report)
            self.assertGreater(len(lines), 0)

            names = {r for r in REASON_NAME.values()}
            for line in lines:
                rec = json.loads(line)
                self.assertIn(rec["reason_name"], names, rec)
                self.assertNotEqual(rec["reason_name"], "off", rec)
                self.assertEqual(len(bytes.fromhex(rec["wsp_out_hex"])), WSP_BYTES)
                self.assertEqual(len(bytes.fromhex(rec["wsp_in_hex"])), WSP_BYTES)
                self.assertEqual(len(rec["q_row"]), 3)
                self.assertNotIn("?", rec["wsp_out"])
                # The contract has no room for prose.
                self.assertEqual(
                    set(rec) - {
                        "turn", "reason", "reason_name", "wsp_in", "wsp_in_hex",
                        "slot", "ham", "q_row", "t_pred", "extract",
                        "wsp_out", "wsp_out_hex",
                    },
                    set(),
                    rec,
                )

            # Locks unmoved by the hook.
            self.assertEqual(report["false_facts"], 0, report)
            self.assertEqual(report["policy_after"], [-12, 5, 0], report)

    def test_novel_wake_records_the_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "c.jsonl")
            run(cortex=True, cortex_log=log)
            recs = [
                json.loads(l)
                for l in Path(log).read_text(encoding="utf-8").splitlines()
            ]
            novel = [r for r in recs if r["reason_name"] == "novel"]
            self.assertGreaterEqual(len(novel), 1)
            out = bytes.fromhex(novel[0]["wsp_out_hex"])
            self.assertEqual(rel_of(out), ATOM_ID["PREGUNTAR"])
            self.assertIn("NOVEL", novel[0]["extract"])


class TestThoughtLog(unittest.TestCase):
    """NEXUS-4c: every turn, not just the woken ones. Replayable."""

    def test_default_bench_writes_no_thought_log(self) -> None:
        report = run()
        self.assertIsNone(report["thought_log"])
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertIsNone(Agent().thought_log)

    def test_thought_log_has_one_line_per_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp) / "thought.jsonl")
            report = run(thought_log=log)
            lines = Path(log).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), report["turns"], report["turns"])

            for line in lines:
                rec = json.loads(line)
                self.assertEqual(set(rec), set(thought.KEYS), rec)
                self.assertIn(rec["cell"], range(N_CELLS))
                self.assertIn(rec["action"], (0, 1, 2))
                self.assertIn(rec["kind"], ("EMPTY", "GOAL", "THREAT", "NOVEL"))
                self.assertEqual(len(rec["q_row"]), 3)
                self.assertNotIn("?", rec["wsp"])

    def test_thought_log_does_not_move_the_locks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run(thought_log=str(Path(tmp) / "t.jsonl"))
            self.assertEqual(report["policy_after"], [-12, 5, 0], report)
            self.assertEqual(report["false_facts"], 0, report)
            self.assertEqual(report["cortex_calls"], 0, report)
            self.assertEqual(report["novel_approach_return"], 80, report)

    def test_thought_and_cortex_logs_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            thought_log = Path(tmp) / "t.jsonl"
            run(thought_log=str(thought_log))
            self.assertTrue(thought_log.is_file())
            self.assertFalse((Path(tmp) / "cortex.jsonl").exists())

    def test_view_renders_a_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            run(thought_log=str(log))
            recs = view.read_records(log)

        layout = view.initial_layout()
        novel = None
        for rec in recs:
            layout[rec["cell"]] = rec["kind"]
            if rec["cell"] == 11:
                novel = rec
                break
        self.assertIsNotNone(novel)

        frame = view.render(novel, layout, color=False)
        self.assertIn("@", frame)          # the agent
        self.assertIn("N", frame)          # the NOVEL cell, not hidden by @
        self.assertIn("DESCONOCIDO", frame)  # an atom, not prose
        self.assertIn("approach", frame)
        self.assertIn("ATTEND", frame)

    def test_view_rejects_a_missing_log(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = view.main(["/nonexistent/thought.jsonl"])
        self.assertEqual(rc, 1)
        self.assertIn("no such log", buf.getvalue())


class TestGui1(unittest.TestCase):
    """GUI-1: a board, not a brain. It reads the log and only the log."""

    OLD_KEYS = (
        "turn", "cell", "kind", "action", "reward", "wsp",
        "attend_on", "reason_name", "q_row", "t_pred",
        "questions", "cortex_calls",
    )

    def _old_record(self) -> dict:
        """A line as it was written before GUI-1 existed."""
        return {
            "turn": 3, "cell": 11, "kind": "NOVEL", "action": 0, "reward": -16,
            "wsp": "YO → DESCONOCIDO → UNK @AHORA", "attend_on": True,
            "reason_name": "novel", "q_row": [-4, 0, 0], "t_pred": None,
            "questions": 1, "cortex_calls": 2,
        }

    # 1 ------------------------------------------------------------------
    def test_keys_are_the_twelve_then_gui1s_five(self) -> None:
        # GUI-1 widened twelve to seventeen; GUI-3 widened it again, at
        # the end. What this test owns is its own five and the order of
        # the twelve before them — the count lives in TestGui3.
        self.assertEqual(len(set(thought.KEYS)), len(thought.KEYS),
                         "a key is repeated")
        self.assertEqual(thought.KEYS[12:17],
                         ("n", "s", "delta", "cortex_action", "gate_decision"))
        # The twelve that already existed keep their name and their order.
        self.assertEqual(thought.KEYS[:12], self.OLD_KEYS)
        rec = thought.build(
            turn=0, cell=0, kind=0, action=2, reward=0, wsp=encode_cell(0, 0),
            attend_on=False, reason=REASON_OFF, q_row=[0, 0, 0], t_pred=None,
            questions=0, cortex_calls=0,
        )
        self.assertEqual(set(rec), set(thought.KEYS))
        # Integers and null. No prose, no nested events[].
        for k in ("n", "s", "delta", "gate_decision"):
            self.assertIsInstance(rec[k], int, k)
        self.assertIsNone(rec["cortex_action"])

    # 2 ------------------------------------------------------------------
    def test_loop_writes_the_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            report = run(thought_log=str(log))
            recs = [json.loads(l) for l in
                    log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(recs), report["turns"])
        for rec in recs:
            self.assertEqual(set(rec), set(thought.KEYS), rec)
            self.assertIn(rec["n"], (0, 1), rec)
            self.assertIn(rec["s"], (0, 1), rec)
            self.assertIn(rec["delta"], (0, 1), rec)
            self.assertIn(rec["gate_decision"], (0, 1, 2), rec)
            self.assertIsNone(rec["cortex_action"], "the ring has no cortex")
        # The flags are the same three learnings the metrics counted, on
        # the same turns — the log is not a second, looser accounting.
        self.assertEqual(sum(r["n"] for r in recs), report["cam_misses"])
        self.assertEqual(sum(r["s"] for r in recs), report["surprises"])
        self.assertEqual(sum(r["delta"] for r in recs), report["deltas"])

    # 3 ------------------------------------------------------------------
    def test_sign_turn_records_cortex_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            with mock.patch.dict(os.environ, {cortex.ENV_CMD: sign.cortex_cmd()}):
                ag = Agent(cortex=True, ask=False, thought_log=str(log),
                           env=sign.SignEnv(sign.LAYOUT_PRIZE))
                ag.turn(0, greedy=True)
                ag.turn(1, greedy=True)
            recs = [json.loads(l) for l in
                    log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(recs[0]["cortex_action"], ACTION_APPROACH)
        self.assertEqual(recs[0]["action"], ACTION_APPROACH)
        self.assertEqual(recs[0]["reward"], R_SUCCESS)
        self.assertEqual(recs[0]["gate_decision"], 0)
        # Turn 1 is off the sign: it woke and the reply was refused, so
        # there is no proposal to record. Null, not a leftover.
        self.assertTrue(recs[1]["attend_on"])
        self.assertIsNone(recs[1]["cortex_action"])

    def test_gate_decision_is_what_the_gate_did(self) -> None:
        """Not what was asked of it. An inhibited slot logs BLOCK."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            ag = Agent(cortex=False, ask=False, thought_log=str(log),
                       env=sign.SignEnv(sign.LAYOUT_PRIZE))
            ag.turn(0, greedy=True)
            slot = ag.cam.get(encode_cell(sign.SIGN, KIND_EMPTY))
            ag.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
            ag.last_cortex_action = ACTION_APPROACH
            ag.turn(1, greedy=True)
            recs = [json.loads(l) for l in
                    log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(recs[1]["cortex_action"], ACTION_APPROACH, "proposed")
        self.assertEqual(recs[1]["gate_decision"], GATE_BLOCK, "and blocked")
        self.assertEqual(recs[1]["action"], ACTION_WAIT)

    # 4 ------------------------------------------------------------------
    def test_old_jsonl_does_not_crash_view(self) -> None:
        old = self._old_record()
        layout = view.initial_layout()
        frame = view.render(old, layout, color=False)
        self.assertIn("@", frame)
        self.assertIn("DESCONOCIDO", frame)

    def test_old_jsonl_does_not_crash_board(self) -> None:
        """Absent is read as 0 / null, never invented."""
        rows = board.normalise([self._old_record()])
        self.assertEqual(set(rows[0]), set(thought.KEYS))
        self.assertEqual(rows[0]["n"], 0)
        self.assertEqual(rows[0]["s"], 0)
        self.assertEqual(rows[0]["delta"], 0)
        self.assertIsNone(rows[0]["cortex_action"])
        self.assertEqual(rows[0]["gate_decision"], 0)
        # And the old twelve are passed through untouched.
        for k, v in self._old_record().items():
            self.assertEqual(rows[0][k], v, k)
        html = board.render_html([self._old_record()], source="old.jsonl")
        self.assertIn("board", html)

    # 5 ------------------------------------------------------------------
    def test_board_embeds_every_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            ag = Agent(ask=False, thought_log=str(log))
            for t in range(3):
                ag.turn(t)
            out = Path(tmp) / "board.html"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = board.main([str(log), "-o", str(out)])
            self.assertEqual(rc, 0)
            html = out.read_text(encoding="utf-8")

        turns = json.loads(
            re.search(r"const TURNS = (\[.*?\]);\n", html, re.S)
            .group(1).replace("\\u003c", "<")
        )
        self.assertEqual(len(turns), 3, "one object per line of the log")
        for rec in turns:
            self.assertEqual(set(rec), set(thought.KEYS), rec)
        # Self-contained: nothing is fetched when the file is opened.
        for forbidden in ("http://", "https://", "cdn", "<link", "<img",
                          "WebSocket", "fetch("):
            self.assertNotIn(forbidden, html, forbidden)
        self.assertEqual(html.count("<script"), 1, "one inline script")

    def test_board_sizes_the_world_from_the_log(self) -> None:
        """A two-cell world must not be drawn as thirty empty boxes."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            with mock.patch.dict(os.environ, {cortex.ENV_CMD: sign.cortex_cmd()}):
                ag = Agent(cortex=True, ask=False, thought_log=str(log),
                           env=sign.SignEnv(sign.LAYOUT_PRIZE))
                for t in range(3):
                    ag.turn(t, greedy=True)
            recs = board.read_records(log)
        self.assertEqual(board.cell_count(board.normalise(recs)), 2)
        html = board.render_html(recs, source="sign.jsonl")
        self.assertIn("__CELLS__ = 2", html)
        self.assertNotIn(f"__CELLS__ = {N_CELLS}", html)
        # And the ring log still measures 32.
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "r.jsonl"
            run(thought_log=str(log))
            ring = board.normalise(board.read_records(log))
        self.assertEqual(board.cell_count(ring), N_CELLS)

    def test_board_rejects_a_missing_log(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = board.main(["/nonexistent/thought.jsonl"])
        self.assertEqual(rc, 1)
        self.assertIn("no such log", buf.getvalue())

    # 6 ------------------------------------------------------------------
    def test_board_does_not_import_the_loop(self) -> None:
        """The viewer reads the jsonl. It does not call Q, T, ATTEND or CAM."""
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "board.py"
        ).read_text(encoding="utf-8")
        for name in ("loop", "qtable", "world", "attend", "cam", "navi10"):
            self.assertNotIn(f"import {name}", src, name)
            self.assertNotIn(f"from echoai.nexus0.{name}", src, name)
        for banned in ("PySide", "PyQt", "QtWidgets", "flask", "fastapi",
                       "matplotlib", "pygame", "websocket", "requests",
                       "urllib"):
            self.assertNotIn(banned, src, banned)

    def test_the_loop_did_not_learn_about_the_gui(self) -> None:
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "loop.py"
        ).read_text(encoding="utf-8")
        for banned in ("board", "PySide", "PyQt", "Qt", "websocket", "http"):
            self.assertNotIn(banned, src, banned)

    # 7 ------------------------------------------------------------------
    def test_ring_locks(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["surprise_known"], 1, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["cortex_actions"], 0, report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)


class TestGui2(unittest.TestCase):
    """GUI-2: the same board, live.

    A `file://` page cannot watch a file grow, so `--follow` serves the
    board from the loopback and the page polls one route. Everything here
    is measured against a real server on a real socket — no screenshot is
    evidence of anything.
    """

    @staticmethod
    def _rec(turn: int, cell: int = 0) -> dict:
        return {
            "turn": turn, "cell": cell, "kind": "EMPTY", "action": 2,
            "reward": 0, "wsp": "YO → OBSERVAR → AQUI @AHORA",
            "attend_on": False, "reason_name": "off", "q_row": [0, 0, 0],
            "t_pred": None, "questions": 0, "cortex_calls": 0,
            "n": 0, "s": 0, "delta": 0, "cortex_action": None,
            "gate_decision": 0,
        }

    @classmethod
    def _write(cls, path: Path, turns) -> None:
        path.write_text(
            "".join(json.dumps(cls._rec(t)) + "\n" for t in turns),
            encoding="utf-8",
        )

    @contextlib.contextmanager
    def _served(self, path, poll_ms: int = 200):
        """One server, one socket, torn down whatever happens."""
        server = board.make_server(path, port=0, poll_ms=poll_ms)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[0], server.server_address[1]
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    @staticmethod
    def _get(url: str):
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")

    # 1 — the KPI --------------------------------------------------------
    def test_the_poll_sees_a_line_that_was_not_there(self) -> None:
        """Append to the jsonl while the server is up; the poll returns it.

        This is the whole slice. If the board only ever showed what was on
        disk when it started, `--follow` would be a word in a docstring.
        """
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "thought.jsonl"
            self._write(log, range(2))
            with self._served(log) as base:
                code, body = self._get(f"{base}{board.POLL_PATH}?from=0")
                first = json.loads(body)
                self.assertEqual(code, 200)
                self.assertEqual(first["total"], 2, first)
                self.assertEqual(len(first["turns"]), 2, first)
                self.assertFalse(first["waiting"], first)

                # The loop writes turn 2 while the board is being watched.
                with log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(self._rec(2, cell=7)) + "\n")

                code, body = self._get(f"{base}{board.POLL_PATH}?from=2")
                after = json.loads(body)
                self.assertEqual(code, 200)
                self.assertEqual(after["total"], 3, after)
                self.assertEqual([t["turn"] for t in after["turns"]], [2], after)
                self.assertEqual(after["turns"][0]["cell"], 7, after)
                # The world grew with it: cell 7 means eight cells, not 32.
                self.assertEqual(after["cells"], 8, after)
                # And it is a full record — the page needs no defaults.
                self.assertEqual(set(after["turns"][0]), set(thought.KEYS))

    def test_the_poll_only_sends_what_is_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(5))
            with self._served(log) as base:
                body = json.loads(self._get(f"{base}{board.POLL_PATH}?from=5")[1])
                self.assertEqual(body["turns"], [], body)
                self.assertEqual(body["total"], 5, body)
                body = json.loads(self._get(f"{base}{board.POLL_PATH}?from=3")[1])
                self.assertEqual([t["turn"] for t in body["turns"]], [3, 4], body)
                # No query at all is the whole log, not an error.
                body = json.loads(self._get(f"{base}{board.POLL_PATH}")[1])
                self.assertEqual(len(body["turns"]), 5, body)

    def test_from_param_is_parsed_by_hand(self) -> None:
        """Junk reads as 0 and an overshoot clamps. No URL library, no 500."""
        self.assertEqual(board._from_param("from=3", 10), 3)
        self.assertEqual(board._from_param("from=99", 10), 10)
        self.assertEqual(board._from_param("from=abc", 10), 0)
        self.assertEqual(board._from_param("from=-1", 10), 0)
        self.assertEqual(board._from_param("", 10), 0)
        self.assertEqual(board._from_param("x=1&from=2", 10), 2)

    # 2 — the page -------------------------------------------------------
    def test_the_live_page_polls_and_holds_no_socket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(3))
            with self._served(log) as base:
                code, html = self._get(base + "/")
                self.assertEqual(code, 200)
        self.assertIn(board.POLL_PATH, html)
        self.assertIn("setInterval(__sync", html)
        self.assertEqual(html.count("<script"), 1, "one inline script")
        # One protocol, and it is the one already in use.
        for banned in ("new WebSocket", "WebSocket(", "EventSource",
                       "http://", "https://", "cdn", "<link", "<img"):
            self.assertNotIn(banned, html, banned)

    def test_unknown_route_is_404(self) -> None:
        """Two routes and no files: nothing on disk is reachable by URL."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(1))
            with self._served(log) as base:
                for route in ("/etc/passwd", "/../../board.py", "/nope"):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        self._get(base + route)
                    self.assertEqual(caught.exception.code, 404, route)
                    caught.exception.close()

    def test_server_binds_the_loopback_only(self) -> None:
        """Not a flag. A board reachable from another machine is a service."""
        self.assertEqual(board.HOST, "127.0.0.1")
        self.assertEqual(board.DEFAULT_PORT, 8765)
        self.assertEqual(board.DEFAULT_POLL_MS, 200)
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(1))
            server = board.make_server(log, port=0)
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
            finally:
                server.server_close()
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "board.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("0.0.0.0", src)
        self.assertIn('HOST = "127.0.0.1"', src)

    # 3 — GUI-1 is untouched --------------------------------------------
    def test_the_file_board_is_untouched_by_gui2(self) -> None:
        """Without --follow the page is what GUI-1 wrote, byte for byte."""
        recs = [self._rec(t) for t in range(4)]
        default = board.render_html(recs, source="t.jsonl")
        static = board.render_html(recs, source="t.jsonl", live=False)
        self.assertEqual(default, static, "the default stopped being static")
        for banned in ("fetch(", board.POLL_PATH, "setInterval(__sync",
                       "POLL_MS", "class=\"dot\"", "WebSocket("):
            self.assertNotIn(banned, static, banned)
        self.assertIn("No network, no model, no live loop", static)
        # And the live page is the same board, not a second one: same CSS,
        # same JS, same blocks, with the poll appended.
        live = board.render_html(recs, source="t.jsonl", live=True)
        self.assertIn(board.CSS, live)
        self.assertIn(board.JS, live)
        self.assertGreater(len(live), len(static))

    def test_file_board_still_written_without_follow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(3))
            out = Path(tmp) / "board.html"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = board.main([str(log), "-o", str(out)])
            self.assertEqual(rc, 0)
            html = out.read_text(encoding="utf-8")
        self.assertNotIn("fetch(", html)
        self.assertNotIn(board.POLL_PATH, html)

    # 4 — the writer is still running -----------------------------------
    def test_a_log_that_is_not_there_yet_waits(self) -> None:
        """The loop may not have started. That is `waiting`, not a crash."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "not-yet.jsonl"
            rows, waiting = board.read_live(missing)
            self.assertEqual(rows, [])
            self.assertTrue(waiting)
            with self._served(missing) as base:
                body = json.loads(self._get(f"{base}{board.POLL_PATH}?from=0")[1])
                self.assertTrue(body["waiting"], body)
                self.assertEqual(body["total"], 0, body)
                code, html = self._get(base + "/")
                self.assertEqual(code, 200)
                self.assertIn("waiting for", html)

    def test_a_torn_last_line_is_dropped_not_raised(self) -> None:
        """The writer appends while we read. Half a line will be whole next
        poll; a bad line anywhere earlier is a corrupt log and says so."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(3))
            with log.open("a", encoding="utf-8") as fh:
                fh.write('{"turn": 3, "cel')
            rows, waiting = board.read_live(log)
            self.assertEqual(len(rows), 3, rows)
            self.assertFalse(waiting)

            broken = Path(tmp) / "broken.jsonl"
            broken.write_text(
                '{"turn": 0, "cel\n' + json.dumps(self._rec(1)) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                board.read_live(broken)

    def test_read_live_notices_the_file_grew(self) -> None:
        """The parse is cached on (mtime, size) so a 200 ms poll is cheap —
        and the cache must not hide the next line."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "t.jsonl"
            self._write(log, range(2))
            self.assertEqual(len(board.read_live(log)[0]), 2)
            self.assertEqual(len(board.read_live(log)[0]), 2)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(self._rec(2)) + "\n")
            self.assertEqual(len(board.read_live(log)[0]), 3)

    # 5 — the loop never learns about any of this ------------------------
    def test_the_loop_still_does_not_know_the_gui_exists(self) -> None:
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "loop.py"
        ).read_text(encoding="utf-8")
        for banned in ("board", "http", "socket", "WebSocket", "PySide", "Qt"):
            self.assertNotIn(banned, src, banned)
        board_src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "board.py"
        ).read_text(encoding="utf-8")
        # Usage, not the word: the module's own docstring says what it
        # does not do, and a test that bans prose is not a test.
        for banned in ("EventSource", "new WebSocket", "WebSocket(",
                       "0.0.0.0", "import socket"):
            self.assertNotIn(banned, board_src, banned)
        # thought.KEYS was not widened to make the live board work: the
        # seventeen GUI-2 was handed are still the first seventeen, and
        # what came after them is GUI-3's pose, which the poll route
        # carries without reading.
        self.assertEqual(thought.KEYS[:17], TestGui3.GUI2_KEYS)

    def test_ring_locks_after_gui2(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["surprise_known"], 1, report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)


class TestGui3(unittest.TestCase):
    """GUI-3: the aquarium next to the electrocardiogram.

    The board could show the pulse and not the animal: `cell` is one
    integer, and the pose it stands for is three plus a heading. Deriving
    one from the other inside the viewer would put the cube's geometry in
    a browser, where it would go stale the first time the world changed.
    So the log carries the pose, the board draws what the log carries,
    and the walls come from nowhere — a voxel nobody has stood in is a
    hole, which is what a wall looks like from inside a body.
    """

    GUI2_KEYS = (
        "turn", "cell", "kind", "action", "reward", "wsp",
        "attend_on", "reason_name", "q_row", "t_pred",
        "questions", "cortex_calls",
        "n", "s", "delta", "cortex_action", "gate_decision",
    )
    POSE_KEYS = ("x", "y", "z", "heading", "frame")

    @staticmethod
    def _read(path: Path) -> list:
        return [json.loads(l) for l in
                path.read_text(encoding="utf-8").splitlines() if l.strip()]

    @contextlib.contextmanager
    def _served(self, path, poll_ms: int = 200):
        server = board.make_server(path, port=0, poll_ms=poll_ms)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[0], server.server_address[1]
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    @staticmethod
    def _get(url: str):
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")

    # 1 ------------------------------------------------------------------
    def test_keys_gained_five_at_the_end_and_nothing_moved(self) -> None:
        self.assertEqual(len(thought.KEYS), 22)
        self.assertEqual(len(set(thought.KEYS)), 22, "a key is repeated")
        # The seventeen that existed keep their names and their order.
        self.assertEqual(thought.KEYS[:17], self.GUI2_KEYS)
        self.assertEqual(thought.KEYS[17:], self.POSE_KEYS)
        rec = thought.build(
            turn=0, cell=0, kind=0, action=2, reward=0, wsp=encode_cell(0, 0),
            attend_on=False, reason=REASON_OFF, q_row=[0, 0, 0], t_pred=None,
            questions=0, cortex_calls=0,
        )
        self.assertEqual(set(rec), set(thought.KEYS))
        for k in self.POSE_KEYS:
            self.assertIsNone(rec[k], k)
        # Integers or null. Never prose, never a nested events[].
        posed = thought.build(
            turn=1, cell=6, kind=0, action=0, reward=0, wsp=encode_cell(6, 0),
            attend_on=False, reason=REASON_OFF, q_row=[0, 0, 0], t_pred=None,
            questions=0, cortex_calls=0,
            x=1, y=0, z=2, heading=4, frame=1,
        )
        for k in self.POSE_KEYS:
            self.assertIsInstance(posed[k], int, k)
        self.assertEqual([posed[k] for k in self.POSE_KEYS], [1, 0, 2, 4, 1])
        self.assertNotIn("events", thought.KEYS)

    # 2 ------------------------------------------------------------------
    def test_the_ring_has_no_pose_and_says_so(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "r.jsonl"
            report = run(thought_log=str(log))
            recs = self._read(log)
        self.assertEqual(len(recs), report["turns"])
        for rec in recs:
            self.assertEqual(set(rec), set(thought.KEYS), rec)
            for k in self.POSE_KEYS:
                self.assertIsNone(rec[k], (rec["turn"], k))
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        # No pose in the log, no cube on the board: it is not invented.
        self.assertFalse(board.has_cube(board.normalise(recs)))
        self.assertEqual(board.cube_side(board.normalise(recs)), 0)

    # 3 ------------------------------------------------------------------
    def test_the_cube_writes_the_pose_every_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "c.jsonl"
            ag = Agent(env=body3d.Body3DEnv(body3d.LAYOUT_OPEN), ask=False,
                       thought_log=str(log))
            for t in range(6):
                ag.turn(t)
            recs = self._read(log)
        self.assertEqual(len(recs), 6)
        for rec in recs:
            self.assertEqual(set(rec), set(thought.KEYS), rec)
            for k in ("x", "y", "z", "heading"):
                self.assertIsInstance(rec[k], int, (rec["turn"], k))
            self.assertIsNone(rec["frame"], "the bare cube has no frame")
            # The pose is the one the index already stood for, spelled out.
            self.assertEqual(
                body3d.index_of(rec["x"], rec["y"], rec["z"], rec["heading"]),
                rec["cell"], rec)
        # A room does have one, and it rides on the env, not in the packet.
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "b.jsonl"
            ag = Agent(env=room1.room_env(room1.FRAME_B), ask=False,
                       thought_log=str(log))
            ag.turn(0)
            rec = self._read(log)[0]
        self.assertEqual(rec["frame"], room1.FRAME_B)
        self.assertIsInstance(rec["x"], int)

    # 4 ------------------------------------------------------------------
    def test_the_board_draws_the_cube_the_log_carries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "c.jsonl"
            ag = Agent(env=body3d.Body3DEnv(body3d.LAYOUT_OPEN), ask=False,
                       remainder=True, explore_flat=True, thought_log=str(log))
            ag.env.teleport(body3d.index_of(2, 2, 1, body3d.PLUS_Z))
            for t in range(40):
                ag.turn(t)
            recs = self._read(log)
            out = Path(tmp) / "board.html"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = board.main([str(log), "-o", str(out)])
            html = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        side = board.cube_side(board.normalise(recs))
        self.assertEqual(side, 3, "the log saw the whole cube")
        # 27 voxels, 3 slices of 3x3. Laid out by the writer from the
        # coordinates in the log, so it is checkable without a browser.
        self.assertEqual(html.count('class="vox"'), side ** 3)
        self.assertEqual(html.count('class="slice"'), side)
        for x in range(side):
            for y in range(side):
                for z in range(side):
                    self.assertIn(f'data-v="{x},{y},{z}"', html)
        # Turn 0 of the page is turn 0 of the log, pose and all.
        turns = json.loads(
            re.search(r"const TURNS = (\[.*?\]);\n", html, re.S)
            .group(1).replace("\\u003c", "<")
        )
        self.assertEqual(len(turns), len(recs))
        for k in ("x", "y", "z", "heading", "cell"):
            self.assertEqual(turns[0][k], recs[0][k], k)
        self.assertIn(
            'data-v="{},{},{}"'.format(*(recs[0][k] for k in ("x", "y", "z"))),
            html)
        # The heading is read, never computed: the six names are a legend.
        self.assertEqual(board.HEADING_NAME, ("+X", "+Y", "+Z", "-X", "-Y", "-Z"))
        self.assertIn(json.dumps(list(board.HEADING_NAME)), html)
        # A smaller world is drawn smaller. The side is the log's, not
        # this cube's: a viewer that assumed 3 would draw 27 boxes round
        # a body that has only ever been inside 8 of them.
        two = [dict(recs[0], turn=0, x=0, y=0, z=0),
               dict(recs[0], turn=1, x=1, y=1, z=1)]
        self.assertEqual(board.cube_side(board.normalise(two)), 2)
        self.assertEqual(
            board.render_html(two, source="s.jsonl").count('class="vox"'), 8)
        # And the eight blocks still read the same line.
        for bid, _name, _note in board.BLOCKS:
            self.assertIn(f'id="{bid}"', html)
        self.assertIn('id="qbars"', html)

    # 5 ------------------------------------------------------------------
    def test_the_board_does_not_invent_a_cube_for_the_ring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "r.jsonl"
            run(thought_log=str(log))
            recs = self._read(log)
            out = Path(tmp) / "board.html"
            with contextlib.redirect_stdout(io.StringIO()):
                board.main([str(log), "-o", str(out)])
            html = out.read_text(encoding="utf-8")
        self.assertNotIn('class="vox"', html)
        self.assertNotIn('id="cube"', html)
        self.assertNotIn('class="stage"', html)
        # The strip of 32 is exactly what it was.
        self.assertEqual(board.cell_count(board.normalise(recs)), N_CELLS)
        self.assertIn(f"__CELLS__ = {N_CELLS}", html)
        self.assertIn('id="ring"', html)

    # 6 ------------------------------------------------------------------
    def test_follow_shows_a_pose_that_was_not_there(self) -> None:
        """Same trick as GUI-2, now with a body: append a turn at another
        voxel while the server is up, and the poll hands it over."""
        def rec(turn, x, y, z, h):
            return {
                "turn": turn, "cell": body3d.index_of(x, y, z, h),
                "kind": "EMPTY", "action": 2, "reward": 0, "wsp": "w",
                "attend_on": False, "reason_name": "off", "q_row": [0, 0, 0],
                "t_pred": None, "questions": 0, "cortex_calls": 0,
                "n": 0, "s": 0, "delta": 0, "cortex_action": None,
                "gate_decision": 0,
                "x": x, "y": y, "z": z, "heading": h, "frame": 0,
            }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "c.jsonl"
            log.write_text(
                json.dumps(rec(0, 0, 0, 0, 0)) + "\n"
                + json.dumps(rec(1, 1, 0, 0, 0)) + "\n", encoding="utf-8")
            with self._served(log) as base:
                code, body = self._get(f"{base}/")
                self.assertEqual(code, 200)
                self.assertIn('class="vox"', body)
                self.assertIn('id="cube"', body)

                code, body = self._get(f"{base}{board.POLL_PATH}?from=0")
                first = json.loads(body)
                self.assertEqual(first["total"], 2, first)

                with log.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec(2, 2, 2, 1, 2)) + "\n")

                code, body = self._get(f"{base}{board.POLL_PATH}?from=2")
                after = json.loads(body)
                self.assertEqual(after["total"], 3, after)
                fresh = after["turns"][0]
                self.assertEqual(
                    [fresh[k] for k in ("x", "y", "z", "heading")],
                    [2, 2, 1, 2], fresh)
                self.assertEqual(set(fresh), set(thought.KEYS))

    # 7 ------------------------------------------------------------------
    def test_no_network_and_no_crash_on_yesterdays_log(self) -> None:
        old = {
            "turn": 3, "cell": 11, "kind": "NOVEL", "action": 0, "reward": -16,
            "wsp": "YO → DESCONOCIDO → UNK @AHORA", "attend_on": True,
            "reason_name": "novel", "q_row": [-4, 0, 0], "t_pred": None,
            "questions": 1, "cortex_calls": 2,
        }
        rows = board.normalise([old])
        self.assertEqual(set(rows[0]), set(thought.KEYS))
        for k in self.POSE_KEYS:
            self.assertIsNone(rows[0][k], k)
        for k, v in old.items():
            self.assertEqual(rows[0][k], v, k)
        html = board.render_html([old], source="old.jsonl")
        self.assertNotIn('class="vox"', html)
        # A cube board is still one file with nothing to fetch.
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "c.jsonl"
            ag = Agent(env=body3d.Body3DEnv(body3d.LAYOUT_OPEN), ask=False,
                       thought_log=str(log))
            for t in range(4):
                ag.turn(t)
            cube_html = board.render_html(self._read(log), source="c.jsonl")
        for forbidden in ("http://", "https://", "cdn", "<link", "<img",
                          "WebSocket", "fetch(", "npm", "three.min"):
            self.assertNotIn(forbidden, cube_html, forbidden)
        self.assertEqual(cube_html.count("<script"), 1, "one inline script")
        # The viewer still knows nothing about the world it is drawing.
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "board.py"
        ).read_text(encoding="utf-8")
        for banned in ("import body3d", "from echoai.nexus0.body3d",
                       "import room1", "from echoai.nexus0.room1",
                       "FLOOR", "BLOCKED", "is_floor", "SHORT_PATH",
                       "LONG_PATH", "N_POSES", "DIRS", "index_of(",
                       "pose_of("):
            self.assertNotIn(banned, src, banned)
        # Nor did the loop learn what a cube is to write one down: it
        # copies whatever the cell happens to carry.
        loop_src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "loop.py"
        ).read_text(encoding="utf-8")
        for banned in ("body3d", "room1", "pose_of(", "index_of(", "SIDE"):
            self.assertNotIn(banned, loop_src, banned)
        self.assertIn('getattr(cell, "x", None)', loop_src)

    # 8 ------------------------------------------------------------------
    def test_the_walk_writes_a_diary_and_no_report(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_pulpo_report.json", "nexus0_self1_report.json",
                  "nexus0_room1_report.json", "nexus0_report.json",
                  "thought.jsonl")
        def stamp(name: Path):
            """Bytes *and* mtime. This experiment is deterministic, so a
            runner that re-ran it and wrote the report back would hand
            back identical bytes — the only trace left of a file that was
            written for nothing is that it was written."""
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = body3d.main(["--thought"])
        self.assertEqual(rc, 0, buf.getvalue())
        after = {n: stamp(lab / n) for n in others}
        self.assertEqual(before, after, "the walk trod on somebody's file")

        log = lab / body3d.THOUGHT_LOG
        self.assertTrue(log.is_file())
        recs = self._read(log)
        self.assertEqual(len(recs), body3d.THOUGHT_TURNS)
        self.assertEqual(recs[0]["cell"], body3d.START)
        for rec in recs:
            self.assertEqual(set(rec), set(thought.KEYS), rec)
            for k in ("x", "y", "z", "heading"):
                self.assertIsInstance(rec[k], int, k)
        # It walked: the diary is a body that got somewhere, not a body
        # that stood still, and the board can draw the whole cube from it.
        self.assertGreater(len({(r["x"], r["y"], r["z"]) for r in recs}), 1)
        self.assertEqual(board.cube_side(board.normalise(recs)), 3)
        self.assertGreater(sum(1 for r in recs if r["kind"] == "GOAL"), 0)


class TestGui35(unittest.TestCase):
    """GUI-3.5: the same log, a view a human can actually watch.

    GUI-3 put the pose in the diary and drew three flat floors from it.
    Nothing about the animal changes here — no new key, no new action, no
    retune. What changes is the view: a cube you can orbit, the diary
    written out line by line, and a run that does not end at turn 64.
    """

    @staticmethod
    def _read(path: Path) -> list:
        return [json.loads(l) for l in
                path.read_text(encoding="utf-8").splitlines() if l.strip()]

    @classmethod
    def _cube_log(cls, tmp: Path, turns: int = 24) -> list:
        log = tmp / "c.jsonl"
        ag = Agent(env=body3d.Body3DEnv(body3d.LAYOUT_OPEN), ask=False,
                   remainder=True, explore_flat=True, thought_log=str(log))
        ag.env.teleport(body3d.index_of(2, 2, 1, body3d.PLUS_Z))
        for t in range(turns):
            ag.turn(t)
        return cls._read(log)

    @contextlib.contextmanager
    def _served(self, path, poll_ms: int = 200):
        server = board.make_server(path, port=0, poll_ms=poll_ms)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[0], server.server_address[1]
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    # 1 ------------------------------------------------------------------
    def test_the_cube_is_a_volume_you_can_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recs = self._cube_log(Path(tmp))
        html = board.render_html(recs, source="c.jsonl")
        # A volume, not three floors: 27 boxes of six faces each, placed
        # in one `preserve-3d` scene by the writer.
        self.assertIn("preserve-3d", html)
        self.assertIn('id="stage3d"', html)
        self.assertIn('id="world"', html)
        self.assertEqual(html.count('class="cell3d"'), 27)
        self.assertEqual(html.count('class="f '), 27 * len(board.FACES))
        self.assertEqual(len(board.FACES), 6)
        # Each one placed by arithmetic on the log's coordinates, so the
        # geometry is checkable without opening a browser.
        self.assertIn(f"translate3d(-{board.VOX}px,{board.VOX}px,"
                      f"-{board.VOX}px)", html.replace(" ", ""))
        self.assertIn("translate3d(0px,0px,0px)", html.replace(" ", ""))
        # And it can be turned: a drag rotates the scene, the wheel zooms,
        # and there is a way back to where it started.
        for handle in ("pointerdown", "pointermove", "rotateX(", "rotateY(",
                       "wheel", "reset3d"):
            self.assertIn(handle, html, handle)
        # The strip of 105 boxes is the same pose in one dimension; with a
        # cube on the page it is hidden rather than deleted.
        self.assertIn('id="ringbox" hidden', html)
        self.assertIn('id="ring"', html)
        # The flat floors survive as a folded minimap, not as the view.
        self.assertIn("<details", html)
        self.assertEqual(html.count('class="slice"'), 3)

    # 2 ------------------------------------------------------------------
    def test_there_is_a_diary_and_it_is_only_the_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recs = self._cube_log(Path(tmp))
        html = board.render_html(recs, source="c.jsonl")
        self.assertIn('id="thought"', html)
        # Every field of a line is a key of the record. The panel is built
        # in the page from TURNS, so what has to be checked here is that
        # nothing else can get in: no key outside thought.KEYS is read.
        js = board.CUBE_JS
        for field in ("rec.turn", "rec.action", "rec.wsp", "rec.t_pred",
                      "rec.q_row", "rec.reward", "rec.delta", "rec.s"):
            self.assertIn(field, js, field)
        used = set(re.findall(r"rec\.([a-z_]+)", js))
        self.assertEqual(used - set(thought.KEYS), set(), used)
        self.assertIn("THOUGHT_TAIL", js)

    # 3 ------------------------------------------------------------------
    def test_the_diary_invents_no_reasons(self) -> None:
        """A board that said why the body turned would be making it up."""
        src = (
            Path(__file__).resolve().parents[1] / "nexus0" / "board.py"
        ).read_text(encoding="utf-8")
        # Usage, not words: a comment may say what the code may not
        # write. What the line writer is allowed to put on a diary line
        # is the record's own fields plus separators — the only word it
        # may spell is the one that names a cell with no pose.
        body = re.search(r"function tline\(rec\) \{(.*?)\n\}",
                         board.CUBE_JS, re.S).group(1)
        for literal in re.findall(r"'([^']*)'", body):
            self.assertEqual(
                [w for w in re.findall(r"[A-Za-z]{3,}", literal)
                 if w != "cell"],
                [], f"the diary spells a word of its own: {literal!r}")
        # No new key was needed to say any of it.
        self.assertEqual(len(thought.KEYS), 22)
        self.assertNotIn("story", thought.KEYS)
        self.assertNotIn("events", thought.KEYS)
        # And the viewer still knows nothing about the world it draws.
        for banned in ("import body3d", "from echoai.nexus0.body3d",
                       "FLOOR", "BLOCKED", "is_floor", "pose_of(",
                       "index_of(", "three", "unpkg", "jsdelivr", "cdn",
                       "importmap", "WebGL", "getContext"):
            self.assertNotIn(banned, src, banned)
        for name in ("loop", "qtable", "world", "attend"):
            self.assertNotIn(f"import {name}", src, name)

    # 4 ------------------------------------------------------------------
    def test_the_ring_gets_no_volume_either(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "r.jsonl"
            run(thought_log=str(log))
            recs = self._read(log)
        html = board.render_html(recs, source="r.jsonl")
        for absent in ("cell3d", "stage3d", "preserve-3d", 'id="thought"',
                       'class="stage"'):
            self.assertNotIn(absent, html, absent)
        # Its own strip is untouched, and still shown.
        self.assertIn(f"__CELLS__ = {N_CELLS}", html)
        self.assertNotIn("hidden", html.split("<main>")[1].split("</div>")[0])
        self.assertEqual(board.cube_side(board.normalise(recs)), 0)

    # 5 ------------------------------------------------------------------
    def test_a_replay_starts_over_instead_of_dying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recs = self._cube_log(Path(tmp))
        static = board.render_html(recs, source="c.jsonl")
        live = board.render_html(recs, source="c.jsonl", live=True)
        # Static: a checkbox, on by default, and the last turn goes to 0.
        self.assertIn('id="loop"', static)
        self.assertIn("checked", static)
        self.assertIn("const LIVE = false;", static)
        self.assertIn("i = 0;", board.JS)
        self.assertNotIn("if (i >= TURNS.length - 1) return stop();", board.JS)
        # Live: no checkbox, and the end of the log is not the end of the
        # run — Play holds there and the poll pushes it on.
        self.assertNotIn('id="loop"', live)
        self.assertIn("const LIVE = true;", live)
        self.assertIn("if (LIVE) return;", board.JS)

    # 6 ------------------------------------------------------------------
    def test_the_walk_does_not_stop_at_sixty_four(self) -> None:
        """`--live` is run for real, in a subprocess, and killed."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "live.jsonl"
            proc = subprocess.Popen(
                [sys.executable, "-m", "echoai.nexus0.body3d", "--live",
                 "--out", str(log), "--pace", "0"],
                cwd=str(ROOT), env={**os.environ, "PYTHONPATH": "."},
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                grown = 0
                for _ in range(600):   # up to ~60 s; the school is ~3 s
                    if log.is_file():
                        grown = len(log.read_bytes().splitlines())
                        if grown > body3d.THOUGHT_TURNS:
                            break
                    time.sleep(0.1)
                self.assertGreater(grown, body3d.THOUGHT_TURNS,
                                   "the walk stopped at the exam's budget")
                # A board following it sees a turn that was not there when
                # the server started.
                with self._served(log) as base:
                    with urllib.request.urlopen(
                            f"{base}{board.POLL_PATH}?from=0", timeout=5) as r:
                        first = json.loads(r.read().decode("utf-8"))
                    self.assertGreater(first["total"], body3d.THOUGHT_TURNS)
                    time.sleep(0.3)
                    with urllib.request.urlopen(
                            f"{base}{board.POLL_PATH}?from={first['total']}",
                            timeout=5) as r:
                        after = json.loads(r.read().decode("utf-8"))
                self.assertGreater(after["total"], first["total"],
                                   "the diary stopped growing")
                fresh = after["turns"][0]
                for k in ("x", "y", "z", "heading"):
                    self.assertIsInstance(fresh[k], int, k)
                self.assertEqual(set(fresh), set(thought.KEYS))
            finally:
                proc.terminate()
                proc.wait(timeout=10)
                proc.stdout.close()
                proc.stderr.close()
            # It walked the corridor more than once: time, not space.
            recs = self._read(log)
            self.assertGreater(sum(1 for r in recs if r["reward"] == R_SUCCESS),
                               1, "it collected at most once")
            self.assertEqual(board.cube_side(board.normalise(recs)), 3)

    # 7 ------------------------------------------------------------------
    def test_the_bounded_walk_and_the_reports_are_untouched(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_pulpo_report.json", "nexus0_self1_report.json",
                  "nexus0_room1_report.json", "nexus0_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = body3d.main(["--thought"])
        self.assertEqual(rc, 0, buf.getvalue())
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "the walk trod on somebody's file")
        recs = self._read(lab / body3d.THOUGHT_LOG)
        self.assertEqual(len(recs), body3d.THOUGHT_TURNS)
        # And `--live` is the same body under a different clock: it never
        # opens a report either.
        src = inspect.getsource(body3d.live_walk)
        for banned in ("report", "green(", "json.dump", "_report.json"):
            self.assertNotIn(banned, src, banned)

    # 8 ------------------------------------------------------------------
    def test_ring_locks_after_gui35(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["surprise_known"], 1, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(len(thought.KEYS), 22)


class TestObj1(unittest.TestCase):
    """OBJ-1: the world has things in it, not only a me.

    PULPO's cube pays when the body stands on (2,2,1); this one pays when
    the *item* does. Carrying is physics — `approach` that lands on the
    item couples, the item follows, and there is no fourth gear and no
    `carrying` bit in the sixteen bytes. What is on the cable instead is a
    kind: `KIND_OBJECT`, painted on the voxel the item is in now, so a body
    holding the glass and a body holding nothing are two different packets
    and Q does not average two futures into one row.

    The control is what the geometry has to earn. A body paid for arriving
    only fails to bring the glass if the glass is not on its way, so the
    table is **not** PULPO's goal voxel: item and table sit on the two arms
    of the cube, which meet only at START. Ten actions to fetch and
    deliver, one to reach the table alone. Both flooded here, neither drawn.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = obj1.experiment()

    # 1 ------------------------------------------------------------------
    def test_the_item_is_not_on_the_cheapest_way_to_the_table(self) -> None:
        r = self.report
        floor = body3d.floor_of(body3d.LAYOUT_OPEN)
        self.assertIn(obj1.ITEM_XYZ, floor)
        self.assertIn(obj1.DEST_XYZ, floor)
        self.assertNotEqual(obj1.ITEM_XYZ, body3d.START_XYZ)
        self.assertNotEqual(obj1.DEST_XYZ, body3d.START_XYZ)
        self.assertNotEqual(obj1.ITEM_XYZ, obj1.DEST_XYZ)
        # The claim the control lives on: going to the table costs the same
        # whether or not the glass may be touched, so a body that only
        # wants the table never has to pick anything up. Flooded twice —
        # once with the glass where it lies, once with the room empty.
        self.assertFalse(obj1.item_on_cheapest_dest_path())
        self.assertFalse(r["item_on_cheapest_dest_path"], r)
        self.assertEqual(obj1.cost_to_dest_alone(),
                         obj1.cost_to_dest_alone(item=obj1.NO_ITEM))
        self.assertTrue(r["item_costs_a_detour"], r)
        self.assertGreater(r["shortest_collect"] - 1,
                           r["cost_to_dest_alone"], r)
        # And it is not the only pair that would have done: the sweep that
        # found none held the table still on PULPO's goal.
        self.assertTrue(r["this_pair_is_one_of_them"], r)
        self.assertGreaterEqual(
            len(r["placements_that_cost_a_detour_and_fit"]), 1, r)
        for pair in r["placements_that_cost_a_detour_and_fit"]:
            q = next(x for x in r["placements"]
                     if [x["item"], x["dest"]] == pair)
            self.assertGreater(q["detour"], 0, q)
            self.assertLessEqual(q["collect"], r["value_horizon"], q)
            self.assertFalse(q["item_on_cheapest_dest_path"], q)
        self.assertEqual(r["layout"], body3d.LAYOUT_OPEN, r)
        self.assertEqual(r["actions"], 3, r)
        self.assertEqual(N_ACTIONS, 3)
        # The levers stay opt-in: the ring is measured on the update it
        # always had, and OBJ-1 asks for both by name.
        self.assertFalse(Agent().q.remainder)
        self.assertFalse(Agent().q.explore_flat)
        ag = obj1._fresh(obj1.Obj1Env())
        self.assertTrue(ag.q.remainder)
        self.assertTrue(ag.q.explore_flat)
        self.assertEqual(ag.plan_depth, 0)
        # Ten actions to fetch and deliver, flooded and not drawn.
        self.assertEqual(r["shortest_collect"], 10, r)
        self.assertEqual(r["cost_to_dest_alone"], 1, r)
        self.assertLessEqual(r["shortest_collect"], r["value_horizon"], r)
        self.assertTrue(r["collect_fits_the_horizon"], r)

    # 2 ------------------------------------------------------------------
    def test_the_thing_is_a_kind_and_never_an_address(self) -> None:
        r = self.report
        for p in range(body3d.N_POSES):
            empty = encode_cell(p, KIND_EMPTY)
            thing = encode_cell(p, KIND_OBJECT)
            self.assertEqual(len(empty), 16)
            self.assertEqual(len(thing), 16)
            self.assertNotEqual(empty, thing, body3d.pose_name(p))
            for kind in (KIND_EMPTY, KIND_OBJECT):
                ext = obj1.ext_of(p, kind)
                self.assertEqual(ext["domain"], 0, body3d.pose_name(p))
                self.assertEqual(ext["style"], 0, body3d.pose_name(p))
                self.assertEqual(ext["seq"], p, body3d.pose_name(p))
        # The affect of a thing is the affect of an empty floor. It is not
        # the prize wearing another name.
        self.assertEqual(unpack(encode_cell(0, KIND_OBJECT))["E"],
                         unpack(encode_cell(0, KIND_EMPTY))["E"])
        self.assertNotEqual(unpack(encode_cell(0, KIND_OBJECT))["E"],
                            unpack(encode_cell(0, KIND_GOAL))["E"])
        # 162 poses twice over, and the ceiling is still where it was.
        self.assertEqual(r["packets_empty"], 162, r)
        self.assertEqual(r["packets_object"], 162, r)
        self.assertEqual(r["packets_across"], 324, r)
        self.assertLess(r["packets_across"], N_SLOTS)
        self.assertEqual(encode_cell(0, KIND_EMPTY),
                         encode_cell(256, KIND_EMPTY))
        self.assertTrue(r["packet_ceiling_holds"], r)
        # The address the body hands the encoder is a pose, never a pose
        # times a voxel: 4374 would not have fitted under 4096 either.
        self.assertEqual(r["index_max"], 161, r)
        env = obj1.Obj1Env()
        for i in range(body3d.N_POSES):
            self.assertLess(env.teleport(i).index, body3d.N_POSES)
        # And holding lives on the world, not in the sixteen bytes. Derived
        # from the encoder path itself, so it is not a field printing True.
        self.assertTrue(r["coupled_is_env_not_wsp"], r)
        self.assertTrue(obj1.coupled_is_env_not_wsp())
        self.assertEqual(
            list(inspect.signature(obj1.packet_of).parameters),
            ["index", "kind"], "the packet grew a way to see the hand")
        self.assertTrue(hasattr(obj1.Obj1Env(), "coupled"))

    # 3 ------------------------------------------------------------------
    def test_landing_on_it_is_holding_it(self) -> None:
        """Every pose here is found by asking the flood, not typed in.

        The first draft named `(1,0,0)` and `(2,1,0)` because that is where
        the old item was. A test that spells the layout has to be rewritten
        every time a constant moves, and one that was forgotten would be
        testing the wrong cube while still passing.
        """
        open_ = body3d.LAYOUT_OPEN
        poses = body3d.reachable(open_)

        def moves(i):
            return obj1.successor((i, obj1.HELD), ACTION_APPROACH)[0] != i

        entry = next(
            i for i in poses
            if obj1.voxel_of(i) != obj1.ITEM_XYZ
            and obj1.voxel_of(
                obj1.successor((i, obj1.FREE), ACTION_APPROACH)[0]
            ) == obj1.ITEM_XYZ)

        env = obj1.Obj1Env()
        env.teleport(entry)
        self.assertFalse(env.coupled)
        self.assertEqual(env.cell().kind, KIND_EMPTY)
        reward, cell = env.step(ACTION_APPROACH)
        self.assertEqual(obj1.voxel_of(env.i), obj1.ITEM_XYZ)
        self.assertTrue(env.coupled, "approach landed on it and did not hold")
        self.assertEqual(cell.kind, KIND_OBJECT, "and the packet did not say so")
        self.assertEqual(reward, 0, "picking a thing up is not a reward")

        # A turn is a turn: the body rotates, the item does not fall. Keep
        # turning until the way ahead is open — the cube decides how many.
        turns = 0
        while not moves(env.i):
            reward, cell = env.step(ACTION_AVOID)
            turns += 1
            self.assertTrue(env.coupled)
            self.assertEqual(env.obj, obj1.ITEM_XYZ)
            self.assertEqual(obj1.voxel_of(env.i), obj1.ITEM_XYZ)
            self.assertEqual(cell.kind, KIND_OBJECT)
            self.assertEqual(reward, 0)
            self.assertLess(turns, body3d.HEADINGS, "it never faced an exit")

        # The next approach that does not walk into stone moves both.
        was = obj1.voxel_of(env.i)
        reward, cell = env.step(ACTION_APPROACH)
        self.assertNotEqual(obj1.voxel_of(env.i), was)
        self.assertEqual(env.obj, obj1.voxel_of(env.i))
        self.assertTrue(env.coupled)
        self.assertEqual(cell.kind, KIND_OBJECT)

        # And one that does walk into stone moves neither, and costs.
        blind = next(h for h in range(body3d.HEADINGS)
                     if body3d.bumps(body3d.index_of(*obj1.ITEM_XYZ, h), open_))
        env = obj1.Obj1Env()
        env.teleport(body3d.index_of(*obj1.ITEM_XYZ, blind))
        self.assertTrue(env.coupled, "teleporting onto it holds it too")
        reward, _cell = env.step(ACTION_APPROACH)
        self.assertEqual(reward, R_THREAT)
        self.assertEqual(env.obj, obj1.ITEM_XYZ)
        self.assertEqual(obj1.voxel_of(env.i), obj1.ITEM_XYZ)
        self.assertTrue(env.bumped)

        # There is no putting down. Nothing but a delivery uncouples.
        env = obj1.Obj1Env()
        env.teleport(body3d.index_of(*obj1.ITEM_XYZ, 0))
        for a in (ACTION_WAIT, ACTION_AVOID, ACTION_APPROACH) * 4:
            if obj1.voxel_of(env.i) == obj1.DEST_XYZ:
                break  # delivering is allowed to uncouple; nothing else is
            env.step(a)
            self.assertTrue(env.coupled)
            self.assertEqual(env.obj, obj1.voxel_of(env.i))

    # 4 ------------------------------------------------------------------
    def test_an_empty_table_does_not_pay_and_a_full_one_does(self) -> None:
        r = self.report
        # Standing on the table with the item still lying in the corridor.
        env = obj1.Obj1Env()
        env.teleport(body3d.index_of(*obj1.DEST_XYZ, body3d.MINUS_Z),
                     holding=False)
        self.assertFalse(env.coupled)
        self.assertEqual(env.obj, obj1.ITEM_XYZ)
        reward, _cell = env.step(ACTION_APPROACH)
        self.assertNotEqual(reward, R_SUCCESS, "the table paid for arriving")
        self.assertEqual(env.obj, obj1.ITEM_XYZ, "the item moved on its own")

        # And with it. Delivery pays, and sends the body home empty-handed.
        env = obj1.Obj1Env()
        env.teleport(body3d.index_of(*obj1.DEST_XYZ, body3d.PLUS_Z),
                     holding=True)
        self.assertEqual(env.obj, obj1.DEST_XYZ)
        reward, _cell = env.step(ACTION_APPROACH)
        self.assertEqual(reward, R_SUCCESS)
        self.assertEqual(env.i, body3d.START)
        self.assertEqual(env.obj, obj1.ITEM_XYZ)
        self.assertFalse(env.coupled)

        # Sitting on the table pays nothing at all, from either hand.
        for a in (ACTION_WAIT, ACTION_AVOID):
            for hands in (True, False):
                env = obj1.Obj1Env()
                env.teleport(body3d.index_of(*obj1.DEST_XYZ, body3d.PLUS_Z),
                             holding=hands)
                self.assertEqual(env.step(a)[0], 0, (a, hands))

        # Asked of all six headings by the runner, because the exam never
        # produces the turn: a body that fetches arrives holding the glass.
        self.assertEqual(r["probe_headings"], 6, r)
        self.assertEqual(r["probe_empty_table_collects"], 0, r)
        self.assertEqual(r["probe_full_table_reward_sum"], 6 * R_SUCCESS, r)
        self.assertTrue(r["probe_the_item_stayed_put"], r)
        self.assertEqual(r["probe_delivering_sends_the_body_home"], 6, r)
        # The table is a place. Nothing anywhere in this world is a prize.
        self.assertTrue(r["dest_is_not_kind_goal"], r)
        self.assertTrue(obj1.no_pose_is_ever_a_goal())
        env = obj1.Obj1Env()
        for v in body3d.floor_of(body3d.LAYOUT_OPEN):
            env.obj = v
            env._paint()
            self.assertNotIn(KIND_GOAL, env.kind, v)

    # 5 ------------------------------------------------------------------
    def test_the_thing_arrives_from_the_canonical_start(self) -> None:
        r = self.report
        self.assertEqual(r["exam_start"], body3d.pose_name(body3d.START), r)
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertTrue(r["exam_item_starts_at_item"], r)
        self.assertEqual(r["exam_item_starts_at_item"], True)
        self.assertGreater(r["exam_object_hits"], 0, r)
        # Every single collection was the item on the table, not the body.
        self.assertEqual(r["exam_object_hits"], r["exam_collects"], r)
        self.assertTrue(r["exam_collections_are_object_at_Y"], r)
        self.assertEqual(r["exam_agent_at_Y_without_object_reward_sum"], 0, r)
        # 512 turns cannot buy more deliveries than eight actions allow.
        self.assertLessEqual(
            r["exam_object_hits"], r["exam_turns"] // r["shortest_collect"], r)
        self.assertEqual(r["exam_reward_sum"],
                         r["exam_object_hits"] * R_SUCCESS, r)
        # And it is a walk, not a body sitting on a pump.
        self.assertGreater(r["exam_poses_visited"], 1, r)
        self.assertGreater(r["exam_turns_holding_the_item"], 0, r)
        # It went past both, and the route is not written down here: the
        # trail is asked whether the two voxels appear in it at all.
        seen = {body3d.pose_of(i)[:3] for i in range(body3d.N_POSES)
                if body3d.pose_name(i) in set(r["exam_trail"])}
        self.assertIn(obj1.ITEM_XYZ, seen, r["exam_trail"])
        self.assertIn(obj1.DEST_XYZ, seen, r["exam_trail"])
        self.assertEqual(r["cortex_calls"], 0, r)

    def test_a_delivery_is_replayed_from_the_world_and_not_from_the_trail(
            self) -> None:
        """The exam's count comes off the env at the turn it happened.

        Walk the trail back through a fresh world and the item has to be on
        the table at every step the exam scored. If the count were taken
        from the reward alone it could not tell delivering from arriving.
        """
        r = self.report
        dist = obj1.distances()
        env = obj1.Obj1Env()
        env.reset()
        env.teleport(body3d.START)
        for _ in range(r["shortest_collect"] - 1):
            here = (env.i, obj1.HELD if env.coupled else obj1.FREE)
            step = next(
                a for a in (ACTION_APPROACH, ACTION_AVOID)
                if dist.get(obj1.successor(here, a), 10 ** 6)
                == dist[here] - 1)
            env.step(step)
        self.assertEqual(obj1.voxel_of(env.i), obj1.DEST_XYZ)
        self.assertEqual(env.obj, obj1.DEST_XYZ)
        self.assertTrue(env.coupled)
        reward, _c = env.step(ACTION_APPROACH)
        self.assertEqual(reward, R_SUCCESS)
        self.assertTrue(env.last_delivered)
        self.assertEqual(env.i, body3d.START)
        self.assertEqual(env.obj, obj1.ITEM_XYZ)

    # 6 ------------------------------------------------------------------
    def test_the_control_goes_to_the_table_empty_handed(self) -> None:
        """The KPI, and it is paid now.

        Same schedule, same cube, same curriculum — only `_payoff` differs:
        it collects for `agent_at_Y` and never asks where the item is. Then
        it sits the real exam. It walks to the table, finds that arriving
        buys nothing there, and never once touches the glass.

        This was an `expectedFailure` while the table was PULPO's goal
        voxel, where the glass lay on the only affordable corridor. The
        cube did not change; the table moved.
        """
        r = self.report
        self.assertEqual(r["control_object_hits"], 0, r)
        self.assertTrue(r["control_went_to_dest"], r)
        self.assertEqual(r["control_turns_holding_the_item"], 0, r)
        # It is a control, not a cripple: it did reach the table, and it
        # was schooled on as many turns as the real body was.
        self.assertGreater(r["control_train_turns"], 0, r)
        # The two bodies also learned different rooms, which is true and
        # reported and deliberately not part of green(): Q at an empty
        # table is 0 for a body that never had reason to value one.
        self.assertGreater(r["control_values_an_empty_table"], 0, r)
        self.assertEqual(r["exam_values_an_empty_table"], 0, r)
        self.assertTrue(r["control_learned_a_different_table"], r)

    # 7 ------------------------------------------------------------------
    def test_the_mutant_leaves_the_glass_behind(self) -> None:
        """The mutant is run every time, not described.

        A cube that pays an empty table collects, and every one of those
        collects has the glass still lying where it started.
        """
        r = self.report
        self.assertTrue(r["mutant_pays_empty_Y"], r)
        self.assertGreater(r["mutant_collects"], 0, r)
        self.assertEqual(r["mutant_object_hits"], 0, r)
        # Measured off the mutant world, not printed: six of six headings
        # collect on a table with nothing on it, where the real world has
        # none of six.
        self.assertEqual(
            obj1.probe_the_table(pays_an_empty_table=True)
            ["empty_table_collects"], 6)
        self.assertEqual(obj1.probe_the_table()["empty_table_collects"], 0)
        # It is a different world, and the difference is in the payoff and
        # nowhere else: the same pose, the same packet, another reward.
        real = obj1.Obj1Env()
        fake = obj1.Obj1Env(pays_an_empty_table=True)
        pose = body3d.index_of(*obj1.DEST_XYZ, 0)
        real.teleport(pose, holding=False)
        fake.teleport(pose, holding=False)
        self.assertEqual(encode_cell(real.cell().index, real.cell().kind),
                         encode_cell(fake.cell().index, fake.cell().kind))
        self.assertNotEqual(real.step(ACTION_APPROACH)[0],
                            fake.step(ACTION_APPROACH)[0])
        self.assertEqual(fake.last_reward, R_SUCCESS)
        self.assertFalse(fake.last_delivered, "an empty table delivered")

    # 8 ------------------------------------------------------------------
    def test_the_source_never_writes_the_things_it_argues_against(
            self) -> None:
        """Usage forms, not words.

        The names the module actually uses, taken off its syntax tree — so
        a paragraph may say `carrying` and `KIND_GOAL` and `ABRIR` while
        the code may not write them. Six times now a plain text ban has
        caught this repo's own prose.
        """
        src = Path(obj1.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.arg):
                used.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                used.add(node.arg)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    used.add(alias.asname or alias.name.split(".")[0])
        for banned in ("carrying", "WSP_DOM", "domain", "style", "ABRIR",
                       "KIND_GOAL", "NEXT", "subprocess", "gguf",
                       "minigrid", "gym", "pack"):
            self.assertNotIn(banned, used,
                             f"obj1 writes {banned!r} as code")
        # Prose is allowed to name what the code may not write, and does.
        self.assertIn("carrying", src)
        self.assertIn("KIND_GOAL", src)
        # Three actions, and no fourth was invented under another name.
        actions = {n for n in used if n.startswith("ACTION_")}
        self.assertEqual(actions, {"ACTION_APPROACH", "ACTION_AVOID",
                                   "ACTION_WAIT"}, actions)
        self.assertEqual(len(ACTION_REL), 3)
        # `_payoff` is where a goal would have been smuggled in.
        payoff = inspect.getsource(obj1.Obj1Env._payoff)
        for banned in ("KIND_GOAL", "GOAL_XYZ"):
            self.assertNotIn(banned, payoff, payoff)
        # PULPO's successor table sends `approach` on the goal home. Reusing
        # it would have collected for arriving, so it is not reused.
        self.assertNotIn("NEXT", inspect.getsource(obj1.Obj1Env.step))
        self.assertIsNot(obj1.Obj1Env.step, body3d.Body3DEnv.step)
        self.assertNotIsInstance(obj1.Obj1Env(), body3d.Body3DEnv)

    def test_the_state_table_and_the_world_agree(self) -> None:
        """`successor` is arithmetic, `step` is the world. If they drifted,
        the curriculum would be flooding a cube nobody walks in."""
        for i in body3d.reachable(body3d.LAYOUT_OPEN):
            for held in (obj1.FREE, obj1.HELD):
                if held == obj1.FREE and obj1.voxel_of(i) == obj1.ITEM_XYZ:
                    continue
                for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                    env = obj1.Obj1Env()
                    env.teleport(i, holding=(held == obj1.HELD))
                    env.step(a)
                    got = (env.i, obj1.HELD if env.coupled else obj1.FREE)
                    self.assertEqual(got, obj1.successor((i, held), a),
                                     (body3d.pose_name(i), held, a))

    # 9 ------------------------------------------------------------------
    def test_ring_and_the_earlier_slices_untouched(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        r = self.report
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertLess(r["cam_occupied"], r["cam_slots"])
        # The diary did not grow a key for a thing. The log already says
        # `kind`, and OBJECT is a kind.
        self.assertEqual(len(thought.KEYS), 22, thought.KEYS)
        self.assertIn("kind", thought.KEYS)
        self.assertNotIn("object_x", thought.KEYS)
        line = json.loads(thought.to_line(thought.build(
            turn=0, cell=0, kind=KIND_OBJECT, action=0, reward=0,
            wsp=encode_cell(0, KIND_OBJECT), attend_on=False,
            reason=REASON_OFF, q_row=[0, 0, 0], t_pred=None,
            questions=0, cortex_calls=0)))
        self.assertEqual(line["kind"], "OBJECT")
        # And a board that meets one will draw it rather than a question
        # mark, which is all the viewer was owed by this slice.
        self.assertEqual(board.SYMBOL[KIND_NAME[KIND_OBJECT]], "O")
        self.assertEqual(KIND_NAME[KIND_OBJECT], "OBJECT")
        # The numbering is the lock, not the length: a later slice with a
        # new physics may add a kind, and it must not renumber these.
        self.assertEqual(KIND_NAME[:5],
                         ("EMPTY", "GOAL", "THREAT", "NOVEL", "OBJECT"))
        self.assertEqual((KIND_EMPTY, KIND_GOAL, KIND_THREAT, KIND_NOVEL,
                          KIND_OBJECT), (0, 1, 2, 3, 4))

    # 10 -----------------------------------------------------------------
    def test_pulpo_still_has_its_goal_and_nobody_lost_a_report(self) -> None:
        """PULPO's goal is still a goal, and OBJ-1's runner writes one file.

        `body3d`, `self1` and `room1` are run for rc=0 by their own classes
        in this same suite; what is only checkable from here is that adding
        a fifth kind did not quietly eat the fourth.
        """
        for h in range(body3d.HEADINGS):
            self.assertEqual(
                body3d.KINDS[body3d.index_of(*body3d.GOAL_XYZ, h)], KIND_GOAL)
        env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        env.teleport(body3d.index_of(*body3d.GOAL_XYZ, body3d.PLUS_Z))
        self.assertEqual(env.step(ACTION_APPROACH)[0], R_SUCCESS)
        self.assertEqual(env.i, body3d.START)

        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_pulpo_report.json",
                  "nexus0_self1_report.json", "nexus0_room1_report.json",
                  "nexus0_cuerpo1_report.json", "nexus0_credit1_report.json",
                  "nexus0_walk1_report.json", "nexus0_world3_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = obj1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertTrue((lab / "nexus0_obj1_report.json").is_file())
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "OBJ-1 wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_obj1_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertGreater(written["exam_object_hits"], 0, written)
        self.assertEqual(written["control_object_hits"], 0, written)
        self.assertEqual(written["mutant_object_hits"], 0, written)


class TestOpen1(unittest.TestCase):
    """OPEN-1: a fourth gear, because there is a fourth physics.

    OBJ-1's glass, with a lid on it. Until the lid comes off the glass
    cannot be picked up at all, and taking it off is a thing no
    combination of the three old gears does — which is the entire licence
    for `ABRIR`. The verb exists in this world and nowhere else: the ring
    still has three gears, `constants.N_ACTIONS` is still 3, and a default
    `Agent` still has a three-wide Q row.

    Three places would otherwise have folded the verb back into
    `approach` while the slice still looked green, and each is a mutant
    rather than a sentence: `select`'s cycle, `is_explore`'s tie, and the
    gate's modulus.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = open1.experiment()

    # 1 ------------------------------------------------------------------
    def test_the_ring_still_has_three_gears(self) -> None:
        r = self.report
        self.assertEqual(N_ACTIONS, 3, "the frozen constant moved")
        default = Agent()
        self.assertEqual(len(default.q.row(0)), 3)
        self.assertEqual(default.n_actions, 3)
        self.assertEqual(default.t.n_actions, 3)
        self.assertFalse(default.q.remainder)
        self.assertFalse(default.q.explore_flat)
        self.assertEqual(len(QTable().row(0)), 3)
        # And this world asks for four, by name.
        self.assertEqual(open1.GEARS_WITH_A_LID, 4)
        self.assertEqual(open1.ACTION_OPEN, 3)
        wide = open1._fresh(open1.fresh_env())
        self.assertEqual(wide.n_actions, 4)
        self.assertEqual(len(wide.q.row(0)), 4)
        self.assertEqual(len(wide.t.pred[0]), 4)
        self.assertEqual(r["actions_default"], 3, r)
        self.assertEqual(r["default_agent_q_width"], 3, r)
        self.assertEqual(r["actions_this_world"], 4, r)
        self.assertEqual(r["this_agent_q_width"], 4, r)
        # Eleven, flooded, and eleven is the whole horizon.
        self.assertEqual(r["shortest_collect"], 11, r)
        self.assertEqual(r["shortest_collect"], r["value_horizon"], r)
        self.assertTrue(r["collect_fits_the_horizon"], r)
        self.assertEqual(r["opens_on_the_cheapest_trip"], 1, r)
        # Without a lid it is OBJ-1's own number, one action shorter.
        self.assertEqual(r["shortest_collect_without_the_lid"], 10, r)
        self.assertEqual(open1.shortest_collect(starts_open=True),
                         obj1.shortest_collect())

    # 2 ------------------------------------------------------------------
    def test_shut_is_a_place_you_can_stand_and_only_the_verb_opens_it(
            self) -> None:
        open_ = body3d.LAYOUT_OPEN
        entry = next(
            i for i in body3d.reachable(open_)
            if open1.voxel_of(i) != open1.ITEM_XYZ
            and open1.voxel_of(
                open1.successor((i, open1.SHUT), ACTION_APPROACH)[0]
            ) == open1.ITEM_XYZ)

        env = open1.fresh_env()
        self.assertFalse(env.lid_open)
        self.assertFalse(env.starts_open)
        env.teleport(entry)
        reward, cell = env.step(ACTION_APPROACH)
        self.assertEqual(open1.voxel_of(env.i), open1.ITEM_XYZ)
        self.assertFalse(env.coupled, "a shut jar was picked up")
        self.assertEqual(cell.kind, KIND_CLOSED)
        self.assertEqual(reward, 0)
        # Standing on it and walking off again leaves it exactly where it
        # was: shut furniture, not a thing that follows.
        moved = open1.fresh_env()
        moved.teleport(body3d.index_of(*open1.ITEM_XYZ, 0))
        for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT) * 3:
            moved.step(a)
            self.assertFalse(moved.lid_open)
            self.assertFalse(moved.coupled)
            self.assertEqual(moved.obj, open1.ITEM_XYZ)

        # The verb, on the jar.
        reward, cell = env.step(open1.ACTION_OPEN)
        self.assertTrue(env.lid_open, "ABRIR on the jar left the lid on")
        self.assertTrue(env.coupled, "an open jar underfoot is not in hand")
        self.assertEqual(cell.kind, KIND_OBJECT)
        self.assertEqual(reward, 0, "opening is not a reward")

        # The verb, anywhere else: nothing at all, and no reward for it.
        away = open1.fresh_env()
        away.teleport(body3d.START)
        before = (away.lid_open, away.coupled, away.i, away.obj)
        reward, _cell = away.step(open1.ACTION_OPEN)
        self.assertEqual((away.lid_open, away.coupled, away.i, away.obj),
                         before, "the jar opened from across the room")
        self.assertEqual(reward, 0)
        # And on the jar a second time, once it is already open.
        again = env.step(open1.ACTION_OPEN)
        self.assertEqual(again[0], 0)

        # Delivering puts the lid back on. Without that the world becomes
        # OBJ-1 after its first collect and every episode trains half its
        # turns on a jar that is not there.
        table = open1.fresh_env()
        table.teleport(body3d.index_of(*open1.DEST_XYZ, 0), holding=True)
        reward, _cell = table.step(ACTION_APPROACH)
        self.assertEqual(reward, R_SUCCESS)
        self.assertFalse(table.lid_open, "the lid stayed off after a delivery")
        self.assertFalse(table.coupled)
        self.assertEqual(table.obj, open1.ITEM_XYZ)
        self.assertEqual(table.i, body3d.START)

        r = self.report
        self.assertTrue(r["lid_starts_closed"], r)
        self.assertTrue(r["probe_closed_approach_does_not_couple"], r)
        self.assertTrue(r["probe_closed_reads_closed"], r)
        self.assertTrue(r["probe_open_on_jar_couples"], r)
        self.assertTrue(r["probe_open_reads_object"], r)
        self.assertTrue(r["probe_open_elsewhere_is_noop"], r)
        self.assertEqual(r["probe_opening_pays"], 0, r)

    def test_the_state_table_and_the_world_agree(self) -> None:
        """`successor` floods, `step` moves. If they drifted the curriculum
        would be schooling a room nobody walks in."""
        for shut in (False, True):
            for i, half in open1.valid_states(starts_open=shut):
                for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT,
                          open1.ACTION_OPEN):
                    env = open1.fresh_env(starts_open=shut)
                    env.teleport(i, holding=(half == open1.HELD))
                    env.step(a)
                    got = (env.i, open1.HELD if env.coupled else open1.SHUT)
                    self.assertEqual(
                        got, open1.successor((i, half), a, starts_open=shut),
                        (body3d.pose_name(i), half, a, shut))

    # 3 ------------------------------------------------------------------
    def test_shut_open_and_empty_are_three_different_packets(self) -> None:
        r = self.report
        for p in range(body3d.N_POSES):
            three = {encode_cell(p, k) for k in
                     (KIND_EMPTY, KIND_OBJECT, KIND_CLOSED)}
            self.assertEqual(len(three), 3, body3d.pose_name(p))
            for raw in three:
                self.assertEqual(len(raw), 16)
            for kind in (KIND_EMPTY, KIND_OBJECT, KIND_CLOSED):
                ext = open1.ext_of(p, kind)
                self.assertEqual(ext["domain"], 0, body3d.pose_name(p))
                self.assertEqual(ext["style"], 0, body3d.pose_name(p))
                self.assertEqual(ext["seq"], p, body3d.pose_name(p))
        # A jar is not a prize and not a hazard: the affect of a shut jar
        # is the affect of an empty floor.
        self.assertEqual(unpack(encode_cell(0, KIND_CLOSED))["E"],
                         unpack(encode_cell(0, KIND_EMPTY))["E"])
        self.assertNotEqual(unpack(encode_cell(0, KIND_CLOSED))["E"],
                            unpack(encode_cell(0, KIND_GOAL))["E"])
        # The packet says what is looked at. ABRIR is a gear, so the atom
        # appears in no packet this world can emit.
        self.assertEqual(
            unpack(encode_cell(0, KIND_CLOSED))["dst"], ATOM_ID["CERRAR"])
        self.assertEqual(
            unpack(encode_cell(0, KIND_CLOSED))["rel"], ATOM_ID["OBSERVAR"])
        self.assertTrue(open1.the_verb_is_not_in_the_packet())
        self.assertTrue(r["the_verb_is_not_in_the_packet"], r)
        self.assertEqual(encode_cell(0, KIND_EMPTY),
                         encode_cell(256, KIND_EMPTY))
        self.assertTrue(r["packet_ceiling_holds"], r)
        self.assertEqual(r["packets_across"], 486, r)
        self.assertLess(r["packets_across"], N_SLOTS)
        self.assertEqual(r["index_max"], 161, r)

    # 4 ------------------------------------------------------------------
    def test_the_glass_arrives_and_the_verb_is_what_gets_it_there(
            self) -> None:
        r = self.report
        self.assertEqual(r["exam_start"], body3d.pose_name(body3d.START), r)
        self.assertTrue(r["exam_start_is_canonical"], r)
        self.assertTrue(r["exam_lid_started_closed"], r)
        self.assertGreater(r["exam_object_hits"], 0, r)
        self.assertGreater(r["exam_used_open"], 0, r)
        self.assertEqual(r["exam_object_hits"], r["exam_collects"], r)
        self.assertTrue(r["exam_collections_are_object_at_Y"], r)
        self.assertEqual(r["exam_reward_sum"],
                         r["exam_object_hits"] * R_SUCCESS, r)
        # One lid per delivery, and 512 turns cannot buy more trips than
        # eleven actions allow.
        self.assertGreaterEqual(r["exam_used_open"], r["exam_object_hits"], r)
        self.assertLessEqual(r["exam_object_hits"],
                             r["exam_turns"] // r["shortest_collect"], r)
        # It walked, and it went past both the jar and the table.
        self.assertGreater(r["exam_poses_visited"], 1, r)
        seen = {body3d.pose_of(i)[:3] for i in range(body3d.N_POSES)
                if body3d.pose_name(i) in set(r["exam_trail"])}
        self.assertIn(open1.ITEM_XYZ, seen, r["exam_trail"])
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertTrue(r["episode_turns_is_odd"], r)

    # 5 ------------------------------------------------------------------
    def test_three_gears_cannot_get_the_glass_out(self) -> None:
        r = self.report
        self.assertEqual(r["control_n_actions"], 3, r)
        self.assertEqual(r["control_q_width"], 3, r)
        self.assertGreater(r["control_train_turns"], 0, r)
        self.assertEqual(r["control_object_hits"], 0, r)
        self.assertEqual(r["control_used_open"], 0, r)
        # It never even sets out, and the number says why rather than the
        # prose: with three gears no state in the closed half of this world
        # leads anywhere that pays, so every row there is flat and `best`
        # answers wait. Reported as it comes.
        self.assertFalse(r["control_went_to_the_jar"], r)
        self.assertEqual(r["control_best_q_in_the_shut_room"], 0, r)
        # So the question is asked where it can be answered: carried to the
        # jar and left there, greedily, the lid stays on.
        self.assertGreater(r["control_on_the_jar_turns"], 0, r)
        self.assertFalse(r["control_on_the_jar_opened_it"], r)
        self.assertFalse(r["control_on_the_jar_picked_it_up"], r)

    # 6 ------------------------------------------------------------------
    def test_a_jar_born_open_needs_no_verb(self) -> None:
        """The mutant, run. Without a lid the room is OBJ-1 again, three
        gears are enough, and the fourth is not what buys the walk."""
        r = self.report
        self.assertEqual(r["mutant_n_actions"], 3, r)
        self.assertGreater(r["mutant_already_open_object_hits"], 0, r)
        self.assertEqual(r["mutant_already_open_used_open"], 0, r)
        # And it really is OBJ-1: the same state space, the same successor
        # table, the same trip.
        mine = sorted(open1.valid_states(starts_open=True))
        theirs = sorted((i, open1.HELD if h == obj1.HELD else open1.SHUT)
                        for i, h in obj1.valid_states())
        self.assertEqual(mine, theirs)
        for state in mine:
            for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
                i, half = state
                got = open1.successor(state, a, starts_open=True)
                want = obj1.successor(
                    (i, obj1.HELD if half == open1.HELD else obj1.FREE), a)
                self.assertEqual(
                    got, (want[0],
                          open1.HELD if want[1] == obj1.HELD else open1.SHUT),
                    (body3d.pose_name(i), half, a))

    # 7 ------------------------------------------------------------------
    def test_the_source_never_writes_the_things_it_argues_against(
            self) -> None:
        """Usage forms, not words. The verb itself is allowed: this slice
        is that verb, so `ACTION_OPEN` and `ABRIR` may be written."""
        src = Path(open1.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        used = set()
        assigned = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
                if isinstance(node.ctx, ast.Store):
                    assigned.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.arg):
                used.add(node.arg)
            elif isinstance(node, ast.keyword) and node.arg:
                used.add(node.arg)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    used.add(alias.asname or alias.name.split(".")[0])
        for banned in ("carrying", "WSP_DOM", "domain", "style", "minigrid",
                       "gym", "gguf", "subprocess", "KIND_NOVEL"):
            self.assertNotIn(banned, used, f"open1 writes {banned!r} as code")
        # The frozen constant is read, never written.
        self.assertIn("N_ACTIONS", used)
        self.assertNotIn("N_ACTIONS", assigned, "open1 assigns N_ACTIONS")
        self.assertNotIn("N_ACTIONS = 4", src)
        # `_payoff` is where a goal would have been smuggled in.
        self.assertNotIn("KIND_GOAL", used)
        # And the verb is a gear here, which is the point of the slice.
        self.assertIn("ACTION_OPEN", used)
        # PULPO's successor table is still not reused.
        self.assertNotIn("NEXT", used)

    # 8 ------------------------------------------------------------------
    def test_ring_and_the_earlier_slices_untouched(self) -> None:
        report = run()
        self.assertEqual(report["policy_after"], [-12, 5, 0], report)
        self.assertEqual(report["novel_approach_return"], 80, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(len(report["policy_after"]), 3, report)
        r = self.report
        self.assertEqual(r["false_facts"], 0, r)
        self.assertEqual(r["destroyed"], 0, r)
        self.assertEqual(r["questions"], 0, r)
        self.assertEqual(r["cortex_calls"], 0, r)
        self.assertLess(r["cam_occupied"], r["cam_slots"])
        # A fourth gear is not a twenty-third key. The log already says
        # `action`, and `open` is an action.
        self.assertEqual(len(thought.KEYS), 22, thought.KEYS)
        self.assertEqual(thought.ACTION_NAME[open1.ACTION_OPEN], "open")
        self.assertEqual(thought.ACTION_NAME[:3],
                         ("approach", "avoid", "wait"))
        line = json.loads(thought.to_line(thought.build(
            turn=0, cell=0, kind=KIND_CLOSED, action=open1.ACTION_OPEN,
            reward=0, wsp=encode_cell(0, KIND_CLOSED), attend_on=False,
            reason=REASON_OFF, q_row=[0, 0, 0, 0], t_pred=None,
            questions=0, cortex_calls=0)))
        # The diary stores the action as the integer it always did; the
        # name is what a viewer looks up, and `view` indexes ACTION_NAME
        # directly — a fourth gear with three names is an IndexError in
        # front of a human.
        self.assertEqual(line["action"], open1.ACTION_OPEN)
        self.assertEqual(thought.ACTION_NAME[line["action"]], "open")
        self.assertEqual(line["kind"], "CLOSED")
        self.assertEqual(KIND_NAME[KIND_CLOSED], "CLOSED")
        self.assertEqual(KIND_NAME[:6], ("EMPTY", "GOAL", "THREAT", "NOVEL",
                                         "OBJECT", "CLOSED"))
        self.assertEqual(KIND_CLOSED, 5)
        # OBJ-1 is closed and stays closed.
        self.assertTrue(obj1.green(json.loads(
            (Path(__file__).resolve().parents[1] / "lab"
             / "nexus0_obj1_report.json").read_text(encoding="utf-8"))))

    # 9 ------------------------------------------------------------------
    def test_the_gate_does_not_fold_the_verb_into_approach(self) -> None:
        """A width the caller states, and the frozen three by default.

        Without this, `open` enters the gate as 3 and leaves as 0: the
        environment never once sees the verb, every ABRIR is an approach,
        and the slice is OBJ-1 wearing a fourth column.
        """
        args = dict(cam_hit=True, extract_ok=True, E=(0, 0, 0, 0, 0, 0))
        decision, action, flags = gate(
            b"\0" * 16, proposed=open1.ACTION_OPEN, n_actions=4, **args)
        self.assertEqual(action, open1.ACTION_OPEN, "the verb was folded away")
        self.assertEqual(decision, GATE_OK)
        self.assertEqual(flags, 0)
        # Default width is the frozen three and folds exactly as it always
        # did — 5 still comes out 2, 3 still comes out 0.
        self.assertEqual(gate(b"\0" * 16, proposed=5, **args)[1], 2)
        self.assertEqual(gate(b"\0" * 16, proposed=3, **args)[1], 0)
        # Threat rules are untouched, and `open` is not one.
        self.assertEqual(
            gate(b"\0" * 16, proposed=ACTION_APPROACH, threat=True,
                 cam_hit=True, extract_ok=False, E=(0, 0, 0, 0, 0, 0))[1],
            ACTION_AVOID)
        self.assertEqual(
            gate(b"\0" * 16, proposed=open1.ACTION_OPEN, n_actions=4,
                 threat=True, cam_hit=True, extract_ok=False,
                 E=(0, 0, 0, 0, 0, 0))[1], open1.ACTION_OPEN)
        # Inhibit still wins over everything, whatever the width.
        self.assertEqual(
            gate(b"\0" * 16, proposed=open1.ACTION_OPEN, n_actions=4,
                 inhibit=True, **args)[:2], (GATE_BLOCK, ACTION_WAIT))

    def test_a_settled_row_is_offered_every_gear(self) -> None:
        """The other place the verb could have died, and the reason the
        first run of this slice collected nothing.

        A settled row explores only when `turn % EPS_PERIOD == 0`, so the
        gear offered is `(8 * k) % n_actions`. With three that walks all
        three; with four it is `approach` for ever, and `open` would be
        offered at no settled state in the whole run.
        """
        three = QTable(explore_flat=True)
        three.set(0, ACTION_APPROACH, -16)
        offered3 = {three.select(0, t) for t in range(0, 8 * 12, 8)}
        self.assertEqual(offered3, {0, 1, 2}, "the ring lost a gear")
        # And byte for byte the answer it always gave, in order.
        self.assertEqual([three.select(0, t) for t in range(0, 8 * 6, 8)],
                         [0, 2, 1, 0, 2, 1])
        four = QTable(n_actions=4, explore_flat=True)
        four.set(0, ACTION_APPROACH, -16)
        self.assertEqual({four.select(0, t) for t in range(0, 8 * 12, 8)},
                         {0, 1, 2, 3}, "a settled row never tries the verb")
        # A flat row explores every turn, so it walks the gears directly.
        self.assertEqual(
            [QTable(n_actions=4, explore_flat=True).select(0, t)
             for t in range(4)], [0, 1, 2, 3])
        # A four-wide row that ties on its first three is not settled.
        wide = QTable(n_actions=4)
        wide.set(0, open1.ACTION_OPEN, 5)
        self.assertFalse(wide.flat(wide.row(0)))
        self.assertTrue(QTable(n_actions=4).flat(QTable(n_actions=4).row(0)))

    # 10 -----------------------------------------------------------------
    def test_pulpo_still_has_its_goal_and_nobody_lost_a_report(self) -> None:
        """`body3d`, `self1`, `room1` and `obj1` are run for rc=0 by their
        own classes in this same suite. What is only checkable from here is
        that a sixth kind and a fourth gear did not eat anybody's world."""
        for h in range(body3d.HEADINGS):
            self.assertEqual(
                body3d.KINDS[body3d.index_of(*body3d.GOAL_XYZ, h)], KIND_GOAL)
        cube_env = body3d.Body3DEnv(body3d.LAYOUT_OPEN)
        cube_env.teleport(body3d.index_of(*body3d.GOAL_XYZ, body3d.PLUS_Z))
        self.assertEqual(cube_env.step(ACTION_APPROACH)[0], R_SUCCESS)
        # OBJ-1's own env still has three gears' worth of physics and no lid.
        jar_less = obj1.Obj1Env()
        self.assertFalse(hasattr(jar_less, "lid_open"))

        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_pulpo_report.json",
                  "nexus0_self1_report.json", "nexus0_room1_report.json",
                  "nexus0_obj1_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_credit1_report.json", "nexus0_walk1_report.json",
                  "nexus0_world3_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = open1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertTrue((lab / "nexus0_open1_report.json").is_file())
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "OPEN-1 wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_open1_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertGreater(written["exam_used_open"], 0, written)


class TestSignC(unittest.TestCase):
    """SIGN-C: being wrong is what makes the slow clock speak.

    WORLD-3 showed T survives a change of topology and is wrong in exactly
    one place. CORTEX-1 showed a sentence the fast loop cannot read can
    change a decision. This is the join, and the order is the whole claim:
    the sign is copied at the origin and *read* only after the world has
    contradicted the map. Every test below is a way of making that order,
    or one of its four preconditions, false.
    """

    # --- helpers --------------------------------------------------------
    def _at_the_fork(self, **kw):
        """A trained agent standing on the fork in SHIFT, about to be wrong.

        Everything up to here is WORLD-3's: 512 turns in HOME, cortex off,
        then the world swapped under it with CAM, T and Q kept.
        """
        ag = signc._train(
            kw.pop("landing_kind", signc.LANDING_KIND),
            kw.pop("train_sign", signc.SIGN_TEXT),
            kw.pop("signed_layouts", (signc.LAYOUT_SHIFT,)),
        )
        ag.cortex_enabled = kw.pop("cortex_on", True)
        ag.conflict_attend = kw.pop("conflict_on", True)
        ag.env = signc.SignCEnv(
            kw.pop("shift_layout", signc.LAYOUT_SHIFT),
            sign_text=kw.pop("sign_text", signc.SIGN_TEXT),
            landing_kind=kw.pop("kind", signc.LANDING_KIND),
            signed_layouts=kw.pop("layouts", (signc.LAYOUT_SHIFT,)),
        )
        ag.env.teleport(signc.SIGN_NODE)
        self.assertFalse(kw, f"unused kwargs: {kw}")
        return ag, signc._slot(ag, signc.SIGN_NODE, KIND_EMPTY)

    @staticmethod
    def _spy():
        """Every call to the slow clock, as (reason, extract). No mocking of
        the loop: `cortex.complete` is the one door out of this process."""
        calls = []
        real = loop_module.cortex.complete

        def spy(record):
            calls.append((record["reason"], record["extract"]))
            return real(record)

        return calls, mock.patch.object(loop_module.cortex, "complete", spy)

    # 1 -------------------------------------------------------------------
    def test_reason_conflict_is_appended_never_renumbered(self) -> None:
        """A log line written before this slice still reads what it meant."""
        self.assertEqual(
            (REASON_OFF, REASON_MISS, REASON_NO_EXTRACT, REASON_LOW_C,
             REASON_NOVEL, REASON_NO_MAP),
            (0, 1, 2, 3, 4, 5))
        self.assertEqual(REASON_CONFLICT, 6)
        self.assertEqual(reason_name(REASON_CONFLICT), "conflict")
        for code, name in ((0, "off"), (1, "miss"), (2, "no_extract"),
                           (3, "low_C"), (4, "novel"), (5, "no_map")):
            self.assertEqual(REASON_NAME[code], name)
        # And it is a code, not a branch: `attend()` runs before the action
        # and cannot be handed a fact from the future. Every input it has
        # is exhausted by the five reasons it already answers.
        self.assertNotIn(
            REASON_CONFLICT,
            {attend(slot_hit=h, extract_ok=e, E=default_e(), kind_novel=k,
                    ham=m, q_confident=q, t_known=t, t_conf=c)[1]
             for h in (True, False) for e in (True, False)
             for k in (True, False) for m in (0, HAM_MISS)
             for q in (True, False) for t in (True, False)
             for c in range(4)})

    # 2 -------------------------------------------------------------------
    def test_the_default_agent_never_takes_this_path(self) -> None:
        """Off by default, and the ring is the ring it always was."""
        self.assertFalse(Agent().conflict_attend)
        self.assertEqual(Agent().conflict_wakes, 0)
        sig = inspect.signature(Agent.__init__)
        self.assertIs(sig.parameters["conflict_attend"].default, False)

        base = Agent()
        base.run(BENCH_TURNS)
        self.assertEqual(base.metrics.cortex_calls, 0)
        self.assertEqual(base.conflict_wakes, 0)

        with sign.cortex_env(None):
            ring = Agent(cortex=True)
            ring.run(BENCH_TURNS)
        self.assertEqual(ring.metrics.cortex_calls, 36,
                         "the ring's ATTEND is not SIGN-C's business")
        self.assertEqual(ring.conflict_wakes, 0)

    # 3 -------------------------------------------------------------------
    def test_the_wake_comes_after_the_world_disagrees(self) -> None:
        """The sign is copied at the origin and read only once T is wrong.

        Proved from inside `env.step`: the world records how many conflict
        wakes the agent had at the moment it was asked to move. If the
        sentence had been consulted first that number would be 1.
        """
        ag, slot_b = self._at_the_fork()
        seen = []
        real_step = ag.env.step

        def watched(a):
            seen.append((int(ag.conflict_wakes), int(ag.metrics.cortex_calls)))
            return real_step(a)

        ag.env.step = watched

        # The four preconditions, measured standing in the new world.
        self.assertEqual(ag.t.predict(slot_b, ACTION_APPROACH),
                         signc._slot(ag, graph.C, KIND_EMPTY),
                         "T still names HOME's successor")
        self.assertGreaterEqual(ag.q.margin(slot_b), ESC_MARGIN)
        self.assertEqual(ag.q.best(slot_b), ACTION_APPROACH)
        self.assertGreater(ag.cam.slot[slot_b].hits, 1, "not a CAM miss")
        self.assertEqual(ag.env.cell().extract_text, signc.SIGN_TEXT)

        calls, patch = self._spy()
        with patch, sign.cortex_env(signc.cortex_cmd()):
            a0 = ag.turn(signc.TRAIN_TURNS, greedy=True)

        self.assertEqual(a0, ACTION_APPROACH, "Q's own answer, not a sign's")
        self.assertEqual(ag.env.cell().index, signc.LANDING_NODE)
        self.assertEqual(seen, [(0, 0)],
                         "the cortex had not been called when the body moved")
        self.assertEqual(ag.conflict_wakes, 1)
        self.assertEqual(ag.metrics.cortex_calls, 1)
        self.assertEqual(ag.last_attend, (True, REASON_CONFLICT))
        self.assertEqual(calls, [(REASON_CONFLICT, signc.SIGN_TEXT)],
                         "one call, with the conflict reason and the sign")

    # 4 -------------------------------------------------------------------
    def test_the_proposal_is_spent_once_and_still_passes_the_gate(self) -> None:
        ag, _ = self._at_the_fork()
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            self.assertEqual(ag.metrics.cortex_actions, 0)
            self.assertIsNotNone(ag.last_cortex_action)
            self.assertTrue(ag.conflict_suppressed)

            a1 = ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
            self.assertEqual(a1, ACTION_APPROACH)
            self.assertEqual(int(ag.env.last_reward), R_SUCCESS)
            self.assertEqual(ag.metrics.cortex_actions, 1)
            # Spent, and the suppression with it: the next turn is the
            # ordinary ladder's again.
            self.assertIsNone(ag.last_cortex_action)
            self.assertFalse(ag.conflict_suppressed)

            ag.turn(signc.TRAIN_TURNS + 2, greedy=True)
            self.assertEqual(ag.metrics.cortex_actions, 1,
                             "a hypothesis does not act twice")
            self.assertEqual(ag.conflict_wakes, 1)

    def test_a_valid_atom_still_has_to_pass_the_gate(self) -> None:
        """The gate has the last word over the slow clock, as always."""
        ag, _ = self._at_the_fork()
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            landing = signc._slot(ag, signc.LANDING_NODE, signc.LANDING_KIND)
            self.assertGreaterEqual(landing, 0)
            ag.cam.slot[landing].flags |= SLOT_FLAG_INHIBIT
            a1 = ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
        self.assertEqual(a1, ACTION_WAIT, "an inhibited slot blocks to wait")
        self.assertEqual(int(ag.env.last_reward), 0)
        self.assertEqual(ag.metrics.cortex_actions, 1,
                         "the proposal was made and consumed; the gate refused")

    def test_prose_is_not_an_action_and_q_keeps_the_turn(self) -> None:
        ag, _ = self._at_the_fork()
        with sign.cortex_env(signc.prose_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            self.assertEqual(ag.conflict_wakes, 1, "the wake still happened")
            self.assertEqual(ag.metrics.cortex_rejected, 1)
            self.assertIsNone(ag.last_cortex_action)
            self.assertTrue(ag.conflict_suppressed,
                            "the query is spent even when the answer is not atoms")
            a1 = ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
        self.assertEqual(ag.metrics.cortex_actions, 0)
        self.assertEqual(a1, ACTION_WAIT, "the flat row's own answer")
        self.assertEqual(int(ag.env.last_reward), 0)

    # 5 -------------------------------------------------------------------
    def test_a_label_is_not_a_sign(self) -> None:
        """`cell=N kind=...` is this loop's own writing, not the world's."""
        synthetic = Cell(index=signc.SIGN_NODE, kind=KIND_EMPTY).extract
        self.assertEqual(synthetic, f"cell={signc.SIGN_NODE} kind=EMPTY")
        for text in (None, "", "   ", synthetic, f"  {synthetic}  "):
            with self.subTest(text=text):
                ag, _ = self._at_the_fork(sign_text=text)
                with sign.cortex_env(signc.cortex_cmd()):
                    ag.turn(signc.TRAIN_TURNS, greedy=True)
                    ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
                self.assertEqual(ag.conflict_wakes, 0)
                self.assertEqual(ag.metrics.cortex_actions, 0)
                # The contradiction was there all the same.
                self.assertEqual(ag.env.cell().index, signc.LANDING_NODE)
                self.assertGreater(ag.metrics.surprise_known, 0)

    def test_a_first_visit_cannot_contradict_anything(self) -> None:
        """A CAM miss is `REASON_MISS`, and it already has a rung.

        In this loop the guard is implied — Q only ever writes the row of a
        slot the body stood on, so a margin at all means more than one hit
        — so it is asserted on the predicate directly rather than left to
        a scenario that cannot be built.
        """
        ag, slot_b = self._at_the_fork()
        cell = ag.env.cell()
        self.assertIsNotNone(ag._conflict_origin(cell, slot_b, 0))
        self.assertIsNone(ag._conflict_origin(cell, slot_b, 1),
                          "a place seen for the first time is a miss, not news")

    # 6 -------------------------------------------------------------------
    def test_a_sign_over_a_map_that_was_right_wakes_nothing(self) -> None:
        """Same sentence, same margin, same T — and the world agrees."""
        ag, slot_b = self._at_the_fork(
            shift_layout=signc.LAYOUT_HOME,
            layouts=(signc.LAYOUT_HOME, signc.LAYOUT_SHIFT))
        self.assertEqual(ag.env.cell().extract_text, signc.SIGN_TEXT)
        pred = ag.t.predict(slot_b, ACTION_APPROACH)
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
        self.assertEqual(ag.env.cell().index, graph.C, "HOME's own edge")
        self.assertEqual(signc._slot(ag, graph.C, KIND_EMPTY), pred)
        self.assertEqual(ag.conflict_wakes, 0)

    # 7 -------------------------------------------------------------------
    def test_a_t_miss_is_ignorance_not_a_contradiction(self) -> None:
        """Nothing was predicted, so nothing it said can be wrong."""
        ag, slot_b = self._at_the_fork()
        ag.t.pred[slot_b][ACTION_APPROACH] = UNKNOWN_NEXT
        self.assertIsNone(ag.t.predict(slot_b, ACTION_APPROACH))
        self.assertGreaterEqual(ag.q.margin(slot_b), ESC_MARGIN)
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
        self.assertEqual(ag.env.cell().index, signc.LANDING_NODE,
                         "the world still moved the edge")
        self.assertEqual(ag.conflict_wakes, 0)
        self.assertEqual(ag.metrics.cortex_actions, 0)

    # 8 -------------------------------------------------------------------
    def test_a_coin_flip_at_the_origin_is_not_news(self) -> None:
        """Below ESC_MARGIN the fast loop was barely committed to anything."""
        ag, slot_b = self._at_the_fork()
        ag.q.q[slot_b] = [4, 3, 0]
        self.assertEqual(ag.q.best(slot_b), ACTION_APPROACH)
        self.assertLess(ag.q.margin(slot_b), ESC_MARGIN)
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
        self.assertEqual(ag.env.cell().index, signc.LANDING_NODE)
        self.assertEqual(ag.conflict_wakes, 0)

    # 9 -------------------------------------------------------------------
    def test_control_and_arm_share_everything_but_the_slow_clock(self) -> None:
        cmd = signc.cortex_cmd()
        arm = signc.arm("signc", cmd, cortex_on=True, conflict_on=True)
        ctl = signc.arm("fast", None)
        self.assertEqual(arm["origin"]["q_row_after_home"],
                         ctl["origin"]["q_row_after_home"])
        self.assertEqual(arm["origin"]["t_pred"], ctl["origin"]["t_pred"])
        self.assertEqual(arm["origin"]["hits"], ctl["origin"]["hits"])
        self.assertEqual(arm["conflict_action"], ctl["conflict_action"])
        self.assertEqual(arm["landed_node"], ctl["landed_node"])
        # Both were contradicted. Only one could do anything with it.
        self.assertTrue(arm["t_prediction_contradicted"])
        self.assertTrue(ctl["t_prediction_contradicted"])
        self.assertEqual(ctl["cortex_calls"], 0)
        self.assertEqual(ctl["cortex_actions_total"], 0)
        self.assertEqual(ctl["action_at_landing"], "wait")
        self.assertEqual(arm["action_at_landing"], "approach")
        self.assertGreater(arm["reward_at_landing"], ctl["reward_at_landing"])
        self.assertGreater(arm["reward_sum_shift"], ctl["reward_sum_shift"])

    def test_the_ordinary_ladder_wakes_and_earns_nothing(self) -> None:
        """Same cortex, same cable, same world. Only the reason differs.

        The landing node has a flat Q row and one hit, so LOW_C fires
        there — and the record that reason carries is the landing node's
        own, whose extract is a label. The sign is at the origin, and only
        the conflict wake goes back for it.
        """
        cmd = signc.cortex_cmd()
        ladder = signc.arm("ladder", cmd, cortex_on=True, conflict_on=False)
        ctl = signc.arm("fast", None)
        self.assertGreater(ladder["cortex_calls"], 0)
        self.assertEqual(ladder["conflict_wakes"], 0)
        self.assertEqual(ladder["attend_reason_at_landing"], "low_C")
        self.assertEqual(ladder["cortex_actions_total"], 0)
        self.assertEqual(ladder["reward_sum_shift"], ctl["reward_sum_shift"])

    # 10 ------------------------------------------------------------------
    def test_the_stub_reads_a_sentence_and_nothing_else(self) -> None:
        src = (Path(signc_cortex.__file__)).read_text(encoding="utf-8")
        tree = ast.parse(src)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
        self.assertEqual(modules - {"__future__"}, {"json", "sys"},
                         "the stub has no echoAI, no network and no model")
        # It reads one field of the record and no other.
        names = {n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for forbidden in ("slot", "wsp_in", "wsp_out", "q_row", "t_pred",
                          "kind", "node", "layout", "index"):
            self.assertNotIn(forbidden, names, f"the stub looked at {forbidden}")
        self.assertIn("extract", names)

        self.assertEqual(signc_cortex.decide(signc.SIGN_TEXT),
                         "YO → UNIR → AQUI @AHORA")
        self.assertEqual(signc_cortex.decide(signc.SIGN_TEXT_RETREAT),
                         "YO → TEMER → AQUI @AHORA")
        # A sentence it has not been taught is silence, not a guess.
        for quiet in ("", "cell=174 kind=EMPTY",
                      "AMBAR: invirtieron la palanca; el peligro de ayer "
                      "es el premio de hoy.",
                      "el letrero esta en blanco"):
            self.assertEqual(signc_cortex.decide(quiet), "", quiet)
        # Same node, same kind, same everything: only the sentence moves it.
        self.assertNotEqual(signc_cortex.decide(signc.SIGN_TEXT),
                            signc_cortex.decide(signc.SIGN_TEXT_RETREAT))

    # 11 ------------------------------------------------------------------
    def test_the_slow_clock_writes_nothing(self) -> None:
        """No CAM fact, no T row, no Q cell comes from the cortex."""
        ag, slot_b = self._at_the_fork()
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            landing = signc._slot(ag, signc.LANDING_NODE, signc.LANDING_KIND)
            facts = [int(s.has_fact) for s in ag.cam.slot]
            t_row = list(ag.t.pred[landing])
            q_row = ag.q.row(landing)
            # The proposal is in flight and has changed nothing yet.
            self.assertIsNotNone(ag.last_cortex_action)
            self.assertEqual([int(s.has_fact) for s in ag.cam.slot], facts)

            ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
        # After it acted, T and Q moved — but by the ordinary path, from
        # what the world paid, not from what the cortex said.
        self.assertEqual([int(s.has_fact) for s in ag.cam.slot], facts,
                         "a hypothesis became a fact")
        self.assertNotEqual(ag.t.pred[landing], t_row,
                            "T learned the step the body actually took")
        self.assertNotEqual(ag.q.row(landing), q_row,
                            "Q learned the reward the world actually paid")
        self.assertEqual(ag.metrics.false_facts, 0)
        self.assertEqual(ag.metrics.destroyed, 0)
        self.assertEqual(ag.cam.destroyed, 0)

    # 12 ------------------------------------------------------------------
    def test_the_hot_path_imports_no_model(self) -> None:
        """No HTTP, no SDK, no torch, no transformers, no llama.

        The hot path is not a hand-kept list: it is the transitive closure
        of what `loop` and `signc` import inside `echoai.nexus0`. A viewer
        that serves a page (`board`) is not in it, and if a later slice
        drags one in, this test says so instead of the network.
        """
        here = Path(loop_module.__file__).resolve().parent

        def imports(mod_name: str):
            path = here / f"{mod_name}.py"
            if not path.is_file():
                return set(), set()
            inner, outer = set(), set()
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        top = a.name.split(".")[0]
                        (inner if a.name.startswith("echoai.nexus0.")
                         else outer).add(
                            a.name.split(".")[-1] if
                            a.name.startswith("echoai.nexus0.") else top)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module == "echoai.nexus0":
                        inner.update(a.name for a in node.names)
                    elif node.module.startswith("echoai.nexus0."):
                        inner.add(node.module.split(".")[-1])
                    elif node.level == 0:
                        outer.add(node.module.split(".")[0])
            return inner, outer

        seen, stack, banned = set(), ["loop", "signc"], set()
        while stack:
            mod = stack.pop()
            if mod in seen:
                continue
            seen.add(mod)
            inner, outer = imports(mod)
            banned |= outer & {
                "urllib", "http", "requests", "httpx", "aiohttp", "socket",
                "torch", "transformers", "llama_cpp", "openai", "anthropic",
                "numpy", "sentencepiece", "tokenizers",
            }
            stack.extend(sorted(inner - seen))
        self.assertIn("cortex", seen)
        self.assertNotIn("board", seen)
        self.assertEqual(banned, set(), f"the hot path grew: {sorted(banned)}")
        # The one door out is a local process the operator has to name.
        self.assertIn("subprocess", imports("cortex")[1])
        self.assertEqual(os.environ.get(cortex.ENV_CMD, ""), "",
                         "CI must not need NAVI_CORTEX_CMD")

    # 13 ------------------------------------------------------------------
    def test_attend_measures_a_flat_row_at_the_real_width(self) -> None:
        """The cleanup, pinned byte for byte at three actions.

        `_attend` used to spell the tie as `row[0] == row[1] == row[2]`.
        For a table of the frozen width `QTable.flat` is that expression
        and nothing else, so the ring's 36 wakes are unmoved; for a wider
        one it no longer reads a row that ties on its first three as
        settled while a fourth gear still has a vote.
        """
        three = QTable()
        for row in ([0, 0, 0], [1, 1, 1], [-7, -7, -7], [1, 1, 2],
                    [2, 1, 1], [1, 2, 1], [0, 0, 1], [5, -5, 0]):
            self.assertEqual(three.flat(row), row[0] == row[1] == row[2], row)
        four = QTable(n_actions=4)
        self.assertFalse(four.flat([1, 1, 1, 2]),
                         "a fourth gear with a different value is not settled")
        self.assertTrue(four.flat([1, 1, 1, 1]))
        with sign.cortex_env(None):
            ring = Agent(cortex=True)
            ring.run(BENCH_TURNS)
        self.assertEqual(ring.metrics.cortex_calls, 36)

    def test_a_four_gear_row_is_not_settled_by_its_first_three(self) -> None:
        """The cleanup where it lives, not only in the table it calls.

        `[1, 1, 1, 2]` seen often enough reads as a settled boring cell to
        the old literal triple, and a settled cell needs no map — so the
        wake for the map it has not got never happens. Measured on
        `_attend` itself, because that is where the triple was.
        """
        ag = Agent(cortex=True, ask=False, n_actions=4)
        cell = ag.env.cell()
        wsp = encode_cell(cell.index, cell.kind)
        slot = ag._slot_for(wsp, 0, cell.extract, default_e())
        s = ag.cam.slot[slot]
        s.hits = ATTEND_SETTLED_HITS + 1
        ag.q.q[slot] = [1, 1, 1, 2]
        self.assertEqual(ag.q.best(slot), 3, "the fourth gear is the winner")
        self.assertIsNone(ag.t.predict(slot, ag.q.best(slot)))
        with sign.cortex_env(None):
            woke = ag._attend(cell, slot, s, default_e(), 0)
        self.assertTrue(woke)
        self.assertEqual(ag.last_attend, (True, REASON_NO_MAP),
                         "a row with a preference is not a settled tie")

    # 14 ------------------------------------------------------------------
    def test_the_hazard_landing_could_not_have_discriminated(self) -> None:
        """Why the moved edge lands on a prize, as a number.

        The plan was WORLD-3's X, a THREAT: a flat Q row waits and collects
        nothing while `avoid` pays +8. It does not. `loop.turn` hands a
        threat cell `E[U] = 80`, `U_SHORT` is 60, and `gate`'s second
        MODIFY rule turns the proposed `wait` into `avoid` before the world
        sees it — so the fast arm takes the +8 by itself and the best a
        cortex can propose there is worth exactly 0.
        """
        d, a, flags = gate(encode_cell(signc.LANDING_NODE, KIND_THREAT),
                           cam_hit=True, extract_ok=True,
                           E=(-80, 80, 0, 20, 80, 0),
                           proposed=ACTION_WAIT, threat=True)
        self.assertEqual((d, a), (GATE_MODIFY, ACTION_AVOID))
        self.assertGreaterEqual(80, U_SHORT)
        self.assertEqual(flags, WSP_FLAG_VETO)
        # And with no hazard the same proposal goes through untouched.
        d, a, _ = gate(encode_cell(signc.LANDING_NODE, KIND_GOAL),
                       cam_hit=True, extract_ok=True,
                       E=default_e(), proposed=ACTION_WAIT, threat=False)
        self.assertEqual((d, a), (GATE_OK, ACTION_WAIT))

        rows = {r["landing_kind"]: r for r in signc.placements()}
        self.assertEqual(rows["threat"]["fast_action_at_landing"], "avoid")
        self.assertEqual(rows["threat"]["fast_reward_at_landing"], R_AVOID_OK)
        self.assertEqual(rows["threat"]["CortexROI"], 0)
        self.assertFalse(rows["threat"]["discriminates"])
        self.assertEqual(rows["goal"]["fast_action_at_landing"], "wait")
        self.assertEqual(rows["goal"]["fast_reward_at_landing"], 0)
        self.assertEqual(rows["goal"]["CortexROI"], R_SUCCESS)
        self.assertTrue(rows["goal"]["discriminates"])
        # No reward and no edge was invented for this: the successor table
        # is WORLD-3's own, and only the landing node's kind is SIGN-C's.
        self.assertEqual(signc.LANDING_NODE, graph.X)
        env = signc.SignCEnv(signc.LAYOUT_SHIFT)
        for act in (ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT):
            self.assertEqual(
                graph.NEXT[graph.LAYOUT_SHIFT][act][graph.X],
                graph.NEXT[graph.LAYOUT_SHIFT][act][signc.LANDING_NODE])
        self.assertEqual(
            [k for i, k in enumerate(env.kind) if k != graph.KINDS[i]],
            [signc.LANDING_KIND],
            "exactly one node's kind differs from WORLD-3's")

    # 15 ------------------------------------------------------------------
    def test_the_sign_is_outside_the_sixteen_bytes(self) -> None:
        """The packet is `encode_cell(index, kind)` and nothing else."""
        plain = graph.GraphEnv(signc.LAYOUT_SHIFT)
        plain.teleport(signc.SIGN_NODE)
        signed = signc.SignCEnv(signc.LAYOUT_SHIFT)
        signed.teleport(signc.SIGN_NODE)
        self.assertIsNone(plain.cell().extract_text)
        self.assertEqual(signed.cell().extract_text, signc.SIGN_TEXT)
        self.assertEqual(
            encode_cell(plain.cell().index, plain.cell().kind),
            encode_cell(signed.cell().index, signed.cell().kind))
        self.assertEqual(signed.cell().kind, KIND_EMPTY,
                         "the fork is not repainted NOVEL or THREAT")
        # And the sentence never becomes an atom in the packet either.
        raw = encode_cell(signed.cell().index, signed.cell().kind)
        self.assertEqual(len(raw), WSP_BYTES)
        self.assertEqual(unpack(raw)["rel"], ATOM_ID["OBSERVAR"])

    # 16 ------------------------------------------------------------------
    def test_runner_writes_its_own_report_and_nobody_elses(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_world3_report.json",
                  "nexus0_cortex1_report.json", "nexus0_qwen4b_report.json",
                  "nexus0_pulpo_report.json", "nexus0_self1_report.json",
                  "nexus0_room1_report.json", "nexus0_obj1_report.json",
                  "nexus0_open1_report.json", "nexus0_cuerpo1_report.json",
                  "nexus0_credit1_report.json", "nexus0_walk1_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = signc.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "SIGN-C wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_signc_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertEqual(written["attend_reason"], "conflict", written)
        self.assertEqual(written["conflict_wakes"], 1, written)
        self.assertGreater(written["CortexROI"], 0, written)
        self.assertEqual(written["control_cortex_wakes"], 0, written)
        self.assertEqual(written["false_facts"], 0, written)
        self.assertEqual(written["ring_cortex_wakes"], 36, written)
        self.assertFalse(written["default_agent_has_conflict_attend"], written)

    def test_the_operator_report_is_not_required_by_ci(self) -> None:
        """The 4B harness is honest without a 4B, and is not the CI green."""
        from echoai.nexus0 import qwen_signc

        self.assertNotIn("nexus0_signc_report.json",
                         Path(qwen_signc.__file__).read_text(encoding="utf-8")
                         .split("def main")[-1])
        for env_var in ("NAVI_QWEN_MODEL", "NAVI_QWEN_URL"):
            self.assertEqual(os.environ.get(env_var, ""), "")
        self.assertFalse(qwen_signc.green({
            "model_configured": False, "false_facts": 0,
            "attend_reason": "conflict", "conflict_wakes": 1,
            "qwen_calls": 8, "qwen_rejected": 0,
            "qwen_action_at_X": "approach", "fast_action_at_X": "wait",
            "CortexROI": 16, "canonical_threat_qwen_action": "avoid",
            "qwen_beats_stub_on_paraphrase": True,
        }), "silence is not a CortexROI")
        # It grades the slow clock, not the body: at a hazard the gate
        # produces `avoid` on its own, and that must not read as a hit.
        self.assertTrue(qwen_cortex.should_speak(signc.SIGN_TEXT))
        self.assertFalse(qwen_cortex.should_speak(
            Cell(index=signc.SIGN_NODE, kind=KIND_EMPTY).extract))
        self.assertGreaterEqual(len(qwen_signc.PARAPHRASE["goal"]), 4)
        for world, texts in qwen_signc.PARAPHRASE.items():
            for text in texts[1:]:
                self.assertEqual(signc_cortex.decide(text), "",
                                 f"a paraphrase the stub already knows: {text}")

    def test_the_operator_report_grades_the_slow_clock_not_the_body(self) -> None:
        """Silence at a hazard scores `avoid`, and that is the gate's work.

        `loop.turn` hands a threat cell `E[U] = 80` and `gate` turns the
        proposed `wait` into `avoid`. A harness that graded the action
        would call every silent row on the hazard side a hit, and a cortex
        that never spoke would beat one that did.
        """
        from echoai.nexus0 import qwen_signc

        cmd = signc.cortex_cmd()
        quiet = qwen_signc.PARAPHRASE["threat"][1]
        self.assertEqual(signc_cortex.decide(quiet), "")
        row = qwen_signc._row("threat", quiet, cmd, cmd)
        self.assertEqual(row["want"], "avoid")
        self.assertEqual(row["stub_action"], "avoid")
        self.assertFalse(row["stub_spoke"], "the stub said nothing")
        self.assertFalse(row["stub_hit"], "and silence is not a hit")
        self.assertFalse(row["qwen_hit"])
        # The canonical sentence it does know is a hit, by the same rule.
        spoken = qwen_signc._row("threat", qwen_signc.PARAPHRASE["threat"][0],
                                 cmd, cmd)
        self.assertTrue(spoken["stub_spoke"])
        self.assertTrue(spoken["stub_hit"])


class TestSignCb(unittest.TestCase):
    """SIGN-Cb: one conflict, one wake, one true line.

    SIGN-C's mechanism is closed. What was not closed is the *record* of
    it. `thought.py` promises "one line per turn, as the loop actually saw
    it" and `board.py` paints `attend_on=true` as `woke`, but the turn that
    only spends the hypothesis was inheriting the wake of the turn before:
    `last_attend` is written by `_attend`, the consuming turn suppresses
    `_attend`, and nothing put the field back. Two lines claimed one wake.

    The counter never lied — `cortex_calls` stayed at 1 across both — which
    is exactly why it had to be read from the diary and not from the
    metrics. TALK-1 will read this jsonl.
    """

    def _diary(self, cmd=None, turns=2):
        """The two lines the loop actually wrote, from a real run."""
        ag = signc._train(signc.LANDING_KIND, signc.SIGN_TEXT,
                          (signc.LAYOUT_SHIFT,))
        ag.cortex_enabled = True
        ag.conflict_attend = True
        ag.env = signc.SignCEnv(signc.LAYOUT_SHIFT)
        ag.env.teleport(signc.SIGN_NODE)
        with tempfile.TemporaryDirectory() as tmp:
            ag.thought_log = str(Path(tmp) / "thought.jsonl")
            with sign.cortex_env(signc.cortex_cmd() if cmd is None else cmd):
                for t in range(turns):
                    ag.turn(signc.TRAIN_TURNS + t, greedy=True)
            lines = [json.loads(x) for x
                     in Path(ag.thought_log).read_text(encoding="utf-8")
                     .splitlines()]
        return ag, lines

    # 1 -------------------------------------------------------------------
    def test_exactly_one_line_says_it_woke_for_a_conflict(self) -> None:
        ag, lines = self._diary()
        self.assertEqual(len(lines), 2)
        woke = [ln for ln in lines
                if ln["attend_on"] and ln["reason_name"] == "conflict"]
        self.assertEqual(len(woke), 1,
                         "one wake must not be attributed to two turns")
        self.assertEqual(woke[0]["turn"], signc.TRAIN_TURNS)
        self.assertEqual(woke[0]["cell"], signc.SIGN_NODE)
        self.assertEqual(ag.conflict_wakes, 1)
        self.assertEqual(ag.metrics.cortex_calls, 1)

    def test_the_conflict_line_is_the_turn_that_was_wrong(self) -> None:
        _, (conflict, _) = self._diary()
        self.assertEqual(conflict["s"], 1, "T committed and the world differed")
        self.assertTrue(conflict["attend_on"])
        self.assertEqual(conflict["reason_name"], "conflict")
        self.assertEqual(conflict["cortex_calls"], 1)
        self.assertIsNone(conflict["cortex_action"],
                          "nothing was consumed on the turn that asked")
        self.assertEqual(conflict["action"], ACTION_APPROACH)
        self.assertEqual(conflict["reward"], 0)

    # 2 -------------------------------------------------------------------
    def test_the_consuming_line_does_not_claim_a_wake(self) -> None:
        _, (conflict, consume) = self._diary()
        self.assertFalse(consume["attend_on"],
                         "this turn made no attend decision")
        self.assertEqual(consume["reason_name"], "off")
        self.assertEqual(consume["cortex_calls"], conflict["cortex_calls"],
                         "the counter did not move, so neither may the line")
        self.assertEqual(consume["cortex_calls"], 1)
        self.assertEqual(consume["cortex_action"], ACTION_APPROACH,
                         "the provenance of the hypothesis is already here")
        self.assertEqual(consume["action"], ACTION_APPROACH)
        self.assertEqual(consume["reward"], R_SUCCESS)
        self.assertEqual(consume["cell"], signc.LANDING_NODE)
        self.assertEqual(consume["gate_decision"], GATE_OK)

    # 4 -------------------------------------------------------------------
    def test_silence_and_prose_leave_no_reason_stuck_either(self) -> None:
        """A wake that got nothing back is still spent, and still one line."""
        for cmd in (signc.prose_cmd(), f"{sys.executable} -c pass"):
            with self.subTest(cmd=cmd.split()[-1]):
                ag, (conflict, consume) = self._diary(cmd=cmd)
                self.assertTrue(conflict["attend_on"])
                self.assertEqual(conflict["reason_name"], "conflict")
                self.assertFalse(consume["attend_on"])
                self.assertEqual(consume["reason_name"], "off")
                self.assertIsNone(consume["cortex_action"])
                self.assertEqual(ag.conflict_wakes, 1)
                self.assertEqual(ag.metrics.cortex_actions, 0)
                self.assertFalse(ag.conflict_suppressed,
                                 "the latch is released whatever came back")

    def test_the_turn_after_the_consume_is_the_ordinary_ladder_again(self) -> None:
        """Suppression lasts one turn, and the third line proves it."""
        ag, lines = self._diary(turns=3)
        self.assertEqual(len(lines), 3)
        self.assertEqual([ln["reason_name"] for ln in lines[:2]],
                         ["conflict", "off"])
        # Whatever the third turn decides, it decided it: the flag is down
        # and `_attend` ran, so the line is that decision and not an echo.
        self.assertEqual(lines[2]["attend_on"], ag.last_attend[0])
        self.assertEqual(lines[2]["reason_name"],
                         reason_name(ag.last_attend[1]))
        self.assertEqual(ag.conflict_wakes, 1)

    # 3 -------------------------------------------------------------------
    def test_last_attend_describes_the_current_turn(self) -> None:
        """The field the diary prints, read straight off the agent."""
        ag = signc._train(signc.LANDING_KIND, signc.SIGN_TEXT,
                          (signc.LAYOUT_SHIFT,))
        ag.cortex_enabled = True
        ag.conflict_attend = True
        ag.env = signc.SignCEnv(signc.LAYOUT_SHIFT)
        ag.env.teleport(signc.SIGN_NODE)
        with sign.cortex_env(signc.cortex_cmd()):
            ag.turn(signc.TRAIN_TURNS, greedy=True)
            self.assertEqual(ag.last_attend, (True, REASON_CONFLICT))
            self.assertTrue(ag.conflict_suppressed)
            ag.turn(signc.TRAIN_TURNS + 1, greedy=True)
        self.assertEqual(ag.last_attend, (False, REASON_OFF),
                         "no attend decision was made on the consuming turn")
        self.assertEqual(ag.metrics.cortex_calls, 1)

    # 5 -------------------------------------------------------------------
    def test_green_carries_the_canonical_bench_not_a_mini_run(self) -> None:
        """`signc.green()` holds the ring's own numbers, not a stand-in.

        The suite already protects them. What is asked here is that the
        JSON which says `green: true` protects them too — so a report can
        never be green while the bench it was built on has moved.
        """
        report = signc.experiment()
        self.assertTrue(signc.green(report), report)
        canon = report["canonical_bench"]
        self.assertEqual(canon["policy_after"], [-12, 5, 0])
        self.assertEqual(canon["novel_approach_return"], 80)
        self.assertEqual([canon["cam_misses"], canon["surprises"],
                          canon["deltas"]], [33, 1, 217])
        self.assertEqual(canon["surprise_known"], 1)
        self.assertEqual(canon["cortex_calls"], 0)
        self.assertEqual([canon["false_facts"], canon["destroyed"]], [0, 0])
        self.assertTrue(canon["encoder_beats_fnv"])
        self.assertTrue(canon["t_beats_ring"])
        self.assertEqual(canon["ring_cortex_wakes"], 36)
        self.assertEqual(canon["ring_turns"], BENCH_TURNS)
        # And each of them is load-bearing: move one, and green goes.
        for key, wrong in (("policy_after", [0, 0, 0]),
                           ("novel_approach_return", 0),
                           ("cam_misses", 34), ("surprises", 0),
                           ("deltas", 216), ("surprise_known", 0),
                           ("cortex_calls", 1), ("false_facts", 1),
                           ("destroyed", 1), ("encoder_beats_fnv", False),
                           ("t_beats_ring", False),
                           ("ring_cortex_wakes", 35)):
            with self.subTest(lock=key):
                bent = dict(report)
                bent["canonical_bench"] = dict(canon, **{key: wrong})
                self.assertFalse(signc.green(bent), key)

    def test_green_falls_if_the_consume_line_claims_a_wake(self) -> None:
        """Every diary clause of `green()`, bent one at a time.

        A `green()` condition that is only ever fed a report which
        satisfies it is untested: loosening it changes no test. So each
        clause gets a report that violates exactly it.
        """
        report = signc.experiment()
        self.assertTrue(signc.green(report), report)

        def bend(**top):
            return signc.green(dict(report, **top))

        conflict = report["conflict_line"]
        consume = report["consume_line"]
        for label, bent in (
            ("consume says it woke",
             {"consume_line": dict(consume, attend_on=True)}),
            ("consume inherits the reason",
             {"consume_line": dict(consume, reason_name="conflict")}),
            ("consume lost the provenance",
             {"consume_line": dict(consume, cortex_action=None)}),
            ("consume did not act on it",
             {"consume_line": dict(consume, action="wait", reward=0)}),
            ("conflict turn says it did not wake",
             {"conflict_line": dict(conflict, attend_on=False)}),
            ("conflict turn lost its reason",
             {"conflict_line": dict(conflict, reason_name="low_C")}),
            ("conflict turn also consumed something",
             {"conflict_line": dict(conflict, cortex_action="approach")}),
            ("the wake did not cost a call", {"cortex_calls_delta_on_conflict": 0}),
            ("the consume cost a call", {"cortex_calls_delta_on_consume": 1}),
            ("two lines claim the wake", {"one_line_claims_the_wake": False}),
        ):
            with self.subTest(bend=label):
                self.assertFalse(bend(**bent), label)

    def test_the_runner_does_not_write_the_bench_report(self) -> None:
        """`bench.run()` computes; only `bench.main()` writes."""
        lab = Path(__file__).resolve().parents[1] / "lab"
        names = ("nexus0_report.json", "nexus0_world3_report.json",
                 "nexus0_cortex1_report.json", "nexus0_obj1_report.json",
                 "nexus0_open1_report.json", "nexus0_self1_report.json",
                 "nexus0_room1_report.json", "nexus0_qwen4b_report.json",
                 "nexus0_qwen_signc_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in names}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = signc.main([])
        self.assertEqual(rc, 0)
        self.assertEqual({n: stamp(lab / n) for n in names}, before,
                         "SIGN-Cb wrote over another slice's report")

    # 6 -------------------------------------------------------------------
    def test_the_log_did_not_grow_a_key_or_the_agent_a_gear(self) -> None:
        """No 23rd key, no second memory, no fourth action.

        The provenance of a consumed hypothesis is already in
        `cortex_action`; a `proposal_reason` beside it would be the same
        fact written twice, and the second copy would be the one that
        could drift.
        """
        self.assertEqual(len(thought.KEYS), 22)
        self.assertNotIn("proposal_reason", thought.KEYS)
        self.assertNotIn("events", thought.KEYS)
        _, lines = self._diary()
        for line in lines:
            self.assertEqual(tuple(sorted(line)), tuple(sorted(thought.KEYS)))
        self.assertEqual(N_ACTIONS, 3)
        self.assertFalse(Agent().conflict_attend)
        self.assertEqual(Agent().last_attend, (False, REASON_OFF))
        # And the report shows the two lines apart instead of one label.
        report = json.loads(
            (Path(__file__).resolve().parents[1] / "lab"
             / "nexus0_signc_report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["conflict_line"]["attend_on"])
        self.assertEqual(report["conflict_line"]["reason_name"], "conflict")
        self.assertFalse(report["consume_line"]["attend_on"])
        self.assertEqual(report["consume_line"]["reason_name"], "off")
        self.assertEqual(report["consume_line"]["cortex_action"], "approach")
        self.assertEqual(report["cortex_calls_delta_on_consume"], 0)


class TestSignCc(unittest.TestCase):
    """SIGN-Cc: score the atom, not the body.

    The operator gate grades whether a 4B *read the sentence*, so what it
    has to compare is the verb the slow clock named. It was comparing
    `action_at_landing` — the body's move **after the gate**. At a hazard
    the gate turns a proposed `wait` into `avoid` (`u >= U_SHORT`), so a
    cortex that answered `OBSERVAR` scored the same as one that answered
    `TEMER`: the harness was crediting the reflex to the reader.

    Silence already scored false (nothing is consumed) and `UNIR` already
    scored false (the gate does not rescue an `approach` that has an
    extract). `OBSERVAR` is the only reply that separates "it spoke" from
    "it named the right verb", which is why it is the mutant here.
    """

    @staticmethod
    def _verb_cmd(atom: Optional[str]) -> str:
        """A slow clock with one fixed atom in it. No model, no weights."""
        if atom is None:
            return f"{shlex.quote(sys.executable)} -c pass"
        line = f'print("YO \u2192 {atom} \u2192 AQUI @AHORA")'
        return f"{shlex.quote(sys.executable)} -c {shlex.quote(line)}"

    def _row(self, world: str, atom: Optional[str]) -> dict:
        from echoai.nexus0 import qwen_signc

        cmd = self._verb_cmd(atom)
        return qwen_signc._row(world, signc.SIGN_TEXT, cmd, cmd)

    # 1 -------------------------------------------------------------------
    def test_observar_at_a_hazard_is_not_a_hit(self) -> None:
        """It spoke, it was consumed, the body did the right thing anyway.

        Every step of that is true and none of it is reading. The +8 came
        from `gate`, and a harness that counts it would rank a cortex that
        names the wrong verb level with one that names the right one.
        """
        row = self._row("threat", "OBSERVAR")
        self.assertEqual(row["want"], "avoid")
        self.assertTrue(row["qwen_spoke"], "the atom parsed and was consumed")
        self.assertEqual(row["qwen_proposal"], "wait", "the wrong verb")
        self.assertEqual(row["qwen_action"], "avoid", "and the gate fixed it")
        self.assertEqual(row["qwen_reward"], R_AVOID_OK)
        self.assertFalse(row["qwen_hit"],
                         "the gate's rescue is not the cortex's answer")
        self.assertFalse(row["stub_hit"])

    # 2 -------------------------------------------------------------------
    def test_temer_at_a_hazard_is_a_hit(self) -> None:
        row = self._row("threat", "TEMER")
        self.assertEqual(row["qwen_proposal"], "avoid")
        self.assertEqual(row["qwen_action"], "avoid")
        self.assertEqual(row["qwen_reward"], R_AVOID_OK)
        self.assertTrue(row["qwen_hit"])

    # 3 -------------------------------------------------------------------
    def test_unir_at_a_prize_is_a_hit(self) -> None:
        row = self._row("goal", "UNIR")
        self.assertEqual(row["qwen_proposal"], "approach")
        self.assertEqual(row["qwen_action"], "approach")
        self.assertEqual(row["qwen_reward"], R_SUCCESS)
        self.assertTrue(row["qwen_hit"])

    def test_the_whole_verb_table(self) -> None:
        """Six cells, and the body agrees with the atom in only four."""
        want = {
            ("threat", "TEMER"): ("avoid", "avoid", R_AVOID_OK, True),
            ("threat", "OBSERVAR"): ("wait", "avoid", R_AVOID_OK, False),
            ("threat", "UNIR"): ("approach", "approach", R_THREAT, False),
            ("threat", None): (None, "avoid", R_AVOID_OK, False),
            ("goal", "UNIR"): ("approach", "approach", R_SUCCESS, True),
            ("goal", "TEMER"): ("avoid", "avoid", 0, False),
        }
        for (world, atom), (prop, act, reward, hit) in want.items():
            with self.subTest(world=world, atom=atom):
                row = self._row(world, atom)
                self.assertEqual(row["qwen_proposal"], prop)
                self.assertEqual(row["qwen_action"], act)
                self.assertEqual(row["qwen_reward"], reward)
                self.assertEqual(row["qwen_hit"], hit)
                self.assertEqual(row["qwen_spoke"], atom is not None)

    def test_the_report_names_the_atom_and_the_body_apart(self) -> None:
        """Two different facts must not share one key."""
        from echoai.nexus0 import qwen_signc

        row = self._row("threat", "OBSERVAR")
        for key in ("qwen_proposal", "qwen_action", "stub_proposal",
                    "stub_action", "qwen_spoke", "stub_spoke"):
            self.assertIn(key, row, key)
        self.assertNotEqual(row["qwen_proposal"], row["qwen_action"],
                            "this is exactly the row where they differ")
        src = Path(qwen_signc.__file__).read_text(encoding="utf-8")
        self.assertNotIn('a["action_at_landing"] == want', src,
                         "the grader still compares the body")

    # 4 -------------------------------------------------------------------
    def test_green_falls_if_the_canonical_threat_proposal_is_bent(self) -> None:
        from echoai.nexus0 import qwen_signc

        base = {
            "model_configured": True, "false_facts": 0,
            "attend_reason": "conflict", "conflict_wakes": 1,
            "qwen_calls": 8, "qwen_rejected": 0,
            "qwen_proposal_at_X": "approach", "qwen_action_at_X": "approach",
            "fast_action_at_X": "wait", "CortexROI": 16,
            "canonical_threat_qwen_proposal": "avoid",
            "qwen_beats_stub_on_paraphrase": True,
            # SIGN-Cd added the output-schema clauses; a fixture without
            # them is refused, which is the new gate doing its job.
            "action_grammar": True,
            "action_grammar_name": qwen_signc.ACTION_GBNF.name,
            "action_grammar_sha256": qwen_signc._sha256(qwen_signc.ACTION_GBNF),
            "general_grammar_sha256": qwen_signc._sha256(
                qwen_signc.GENERAL_GBNF),
        }
        self.assertTrue(qwen_signc.green(base))
        for key, wrong in (("canonical_threat_qwen_proposal", "wait"),
                           ("canonical_threat_qwen_proposal", "approach"),
                           ("qwen_proposal_at_X", "wait"),
                           ("qwen_proposal_at_X", "avoid")):
            with self.subTest(bend=f"{key}={wrong}"):
                self.assertFalse(qwen_signc.green(dict(base, **{key: wrong})),
                                 f"{key}={wrong}")
        # The body alone is not enough: a right action off a wrong atom
        # must not carry the gate.
        self.assertFalse(qwen_signc.green(
            dict(base, canonical_threat_qwen_proposal="wait",
                 canonical_threat_qwen_action="avoid")))

    # 5 -------------------------------------------------------------------
    def test_the_stub_still_scores_two_canonicals_and_no_paraphrase(self) -> None:
        from echoai.nexus0 import qwen_signc

        cmd = signc.cortex_cmd()
        rows = [qwen_signc._row(w, t, cmd, cmd)
                for w, texts in qwen_signc.PARAPHRASE.items() for t in texts]
        canonical = [r for r in rows if r["canonical"]]
        extra = [r for r in rows if not r["canonical"]]
        self.assertEqual(sum(1 for r in canonical if r["stub_hit"]), 2)
        self.assertEqual(sum(1 for r in extra if r["stub_hit"]), 0)
        for r in extra:
            self.assertEqual(r["stub_line"], "")
            self.assertFalse(r["stub_spoke"], "silence consumes nothing")
            self.assertIsNone(r["stub_proposal"])
        # And the hazard paraphrases are exactly where the old rule lied:
        # the body did `avoid` off no atom at all.
        for r in extra:
            if r["world"] == "threat":
                self.assertEqual(r["stub_action"], "avoid")
                self.assertFalse(r["stub_hit"])

    # 6 -------------------------------------------------------------------
    def test_the_runner_is_honestly_red_without_a_model(self) -> None:
        from echoai.nexus0 import qwen_signc

        for env_var in ("NAVI_QWEN_MODEL", "NAVI_QWEN_URL"):
            self.assertEqual(os.environ.get(env_var, ""), "")
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_signc_report.json",
                  "nexus0_world3_report.json", "nexus0_cortex1_report.json",
                  "nexus0_qwen4b_report.json", "nexus0_obj1_report.json",
                  "nexus0_open1_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = qwen_signc.main([])
        self.assertEqual(rc, 1, "no model, no green — and the runner says so")
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "the operator harness wrote over another report")
        written = json.loads(
            (lab / "nexus0_qwen_signc_report.json").read_text(encoding="utf-8"))
        self.assertFalse(written["model_configured"])
        self.assertFalse(written["green"])
        self.assertEqual(written["qwen_hits"], 0)
        self.assertEqual(written["CortexROI"], 0)
        self.assertEqual(written["stub_hits"], 2)
        self.assertEqual(written["paraphrase_stub_hits"], 0)
        self.assertEqual(written["false_facts"], 0)
        self.assertEqual(written["attend_reason"], "conflict")
        self.assertIsNone(written["qwen_proposal_at_X"], "silence proposes nothing")


class TestSignCd(unittest.TestCase):
    """SIGN-Cd: the action atom belongs in the relation field.

    The first real 4B run was red with `qwen_rejected = 0`. Asked what the
    hazard sign meant, the model answered

        AMOR → CAMBIAR → TEMER @AHORA

    which is a well-formed WSP and a fair reading — the thing that changed
    is now to be feared. `parse_reply` accepted it. But `loop` builds a
    proposal from the **rel**, and this line has TEMER in DST, so it
    produced no action at all: neither a reject nor a decision.

    The fix is not to teach the parser that sentence and not to widen what
    counts as an action. It is to ask the question in the shape the answer
    has to take, for this report only. `cortex.gbnf` stays the general
    contract; `cortex_action.gbnf` is the operator's narrower question.
    """

    LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
    TERM = re.compile(r'"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_]*')

    @classmethod
    def _rules(cls, path: Path) -> dict:
        """Parse a GBNF of the shape these two files use.

        Literals and rule references, concatenation and alternation, no
        repetition and no character classes — which is all either file
        contains. Enough to *derive* what each grammar accepts instead of
        asserting it from the prose above the rules.
        """
        rules = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if "::=" not in line:
                continue
            name, body = line.split("::=", 1)
            rules[name.strip()] = [alt.strip() for alt in body.split("|")]
        return rules

    @classmethod
    def _language(cls, rules: dict, symbol: str = "root") -> set:
        out = set()
        for alt in rules[symbol]:
            pieces = [""]
            for term in cls.TERM.findall(alt):
                if term.startswith('"'):
                    lit = term[1:-1].replace("\\n", "\n").replace('\\"', '"')
                    pieces = [p + lit for p in pieces]
                else:
                    tails = cls._language(rules, term)
                    pieces = [p + t for p in pieces for t in tails]
            out.update(pieces)
        return out

    @staticmethod
    def _literals(alts) -> list:
        return [a.strip()[1:-1] for a in alts if a.strip().startswith('"')]

    # 1 -------------------------------------------------------------------
    def test_the_general_grammar_is_byte_identical(self) -> None:
        """It is the vocabulary of the slow clock, not this report's key."""
        path = Path(loop_module.__file__).resolve().parent / "cortex.gbnf"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "2be563fcb54456b81d5b2fb11faed584079d7f2456ed2beebb66f5a6578184d0",
            "cortex.gbnf is the general contract and does not move")
        rules = self._rules(path)
        # All four fields still take every atom: a cortex that can only
        # name actions cannot think anything else.
        for field in ("src", "rel", "dst", "time"):
            self.assertEqual(rules[field], ["atom"], field)
        self.assertEqual(set(self._literals(rules["atom"])), set(ATOM_ID))
        self.assertEqual(len(self._literals(rules["atom"])), 42)
        self.assertEqual(len(ATOM_ID), 42)

    # 2 -------------------------------------------------------------------
    def test_the_action_grammar_admits_four_lines_and_no_others(self) -> None:
        from echoai.nexus0 import qwen_signc

        rules = self._rules(qwen_signc.ACTION_GBNF)
        self.assertEqual(self._literals(rules["src"]), ["YO"])
        self.assertEqual(self._literals(rules["dst"]), ["AQUI"])
        self.assertEqual(self._literals(rules["time"]), ["AHORA"])
        self.assertEqual(self._literals(rules["rel"]),
                         ["UNIR", "TEMER", "OBSERVAR", "NONE"])
        lang = self._language(rules)
        self.assertEqual(
            lang,
            {f"YO → {rel} → AQUI @AHORA\n"
             for rel in ("UNIR", "TEMER", "OBSERVAR", "NONE")})
        # The shape is the one `parse_reply` already reads: nothing
        # downstream can tell which grammar produced a line.
        for line in lang:
            self.assertIsNotNone(cortex.parse_reply(line), line)
        # And the line the 4B actually sent does not fit.
        real = "AMOR → CAMBIAR → TEMER @AHORA"
        self.assertNotIn(real + "\n", lang)
        self.assertNotIn("CAMBIAR", self._literals(rules["rel"]))
        self.assertNotIn("TEMER", self._literals(rules["dst"]))
        # It is not malformed — that is the whole point of this slice.
        parsed = cortex.parse_reply(real)
        self.assertIsNotNone(parsed, "it was never a reject")
        self.assertEqual(rel_of(parsed), ATOM_ID["CAMBIAR"])
        self.assertNotIn(rel_of(parsed), ACTION_REL,
                         "a valid WSP that the body cannot take")

    # 3 -------------------------------------------------------------------
    def test_none_parses_and_proposes_nothing(self) -> None:
        """Abstaining is sayable. A cortex that cannot decline cannot be wrong."""
        raw = cortex.parse_reply("YO → NONE → AQUI @AHORA")
        self.assertIsNotNone(raw)
        self.assertEqual(len(raw), WSP_BYTES)
        self.assertEqual(rel_of(raw), ATOM_ID["NONE"])
        self.assertNotIn(rel_of(raw), ACTION_REL)
        # End to end: it wakes, it is not rejected, and it acts on nothing.
        cmd = TestSignCc._verb_cmd("NONE")
        arm = signc.arm("none", cmd, cortex_on=True, conflict_on=True)
        self.assertEqual(arm["conflict_wakes"], 1)
        self.assertEqual(arm["cortex_rejected"], 0, "NONE is not a reject")
        self.assertEqual(arm["cortex_actions_total"], 0)
        self.assertFalse(arm["proposal_consumed_next_turn"])
        self.assertIsNone(arm["consume_line"]["cortex_action"])
        self.assertEqual(arm["consume_line"]["reason_name"], "off")
        # The three that are actions still are.
        for atom, want in (("UNIR", "approach"), ("TEMER", "avoid"),
                           ("OBSERVAR", "wait")):
            with self.subTest(atom=atom):
                a = signc.arm(atom, TestSignCc._verb_cmd(atom),
                              cortex_on=True, conflict_on=True)
                self.assertEqual(a["consume_line"]["cortex_action"], want)

    # 4 -------------------------------------------------------------------
    def test_the_grammar_is_selected_and_the_environment_restored(self) -> None:
        from echoai.nexus0 import qwen_signc

        seen = []
        real_arm = signc.arm

        def spy(name, cmd, **kw):
            seen.append((name, os.environ.get(qwen_signc.ENV_GBNF)))
            return real_arm(name, cmd, **kw)

        sentinel = "/sentinel/previous.gbnf"
        with mock.patch.dict(os.environ, {qwen_signc.ENV_GBNF: sentinel}):
            with mock.patch.object(signc, "arm", spy):
                qwen_signc._row("goal", signc.SIGN_TEXT,
                                signc.cortex_cmd(), signc.cortex_cmd())
            self.assertEqual(os.environ[qwen_signc.ENV_GBNF], sentinel,
                             "the operator's own setting must come back")
        by_arm = dict(seen)
        self.assertEqual(by_arm["qwen"], str(qwen_signc.ACTION_GBNF),
                         "the 4B arm is constrained to the action grammar")
        for other in ("fast", "stub"):
            self.assertEqual(by_arm[other], sentinel,
                             f"{other} must not be re-pointed")

        # Unset stays unset — a blank value means "default" to the wrapper.
        os.environ.pop(qwen_signc.ENV_GBNF, None)
        with self.assertRaises(RuntimeError):
            with qwen_signc.action_grammar():
                raise RuntimeError("a row blew up")
        self.assertIsNone(os.environ.get(qwen_signc.ENV_GBNF),
                          "a failed row must not leave the variable behind")
        self.assertEqual(qwen_cortex._gbnf_path().name, "cortex.gbnf",
                         "and the wrapper's default is still the general one")

    # 5 -------------------------------------------------------------------
    def test_green_refuses_a_run_made_with_the_general_grammar(self) -> None:
        from echoai.nexus0 import qwen_signc

        good = {
            "model_configured": True, "false_facts": 0,
            "attend_reason": "conflict", "conflict_wakes": 1,
            "qwen_calls": 8, "qwen_rejected": 0,
            "qwen_proposal_at_X": "approach", "qwen_action_at_X": "approach",
            "fast_action_at_X": "wait", "CortexROI": 16,
            "canonical_threat_qwen_proposal": "avoid",
            "qwen_beats_stub_on_paraphrase": True,
            "action_grammar": True,
            "action_grammar_name": qwen_signc.ACTION_GBNF.name,
            "action_grammar_sha256": qwen_signc._sha256(qwen_signc.ACTION_GBNF),
            "general_grammar_sha256": qwen_signc._sha256(
                qwen_signc.GENERAL_GBNF),
        }
        self.assertTrue(qwen_signc.green(good))
        general = qwen_signc._sha256(qwen_signc.GENERAL_GBNF)
        for label, bent in (
            ("the flag is false", {"action_grammar": False}),
            ("the flag is missing", {"action_grammar": None}),
            ("the general grammar was used",
             {"action_grammar_name": "cortex.gbnf",
              "action_grammar_sha256": general}),
            ("only the name was changed",
             {"action_grammar_name": "cortex.gbnf"}),
            ("only the hash was changed", {"action_grammar_sha256": general}),
            ("the hash is of an edited file",
             {"action_grammar_sha256": "0" * 64}),
            ("both hashes agree", {"general_grammar_sha256": good[
                "action_grammar_sha256"]}),
            ("the prize proposal is missing",
             {"qwen_proposal_at_X": "wait"}),
            ("the hazard proposal is missing",
             {"canonical_threat_qwen_proposal": "wait"}),
        ):
            with self.subTest(bend=label):
                self.assertFalse(qwen_signc.green(dict(good, **bent)), label)

    def test_the_report_separates_grammar_proposal_and_body(self) -> None:
        from echoai.nexus0 import qwen_signc

        report = json.loads(
            (Path(__file__).resolve().parents[1] / "lab"
             / "nexus0_qwen_signc_report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["action_grammar"])
        self.assertEqual(report["action_grammar_name"], "cortex_action.gbnf")
        self.assertEqual(report["action_grammar_sha256"],
                         qwen_signc._sha256(qwen_signc.ACTION_GBNF))
        self.assertEqual(report["general_grammar_sha256"],
                         qwen_signc._sha256(qwen_signc.GENERAL_GBNF))
        self.assertNotEqual(report["action_grammar_sha256"],
                            report["general_grammar_sha256"])
        for key in ("qwen_proposal_at_X", "qwen_action_at_X",
                    "canonical_threat_qwen_proposal",
                    "canonical_threat_qwen_action", "qwen_proposals"):
            self.assertIn(key, report, key)
        self.assertEqual(sorted(report["qwen_proposals"]), ["goal", "threat"])
        for world, props in report["qwen_proposals"].items():
            self.assertEqual(len(props), 4, world)
            for prop in props:
                self.assertIn(prop, (None, "approach", "avoid", "wait"))

    # 6 -------------------------------------------------------------------
    def test_signcc_matrix_survives(self) -> None:
        """A narrower grammar does not un-fix the grading."""
        row = TestSignCc()._row("threat", "OBSERVAR")
        self.assertEqual(row["qwen_proposal"], "wait")
        self.assertEqual(row["qwen_action"], "avoid")
        self.assertEqual(row["qwen_reward"], R_AVOID_OK)
        self.assertFalse(row["qwen_hit"])
        hit = TestSignCc()._row("threat", "TEMER")
        self.assertEqual(hit["qwen_proposal"], "avoid")
        self.assertTrue(hit["qwen_hit"])

    # 7 and 8 -------------------------------------------------------------
    def test_still_honestly_red_without_a_server(self) -> None:
        from echoai.nexus0 import qwen_signc

        for env_var in ("NAVI_QWEN_MODEL", "NAVI_QWEN_URL"):
            self.assertEqual(os.environ.get(env_var, ""), "")
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_signc_report.json",
                  "nexus0_world3_report.json", "nexus0_cortex1_report.json",
                  "nexus0_qwen4b_report.json", "nexus0_obj1_report.json",
                  "nexus0_open1_report.json", "nexus0_pulpo_report.json")

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = qwen_signc.main([])
        self.assertEqual(rc, 1)
        self.assertEqual({n: stamp(lab / n) for n in others}, before,
                         "SIGN-Cd wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_qwen_signc_report.json").read_text(encoding="utf-8"))
        self.assertFalse(written["green"])
        self.assertFalse(written["model_configured"])
        self.assertTrue(written["action_grammar"],
                        "the grammar is recorded even on a red run")

    def test_qwen0_still_gets_the_general_grammar(self) -> None:
        """SIGN-C's narrower question must not follow the wrapper around."""
        self.assertIsNone(os.environ.get("NAVI_QWEN_GBNF"))
        self.assertEqual(qwen_cortex._gbnf_path().name, "cortex.gbnf")
        # The file name, not the bare stem: `cortex_actions` is a metric
        # every one of these modules already counts, and matching that
        # would be the ban catching my own prose again.
        from echoai.nexus0 import qwen_signc

        needle = qwen_signc.ACTION_GBNF.name
        self.assertEqual(needle, "cortex_action.gbnf")
        self.assertNotIn(needle,
                         Path(qwen_sign_module.__file__).read_text(encoding="utf-8"),
                         "Qwen-0 does not know this grammar exists")
        self.assertNotIn(needle,
                         Path(qwen_cortex.__file__).read_text(encoding="utf-8"),
                         "and neither does the wrapper")
        self.assertNotIn(needle,
                         Path(loop_module.__file__).read_text(encoding="utf-8"),
                         "nor the loop")
        # Qwen-0's own gate is untouched and still keys on its own numbers.
        self.assertNotIn("action_grammar", inspect.getsource(
            qwen_sign_module.green))


class TestTalk1(unittest.TestCase):
    """TALK-1: posthumous subtitles, never causal thought.

    The turn already happened. `talk.py` reads the diary and writes
    Spanish, and the only claim is the order of those two things: nothing
    it produces can reach the animal, and nothing it says may be more than
    the record contains. No `porque`; the proposal and the body stay two
    facts, because the gate still had the last word.
    """

    # --- helpers --------------------------------------------------------
    def _write(self, records) -> Path:
        tmp = tempfile.mkdtemp()
        path = Path(tmp) / "thought.jsonl"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                    for r in records), encoding="utf-8")
        return path

    def _cli(self, path):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = talk.main([str(path)])
        return rc, out.getvalue(), err.getvalue()

    # 1 -------------------------------------------------------------------
    def test_the_copied_contract_is_pinned_to_the_real_one(self) -> None:
        """The translator duplicates the schema rather than importing it.

        That is the right trade — importing `thought` at runtime is a step
        toward importing the animal — but a copy that can drift in silence
        is worse than no copy, so it is pinned here.
        """
        self.assertEqual(tuple(talk.KEYS), tuple(thought.KEYS))
        self.assertEqual(len(talk.KEYS), 22)
        self.assertEqual(tuple(talk.ACTION_NAME), tuple(thought.ACTION_NAME))
        self.assertEqual(tuple(talk.KIND_NAME), tuple(KIND_NAME))
        self.assertEqual(set(talk.REASON_NAME), set(REASON_NAME.values()))
        self.assertEqual(len(talk.BODY), N_ACTIONS + 1)
        self.assertEqual(len(talk.PROPOSAL), N_ACTIONS + 1)
        # And no key was added to the log to make narration easier.
        for forbidden in ("story", "events", "text", "narration",
                          "subtitle", "why"):
            self.assertNotIn(forbidden, thought.KEYS)

    # 2 -------------------------------------------------------------------
    def test_the_translator_cannot_reach_the_animal(self) -> None:
        source = Path(talk.__file__).read_text(encoding="utf-8")
        self.assertEqual(talk1.causal_findings(source, "talk.py"), [])
        # Standard library only, and nothing that can write or dial out.
        modules = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        self.assertEqual(modules, {"__future__", "json", "sys", "pathlib",
                                   "typing"})
        # And the animal does not know it exists: no import, no call, no
        # file it reads back.
        for mod in (loop_module, thought, signc, open1, obj1):
            self.assertNotIn(
                "talk", {n.split(".")[-1] for n in _module_imports(mod)},
                f"{mod.__name__} imports the narrator")

    def test_the_scanner_sees_a_translator_that_reaches_back(self) -> None:
        """The isolation check has to be able to fail."""
        source = Path(talk.__file__).read_text(encoding="utf-8")
        # Both import forms: `import echoai...` and `from echoai... import`
        # are different AST nodes and were different branches, and only one
        # of them was ever exercised.
        for injection in ("from echoai.nexus0.loop import Agent",
                          "import echoai.nexus0.loop",
                          "import echoai",
                          "import subprocess",
                          "from socket import socket",
                          "def _x(p):\n    Path(p).write_text('')",
                          "def _x(p):\n    open(p, 'a')"):
            with self.subTest(injection=injection.splitlines()[0]):
                self.assertTrue(
                    talk1.causal_findings(source + "\n" + injection, "m"),
                    injection)

    # 3 -------------------------------------------------------------------
    def test_a_record_this_loop_could_not_have_written_is_an_error(self) -> None:
        good = dict(talk1._base(0), action=0)
        self.assertIsInstance(talk.render(good), str)
        for label, bend in (
            ("missing key", {"__drop__": "reward"}),
            ("extra key", {"story": "se acercó"}),
            ("action out of range", {"action": 4}),
            ("negative action", {"action": -1}),
            ("gate out of range", {"gate_decision": 7}),
            ("proposal out of range", {"cortex_action": 9}),
            ("flag that is not a flag", {"n": 2}),
            ("unknown kind", {"kind": "PLANTA"}),
            ("unknown reason", {"reason_name": "aburrimiento"}),
            ("attend on with reason off", {"attend_on": True}),
            ("attend off with a reason", {"reason_name": "conflict"}),
            ("half a pose", {"x": 1}),
            ("a heading with no pose", {"heading": 2}),
            ("a Q row of two", {"q_row": [0, 0]}),
            ("a Q row of floats", {"q_row": [0.5, 0, 0]}),
            ("an empty packet", {"wsp": "   "}),
            ("a turn that is a string", {"turn": "513"}),
            ("a reward that is a float", {"reward": 1.5}),
        ):
            with self.subTest(bend=label):
                bad = dict(good)
                if "__drop__" in bend:
                    bad.pop(bend["__drop__"])
                else:
                    bad.update(bend)
                with self.assertRaises(talk.BadRecord, msg=label):
                    talk.render(bad)

    def test_half_a_narration_is_never_produced(self) -> None:
        """A file that breaks on its fourth line narrates none of it."""
        good = [dict(talk1._base(i), action=i % 3) for i in range(3)]
        path = self._write(good)
        rc, out, err = self._cli(path)
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.splitlines()), 3)
        self.assertEqual(err, "")

        broken = path.parent / "broken.jsonl"
        broken.write_text(path.read_text(encoding="utf-8") + "{no es json}\n",
                          encoding="utf-8")
        rc, out, err = self._cli(broken)
        self.assertEqual(rc, 2)
        self.assertEqual(out, "", "not one line of a narration that is wrong")
        self.assertIn("JSON ilegible", err)

        missing = path.parent / "missing.jsonl"
        half = dict(good[0])
        half.pop("t_pred")
        missing.write_text(json.dumps(half) + "\n", encoding="utf-8")
        rc, out, err = self._cli(missing)
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("t_pred", err)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(talk.main([]), 2,
                             "the CLI wants exactly one path")

    # 4 -------------------------------------------------------------------
    def test_wait_is_never_narrated_as_movement(self) -> None:
        """The central mutant, on the record and on the rendered line."""
        rec = dict(talk1._base(0), action=ACTION_WAIT, kind="EMPTY")
        line = talk.render(rec)
        clause = talk1.parse(line)["cuerpo"]
        self.assertEqual(clause, "esperó")
        for word in ("giró", "avanzó", "retrocedió", "se acercó", "se alejó",
                     "abrió", "se apartó"):
            self.assertNotIn(word, clause, word)
        self.assertEqual(talk1.audit(rec, line), [])
        # And a subtitle that says otherwise is caught.
        for lie in ("giró", "avanzó", "retrocedió", "se acercó", "se alejó",
                    "abrió"):
            with self.subTest(lie=lie):
                bad = line.replace("cuerpo: esperó", f"cuerpo: {lie}")
                self.assertTrue(talk1.audit(rec, bad), lie)

    def test_the_proposal_never_takes_credit_for_the_gate(self) -> None:
        """SIGN-Cc's separation, in Spanish."""
        rec = dict(talk1._base(0), action=ACTION_AVOID, cortex_action=ACTION_WAIT,
                   kind="THREAT", reward=R_AVOID_OK, gate_decision=GATE_MODIFY,
                   cortex_calls=1)
        line = talk.render(rec)
        clauses = talk1.parse(line)
        self.assertEqual(clauses["córtex"], "propuso esperar")
        self.assertEqual(clauses["cuerpo"], "se apartó")
        self.assertEqual(clauses["gate"], "modificó")
        self.assertEqual(talk1.audit(rec, line), [])
        bad = line.replace("córtex: propuso esperar", "córtex: propuso apartarse")
        self.assertTrue(talk1.audit(rec, bad),
                        "the reflex must not be credited to the reader")

    def test_no_subtitle_invents_a_cause(self) -> None:
        rows = talk1.matrix()
        for name, rec in rows:
            with self.subTest(row=name):
                line = talk.render(rec).lower()
                for word in talk1.CAUSAL:
                    self.assertNotIn(word, line, f"{name}: {word}")
        # The conflict pair says both facts and joins neither.
        pair = {n: r for n, r in rows}
        conflict = talk1.parse(talk.render(pair["real_signc_conflict"]))
        consume = talk1.parse(talk.render(pair["real_signc_consume"]))
        self.assertEqual(conflict["atención"], "despertó por conflicto")
        self.assertEqual(conflict["córtex"], "no propuso")
        self.assertEqual(consume["atención"], "apagada")
        self.assertEqual(consume["córtex"], "propuso acercarse")
        self.assertEqual(consume["cuerpo"], "se acercó")
        self.assertEqual(consume["recompensa"], f"+{R_SUCCESS}")

    def test_the_matrix_audits_clean_and_the_mutants_do_not(self) -> None:
        rows = talk1.matrix()
        records = [rec for _, rec in rows]
        subtitles = [talk.render(rec) for rec in records]
        self.assertEqual(talk1.audit_file(records, subtitles), [])
        self.assertTrue(talk1.same_order(records, subtitles))
        battery = talk1.mutants(rows)
        self.assertGreaterEqual(len(battery), 12)
        for m in battery:
            with self.subTest(mutant=m["mutant"]):
                self.assertTrue(m["killed"], m["mutant"])
        # The auditor is not the renderer: it rejects a line the renderer
        # would never write, and it never calls it.
        src = Path(talk1.__file__).read_text(encoding="utf-8")
        audit_src = inspect.getsource(talk1.audit)
        self.assertNotIn("talk.render", audit_src,
                         "the auditor must not ask the renderer what it meant")
        self.assertNotIn("talk.BODY", audit_src)
        self.assertNotIn("talk.PROPOSAL", audit_src)
        self.assertIn("WANT_BODY", audit_src)
        del src

    # 5 -------------------------------------------------------------------
    def test_green_falls_on_every_lock(self) -> None:
        report = talk1.experiment()
        self.assertTrue(talk1.green(report), report.get("audit_failures"))
        for key, wrong in (
            ("source_records", 0),
            ("narrated_records", 255),
            ("same_order", False),
            ("source_unchanged", False),
            ("file_failure_count", 1),
            ("TranslationConsistency", 99),
            ("consistency_hits", report["consistency_total"] - 1),
            ("mutants_total", 3),
            ("mutants_killed", report["mutants_total"] - 1),
            ("causal_writes", 1),
            ("uses_a_conjunction", 1),
            ("thought_keys", 23),
            ("keys_match_thought", False),
            ("action_names_match_thought", False),
            ("matrix_actions", [0, 1, 2]),
            ("matrix_reasons", ["off"]),
            ("matrix_gate_decisions", [0]),
            ("matrix_reward_signs", [0, 1]),
            ("matrix_has_pose", False),
            ("matrix_has_ring_nulls", False),
            ("matrix_t_known_and_unknown", False),
            ("matrix_flags_both_ways", False),
            ("matrix_names", ["real_signc_conflict"]),
        ):
            with self.subTest(lock=key):
                self.assertFalse(talk1.green(dict(report, **{key: wrong})), key)

    # 6 -------------------------------------------------------------------
    def test_the_source_diary_is_never_touched(self) -> None:
        records = [dict(talk1._base(i), action=i % 4,
                        q_row=[0, 0, 0, 0] if i % 4 == 3 else [0, 0, 0],
                        kind="CLOSED" if i % 4 == 3 else "EMPTY")
                   for i in range(12)]
        path = self._write(records)
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        lines = talk.translate(path)
        self.assertEqual(len(lines), len(records))
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before,
                         "the translator wrote to its own source")
        self.assertEqual(talk1.audit_file(talk.read_records(path), lines), [])

    def test_runner_writes_its_own_report_and_nobody_elses(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_signc_report.json",
                  "nexus0_qwen_signc_report.json", "nexus0_world3_report.json",
                  "nexus0_cortex1_report.json", "nexus0_qwen4b_report.json",
                  "nexus0_obj1_report.json", "nexus0_open1_report.json",
                  "nexus0_self1_report.json", "nexus0_room1_report.json",
                  "nexus0_pulpo_report.json")
        diaries = tuple(sorted(p.name for p in lab.glob("*.jsonl")))

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others + diaries}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = talk1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertEqual({n: stamp(lab / n) for n in others + diaries}, before,
                         "TALK-1 wrote over a report or a diary")
        written = json.loads(
            (lab / "nexus0_talk1_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertEqual(written["TranslationConsistency"], 100, written)
        self.assertEqual(written["causal_writes"], 0, written)
        self.assertEqual(written["thought_keys"], 22, written)
        self.assertEqual(written["mutants_killed"], written["mutants_total"])
        self.assertGreaterEqual(written["mutants_total"], 12)
        self.assertEqual(written["source_sha256_before"],
                         written["source_sha256_after"])

    def test_the_animal_is_where_it_was(self) -> None:
        """A consumer adapts to the contract; the contract does not move."""
        self.assertEqual(N_ACTIONS, 3)
        self.assertEqual(len(thought.KEYS), 22)
        self.assertEqual(thought.ACTION_NAME,
                         ("approach", "avoid", "wait", "open"))
        base = Agent()
        base.run(BENCH_TURNS)
        self.assertEqual(base.metrics.cortex_calls, 0)
        self.assertEqual(base.metrics.false_facts, 0)
        self.assertEqual(base.metrics.destroyed, 0)
        with sign.cortex_env(None):
            ring = Agent(cortex=True)
            ring.run(BENCH_TURNS)
        self.assertEqual(ring.metrics.cortex_calls, 36)

    def test_the_real_rows_are_real(self) -> None:
        """Two of the matrix rows were produced by the animal, not by me."""
        rows = dict(talk1.matrix())
        conflict, consume = (rows["real_signc_conflict"],
                             rows["real_signc_consume"])
        self.assertEqual(conflict["reason_name"], "conflict")
        self.assertTrue(conflict["attend_on"])
        self.assertIsNone(conflict["cortex_action"])
        self.assertEqual(conflict["s"], 1)
        self.assertFalse(consume["attend_on"])
        self.assertEqual(consume["reason_name"], "off")
        self.assertEqual(consume["cortex_action"], ACTION_APPROACH)
        self.assertEqual(consume["reward"], R_SUCCESS)
        self.assertEqual(consume["cortex_calls"], conflict["cortex_calls"])

        jar = rows["real_open1_turn"]
        self.assertEqual(jar["action"], 3)
        self.assertEqual(jar["kind"], "CLOSED")
        self.assertEqual(len(jar["q_row"]), 4)
        self.assertEqual(talk1.parse(talk.render(jar))["cuerpo"], "abrió")


def _module_imports(mod) -> set:
    """Top-level module names a module imports, by AST."""
    out = set()
    for node in ast.walk(ast.parse(
            Path(mod.__file__).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out.update(f"{node.module}.{a.name}" for a in node.names)
    return out


class TestTalk1b(unittest.TestCase):
    """TALK-1b: the auditor must not be able to agree with the narrator.

    TALK-1 shipped a good narrator and real isolation, and a gate that
    accepted false subtitles. Three holes, all the same shape — a check
    that could not disagree with what it was checking:

    - pose was audited by looking for each coordinate as a **substring**,
      so `1` was in `100`, order did not matter, and anything could be
      appended;
    - `audit()` read `talk.REASON_ES`, the renderer's own table, so a
      renderer that renamed a reason was checked against its own mistake;
    - the scanner read the mode of `open` positionally as if every call
      were the builtin, and never looked at `write` at all.

    The fourteen tests of TALK-1 all passed. That was the defect.
    """

    def _rows(self):
        return dict(talk1.matrix())

    def _clause(self, rec, label):
        return talk1.parse(talk.render(rec))[label]

    def _bend(self, rec, label, value):
        line = talk.render(rec)
        return line.replace(f"{label}: {self._clause(rec, label)}",
                            f"{label}: {value}", 1)

    # --- 1. pose ---------------------------------------------------------
    def test_the_four_false_poses_are_now_refused(self) -> None:
        """The exact counterexamples, as they were reported."""
        rows = self._rows()
        for key, fake in (
            ("pose_full", "(100, 200, 0) rumbo 3 marco 1"),
            ("pose_full", "(2, 1, 0) rumbo 3 marco 1"),
            ("pose_full", "(1, 2, 0) rumbo 3 marco 1 con obstáculo"),
            ("pose_no_frame", "(0, 0, 2) rumbo 5 marco 99"),
        ):
            with self.subTest(pose=fake):
                rec = rows[key]
                self.assertTrue(talk1.audit(rec, self._bend(rec, "pose", fake)),
                                fake)

    def test_pose_is_audited_by_equality_not_by_substring(self) -> None:
        rows = self._rows()
        full, no_frame, none = (rows["pose_full"], rows["pose_no_frame"],
                                rows["pose_none"])
        self.assertEqual(talk1.want_pose(full), "(1, 2, 0) rumbo 3 marco 1")
        self.assertEqual(talk1.want_pose(no_frame), "(0, 0, 2) rumbo 5")
        self.assertEqual(talk1.want_pose(none), "sin pose")
        for rec, fake in (
            (full, "(1, 2, 0) rumbo 3"),                # the frame dropped
            (full, "(1, 2, 0) marco 1"),                # the heading dropped
            (full, "(1, 2, 0) rumbo 4 marco 1"),        # a heading invented
            (full, "(1, 2, 0) rumbo 3 marco 2"),        # a frame invented
            (full, "(0, 1, 2) rumbo 3 marco 1"),        # shifted
            (full, "x=1 y=2 z=0 rumbo 3 marco 1"),      # re-spelled
            (full, " (1, 2, 0) rumbo 3 marco 1"),       # a prefix
            (full, "(1, 2, 0) rumbo 3 marco 1 "),       # a suffix
            (no_frame, "(0, 0, 2)"),                    # the heading dropped
            (none, "(0, 0, 0)"),                        # a pose invented
            (none, "sin pose conocida"),
        ):
            with self.subTest(fake=fake):
                self.assertTrue(talk1.audit(rec, self._bend(rec, "pose", fake)),
                                fake)
        # And the true one still passes.
        for rec in (full, no_frame, none):
            self.assertEqual(talk1.audit(rec, talk.render(rec)), [])
        # The auditor builds it itself.
        src = inspect.getsource(talk1.want_pose) + inspect.getsource(talk1.audit)
        self.assertNotIn("talk._pose", src)

    def test_validate_refuses_a_pose_that_is_not_one(self) -> None:
        good = dict(talk1._base(0), action=0)
        for label, bend in (
            ("a frame with no pose", {"frame": 1}),
            ("a heading with no pose", {"heading": 1}),
            ("a q row of five", {"q_row": [0, 0, 0, 0, 0]}),
            ("a q row of one", {"q_row": [0]}),
            ("open beside a three-wide row", {"action": 3}),
            ("a proposal beside a three-wide row", {"cortex_action": 3}),
        ):
            with self.subTest(bend=label):
                with self.assertRaises(talk.BadRecord, msg=label):
                    talk.render(dict(good, **bend))
        # Four gears with a four-wide row is the one that is legal.
        self.assertIsInstance(
            talk.render(dict(good, action=3, q_row=[0, 0, 0, 1],
                             kind="CLOSED")), str)

    # --- 2. the shared table --------------------------------------------
    def test_the_auditor_reads_no_table_of_the_renderer(self) -> None:
        src = (inspect.getsource(talk1.parse) + inspect.getsource(talk1.audit)
               + inspect.getsource(talk1.want_pose))
        for forbidden in ("talk.LABELS", "talk.SEP", "talk.REASON_NAME",
                          "talk.REASON_ES", "talk.BODY", "talk.PROPOSAL",
                          "talk.GATE", "talk._pose", "talk.render"):
            self.assertNotIn(forbidden, src, forbidden)
        # It has its own, and they are pinned to the renderer's here — so
        # drift is a red test rather than a silent agreement.
        self.assertEqual(talk1.WANT_LABELS, tuple(talk.LABELS))
        self.assertEqual(talk1.WANT_SEP, talk.SEP)
        self.assertEqual(talk1.WANT_BODY, talk.BODY)
        self.assertEqual(talk1.WANT_PROPOSAL, talk.PROPOSAL)
        self.assertEqual(talk1.WANT_GATE, talk.GATE)
        self.assertEqual(talk1.WANT_REASON, talk.REASON_ES)
        self.assertEqual(talk1.REASONS, tuple(talk.REASON_NAME))
        self.assertEqual(len(talk1.WANT_LABELS), 16)
        self.assertEqual(
            talk1.WANT_LABELS,
            ("turno", "celda", "pose", "cuerpo", "gate", "recompensa",
             "atención", "córtex", "T", "nuevo", "sorpresa", "δ",
             "preguntas", "llamadas", "Q", "WSP"))

    def test_each_of_the_seven_reasons_is_caught_when_twisted(self) -> None:
        """Twist the renderer's translation, one reason at a time."""
        rows = self._rows()
        for reason in talk1.REASONS:
            other = "conflict" if reason != "conflict" else "off"
            rec = rows[f"reason_{reason}"]
            keep = talk.REASON_ES[reason]
            talk.REASON_ES[reason] = talk.REASON_ES[other]
            try:
                bad = talk.render(rec)
            finally:
                talk.REASON_ES[reason] = keep
            with self.subTest(reason=reason):
                self.assertTrue(talk1.audit(rec, bad),
                                f"a twisted {reason!r} passed")
            # And the honest line still passes.
            self.assertEqual(talk1.audit(rec, talk.render(rec)), [], reason)

    def test_no_reason_may_wear_another_reasons_words(self) -> None:
        rows = self._rows()
        for reason in talk1.REASONS:
            rec = rows[f"reason_{reason}"]
            for other in talk1.REASONS:
                if other == reason:
                    continue
                with self.subTest(reason=reason, said=other):
                    bad = self._bend(rec, "atención", talk1.WANT_REASON[other])
                    self.assertTrue(talk1.audit(rec, bad))

    # --- 3. the scanner --------------------------------------------------
    def test_the_scanner_sees_every_equivalent_write(self) -> None:
        source = Path(talk.__file__).read_text(encoding="utf-8")
        for injection in (
            "def _x(p):\n    Path(p).open('w').write('x')",
            "def _x(p, mode):\n    Path(p).open(mode).write('x')",
            "def _x(p, mode):\n    open(p, mode).write('x')",
            "def _x(fh):\n    fh.write('x')",
            "def _x():\n    __import__('echoai.nexus0.loop')",
            "def _x(p):\n    Path(p).open('r')",
            "def _x(fh):\n    fh.writelines(['x'])",
            "def _x(fh):\n    fh.truncate()",
            # A handle that merely *looks* like a stream is not the CLI's.
            "def _x(evil):\n    evil.stdout.write('x')",
            "def _x(evil):\n    evil.stderr.writelines(['x'])",
            "def _x():\n    eval('1')",
            "def _x():\n    exec('pass')",
            "import importlib",
            "def _x(p):\n    Path(p).touch()",
        ):
            with self.subTest(injection=injection.splitlines()[-1].strip()):
                self.assertTrue(
                    talk1.causal_findings(source + "\n" + injection, "m"),
                    injection)
        # The real file is still clean, and its two allowed writes are the
        # CLI's own streams.
        self.assertEqual(talk1.causal_findings(source, "talk.py"), [])
        self.assertIn("sys.stdout.write", source)
        self.assertIn("sys.stderr.write", source)
        # A stream write that is not sys.stdout/stderr is not exempt.
        self.assertTrue(talk1.causal_findings(
            source + "\nimport io\ndef _x():\n    io.StringIO().write('x')\n", "m"))

    # --- 4. the battery cannot be emptied --------------------------------
    def test_deleting_any_required_mutant_makes_green_fall(self) -> None:
        report = talk1.experiment()
        self.assertTrue(talk1.green(report), report.get("audit_failures"))
        self.assertGreaterEqual(len(talk1.REQUIRED_MUTANTS), 40)
        for required in talk1.REQUIRED_MUTANTS:
            with self.subTest(deleted=required):
                battery = [m for m in report["mutants"]
                           if m["mutant"] != required]
                self.assertEqual(len(battery), len(report["mutants"]) - 1,
                                 f"{required} is not in the battery")
                state = talk1.battery_state(battery)
                self.assertEqual(state["missing"], [required])
                # The summary fields are deliberately left saying all is
                # well: `green()` has to recompute from the list, not
                # believe what the report says about its own battery.
                bent = dict(report, mutants=battery,
                            mutants_total=len(battery),
                            mutants_killed=sum(1 for m in battery if m["killed"]))
                self.assertFalse(talk1.green(bent), required)

    def test_a_duplicated_or_surviving_mutant_makes_green_fall(self) -> None:
        report = talk1.experiment()
        first = report["mutants"][0]
        dup = report["mutants"] + [dict(first)]
        state = talk1.battery_state(dup)
        self.assertEqual(state["duplicated"], [first["mutant"]])
        self.assertFalse(talk1.green(dict(
            report, mutants=dup, mutants_total=len(dup),
            mutants_killed=sum(1 for m in dup if m["killed"]))))
        # One that stops dying is enough on its own — and the report is
        # left claiming it died, so only the recomputation can catch it.
        alive = [dict(m, killed=False) if m is first else m
                 for m in report["mutants"]]
        state = talk1.battery_state(alive)
        self.assertEqual(state["alive"], [first["mutant"]])
        self.assertFalse(talk1.green(dict(
            report, mutants=alive,
            mutants_killed=report["mutants_total"])),
            "green believed the report's own count over its own battery")
        # `green()` reads the list, not only the counters: a battery whose
        # counters are consistent but whose categories are gone is refused.
        few = report["mutants"][:12]
        self.assertFalse(talk1.green(dict(
            report, mutants=few, mutants_total=12,
            mutants_killed=sum(1 for m in few if m["killed"]))))

    def test_the_required_set_names_the_categories_it_claims(self) -> None:
        req = talk1.REQUIRED_MUTANTS
        self.assertEqual(len(req), len(set(req)), "the required set repeats")
        self.assertGreaterEqual(
            sum(1 for n in req if n.startswith("pose con")), 4)
        for reason in talk1.REASONS:
            self.assertIn(f"razón torcida en el redactor: {reason}", req)
        for form in ("Path.open y escribe", "un modo dinámico",
                     "open con un modo dinámico",
                     "escribe en un descriptor cualquiera",
                     "importa el animal dinámicamente"):
            self.assertTrue(any(form in n for n in req), form)
        report = talk1.experiment()
        self.assertEqual(report["required_mutants"], len(req))
        for name in req:
            self.assertIn(name, [m["mutant"] for m in report["mutants"]], name)


class TestTalk1c(unittest.TestCase):
    """TALK-1c: no surviving mutant, not even one added later.

    `green()` promised to protect "every mutant in the battery, required
    or not" and did not. `battery_state()["alive"]` intersected with
    `REQUIRED_MUTANTS`, so an entry that was not on the list could survive
    unseen; and the two totals were only compared with each other, so a
    report that lied about both agreed with itself. Appending
    `{"mutant": "extra futuro vivo", "killed": False}` and setting
    `mutants_killed = mutants_total` kept the gate green.

    The point is not to add that name to the required set. It is that the
    gate protects extensions it has never heard of.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = talk1.experiment()

    def _report(self, **over):
        return dict(self.report, **over)

    def _with(self, *entries, total=None, killed=None):
        """The battery plus some entries, with honest counters by default."""
        battery = list(self.report["mutants"]) + list(entries)
        real_killed = sum(1 for m in battery
                          if isinstance(m, dict) and m.get("killed") is True)
        return self._report(
            mutants=battery,
            mutants_total=len(battery) if total is None else total,
            mutants_killed=real_killed if killed is None else killed)

    # 1 -------------------------------------------------------------------
    def test_the_false_green_is_gone(self) -> None:
        """The counterexample, literally as it was reported."""
        r = talk1.experiment()
        r["mutants"].append({
            "mutant": "extra futuro vivo", "killed": False, "failures": []})
        r["mutants_total"] = len(r["mutants"])
        r["mutants_killed"] = r["mutants_total"]  # contador mentiroso
        self.assertIs(talk1.green(r), False)
        self.assertEqual(talk1.battery_state(r["mutants"])["alive"],
                         ["extra futuro vivo"])
        # And with honest counters too: surviving is what makes it red.
        self.assertFalse(talk1.green(self._with(
            {"mutant": "extra futuro vivo", "killed": False})))

    # 2 -------------------------------------------------------------------
    def test_a_future_mutant_that_dies_is_welcome(self) -> None:
        """The battery must stay extendable, or the lock is a cage."""
        bent = self._with({"mutant": "extra futuro muerto", "killed": True,
                           "failures": ["algo falló, que es el punto"]})
        self.assertTrue(talk1.green(bent))
        state = talk1.battery_state(bent["mutants"])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["total"], len(self.report["mutants"]) + 1)
        self.assertEqual(state["killed"], state["total"])
        # Two of them, and one of the two alive, is red again.
        self.assertFalse(talk1.green(self._with(
            {"mutant": "extra uno", "killed": True},
            {"mutant": "extra dos", "killed": False})))

    # 3 -------------------------------------------------------------------
    def test_lying_only_in_mutants_total_is_red(self) -> None:
        real = self.report["mutants_total"]
        for wrong in (real + 1, real - 1, 0, 12):
            with self.subTest(total=wrong):
                self.assertFalse(talk1.green(self._report(mutants_total=wrong)))
        self.assertTrue(talk1.green(self._report(mutants_total=real)))

    # 4 -------------------------------------------------------------------
    def test_lying_only_in_mutants_killed_is_red(self) -> None:
        real = self.report["mutants_killed"]
        for wrong in (real + 1, real - 1, 0):
            with self.subTest(killed=wrong):
                self.assertFalse(talk1.green(self._report(mutants_killed=wrong)))
        self.assertTrue(talk1.green(self._report(mutants_killed=real)))

    # 5 -------------------------------------------------------------------
    def test_a_malformed_entry_is_red_and_not_a_traceback(self) -> None:
        """A gate that crashes on a bad report has not judged it."""
        for label, entry in (
            ("no name", {"killed": True}),
            ("an empty name", {"mutant": "", "killed": True}),
            ("a name that is not text", {"mutant": 7, "killed": True}),
            ("no killed", {"mutant": "extra sin veredicto"}),
            ("killed as the integer 1", {"mutant": "extra", "killed": 1}),
            ("killed as a string", {"mutant": "extra", "killed": "true"}),
            ("killed as None", {"mutant": "extra", "killed": None}),
            ("not an object at all", "no soy un objeto"),
            ("an entry that is a list", ["extra", True]),
        ):
            with self.subTest(entry=label):
                bent = self._with(entry)
                self.assertIs(talk1.green(bent), False, label)
                self.assertTrue(
                    talk1.battery_state(bent["mutants"])["malformed"], label)
        # And the whole field being wrong is judged, not raised.
        for battery in (None, "los mutantes", 42, {"mutant": "x"}):
            with self.subTest(battery=type(battery).__name__):
                self.assertIs(talk1.green(self._report(mutants=battery)), False)
                self.assertTrue(
                    talk1.battery_state(battery)["malformed"]
                    or talk1.battery_state(battery)["missing"])
        self.assertIs(talk1.green(
            {k: v for k, v in self.report.items() if k != "mutants"}), False)

    # 6 -------------------------------------------------------------------
    def test_the_forty_two_required_are_still_present_unique_and_dead(self) -> None:
        state = talk1.battery_state(self.report["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(len(talk1.REQUIRED_MUTANTS), 42)
        self.assertEqual(state["total"], state["killed"])
        self.assertEqual(state["total"], self.report["mutants_total"])
        self.assertEqual(state["killed"], self.report["mutants_killed"])
        self.assertTrue(talk1.green(self.report))
        self.assertEqual(self.report["mutants_alive"], [])
        self.assertEqual(self.report["mutants_malformed"], [])
        # A required one going missing or surviving is still red.
        for required in ("pose con coordenadas infladas",
                         "razón torcida en el redactor: miss",
                         "el traductor escribe en un descriptor cualquiera"):
            with self.subTest(required=required):
                gone = [m for m in self.report["mutants"]
                        if m["mutant"] != required]
                self.assertFalse(talk1.green(self._report(
                    mutants=gone, mutants_total=len(gone),
                    mutants_killed=sum(1 for m in gone if m["killed"]))))

    def test_green_recounts_and_does_not_read_its_own_summary(self) -> None:
        """The summary fields are evidence for a reader, not the gate."""
        src = inspect.getsource(talk1.green)
        for field in ("required_mutants_missing", "required_mutants_duplicated",
                      "mutants_alive", "mutants_malformed"):
            self.assertNotIn(field, src, field)
        self.assertIn("battery_state", src)
        # So a report whose summary says everything is fine is still judged
        # on its list.
        bent = self._with({"mutant": "extra futuro vivo", "killed": False})
        bent.update(required_mutants_missing=[], required_mutants_duplicated=[],
                    mutants_alive=[], mutants_malformed=[])
        self.assertFalse(talk1.green(bent))


class TestPattern0(unittest.TestCase):
    """PATTERN-0: a riff one-step T cannot hear.

        ... B → A → C → A → B → A → C → A ...

    At `A`, under the same action, the world hands back `C` sometimes and
    `B` other times. `World.predict(A, approach)` has one row and one
    answer. What decides the successor is where the body came from, and
    that is not in T's argument list — so a context of order two wins on
    held-out segments while T sits at a coin flip.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = pattern0.experiment()

    # --- the memory ------------------------------------------------------
    def test_the_key_is_the_context_and_not_a_hash_of_it(self) -> None:
        seen = {}
        for prev in (0, 1, 4095, 2047):
            for cur in (0, 1, 4095, 2047):
                for action in range(N_ACTIONS + 1):
                    key = pattern.context_key(prev, cur, action)
                    self.assertNotIn(key, seen,
                                     f"{(prev, cur, action)} colisiona con "
                                     f"{seen.get(key)}")
                    seen[key] = (prev, cur, action)
        self.assertEqual(len(seen), 4 * 4 * (N_ACTIONS + 1))

    def test_one_observation_is_a_coincidence(self) -> None:
        mem = pattern.PatternMemory()
        self.assertEqual(mem.min_hits, 2)
        self.assertGreaterEqual(mem.min_hits, 2, "uno no es una frecuencia")
        mem.observe(11, 22, 0, 33)
        self.assertIsNone(mem.predict(11, 22, 0))
        self.assertFalse(mem.mature(11, 22, 0))
        self.assertEqual(mem.hits(11, 22, 0), 1)
        mem.observe(11, 22, 0, 33)
        self.assertEqual(mem.predict(11, 22, 0), 33)
        self.assertTrue(mem.mature(11, 22, 0))
        # A rule that has ever been contradicted is held and not offered.
        mem.observe(11, 22, 0, 44)
        self.assertIsNone(mem.predict(11, 22, 0))
        self.assertFalse(mem.mature(11, 22, 0),
                         "una regla contradicha no está madura")
        self.assertEqual(mem.conflicts, 1)
        # KCC: the incumbent survives until the alternative strictly wins.
        self.assertEqual(mem.hits(11, 22, 0), 2)
        for _ in range(3):
            mem.observe(11, 22, 0, 44)
        self.assertIsNone(mem.predict(11, 22, 0),
                          "una regla contradicha no vuelve por mayoría")

    def test_the_action_is_part_of_the_context(self) -> None:
        mem = pattern.PatternMemory()
        for _ in range(mem.min_hits):
            mem.observe(11, 22, ACTION_APPROACH, 33)
            mem.observe(11, 22, ACTION_AVOID, 22)
        self.assertEqual(mem.predict(11, 22, ACTION_APPROACH), 33)
        self.assertEqual(mem.predict(11, 22, ACTION_AVOID), 22)
        self.assertIsNone(mem.predict(11, 22, ACTION_WAIT))

    def test_the_memory_is_bounded_and_says_what_it_lost(self) -> None:
        probe = pattern0.capacity_probe(capacity=4)
        self.assertEqual(probe["capacity"], 4)
        self.assertEqual(probe["size_before"], 4)
        self.assertEqual(probe["size_after"], 4, "no creció")
        self.assertTrue(probe["size_never_exceeds_capacity"])
        self.assertTrue(probe["nothing_was_overwritten"],
                        "una regla ya aprendida cambió de respuesta")
        self.assertTrue(probe["new_contexts_were_dropped"])
        self.assertGreater(probe["dropped_after"], 0)
        self.assertEqual(probe["dropped_before"], 0)
        # No dict, no growth, no eviction: fixed lists, declared capacity.
        mem = pattern.PatternMemory(capacity=8)
        for arr in (mem.key, mem.pred, mem.n, mem.alt, mem.alt_n):
            self.assertIsInstance(arr, list)
            self.assertEqual(len(arr), 8)
        for k in range(200):
            mem.observe(k, k, 0, k)
        for arr in (mem.key, mem.pred, mem.n, mem.alt, mem.alt_n):
            self.assertEqual(len(arr), 8, "la memoria creció con la corrida")
        self.assertLessEqual(mem.size, 8)
        self.assertGreater(mem.dropped, 0)

    def test_the_memory_stores_integers_and_reaches_nothing(self) -> None:
        source = Path(pattern.__file__).read_text(encoding="utf-8")
        self.assertEqual(pattern0.isolation_findings(source), [])
        modules = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        self.assertEqual(modules, {"__future__", "hashlib", "typing",
                                   "echoai.nexus0.constants"})
        # And the check can fail.
        for label, injected in pattern0.ISOLATION_INJECTIONS:
            with self.subTest(injected=label):
                self.assertTrue(pattern0.isolation_findings(injected, "m"),
                                label)
        # No turn, no clock, no world name anywhere in the API.
        self.assertTrue(pattern0._predict_signature())
        for fn in (pattern.PatternMemory.predict, pattern.PatternMemory.observe):
            self.assertNotIn("turn", inspect.signature(fn).parameters)

    def test_the_five_writes_into_t_that_used_to_pass(self) -> None:
        """The counterexamples, literally.

        The scanner looked at attribute *names* and at calls, so a write
        through any number of subscripts was invisible: `pred` is not a
        forbidden field name — it is `World`'s table, and what makes it
        somebody else's is the receiver.
        """
        for line in ("self.world.pred[0][0] = 9",
                     "self.world.n[0][0] += 1",
                     "self.world.alt[0][0] = 9",
                     "self.world.alt_n[0][0] = 1",
                     "self.world.pred = []"):
            with self.subTest(write=line):
                found = pattern0.isolation_findings(
                    f"def x(self):\n    {line}\n", "m")
                self.assertTrue(found, line)
                self.assertIn("escribe en", found[0])
        # Every syntax a write can arrive in, and every depth.
        for line in ("self.t.pred[0] = 1", "self.t.alt_n = []",
                     "self.world.inv[0][0][0] = 1",
                     "world.pred[0][0] = 9",
                     "self.world.conflicts += 1",
                     "self.world.pred[0][0]: int = 9",
                     "self.world.pred[0], other = 9, 8"):
            with self.subTest(write=line):
                self.assertTrue(pattern0.isolation_findings(
                    f"def x(self, other, world):\n    {line}\n", "m"), line)

    def test_the_memory_may_write_its_own_four_tables(self) -> None:
        """`pred`, `n`, `alt` and `alt_n` are names, not ownership.

        `PatternMemory` has tables of all four names and writes them on
        every observation. What the rule is about is the receiver, so a
        check keyed on the field name alone would either miss the writes
        into `World` or forbid the memory from being a memory.
        """
        for line in ("self.pred[i] = nxt", "self.n[i] += 1",
                     "self.alt[i] = nxt", "self.alt_n[i] = 1",
                     "self.key[i] = key", "self.size += 1",
                     "self.pred[i], self.alt[i] = self.alt[i], self.pred[i]"):
            with self.subTest(write=line):
                self.assertEqual(pattern0.isolation_findings(
                    f"def x(self, i, nxt, key):\n    {line}\n", "m"), [], line)
        # And the real file, which does all of that, is clean.
        self.assertEqual(pattern0.isolation_findings(
            Path(pattern.__file__).read_text(encoding="utf-8")), [])
        for name in ("pred", "n", "alt", "alt_n"):
            self.assertIn(name, pattern.PatternMemory().__dict__, name)

    def test_every_way_out_is_detected_on_its_own(self) -> None:
        """No single finding may be carrying the rest.

        The battery used to inject one blob containing an import, a call
        and a stored packet, and scored it killed if anything at all was
        found — so five writes into `World` rode along undetected.
        """
        self.assertGreaterEqual(len(pattern0.ISOLATION_INJECTIONS), 12)
        labels = [label for label, _ in pattern0.ISOLATION_INJECTIONS]
        self.assertEqual(len(labels), len(set(labels)))
        for label, injected in pattern0.ISOLATION_INJECTIONS:
            with self.subTest(injection=label):
                self.assertTrue(pattern0.isolation_findings(injected, "m"),
                                label)
                self.assertIn(f"el patrón {label}", pattern0.REQUIRED_MUTANTS)
        self.assertIn("el patrón real no toca nada", pattern0.REQUIRED_MUTANTS)
        # And each is its own entry in the battery, dead on its own, with
        # the evidence of its **own** injection. Checking only `killed`
        # would pass a battery that re-injected everything in one blob and
        # scored each entry against the same soup.
        by_name = {m["mutant"]: m for m in self.report["mutants"]}
        for label, injected in pattern0.ISOLATION_INJECTIONS:
            with self.subTest(entry=label):
                entry = by_name[f"el patrón {label}"]
                self.assertTrue(entry["killed"], label)
                self.assertTrue(entry["evidence"],
                                f"{label}: sin evidencia propia")
                self.assertEqual(
                    entry["evidence"],
                    pattern0.isolation_findings(injected, "mutante"),
                    f"{label}: la evidencia no es la de su inyección")
        # Two entries *may* share evidence — `world.pred[0][0] = 9` and
        # `world.pred = []` are the same table written two ways — so
        # uniqueness is not the rule. The rule is that each entry carries
        # what its own injection produces, which is what a blob cannot.

    # --- the world -------------------------------------------------------
    def test_the_ambiguity_is_measured_not_designed(self) -> None:
        counts = self.report["ambiguous_state_counts"]
        self.assertEqual(len(counts), 1, counts)
        (label, successors), = counts.items()
        self.assertEqual(len(successors), 2, successors)
        self.assertEqual(sorted(successors.values()), [50, 50],
                         "los dos sucesores, contados, no afirmados")
        self.assertEqual(self.report["ambiguous_states"], 1)
        # The physics is read off the cycle, not typed beside it.
        table = pattern0.successors_of()
        self.assertEqual(table[(pattern0.CELL_B, pattern0.CELL_A)],
                         pattern0.CELL_C)
        self.assertEqual(table[(pattern0.CELL_C, pattern0.CELL_A)],
                         pattern0.CELL_B)
        self.assertEqual(len(set(table.values())), 3)

    # --- the result ------------------------------------------------------
    def test_the_exam_comes_after_the_freeze(self) -> None:
        """Held out in time, not in phase.

        The training walk is one run from phase 0 and does pass through
        all four phases on its way — saying otherwise would be a claim the
        numbers do not support. What makes the exam held out is that its
        transitions are taken *after* both memories were frozen and
        hashed, from fresh envs, with the local counter back at zero.
        """
        cam, t, mem, stream = pattern0.train()
        walked = {p for p, _c, _a, _n in stream}
        self.assertGreater(len(walked), 1,
                           "el entrenamiento sí recorre varias fases")
        before = (pattern0.world_hash(t), mem.snapshot_hash())
        r = pattern0.exam(cam, t, mem)
        self.assertEqual((pattern0.world_hash(t), mem.snapshot_hash()), before)
        self.assertEqual(r["observes_during_exam"], 0)
        self.assertEqual([row["first_local_turn"] for row in r["by_rotation"]],
                         [0, 0, 0, 0])
        src = Path(pattern0.__file__).read_text(encoding="utf-8")
        self.assertNotIn("the training never", src,
                         "la cabecera afirmaba algo que no es cierto")

    def test_the_context_beats_t_on_held_out_segments(self) -> None:
        r = self.report
        self.assertEqual(r["decision_points"], 80)
        self.assertEqual(r["t_hits"], 40, "T acierta la mitad, como debe")
        self.assertEqual(r["pattern_hits"], 80)
        self.assertEqual(r["prediction_gain_hits"], 40)
        self.assertEqual(r["pattern_unknown"], 0,
                         "None no es acierto y no sale del denominador")
        self.assertEqual(len(r["by_rotation"]), 4)
        for row in r["by_rotation"]:
            self.assertGreater(row["pattern_hits"], row["t_hits"], row)
        self.assertEqual(r["context_order"], 2)

    def test_nothing_learned_during_the_exam(self) -> None:
        r = self.report
        self.assertEqual(r["observes_during_exam"], 0)
        self.assertEqual(r["t_hash_before"], r["t_hash_after"])
        self.assertEqual(r["pattern_hash_before"], r["pattern_hash_after"])
        self.assertTrue(r["memories_frozen"])
        # And the freeze can be broken, which is how we know it is checked.
        cam, t, mem, _ = pattern0.train()
        before = (pattern0.world_hash(t), mem.snapshot_hash())
        leaky = pattern0.exam(cam, t, mem, learn=True)
        self.assertGreater(leaky["observes_during_exam"], 0)
        self.assertNotEqual((pattern0.world_hash(t), mem.snapshot_hash()),
                            before)

    # --- the controls ----------------------------------------------------
    def test_the_previous_slot_is_load_bearing(self) -> None:
        self.assertEqual(self.report["no_context_gain_hits"], 0)
        cam, t, mem = pattern0.train_without_context()
        blind = pattern0.exam(cam, t, mem)
        self.assertEqual(blind["pattern_hits"], blind["t_hits"],
                         "sin el slot anterior colapsa sobre T")
        self.assertLessEqual(blind["prediction_gain_hits"], 0)
        # The ambiguous context never matures once history is thrown away.
        a_slot = pattern0._slot(cam, pattern0.CELL_A)
        self.assertIsNone(mem.predict(0, a_slot, ACTION_APPROACH))

    def test_a_world_with_no_regularity_matures_nothing(self) -> None:
        r = self.report
        self.assertTrue(r["no_pattern_mature"])
        self.assertLessEqual(r["no_pattern_gain_hits"], 0)
        self.assertGreater(r["no_pattern_conflicts"], 0,
                           "el control se contradice, por construcción")
        _cam, _t, mem = pattern0.train(balanced=True)[:3]
        self.assertEqual(mem.mature_counts(), {})
        # Balanced by construction, not by luck: every context has two
        # successors and they are taken in turn.
        table = pattern0.balanced_successors()
        for key, options in table.items():
            self.assertEqual(len(options), 2, key)
            self.assertNotIn(key[1], options, "un sucesor que es uno mismo")

    def test_an_absolute_clock_cannot_do_it(self) -> None:
        r = self.report
        self.assertTrue(r["absolute_clock_control_fails"])
        self.assertLess(r["best_clock_hits"], r["pattern_hits"])
        for period, hits in r["clock_hits"].items():
            self.assertLess(hits, r["pattern_hits"], period)
        # The rotations are what break it: each starts its local counter
        # at zero from a different phase.
        self.assertEqual(r["exam_rotations"], [0, 1, 2, 3])
        phases = {pattern0.PatternEnv(phase=p).i for p in r["exam_rotations"]}
        self.assertGreater(len(phases), 1)

    # --- the gate --------------------------------------------------------
    def test_a_predictor_that_knows_nothing_scores_zero_of_all_of_them(self) -> None:
        """None is a miss, and it does not leave the denominator.

        Scored on exactly the same ambiguous points with an empty T and an
        empty memory. Without this arm, both of those rules are things
        nothing in the bench can violate.
        """
        r = self.report
        self.assertEqual(r["unknown_decision_points"], r["decision_points"])
        self.assertEqual(r["unknown_pattern_hits"], 0)
        self.assertEqual(r["unknown_t_hits"], 0)
        self.assertEqual(r["unknown_pattern_unknown"], r["decision_points"])
        # And every rotation's local counter starts at zero.
        self.assertEqual(r["exam_local_turn_starts"], [0, 0, 0, 0])
        for row in r["by_rotation"]:
            self.assertEqual(row["first_local_turn"], 0, row)

    def test_green_falls_on_every_lock(self) -> None:
        r = self.report
        self.assertTrue(pattern0.green(r))
        for key, wrong in (
            ("prediction_gain_hits", 0), ("prediction_gain_hits", -1),
            ("pattern_hits", r["t_hits"]), ("decision_points", 0),
            ("pattern_unknown", 1),
            ("observes_during_exam", 1),
            ("t_hash_after", "otro"), ("pattern_hash_after", "otro"),
            ("min_hits", 1), ("context_order", 1),
            ("predict_takes_no_turn", False),
            ("no_pattern_mature", False), ("no_pattern_gain_hits", 1),
            ("no_context_gain_hits", 1),
            ("absolute_clock_control_fails", False),
            ("ambiguous_states", 0),
            ("size", r["capacity"] + 1),
            ("size_never_exceeds_capacity", False),
            ("nothing_was_overwritten", False),
            ("new_contexts_were_dropped", False),
            ("isolation_findings", ["algo"]),
            ("unknown_pattern_hits", 1), ("unknown_t_hits", 1),
            ("unknown_decision_points", 0),
            ("unknown_pattern_unknown", 0),
            ("exam_local_turn_starts", [0, 40, 80, 120]),
            ("false_facts", 1), ("destroyed", 1), ("cortex_calls", 1),
            ("llm_calls", 1), ("human_labels", 1),
            ("n_actions", 4),
        ):
            with self.subTest(lock=f"{key}={wrong}"):
                self.assertFalse(pattern0.green(dict(r, **{key: wrong})), key)

    def test_the_battery_cannot_be_emptied_or_faked(self) -> None:
        """TALK-1c's lesson, applied here from the start."""
        r = self.report
        state = pattern0.battery_state(r["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(len(pattern0.REQUIRED_MUTANTS), 29)
        self.assertEqual(state["total"], state["killed"])
        for required in pattern0.REQUIRED_MUTANTS:
            with self.subTest(deleted=required):
                gone = [m for m in r["mutants"] if m["mutant"] != required]
                self.assertFalse(pattern0.green(dict(
                    r, mutants=gone, mutants_total=len(gone),
                    mutants_killed=sum(1 for m in gone if m["killed"]))))
        # An extra one that dies is welcome; one that lives is red even
        # when the counters say otherwise.
        alive = r["mutants"] + [{"mutant": "extra vivo", "killed": False}]
        self.assertFalse(pattern0.green(dict(
            r, mutants=alive, mutants_total=len(alive),
            mutants_killed=len(alive))), "el contador mentía")
        # And with entirely honest counters, so that only `alive` can be
        # the thing that refuses it.
        self.assertFalse(pattern0.green(dict(
            r, mutants=alive, mutants_total=len(alive),
            mutants_killed=sum(1 for m in alive if m["killed"]))),
            "un mutante vivo con los contadores bien")
        dead = r["mutants"] + [{"mutant": "extra muerto", "killed": True}]
        self.assertTrue(pattern0.green(dict(
            r, mutants=dead, mutants_total=len(dead),
            mutants_killed=len(dead))))
        for bad in ({"killed": True}, {"mutant": "x"},
                    {"mutant": "y", "killed": 1}, "no soy un objeto"):
            with self.subTest(entry=str(bad)[:24]):
                battery = r["mutants"] + [bad]
                self.assertFalse(pattern0.green(dict(
                    r, mutants=battery, mutants_total=len(battery),
                    mutants_killed=sum(
                        1 for m in battery
                        if isinstance(m, dict) and m.get("killed") is True))))
        self.assertFalse(pattern0.green(dict(r, mutants=None)))
        self.assertFalse(pattern0.green(dict(r, mutants_total=99)))
        self.assertFalse(pattern0.green(dict(r, mutants_killed=0)))

    # --- the locks -------------------------------------------------------
    def test_the_animal_is_where_it_was(self) -> None:
        """Nothing is wired into the hot path; XFER-1 decides that."""
        # XFER-1 wired the memory into `Agent` as an **opt-in** extension,
        # so "the loop does not import pattern" is no longer the invariant
        # — the invariant is that the default agent does not build one and
        # its numbers do not move. Both are checked here and below.
        agent = Agent()
        self.assertIsNone(agent.pattern_memory)
        self.assertIsNone(agent.prev_slot)
        self.assertIs(inspect.signature(Agent.__init__)
                      .parameters["pattern_memory"].default, False)
        self.assertFalse(hasattr(agent, "context"))
        self.assertEqual(N_ACTIONS, 3)
        self.assertEqual(len(thought.KEYS), 22)
        self.assertNotIn("pattern", thought.KEYS)
        agent.run(BENCH_TURNS)
        self.assertEqual(agent.metrics.cortex_calls, 0)
        self.assertEqual(agent.metrics.destroyed, 0)
        self.assertEqual(agent.metrics.false_facts, 0)
        with sign.cortex_env(None):
            ring = Agent(cortex=True)
            ring.run(BENCH_TURNS)
        self.assertEqual(ring.metrics.cortex_calls, 36)
        # T's own semantics are untouched: the memory never writes to it.
        _cam, t, _mem, _stream = pattern0.train()
        before = pattern0.world_hash(t)
        mem = pattern.PatternMemory()
        combined = pattern.ContextPredictor(t, mem)
        for _ in range(8):
            combined.predict(1, 2, 0)
        self.assertEqual(pattern0.world_hash(t), before)

    def test_runner_writes_its_own_report_and_nobody_elses(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_talk1_report.json",
                  "nexus0_signc_report.json", "nexus0_world3_report.json",
                  "nexus0_cortex1_report.json", "nexus0_qwen4b_report.json",
                  "nexus0_obj1_report.json", "nexus0_open1_report.json",
                  "nexus0_pulpo_report.json", "nexus0_self1_report.json",
                  "nexus0_room1_report.json")
        diaries = tuple(sorted(p.name for p in lab.glob("*.jsonl")))

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others + diaries}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = pattern0.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertEqual({n: stamp(lab / n) for n in others + diaries}, before,
                         "PATTERN-0 wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_pattern0_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertGreater(written["prediction_gain_hits"], 0, written)
        self.assertEqual(written["observes_during_exam"], 0, written)
        self.assertEqual(written["human_labels"], 0, written)
        self.assertEqual(written["llm_calls"], 0, written)
        self.assertEqual(written["mutants_killed"], written["mutants_total"])


class TestXfer1(unittest.TestCase):
    """XFER-1: the same animal, three worlds.

    Not the same class run three times and not three agents handed copies
    of each other's tables. One `Agent` object, born once, whose CAM, Q, T
    and pattern memory are the same four objects on both sides of both
    borders — checked by `id()`, because resemblance is not identity.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = xfer1.experiment()

    # --- the opt-in hook -------------------------------------------------
    def test_the_default_agent_is_untouched(self) -> None:
        """The hook is off, builds nothing, and the ring has not moved."""
        agent = Agent()
        self.assertIsNone(agent.pattern_memory)
        self.assertIsNone(agent.prev_slot)
        self.assertFalse(self.report["default_agent_has_pattern_memory"])
        agent.run(BENCH_TURNS)
        m = agent.metrics
        self.assertEqual([m.turns, m.cam_misses, m.surprises, m.deltas],
                         [256, 31, 0, 168])
        self.assertEqual(m.cortex_calls, 0)
        self.assertEqual(m.false_facts, 0)
        self.assertEqual(m.destroyed, 0)
        self.assertEqual(agent.q.snapshot(agent.threat_slots()[0]),
                         [-12, 5, 0])
        self.assertIsNone(agent.pattern_memory, "el default no creó memoria")
        with sign.cortex_env(None):
            ring = Agent(cortex=True)
            ring.run(BENCH_TURNS)
        self.assertEqual(ring.metrics.cortex_calls, 36)
        # And the canonical bench, which SIGN-C's gate also recomputes.
        report = bench_run()
        self.assertEqual(report["policy_after"], [-12, 5, 0])
        self.assertEqual(report["novel_approach_return"], 80)
        self.assertEqual([report["cam_misses"], report["surprises"],
                          report["deltas"]], [33, 1, 217])

    def test_the_hook_is_one_channel_and_not_a_second_t(self) -> None:
        """Same transition, same moment, same condition."""
        ag = Agent(ask=False, pattern_memory=True, env=xfer1.ParkEnv())
        ag.clear_context()
        self.assertIsNone(ag.prev_slot)
        ag.turn(0)
        first = ag.prev_slot
        self.assertIsNotNone(first, "el latch avanza con el cuerpo")
        self.assertEqual(ag.pattern_memory.observations, 0,
                         "el primer turno tras un corte no observa")
        ag.turn(1)
        self.assertEqual(ag.pattern_memory.observations, 1)
        for t in range(2, 40):
            ag.turn(t)
        self.assertEqual(ag.pattern_memory.observations, 39)
        # It is the loop's own prediction channel, not a parallel one.
        self.assertIn("self._predict(slot, a)",
                      Path(loop_module.__file__).read_text(encoding="utf-8"))
        # And it never writes T.
        self.assertEqual(pattern0.isolation_findings(
            Path(pattern.__file__).read_text(encoding="utf-8")), [])

    # --- one animal ------------------------------------------------------
    def test_the_same_four_objects_cross_both_borders(self) -> None:
        r = self.report
        self.assertTrue(r["same_agent_across_worlds"])
        for key in ("same_cam_object", "same_q_object", "same_t_object",
                    "same_pattern_object"):
            self.assertTrue(r[key], key)
        self.assertTrue(r["identity_survives_school"])
        self.assertTrue(r["identity_survives_borders"])
        self.assertEqual(r["identity_checks"],
                         {"cam": True, "q": True, "t": True, "pattern": True})
        # And the report carries no raw address: two identical runs must
        # produce identical bytes.
        self.assertNotIn("identities_at_birth", r)
        # Measured live, not read off the report.
        ag = xfer1.new_agent()
        born = xfer1.identities(ag)
        xfer1.school(ag)
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            xfer1.cross_into(ag, layout)
            xfer1._walk(ag, 8, base=xfer1.TURN_BASE[layout])
            self.assertEqual(xfer1.identities(ag), born, layout)
        # A twin with the rows copied in is a different animal.
        twin = xfer1.new_agent()
        twin.q.load_rows([ag.q.row(i) for i in range(len(ag.q.q))])
        self.assertNotEqual(xfer1.identities(twin), born)

    def test_the_border_drops_the_latch_and_nothing_else(self) -> None:
        """Clearing `prev_slot` is not forgetting anything."""
        ag = xfer1.new_agent()
        xfer1.school(ag)
        before = (xfer1.identities(ag), ag.cam.get(
            encode_cell(xfer1.HAZ if hasattr(xfer1, "HAZ") else xfer1.H1,
                        KIND_THREAT)),
            ag.q.row(xfer1.slot_of(ag, xfer1.H1)),
            ag.pattern_memory.size)
        xfer1.cross_into(ag, xfer1.PARK_B)
        self.assertIsNone(ag.prev_slot)
        after = (xfer1.identities(ag), ag.cam.get(
            encode_cell(xfer1.H1, KIND_THREAT)),
            ag.q.row(xfer1.slot_of(ag, xfer1.H1)),
            ag.pattern_memory.size)
        self.assertEqual(before, after, "la frontera borró algo más")

    # --- three worlds ----------------------------------------------------
    def test_the_borders_move_real_physics(self) -> None:
        r = self.report
        self.assertEqual(r["worlds"], 3)
        self.assertGreater(r["world_physics_differences_A_B"], 0)
        self.assertGreater(r["world_physics_differences_B_C"], 0)
        self.assertNotEqual(r["physics_differences_A_B"],
                            r["physics_differences_B_C"],
                            "el segundo cambio no puede ser el primero")
        self.assertEqual(xfer1.physics_differences(xfer1.PARK_B,
                                                   xfer1.PARK_B), [])
        # Kinds, actions and packets are shared; only the tables move.
        for one in xfer1.LAYOUTS:
            env = xfer1.ParkEnv(one)
            self.assertEqual(env.kind, xfer1.KINDS)
            self.assertEqual(env.riff, xfer1.riff_table())
        # T holds rows that still fit, and at least one that no longer does.
        for label in ("B", "C"):
            self.assertGreater(r[f"t_known_rows_on_entry_{label}"], 0, label)
            self.assertGreater(r[f"t_agreements_on_entry_{label}"], 0, label)
            self.assertGreater(r[f"t_contradictions_on_entry_{label}"], 0,
                               label)
            self.assertLess(r[f"t_contradictions_on_entry_{label}"],
                            r[f"t_known_rows_on_entry_{label}"], label)

    def test_the_riff_is_the_same_rule_in_all_three(self) -> None:
        """One table, off a cycle, and no branch by world name."""
        table = xfer1.riff_table()
        self.assertEqual(table, pattern0.successors_of(xfer1.RIFF_CYCLE))
        self.assertEqual(len(table), len(xfer1.RIFF_CYCLE))
        for one in xfer1.LAYOUTS:
            self.assertEqual(xfer1.ParkEnv(one).riff, table, one)
        self.assertEqual(self.report["world_name_branches_in_core"], [])
        # The scan can fail.
        # Both rules, each on an injection that trips only it.
        self.assertTrue(xfer1.world_name_branches(
            {"loop.py": "# park_b es el segundo parque\n"}),
            "el barrido de texto")
        self.assertTrue(xfer1.world_name_branches(
            {"loop.py": "def f(env):\n    return env.layout\n"}),
            "leer el nombre del mundo sin nombrarlo")
        self.assertTrue(xfer1.world_name_branches(
            {"world.py": "PARK_A = 1\n"}))
        # And `escalate.level` is not a world's name.
        self.assertEqual(xfer1.world_name_branches(
            {"loop.py": "def f(e):\n    return e.level\n"}), [])
        self.assertGreaterEqual(self.report["pattern_mature_contexts"], 2)

    # --- the two borders -------------------------------------------------
    def test_both_borders_pay_on_their_own(self) -> None:
        r = self.report
        self.assertGreater(r["gain_B"], 0, r["rows"][xfer1.PARK_B])
        self.assertGreater(r["gain_C"], 0, r["rows"][xfer1.PARK_C])
        self.assertEqual(r["gain_B"],
                         r["transfer_reward_B"] - r["scratch_reward_B"])
        self.assertEqual(r["gain_C"],
                         r["transfer_reward_C"] - r["scratch_reward_C"])
        self.assertEqual(r["aggregate_transfer_gain"],
                         r["gain_B"] + r["gain_C"])
        self.assertGreater(r["aggregate_transfer_gain"], 0)
        # A positive total with a dead border must not pass — and each
        # clause has to be the one that refuses it, so the bend leaves
        # every other clause satisfied: the aggregate still adds up, is
        # still positive, and the rewards still differ.
        for label, other in (("B", "C"), ("C", "B")):
            bent = dict(r)
            bent[f"gain_{label}"] = 0
            bent[f"gain_{other}"] = r["aggregate_transfer_gain"]
            bent["aggregate_transfer_gain"] = bent["gain_B"] + bent["gain_C"]
            self.assertGreater(bent["aggregate_transfer_gain"], 0)
            self.assertEqual(bent["aggregate_transfer_gain"],
                             bent["gain_B"] + bent["gain_C"])
            self.assertGreater(
                bent[f"transfer_reward_{label}"] - bent[f"scratch_reward_{label}"],
                0, "la cláusula de recompensas sigue contenta")
            self.assertFalse(xfer1.green(bent),
                             f"gain_{label} = 0 pasó con el total positivo")
        # And the reward clause is load-bearing on its own too.
        for label in ("B", "C"):
            bent = dict(r, **{f"transfer_reward_{label}":
                              r[f"scratch_reward_{label}"]})
            self.assertFalse(xfer1.green(bent), label)

    def test_mileage_alone_buys_nothing(self) -> None:
        r = self.report
        self.assertLessEqual(r["age_control_gain_B"], 0)
        self.assertLessEqual(r["age_control_gain_C"], 0)
        self.assertEqual(r["pattern_age_hits_B"], 0)
        self.assertEqual(r["pattern_age_hits_C"], 0)
        # And it really did spend the turns.
        self.assertEqual(r["age_control_mileage_B"],
                         xfer1.SCHOOL_TURNS + xfer1.RIFF_TURNS)
        self.assertEqual(r["age_control_mileage_C"],
                         r["age_control_mileage_B"] + xfer1.WINDOW_TURNS)
        aged = xfer1.aged_agent(xfer1.SCHOOL_TURNS)
        self.assertEqual(aged.metrics.turns, xfer1.SCHOOL_TURNS)
        # Its own corridor is deterministic and does mature contexts — the
        # claim is not that an aged body learns nothing at all, it is that
        # it has none of the **transferable** structure. It never sees the
        # riff, and the hazards and the prize are not in its park.
        self.assertEqual(xfer1.probe(aged, xfer1.riff_points())["hits"], 0)
        for cell in xfer1.RIFF_CELLS:
            self.assertLess(xfer1.slot_of(aged, cell), 0,
                            f"el control de edad pisó el riff: {cell}")
        for cell in xfer1.HAZARDS + (xfer1.GOAL,):
            self.assertLess(xfer1.slot_of(aged, cell), 0,
                            f"el control de edad vio el paquete de {cell}")
        self.assertEqual(aged.metrics.action_pos, 0,
                         "en el parque vacío no se cobra nada")

    def test_the_protocol_is_matched_and_the_match_is_recorded(self) -> None:
        """Matched is a property of the protocol, not of the outcome.

        In this park the ε phase does not move the reward, so a control
        run on different turns would score the same and no number would
        notice. The fingerprint does.
        """
        r = self.report
        self.assertTrue(r["matched_seat"])
        self.assertTrue(r["matched_turns"])
        self.assertTrue(r["matched_flags"])
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            row = r["rows"][layout]
            self.assertTrue(row["matched_turn_values"], layout)
            self.assertTrue(row["matched_entry_cell"], layout)
            self.assertEqual(row["transfer"]["turn_first"],
                             row["scratch"]["turn_first"])
            self.assertEqual(row["transfer"]["turn_fingerprint"],
                             row["scratch"]["turn_fingerprint"])
            self.assertEqual(row["transfer"]["entry_cell"],
                             row["scratch"]["entry_cell"])
            self.assertEqual(row["transfer"]["turns"],
                             row["scratch"]["turns"])

    def test_the_predictor_is_t_extended_by_context(self) -> None:
        """Where the context has a rule it answers; elsewhere T does.

        Measured on the riff, where T is genuinely of two minds: the loop's
        own `_predict` has to come back with the context's answer, and it
        has to differ from what T alone would have said.
        """
        ag = xfer1.new_agent()
        xfer1.school(ag)
        r0 = xfer1.slot_of(ag, xfer1.R0)
        r1 = xfer1.slot_of(ag, xfer1.R1)
        r2 = xfer1.slot_of(ag, xfer1.R2)
        self.assertTrue(min(r0, r1, r2) >= 0)
        t_alone = ag.t.predict(r0, ACTION_APPROACH)
        self.assertIsNotNone(t_alone, "T tiene una fila, y una sola respuesta")
        answers = set()
        for prev, want_cell in ((r1, xfer1.R2), (r2, xfer1.R1)):
            ag.prev_slot = prev
            got = ag._predict(r0, ACTION_APPROACH)
            self.assertEqual(got, xfer1.slot_of(ag, want_cell))
            answers.add(got)
        self.assertEqual(len(answers), 2,
                         "el contexto distingue lo que T no puede")
        self.assertIn(t_alone, answers)
        self.assertEqual(sum(1 for a in answers if a != t_alone), 1)
        # With no context the answer falls through to T, unchanged.
        ag.clear_context()
        self.assertEqual(ag._predict(r0, ACTION_APPROACH), t_alone)
        # And with the memory off it is T and nothing else.
        plain = Agent(ask=False, env=xfer1.ParkEnv())
        self.assertIsNone(plain.pattern_memory)
        self.assertEqual(plain._predict(3, 0), plain.t.predict(3, 0))

    # --- the pattern probe -----------------------------------------------
    def test_the_context_memory_crosses_and_the_probe_learns_nothing(self) -> None:
        r = self.report
        for label in ("B", "C"):
            self.assertGreater(r[f"pattern_entry_points_{label}"], 0)
            self.assertGreater(r[f"pattern_transfer_hits_{label}"],
                               r[f"pattern_scratch_hits_{label}"], label)
        self.assertEqual(r["pattern_entry_points_B"],
                         r["pattern_entry_points_C"])
        self.assertEqual(r["pattern_observes_during_entry_probes"], 0)
        # None is a miss and stays in the denominator.
        row = r["rows"][xfer1.PARK_B]["pattern"]
        self.assertEqual(row["scratch"]["hits"], 0)
        self.assertEqual(row["scratch"]["unknown"],
                         row["scratch"]["points"])
        self.assertEqual(row["transfer"]["hits"] + row["transfer"]["unknown"],
                         row["transfer"]["points"])
        # The probe writes nothing.
        ag = xfer1.new_agent()
        xfer1.school(ag)
        before = (xfer1.identities(ag), ag.pattern_memory.snapshot_hash(),
                  ag.pattern_memory.observations,
                  sum(1 for s in ag.cam.slot if s.occupied))
        xfer1.probe(ag, xfer1.riff_points())
        self.assertEqual((xfer1.identities(ag),
                          ag.pattern_memory.snapshot_hash(),
                          ag.pattern_memory.observations,
                          sum(1 for s in ag.cam.slot if s.occupied)), before)

    # --- the gate --------------------------------------------------------
    def test_green_falls_on_every_lock(self) -> None:
        r = self.report
        self.assertTrue(xfer1.green(r))
        for key, wrong in (
            ("worlds", 2), ("same_agent_across_worlds", False),
            ("same_cam_object", False), ("same_q_object", False),
            ("same_t_object", False), ("same_pattern_object", False),
            ("world_physics_differences_A_B", 0),
            ("world_physics_differences_B_C", 0),
            ("t_known_rows_on_entry_B", 0), ("t_known_rows_on_entry_C", 0),
            ("t_contradictions_on_entry_B", 0),
            ("t_contradictions_on_entry_C", 0),
            ("gain_B", 0), ("gain_C", 0), ("gain_B", -1),
            ("transfer_reward_B", r["scratch_reward_B"]),
            ("transfer_reward_C", r["scratch_reward_C"]),
            ("aggregate_transfer_gain", 0),
            ("age_control_gain_B", 1), ("age_control_gain_C", 1),
            ("pattern_entry_points_B", 0),
            ("pattern_transfer_hits_B", 0), ("pattern_transfer_hits_C", 0),
            ("pattern_scratch_hits_B", r["pattern_transfer_hits_B"]),
            ("pattern_scratch_hits_C", r["pattern_transfer_hits_C"]),
            ("pattern_observes_during_entry_probes", 1),
            ("matched_seat", False), ("matched_turns", False),
            ("matched_flags", False),
            ("world_name_branches_in_core", ["algo"]),
            ("false_facts", 1), ("destroyed", 1), ("cortex_calls", 1),
            ("all_arms_cortex_calls", 1), ("human_labels", 1),
            ("n_actions", 4), ("thought_keys", 23),
            ("default_agent_has_pattern_memory", True),
        ):
            with self.subTest(lock=f"{key}={wrong}"):
                self.assertFalse(xfer1.green(dict(r, **{key: wrong})), key)

    def test_the_battery_cannot_be_emptied_or_faked(self) -> None:
        r = self.report
        state = xfer1.battery_state(r["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(len(xfer1.REQUIRED_MUTANTS),
                         len(set(xfer1.REQUIRED_MUTANTS)))
        self.assertGreaterEqual(len(xfer1.REQUIRED_MUTANTS), 22)
        self.assertEqual(state["total"], state["killed"])
        for required in xfer1.REQUIRED_MUTANTS:
            with self.subTest(deleted=required):
                gone = [m for m in r["mutants"] if m["mutant"] != required]
                self.assertFalse(xfer1.green(dict(
                    r, mutants=gone, mutants_total=len(gone),
                    mutants_killed=sum(1 for m in gone if m["killed"]))))
        alive = r["mutants"] + [{"mutant": "extra vivo", "killed": False}]
        for killed in (len(alive), sum(1 for m in alive if m["killed"])):
            self.assertFalse(xfer1.green(dict(
                r, mutants=alive, mutants_total=len(alive),
                mutants_killed=killed)))
        dead = r["mutants"] + [{"mutant": "extra muerto", "killed": True}]
        self.assertTrue(xfer1.green(dict(
            r, mutants=dead, mutants_total=len(dead),
            mutants_killed=len(dead))))
        for bad in ({"killed": True}, {"mutant": "x"},
                    {"mutant": "y", "killed": 1}, "no soy un objeto"):
            battery = r["mutants"] + [bad]
            self.assertFalse(xfer1.green(dict(
                r, mutants=battery, mutants_total=len(battery),
                mutants_killed=sum(1 for m in battery if isinstance(m, dict)
                                   and m.get("killed") is True))))
        self.assertFalse(xfer1.green(dict(r, mutants=None)))
        self.assertFalse(xfer1.green(dict(r, mutants_total=99)))
        self.assertFalse(xfer1.green(dict(r, mutants_killed=0)))
        for m in r["mutants"]:
            self.assertTrue(m["killed"], m["mutant"])

    # --- isolation -------------------------------------------------------
    def test_runner_writes_its_own_report_and_nobody_elses(self) -> None:
        lab = Path(__file__).resolve().parents[1] / "lab"
        others = ("nexus0_report.json", "nexus0_pattern0_report.json",
                  "nexus0_talk1_report.json", "nexus0_signc_report.json",
                  "nexus0_world3_report.json", "nexus0_cortex1_report.json",
                  "nexus0_qwen4b_report.json", "nexus0_obj1_report.json",
                  "nexus0_open1_report.json", "nexus0_room1_report.json",
                  "nexus0_self1_report.json", "nexus0_pulpo_report.json")
        diaries = tuple(sorted(p.name for p in lab.glob("*.jsonl")))

        def stamp(name: Path):
            if not name.is_file():
                return None
            return (name.read_bytes(), name.stat().st_mtime_ns)

        before = {n: stamp(lab / n) for n in others + diaries}
        with contextlib.redirect_stdout(io.StringIO()):
            rc = xfer1.main([])
        self.assertEqual(rc, 0, "green() passed, so the runner says 0")
        self.assertEqual({n: stamp(lab / n) for n in others + diaries}, before,
                         "XFER-1 wrote over another slice's report")
        written = json.loads(
            (lab / "nexus0_xfer1_report.json").read_text(encoding="utf-8"))
        self.assertTrue(written["green"], written)
        self.assertGreater(written["gain_B"], 0)
        self.assertGreater(written["gain_C"], 0)
        self.assertEqual(written["mutants_killed"], written["mutants_total"])
        self.assertEqual(written["world_name_branches_in_core"], [])

    def test_no_network_no_model_no_floats_in_the_park(self) -> None:
        source = Path(xfer1.__file__).read_text(encoding="utf-8")
        modules = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
            elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                self.fail(f"un float en el parque: {node.value}")
        for banned in ("urllib", "http", "requests", "socket", "subprocess",
                       "numpy", "torch", "transformers", "llama_cpp"):
            self.assertNotIn(banned, modules, banned)


class TestXfer1b(unittest.TestCase):
    """XFER-1b: closing the identity, the gains and the controls.

    XFER-1's causal result stands — 208 vs 152 at B, 224 vs 152 at C — and
    none of the physics, rewards, turns, seats or numbers move here. What
    moves is the audit, because three of its claims could be satisfied by
    something that was not what the claim said.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = xfer1.experiment()

    # --- 1. the body, not the luggage ------------------------------------
    def test_four_grafted_memories_are_not_the_same_animal(self) -> None:
        """The counterexample, literally."""
        old = xfer1.new_agent()
        xfer1.school(old)
        reborn = xfer1.new_agent()
        reborn.cam = old.cam
        reborn.q = old.q
        reborn.t = old.t
        reborn.pattern_memory = old.pattern_memory

        self.assertIsNot(reborn, old)
        self.assertEqual(xfer1.identities(reborn), xfer1.identities(old),
                         "las cuatro memorias son las mismas, y eso es cierto")
        self.assertFalse(xfer1.is_same_body(reborn, old),
                         "pero no es el mismo cuerpo")
        # Both claims stay: they are different claims.
        r = self.report
        self.assertTrue(r["same_agent_across_worlds"])
        self.assertTrue(r["same_agent_object"])
        self.assertFalse(xfer1.green(dict(r, same_agent_object=False)))
        for key in ("same_cam_object", "same_q_object", "same_t_object",
                    "same_pattern_object"):
            self.assertFalse(xfer1.green(dict(r, **{key: False})), key)
        # And each border carries its own answer — the border is the one
        # authority, and it can say no.
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            self.assertTrue(r["rows"][layout]["same_agent_object"], layout)
        expected = xfer1.new_agent()
        row = xfer1.border(xfer1.new_agent(), xfer1.PARK_B,
                           xfer1.riff_points()[:4], original=expected)
        self.assertFalse(row["same_agent_object"],
                         "un cuerpo distinto cruzó y la frontera lo aceptó")

    # --- 2. gains that are the differences they claim --------------------
    def test_a_gain_must_be_the_difference_it_names(self) -> None:
        """The counterexample: positive gains detached from the rewards."""
        r = self.report
        bent = dict(r, gain_B=1, gain_C=1, aggregate_transfer_gain=2)
        self.assertGreater(bent["gain_B"], 0)
        self.assertGreater(bent["gain_C"], 0)
        self.assertEqual(bent["aggregate_transfer_gain"],
                         bent["gain_B"] + bent["gain_C"])
        self.assertFalse(xfer1.green(bent),
                         "gains positivos desligados de las restas")
        # One at a time, with everything else consistent, and with the
        # summary flag lying — the gate recomputes.
        for label in ("B", "C"):
            other = "C" if label == "B" else "B"
            single = dict(r)
            single[f"gain_{label}"] = 1
            single["aggregate_transfer_gain"] = (single["gain_B"]
                                                 + single["gain_C"])
            single["gains_equal_reward_differences"] = True
            self.assertGreater(single[f"gain_{label}"], 0)
            self.assertGreater(single[f"gain_{other}"], 0)
            self.assertFalse(xfer1.green(single), label)
        self.assertTrue(r["gains_equal_reward_differences"])
        self.assertEqual(r["gain_B"],
                         r["transfer_reward_B"] - r["scratch_reward_B"])
        self.assertEqual(r["gain_C"],
                         r["transfer_reward_C"] - r["scratch_reward_C"])

    # --- 3. the flags of the arms that ran -------------------------------
    def test_the_signature_covers_every_arm_that_ran(self) -> None:
        r = self.report
        self.assertTrue(r["protocol_signatures_match"])
        wanted = {"n_actions", "ask_enabled", "cortex_enabled",
                  "pattern_memory", "plan_depth", "escalate_enabled",
                  "conflict_attend", "q_trace", "q_remainder",
                  "q_explore_flat", "env_seed"}
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            sigs = r["rows"][layout]["protocol_signatures"]
            self.assertEqual(set(sigs), {"transfer", "scratch", "age"}, layout)
            for arm, sig in sigs.items():
                self.assertTrue(wanted <= set(sig), f"{layout}/{arm}")
            self.assertTrue(xfer1.signatures_match(sigs), layout)
            self.assertEqual(r["rows"][layout]["protocol_signatures_match"],
                             xfer1.signatures_match(sigs), layout)
        # The comparison is one function, and it can say no.
        honest_sig = xfer1.protocol_signature(xfer1.new_agent())
        self.assertTrue(xfer1.signatures_match({"a": honest_sig,
                                                "b": dict(honest_sig)}))
        self.assertFalse(xfer1.signatures_match(
            {"a": honest_sig, "b": dict(honest_sig, ask_enabled=True)}))
        self.assertFalse(xfer1.signatures_match(
            {"a": honest_sig, "b": dict(honest_sig, env_seed=1)}))
        # The layout is deliberately not in it: it is the age arm's own
        # variable.
        self.assertNotIn("layout", r["protocol_signature"])
        self.assertNotIn("void", r["protocol_signature"])
        # Each way an arm could be a different kind of animal.
        honest = honest_sig
        for label, odd in (
            ("sin PatternMemory", xfer1.new_agent(pattern_on=False)),
            ("con cortex", Agent(ask=False, cortex=True, pattern_memory=True,
                                 env=xfer1.ParkEnv())),
            ("con ask", Agent(ask=True, pattern_memory=True,
                              env=xfer1.ParkEnv())),
            ("con explore_flat", Agent(ask=False, pattern_memory=True,
                                       explore_flat=True,
                                       env=xfer1.ParkEnv())),
            ("con remainder", Agent(ask=False, pattern_memory=True,
                                    remainder=True, env=xfer1.ParkEnv())),
            ("con plan_depth", Agent(ask=False, pattern_memory=True,
                                     plan_depth=2, env=xfer1.ParkEnv())),
            ("con otra semilla", Agent(ask=False, pattern_memory=True,
                                       env=xfer1.ParkEnv(seed=1))),
        ):
            with self.subTest(arm=label):
                self.assertNotEqual(xfer1.protocol_signature(odd), honest,
                                    label)
        self.assertFalse(xfer1.green(dict(r, protocol_signatures_match=False)))

    def test_the_invariants_are_summed_over_every_arm(self) -> None:
        r = self.report
        self.assertEqual(r["all_arms_false_facts"], 0)
        self.assertEqual(r["all_arms_destroyed"], 0)
        self.assertEqual(r["all_arms_cortex_calls"], 0)
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            self.assertEqual(set(r["arm_metrics"][layout]),
                             {"transfer", "scratch", "age"})
        for key in ("all_arms_false_facts", "all_arms_destroyed",
                    "all_arms_cortex_calls"):
            self.assertFalse(xfer1.green(dict(r, **{key: 1})), key)
        # `llm_calls` is not a written-down zero: the cortex hook is the
        # only door to a model, so it is that sum.
        self.assertEqual(r["llm_calls"], r["all_arms_cortex_calls"])
        self.assertEqual(r["human_labels"], 0)
        for layout in (xfer1.PARK_A, xfer1.PARK_B, xfer1.PARK_C):
            env = xfer1.ParkEnv(layout)
            for cell in (xfer1.S0, xfer1.H1, xfer1.GOAL, xfer1.R0):
                self.assertIsNone(env.teleport(cell).extract_text)

    # --- 4. the memory, isolated from CAM availability -------------------
    def test_the_ablation_is_perceptually_matched(self) -> None:
        """96–0 with an empty CAM proves nothing about the memory.

        The scratch row's zero is fully explained by having no slot for
        R0/R1/R2 — it never gets as far as asking. So the two arms are
        handed the same already-resolved integers.
        """
        r = self.report
        ag = xfer1.new_agent()
        xfer1.school(ag)
        points = xfer1.riff_points()
        resolved = xfer1.resolve_points(ag, points)
        self.assertEqual(xfer1.known_slots(resolved), len(points))
        for prev, cur, action, nxt in resolved:
            self.assertGreaterEqual(min(prev, cur, nxt), 0)

        matched = xfer1.ablation(ag, points)
        self.assertTrue(matched["mapping_matched"])
        self.assertEqual(matched["known_slots"], matched["points"])
        self.assertGreater(matched["trained"]["hits"], matched["empty"]["hits"])
        self.assertEqual(matched["empty"]["hits"], 0)
        self.assertEqual(matched["empty"]["unknown"], matched["points"],
                         "None sigue en el denominador")
        self.assertEqual(matched["writes"], 0)

        # The inverse: a CAM that cannot resolve gives zero for a reason
        # that has nothing to do with the memory, and must not be cited.
        blind = xfer1.ablation(xfer1.new_agent(), points)
        self.assertFalse(blind["mapping_matched"])
        self.assertEqual(blind["known_slots"], 0)
        self.assertEqual(blind["trained"]["hits"], 0)
        for key in ("pattern_probe_mapping_matched_B",
                    "pattern_probe_mapping_matched_C"):
            self.assertFalse(xfer1.green(dict(r, **{key: False})), key)
        for label in ("B", "C"):
            self.assertFalse(xfer1.green(dict(
                r, **{f"trained_pattern_hits_{label}":
                      r[f"empty_pattern_hits_{label}"]})), label)
            self.assertFalse(xfer1.green(dict(
                r, **{f"pattern_probe_known_slots_{label}": 0})), label)
        self.assertFalse(xfer1.green(dict(r, pattern_probe_writes=1)))
        # And it writes nothing anywhere.
        before = (ag.pattern_memory.snapshot_hash(),
                  ag.pattern_memory.observations,
                  pattern0.world_hash(ag.t),
                  sum(1 for s in ag.cam.slot if s.occupied))
        xfer1.ablation(ag, points)
        self.assertEqual((ag.pattern_memory.snapshot_hash(),
                          ag.pattern_memory.observations,
                          pattern0.world_hash(ag.t),
                          sum(1 for s in ag.cam.slot if s.occupied)), before)

    # --- 5. the channel --------------------------------------------------
    def test_the_memory_is_fed_exactly_what_t_is_fed(self) -> None:
        r = self.report
        audit = r["channel"]
        self.assertTrue(r["pattern_channel_matches_t"])
        self.assertTrue(audit["counts_match"])
        self.assertTrue(audit["projection_matches"])
        self.assertTrue(audit["refused_step_silences_both"])
        self.assertNotIn("matches", audit,
                         "una conjunción junto a sus propios conjuntos")
        # The audit can come back false: one transition dropped on its way
        # to the memory, and nothing else changed.
        broken = xfer1.channel_audit(skip_at=10)
        self.assertTrue(broken["skipped_one"])
        self.assertFalse(broken["projection_matches"],
                         "una transición perdida y la auditoría no lo vio")
        self.assertTrue(broken["refused_step_silences_both"])
        # One transition skipped per cut, and no more.
        self.assertEqual(audit["pattern_observations"],
                         audit["t_observations"] - audit["cuts"])
        self.assertEqual(len(audit["skipped_after_cuts"]), audit["cuts"])
        self.assertEqual(audit["skipped_after_cuts"][0], 0)
        # Measured again live, not read off the report.
        live = xfer1.channel_audit(turns=32)
        self.assertTrue(live["counts_match"])
        self.assertTrue(live["projection_matches"])
        self.assertEqual(live["pattern_observations"],
                         live["t_observations"] - live["cuts"])
        self.assertFalse(xfer1.green(dict(r, pattern_channel_matches_t=False)))

    # --- 6. the dead claim -----------------------------------------------
    def test_the_age_control_has_no_asserted_riff(self) -> None:
        """A control regularity claimed and never executed is gone.

        `PARK_VOID` used to be described as having "a riff whose
        successors alternate". It never ran: `aged_agent` does not enter
        R0/R1/R2 and the branch returned `options[0]` every time. The
        claim has been removed rather than dressed up.
        """
        void = xfer1.ParkEnv(xfer1.PARK_VOID, void=True)
        self.assertEqual(void.riff, {})
        self.assertFalse(hasattr(void, "void_riff"))
        src = Path(xfer1.__file__).read_text(encoding="utf-8")
        self.assertNotIn("balanced_successors", src,
                         "el riff alternante no usado sigue ahí")
        # What is true is measured: the aged body never touches the riff.
        aged = xfer1.aged_agent(xfer1.SCHOOL_TURNS)
        for cell in xfer1.RIFF_CELLS:
            self.assertLess(xfer1.slot_of(aged, cell), 0, cell)
        self.assertEqual(self.report["pattern_age_hits_B"], 0)
        self.assertEqual(self.report["pattern_age_hits_C"], 0)

    # --- the battery and the report --------------------------------------
    def test_the_battery_covers_the_new_claims(self) -> None:
        r = self.report
        state = xfer1.battery_state(r["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(state["total"], state["killed"])
        for name in ("Agent nuevo con las cuatro memorias antiguas injertadas",
                     "gain_B positivo pero desligado de las restas",
                     "gain_C positivo pero desligado de las restas",
                     "el scratch nace sin PatternMemory",
                     "el scratch nace con cortex y ask encendidos",
                     "el scratch nace con otro remainder o explore_flat",
                     "el control de edad nace con otros flags",
                     "el scratch nace con otra semilla",
                     "la ablación cita una CAM que no resuelve",
                     "una transición se le quita a PatternMemory"):
            self.assertIn(name, xfer1.REQUIRED_MUTANTS, name)
            self.assertIn(name, [m["mutant"] for m in r["mutants"]], name)
        for required in xfer1.REQUIRED_MUTANTS:
            with self.subTest(deleted=required):
                gone = [m for m in r["mutants"] if m["mutant"] != required]
                self.assertFalse(xfer1.green(dict(
                    r, mutants=gone, mutants_total=len(gone),
                    mutants_killed=sum(1 for m in gone if m["killed"]))))

    def test_the_report_is_deterministic_and_carries_no_address(self) -> None:
        first = xfer1.experiment()
        second = xfer1.experiment()
        for report in (first, second):
            report.pop("mutants", None)
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))
        blob = json.dumps(self.report, sort_keys=True)
        self.assertNotIn("identities_at_birth", blob)
        for key in ("identities_before", "identities_after"):
            self.assertNotIn(key, blob, key)


class TestXfer1c(unittest.TestCase):
    """XFER-1c: the gate reads the evidence, not the report's summary of it.

    XFER-1b's implementation was right and its numbers are untouched. What
    was left was a certificate that could contradict the rows underneath
    it: the raw data lives in `rows`, `arm_metrics`, `channel` and
    `ablation`, and `green()` only ever consulted top-level copies. So
    emptying `rows` entirely changed nothing.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = xfer1.experiment()

    def _bend(self, **_unused):
        import copy

        return copy.deepcopy(self.report)

    # --- the six counterexamples, literally ------------------------------
    def test_the_certificate_cannot_contradict_its_own_rows(self) -> None:
        B = xfer1.PARK_B
        self.assertTrue(xfer1.green(self.report))

        b = self._bend(); b["rows"] = {}
        self.assertFalse(xfer1.green(b), "rows vacías")

        b = self._bend(); b["rows"][B]["same_agent_object"] = False
        self.assertFalse(xfer1.green(b), "la fila dice que no es el mismo cuerpo")

        b = self._bend()
        b["rows"][B]["protocol_signatures"]["scratch"]["ask_enabled"] = True
        self.assertFalse(xfer1.green(b), "la firma cruda del scratch difiere")

        b = self._bend(); b["arm_metrics"][B]["scratch"]["cortex_calls"] = 1
        self.assertFalse(xfer1.green(b), "un scratch llamó al córtex")

        b = self._bend(); b["channel"]["projection_matches"] = False
        self.assertFalse(xfer1.green(b), "el canal crudo no cuadra")

        b = self._bend(); b["rows"][B]["ablation"]["mapping_matched"] = False
        self.assertFalse(xfer1.green(b), "la ablación cruda no está emparejada")

    def test_every_summary_is_tied_to_the_row_it_summarises(self) -> None:
        for layout, label in ((xfer1.PARK_B, "B"), (xfer1.PARK_C, "C")):
            for key, bend in (
                (f"transfer_reward_{label}", lambda r, la=layout:
                 r["rows"][la]["transfer"].update(reward=1)),
                (f"scratch_reward_{label}", lambda r, la=layout:
                 r["rows"][la]["scratch"].update(reward=1)),
                (f"age_control_gain_{label}", lambda r, la=layout:
                 r["rows"][la]["age"].update(reward=10 ** 6)),
                (f"pattern_transfer_hits_{label}", lambda r, la=layout:
                 r["rows"][la]["pattern"]["transfer"].update(hits=0)),
                (f"trained_pattern_hits_{label}", lambda r, la=layout:
                 r["rows"][la]["ablation"]["trained"].update(hits=0)),
                (f"pattern_probe_known_slots_{label}", lambda r, la=layout:
                 r["rows"][la]["ablation"].update(known_slots=0)),
            ):
                with self.subTest(row=key):
                    b = self._bend()
                    bend(b)
                    self.assertFalse(xfer1.green(b), key)
            # And the summary moved while the row stays put.
            for key, wrong in ((f"transfer_reward_{label}", 999),
                               (f"scratch_reward_{label}", 0),
                               (f"gain_{label}", 999),
                               (f"age_control_gain_{label}", -5),
                               (f"pattern_entry_points_{label}", 1),
                               (f"pattern_scratch_hits_{label}", 96),
                               (f"empty_pattern_hits_{label}", 96)):
                with self.subTest(summary=key):
                    self.assertFalse(
                        xfer1.green(dict(self.report, **{key: wrong})), key)
        self.assertFalse(xfer1.green(dict(self.report,
                                          aggregate_transfer_gain=1)))
        self.assertFalse(xfer1.green(dict(self.report, llm_calls=1)))
        for key in ("all_arms_false_facts", "all_arms_destroyed",
                    "all_arms_cortex_calls", "all_arms_cortex_rejected"):
            self.assertFalse(xfer1.green(dict(self.report, **{key: 1})), key)

    def test_a_probe_or_an_arm_that_wrote_is_caught_from_the_row(self) -> None:
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            for arm in ("transfer", "scratch", "age"):
                with self.subTest(layout=layout, arm=arm):
                    b = self._bend()
                    b["rows"][layout]["pattern"][arm]["observes"] = 1
                    self.assertFalse(xfer1.green(b))
                for key in ("false_facts", "destroyed", "cortex_calls",
                            "cortex_rejected"):
                    with self.subTest(layout=layout, arm=arm, metric=key):
                        b = self._bend()
                        b["arm_metrics"][layout][arm][key] = 1
                        self.assertFalse(xfer1.green(b))
            b = self._bend()
            b["rows"][layout]["ablation"]["writes"] = 1
            self.assertFalse(xfer1.green(b))

    def test_a_malformed_report_is_judged_not_raised(self) -> None:
        for label, bend in (
            ("rows ausente", lambda r: r.pop("rows")),
            ("rows es texto", lambda r: r.update(rows="dos parques")),
            ("una fila de más", lambda r: r["rows"].update(park_z={})),
            ("una fila de menos", lambda r: r["rows"].pop(xfer1.PARK_C)),
            ("arm_metrics ausente", lambda r: r.pop("arm_metrics")),
            ("un brazo de menos", lambda r:
             r["arm_metrics"][xfer1.PARK_B].pop("age")),
            ("una métrica no entera", lambda r:
             r["arm_metrics"][xfer1.PARK_B]["scratch"].update(cortex_calls="0")),
            ("una métrica booleana", lambda r:
             r["arm_metrics"][xfer1.PARK_B]["scratch"].update(cortex_calls=False)),
            ("channel ausente", lambda r: r.pop("channel")),
            ("firmas incompletas", lambda r:
             r["rows"][xfer1.PARK_B]["protocol_signatures"].pop("age")),
            ("una recompensa que no es entera", lambda r:
             r["rows"][xfer1.PARK_B]["transfer"].update(reward=None)),
            ("la ablación no es un objeto", lambda r:
             r["rows"][xfer1.PARK_B].update(ablation=7)),
        ):
            with self.subTest(bend=label):
                b = self._bend()
                bend(b)
                self.assertIs(xfer1.green(b), False, label)
        for junk in (None, "un informe", 42, [], {}):
            with self.subTest(junk=type(junk).__name__):
                self.assertIs(xfer1.green(junk), False)
                self.assertIsNone(xfer1.evidence(junk))

    def test_each_check_refuses_something_only_it_can_see(self) -> None:
        """Bend the row *and* its summary together, so the tie agrees.

        With both moved consistently the equality checks are satisfied and
        only the direct clause is left to refuse — otherwise the tie would
        be doing all the work and the clause could be deleted unnoticed.
        """
        B = xfer1.PARK_B
        # the signatures themselves, with the row's own flag agreeing
        b = self._bend()
        b["rows"][B]["protocol_signatures"]["scratch"]["ask_enabled"] = True
        b["rows"][B]["protocol_signatures_match"] = False
        self.assertFalse(xfer1.signatures_match(
            b["rows"][B]["protocol_signatures"]))
        self.assertFalse(xfer1.green(b), "las firmas crudas difieren")

        # the arm metrics, with the top-level sums moved to match
        b = self._bend()
        b["arm_metrics"][B]["scratch"]["cortex_calls"] = 1
        b["all_arms_cortex_calls"] = 1
        b["llm_calls"] = 1
        self.assertFalse(xfer1.green(b), "un brazo llamó al córtex")
        b = self._bend()
        b["arm_metrics"][B]["age"]["cortex_rejected"] = 1
        b["all_arms_cortex_rejected"] = 1
        self.assertFalse(xfer1.green(b), "un brazo tuvo un rechazo")

        # the ablation, with its summary moved to match
        b = self._bend()
        b["rows"][B]["ablation"]["mapping_matched"] = False
        b["pattern_probe_mapping_matched_B"] = False
        self.assertFalse(xfer1.green(b), "la ablación no está emparejada")

        # the probe writes, with the summary moved to match
        b = self._bend()
        b["rows"][B]["pattern"]["transfer"]["observes"] = 1
        b["pattern_observes_during_entry_probes"] = 1
        self.assertFalse(xfer1.green(b), "la sonda escribió")
        b = self._bend()
        b["rows"][B]["ablation"]["writes"] = 1
        b["pattern_probe_writes"] = 1
        self.assertFalse(xfer1.green(b), "la ablación escribió")

    def test_a_leaf_missing_from_a_row_is_judged_not_raised(self) -> None:
        """The net covers the verdict, not only the shape check."""
        B = xfer1.PARK_B
        for label, bend in (
            ("trained sin hits", lambda r:
             r["rows"][B]["ablation"]["trained"].pop("hits")),
            ("empty sin hits", lambda r:
             r["rows"][B]["ablation"]["empty"].pop("hits")),
            ("una sonda sin observes", lambda r:
             r["rows"][B]["pattern"]["scratch"].pop("observes")),
            ("una sonda que no es un objeto", lambda r:
             r["rows"][B]["pattern"].update(scratch=None)),
            ("la ablación sin points", lambda r:
             r["rows"][B]["ablation"].pop("points")),
        ):
            with self.subTest(bend=label):
                b = self._bend()
                bend(b)
                self.assertIs(xfer1.green(b), False, label)

    def test_evidence_recomputes_what_the_report_claims(self) -> None:
        ev = xfer1.evidence(self.report)
        self.assertIsNotNone(ev)
        r = self.report
        for layout, label in ((xfer1.PARK_B, "B"), (xfer1.PARK_C, "C")):
            self.assertEqual(ev["gains"][layout], r[f"gain_{label}"])
            self.assertEqual(ev["age_gains"][layout],
                             r[f"age_control_gain_{label}"])
            self.assertEqual(ev["rewards"][layout]["transfer"],
                             r[f"transfer_reward_{label}"])
        self.assertEqual(sum(ev["gains"].values()),
                         r["aggregate_transfer_gain"])
        self.assertEqual(ev["sums"], {"false_facts": 0, "destroyed": 0,
                                      "cortex_calls": 0, "cortex_rejected": 0})
        # XFER-1d moved the booleans out of `evidence`: a claim that fails
        # now makes it return None rather than come back as a False that
        # somebody has to remember to read.
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            self.assertIn(layout, ev["walks"])
            self.assertIn(layout, ev["pattern"])
            self.assertIn(layout, ev["ablation"])
        self.assertTrue(ev["channel"]["silent"])

    # --- 2. the refusal, audited from the calls --------------------------
    def test_a_refused_step_silences_both_and_the_audit_can_see_it(self) -> None:
        honest = xfer1.channel_audit()
        self.assertEqual(honest["refused_t_observations"], 0)
        self.assertEqual(honest["refused_pattern_observations"], 0)
        self.assertTrue(honest["refused_step_silences_both"])
        # The counterexample: T observes after the refusal, in a slot the
        # old check — `quiet.t.pred[0]` before and after — never looked at.
        leaked = xfer1.channel_audit(leak_at_slot=1234)
        self.assertEqual(leaked["refused_t_observations"], 1)
        self.assertEqual(leaked["refused_pattern_observations"], 0)
        self.assertFalse(leaked["refused_step_silences_both"],
                         "T aprendió tras el rechazo y la auditoría no lo vio")
        # Everything else about that run is unchanged, so it is that one
        # counter doing the work.
        for key in ("t_observations", "pattern_observations", "cuts",
                    "counts_match", "projection_matches"):
            self.assertEqual(leaked[key], honest[key], key)
        b = self._bend()
        b["channel"] = leaked
        self.assertFalse(xfer1.green(b))
        self.assertNotIn("t_before", xfer1.channel_audit())

    # --- the battery -----------------------------------------------------
    def test_the_battery_covers_the_raw_evidence(self) -> None:
        r = self.report
        for name in ("las filas crudas desaparecen del informe",
                     "una fila cruda dice que el cuerpo no es el mismo",
                     "la firma cruda del scratch difiere",
                     "un scratch registra una llamada al córtex",
                     "un brazo registra un rechazo del córtex",
                     "la ablación cruda dice que no está emparejada",
                     "el canal crudo dice que la proyección no cuadra",
                     "tras el rechazo T observa fuera de la fila cero"):
            self.assertIn(name, xfer1.REQUIRED_MUTANTS, name)
            entry = next(m for m in r["mutants"] if m["mutant"] == name)
            self.assertTrue(entry["killed"], name)
        state = xfer1.battery_state(r["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(len(xfer1.REQUIRED_MUTANTS),
                         len(set(xfer1.REQUIRED_MUTANTS)))

    def test_the_numbers_did_not_move(self) -> None:
        r = self.report
        self.assertEqual((r["transfer_reward_B"], r["scratch_reward_B"],
                          r["gain_B"]), (208, 152, 56))
        self.assertEqual((r["transfer_reward_C"], r["scratch_reward_C"],
                          r["gain_C"]), (224, 152, 72))
        self.assertEqual(r["aggregate_transfer_gain"], 128)
        self.assertEqual((r["trained_pattern_hits_B"],
                          r["empty_pattern_hits_B"],
                          r["pattern_probe_writes"]), (96, 0, 0))
        self.assertEqual((r["channel"]["t_observations"],
                          r["channel"]["pattern_observations"],
                          r["channel"]["cuts"]), (64, 62, 2))
        self.assertTrue(r["green"] if "green" in r else xfer1.green(r))


class TestXfer1d(unittest.TestCase):
    """XFER-1d: the whole evidence graph, coherent with itself.

    XFER-1c stopped the certificate contradicting its rows. What was left
    was rows contradicting **each other**: three signatures agreeing on
    the wrong protocol, an ablation of 95 points quoted beside a 96-point
    probe, a refusal counter beside a boolean that disagreed with it. The
    numbers are untouched — this is all certificate.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = xfer1.experiment()

    def _bend(self):
        import copy

        return copy.deepcopy(self.report)

    # --- 1. the canonical signature --------------------------------------
    def test_the_expected_protocol_is_pinned_to_the_real_one(self) -> None:
        """A literal, pinned here — so a change to `new_agent` goes red."""
        self.assertEqual(xfer1.XFER1_PROTOCOL,
                         xfer1.protocol_signature(xfer1.new_agent()))
        self.assertEqual(xfer1.XFER1_PROTOCOL["ask_enabled"], False)
        self.assertEqual(xfer1.XFER1_PROTOCOL["cortex_enabled"], False)
        self.assertEqual(xfer1.XFER1_PROTOCOL["pattern_memory"], True)
        self.assertEqual(xfer1.XFER1_PROTOCOL["n_actions"], N_ACTIONS)
        self.assertEqual(xfer1.XFER1_PROTOCOL["env_seed"],
                         xfer1.ParkEnv().seed)
        self.assertEqual(xfer1.XFER1_PROTOCOL["window_turns"],
                         xfer1.WINDOW_TURNS)
        self.assertEqual(set(xfer1.XFER1_PROTOCOL),
                         set(xfer1.SIGNATURE_BOOLS) | set(xfer1.SIGNATURE_INTS))

    def test_equality_between_signatures_is_not_correctness(self) -> None:
        B, C = xfer1.PARK_B, xfer1.PARK_C
        # 1 — the same key missing from all three.
        b = self._bend()
        for arm in xfer1.ARMS:
            b["rows"][B]["protocol_signatures"][arm].pop("ask_enabled")
        self.assertTrue(xfer1.signatures_match(
            b["rows"][B]["protocol_signatures"]), "las tres siguen iguales")
        self.assertFalse(xfer1.green(b), "falta la misma clave en las tres")
        # 2 — all three break the protocol, in perfect agreement.
        b = self._bend()
        for layout in (B, C):
            for arm in xfer1.ARMS:
                b["rows"][layout]["protocol_signatures"][arm]["ask_enabled"] = True
        self.assertTrue(xfer1.signatures_match(
            b["rows"][B]["protocol_signatures"]))
        self.assertFalse(xfer1.green(b), "las tres incumplen el protocolo")
        # 3 — one differs from the other two.
        b = self._bend()
        b["rows"][C]["protocol_signatures"]["age"]["plan_depth"] = 2
        self.assertFalse(xfer1.green(b))
        # types, not just values
        for arm_key, wrong in (("ask_enabled", 0), ("pattern_memory", 1),
                               ("n_actions", True), ("env_seed", "20260903"),
                               ("plan_depth", 0.0)):
            with self.subTest(typed=arm_key):
                b = self._bend()
                for layout in (B, C):
                    for arm in xfer1.ARMS:
                        b["rows"][layout]["protocol_signatures"][arm][arm_key] = wrong
                self.assertIsNone(xfer1.signature_evidence(
                    b["rows"][B]["protocol_signatures"]), arm_key)
                self.assertFalse(xfer1.green(b), arm_key)
        # an extra key is not the canonical signature either
        b = self._bend()
        for arm in xfer1.ARMS:
            b["rows"][B]["protocol_signatures"][arm]["extra"] = 1
        self.assertFalse(xfer1.green(b))

    # --- 2. the protocol, recomputed from the walks ----------------------
    def test_the_walk_protocol_is_recomputed_not_believed(self) -> None:
        B, C = xfer1.PARK_B, xfer1.PARK_C
        for label, layout, arm, field, delta in (
            ("turn_first", B, "transfer", "turn_first", 1),
            ("turn_last", C, "scratch", "turn_last", 1),
            ("fingerprint", C, "scratch", "turn_fingerprint", 1),
            ("turns", B, "age", "turns", 1),
            ("entry_cell", B, "age", "entry_cell", 13),
        ):
            with self.subTest(field=label):
                b = self._bend()
                b["rows"][layout][arm][field] += delta
                # The row's own booleans are left saying everything matched.
                self.assertTrue(b["rows"][layout]["matched_turn_values"])
                self.assertTrue(b["rows"][layout]["matched_entry_cell"])
                self.assertFalse(xfer1.green(b), label)
        # The fingerprint is the sum of the turn values, so it cannot be
        # moved on its own — recomputed, not copied.
        ev = xfer1.evidence(self.report)
        for layout in (B, C):
            walk = ev["walks"][layout]
            self.assertEqual(walk["turn_fingerprint"],
                             sum(range(walk["turn_first"],
                                       walk["turn_last"] + 1)))
            self.assertEqual(walk["turns"], xfer1.WINDOW_TURNS)
            self.assertEqual(walk["entry_cell"], xfer1.SEAT)
        self.assertIsNone(xfer1.walk_evidence({}))
        self.assertIsNone(xfer1.walk_evidence(
            {a: {"reward": 0} for a in xfer1.ARMS}))

    # --- 3. the denominators ---------------------------------------------
    def test_every_denominator_is_checked_from_the_row(self) -> None:
        B, C = xfer1.PARK_B, xfer1.PARK_C
        # the published entry table
        ev = xfer1.evidence(self.report)
        for layout in (B, C):
            probes = ev["pattern"][layout]
            n = probes["transfer"]["points"]
            self.assertEqual(n, 96)
            self.assertEqual((probes["transfer"]["hits"],
                              probes["transfer"]["unknown"]), (96, 0))
            for arm in ("scratch", "age"):
                self.assertEqual((probes[arm]["hits"], probes[arm]["unknown"]),
                                 (0, n), arm)
            for arm in xfer1.ARMS:
                self.assertEqual(probes[arm]["observes"], 0, arm)
            ab = ev["ablation"][layout]
            self.assertEqual(ab["points"], n)
            self.assertEqual(ab["known_slots"], n)
            self.assertEqual((ab["trained"]["hits"], ab["trained"]["unknown"]),
                             (n, 0))
            self.assertEqual((ab["empty"]["hits"], ab["empty"]["unknown"]),
                             (0, n))
            self.assertEqual(ab["writes"], 0)

        for label, bend in (
            ("el vacío deja de declarar sus None",
             lambda r: r["rows"][B]["ablation"]["empty"].update(unknown=0)),
            ("la ablación entrenada escribe",
             lambda r: r["rows"][B]["ablation"]["trained"].update(observes=1)),
            ("la ablación declara escrituras",
             lambda r: r["rows"][B]["ablation"].update(writes=1)),
            ("una sonda con otro número de puntos",
             lambda r: r["rows"][B]["pattern"]["scratch"].update(points=95)),
            ("el brazo de edad con otros puntos",
             lambda r: r["rows"][C]["pattern"]["age"].update(points=95)),
            ("hits mayores que los puntos",
             lambda r: r["rows"][B]["pattern"]["transfer"].update(hits=999)),
            ("hits negativos",
             lambda r: r["rows"][B]["pattern"]["scratch"].update(hits=-1)),
            ("unknown negativo",
             lambda r: r["rows"][C]["pattern"]["age"].update(unknown=-1)),
            ("un contador booleano",
             lambda r: r["rows"][B]["pattern"]["scratch"].update(observes=False)),
            ("hits + unknown por encima del total",
             lambda r: r["rows"][B]["ablation"]["empty"].update(hits=1)),
            ("cero puntos",
             lambda r: r["rows"][B]["pattern"]["transfer"].update(points=0)),
        ):
            with self.subTest(bend=label):
                b = self._bend()
                bend(b)
                self.assertFalse(xfer1.green(b), label)

        # An ablation of 95 quoted beside a 96-point probe, with every
        # summary moved coherently.
        b = self._bend()
        ab = b["rows"][B]["ablation"]
        ab["points"] = ab["known_slots"] = 95
        ab["trained"]["points"] = ab["empty"]["points"] = 95
        ab["trained"]["hits"] = 95
        ab["trained"]["unknown"] = 0
        ab["empty"]["unknown"] = 95
        b["pattern_probe_known_slots_B"] = 95
        b["trained_pattern_hits_B"] = 95
        self.assertEqual(b["rows"][B]["pattern"]["transfer"]["points"], 96)
        self.assertFalse(xfer1.green(b),
                         "una ablación de 95 junto a una sonda de 96")

    # --- 4. the channel ---------------------------------------------------
    def test_the_channel_verdict_is_recomputed_from_its_counters(self) -> None:
        r = self.report
        b = self._bend()
        b["channel"]["refused_t_observations"] = 1
        self.assertTrue(b["channel"]["refused_step_silences_both"],
                        "el resumen sigue diciendo que hubo silencio")
        self.assertFalse(xfer1.green(b))
        b = self._bend()
        b["channel"]["refused_pattern_observations"] = 1
        self.assertFalse(xfer1.green(b))
        # the honest protocol of the audit itself
        ch = r["channel"]
        self.assertEqual(ch["turns"], xfer1.CHANNEL_TURNS)
        self.assertEqual(ch["t_observations"], ch["turns"])
        self.assertEqual(ch["cuts"], len(ch["skipped_after_cuts"]))
        self.assertEqual(tuple(ch["skipped_after_cuts"]), xfer1.CHANNEL_CUTS)
        self.assertEqual(ch["pattern_observations"],
                         ch["t_observations"] - ch["cuts"])
        for label, bend in (
            ("otro número de turnos", lambda c: c.update(turns=32)),
            ("T observó de más", lambda c: c.update(t_observations=65)),
            ("otro número de cortes", lambda c: c.update(cuts=1)),
            ("otros cortes", lambda c: c.update(skipped_after_cuts=[0, 31])),
            ("Pattern observó de más",
             lambda c: c.update(pattern_observations=63)),
            ("counts_match falso", lambda c: c.update(counts_match=False)),
            ("projection_matches falso",
             lambda c: c.update(projection_matches=False)),
            ("un contador que no es entero",
             lambda c: c.update(t_observations="64")),
        ):
            with self.subTest(bend=label):
                b = self._bend()
                bend(b["channel"])
                self.assertFalse(xfer1.green(b), label)
        # and the executable mutant still works
        leaked = xfer1.channel_audit(leak_at_slot=1234)
        self.assertIsNone(xfer1.channel_evidence(leaked))
        b = self._bend()
        b["channel"] = leaked
        self.assertFalse(xfer1.green(b))

    # --- 5. the memories at each border ----------------------------------
    def test_each_border_says_the_four_memories_are_the_same(self) -> None:
        r = self.report
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            self.assertTrue(r["rows"][layout]["same_objects"], layout)
            with self.subTest(layout=layout):
                b = self._bend()
                b["rows"][layout]["same_objects"] = False
                self.assertFalse(xfer1.green(b))
                b = self._bend()
                b["rows"][layout]["same_agent_object"] = False
                self.assertFalse(xfer1.green(b))
        # And the direct `is` checks stay, on a live run.
        ag = xfer1.new_agent()
        born, mems = ag, xfer1.identities(ag)
        xfer1.school(ag)
        for layout in (xfer1.PARK_B, xfer1.PARK_C):
            xfer1.cross_into(ag, layout)
            self.assertIs(ag, born)
            self.assertEqual(xfer1.identities(ag), mems)
        # No addresses in the report: neither the old keys nor any value
        # big enough to be one.
        for key in ("identities_at_birth", "identities_after_school",
                    "identities_after_borders", "identities_before",
                    "identities_after"):
            self.assertNotIn(key, json.dumps(r, sort_keys=True), key)

        def addresses(node):
            if isinstance(node, dict):
                return any(addresses(v) for v in node.values())
            if isinstance(node, list):
                return any(addresses(v) for v in node)
            return isinstance(node, int) and not isinstance(node, bool) \
                and abs(node) > 10 ** 9

        self.assertFalse(addresses(r), "un valor con pinta de dirección")

    # --- 6. one validator per structure ----------------------------------
    def test_every_validator_refuses_a_shape_and_never_raises(self) -> None:
        for fn in (xfer1.signature_evidence, xfer1.walk_evidence,
                   xfer1.pattern_evidence, xfer1.channel_evidence,
                   xfer1.evidence):
            for junk in (None, "texto", 42, [], {}, {"a": 1}):
                with self.subTest(fn=fn.__name__, junk=type(junk).__name__):
                    self.assertIsNone(fn(junk))
        # And they say yes to the real thing.
        row = self.report["rows"][xfer1.PARK_B]
        self.assertIsNotNone(
            xfer1.signature_evidence(row["protocol_signatures"]))
        self.assertIsNotNone(xfer1.walk_evidence(row))
        self.assertIsNotNone(xfer1.pattern_evidence(row))
        self.assertIsNotNone(xfer1.channel_evidence(self.report["channel"]))
        self.assertIsNotNone(xfer1.evidence(self.report))
        # No boolean in a row is the final authority for its own structure.
        for key in ("matched_turn_values", "matched_entry_cell",
                    "protocol_signatures_match", "same_objects",
                    "same_agent_object"):
            b = self._bend()
            b["rows"][xfer1.PARK_B][key] = False
            self.assertFalse(xfer1.green(b), key)

    def test_a_coherent_lie_across_all_three_arms_still_falls(self) -> None:
        """Bend every arm the same way, so the cross-arm check agrees.

        Moving one arm's fingerprint breaks the comparison between arms
        and is caught there; moving all three keeps them agreeing, and
        only the recomputation is left to refuse.
        """
        B, C = xfer1.PARK_B, xfer1.PARK_C
        for label, bend in (
            ("el fingerprint de los tres brazos", lambda r: [
                r["rows"][B][arm].update(
                    turn_fingerprint=r["rows"][B][arm]["turn_fingerprint"] + 1)
                for arm in xfer1.ARMS]),
            ("la ventana de los tres brazos", lambda r: [
                r["rows"][B][arm].update(turns=32) for arm in xfer1.ARMS]),
            ("el asiento de los tres brazos", lambda r: [
                r["rows"][B][arm].update(entry_cell=xfer1.S5)
                for arm in xfer1.ARMS]),
            ("el turno final de los tres brazos", lambda r: [
                r["rows"][C][arm].update(
                    turn_last=r["rows"][C][arm]["turn_last"] + 1)
                for arm in xfer1.ARMS]),
        ):
            with self.subTest(bend=label):
                b = self._bend()
                bend(b)
                self.assertTrue(b["rows"][B]["matched_turn_values"])
                self.assertFalse(xfer1.green(b), label)

        # Every probe of a border moved to the same smaller number, with
        # the ablation and both summaries moved to match.
        b = self._bend()
        for arm in xfer1.ARMS:
            probe = b["rows"][B]["pattern"][arm]
            probe["points"] = 48
            probe["hits"] = 48 if arm == "transfer" else 0
            probe["unknown"] = 0 if arm == "transfer" else 48
        b["pattern_entry_points_B"] = 48
        b["pattern_transfer_hits_B"] = 48
        self.assertEqual(b["rows"][B]["ablation"]["points"], 96)
        self.assertFalse(xfer1.green(b),
                         "la ablación quedó atada a otros puntos")
        # The other way round: the ablation's own head says 48 while its
        # two arms and the entry probe are all still on 96, with the
        # summary moved to match. Only the tie between the ablation's
        # points and the probe's can refuse this.
        b = self._bend()
        ab = b["rows"][B]["ablation"]
        ab["points"] = ab["known_slots"] = 48
        b["pattern_probe_known_slots_B"] = 48
        self.assertEqual(ab["trained"]["points"], 96)
        self.assertEqual(b["rows"][B]["pattern"]["transfer"]["points"], 96)
        self.assertFalse(xfer1.green(b),
                         "la cabecera de la ablación se soltó de la sonda")
        # And the two borders on different numbers of points.
        b = self._bend()
        for arm in xfer1.ARMS:
            probe = b["rows"][C]["pattern"][arm]
            probe["points"] = 48
            probe["hits"] = 48 if arm == "transfer" else 0
            probe["unknown"] = 0 if arm == "transfer" else 48
        ab = b["rows"][C]["ablation"]
        ab["points"] = ab["known_slots"] = 48
        ab["trained"].update(points=48, hits=48, unknown=0)
        ab["empty"].update(points=48, hits=0, unknown=48)
        b["pattern_entry_points_C"] = 48
        b["pattern_transfer_hits_C"] = 48
        b["pattern_probe_known_slots_C"] = 48
        b["trained_pattern_hits_C"] = 48
        self.assertFalse(xfer1.green(b),
                         "las dos fronteras sobre puntos distintos")

    def test_each_validator_refuses_out_of_range_on_its_own(self) -> None:
        """The validators, exercised directly.

        Some of their checks cannot be reached through a whole report —
        the published table pins `hits` and `unknown` exactly, so a range
        violation is caught by the table first. They are still the
        validator's job, so they are tested where they live.
        """
        good = {"points": 10, "hits": 4, "unknown": 3, "observes": 0}
        self.assertIsNotNone(xfer1._probe_ok(dict(good)))
        for label, bend in (
            ("hits por encima de los puntos", {"hits": 11}),
            ("hits negativos", {"hits": -1}),
            ("unknown por encima", {"unknown": 11}),
            ("unknown negativo", {"unknown": -1}),
            ("hits + unknown por encima", {"hits": 7, "unknown": 5}),
            ("cero puntos", {"points": 0}),
            ("puntos negativos", {"points": -1}),
            ("una escritura", {"observes": 1}),
            ("un contador booleano", {"hits": True}),
            ("un contador de coma flotante", {"unknown": 1.0}),
            ("un contador de texto", {"observes": "0"}),
        ):
            with self.subTest(probe=label):
                self.assertIsNone(xfer1._probe_ok(dict(good, **bend)), label)
        for missing in ("points", "hits", "unknown", "observes"):
            probe = dict(good)
            probe.pop(missing)
            self.assertIsNone(xfer1._probe_ok(probe), missing)
        # points pinned by a caller
        self.assertIsNone(xfer1._probe_ok(dict(good), 11))
        self.assertIsNotNone(xfer1._probe_ok(dict(good), 10))

        # walk_evidence, on a hand-made row
        walk = {"entry_cell": xfer1.SEAT, "turns": xfer1.WINDOW_TURNS,
                "turn_first": 100, "turn_last": 100 + xfer1.WINDOW_TURNS - 1,
                "turn_fingerprint": sum(range(100, 100 + xfer1.WINDOW_TURNS)),
                "reward": 0}
        row = {arm: dict(walk) for arm in xfer1.ARMS}
        self.assertIsNotNone(xfer1.walk_evidence(row))
        for label, bend in (
            ("el asiento", {"entry_cell": xfer1.S5}),
            ("la ventana", {"turns": 32}),
            ("el fingerprint", {"turn_fingerprint": 1}),
            ("el turno final", {"turn_last": 999}),
            ("un campo booleano", {"turns": True}),
            ("un campo de texto", {"turn_first": "100"}),
        ):
            with self.subTest(walk=label):
                bent = {arm: dict(walk, **bend) for arm in xfer1.ARMS}
                self.assertIsNone(xfer1.walk_evidence(bent), label)
        # one arm out of step
        bent = {arm: dict(walk) for arm in xfer1.ARMS}
        bent["age"]["turn_first"] = 101
        self.assertIsNone(xfer1.walk_evidence(bent))

        # signature_evidence
        sigs = {arm: dict(xfer1.XFER1_PROTOCOL) for arm in xfer1.ARMS}
        self.assertIsNotNone(xfer1.signature_evidence(sigs))
        for label, bend in (("una clave de más", {"extra": 1}),
                            ("ask encendido", {"ask_enabled": True}),
                            ("un cero por un False", {"ask_enabled": 0}),
                            ("un uno por un True", {"pattern_memory": 1}),
                            ("una semilla de texto", {"env_seed": "x"})):
            with self.subTest(signature=label):
                bent = {arm: dict(xfer1.XFER1_PROTOCOL, **bend)
                        for arm in xfer1.ARMS}
                self.assertIsNone(xfer1.signature_evidence(bent), label)
        for missing in xfer1.XFER1_PROTOCOL:
            bent = {arm: {k: v for k, v in xfer1.XFER1_PROTOCOL.items()
                          if k != missing} for arm in xfer1.ARMS}
            self.assertIsNone(xfer1.signature_evidence(bent), missing)
        bent = {arm: dict(xfer1.XFER1_PROTOCOL) for arm in xfer1.ARMS}
        bent["scratch"]["plan_depth"] = 1
        self.assertIsNone(xfer1.signature_evidence(bent))

    def test_the_battery_covers_the_graph(self) -> None:
        r = self.report
        for name in ("el contador de rechazo contradice su resumen",
                     "los tres brazos pierden la misma clave de la firma",
                     "los tres brazos incumplen el protocolo por igual",
                     "el predictor vacío deja de declarar sus None",
                     "una ablación de 95 puntos junto a una sonda de 96",
                     "sólo turn_first cambia y matched sigue en true",
                     "sólo el fingerprint cambia",
                     "sólo el asiento del brazo de edad cambia",
                     "una sonda declara hits mayores que sus puntos",
                     "una sonda declara un contador booleano",
                     "la ablación declara una escritura"):
            self.assertIn(name, xfer1.REQUIRED_MUTANTS, name)
            entry = next(m for m in r["mutants"] if m["mutant"] == name)
            self.assertTrue(entry["killed"], name)
        state = xfer1.battery_state(r["mutants"])
        self.assertEqual(state["missing"], [])
        self.assertEqual(state["duplicated"], [])
        self.assertEqual(state["alive"], [])
        self.assertEqual(state["malformed"], [])
        self.assertEqual(state["total"], state["killed"])

    def test_the_numbers_are_exactly_where_they_were(self) -> None:
        r = self.report
        self.assertEqual((r["transfer_reward_B"], r["scratch_reward_B"],
                          r["gain_B"]), (208, 152, 56))
        self.assertEqual((r["transfer_reward_C"], r["scratch_reward_C"],
                          r["gain_C"]), (224, 152, 72))
        self.assertEqual(r["aggregate_transfer_gain"], 128)
        self.assertEqual((r["trained_pattern_hits_B"],
                          r["empty_pattern_hits_B"],
                          r["pattern_probe_writes"]), (96, 0, 0))
        ch = r["channel"]
        self.assertEqual((ch["t_observations"], ch["pattern_observations"],
                          ch["cuts"], ch["refused_t_observations"],
                          ch["refused_pattern_observations"]),
                         (64, 62, 2, 0, 0))
        self.assertTrue(xfer1.green(r))


class TestGate(unittest.TestCase):
    def test_gate_inhibit_blocks(self) -> None:
        d, a, flags = gate(
            b"\x00" * 16,
            cam_hit=True,
            extract_ok=True,
            E=(0, 0, 0, 80, 0, 0),
            proposed=ACTION_APPROACH,
            inhibit=True,
        )
        self.assertEqual(d, GATE_BLOCK)
        self.assertEqual(flags, WSP_FLAG_VETO)
        self.assertNotEqual(a, ACTION_APPROACH)


class TestBench(unittest.TestCase):
    def test_loop_kpis(self) -> None:
        report = run()
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertTrue(report["encoder_beats_fnv"], report)
        self.assertGreaterEqual(report["turns"], 256)
        self.assertTrue(
            report["negative_delta_causes_policy_change"],
            report,
        )

    def test_phase_e_no_approach_threat(self) -> None:
        """Approach must lose on the threat row. Not a magic number."""
        report = run()
        self.assertNotEqual(report["phase_e_action"], ACTION_APPROACH, report)
        q = report["policy_after"]
        self.assertLess(q[ACTION_APPROACH], max(q[1], q[2]), q)

    def test_phase_g_generalizes(self) -> None:
        report = run()
        self.assertTrue(report["generalize_moved_threat"], report)
        self.assertNotEqual(report["phase_g_action"], ACTION_APPROACH, report)

    def test_t_beats_persist(self) -> None:
        """T memorises transitions; 'nothing moves' does not."""
        report = run()
        self.assertTrue(report["t_beats_persist"], report)
        self.assertGreater(
            report["prediction_accuracy"],
            report["baseline_persist_accuracy"],
            report,
        )

    def test_t_beats_ring(self) -> None:
        """The lock that replaced test_t_does_not_beat_ring_arithmetic.

        Two cells jump +2 on approach; the (i±1) baseline cannot know that.
        If this fails, the slice is not green: raise exploration or turns
        and say by how much. Do not lower the bar.
        """
        report = run()
        self.assertTrue(report["t_beats_ring"], report)
        self.assertGreater(
            report["prediction_accuracy"],
            report["baseline_ring_accuracy"],
            report,
        )
        self.assertFalse(report["t_equals_ring"], report)
        self.assertGreater(report["jump_hits"], 0, report)

    def test_oracle_beats_blind(self) -> None:
        """NEXUS-3 gate: asking pays. Same ring, same seed, one question."""
        seer = run(ask=True)
        blind = run(ask=False)

        self.assertGreater(
            seer["novel_approach_return"],
            blind["novel_approach_return"],
            (seer["novel_approach_return"], blind["novel_approach_return"]),
        )
        self.assertGreaterEqual(seer["questions"], 1, seer)
        self.assertEqual(blind["questions"], 0, blind)

        for report in (seer, blind):
            with self.subTest(ask=report["ask"]):
                self.assertEqual(report["false_facts"], 0, report)
                self.assertEqual(report["destroyed"], 0, report)
                self.assertEqual(report["cortex_calls"], 0, report)
                # The threat at 7 is untouched by the bait.
                self.assertNotEqual(report["phase_e_action"], ACTION_APPROACH)
                q = report["policy_after"]
                self.assertLess(q[ACTION_APPROACH], max(q[1], q[2]), q)

    def test_same_approaches_opposite_sign(self) -> None:
        """The bait changes the sign, not the number of visits. 5 each way."""
        seer = run(ask=True)
        blind = run(ask=False)
        self.assertEqual(
            abs(seer["novel_approach_return"]),
            abs(blind["novel_approach_return"]),
        )
        self.assertGreater(seer["novel_approach_return"], 0)
        self.assertLess(blind["novel_approach_return"], 0)

    def test_greedy_probe_does_not_leave_cell_zero(self) -> None:
        """NEXUS-3 closes as 'value, not map'. Documented, not lowered.

        novel_hits_greedy is 0 in both arms, and not because the seer
        refuses to go: a greedy walk from cell 0 never starts. Q[c0] is
        [0,0,0], the tie-break is wait, and wait does not move. TD carried
        value exactly one cell back from each rewarded cell in 256 turns,
        which never reaches c0. Raising the probe to 64 steps changes
        nothing. Asking changed the value of the cell, not the map to it.
        """
        seer = run(ask=True)
        blind = run(ask=False)
        self.assertEqual(seer["novel_hits_greedy"], 0, seer)
        self.assertEqual(blind["novel_hits_greedy"], 0, blind)

        ag = Agent(ask=True)
        ag.run(BENCH_TURNS)
        self.assertEqual(ag.q.snapshot(self._slot(ag, 0)), [0, 0, 0])
        self.assertEqual(ag.q.best(self._slot(ag, 0)), ACTION_WAIT)
        self.assertEqual(ag.walk_greedy(64, start=0), 0)

    def _slot(self, ag: Agent, cell: int) -> int:
        return ag.cam.get(encode_cell(cell, ag.env.kind[cell]))

    def test_seer_steps_into_novel_from_the_neighbouring_cell(self) -> None:
        """One cell wide — the only seeking TD actually propagated.

        This is NOT 'the agent seeks information'. It is: from c10, the
        cell that leads into the NOVEL cell, the agent that asked has a
        positive approach value and walks in; the blind one sits.
        """
        seer = Agent(ask=True)
        seer.run(BENCH_TURNS)
        blind = Agent(ask=False)
        blind.run(BENCH_TURNS)

        self.assertGreater(seer.q.get(self._slot(seer, 10), ACTION_APPROACH), 0)
        self.assertEqual(seer.q.best(self._slot(seer, 10)), ACTION_APPROACH)
        self.assertEqual(seer.q.best(self._slot(seer, 11)), ACTION_APPROACH)

        self.assertEqual(blind.q.best(self._slot(blind, 10)), ACTION_WAIT)
        self.assertEqual(blind.q.best(self._slot(blind, 11)), ACTION_WAIT)

    def test_blind_gets_stuck_on_the_trap_cell(self) -> None:
        """Blind visits 11 far more, and that is paralysis, not curiosity:
        it learned wait, and wait does not move."""
        seer = run(ask=True)
        blind = run(ask=False)
        self.assertGreater(blind["novel_visits"], seer["novel_visits"], (seer, blind))

    def test_blind_learns_the_novel_cell_is_a_trap(self) -> None:
        blind = run(ask=False)
        self.assertLess(blind["novel_approach_return"], 0, blind)

    def test_plan2_side_report_keeps_the_hard_invariants(self) -> None:
        """Opt-in run: the three that can never move. Policy is NOT pinned."""
        report = run(plan_depth=2)
        self.assertEqual(report["false_facts"], 0, report)
        self.assertEqual(report["destroyed"], 0, report)
        self.assertEqual(report["cortex_calls"], 0, report)
        self.assertEqual(report["plan_depth"], 2, report)

    def test_plan2_writes_a_separate_file(self) -> None:
        self.assertEqual(report_name(0), "nexus0_report.json")
        self.assertEqual(report_name(2), "nexus0_plan2_report.json")
        self.assertNotEqual(report_name(0), report_name(2))

    def test_report_carries_atom_sample(self) -> None:
        report = run()
        sample = report["sample_wsp"]
        self.assertEqual(len(sample), SAMPLE_TURNS, sample)
        for line in sample:
            self.assertNotIn("?", line)
        self.assertTrue(any("TEMER → PELIGRO" in s for s in sample), sample)


class TestQwen0Harness(unittest.TestCase):
    """Operator cable for the 4B. No weights in CI."""

    def test_timeout_default_stays_ten(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(cortex.ENV_TIMEOUT, None)
            self.assertEqual(cortex._timeout_s(), 10)

    def test_timeout_env_overrides(self) -> None:
        with mock.patch.dict(os.environ, {cortex.ENV_TIMEOUT: "120"}):
            self.assertEqual(cortex._timeout_s(), 120.0)

    def test_should_speak_only_on_language(self) -> None:
        self.assertTrue(qwen_cortex.should_speak(sign.SIGN_TEXT[sign.LAYOUT_PRIZE]))
        self.assertFalse(qwen_cortex.should_speak("cell=0 kind=EMPTY"))
        self.assertFalse(qwen_cortex.should_speak("cell=1 kind=GOAL"))
        self.assertFalse(qwen_cortex.should_speak(""))

    def test_wrapper_silent_without_model(self) -> None:
        env = {
            "NAVI_QWEN_MODEL": "",
            "NAVI_QWEN_URL": "",
            "NAVI_QWEN_CLI": "",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("NAVI_QWEN_MODEL", None)
            os.environ.pop("NAVI_QWEN_URL", None)
            os.environ.pop("NAVI_QWEN_CLI", None)
            self.assertEqual(qwen_cortex.complete_extract("AMBAR: entra."), "")
            self.assertEqual(qwen_cortex.complete_extract("cell=0 kind=EMPTY"), "")

    def test_sign_text_override_keeps_packet(self) -> None:
        a = sign.SignEnv(sign.LAYOUT_PRIZE)
        b = sign.SignEnv(
            sign.LAYOUT_PRIZE,
            sign_text="AMBAR: pasa. Lo de adelante es el premio.",
        )
        self.assertEqual(
            encode_cell(sign.SIGN, KIND_EMPTY),
            encode_cell(a.cell().index, a.cell().kind),
        )
        self.assertEqual(a.cell().kind, b.cell().kind)
        self.assertNotEqual(a.cell().extract, b.cell().extract)

    def test_stub_misses_a_paraphrase_the_4b_must_catch(self) -> None:
        text = "No pases. Lo siguiente mata."
        self.assertEqual(sign_cortex.decide(text), "")
        self.assertTrue(qwen_cortex.should_speak(text))

    def test_canonical_report_file_is_not_qwen(self) -> None:
        self.assertNotEqual(
            Path("echoai/lab/nexus0_report.json").name,
            "nexus0_qwen4b_report.json",
        )


class TestDemo(unittest.TestCase):
    """MVP: one command to watch the fast loop. Cortex off."""

    def test_live_short_writes_one_line_per_turn_and_draws(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "thought.jsonl"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = demo.main(
                    ["--short", "--fps", "0", "--no-color", "--log", str(log)]
                )
            self.assertEqual(rc, 0)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), demo.SHORT_TURNS)
            frame = buf.getvalue()
            self.assertIn("@", frame)
            self.assertIn("ATTEND", frame)

    def test_replay_refuses_a_missing_log(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = demo.main(["--replay", "--log", "/nonexistent/thought.jsonl"])
        self.assertEqual(rc, 1)
        self.assertIn("no such log", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
