"""Integer sensory prediction using the existing CAM, T and PATTERN-0.

Only public WSP packets and executed actions cross this API. No physics,
body registers, evaluator, seeds, viability or policy are imported here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json

from echoai.core.cam import Cam
from echoai.core.qn import simhash16
from echoai.core.wsp import E_NAMES, unpack
from echoai.nexus0.constants import N_SLOTS
from echoai.nexus0.pattern import PatternMemory
from echoai.nexus0.world import World
from echoai.echo4.sensation import SensoryHistory, checked_packet

CONTEXT_CAPACITY = 2048
PATTERN_CAPACITY = 8191
MIN_HITS = 8
COUNTER_MAX = (1 << 32) - 1


def _action(value: int) -> None:
    if type(value) is not int or not 0 <= value < 3:
        raise ValueError("executed action must be an integer in 0..2")


@dataclass(frozen=True)
class Prediction:
    packet: bytes | None
    slot: int | None
    confidence: int
    source: str


@dataclass(frozen=True)
class Sensation:
    label: int  # 0 expected, 1 small deviation, 2 large, 3 insufficient evidence
    error: int | None
    exact: bool
    confidence: int
    source: str


def assess(prediction: Prediction, actual: bytes) -> Sensation:
    checked_packet(actual)
    if prediction.packet is None:
        return Sensation(3, None, False, prediction.confidence, prediction.source)
    expected = prediction.packet
    p, a = unpack(expected)["E"], unpack(actual)["E"]
    error = abs(p["U"] - a["U"]) + abs(p["B"] - a["B"])
    # Non-sensory fields cannot change unnoticed just because U/B agree.
    error += sum(expected[i] != actual[i] for i in range(16) if i not in (8, 9))
    label = 3 if prediction.confidence < 3 else (0 if error == 0 else 1 if error <= 32 else 2)
    return Sensation(label, error, expected == actual, prediction.confidence, prediction.source)


class SensationPredictor:
    """An opt-in extension of T, with no parallel CAM or unbounded history.

    `update_base=False` is for Agent integration: its own turn already learns
    T from the same consequence. Standalone training uses update_base=True.
    Model state freezes; the sensory window and pending forecast still move.
    """

    def __init__(self, cam: Cam, world: World, *, depth: int = 2,
                 context_capacity: int = CONTEXT_CAPACITY,
                 pattern_capacity: int = PATTERN_CAPACITY,
                 update_base: bool = True):
        if not isinstance(cam, Cam) or not isinstance(world, World) or world.n_actions != 3:
            raise ValueError("requires the existing CAM and a three-action T")
        if type(context_capacity) is not int or not 1 <= context_capacity <= N_SLOTS:
            raise ValueError("context capacity must be in 1..4096")
        if type(pattern_capacity) is not int or not 1 <= pattern_capacity <= PATTERN_CAPACITY:
            raise ValueError("invalid pattern capacity")
        if type(update_base) is not bool:
            raise ValueError("update_base must be bool")
        self.history = SensoryHistory(depth)
        self.cam, self.world = cam, world
        self.memory = PatternMemory(capacity=pattern_capacity, min_hits=MIN_HITS)
        self.context_capacity = context_capacity
        self.contexts: dict[bytes, int] = {}
        self.context_dropped = 0
        self.cam_dropped = 0
        self.update_base = update_base
        self.frozen = False
        self.pending: tuple[int, Prediction] | None = None

    def start(self, packet: bytes) -> None:
        checked_packet(packet)
        if self.pending is not None:
            raise RuntimeError("cannot reset an unconsumed prediction")
        self.history.start(packet)

    def freeze(self) -> None:
        if not self.update_base:
            raise RuntimeError("external Agent owns T updates; standalone predictor required for frozen exams")
        if self.pending is not None:
            raise RuntimeError("finish the pending transition before freezing")
        self.frozen = True

    def _slot(self, packet: bytes, *, create: bool = False) -> int:
        slot = self.cam.get(packet)
        if slot >= 0 or not create:
            return slot
        if self.cam.used >= N_SLOTS:
            self.cam_dropped = min(COUNTER_MAX, self.cam_dropped + 1)
            return -1
        e = unpack(packet)["E"]
        return self.cam.put(packet, simhash16(packet), 0,
                            tuple(e[name] for name in E_NAMES), has_fact=0,
                            source="sensation-observation", kind="observation", key=packet)

    def anticipate(self, executed_action: int) -> Prediction:
        _action(executed_action)
        if self.pending is not None:
            raise RuntimeError("prediction already pending")
        history = self.history.snapshot()
        slot = self._slot(history[-16:])
        result = Prediction(None, None, 0, "unknown")
        if slot >= 0:
            context = self.contexts.get(history)
            nxt = None
            if self.history.depth and self.history.steps == self.history.depth and context is not None:
                nxt = self.memory.predict(context, slot, executed_action)
            if nxt is not None:
                result = Prediction(self.cam.slot[nxt].wsp, nxt, 3, "history")
            else:
                nxt = self.world.predict(slot, executed_action)
                if nxt is not None:
                    result = Prediction(self.cam.slot[nxt].wsp, nxt,
                                        self.world.conf(slot, executed_action), "t")
        self.pending = (executed_action, result)
        return result

    def observe(self, packet: bytes) -> Sensation:
        checked_packet(packet)
        if self.pending is None:
            raise RuntimeError("consequence requires a previous prediction")
        action, prediction = self.pending
        result = assess(prediction, packet)  # Score BEFORE any learning.
        history = self.history.snapshot()
        if not self.frozen:
            slot = self._slot(history[-16:], create=True)
            nxt = self._slot(packet, create=True)
            if slot >= 0 and nxt >= 0:
                if self.update_base:
                    self.world.observe(slot, action, nxt)
                    self.world.conflicts = min(COUNTER_MAX, self.world.conflicts)
                    self.world.inv_dropped = min(COUNTER_MAX, self.world.inv_dropped)
                if self.history.depth and self.history.steps == self.history.depth:
                    context = self.contexts.get(history)
                    if context is None:
                        if len(self.contexts) < self.context_capacity:
                            context = len(self.contexts)
                            self.contexts[history] = context
                        else:
                            self.context_dropped = min(COUNTER_MAX, self.context_dropped + 1)
                    if context is not None:
                        self.memory.observe(context, slot, action, nxt)
                        for name in ("observations", "conflicts", "dropped"):
                            setattr(self.memory, name, min(COUNTER_MAX, getattr(self.memory, name)))
        self.history.advance(action, packet)
        self.pending = None
        return result

    def model_state(self) -> dict:
        """All learned state, excluding current window and pending forecast."""
        return {
            "depth": self.history.depth, "context_capacity": self.context_capacity,
            "pattern_capacity": self.memory.capacity, "min_hits": self.memory.min_hits,
            "cam": [(i, asdict(s)) for i, s in enumerate(self.cam.slot) if s.occupied],
            "cam_used": self.cam.used, "cam_destroyed": self.cam.destroyed,
            "cam_keys": sorted((key.hex(), slot) for key, slot in self.cam.key_index.items()),
            "t": vars(self.world),
            "pattern": vars(self.memory),
            "contexts": sorted((key.hex(), value) for key, value in self.contexts.items()),
            "context_dropped": self.context_dropped, "cam_dropped": self.cam_dropped,
        }

    def model_hash(self) -> str:
        raw = json.dumps(self.model_state(), sort_keys=True, separators=(",", ":"),
                         default=lambda value: value.hex() if isinstance(value, bytes) else None)
        return hashlib.sha256(raw.encode()).hexdigest()

    def resources(self) -> dict:
        # CPython reachable-object estimate, not RSS, C packing or NPU energy.
        import sys
        seen = set()

        def size(obj):
            identity = id(obj)
            if identity in seen:
                return 0
            seen.add(identity)
            total = sys.getsizeof(obj)
            if isinstance(obj, dict):
                total += sum(size(k) + size(v) for k, v in obj.items())
            elif isinstance(obj, (list, tuple)):
                total += sum(size(v) for v in obj)
            elif hasattr(obj, "__dict__"):
                total += size(vars(obj))
            return total

        return {"cam_capacity": N_SLOTS, "cam_used": self.cam.used,
                "context_capacity": self.context_capacity, "contexts": len(self.contexts),
                "context_key_bytes_limit": self.context_capacity * self.history.payload_bytes,
                "context_key_bytes_used": sum(map(len, self.contexts)),
                "context_dropped": self.context_dropped, "cam_dropped": self.cam_dropped,
                "pattern_capacity": self.memory.capacity, "patterns": self.memory.size,
                "pattern_dropped": self.memory.dropped, "history_bytes": self.history.payload_bytes,
                "python_model_bytes": size((self.cam, self.world, self.memory, self.contexts))}
