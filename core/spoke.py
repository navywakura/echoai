"""
NAVI 10 — Stream-to-Spoke.

Convierte un evento (sensor, red WSP, bytes de texto) en un tren de
impulsos a la cadencia entera de Akida (T_MAX=16 ticks). No parsea
español: recorta por delimitadores de byte (≤0x20 y puntuación) y
codifica latencia. Heap-0: buffers fijos en el llamador.
"""

from __future__ import annotations

from typing import List, Tuple

from echoai.core.qn import Q8_N, T_MAX, simhash16

_PUNCT = set(b".,;:!?/\\|\"'()[]{}")


def fold_bytes(text: str) -> bytes:
    t = (text or "").lower()
    for a, b in (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"),
        ("¿", " "), ("¡", " "),
    ):
        t = t.replace(a, b)
    return t.encode("utf-8")


def windows(data: bytes) -> List[bytes]:
    """Segmentación por delimitador de byte. No es un léxico de 73 fichas."""
    out: List[bytes] = []
    cur = bytearray()

    def flush() -> None:
        w = bytes(cur)
        cur.clear()
        if w:
            out.append(w)

    for b in data:
        if b <= 0x20 or b in _PUNCT:
            flush()
        else:
            cur.append(b)
    flush()
    if data and data not in out:
        out.insert(0, data)
    return out


def event_latency(data: bytes) -> int:
    if not data:
        return 0
    n = min(len(data), 32)
    acc = sum(data[:n])
    return (acc // n) >> 4  # 0..15


def event_ticks(data: bytes) -> List[int]:
    """256 neuronas, 255 = no dispara. Latencia = nibble alto del byte."""
    ticks = [255] * Q8_N
    if not data:
        return ticks
    acc = 0
    for i, b in enumerate(data[:32]):
        acc ^= b
        n = (acc + i * 17) & 0xFF
        t = b >> 4
        if t > T_MAX - 1:
            t = T_MAX - 1
        if t < ticks[n]:
            ticks[n] = t
    return ticks


def event_addr(data: bytes) -> int:
    return simhash16(data)


def encode_event(data: bytes) -> Tuple[int, int, List[int]]:
    """(vertex Q8×Q8, latency, ticks[256])."""
    return event_addr(data), event_latency(data), event_ticks(data)
