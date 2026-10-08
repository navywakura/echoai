# CLAUDE — WALK-1 (pegar tal cual)

CUERPO-1 está **verde**. No lo reabras. No descargues un LLM. No toques
kernel, ISO, `parse_reply`, `plan.py` (sigue default 0), `thought.KEYS`,
`encoder.py`, `qtable.py` (α, γ, clip, `ALPHA_SHIFT`), `world.py`,
`graph.py`, `sign.py`, `board.py`, `R_*`, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/CLAUDE.md`, `echoai/nexus0/body.py` (la planta),
`echoai/docs/NOW.md`, el informe `lab/nexus0_cuerpo1_report.json`.

Eres implementador. Un slice. Un KPI. Córtex **apagado**.

**No hardcodear.** Ni el camino este-luego-norte, ni “si pose==GOAL-1
entonces approach”, ni una tabla de waypoints, ni mover el START del
*test* junto al GOAL. El bicho tiene que **aprender**. El curriculum
solo cambia **desde dónde se pisa** en el entrenamiento.

---

## Qué construyes

Hoy, greedy 128 turnos desde START `(0,0,E)`: `goal_hits=0`,
`poses_visited=1`, Q en el bucle libre `0 0 0 0 -4 0 0 4 8 13`.
α=1/4 mata δ<4; el valor no llega al arranque. Eso no se arregla
subiendo R ni bajando α.

**WALK-1 = reverse curriculum en el *entrenamiento*, examen en el START
canónico.**

```
entrenar un rato teletransportado a distancia 1 del GOAL
→ luego 2 → luego 3 → … hasta el START de CUERPO-1
examinar: Agent fresco de política… no. El MISMO Q/T/CAM,
teleport al START canónico (0,0,E), greedy, córtex off.
KPI: goal_hits > 0
```

Layout `open` (pasillo libre). `block` no es este KPI.

El número a batir está medido: `greedy_free.goal_hits == 0`.

---

## Cómo (y cómo no)

Permitido:

- `env.teleport(pose)` entre fases de tren. Las poses las sacas de la
  física (`index_of` / vecinos approach), no de una lista mágica de
  celdas “buenas”.
- Distancia = pasos **mínimos** de approach+avoid hasta pisar GOAL
  (inundación en la tabla de sucesores, no Manhattan ciego al heading).
- Mismo `Agent` a lo largo del curriculum (conserva Q/T/CAM), o uno
  solo que se va alejando. No copies Q a mano.
- `eps` de entrenamiento el de siempre (`q.select` no greedy). El
  **examen** es `greedy=True`.

Prohibido:

- Cambiar `R_SUCCESS`, `R_THREAT`, `R_AVOID_OK`, `ALPHA_SHIFT`, `GAMMA_*`.
- Trazas (`trace=True`) como truco de este slice. Ya se midieron feas.
- n-step, residual accumulator, planner always-on. Eso es NEXUS posterior.
- `if x==4 and y==0: action = avoid` ni equivalente.
- Enchufar Qwen / `NAVI_CORTEX_CMD`.
- Pintar el suelo de THREAT para que el gate empuje.
- Examinar desde GOAL-1 y llamar a eso “llegó desde START”.

Si el curriculum no basta y greedy desde START sigue en 0, **dímelo
claro**: slice rojo, no bajes el START del test.

---

## Informe

```
PYTHONPATH=. python3 -m echoai.nexus0.body --walk
```

o un `walk()` en `body.py` que escriba
`echoai/lab/nexus0_walk1_report.json`. **Nunca** pisa
`nexus0_report.json` ni `nexus0_cuerpo1_report.json` (puedes leer el
segundo).

JSON mínimo:

```
alpha_shift, gamma, R (copia, para ver que no se tocaron)
curriculum: lista {dist, turns, goal_hits_in_phase}
exam_start: "(0,0,E)"
exam_turns
exam_goal_hits     # KPI > 0
exam_reward_sum
exam_bumps
q_approach_along_a_path_from_start   # para ver si el 0…0 se llenó
false_facts, destroyed, cortex_calls, questions  # 0
green
```

`green()` exige el examen en START canónico, no en un START movido.

---

## Tests (`TestWalk1`)

1. `test_exam_is_canonical_start` — el probe greedy usa `(0,0,E)`, no
   una pose a distancia 1.
2. `test_goal_hits_positive` — el número.
3. `test_rewards_and_alpha_untouched` — constantes iguales a CUERPO-1 /
   `constants.py`.
4. `test_no_hardcoded_path` — `body.py` (y lo que añadas) no contiene
   una secuencia literal de poses del bucle este-norte como política.
   Grep de `"(4,0,N)"` como acción impuesta = rojo si decide el acto.
5. `test_cortex_off`.
6. `test_cuerpo1_report_untouched` y anillo `nexus0_report.json` bytes.
7. Mutante documentado: si el examen teleporta a distancia 1, el test
   `test_exam_is_canonical_start` se pone rojo (no lo implementes mal
   para “pasar”).

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
```

Tests ≥ 238. Candados del anillo iguales.

---

## Informe que me pegas a Grok

- distancias del curriculum y turnos por fase
- `exam_goal_hits` y si el camino greedy es el bucle de 10 u otro
- Q desde START (¿sigue `0 0 0…`?)
- archivos tocados
- si falló: dímelo claro, no retunees R
