"""Bounded interventional influence map. Public observations/receipts only.

Restoration receipts are trusted experimental provenance, not a deduction
from WSP equality or a cryptographic proof. The separate auditor checks them.
No body ownership, physics, family labels or evaluator enter this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from echoai.core.cam import Cam
from echoai.core.qn import simhash16
from echoai.core.wsp import E_NAMES, unpack
from echoai.echo4.sensation import checked_packet

CHANNELS = (8, 9)
MASK = (1 << 8) | (1 << 9)
ALL = (1 << 16) - 1
ROW_CAPACITY = 128
PAIR_CAPACITY = 4096


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError("invalid bounded integer")


def code(packet: bytes, channel: int) -> int:
    value = packet[channel]
    return value - 256 if value >= 128 else value


@dataclass(frozen=True)
class Trial:
    token: int
    intended: int
    packets: tuple[bytes, bytes, bytes]
    ticks: tuple[int, int, int]
    applied: tuple[int | None, int | None]
    gates: tuple[int, int]
    terminal: tuple[bool, bool, bool]


@dataclass(frozen=True)
class Pair:
    identifier: int
    restored: bool
    common_schedule: bool
    treatment: Trial
    reference: Trial


def validate(pair: Pair) -> int:
    """Validate everything before mutation; return first confirmed action tick."""
    if type(pair) is not Pair:
        raise ValueError("requires Pair")
    integer(pair.identifier, 1, (1 << 31) - 1)
    if pair.restored is not True or pair.common_schedule is not True:
        raise ValueError("missing matched restoration receipt")
    for arm in (pair.treatment, pair.reference):
        if type(arm) is not Trial:
            raise ValueError("requires Trial")
        integer(arm.token, 1, (1 << 31) - 1)
        integer(arm.intended, 0, 2)
        if arm.token != pair.identifier:
            raise ValueError("mismatched trial token")
        for values, length in ((arm.packets, 3), (arm.ticks, 3),
                               (arm.applied, 2), (arm.gates, 2), (arm.terminal, 3)):
            if type(values) is not tuple or len(values) != length:
                raise ValueError("invalid trial shape")
        for packet in arm.packets:
            checked_packet(packet)
        for tick in arm.ticks:
            integer(tick, 0, 2)
        if arm.ticks != (0, 1, 2):
            raise ValueError("stale or incomplete capture")
        for action in arm.applied:
            integer(action, 0, 2)
        for decision in arm.gates:
            integer(decision, 0, 2)
        if any(type(v) is not bool for v in arm.terminal) or any(arm.terminal):
            raise ValueError("terminal or malformed trial")
        if arm.gates != (0, 0):
            raise ValueError("veto/modified action is not an executed intervention")
    treatment, reference = pair.treatment, pair.reference
    if treatment.intended not in (0, 1) or reference.intended != 2:
        raise ValueError("requires active intervention versus wait")
    if treatment.packets[0] != reference.packets[0]:
        raise ValueError("unequal initial observations")
    if reference.applied != (2, 2):
        raise ValueError("reference must wait")
    if treatment.applied not in ((treatment.intended, 2), (2, treatment.intended)):
        raise ValueError("requires exactly one confirmed pulse")
    return treatment.applied.index(treatment.intended) + 1


@dataclass(frozen=True)
class Estimate:
    influence: int = 0
    no_observed_effect: int = 0
    unknown: int = ALL
    signs: tuple[int, int] = (0, 0)
    first_effect: tuple[int, int] = (0, 0)


class BoundaryMap:
    """128 rows × 2 channels × 2 lags × 3 integer sign counters, at most.

    Keys use the original CAM. Estimates never become CAM facts. Limits
    reject new evidence, without eviction or a fallback to slot zero.
    """

    def __init__(self, cam: Cam, *, capacity: int = ROW_CAPACITY):
        if not isinstance(cam, Cam):
            raise ValueError("requires original CAM")
        integer(capacity, 1, ROW_CAPACITY)
        self.cam = cam
        self.capacity = capacity
        self.rows: dict[tuple[int, int], list[list[list[int]]]] = {}
        self.pairs = 0
        self.last_identifier = 0
        self.frozen = False

    def observe(self, pair: Pair) -> None:
        applied_at = validate(pair)
        if self.frozen:
            raise RuntimeError("map is frozen")
        if pair.identifier <= self.last_identifier:
            raise ValueError("repeated/out-of-order pair")
        if self.pairs >= PAIR_CAPACITY:
            raise OverflowError("pair budget exhausted")
        initial = pair.treatment.packets[0]
        slot = self.cam.get(initial)
        action = pair.treatment.intended
        key = (slot, action)
        if key not in self.rows and len(self.rows) >= self.capacity:
            raise OverflowError("map capacity exhausted")
        if slot < 0:
            if self.cam.used >= len(self.cam.slot):
                raise OverflowError("CAM capacity exhausted")
            e = unpack(initial)["E"]
            slot = self.cam.put(initial, simhash16(initial), 0,
                                tuple(e[name] for name in E_NAMES), has_fact=0,
                                source="boundary-observation", kind="observation", key=initial)
            if slot < 0:
                raise OverflowError("CAM allocation failed")
            key = (slot, action)
        row = self.rows.setdefault(key, [[[0, 0, 0] for _ in range(2)] for _ in CHANNELS])
        for j, channel in enumerate(CHANNELS):
            for tick in range(applied_at, 3):
                t, r = pair.treatment.packets, pair.reference.packets
                delta = (code(t[tick], channel) - code(t[0], channel)
                         - code(r[tick], channel) + code(r[0], channel))
                sign = (delta > 0) - (delta < 0)
                row[j][tick - 1][sign + 1] += 1
        self.pairs += 1
        self.last_identifier = pair.identifier

    def estimate(self, packet: bytes, action: int) -> Estimate:
        checked_packet(packet)
        integer(action, 0, 1)
        row = self.rows.get((self.cam.get(packet), action))
        if row is None:
            return Estimate()
        influence = no_effect = 0
        signs, lags = [0, 0], [0, 0]
        for j, channel in enumerate(CHANNELS):
            states = []
            for negative, zero, positive in row[j]:
                total = negative + zero + positive
                state = None
                if total >= 8:
                    if zero == total:
                        state = 0
                    elif negative == 0 and 8 * positive >= 7 * total:
                        state = 1
                    elif positive == 0 and 8 * negative >= 7 * total:
                        state = -1
                states.append(state)
            # Final horizon must have enough consistent evidence. Ignore a
            # never-observed pre-application lag, but not contradictory data.
            if states[1] is None or any(s is None and sum(c) for s, c in zip(states, row[j])):
                continue
            effects = [(i + 1, s) for i, s in enumerate(states) if s not in (None, 0)]
            if effects and len({s for _, s in effects}) == 1:
                influence |= 1 << channel
                lags[j], signs[j] = effects[0]
            elif not effects:
                no_effect |= 1 << channel
        return Estimate(influence, no_effect, ALL ^ (influence | no_effect), tuple(signs), tuple(lags))

    def freeze(self) -> None:
        self.frozen = True

    def model_hash(self) -> str:
        state = {"capacity": self.capacity, "pairs": self.pairs,
                 "last_identifier": self.last_identifier,
                 "rows": sorted((key, value) for key, value in self.rows.items())}
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def resources(self) -> dict:
        return {"rows": len(self.rows), "capacity": self.capacity, "pairs": self.pairs,
                "pair_capacity": PAIR_CAPACITY, "sign_counters": 12 * len(self.rows),
                "counter_capacity": 12 * self.capacity,
                "cam_shared": True, "retained_trials": 0}


def public_record(pair: Pair) -> dict:
    result = asdict(pair)
    for name in ("treatment", "reference"):
        result[name]["packets"] = [p.hex() for p in result[name]["packets"]]
    return result
