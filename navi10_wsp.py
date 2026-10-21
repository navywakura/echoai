"""
NAVI 10 — evento → postal WSP de 16 B.

No hay parsedown ni conversores de texto rígidos. La señal (bytes)
se pliega a un paquete RogexWSP. Átomos 0..31 = primitivos SPEC.
Layout idéntico a kernel/include/wsp.h.
"""

from __future__ import annotations

import struct
from typing import Dict, List, Optional, Tuple

from navi10_qn import WSP_BYTES, fnv32

ATOMS = (
    "SER", "NO_SER", "YO", "OTRO",
    "AQUI", "ALLI", "DENTRO", "FUERA",
    "AHORA", "ANTES", "DESPUES",
    "UNIR", "SEPARAR", "CAMBIAR", "OBSERVAR",
    "PREGUNTAR", "RESPONDER", "DESEAR", "TEMER",
    "RECORDAR", "OLVIDAR", "CREAR", "DESTRUIR",
    "SUBIR", "BAJAR", "ABRIR", "CERRAR",
    "CAUSA", "EFECTO", "POSIBLE", "IMPOSIBLE", "DESCONOCIDO",
)
ATOM_MAX = 48
AHORA = 8
DESCONOCIDO = 31

E_NAMES = ("V", "A", "D", "C", "U", "B")


def clamp_e(n: int) -> int:
    return max(-100, min(100, int(n)))


def atom_id(name: str) -> int:
    try:
        return ATOMS.index(name)
    except ValueError:
        return DESCONOCIDO


def atom_name(i: int) -> str:
    if 0 <= i < len(ATOMS):
        return ATOMS[i]
    return "?"


def pack(
    src: int = 2,
    rel: int = DESCONOCIDO,
    dst: int = 41,
    time: int = AHORA,
    E: Optional[Dict[str, int]] = None,
    flags: int = 0,
    domain: int = 0,
    generator: int = 0,
    style: int = 0,
    slot: int = 0,
    seq: int = 0,
) -> bytes:
    e = E or {}
    ev = [clamp_e(e.get(k, 0)) for k in E_NAMES]
    return struct.pack(
        "<BBBBbbbbbbBBBBBB",
        src & 0xFF,
        rel & 0xFF,
        dst & 0xFF,
        time & 0xFF,
        ev[0], ev[1], ev[2], ev[3], ev[4], ev[5],
        flags & 0xFF,
        domain & 0xFF,
        generator & 0xFF,
        style & 0xFF,
        slot & 0xFF,
        seq & 0xFF,
    )


def unpack(raw: bytes) -> dict:
    if len(raw) != WSP_BYTES:
        raise ValueError("WSP must be 16 bytes")
    src, rel, dst, time, *rest = struct.unpack("<BBBBbbbbbbBBBBBB", raw)
    Evals = rest[:6]
    flags, domain, generator, style, slot, seq = rest[6:]
    return {
        "src": src,
        "rel": rel,
        "dst": dst,
        "time": time,
        "E": {k: int(v) for k, v in zip(E_NAMES, Evals)},
        "flags": flags,
        "ext": {
            "domain": domain,
            "generator": generator,
            "style": style,
            "slot": slot,
            "seq": seq,
        },
        "compact": compact(src, rel, dst, time, {k: int(v) for k, v in zip(E_NAMES, Evals)}),
    }


def compact(src: int, rel: int, dst: int, time: int, E: Dict[str, int]) -> str:
    e = E
    return (
        f"{atom_name(src)} → {atom_name(rel)} → {atom_name(dst)} @{atom_name(time)} | "
        f"E[V{e.get('V', 0):+d} A{e.get('A', 0):+d} D{e.get('D', 0):+d} "
        f"C{e.get('C', 0):+d} U{e.get('U', 0):+d} B{e.get('B', 0):+d}]"
    )


def event_to_wsp(data: bytes) -> bytes:
    """Conversión directa señal → 16 B. Bit-idéntica a navi10_event_to_wsp C."""
    h = fnv32(data)
    h2 = fnv32(h.to_bytes(4, "little"))
    out = bytearray(16)
    out[0] = h % 32
    out[1] = (h >> 8) % 32
    out[2] = (h >> 16) % 32
    out[3] = AHORA
    out[4] = (h2 >> 0) & 63
    out[5] = (h2 >> 6) & 63
    out[6] = (h2 >> 12) & 63
    out[7] = (h2 >> 18) & 63
    out[8] = (h2 >> 24) & 63
    out[9] = (h2 >> 2) & 63
    out[10] = 0
    out[11] = 0
    out[12] = 0
    out[13] = 0
    out[14] = 0
    out[15] = h & 0xFF
    return bytes(out)


def hex16(raw: bytes) -> str:
    return raw.hex()
