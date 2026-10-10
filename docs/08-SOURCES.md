# 08 — Fuentes

Cita el repo para el repo. Cita BrainChip para BrainChip. Los papers
son contexto, no dependencias.

---

## Internas (canónicas)

| Path | Por qué |
|---|---|
| `echoai/docs/05-NEXUS-0-SPEC.md` | spec de este sprint |
| `kernel/include/wsp.h` | cable 16 B |
| `kernel/navi/wsp_lex.c` | n-gramas encoder |
| `kernel/navi/navi_q6.c` / `.h` | Q6 LIF |
| `NAVI_AI_SNN/RFC-2026-08-Q6.md` | hipótesis Q6 + KPI 48/48 |
| `NAVI_AI_SNN/qn/navi_qn.c` | Q8 spoke C |
| `NAVI_AI_SNN/results/latest.txt` | Q6_1BIT 48/48 |
| `navi10_qn.py` | Q_N + constantes |
| `navi10_cam.py` | CAM 4096 |
| `navi10_wsp.py` | pack/unpack; FNV = baseline |
| `navi10_stdp.py` | gates E[6], LTP/LTD |
| `navi10_spoke.py` | Stream-to-Spoke |
| `navi10_dag.py` | allocate ranura |
| `navi10_engine.py` | `think()` = router a **no** envolver |
| `navi10_intent.py` | substrings (diagnóstico) |
| `navi10_lpu.py` | compositor de marcos, no SLM servido |
| `docs/NAVI10.md` | contrato navi10 |
| `docs/NAVI9_HYBRID.md` | LLM = boca atada |
| `docs/NAVI3_WSP_ARCHITECTURE.md` | transductor + veto L2 |
| `docs/AKIDA.md` | cinco cerraduras |
| `docs/CIANOTIPO.md` | tres líneas, un idioma |
| `docs/ECHO.md` | tipos de acto |
| `docs2.0/neuromorfico.md` | 2.1: Q6, prisma5 sintético, navi10 fuera |
| `docs2.0/limites.md` | lo que 2.1 no hace |
| `vendor/RogexWSP/docs/SPEC.md` | 32 átomos, E[6] |
| `vendor/RogexWSP/docs/SPEC_V0.5.md` | Hail Mary (no es el struct kernel) |
| `vendor/RogexWSP/examples/` | banco encoder |
| `docs/PITCH_2.1.md` | consola, SNN, robótica, Akida-cuando-haya |

## Diagnóstico navi10 (resumen para el agente)

`--ask` = intent substrings → plantillas / CAM+wiki / compositor.
SNN lateral (SimHash + spikes contados). WSP de salida a menudo FNV.
LPU-S 57 M overfit, no servido. TUI = cara. Sedimento navi7–9.
VERIFY/DESCONOCIDO y Q6 48/48 son lo sólido.

## Papers citados por la investigación 2026 (no implementarlos)

No se `pip install` nada de esta lista para NEXUS-0.

| Idea | Ref | Uso en echoAI |
|---|---|---|
| MAP (planner modular) | Nature Comm. s41467-025-63804-5 | separar monitor/propuesta/predicción; no copiar módulos |
| V-JEPA 2 | Meta AI | T(s,a) como predicción; nuestro T es tabla entera |
| Dreamer | (clásico) | world / critic / actor ≈ T / Q / gate |
| Titans | NeurIPS 2025 / Google | memoria persistente vs corto plazo → NEXUS-5 |
| Memory for LLM agents | arXiv:2603.07670 | write/manage/read; consolidación |
| DMP-SNN dual memory | Nature Mach. Intell. 2026 s42256-026-01255-3 | vías rápida/lenta; ya es nuestra tesis |
| Cognitive maps / sampling | Nature Mach. Intell. s42256-026-01254-4 | search sobre mapa discreto → NEXUS-2 |
| WorldEvolver | arXiv:2606.30639 | episódico vs reglas T; consolidación |
| Neuromorphic spike LLM | PubMed 2025 | **no** es el path |
| Spiking Transformer WTA | arXiv:2604.11321 | **no** es el path |
| Akida user guide | doc.brainchipinc.com | capas reales Akida 1 |
| AKD1000 product brief | brainchip.com PDF | 20 NPUs, event-driven |
| BrainChip AGM 2026 roadmap | investor.brainchip.com | GenAI ≠ nuestro silicon |

## Qué no leer para implementar NEXUS-0

Loihi, EEG clínico, ISO 10, spiking-transformer como motor de navi10,
vector DBs, AGI recipes, `echo/echo_router.py` como arquitectura.
