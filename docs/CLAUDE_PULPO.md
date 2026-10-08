# CLAUDE — PULPO (cerrar la etapa, pegar tal cual)

CREDIT-1 está **verde**. CUERPO-1 2D se queda. WALK-1 sin resto se queda
**rojo** (`expectedFailure`). No los reabras. No descargues un LLM.
No toques kernel, ISO, `parse_reply`, `encoder.py` (el techo `index & 0xFF`
se **mide**, no se agranda), `constants.py` (`R_*`, `ALPHA_SHIFT`),
`graph.py`, `sign.py`, `board.py`, `thought.KEYS`, `plan.py` default 0,
ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/CLAUDE.md`, `echoai/nexus0/body.py` (contrato de
env + remainder), `echoai/nexus0/qtable.py` (`remainder=True` ya existe),
`echoai/docs/NOW.md`, `echoai/docs/CHATGPT_SCALE_VERDICT.md` § 3D-162.

Eres implementador. **Esta es la etapa pulpo.** Tres verdes a la vez,
un mundo nuevo, córtex **apagado**. Si uno falla, el slice es rojo:
dímelo claro. **No hardcodees** caminos, waypoints, ni `if pose==`.

---

## Qué es “pulpo 100 %” en este lab (no un cefalópodo)

Hoy hay tortuga **2D** que, **con** `remainder=True`, recorre un pasillo
de 10 y cobra 12 veces. Eso no es pulpo cerrado. Falta:

1. Cuerpo en **espacio 3D** (posición + dirección de avance).
2. **Moverse** y **llegar al premio** greedy desde un START canónico
   (remainder on, α/R iguales).
3. **Cambiar de estrategia** cuando tapas el pasillo: el camino corto
   muere, existe un desvío, greedy **sigue cobrando**. Córtex off.
4. T predice el cuerpo 3D mejor que “siempre +X”.

El 4B no camina. GUI no se toca. ABRIR / objetos / self-model / segundo
agente son **ECHO-1**, la etapa **después** de este verde.

---

## El mundo (`echoai/nexus0/body3d.py`)

Cubo **3×3×3** voxeles, **6** headings (caras, no 24 orientaciones):

```
x,y,z ∈ {0,1,2}
h ∈ {+X, -X, +Y, -Y, +Z, -Z}     # 0..5
index = ((x + 3*y + 9*z) * 6 + h)     # 0..161 < 256
```

`index_of` / `pose_of` inversos, testeados en las 162 poses.
`encode_cell(index, kind)` — 162 paquetes distintos; 256 sigue colisionando
con 0 (no lo “arregles”).

Acciones, las de siempre:

| acción | física |
|---|---|
| `approach` | un voxel **hacia donde mira**. Fuera o pared: no avanza, paga `R_THREAT`. |
| `avoid`    | **ciclo** de heading `h → (h+1) mod 6`. No traduce. (3 acciones: no hay yaw y pitch aparte.) |
| `wait`     | nada. |

Suelo vs pared: voxeles sólidos no se pisan. `kind` es del **voxel**,
igual en las 6 poses. **Ningún suelo pintado THREAT** — la amenaza es el
choque, como CUERPO-1.

GOAL cobra `R_SUCCESS` y vuelve a START (no bomba). Seed `BENCH_SEED`.
`reveal()` no-op. Sin `KIND_NOVEL` en el KPI.

### Geometría (tú la fijas y la documentas; no un grid vacío)

Dos caminos **disjuntos en el medio**, los dos andables en `open`:

- **Corto:** p.ej. `(0,0,0) → … → (2,2,2)` por un túnel.
- **Largo:** un desvío por otra cara / otra arista del cubo.

`block`: **un** voxel del camino corto se vuelve pared. El largo **sigue**.
Inundación: START alcanza GOAL en ambos layouts. En `block`, el corto
ya no.

Mismas 3 acciones. `cell().index` es la pose 3D — una sola ficha.

Layout names: `open` / `block`.

---

## El experimento

```
PYTHONPATH=. python3 -m echoai.nexus0.body3d
```

Escribe `echoai/lab/nexus0_pulpo_report.json`. Nunca pisa
`nexus0_report.json`, `nexus0_cuerpo1_report.json`, `nexus0_credit1_report.json`.

Entrenamiento: curriculum inverso (como WALK-1) **con** `remainder=True`.
Examen greedy, córtex off, teleport al START canónico — **no** a un
vecino del GOAL.

Dos exámenes, mismo Agent o el mismo Q/T/CAM copiado con honestidad
(un Agent entrenado en `open`+remainder, luego `env` → `block` **sin**
resetear Q/T/CAM, teleport START, greedy):

| brazo | layout examen | KPI |
|---|---|---|
| A | `open`  | `exam_open_goal_hits > 0` |
| B | `block` | `exam_block_goal_hits > 0`  ← el pulpo: el corto murió y aún cobra |

Si B es 0 porque Q sigue intentando el túnel tapado y se queda en wait
contra la pared: **rojo**. No pongas un `if block: avoid`. Tiene que
**haber visitado el desvío en el tren** (curriculum que cubra distancias
del camino largo, o explorar `q.select` como siempre) y el resto tiene
que dejar Q>0 en ese camino.

T (córtex off, remainder irrelevante para T):

- `t_beats_stepper`: baseline “approach siempre +X, ignora heading y paredes”.
- Barrido de poses alcanzables, como CUERPO-1.

Transferencia de T `open→block`: sucesores approach que cambian se
**cuentan**; las filas no afectadas siguen ciertas. Como WORLD-3 / cuerpo 2D.

---

## `green()` — los tres a la vez

```
false_facts=0 destroyed=0 cortex_calls=0 questions=0
poses=162  max_index=161  packet_ceiling=256  (256 colisiona con 0)
t_beats_stepper  (barrido)
bump_is_threat  avoid_cycles_heading  goal_returns_to_start
exam_start canónico
exam_open_goal_hits  > 0
exam_block_goal_hits > 0     # sin esto no es pulpo
remainder True en el Agent del walk; False en el anillo
alpha_shift==2  R iguales
open vs block: approach_diff_count > 0  y el desvío sigue conectado
```

**No hardcodear:** grep de una lista de poses del desvío como política
= rojo. `shortest_path` solo para el informe.

Si 3×3×3 se queda corto de desvío, **no** subas a 4×4×4 (384 > 256).
Ajusta paredes dentro de 162. Si walk open funciona y block no, slice
rojo, no finjas geometría imposible.

---

## Tests (`TestPulpo`)

Sin GGUF, sin `NAVI_CORTEX_CMD`.

1. 162 poses, inversos, 162 paquetes distintos, 256==0.
2. approach según 6 headings; bump no atraviesa.
3. avoid cicla heading, no xyz.
4. wait quieto.
5. GOAL no bomba.
6. `open` y `block` conectados; el voxel tapado está en el corto, no en el largo.
7. `t_beats_stepper`.
8. T no afectadas sobreviven al block.
9. `exam_open_goal_hits > 0` desde START, remainder on.
10. `exam_block_goal_hits > 0` desde START, **mismo** Q/T/CAM, remainder on.
11. `test_no_hardcoded_path` en el examen.
12. anillo default `remainder=False`, `policy_after [-12,+5,0]`.
13. no pisa informes ajenos; módulo sin cortex/llama.

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d
```

Tests ≥ 260. Un expectedFailure (WALK-1 2D sin resto) se queda.

---

## Informe que me pegas a Grok

- mapa de voxeles (cuáles son pared, corto, largo, el tapón)
- `exam_open_goal_hits` / `exam_block_goal_hits` / poses visitadas
- si el greedy en block **usa el desvío** (sí/no, con el path)
- T barrido vs stepper
- CAM ocupada
- archivos tocados
- si block es 0: dímelo claro, no retunees R ni hardcodees el giro
