"""
NAVI 10 — CAM / memoria asociativa Heap-0.

Tabla estática de 4096 ranuras × 32 B. Mapea un paquete WSP de 16 B
(y un vértice Q8×Q8 + latencia) sin malloc. En silicio sería un CAM
paralelo; aquí un pase acotado por SLOTS. KCC: destroyed=0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from echoai.core.qn import (
    CAM_SLOTS,
    HAM_LIMIT,
    SLOT_FLAG_ACTION,
    SLOT_FLAG_INHIBIT,
    WSP_BYTES,
    combined_score,
    fnv32,
    hamming16,
)


@dataclass
class CamSlot:
    wsp: bytes = b"\x00" * WSP_BYTES
    vertex: int = 0
    latency: int = 0
    hits: int = 0
    occupied: int = 0
    flags: int = 0
    persona: int = 0
    E: Tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0)
    weight: int = 32
    has_fact: int = 0
    # host-only payload (not in the C 32 B slot)
    extract: str = ""
    source: str = ""
    label: str = ""
    kind: str = "fact"
    see: List[int] = field(default_factory=list)
    keys: List[bytes] = field(default_factory=list)


class Cam:
    """Fixed table. put/get never allocate."""

    def __init__(self) -> None:
        self.slot: List[CamSlot] = [CamSlot() for _ in range(CAM_SLOTS)]
        self.used = 0
        self.destroyed = 0
        self.key_index: dict[bytes, int] = {}

    def _probe(self, wsp: bytes) -> int:
        return fnv32(wsp) & (CAM_SLOTS - 1)

    def put(
        self,
        wsp: bytes,
        vertex: int,
        latency: int,
        E: Tuple[int, ...] = (0, 0, 0, 0, 0, 0),
        has_fact: int = 0,
        extract: str = "",
        source: str = "",
        label: str = "",
        kind: str = "",
        see: Optional[List[int]] = None,
        key: bytes = b"",
        flags: int = 0,
        persona: int = 0,
    ) -> int:
        if len(wsp) != WSP_BYTES:
            raise ValueError("WSP must be 16 bytes")
        h = self._probe(wsp)
        e6 = tuple(int(x) for x in (E + (0, 0, 0, 0, 0, 0))[:6])
        for i in range(CAM_SLOTS):
            j = (h + i) & (CAM_SLOTS - 1)
            s = self.slot[j]
            if not s.occupied:
                s.wsp = bytes(wsp)
                s.vertex = vertex & 0xFFFF
                s.latency = int(latency) & 0xFFFF
                s.hits = 1
                s.occupied = 1
                s.flags = int(flags) & 0xFF
                s.persona = int(persona) & 0xFFFF
                s.E = e6  # type: ignore[assignment]
                s.weight = 32
                s.has_fact = 1 if has_fact else 0
                s.extract = extract
                s.source = source
                s.label = label
                if kind:
                    s.kind = kind
                s.see = list(see or [])
                s.keys = []
                self.used += 1
                self._index_key(j, key)
                return j
            if s.wsp == wsp:
                s.hits = min(65535, s.hits + 1)
                s.vertex = vertex & 0xFFFF
                s.latency = int(latency) & 0xFFFF
                if has_fact:
                    s.has_fact = 1
                if flags:
                    s.flags = int(flags) & 0xFF
                s.persona = int(persona) & 0xFFFF
                s.E = e6  # type: ignore[assignment]
                if extract:
                    s.extract = extract
                if source:
                    s.source = source
                if label:
                    s.label = label
                if kind:
                    s.kind = kind
                if see:
                    for v in see:
                        if v not in s.see:
                            s.see.append(v)
                if s.weight < 120:
                    s.weight += 1
                self._index_key(j, key)
                return j
        return -1

    def _index_key(self, slot: int, key: bytes) -> None:
        if not key:
            return
        s = self.slot[slot]
        if key not in s.keys:
            s.keys.append(key)
        self.key_index[key] = slot

    def _persona_ok(self, slot: int, persona_mask: int) -> bool:
        s = self.slot[slot]
        if persona_mask == 0:
            return s.persona == 0
        return s.persona == persona_mask

    def lookup_key(self, key: bytes, persona_mask: int = 0) -> int:
        """Exact event window → slot. O(1). Máscara de persona aísla el codebook."""
        if key in self.key_index:
            slot = self.key_index[key]
            if self._persona_ok(slot, persona_mask):
                return slot
            return -1
        if len(key) < 4:
            return -1
        best = -1
        best_d = 99
        for k, slot in self.key_index.items():
            if not self._persona_ok(slot, persona_mask):
                continue
            if len(k) != len(key):
                continue
            d = 0
            for a, b in zip(k, key):
                if a != b:
                    d += 1
                    if d > 1:
                        break
            if d == 1 and d < best_d:
                if self.slot[slot].flags & (SLOT_FLAG_INHIBIT | SLOT_FLAG_ACTION):
                    continue
                best_d = d
                best = slot
        return best

    def get(self, wsp: bytes) -> int:
        h = self._probe(wsp)
        for i in range(CAM_SLOTS):
            j = (h + i) & (CAM_SLOTS - 1)
            s = self.slot[j]
            if not s.occupied:
                return -1
            if s.wsp == wsp:
                return j
        return -1

    def nearest(
        self, vertex: int, latency: int
    ) -> Tuple[int, int, int]:
        """Return (slot, ham, score). slot=-1 if none within HAM_LIMIT."""
        best_slot = -1
        best_score = 1 << 20
        best_ham = 99
        vertex &= 0xFFFF
        for i, s in enumerate(self.slot):
            if not s.occupied:
                continue
            ham = hamming16(vertex, s.vertex)
            if ham > HAM_LIMIT:
                continue
            sc = combined_score(ham, latency, s.latency)
            if (
                sc < best_score
                or (sc == best_score and ham < best_ham)
                or (sc == best_score and ham == best_ham and (best_slot < 0 or i < best_slot))
            ):
                best_score = sc
                best_ham = ham
                best_slot = i
        return best_slot, best_ham, best_score

    def occupied_slots(self) -> List[int]:
        return [i for i, s in enumerate(self.slot) if s.occupied]
