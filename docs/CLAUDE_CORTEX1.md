# CLAUDE — CORTEX-1 (pegar tal cual)

Lees **antes de tocar código**: `echoai/CLAUDE.md`, `echoai/CLAUDE_SITUATED.md`
(programa situado **cerrado**, no lo reabras), `echoai/docs/NEXT_APPROACH.md`
§ CORTEX-1, `echoai/docs/GROK_HANDOFF.md` §5 y §8.

Eres implementador. Un slice. Un KPI. No rediseñes. No descargues un LLM.
No toques kernel, ISO, `plan.py`, `oracle.accept`, `parse_reply`, `thought.KEYS`,
el anillo de 32 como mundo de este KPI, ni `lab/nexus0_report.json`.

---

## Qué construyes

El córtex **cambia una decisión de verdad**. Hoy, si `parse_reply` devuelve
UNIR / TEMER / OBSERVAR, `loop.py` lo **ignora**. Solo si `rel == PREGUNTAR`
llama a `_ask()`. Ese cable es el corazón del slice.

Un **env nuevo** (no el anillo, no el pasillo). El mundo muestra un **letrero
en lenguaje**. El rápido ve WSP/Q/T y **no** entiende el letrero. Sin córtex,
en greedy, Q en empate elige `wait`. Con córtex, un script (no un 4B) lee el
letrero y propone UNIR o TEMER. El gate sigue teniendo la última palabra.
La hipótesis **nunca** se escribe como hecho.

No es AGI. No es enchufar Qwen. Es: una acción distinta de Q y distinta de
PREGUNTAR, con `false_facts=0`, y el anillo default intacto.

---

## El mundo (`echoai/nexus0/sign.py`)

Como `corridor.py`: sucesor por **tabla**, no `(i+1)%n`. Cuatro celdas
como mucho. Mismas 3 acciones. `Agent` ya admite `env=`.

```
SIGN (índice 0, KIND_EMPTY)  --approach-->  NEXT (índice 1)
```

Dos layouts, **mismo** índice y **mismo** kind en SIGN. El WSP de SIGN es
idéntico en ambos (`encode_cell(0, EMPTY)`). Lo único que cambia es el
`extract` (el letrero) y la física del `step`:

| layout | extract en SIGN (exacto) | `step(approach)` en SIGN |
|---|---|---|
| `prize` | `AMBAR: entra. El siguiente sitio es el premio.` | `r = R_SUCCESS` (+16), ir a NEXT |
| `trap`  | `AMBAR: no entres. El siguiente sitio es una trampa.` | `r = R_THREAT` (−16), ir a NEXT |

- `KIND` de SIGN es **EMPTY** en los dos. No uses `KIND_NOVEL` (dispararía
  PREGUNTAR). No pongas `KIND_THREAT` en SIGN (el gate podría MODIFY).
- NEXT puede ser GOAL en prize y THREAT en trap; no es el KPI. El pago que
  cuenta es el de `approach` **desde** SIGN.
- `wait` en SIGN: `r = 0`, quedarse.
- `avoid` en SIGN: `r = 0`, quedarse (no hace falta un cuarto sitio).
- `reveal()` existe y no hace nada útil. `RingEnv.ask()` sigue **sin existir**.
- Arranca en SIGN (`i = 0`). Contrato de env: `cell/step/reset/teleport/reveal`
  y atributo `kind` (lista), igual que el pasillo.

El letrero lo entrega el **env**, como el anillo entrega `cell=11 kind=NOVEL`.
El LLM (hoy el stub) interpreta y emite **acción**. No escribe
`has_fact` del tipo “amber=premio”. `has_fact` significa “había un letrero”,
no “el letrero decía la verdad”.

`Cell.extract` hoy es `cell={i} kind={NAME}`. El anillo y el pasillo no
pueden cambiar ese string. Añade un override **opcional** (`extract_text=None`)
que el anillo **nunca** setea. Tests de extract del anillo siguen iguales.

---

## El cable (el que el informe de ChatGPT dio por hecho)

Hoy, al final de `_attend`:

```
if rel_of(wsp_c) == ATOM_ID["PREGUNTAR"]:
    self._ask(...)
return True
```

CORTEX-1:

```
ATTEND on
  → propose() stub
  → complete() si NAVI_CORTEX_CMD
  → parse_reply
  → si rel ∈ {UNIR, TEMER, OBSERVAR}:
        last_cortex_action = approach | avoid | wait   # hipótesis
  → si rel == PREGUNTAR: _ask()  (sin cambio; no cuenta como decision_change)
  → si reject: last_cortex_action queda None; decide Q
gate(proposed)
T.predict(a); env.step(a); observe; Q.update
```

Mapeo **ya existe**. No inventes otra tabla:

```
constants.ACTION_REL = (REL_UNIR, REL_TEMER, REL_OBSERVAR)
# índice 0 approach, 1 avoid, 2 wait
```

Reglas del cable:

1. El córtex **propone** al gate. No llama `env.step`. No escribe CAM, T ni Q.
2. `last_cortex_action` vive **un turno**. `_propose` lo consume si no es
   None; si es None, el camino de siempre (`q.select` / escalate / plan).
3. Exploración: en este experimento las sondas van con `greedy=True`, así
   Q en empate es `wait` (`q.best`), no el `approach` de entrenamiento en
   fila [0,0,0]. No cambies `q.select`.
4. PREGUNTAR no setea `last_cortex_action`.
5. `parse_reply` **no se toca**. `@AHORA` sigue obligatorio. Prosa → None.
6. `CMD_TIMEOUT_S = 10` se queda (el stub responde al instante).
7. `thought.KEYS` **no se amplía**. Eso es GUI-1.

No añadas `REASON_SIGN` a `attend.py` si eso puede disparar en el anillo.
En el primer turno greedy en SIGN, Q está empatada y `hits < SETTLED_HITS`,
así que ATTEND ya despierta por `REASON_LOW_C` (o MISS). Mídelo. Si no
despierta, dímelo claro: no subas los wakes del anillo por encima de 36/256
para arreglarlo.

---

## El “córtex” de CI (sin pesos)

`echoai/nexus0/tools/sign_cortex.py`

- stdin: el JSON de un turno (`cortex_turn.build`: tiene `extract`).
- stdout: **una** línea que `parse_reply` acepta, nada más.
- Regla: si `extract` contiene `no entres` → `YO → TEMER → AQUI @AHORA`
  else si contiene `entra` → `YO → UNIR → AQUI @AHORA`
  else → no imprimas átomos (el loop debe contar reject y caer a Q).
- Sin dependencias. Sin red. Sin modelo.
- Tests lo invocan con `NAVI_CORTEX_CMD` (monkeypatch / `os.environ`).

Opcional, no bloquea el verde: `echoai/nexus0/cortex.gbnf` que genere
exactamente `SRC → REL → DST @ TIME` con átomos de `ATOM_ID`. Nadie lo
ejecuta en CI. Es el contrato para un llama.cpp futuro.

**Prohibido en este slice:** descargar Qwen, llama.cpp, GGUF, bitsandbytes,
API HTTP, `navi10_engine.think`. El 4B es un informe **después**, con
host y quant etiquetados. Los tests no pueden exigir un binario de 2.5 GB.

---

## Informe

Módulo ejecutable, como el pasillo:

```
PYTHONPATH=. python3 -m echoai.nexus0.sign
```

Escribe `echoai/lab/nexus0_cortex1_report.json`. **Nunca** pisa
`nexus0_report.json` ni `nexus0_cortex_report.json` (ese es el `--cortex`
del anillo, 36/256).

Sonda (no 256 turnos): mismo seed, `greedy=True`, arrancar en SIGN, 1 turno
es suficiente para el KPI; 8 si quieres ver que no se rompe. Dos agentes:

- rápido: `Agent(cortex=False, ask=False, env=SignEnv("prize"))`
- córtex: `Agent(cortex=True, ask=False, env=SignEnv("prize"))` con
  `NAVI_CORTEX_CMD` apuntando al stub.

Repite trap.

Campos mínimos del JSON:

```
false_facts, destroyed
prize_fast_action, prize_cortex_action, prize_fast_reward, prize_cortex_reward
trap_fast_action, trap_cortex_action, trap_fast_reward, trap_cortex_reward
decision_change          # True si alguna acción córtex ≠ Q.best y ≠ PREGUNTAR
cortex_calls, cortex_rejected
CortexROI                # prize_cortex_reward - prize_fast_reward  (entero)
ring_wakes_unchanged     # Agent(cortex=True) en RingEnv, 256 turnos → 36
```

`CortexROI` es resta de enteros. No inventes un float IG_q.

---

## KPI (todos a la vez; si uno falla, rojo)

```
false_facts = 0
destroyed = 0
anillo default intacto:
  cortex_calls = 0 en bench sin flags
  policy_after = [-12, 5, 0]
  novel_approach_return = +80
  surprise_known = 1
  ATTEND en el anillo con --cortex sigue 36/256  (no más)

en CORTEX-1 / prize, greedy, turno 0:
  cortex_calls ≥ 1
  prize_fast_action  = wait
  prize_cortex_action = approach
  prize_cortex_reward > prize_fast_reward
  CortexROI > 0

en CORTEX-1 / trap, greedy, turno 0:
  trap_cortex_action = avoid          # no approach; no wait
  trap_fast_action   = wait

esa acción no es PREGUNTAR
cortex_rejected no esconde el resultado
  (si rejected ≈ calls, el stub no habla átomos: slice rojo)
```

No cuentes PREGUNTAR como “el córtex cambió algo”. El stub del anillo ya pregunta.

---

## Tests (en `echoai/tests/test_nexus0.py`, clase nueva `TestCortex1`)

Que fallen si el mérito es teatro:

1. `test_sign_extract_is_language_not_kind` — SIGN es EMPTY en prize y trap;
   los extractos son distintos; `encode_cell` de SIGN es **el mismo** bytes.
2. `test_greedy_fast_waits` — sin córtex, `turn(0, greedy=True)` en SIGN
   es `ACTION_WAIT`, reward 0.
3. `test_stub_prize_approaches` — `NAVI_CORTEX_CMD` = stub; prize → approach,
   reward +16; `cortex_calls ≥ 1`; `questions == 0`.
4. `test_stub_trap_avoids` — trap → avoid; reward 0; no approach.
5. `test_prose_cmd_falls_back_to_q` — CMD imprime `amber means goal\n`;
   `parse_reply` None; `cortex_rejected ≥ 1`; acción = wait; `false_facts=0`.
6. `test_unir_is_proposal_not_fact` — tras UNIR, `has_fact` del slot SIGN
   no se vuelve un hecho nuevo del tipo “amber=premio”; CAM no crece por
   la hipótesis. El extracto del letrero puede estar (lo puso el env).
7. `test_gate_still_runs` — si el env marca `threat` o inhibit en un caso
   sintético, el córtex no salta el gate. (Si no hay un hook limpio sin
   romper SIGN, un monkeypatch de `gate` que cuente la llamada basta.)
8. `test_parse_reply_untouched` — `YO → UNIR → AQUI @AHORA` sigue pasando;
   `YO → UNIR → AQUI` (sin @) sigue None; prosa sigue None.
9. `test_thought_keys_untouched` — `set(rec) == set(thought.KEYS)` sigue.
10. `test_ring_locks` — `run()` default: `cortex_calls=0`,
    `policy_after==[-12,5,0]`, `novel_approach_return==80`.
11. `test_ring_attend_still_36` — `Agent(cortex=True)` 256 turnos en el
    anillo: `cortex_calls == 36`. Si sube, el slice está rojo.
12. `test_report_file_is_own` — el experimento escribe
    `lab/nexus0_cortex1_report.json` y no toca `lab/nexus0_report.json`.

No alargues `BENCH_TURNS`. No toques `SETTLED_HITS`. No IG_q float.

---

## Qué no tocas (cerrado)

`plan.py`, `escalate.py` (política del anillo), `oracle.py` / `accept`,
`parse_reply` (el regex, los átomos), `RingEnv` geometría, JUMP, pasillo,
`view.py`, `demo.py`, `thought.KEYS`, kernel, ISO, Akida, FAISS, MiniGrid,
8 acciones, planner always-on, descargar pesos.

`--cortex` del anillo sigue siendo el stub PREGUNTAR. No lo conviertas en
UNIR. El ROI del anillo con stub seguiría siendo teatro.

---

## Verificación que me pegas al terminar

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench          # candados, cortex_calls=0
PYTHONPATH=. python3 -m echoai.nexus0.sign           # informe CORTEX-1
```

Pega: nº de tests (antes 155), el JSON `nexus0_cortex1_report.json`,
`policy_after` del bench default, `cortex_calls` del anillo `--cortex`
si lo corriste (debe seguir 36), y **qué archivos tocaste**.

Si ATTEND no despierta en SIGN, o si `q.select` (no greedy) te iguala
UNIR con approach por el empate-explora, **no** retunees Q ni el anillo:
dímelo claro. El slice no está verde.

Si el stub es el único “córtex” y CortexROI>0, el slice **está verde**.
Eso es exactamente el punto: el cable, no la marca del modelo.
)
