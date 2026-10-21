"""
NAVI 10 — Q_N mesh (Q8 × Q8).

Address space: 16-bit product of two 8-cubes (65536 vertices).
LIF runs on one Q8 spoke (256 neurons). Hamming is popcount(a^b) — O(1).
No FPU. Bit-identical with NAVI_AI_SNN/qn/navi_qn.c.
"""

from __future__ import annotations

from dataclasses import dataclass

Q8_DIM = 8
Q8_N = 256
Q8_DEGREE = 8
Q8_EDGES = 1024
Q8_NCODE = 16
Q8_CODEWORDS = (
    0, 177, 210, 99, 228, 85, 54, 135, 120, 201, 170, 27, 156, 45, 78, 255
)

MESH_DIM = 16
ADDR_MASK = 0xFFFF

VTH = 40
LEAK_NUM = 7
LEAK_DEN = 8
I_STIM = 40
I_CODE = 12
I_HOP = 40
W_EDGE = 32
T_MAX = 16
STIM_WINDOW = 1

CAM_SLOTS = 4096
HAM_LIMIT = 3
LAT_SHIFT = 4
C_PLASTIC = 20
U_SHORT = 60
WSP_BYTES = 16

SLOT_FLAG_FACTUAL = 0x01
SLOT_FLAG_ACTION = 0x02
SLOT_FLAG_INHIBIT = 0x04
SLOT_FLAG_METAPATH = 0x08
SLOT_FLAG_ACTIVE = 0x80

META_IDLE = 0
META_THINKING = 1
META_ACTION_REQ = 2

PERSONA_SYSTEM = 0x0000
PERSONA_HERMETIC = 0x00FF
PERSONA_PHYSICS = 0xFF00

META_PASSES = 4


def certainty_from_ham(ham: int) -> int:
    """C = 100 - ham*100/16. Entero. ham≥99 (miss) → 0."""
    if ham < 0 or ham >= 99:
        return 0
    if ham > 16:
        ham = 16
    return 100 - (ham * 100) // 16


def key_mask(vertex: int, persona_mask: int) -> int:
    return (int(vertex) ^ int(persona_mask)) & ADDR_MASK

FNV_OFF = 2166136261
FNV_PRIME = 16777619


def popcount(x: int) -> int:
    return int(x).bit_count()


def hamming16(u: int, v: int) -> int:
    return popcount((u ^ v) & ADDR_MASK)


def fnv32(data: bytes) -> int:
    h = FNV_OFF
    for b in data:
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFF
    return h


def simhash16(data: bytes) -> int:
    """Integer SimHash-16. Nearby byte strings stay nearby in Hamming."""
    if not data:
        return 0
    acc = [0] * 16
    for i, b in enumerate(data):
        h = (b * 2654435761 + i * 1640531527) & 0xFFFFFFFF
        for bit in range(16):
            if (h >> bit) & 1:
                acc[bit] += 1
            else:
                acc[bit] -= 1
    v = 0
    for bit in range(16):
        if acc[bit] >= 0:
            v |= 1 << bit
    return v


def q8_nearest(x: int) -> int:
    x &= 0xFF
    best = Q8_CODEWORDS[0]
    best_d = 9
    for w in Q8_CODEWORDS:
        d = popcount((x ^ w) & 0xFF)
        if d < best_d or (d == best_d and w < best):
            best = w
            best_d = d
    return best


def product_nearest(x: int) -> int:
    hi = (x >> 8) & 0xFF
    lo = x & 0xFF
    return (q8_nearest(hi) << 8) | q8_nearest(lo)


def q8_graph_ok() -> bool:
    edges = 0
    for i in range(Q8_N):
        for b in range(Q8_DIM):
            j = i ^ (1 << b)
            if popcount(i ^ j) != 1:
                return False
            if i < j:
                edges += 1
    return edges == Q8_EDGES


def combined_score(ham: int, lat_a: int, lat_b: int) -> int:
    dt = abs(int(lat_a) - int(lat_b))
    if dt > 15:
        dt = 15
    return (int(ham) << LAT_SHIFT) + dt


@dataclass
class Q8Run:
    winner: int
    first_target_spike: int
    spikes_total: int
    counts: list[int]


class Layer256:
    """Integer LIF on one Q8 spoke. Same rule as Q6, DIM=8."""

    def __init__(self) -> None:
        self.code_mask = 0
        for w in Q8_CODEWORDS:
            self.code_mask |= 1 << w
        self.v = [0] * Q8_N
        self.spikes = 0

    def reset(self) -> None:
        self.v = [0] * Q8_N
        self.spikes = 0

    def step(self, stim: int, stim_on: bool, hop_on: bool = False) -> int:
        prev = self.spikes
        nxt = 0
        v = self.v
        stim &= 0xFF
        for i in range(Q8_N):
            cur = 0
            if stim_on and i == stim:
                cur += I_STIM
            if hop_on:
                if (i ^ stim).bit_count() == 1:
                    cur += I_HOP
            for b in range(Q8_DIM):
                j = i ^ (1 << b)
                if (prev >> j) & 1:
                    cur += W_EDGE
            pot = (v[i] * LEAK_NUM) // LEAK_DEN + cur
            if pot > 255:
                pot = 255
            thresh = (VTH - I_CODE) if ((self.code_mask >> i) & 1) else VTH
            if pot >= thresh:
                nxt |= 1 << i
                pot = 0
            v[i] = pot
        self.spikes = nxt
        return nxt

    def run(self, stim: int, target: int, t_max: int = T_MAX) -> Q8Run:
        self.reset()
        counts = [0] * Q8_N
        first = t_max
        total = 0
        saw_code = False
        stim &= 0xFF
        target &= 0xFF
        for t in range(t_max):
            hop = (t >= STIM_WINDOW + 1) and (not saw_code)
            bits = self.step(stim, t < STIM_WINDOW, hop)
            if bits & self.code_mask:
                saw_code = True
            total += bits.bit_count()
            if ((bits >> target) & 1) and first == t_max:
                first = t
            x = bits
            while x:
                lsb = x & -x
                idx = (lsb - 1).bit_count()
                if counts[idx] < 255:
                    counts[idx] += 1
                x ^= lsb
        best = -1
        winner = -1
        for w in Q8_CODEWORDS:
            c = counts[w]
            if c > 0 and (c > best or (c == best and (winner < 0 or w < winner))):
                best = c
                winner = w
        return Q8Run(winner=winner, first_target_spike=first, spikes_total=total, counts=counts)
