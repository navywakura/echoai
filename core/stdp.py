"""
NAVI 10 — STDP entero + neuromodulación E[6].

E = (V, A, D, C, U, B). No es un sentimiento fingido: es la señal
que abre o cierra plasticidad y elige geodésica vs. peso.

  C < C_PLASTIC  →  STDP ON (registrar patrón nuevo)
  U >= U_SHORT   →  ruta más corta (Hamming), ignora pesos
  A              →  extra de I_STIM (0..5)

Pesos int8, sin FPU. En Akida esto sería edge-learning de la última
FC; hoy es software y se etiqueta como tal.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from echoai.core.qn import C_PLASTIC, Q8_DIM, U_SHORT


def clamp_w(w: int) -> int:
    if w < -40:
        return -40
    if w > 40:
        return 40
    return w


def gates(E: Sequence[int]) -> Dict[str, int]:
    e = list(E) + [0] * 6
    C = int(e[3])
    U = int(e[4])
    A = int(e[1])
    return {
        "plastic": 1 if C < C_PLASTIC else 0,
        "short_path": 1 if U >= U_SHORT else 0,
        "i_stim_boost": max(0, A) // 20,
        "C": C,
        "U": U,
    }


def ltp(w_dim: list, xorv: int) -> None:
    """Refuerza las dimensiones que NO diferían (coincidencia temporal)."""
    for b in range(Q8_DIM):
        if ((xorv >> b) & 1) == 0:
            w_dim[b] = clamp_w(w_dim[b] + 1)


def ltd(w_dim: list, xorv: int) -> None:
    """Debilita las dimensiones que sí diferían (desfase)."""
    for b in range(Q8_DIM):
        if (xorv >> b) & 1:
            w_dim[b] = clamp_w(w_dim[b] - 1)


def edge_energy(w_dim: Sequence[int], bit: int) -> int:
    """Energía de una arista del hipercubo: W_EDGE - peso STDP (entero)."""
    w = int(w_dim[bit]) if bit < len(w_dim) else 0
    return 32 - w
