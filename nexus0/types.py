"""NEXUS-0 frozen types. Integers only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from echoai.nexus0.constants import (
    ACTION_AVOID,
    ACTION_WAIT,
    GATE_BLOCK,
    GATE_MODIFY,
    GATE_OK,
    N_ACTIONS,
)

E6 = Tuple[int, int, int, int, int, int]


def clip_i8(x: int) -> int:
    if x < -127:
        return -127
    if x > 127:
        return 127
    return int(x)


def clip_u8(x: int) -> int:
    if x < 0:
        return 0
    if x > 255:
        return 255
    return int(x)


@dataclass
class State:
    slot: int
    vertex: int
    wsp: bytes
    E: E6
    ham: int
    novelty: int


@dataclass
class StepResult:
    action: int
    decision: int  # GATE_OK / MODIFY / BLOCK
    reward: int
    slot: int
    slot_next: int
    vertex: int
    vertex_next: int
    surprise: int
    novelty: int
    extract_ok: int
    veto: int


@dataclass
class Metrics:
    turns: int = 0
    verify: int = 0
    unknown: int = 0
    false_facts: int = 0
    cortex_calls: int = 0
    destroyed: int = 0
    ham_sum: int = 0
    pred_hits: int = 0
    pred_known: int = 0
    pred_ham_sum: int = 0
    action_pos: int = 0
    store_priority: int = 0
    # Baselines scored on the same turns as T, i.e. denominator pred_known.
    persist_hits: int = 0
    ring_hits: int = 0
    jump_hits: int = 0  # times approach was taken from a JUMP cell
    questions: int = 0  # NEXUS-3 PREGUNTAR packets emitted
    cortex_rejected: int = 0  # slow-clock replies refused by parse_reply
    # CORTEX-1: turns where the action handed to the gate came from the
    # slow clock instead of Q. PREGUNTAR is not counted here — asking is
    # not deciding.
    cortex_actions: int = 0
    oracle_rejected: int = 0  # answers refused by oracle.accept (VERIFY)
    novel_approach_return: int = 0  # summed r of approach on the NOVEL cell
    novel_visits: int = 0  # turns started standing on the NOVEL cell
    # NEXUS-4g — three different facts about one turn, counted apart.
    # N  the origin slot had never been hit before this turn (CAM miss).
    #    KIND_NOVEL is a kind of cell, not a kind of ignorance: after the
    #    first hit, standing on cell 11 again is not a miss.
    # S  T had a prediction and it was wrong. T_MISS (no prediction) is
    #    ignorance, not surprise, and is not counted here. Slot inequality,
    #    not Hamming — the Hamming distance stays in
    #    prediction_hamming_error, where it already was.
    # δ  the integer q.update() returns, counted when non-zero.
    cam_misses: int = 0
    surprises: int = 0
    deltas: int = 0
    surprise_known: int = 0  # S and not N — a known place, a wrong map
    novel_no_surprise: int = 0  # N and not S — a new place, nothing to be wrong about
    delta_only: int = 0  # δ moved with neither of the above

    def mean_ham(self) -> float:
        return (self.ham_sum / self.turns) if self.turns else 0.0

    def prediction_accuracy(self) -> float:
        return (self.pred_hits / self.pred_known) if self.pred_known else 0.0

    def persist_accuracy(self) -> float:
        return (self.persist_hits / self.pred_known) if self.pred_known else 0.0

    def ring_accuracy(self) -> float:
        return (self.ring_hits / self.pred_known) if self.pred_known else 0.0

    def as_dict(self) -> dict:
        return {
            "turns": self.turns,
            "verify": self.verify,
            "unknown": self.unknown,
            "false_facts": self.false_facts,
            "cortex_calls": self.cortex_calls,
            "destroyed": self.destroyed,
            "mean_ham": self.mean_ham(),
            "prediction_accuracy": self.prediction_accuracy(),
            "prediction_hamming_error": (
                (self.pred_ham_sum / self.pred_known) if self.pred_known else 0.0
            ),
            "prediction_known_turns": self.pred_known,
            "baseline_persist_accuracy": self.persist_accuracy(),
            "baseline_ring_accuracy": self.ring_accuracy(),
            # Integer comparisons: same denominator, so counts decide.
            "t_beats_persist": self.pred_hits > self.persist_hits,
            "t_equals_ring": self.pred_hits == self.ring_hits,
            "t_beats_ring": self.pred_hits > self.ring_hits,
            "jump_hits": self.jump_hits,
            "questions": self.questions,
            "cortex_rejected": self.cortex_rejected,
            "cortex_actions": self.cortex_actions,
            "oracle_rejected": self.oracle_rejected,
            "novel_approach_return": self.novel_approach_return,
            "novel_visits": self.novel_visits,
            "cam_misses": self.cam_misses,
            "surprises": self.surprises,
            "deltas": self.deltas,
            "surprise_known": self.surprise_known,
            "novel_no_surprise": self.novel_no_surprise,
            "delta_only": self.delta_only,
            "action_success": (self.action_pos / self.turns) if self.turns else 0.0,
        }


def action_name(a: int) -> str:
    return ("approach", "avoid", "wait")[int(a) % N_ACTIONS]


def gate_name(d: int) -> str:
    return {GATE_OK: "OK", GATE_MODIFY: "MODIFY", GATE_BLOCK: "BLOCK"}.get(d, "?")


def default_e() -> E6:
    return (0, 10, 0, 15, 10, 0)


__all__ = [
    "E6",
    "State",
    "StepResult",
    "Metrics",
    "clip_i8",
    "clip_u8",
    "action_name",
    "gate_name",
    "default_e",
    "ACTION_AVOID",
    "ACTION_WAIT",
]
