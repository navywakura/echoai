# 04 — Decisiones: se queda / se tira / se añade

Síntesis del inventario del repositorio y de la revisión de investigación
de 2026 (SCHNC-2).

## Se queda (hipótesis)

- Dos relojes. Fast control vs slow proposal.
- La LLM **no** tiene control absoluto. Veto basal.
- WSP 16 B es el único cable de pensamiento.
- E[6] int8 es el estado neuromodulador.
- CAM Hamming es memoria de hechos / episodios.
- VERIFY / DESCONOCIDO.
- Q6/Q_N LIF entero como procesamiento rápido (software hoy).
- Córtex apagable; el agente sigue eligiendo acciones.
- NEXUS-0 pequeño, 3 acciones, entorno sintético, KPI o muerte.
- Akida como coprocesador **después**, nunca como “el subcórtex”.
- No AGI como objetivo de producto.

## Se tira (no reintroducir)

1. AKD1000 = cerebro reptiliano; LLM = neocórtex.
2. Arquitectura NEXUS como árbol de carpetas biológicas
   (`brainstem.py`, `amygdala.py`, `hypothalamus.py`).
3. Event bus paralelo (`SPIKE_EVENT`, `STATE_EVENT`, `GOAL_EVENT`).
4. `internal_state` float64 (arousal=0.73, …).
5. Vector DB / embeddings float para hechos.
6. LLM como dueña de planificación, imaginación y verdad.
7. LLM dentro del AKD1000. Akida GenAI / TENNs / SSM como path actual.
8. Edge learning BrainChip relabelado STDP.
9. Julios de ficha BrainChip como resultado Knights Labs.
10. PRISMA clínico / EEG / BCI. `prisma5` es sintético.
11. Loihi como backend.
12. Sri Yantra / I Ching como operador (hexagramas = etiqueta de vértice).
13. FNV `event_to_wsp` llamado “pensamiento”.
14. Compositor de marcos fingiendo Broca / `.pt` 57 M en `--ask`.
15. Importar navi5–navi9 al núcleo.
16. ISO 10 / Echo in-OS / tecla `v` como NEXUS-0.
17. Claim 1–20 ms (PIT a 100 Hz; no hay HPET/LAPIC en este sprint).
18. World model en prosa (“si hago A ocurrirá B” generado por LLM).
19. Marca comercial “NEXUS” / “SCHNC”. Experimento sí, producto = echoAI.
20. Meter δ en E[V].
21. Construir *alrededor* de navi10 `--ask`.
22. Forzar Q6 entero dentro de Akida 1 (capas = conv/separable/FC).
23. Self-model / “yo soy una persona”.
24. Sueño/consolidación, córtex, PREGUNTAR activo, contrafactuales
    multi-paso **en NEXUS-0** (van a la ladder).

## Se añade (trabajo real)

Orden = `05-NEXUS-0-SPEC.md` + `06-LADDER.md`.

### NEXUS-0 (ahora)

| # | Qué | Dónde |
|---|---|---|
| A1 | Encoder WSP semántico (lex + vendor bank) | `nexus0/encoder.py` |
| A2 | KPI src/rel/dst + `semantic_collision` | tests |
| A3 | Gate OK/MODIFY/BLOCK puro sobre WSP+CAM | `nexus0/gate.py` |
| A4 | Q[4096][3] int8, γ=7/8, clip | `nexus0/qtable.py` **hecho** |
| A5 | T(s,a)→ŝ' uint16, e=d_H | `nexus0/world.py` **hecho** |
| A6 | CAM episodios ≠ Q política | loop escribe ambos |
| A7 | Entorno sintético 3 acciones, fases A–G | `nexus0/env.py` |
| A8 | Bucle S→A→ŝ'→S'→δ, córtex OFF | `nexus0/loop.py` |
| A9 | Bench 256 turnos + informe JSON | `nexus0/bench.py` |
| A10 | Curiosity = novelty ∧ surprise (enteros) | loop, no módulo extra |

### Después (no ahora)

| Peldaño | Añade |
|---|---|
| NEXUS-1 | T consolidado + predicción que gana al baseline |
| NEXUS-2 | search / contrafactuales multi-paso sobre T |
| NEXUS-3 | UNKNOWN → PREGUNTAR (información activa) |
| NEXUS-4 | córtex OFF→ON bajo ATTEND; emite ≤3 WSP `G_plan` |
| NEXUS-5 | consolidación sueño (episodios → reglas T) |
| NEXUS-6 | embodiment / multimodal (Edge SKU, no desktop) |
| NEXUS-7 | transferencia de tarea |

Akida Cerradura 0 (MetaTF, sin placa): **después** de NEXUS-0 verde.
Head de 3 acciones, no VERIFY.

## Decisiones concretas que ya no se debaten

1. **Índice de Q/T = ranura CAM 0..4095**, no vértice 16-bit 0..65535.
2. **3 acciones = átomos UNIR / TEMER / OBSERVAR** (11 / 18 / 14).
3. **γ = 7/8** (el mismo leak LIF). α = 1/4 (`delta >> 2`).
4. **Reward int8 escalado:** VERIFY/éxito = +16, fallo/amenaza = −16,
   wait = 0, avoid-correcto = +8.
5. **Córtex default OFF.** Un flag `cortex=0` en el banco principal.
6. **Encoder gana a FNV** o el encoder no se mergea.
7. **Software first:** LIF del repo; simulador Akida luego; placa luego.
8. echoAI vive en `echoai/`. No se fusiona a ISO 2.1.
