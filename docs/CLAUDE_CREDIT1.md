# CLAUDE — CREDIT-1 (pegar tal cual)

WALK-1 está **rojo medido**, no fallido por vago. No lo maquilles.
No retunees `R_*`, no bajes `ALPHA_SHIFT` en el default, no traces,
no planner always-on, no hardcodees el camino, no muevas el START
del examen. No descargues un LLM. No toques kernel, ISO, `parse_reply`,
`encoder.py`, `world.py`, `graph.py`, `sign.py`, `board.py`,
`thought.KEYS`, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/qtable.py` (`update`, `ALPHA_SHIFT=2`),
`echoai/nexus0/body.py` (`credit_chain`, `walk`, `_exam`),
`echoai/lab/nexus0_walk1_report.json`, `echoai/docs/CHATGPT_SCALE_VERDICT.md`
§ residual.

Eres implementador. Un slice. Un KPI.

---

## Qué está demostrado (no lo reabras)

```
credit_chain(shift=2, 12) = [13, 8, 4, 0, 0, …]
credit_chain(shift=0, 12) = [16, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1, 0]
Q medido por distancia     {0:13, 1:8, 2:4, 3:0, …}
examen (0,0,E)             goal_hits=0, poses_visited=1
curriculum                 cobra en d=1..5; el muro no se mueve
```

`q += delta >> 2` tira δ∈{1,2,3}. El START está a 9. Una sonda
`ALPHA_SHIFT=0` (fuera del repo) cobró 12 veces: el bloqueo es **solo**
ese truncamiento. WALK-1 lo dejó en `expectedFailure`. Ese test **sigue**
expected-failure sobre `walk()` **sin** resto. El verde nuevo es **otro**
informe.

---

## Qué construyes

Un **resto entero** opt-in en `QTable.update`. α sigue siendo 1/4.
No hay float. Default **off**: el anillo no se entera.

```
# idea (hacia cero, no el >> aritmético de Python en negativos)

rem[s][a] += delta
step = trunc_div(rem[s][a], 4)      #  5→1,  3→0,  -3→0,  -5→-1
rem[s][a] -= step * 4
q[s][a]   += step                   # clip_i8 como ahora
```

`trunc_div(x, 4)` = signo(x) * (|x| >> 2). **No** uses `x >> 2` sobre
negativos en Python (`(-5)>>2 == -2`).

Memoria: `rem[4096][3]` int, estático, Heap-0, solo si el flag está
encendido. Si está apagado, **cero** arrays extra y el bytecode de
`update` es el de siempre (`q += delta >> ALPHA_SHIFT`).

El Agent gana un kwarg `remainder: bool = False` (o el QTable se
construye con él). Banco default: False.

---

## KPI (todos a la vez)

```
1. walk() SIN remainder: exam_goal_hits=0, walk_green False
   (WALK-1 no se reescribe; expectedFailure sigue)

2. walk CON remainder:
   examen (0,0,E), greedy, córtex off, R/α/γ iguales
   exam_goal_hits > 0
   false_facts=0 destroyed=0 cortex_calls=0 questions=0
   informe lab/nexus0_credit1_report.json
   NUNCA pisa nexus0_report.json ni nexus0_walk1_report.json
   (este último se puede regenerar, bytes de WALK-1 rojo se quedan)

3. banco anillo SIN remainder: policy_after [-12,+5,0], +80,
   surprise_known=1, cortex_calls=0, 33/1/217

4. credit_chain(2) sigue prediciendo el muro (no se toca la fórmula
   de α; el resto es otro camino)
```

**No hardcodear** el camino. El curriculum de WALK-1 se puede reutilizar
(`walk(remainder=True)`). El examen teleporta a `START`. Si con resto
sigue en 0, slice rojo — dímelo claro, no retunees R.

n-step no es este slice. Trazas no. `ALPHA_SHIFT=0` no.

---

## Tests

1. `test_remainder_off_is_the_old_shift` — update sin flag: Q igual
   que hoy (δ=3 no mueve Q; δ=4 mueve +1).
2. `test_remainder_keeps_the_crumbs` — tres updates con δ=3 → al
   tercero Q +=1 y rem=1 (números exactos, no “aprox”).
3. `test_negative_truncates_toward_zero` — δ=-3 tres veces no aplica
   -2 por el >> de Python.
4. `test_ring_default_has_no_remainder` — Agent() / bench:
   `remainder is False`; `policy_after` candado.
5. `test_credit1_exam_hits_from_canonical_start` — el KPI.
6. `test_walk1_without_remainder_still_red` — `walk()` sin flag,
   `exam_goal_hits==0`.
7. `test_does_not_touch_alpha_or_R`.
8. `test_no_hardcoded_path` (el de WALK-1, sobre el examen con resto).

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body --walk          # rc=1, sigue
PYTHONPATH=. python3 -m echoai.nexus0.body --walk-remainder  # rc=0
```

Tests ≥ 249. Un expectedFailure (WALK-1 sin resto) se queda.

---

## Informe que me pegas a Grok

- `exam_goal_hits` con resto, START, Q a lo largo del camino
- candados del anillo (copia `policy_after`, +80)
- cuánto vale `rem` típico
- archivos tocados
- si el anillo CON remainder (sonda, no default) mueve candados:
  **mídalo y dímelo**, no lo enciendas
