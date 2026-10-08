# 02 — Invariantes

Si un PR los rompe, se rechaza. Origen: `kernel/include/wsp.h`,
`docs/NAVI10.md`, `docs/AKIDA.md`, `NAVI_AI_SNN/RFC-2026-08-Q6.md`.

| # | Contrato | Cómo se comprueba |
|---|---|---|
| I1 | WSP = 16 bytes | `_Static_assert(sizeof(wsp_packet_t) == 16)` |
| I2 | Layout WSP congelado | src,rel,dst,time, E[6] int8 ±100, flags, ext{domain,generator,style,slot,seq} |
| I3 | 0 FPU en el paso rápido | leak 7/8, popcount, int8; nada de `float` en `nexus0/` caliente |
| I4 | Heap-0 en CAM / Q6 / Q | 4096 ranuras estáticas; `Q[4096][3]` estático; sin malloc en el step |
| I5 | VERIFY = (d_H ≤ 3) ∧ extracto | si falta uno: DESCONOCIDO |
| I6 | `destroyed == 0` | el CAM no poda (KCC) |
| I7 | Umbral neuronal no decide caminos de corrección | no IRQ, disco, #PF, `G_rxos` |
| I8 | Akida ausente se niega | `neurocpu akida`; NEXUS-0 no finge silicio |
| I9 | Edge learning BrainChip ≠ STDP nuestro | prosa y comentarios |
| I10 | Julios: RAPL/shunt de un chasis o silencio | QEMU no inventa mJ de NPU |
| I11 | LLM/LPU atada o apagada | banco NEXUS-0: `cortex_calls == 0` |
| I12 | Unikernel ≠ host | echoAI no entra en ISO 2.1 |
| I13 | Q6 1-bit no baja de 48/48 | no tocar `navi_q6.c` “para que quepa en Akida” |
| I14 | Firewall epistémico | hipótesis de córtex **nunca** se escribe como `has_fact=1` |
| I15 | CAM ≠ Q | episodios en CAM; política en Q-table |
| I16 | δ no vive en E[V] | δ actualiza `Q[s,a]` |
| I17 | Un solo cable | no hay segundo event-bus de pensamiento |

## Constantes numéricas (no las cambies sin banco)

De `navi10_qn.py` / `navi_q6.h` / `wsp.h`:

```
CAM_SLOTS     = 4096
HAM_LIMIT     = 3
WSP_BYTES     = 16
Q8_N          = 256          # neuronas LIF del spoke
ADDR_SPACE    = 65536        # Q8×Q8, el Q-table de NEXUS-0 NO es 65536
VTH           = 40
LEAK_NUM/DEN  = 7/8
I_STIM        = 40
W_EDGE        = 32
T_MAX         = 16
C_PLASTIC     = 20           # C < 20 abre plasticidad
U_SHORT       = 60           # U ≥ 60 fuerza geodésica
WSP_E_MIN/MAX = -100 / 100
WSP_ATOM_PRIM = 32           # 0..31 primitivos SPEC
WSP_ATOM_MAX  = 48           # 32..47 derivados + pads
```

NEXUS-0 indexa Q y T por **ranura CAM (0..4095)**, no por vértice 16-bit
completo. El vértice se guarda en la ranura. Razón: 65536×3 no es
Heap-0-amigable para el experimento; 4096×3 = 12288 B.

## Átomos de las 3 acciones (NEXUS-0)

De `kernel/include/wsp.h`:

| Acción | id de política | `rel` WSP | valor enum |
|---|---|---|---|
| approach | 0 | `WSP_UNIR` | 11 |
| avoid | 1 | `WSP_TEMER` | 18 |
| wait | 2 | `WSP_OBSERVAR` | 14 |

No uses strings `"approach"` en el cable. El cable lleva el átomo.

## Encoder: FNV no es pensamiento

`navi10_wsp.event_to_wsp` (FNV) es **baseline a perder**. El encoder
NEXUS-0 emite átomos reales. El hash puede quedar como fallback de
colisión, no como semántica.
