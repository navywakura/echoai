"""Bounded local history of existing WSP observations, not a new bus.

No simulator, private physiology, CAM allocation, policy or oracle here.
History length means past executed transitions, not number of packets.
"""
from __future__ import annotations

from echoai.core.wsp import unpack

from echoai.nexus0.constants import N_ACTIONS, WSP_BYTES

HISTORY_STEPS = (0, 2, 4)
RECORD_BYTES = WSP_BYTES + 1


def checked_packet(packet: bytes) -> None:
    if type(packet) is not bytes or len(packet) != WSP_BYTES:
        raise ValueError("observation must be immutable WSP bytes of length 16")


class SensoryHistory:
    """At most 84 payload bytes; no hidden accumulating trace or auto-reset.

    Layout is a private working-memory buffer of unchanged packets separated
    by executed action IDs. It is never emitted as a WSP packet.
    """

    __slots__ = ("_depth", "_buffer", "_count", "_started")

    def __init__(self, depth: int):
        if type(depth) is not int or depth not in HISTORY_STEPS:
            raise ValueError("history depth must be 0, 2 or 4")
        self._depth = depth
        self._buffer = bytearray(WSP_BYTES + RECORD_BYTES * depth)
        self._count = 0
        self._started = False

    @property
    def depth(self) -> int:
        return self._depth

    @property
    def steps(self) -> int:
        return self._count

    @property
    def payload_bytes(self) -> int:
        return len(self._buffer)

    def start(self, observation: bytes) -> None:
        """Explicit new history/life; validation precedes all mutation."""
        checked_packet(observation)
        self._buffer[:] = bytes(len(self._buffer))
        self._buffer[:WSP_BYTES] = observation
        self._count = 0
        self._started = True

    def advance(self, executed_action: int, observation: bytes) -> None:
        checked_packet(observation)
        if type(executed_action) is not int or not 0 <= executed_action < N_ACTIONS:
            raise ValueError("executed action must be an integer in 0..2")
        if not self._started:
            raise RuntimeError("start the history before advancing")
        if self._depth == 0:
            self._buffer[:] = observation
            return
        if self._count == self._depth:
            # Same-size assignments keep storage bounded; these host copies
            # are not a claim of allocation-free C execution.
            self._buffer[:-RECORD_BYTES] = self._buffer[RECORD_BYTES:]
            offset = len(self._buffer) - RECORD_BYTES
        else:
            offset = WSP_BYTES + RECORD_BYTES * self._count
            self._count += 1
        self._buffer[offset] = executed_action
        self._buffer[offset + 1:offset + RECORD_BYTES] = observation

    def snapshot(self) -> bytes:
        if not self._started:
            raise RuntimeError("history has not started")
        return bytes(self._buffer[:WSP_BYTES + RECORD_BYTES * self._count])

    def sensory_delta(self) -> tuple[int, int]:
        """Oldest-to-current U/B code differences, NOT exact H/theta rates."""
        raw = self.snapshot()
        before = unpack(raw[:WSP_BYTES])["E"]
        after = unpack(raw[-WSP_BYTES:])["E"]
        return after["U"] - before["U"], after["B"] - before["B"]
