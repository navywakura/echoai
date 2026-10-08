"""
NAVI 10 — Dynamic Attractor Generator.

Cuando el impulso no estabiliza un atractor (Hamming > HAM_LIMIT),
y E[C] es baja (o hay enseña), se reserva la siguiente ranura libre
del CAM, se le asigna un vértice Q8×Q8 y un WSP de 16 B.

No se toca el codebook lineal [8,4,4] (16 modos). El atractor nuevo
es una etiqueta dispersa en el producto. KCC: jamás se borra.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from echoai.core.cam import Cam
from echoai.core.qn import CAM_SLOTS, HAM_LIMIT


def allocate(
    cam: Cam,
    wsp: bytes,
    vertex: int,
    latency: int,
    E: Sequence[int],
    *,
    has_fact: int = 0,
    extract: str = "",
    source: str = "",
    label: str = "",
    see: Optional[list] = None,
    key: bytes = b"",
    flags: int = 0,
    persona: int = 0,
) -> Tuple[int, str]:
    """Return (slot, note). slot=-1 if the static pool is full."""
    if cam.used >= CAM_SLOTS:
        return -1, "CAM full — Heap-0 pool exhausted (no malloc)"
    slot = cam.put(
        wsp,
        vertex,
        latency,
        tuple(E),
        has_fact=has_fact,
        extract=extract,
        source=source,
        label=label,
        see=see,
        key=key,
        flags=flags,
        persona=persona,
    )
    if slot < 0:
        return -1, "CAM full"
    return slot, "new attractor"


def within_limit(ham: int) -> bool:
    return 0 <= ham <= HAM_LIMIT
