# CLAUDE — PULPO-C (reorientación; pegar tal cual)

PULPO está **rojo medido** en la pata 3. No lo maquilles. No retunees
`R_*`, `ALPHA_SHIFT`, `GAMMA_*`. No traces, no n-step, no planner, no
4ª acción, no `if block: avoid`, no waypoints, no lista de poses en el
examen. No descargues un LLM. No toques kernel, ISO, `parse_reply`,
`encoder.py`, `constants.py`, `body.py`, `graph.py`, `sign.py`,
`board.py`, `thought.KEYS`, `plan.py` default 0, ni
`lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/qtable.py` (`select`, `is_explore`,
`best`), `echoai/nexus0/body3d.py` (`experiment`, `value_horizon`,
`turn_poses`, `green`), `echoai/lab/nexus0_pulpo_report.json`,
`echoai/docs/CHATGPT_ECHO1_VERDICT.md` § cómo se cierra PULPO.

Eres implementador. Un slice. Un KPI.

---

## Qué está demostrado (no lo reabras)

```
open   exam_open_goal_hits=56  reward=896  9 poses  llegó (2,2,2)
T      70/70 vs stepper 4/70   stepper falló 38 (heading y piedra)
block  exam_block_goal_hits=0  reward=-32  trail (2,0,0,+Y) wait
desvío 18  >  value_horizon 11
open_route_is_learnable true    (2 giros, los dos contra piedra)
block_route_is_learnable false  (12 giros, 3 al aire)
select fila plana → siempre approach
best   empate → wait
curriculum  solo poses_by_distance(OPEN)
green() false   runner rc=1
expectedFailure  test_exam_block_goal_hits_positive
```

Búsqueda exhaustiva ya hecha: 0 geometrías con las dos rutas ≤11 **y**
todos los giros contra piedra. No la repitas con el mismo predicado.
El predicado cambia si una fila plana puede probar `avoid`.

WALK-1 sin resto se queda `expectedFailure`. CREDIT-1 se queda.

---

## El KPI

```
exam_block_goal_hits > 0
exam_block_corridor.used_the_detour
exam_open_goal_hits  > 0     # no romper el brazo que ya anda
green() true
córtex 0, questions 0, false_facts 0, destroyed 0
anillo default: policy_after [-12,+5,0], novel_approach_return +80
```

Examen **greedy**, START canónico, remainder on, 3 acciones. El tapón
sigue siendo un voxel del corto; el largo sigue conectado. Mismo Agent:
entrena, examina `open`, enchufa el tapón **sin** resetear Q/T/CAM,
se adapta, examina `block` greedy desde START.

Cuando el block cobre, **promociona** `test_exam_block_goal_hits_positive`
(quita `@expectedFailure`). No dejes un expectedFailure que ya pasa.

---

## Qué construyes (dos palancas, no una)

### 1. Exploración en fila plana — opt-in

Hoy `qtable.select`: fila `[0,0,0]` → `ACTION_APPROACH` siempre, incluso
en turno de exploración. Por eso un giro al aire libre es invisible.

Flag **nuevo**, default **False** (el anillo no se entera):

```
# idea, nombres a tu criterio, un solo sitio
if explore_flat and row is full tie and not greedy:
    return turn % N_ACTIONS     # puede ser avoid
else:
    # bytecode de hoy
```

Memoria extra: **cero**. No toques `update`, remainder, ni `best()`.
Tests: default off ⇒ `select` en fila plana sigue devolviendo approach
(el test que ya exista, o uno nuevo). Flag on ⇒ en algún turno de tren
sale `avoid` desde `[0,0,0]`.

El Agent del pulpo enciende el flag. `Agent()` del banco no.

### 2. Geometría con desvío ≤ horizonte, y el tren visita el desvío

`value_horizon()` = 11 con los enteros de serie. Un desvío de 18 **no
puede** tener Q>0 en el START, da igual cuánto explores. Si dejas el
cubo actual, el KPI es aritméticamente imposible.

Dentro de 3×3×3×6=162 (no 4×4×4):

- corto más barato que el largo; los dos andables en `open`
- un tapón en el corto; el largo intacto
- `detour_cost_block <= value_horizon()`   # ≤11
- `start_distance_open > 5`                # no un vecino del GOAL
- corredores disjuntos en el medio (solo START y GOAL compartidos)
- START documentado; canónico preferido `(0,0,0,+X)` si existe un par

Tras el tapón, **curriculum inverso en `block`** (teleport a poses a
distancia d del GOAL en el layout tapado, remainder on, `explore_flat`
on, córtex off). El prompt PULPO ya pedía visitar el desvío en el tren;
`experiment()` hoy solo usa `poses_by_distance(OPEN)`.

Después: `_exam` greedy desde START, igual que ahora. `_exam` **sigue**
sin `NEXT`, sin `SHORT_PATH`, sin `ACTION_*`, un solo `teleport(START)`.

Si **no** existe un par de corredores que cumpla desvío≤11 con
`explore_flat`: **para**, `green=false`, escribe el recuento. No n-step.
No alargues el horizonte a mano. Eso sería otro tajo (PULPO-H).

---

## Informe

Sigue siendo `lab/nexus0_pulpo_report.json`. Añade, no borres:

```
explore_flat                 true en este Agent
value_horizon                (sigue 11)
detour_cost_block            (ahora ≤11, o el recuento de por qué no)
readapt_turns                turnos del curriculum en block
exam_block_goal_hits
used_the_detour
block_route_is_learnable     (redefine discoverable: giro al aire = sí
                              cuando explore_flat)
turn_is_a_cycle              el anillo REAL (+X,+Y,+Z,-X,-Y,-Z), no el
                              string stale
```

`green()` ya exige block hits y `used_the_detour`. No lo debilites.

Runner rc=0 solo si `green()`. Banco:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d
```

---

## Tests

`TestPulpo` se queda. Cambia lo mínimo:

1. `test_exam_block_goal_hits_positive` — sin expectedFailure cuando
   el informe cobre. Un test nuevo que **pincha** `exam_block_goal_hits==0`
   es mentira el día que cierre: bórralo o condicionalo al informe.
2. `test_the_blocked_arm_is_red_for_two_measured_reasons` — o se
   reescribe como historia del rojo anterior, o se sustituye por
   “con explore_flat el desvío es aprendible y cobra”. No dejes un
   assert `==0` que falle el día verde.
3. Flag off: `select` en `[0,0,0]` = approach. Anillo `[-12,+5,0]`.
4. `test_no_hardcoded_path` sigue leyendo `_exam`.
5. `detour_cost_block <= value_horizon` en el informe verde.

---

## Qué no es este tajo

SELF-1, rooms, ABRIR, objeto X→Y, traductor, PATTERN-0, U/A decay,
n-step, remainder default-on, 24 orientaciones, córtex.

Si el block cobra: pulpo **cerrado**. ECHO-1 empieza en SELF-1, no aquí.
