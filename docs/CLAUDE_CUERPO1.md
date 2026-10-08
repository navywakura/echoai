# CLAUDE — CUERPO-1 (pegar tal cual)

GUI-2 y WORLD-3 están **verdes**. No los reabras. No descargues un LLM.
No toques kernel, ISO, `parse_reply`, `plan.py`, `thought.KEYS`,
`graph.py`, `sign.py`, `qtable.py`, `world.py`, `encoder.py` (el techo
`index & 0xFF` se mide, no se “arregla” aquí), `loop.py`, `board.py`,
ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/CLAUDE.md`, `echoai/CLAUDE_SITUATED.md`,
`echoai/docs/NOW.md`, `echoai/nexus0/graph.py` (patrón de informe),
`echoai/nexus0/env.py` (contrato `cell/step/reset/teleport/reveal` + `kind`).

Eres implementador. Un slice. Un KPI. Córtex **apagado**.

---

## Qué construyes

Un **cuerpo**, no un grafo más. El animal deja de ser un índice en una
tabla: tiene pose y una física mínima. El `Agent` no cambia. Tres
acciones. El cable sigue siendo WSP 16 B vía `encode_cell(index, kind)`.

Esto no es MiniGrid, no es 8 acciones, no es lidar, no es cámara, no es
Akida. Lidar y cámara vienen **después**. Si el muñeco tiene una ficha
de posición distinta de la que entra en CAM, el slice es rojo: es un
disfraz.

Analogía (no anatomía): el cerebelo predice la consecuencia de un
movimiento. Aquí eso es T sobre un **planta**, no sobre `(i+1)%n`.

---

## El mundo (`echoai/nexus0/body.py`)

Tortuga en una habitación pequeña. La **orientación es estado del
cuerpo**, no una 4ª acción:

```
grid     5 × 5
heading  0,1,2,3   (E, N, W, S) — interna, el loop no ve un “norte”
pose     index = (x + 5*y)*4 + heading     # 100 bins, < 256 (techo de seq)
```

Acciones, las de siempre:

| acción | física |
|---|---|
| `approach` (UNIR) | un paso **hacia donde mira**. Si la casilla destino es pared o fuera: no avanza, `kind` de esta pose se trata como THREAT para el payoff (`R_THREAT`). |
| `avoid` (TEMER)   | gira 90° (elige un sentido, fíjalo, documenta). No traduce. |
| `wait`            | no mueve pose. |

Recompensas: las del anillo, `_reward` de `env.py`. No retunees `R_*`.

- Una casilla GOAL (approach encima cobra `R_SUCCESS`). No bomba: tras
  cobrar, teleporta a START (como GOAL en el grafo).
- Paredes = no se pisan. Approach contra pared paga amenaza.
- START fijo. Seed `BENCH_SEED`.
- `kind` es por **celda del suelo** (EMPTY/GOAL/THREAT), no por heading.
  Cuatro headings en la misma (x,y) GOAL son GOAL. El index las separa.
- `reveal()` no-op. Sin `KIND_NOVEL` en el camino del KPI (no PREGUNTAR).
- `RingEnv.ask()` sigue sin existir.

Contrato de env: `cell/step/reset/teleport/reveal` y `kind`. `cell().index`
es la pose (100 valores), no el id de baldosa. `teleport` acepta un index
de pose. Documenta `pose_of(index) -> (x,y,h)` y al revés.

Dos layouts, **un** cambio de física (como HOME/SHIFT, una arista):

| layout | qué cambia |
|---|---|
| `open`  | el pasillo al GOAL está libre |
| `block` | **una** baldosa del pasillo se vuelve pared (no se pinta de THREAT el suelo si no chocan: el choque *es* el approach contra fuera/pared). Misma START, mismo GOAL, mismos headings. |

Nada se “repinta” a otro kind para fingir geometría: o hay pared o no.
Los bins de pose que no chocan conservan paquete, CAM, T, Q.

---

## El experimento

```
PYTHONPATH=. python3 -m echoai.nexus0.body
```

Escribe `echoai/lab/nexus0_cuerpo1_report.json`. Nunca pisa
`nexus0_report.json` ni `nexus0_world3_report.json`.

Córtex off. `Agent(env=BodyEnv("open"))`. Constantes propias
(`TRAIN_TURNS`, …). No toques `BENCH_TURNS`.

### KPI (todos a la vez)

```
false_facts = 0
destroyed = 0
cortex_calls = 0
questions = 0
3 acciones
poses = 100
t_beats_stepper = True
  # T predice el sucesor de approach mejor que la aritmética
  # “siempre x+1” (un paso este, ignorando heading y paredes).
  # Cita JUMP: no 0.99 como world model; cita el lugar donde
  # heading o pared hace que stepper falle y T acierte.

bump_is_threat
  # approach contra pared: r = R_THREAT, pose no atraviesa.

avoid_turns_not_translates
  # avoid cambia heading, no x,y.

open vs block: exactamente las poses cuyo sucesor approach cambia
  se cuentan (como test_only_one_edge_differs). El resto de T sobrevive.

anillo default intacto si corres el banco
```

**No** exijas “greedy desde START llega a GOAL”. Eso es **WALK-1**,
el slice siguiente. Si de casualidad llega, anótalo; no es el verde.

Si 5×5×4 se come el horizonte de crédito y T no llega a ver paredes:
reduce a 4×4 (64 poses) y deja `poses_requested=100, poses=64, reason=…`
en el JSON. No finjas 100. No bajes de 4×4.

---

## Qué no se toca

Encoder, `index & 0xFF` (mide colisión 256 vs 0 si algún index llega;
en 100 no debería). MiniGrid, lidar, cámara, float en el **rápido**
(el env puede usar int para x,y,h; si necesitas un paso intermedio
float en el env, no lo cueles a Q/T/CAM). 8 acciones. Qwen. GUI.
SLEEP. ANTI-ALIAS. `plan.py` default 0.

---

## Tests (`TestCuerpo1`)

Sin red, sin GGUF, sin `NAVI_CORTEX_CMD`.

1. 100 poses (o el número honesto del JSON) y tabla total 3 acciones.
2. approach avanza según heading; contra pared no atraviesa y paga amenaza.
3. avoid gira, no traduce.
4. wait no mueve.
5. GOAL no bomba (vuelve a START).
6. `t_beats_stepper`.
7. open vs block: diff de sucesores acotado y nombrado; T de poses
   no afectadas sobrevive si entrenas y cambias layout (mismo Agent).
8. `false_facts=0`, `cortex_calls=0`.
9. el módulo no importa cortex/llama/urllib.
10. no pisa `nexus0_report.json`.

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body
```

Tests ≥ 221. Bench candados. Informe `green: true`.

---

## Informe que me pegas a Grok

- física (sentido del giro, tamaño, START/GOAL/pared)
- `t_beats_stepper` con un ejemplo (heading o pared)
- cuántos sucesores cambian open→block
- CAM ocupada / 4096
- si greedy alcanzó GOAL, número al lado, **no** como KPI
- archivos tocados
- si bajaste a 4×4: reason en el JSON
