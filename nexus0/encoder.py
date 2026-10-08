"""
Semantic WSP encoder for NEXUS-0.

Order: vendor bank (exact match) → wsp_lex n-grams → DESCONOCIDO.
FNV never runs in this path; it stays as the bench baseline to beat.
A miss is declared a miss: `h % 32` is not a meaning.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.core.spoke import fold_bytes
from echoai.core.wsp import event_to_wsp, pack, unpack

from echoai.nexus0 import lex
from echoai.nexus0.constants import WSP_BYTES
from echoai.nexus0.env import (
    KIND_EMPTY,
    KIND_GOAL,
    KIND_CLOSED,
    KIND_NOVEL,
    KIND_OBJECT,
    KIND_THREAT,
)

# wsp.h 0..39 (primitives + factory derived)
ATOM_ID: Dict[str, int] = {
    "SER": 0, "NO_SER": 1, "YO": 2, "OTRO": 3,
    "AQUI": 4, "ALLI": 5, "DENTRO": 6, "FUERA": 7,
    "AHORA": 8, "ANTES": 9, "DESPUES": 10,
    "UNIR": 11, "SEPARAR": 12, "CAMBIAR": 13, "OBSERVAR": 14,
    "PREGUNTAR": 15, "RESPONDER": 16, "DESEAR": 17, "TEMER": 18,
    "RECORDAR": 19, "OLVIDAR": 20, "CREAR": 21, "DESTRUIR": 22,
    "SUBIR": 23, "BAJAR": 24, "ABRIR": 25, "CERRAR": 26,
    "CAUSA": 27, "EFECTO": 28, "POSIBLE": 29, "IMPOSIBLE": 30,
    "DESCONOCIDO": 31,
    "AMOR": 32, "SOLEDAD": 33, "COMUNICAR": 34, "CONEXION": 35,
    "PELIGRO": 36, "BIENVENIDA": 37, "CONCIENCIA": 38, "WIRED": 39,
    "NONE": 40, "UNK": 41,
}

ATOM_NAME: Dict[int, str] = {v: k for k, v in ATOM_ID.items()}

BANK_PATH = Path(__file__).resolve().parent / "bank" / "canonical.json"


def atom_name(a: int) -> str:
    """Full 0..47 table. echoai.core.wsp.atom_name only knows the 32 primitives."""
    return ATOM_NAME.get(int(a), "?")


def compact(raw: bytes) -> str:
    """Atoms, not hex. One line per packet."""
    p = unpack(raw)
    e = p["E"]
    return (
        f"{atom_name(p['src'])} → {atom_name(p['rel'])} → {atom_name(p['dst'])}"
        f" @{atom_name(p['time'])} | "
        f"E[V{e['V']:+d} A{e['A']:+d} D{e['D']:+d} "
        f"C{e['C']:+d} U{e['U']:+d} B{e['B']:+d}]"
    )


def _fold_text(text: str) -> str:
    return fold_bytes(text).decode("utf-8", "replace").strip()


def _load_bank() -> List[dict]:
    if not BANK_PATH.is_file():
        return []
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    return list(data.get("phrases") or [])


def _atoms(row: dict) -> Tuple[int, int, int, int, Dict[str, int]]:
    src = ATOM_ID[row["src"]]
    rel = ATOM_ID[row["rel"]]
    dst = ATOM_ID[row["dst"]]
    time = ATOM_ID[row["time"]]
    E = {k: int(v) for k, v in (row.get("E") or {}).items()}
    return src, rel, dst, time, E


def encode_semantic(text: str) -> Optional[bytes]:
    """Return 16 B if the folded text hits the vendor bank. Else None."""
    folded = _fold_text(text)
    for row in _load_bank():
        if _fold_text(str(row.get("text") or "")) == folded:
            src, rel, dst, time, E = _atoms(row)
            raw = pack(src=src, rel=rel, dst=dst, time=time, E=E, generator=0x05)
            if len(raw) != WSP_BYTES:
                raise RuntimeError("pack() broke 16 B")
            return raw
    return None


# A miss carries low certainty and some urgency: "I do not know this".
E_UNKNOWN: Dict[str, int] = {"V": 0, "A": 10, "D": 0, "C": 10, "U": 20, "B": 0}


def encode_unknown() -> bytes:
    """YO → DESCONOCIDO → UNK @AHORA. Still 16 B, still not a hash."""
    raw = pack(
        src=ATOM_ID["YO"],
        rel=ATOM_ID["DESCONOCIDO"],
        dst=ATOM_ID["UNK"],
        time=ATOM_ID["AHORA"],
        E=E_UNKNOWN,
        domain=lex.DOM_GENERAL,
        generator=0x05,
    )
    if len(raw) != WSP_BYTES:
        raise RuntimeError("pack() broke 16 B")
    return raw


def encode(text: str) -> bytes:
    """Production encoder: bank → lex n-grams → DESCONOCIDO. No FNV."""
    hit = encode_semantic(text)
    if hit is not None:
        return hit
    hit = lex.apply_wsp(text)
    if hit is not None:
        return hit
    return encode_unknown()


def encode_source(text: str) -> str:
    """Which layer answered: 'bank' | 'lex' | 'unknown'. For the report."""
    if encode_semantic(text) is not None:
        return "bank"
    if lex.apply(text) is not None:
        return "lex"
    return "unknown"


def encode_fnv(text: str) -> bytes:
    """Baseline only. Kept so the bench can show what it beats."""
    return event_to_wsp(fold_bytes(text))


def rel_of(raw: bytes) -> int:
    return unpack(raw)["rel"]


def src_of(raw: bytes) -> int:
    return unpack(raw)["src"]


def dst_of(raw: bytes) -> int:
    return unpack(raw)["dst"]


# Cell kind → (rel, dst). Same atom table as text: the agent's own
# perception is on the shared cable, not in a private codec.
CELL_ATOMS: Dict[int, Tuple[int, int]] = {
    KIND_EMPTY: (ATOM_ID["OBSERVAR"], ATOM_ID["AQUI"]),
    KIND_GOAL: (ATOM_ID["DESEAR"], ATOM_ID["AQUI"]),
    KIND_THREAT: (ATOM_ID["TEMER"], ATOM_ID["PELIGRO"]),
    KIND_NOVEL: (ATOM_ID["DESCONOCIDO"], ATOM_ID["UNK"]),
    # OBJ-1. Perception, not a verb: the body sees that something which is
    # not itself is here. UNIR is approach and stays approach, and the
    # affect below is EMPTY's — the glass is not the reward.
    KIND_OBJECT: (ATOM_ID["OBSERVAR"], ATOM_ID["OTRO"]),
    # OPEN-1. Still perception: the body sees that the thing here is shut.
    # The rel is OBSERVAR and the object of the sentence is CERRAR — the
    # state of the world, not an instruction. ABRIR is the gear, and a
    # gear does not belong in a packet that says what is being looked at.
    KIND_CLOSED: (ATOM_ID["OBSERVAR"], ATOM_ID["CERRAR"]),
}


# A question is aroused and uncertain: low C, high U. It is not a fact.
E_ASK: Dict[str, int] = {"V": 0, "A": 40, "D": 0, "C": 10, "U": 60, "B": 0}


def encode_ask() -> bytes:
    """NEXUS-3 PREGUNTAR packet: YO → PREGUNTAR → DESCONOCIDO @AHORA.

    The act of asking, on the same 16 B cable as everything else. Not FNV,
    not a movement action.
    """
    raw = pack(
        src=ATOM_ID["YO"],
        rel=ATOM_ID["PREGUNTAR"],
        dst=ATOM_ID["DESCONOCIDO"],
        time=ATOM_ID["AHORA"],
        E=E_ASK,
        generator=0x05,
    )
    if len(raw) != WSP_BYTES:
        raise RuntimeError("pack() broke 16 B")
    return raw


def encode_cell(index: int, kind: int, *, vitality: Optional[int] = None,
                temperature: Optional[int] = None,
                temperature_bands: int = 4) -> bytes:
    """WSP for a synthetic cell. seq=index, or two same-kind cells collide."""
    rel, dst = CELL_ATOMS.get(int(kind), CELL_ATOMS[KIND_EMPTY])
    e = {"V": 0, "A": 20, "D": 0, "C": 40, "U": 40 if kind == KIND_THREAT else 10, "B": 0}
    if kind == KIND_THREAT:
        e["V"] = -80
        e["A"] = 80
        e["U"] = 80
    elif kind == KIND_GOAL:
        e["V"] = 40
        e["C"] = 80
    if vitality is not None:
        if type(vitality) is not int or not 0 <= vitality <= 127:
            raise ValueError("vitality must be an integer in 0..127")
        # Observation only: the physiological register remains in Agent.
        # Four viable bands plus a distinct terminal observation.
        e["U"] = (100 if vitality == 0 else
                  (90, 60, 30, 0)[(vitality - 1) // 32])
    if temperature is not None:
        if type(temperature) is not int or not 0 <= temperature <= 127:
            raise ValueError("temperature must be an integer in 0..127")
        if type(temperature_bands) is not int or temperature_bands not in (4, 8):
            raise ValueError("temperature_bands must be 4 or 8")
        # HEAT-1 observation only. The register stays in Agent; B carries
        # a coarse signed thermal band on the existing 16-byte packet.
        values = ((-75, -25, 25, 75) if temperature_bands == 4 else
                  (-88, -63, -38, -13, 13, 38, 63, 88))
        width = 128 // temperature_bands
        e["B"] = -100 if temperature == 0 else values[(temperature - 1) // width]
    raw = pack(
        src=ATOM_ID["YO"],
        rel=rel,
        dst=dst,
        time=ATOM_ID["AHORA"],
        E=e,
        generator=0x05,
        seq=int(index) & 0xFF,
    )
    if len(raw) != WSP_BYTES:
        raise RuntimeError("pack() broke 16 B")
    return raw
