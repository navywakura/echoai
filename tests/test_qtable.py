#!/usr/bin/env python3
"""Q-table: negative δ flips policy. No env required."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.constants import ACTION_APPROACH, R_THREAT
from echoai.nexus0.qtable import QTable


class TestQTable(unittest.TestCase):
    def test_negative_delta_flips_policy(self) -> None:
        q = QTable()
        s = 7
        q.set(s, ACTION_APPROACH, 40)
        self.assertEqual(q.best(s), ACTION_APPROACH)
        for _ in range(24):
            q.update(s, ACTION_APPROACH, R_THREAT, s)
        self.assertNotEqual(q.best(s), ACTION_APPROACH)
        self.assertLess(q.get(s, ACTION_APPROACH), 40)

    def test_clip(self) -> None:
        q = QTable()
        q.set(0, 0, 200)
        self.assertEqual(q.get(0, 0), 127)
        q.set(0, 1, -200)
        self.assertEqual(q.get(0, 1), -127)

    def test_size(self) -> None:
        q = QTable()
        self.assertEqual(len(q.q), 4096)
        self.assertEqual(len(q.q[0]), 3)

    def test_terminal_does_not_borrow_value_from_respawn(self) -> None:
        for options in ({}, {"remainder": True}, {"trace": True},
                        {"n_actions": 4}):
            with self.subTest(options=options):
                q = QTable(**options)
                q.set(9, 0, 127)  # A valuable respawn must not reward death.
                delta = q.update(7, 0, -16, 9, terminal=True)
                self.assertEqual(delta, -16)
                self.assertEqual(q.get(7, 0), -4)
                self.assertEqual(q.get(9, 0), 127)

    def test_negative_reward_is_not_automatically_terminal(self) -> None:
        q = QTable()
        q.set(9, 0, 80)
        self.assertEqual(q.update(7, 0, -16, 9), 54)
        self.assertEqual(q.get(7, 0), 13)

    def test_terminal_pays_traces_then_prevents_cross_life_credit(self) -> None:
        q = QTable(trace=True)
        q.update(1, 0, 0, 2)
        q.update(2, 0, -16, 9, terminal=True)
        self.assertLess(q.get(1, 0), 0)
        self.assertEqual(q.get(2, 0), -4)
        self.assertEqual(q._active, [])
        self.assertFalse(any(any(row) for row in q.z))
        previous_life = (q.row(1), q.row(2))
        q.update(9, 0, 16, 10)
        self.assertEqual((q.row(1), q.row(2)), previous_life)

    def test_terminal_preserves_fractional_learning_between_lives(self) -> None:
        q = QTable(remainder=True)
        q.update(1, 0, -3, 9, terminal=True)
        self.assertEqual(q.get(1, 0), 0)
        self.assertEqual(q.rem[1][0], -3)
        q.update(1, 0, -3, 9, terminal=True)
        self.assertEqual(q.get(1, 0), -1)
        self.assertEqual(q.rem[1][0], -2)


if __name__ == "__main__":
    unittest.main()
