# echoAI — briefing para Gemini (cierre del programa situado)

**Fecha:** 2026-09-03.
**Repo:** `/home/roger/REALRXOS/RXos` (workspace `echoai/` dentro de ese árbol).
**Estado:** el programa científico de este directorio **está cerrado**. Esto no es AGI. Es un MVP que se puede ver pensar en una terminal.
**Cómo verlo:** desde la raíz del repo, `PYTHONPATH=. python3 -m echoai.nexus0.demo`
**Cómo comprobar:** `PYTHONPATH=. python3 -m echoai.tests.test_nexus0` (153+ tests).

Este documento existe para que puedas discutir el **futuro** del proyecto con todos los hechos encima de la mesa. No reescribas la tesis. No conviertas números de juguete en claims de inteligencia general. Si una idea choca con un invariante, gana el invariante.

---

## 1. Qué es, en una frase

echoAI es un **agente de dos relojes** cuyo núcleo funciona **con el córtex apagado**: percibe, recuerda, predice, actúa y aprende sobre un cable discreto de 16 bytes (WSP). Un modelo de lenguaje, si se enchufa, es el reloj lento: propone hipótesis. Nunca escribe hechos.

Formulación que el laboratorio acepta:

> echoAI = un sistema cognitivo de dos tiempos, donde el estado rápido aprende y controla, el sistema lento abstrae y propone, y **ninguno de los dos tiene por sí solo la representación completa de la realidad**.

Tesis que ChatGPT researcher firmó y el lab adoptó:

> EchoAI **no** se investiga como “SNN + LLM”. Se investiga como arquitectura de aprendizaje **situada**: WSP/QN espacio discreto compartido, CAM memoria, T dinámica, Q política, ATTEND cuándo gastar cómputo cortical, córtex hipótesis que deben sobrevivir al basal.

Hipótesis operativa:

> Intelligence ≈ representation + memory + prediction + action + learning + information acquisition.

La prueba que esa tesis pedía (y que este programa cerró en miniatura):

> El agente cambia de comportamiento **correctamente** después de descubrir que su modelo del mundo estaba equivocado — en un mundo que **no** sea solo el anillo de 32 celdas — sin dejar de preguntar, sin planificar de más, sin córtex si lo barato basta.

---

## 2. Qué no es

- **No es AGI.** La escalera del propio laboratorio termina en NEXUS-7 (transferencia de tarea abierta). **No hay NEXUS-8 “AGI”.** AGI no es KPI de ningún slice.
- **No es un chatbot.** No hay conversación. No hay HTTP. El banco principal no llama a ningún LLM.
- **No es “SNN + LLM” como producto.** Esa etiqueta se descartó.
- **No es un cerebro humano.** No hay emoción sentida, no hay consciencia, no hay “alma en E[6]”.
- **No es echOS 2.1.** El unikernel es el cuerpo de Rogex. echoAI **no** entra en la ISO. NEXUS-0 corre en host Python e **importa** primitivas de navi10; no envuelve `navi10_engine.think`.
- **No es Akida.** Hay 0 placas AKD1000. El bucle rápido es software. Akida, si algún día existe, acelera poblaciones (cabeza de 3 acciones, novedad, secuencia). Nunca VERIFY, nunca hechos, nunca veto, nunca IRQ/disco/`G_rxos`.
- **No es navi10 `--ask`.** Eso es un router (intent → plantillas / RAG → compositor). echoAI no se construye alrededor de ese router.
- **No es el teseracto de `./navi10 --tui`.** Eso es otra cara. Ver pensar echoAI es `python3 -m echoai.nexus0.demo`.

Frase que el lab **no cita** como world model: T = 0.9964 en el anillo liso. Eso es “T acierta el anillo casi tanto como la aritmética i±1”. El resultado que sí se cita es **JUMP**: T aprende dos celdas que saltan +2, y gana a esa aritmética.

---

## 3. Si el LLM es el neocórtex, ¿qué tenemos ahora?

El laboratorio **descartó** la metáfora de marketing “AKD1000 = cerebro reptiliano, LLM = neocórtex” como *claim de producto* y como árbol de directorios biológicos (`nexus/amygdala.py`, etc.).

Lo que **sí** se mantiene, y es la analogía útil para discutir el futuro:

> Si en este sistema hay un neocórtex, es un **LLM detrás de un firewall**, apagado por defecto, que solo emite hipótesis en el mismo cable de 16 bytes. El resto del sistema nervioso **tiene que funcionar con ese neocórtex desenchufado**. Eso es lo que está construido.

### Mapa (analogía, no anatomía)

| Analogía que usamos | Pieza real | Qué hace, en claro | Estado |
|---|---|---|---|
| Código nervioso común | **WSP 16 bytes** | Un paquete: quién → verbo → qué, más 6 números de modulación. No hay un segundo bus de “pensamiento”. | hecho |
| Sentidos / cifrado | **encoder** | Texto o celda del mundo → el mismo paquete de 16 B. Un miss es DESCONOCIDO, no un hash. FNV (hash) pierde a propósito. | hecho |
| Memoria de lo percibido | **CAM 4096 ranuras** | “¿He visto este paquete?” Episodios, no política. | hecho |
| Predicción (“si hago esto, ¿qué pasa?”) | **T(s,a) → s'** | Modelo del mundo, enteros, con conteo y conflictos. | hecho |
| Certeza de esa predicción | **T_CONF 0–3** | Nunca / una vez / consistente / muy consistente. Un conflicto impide el 3. | hecho |
| Gramática causal inversa | **I(s,s') → a** | “¿Qué acción me trajo aquí?” Solo vecinos vistos, no una matriz 4096². | hecho |
| Hábito / valor de acción | **Q[4096][3]** | Acercarse, alejarse, esperar. 12 KiB. Enteros. | hecho |
| Reflejo / veto | **gate** | Puede bloquear o modificar la acción propuesta. | hecho |
| Modulación (no “sentir”) | **E[6] int8** | Valencia, arousal, dominance, certainty, urgency, bond. No es emoción sentida. δ **no** vive en E[V]; vive en Q. | hecho |
| Atención (“¿merece pensar caro?”) | **ATTEND** | Despierta el reloj lento solo si el rápido no basta. 36 de 256 turnos. | hecho |
| Pedir información | **PREGUNTAR + oráculo fuera** | No es una 4ª marcha. El mundo **no** contesta. Un sensor / archivo / callable contesta. VERIFY decide si es un hecho. | hecho |
| Planificar un paso más | **plan.py** | Módulo. Apagado por defecto. En este anillo, pensar más **copia** a Q (`search_strictly_better = 0`). Sirve en celdas concretas (c9, 8→11). | hecho, no siempre-on |
| Neocórtex | **LLM** | Socket: `parse_reply` (solo átomos, tira prosa), `complete()` vía `NAVI_CORTEX_CMD` (subprocess, no HTTP). El stub actual propone el mismo PREGUNTAR que el rápido ya sabe hacer. | **enchufe vacío**. Off por defecto. `cortex_calls = 0` en el banco principal |
| Sueño / consolidación | NEXUS-5 | Episodios → reglas T estables, sin reentrenar Q con prosa. | **no hecho** |
| Cuerpo | NEXUS-6 / echOS / sensores | El mismo bucle en C, o sensores reales. No es la ISO 2.1. | **no hecho** |
| Silicio neuromórfico | Akida AKD1000 | 0 placas. Sensing futuro, nunca VERIFY. | **ausente** |

En una frase para un humano:

> Tenemos el animal que camina, recuerda, se equivoca, pregunta y aprende **sin corteza**. La corteza es un enchufe. Todavía no hay nadie al otro lado. El firewall ya está: si alguien enchufa un LLM que habla en prosa, esa prosa **no** se convierte en hecho.

---

## 4. El bucle de un turno (lo que “pensar” significa aquí)

```
S_t  →  A_t  →  Ŝ_{t+1}  →  S_{t+1}  →  δ_t  →  aprendizaje
```

En el código (`echoai/nexus0/loop.py`, `Agent.turn`):

1. Ver la celda. Codificarla a WSP 16 B. Buscarla en CAM (¿es nueva?).
2. Si el córtex está *enchufado*, ATTEND decide si despertarlo. Por defecto no lo está.
3. Si hay un misterio (celda NOVEL) y preguntar está on, emitir PREGUNTAR. El **oráculo** (no el mundo) contesta. `accept` verifica. Solo entonces `reveal` desarma la trampa.
4. Q (o, si se pidió, el planner / la escalada) propone una acción: approach / avoid / wait.
5. El gate puede vetarla.
6. T predice adónde se llegará.
7. El mundo ejecuta. Llega una recompensa entera.
8. Se observa T (el mapa se corrige). Se actualiza Q (la política se corrige).
9. Se escribe una línea en `thought.jsonl` si se pidió.

Tres aprendizajes distintos, ya no una palabra (`N ≠ S ≠ δ`):

| Nombre | Qué es | Default 352 turnos |
|---|---|---|
| N `cam_misses` | primera vez que el agente **pisa** este origen | 33 |
| S `surprises` | T tenía predicción **y** estaba mal | 1 |
| δ `deltas` | Q se movió (`update` ≠ 0) | 217 |
| `surprise_known` | S sin N (sitio conocido, mapa equivocado) | **1** (fase F, celda 5) |
| `novel_no_surprise` | N sin S | 33 |
| `delta_only` | Q se mueve sin N ni S | 208 |

Definición que hubo que medir: `navi10_cam.Cam.put()` siembra `hits = 1`, así que N es `s.hits <= 1` después de asignar. Un miss de T (`T_MISS`) **no** es sorpresa: es ignorancia. `KIND_NOVEL` es un tipo de celda, no “nuevo para siempre”.

---

## 5. El mundo de juguete

**Anillo de 32 celdas** (`RingEnv`). Tres acciones. Premios enteros:

| Acción | Átomo WSP | Premio típico |
|---|---|---|
| 0 approach | UNIR | +16 en GOAL, −16 en THREAT, −16 en NOVEL hasta preguntar / +16 después |
| 1 avoid | TEMER | +8 en THREAT |
| 2 wait | OBSERVAR | 0 |

- Celdas JUMP (5 y 21): approach salta **+2**, no +1. El baseline aritmético no lo sabe; T sí.
- Celda NOVEL (11): un bit oculto que **la observación no ve**. Solo un extracto verificado (`NOVEL_CLEAR`) lo despeja.
- Fase F del banco: tras 256 turnos, la amenaza se mueve 7→8 y hay 64 turnos más (352 total).
- Semilla `BENCH_SEED = 20260903`. `BENCH_TURNS = 256`.

**Pasillo de 5 celdas** (`CorridorEnv`) — segundo mundo, no el anillo pintado:

```
HOME    A → B → C → D     D = GOAL, C = EMPTY
SHIFT   A → B → X → D     X = THREAT, C fuera del camino
```

Sucesor por **tabla**, nunca `(i+1) % n`. A, B, D conservan índice y tipo → el mismo paquete WSP → CAM/T/Q se arrastran. C y X son índices distintos. `home.kind == shift.kind` (nada se repinta; eso era fase F).

---

## 6. Resultados cerrados (los números que se pueden citar)

Reproducir, raíz del repo:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.corridor
PYTHONPATH=. python3 -m echoai.nexus0.demo --short
```

| Peldaño | Estado | Número que lo cierra |
|---|---|---|
| **NEXUS-0** memoria, política, aprendizaje, gate | cerrado | `policy_after = [-12, +5, 0]`: approach en la amenaza es negativo y pierde frente a avoid. `false_facts=0`, `destroyed=0`, `cortex_calls=0`. Encoder semántico gana a FNV (banco vendor 6/6 rel vs FNV 0/6). |
| **NEXUS-1** modelo del mundo ≠ fórmula del env | cerrado | `t_beats_ring` True. JUMP +2: T 0.9964 vs aritmética i±1 0.9715, mismos turnos. **No citar 0.9964 como world model**; citar JUMP. |
| **NEXUS-2** planner como módulo | cerrado | A distancia 2 ve un GOAL que profundidad 1 no ve. No muta Q ni T. Default `plan_depth=0`. |
| **NEXUS-2 en el anillo de 320 turnos** | **refutado** | plan-2 espera el 58 % de los turnos (T(s,wait)=s hace que wait se vea bien). Con descuento del bucle, plan-2 ≡ Q.best. En 32 celdas TD ya llena las filas vecinas. |
| **NEXUS-3** preguntar | cerrado | `novel_approach_return` **+80 preguntando, −80 ciego**. Una pregunta vale 160 puntos. `questions` 1 vs 0. La política de la amenaza **no** cambia. |
| **NEXUS-3 seeking** | honesto, no bajado | `novel_hits_greedy = 0`. Q[c0]=[0,0,0] → wait. Preguntar cambió el **valor** de la celda 11, no el mapa hasta casa. |
| **NEXUS-4a** ATTEND | cerrado | 36 wakes / 256. No pensar siempre. `--cortex` no mueve los candados. |
| **NEXUS-4b** hook cortical | cerrado | `parse_reply` acepta átomos / hex 16 B; tira prosa, JSON, claims. `complete()` solo si `NAVI_CORTEX_CMD`. Sin HTTP. |
| **NEXUS-4c** thought.jsonl + visor ANSI | cerrado | Una línea por turno. `python3 -m echoai.nexus0.view`. Ahora también `python3 -m echoai.nexus0.demo`. |
| **NEXUS-4d** T_CONF 0–3 | cerrado | ATTEND lo lee. Un conflicto impide 3. `--cortex` sigue 36/256. |
| **NEXUS-4e** inverso I | cerrado | I(s, T(s,a)) == a si n≥2. Lista por slot, máx 8. JUMP no vuelve como wait. El conflicto de fase F es de s', no de a. |
| **NEXUS-4f** escalada 0 vs 2, ΔQ | cerrado | Default sigue Q (monkeypatch de `plan.best` → lista vacía). `--escalate`, ESC_MARGIN=4: `search_strictly_better = 0`. 183 “differs” son un desempate wait vs approach, no mérito. ChatGPT tenía razón: en este anillo profundidad 2 copia a Q. `plan.py` se queda como módulo. Actuar el escalate **empeora** política `[-12,+5,0] → [-7,+5,0]`, retorno +80 → +48. |
| **NEXUS-4g** N ≠ S ≠ δ | cerrado | 33 / 1 / 217. `surprise_known=1` = fase F en celda 5, mismo slot CAM, `observe()` no asigna. |
| **NEXUS-4h** oráculo fuera | cerrado | `RingEnv.ask()` **no existe**. reply → accept → reveal. `accept` ≠ `parse_reply` (el mismo string “YO → PREGUNTAR → DESCONOCIDO @AHORA” lo acepta uno y lo rechaza el otro). Default `source=sensor`, +80 intacto. `--oracle PATH` es un archivo; prosa o ausente: 66 rechazos (la pregunta sigue abierta), retorno −80, `false_facts=0`. |
| **NEXUS-4i** pasillo / transferencia | cerrado | Ver §7. |

Candados que **ningún** slice mueve en el banco **sin flags**:

```
policy_after                 [-12, +5, 0]
false_facts                  0
destroyed                    0
cortex_calls                 0
encoder_beats_fnv            True
t_beats_ring                 True
novel_approach_return        +80
surprise_known               1
level_search                 0
oracle_source                sensor
```

`--cortex` wakes **36/256**, sin cambio a lo largo de T_CONF / inverso / escalate / N/S/δ / oráculo / pasillo.

---

## 7. El pasillo (el último experimento de este programa)

Mismo agente, mismo cable 16 B, mismas 3 acciones, **un mundo que no es 32 celdas**, T/Q del primero frente a Q=0.

Al **entrar** en SHIFT (antes de caminar):

| | T(B, approach) | conf | sin ver de {A,B,D} |
|---|---|---|---|
| transferido | **C** (conocido) | 3 | **0** |
| control (Q=T=0) | **None** | 0 | **3** |

Primeras visitas pagadas en la ventana SHIFT: transferido **1** (solo X, lo genuinamente nuevo), control **4**. `surprise_known`: transferido **14**, control **0** — el control no puede sorprenderse porque nunca predijo nada.

Primer paso equivocado: turno 97. Origen B, **mismo slot**, origen no es miss, conflicts sube, KCC mantiene al titular con una observación, X es paquete nuevo (N del destino). La forma de fase F, en otro mundo.

**KPI 4 no salió como se predijo, y no se retuneó.** Se esperaba que approach en B dejara de ganar tras el golpe en X. No deja de ganar, y converge ahí (comprobado a 512 turnos de SHIFT):

```
Q[B]  home [4, 0, 0]  →  shift [1, 0, 0]   sigue ganando approach
Q[X]  shift [-3, +5, 0]                    approach negativo, avoid paga
```

La política **sí se dobla** donde el mundo se movió (Q[B,approach] cae 75 %, Q[X,approach] se vuelve negativo). Lo que **no** hace es convertirse en rechazo: en SHIFT la única ruta a D **pasa por X**, y avoid en una amenaza paga `R_AVOID_OK`, así que max Q[X] se queda positivo y el backup de B con él. El agente aprende **“entra en X y luego esquiva”**, no “nunca entres en X”. El pasillo reutiliza el `_reward` del anillo; el test aserta lo medido.

Esto **no es AGI**. Es cinco celdas, un cambio de topología, una tabla transferida. Lo que muestra, estrecho: una T aprendida en un mundo sigue siendo cierta de la parte del siguiente que no cambió, se equivoca en la que sí, y se entera **equivocándose**, no porque se lo cuenten.

`_ask()` sigue cableado y no dispara (`questions = 0`): no hay KIND_NOVEL en el pasillo.

Informe: `echoai/lab/nexus0_corridor_report.json` (nunca pisa `nexus0_report.json`).

---

## 8. Firewall epistémico (lo que un LLM no puede romper)

Invariante I14: una hipótesis de córtex **nunca** se escribe como `has_fact=1`.

Tres canales que una LLM mezcla y echoAI obliga a no cruzar:

| Canal | Pregunta | Artefacto |
|---|---|---|
| Representación | ¿Qué ocurre? | WSP 16 B + vértice Q_N + CAM |
| Epistemología | ¿Lo sé? | VERIFY (Hamming ≤ 3 ∧ extracto) / DESCONOCIDO |
| Control | ¿Qué hago? | Q[s,a] + gate + 3 acciones |

Puertas distintas:

- **Sensor / oráculo** (`oracle.accept`): un extracto (`NOVEL_CLEAR`) o nada. Prosa, JSON, multilínea, hex WSP → None.
- **Córtex** (`cortex.parse_reply`): un paquete WSP de 16 B (átomos o hex). Prosa → None.
- El string `YO → PREGUNTAR → DESCONOCIDO @AHORA` **pasa** `parse_reply` y **falla** `accept`. Testeado.

`source=` es procedencia, no etiqueta:

| paquete | source |
|---|---|
| celda 11 | `nexus0-env` (lo percibió el anillo) |
| PREGUNTAR | `sensor` (default) o `file` (`--oracle PATH`) |

Nunca `nexus0-env` en la pregunta. Nunca `sensor` en la celda.

`--no-ask` es silencio (`Agent.oracle is None`), no un oráculo mudo.

---

## 9. Cómo probar el MVP en terminal

Desde `/home/roger/REALRXOS/RXos` (o el clone):

```bash
export PYTHONPATH=.

# Verlo pensar (córtex apagado, 5 fotogramas/s)
python3 -m echoai.nexus0.demo            # 352 turnos ~ 70 s
python3 -m echoai.nexus0.demo --short    # 48 turnos ~ 10 s
python3 -m echoai.nexus0.demo --replay   # si ya hay lab/thought.jsonl

# Laboratorio
python3 -m echoai.tests.test_nexus0
python3 -m echoai.nexus0.bench           # lab/nexus0_report.json
python3 -m echoai.nexus0.corridor        # lab/nexus0_corridor_report.json
python3 -m echoai.nexus0.tools.gen_lex --check
```

Leyenda del visor: `G` premio, `T` trampa, `N` misterio, `·` vacío, `@` el agente (fila propia, no tapa la N), `<` la acción, barras = Q de esa celda, `ATTEND OFF` casi siempre.

Flags del banco (cada uno escribe su propio JSON, no pisan el candado):

| Flag | Informe |
|---|---|
| (ninguno) | `lab/nexus0_report.json` |
| `--no-ask` | `nexus0_noask_report.json` (−80) |
| `--plan-depth 2` | `nexus0_plan2_report.json` |
| `--trace` | `nexus0_trace_report.json` |
| `--cortex` | `nexus0_cortex_report.json` + `cortex.jsonl` |
| `--thought` | `thought.jsonl` (352 líneas) |
| `--escalate` | `nexus0_escalate_report.json` |
| `--oracle PATH` | `nexus0_oracle_report.json` |

Documentación de usuario: `echoai/README.md`, `echoai/WATCH.md`.

---

## 10. Mapa de archivos

```
echoai/
  README.md                 puerta del MVP
  WATCH.md                  cómo ver el pensamiento
  CLAUDE.md                 invariantes para un implementador
  CLAUDE_SITUATED.md        programa situado (cerrado)
  docs/
    00-READ-ME-FIRST.md     tesis de una página
    01-INVENTORY.md         qué hay ya en RXos
    02-INVARIANTS.md        I1–I17
    03-HYPOTHESIS.md        dos relojes, tres canales
    04-DECISIONS.md         se queda / se tira
    05-NEXUS-0-SPEC.md      spec original
    06-LADDER.md            NEXUS-0 … 7; no hay 8 AGI
    07-AKIDA.md             0 placas; cerraduras
    08-SOURCES.md
    CHATGPT_REVIEW.md       qué firmó ChatGPT vs qué hizo el lab
    STATUS.md               cada peldaño y el número que lo cierra
    ECHOAI_FOR_GEMINI.md    este archivo
  nexus0/                   único código nuevo del sprint
    loop.py                 Agent, un turno
    env.py                  anillo 32
    corridor.py             pasillo 5, HOME/SHIFT
    world.py                T + conf + inverso
    qtable.py               Q, δ, margin, traces opt-in
    gate.py attend.py
    encoder.py lex.py       banco + lex 235 filas, sync con C
    plan.py                 lookahead, default off
    escalate.py             niveles 0/2; 1/3/4 nombrados no cableados
    oracle.py               Sensor / FileOracle / accept
    cortex.py cortex_turn.py
    thought.py view.py demo.py
    bench.py constants.py types.py
  tests/test_nexus0.py      KPIs
  lab/                      JSON + thought.jsonl + preview.txt
```

El resto del repo RXos es el **cuerpo** (unikernel, `kernel/include/wsp.h`, Q6) y el **sedimento** (navi5–navi10). NEXUS-0 **importa** `navi10_cam`, `navi10_qn`, `navi10_wsp`, `navi10_spoke`, `navi10_dag`. No los clona. No toca `kernel/` ni la ISO en este sprint.

WSP vendor (otro proyecto, v0.5) **no** es este WSP. Este es RogexWSP 16 B: src/rel/dst/time + E[6] int8 VAD-CUB.

---

## 11. Constantes congeladas (no cambiar sin banco)

```
CAM_SLOTS / N_SLOTS     4096
N_ACTIONS               3
WSP_BYTES               16
HAM_LIMIT               3          VERIFY: Hamming ≤ 3 ∧ extracto
Q int8                  ±127
γ                       7/8        (mismo leak LIF)
α                       1/4        (δ >> 2)
R_SUCCESS / R_THREAT    +16 / −16
R_AVOID_OK / R_WAIT     +8 / 0
C_PLASTIC               20
ATTEND_SETTLED_HITS     2
ESC_MARGIN              4          (Q units; barrido 2/4/8, mismo mérito 0)
T_CONF_HIGH_N           8
INV_MAX_ENTRIES         8
JUMP_CELLS              (5, 21)
N_CELLS anillo          32
BENCH_TURNS             256
BENCH_SEED              20260903
lex                     235 filas, sync con wsp_lex.c
```

Prohibido en el núcleo caliente: floats, vector DB, FAISS, segundo event-bus, meter δ en E[V], prosa → `has_fact`, LLM en el banco principal, clonar Layer256, driver Akida.

---

## 12. Lo que falta — dos listas distintas

### 12.1 Para **cerrar este proyecto** (hecho)

- Tesis situada, con números, sin AGI.
- Visor de pensamiento en terminal.
- Un comando (`demo`).
- README / WATCH / este briefing.
- Tests verdes, candados quietos.

Si “cerrar” significa “alguien clona el repo, corre un comando y ve a un agente equivocarse y aprender, sin LLM”, **está cerrado**.

### 12.2 Para un sistema nervioso **más completo** (otro proyecto)

No son deuda de este MVP. Son capítulos nuevos. El orden razonable, un KPI cada uno, si se reabre:

1. **Enchufar un LLM de verdad** detrás de `NAVI_CORTEX_CMD` + `parse_reply`. El stub hoy es el mismo PREGUNTAR que el rápido ya hace: medir CortexROI ahora daría ≈0 y sería teatro. KPI: el córtex cambia **una decisión** que el rápido no habría tomado, y 0 hechos nuevos sin extracto. `cortex_calls=0` sigue siendo el default.
2. **Sueño (NEXUS-5).** WAKE percibe y actúa; SLEEP convierte episodios consistentes en T estable. KPI: `prediction_accuracy` sube **sin** turnos nuevos de vigilia.
3. **Cuerpo (NEXUS-6).** El mismo bucle importando el C de Q6, o sensores reales. No es meter echoAI en la ISO 2.1.
4. **Transferencia abierta (NEXUS-7).** El pasillo es la miniatura. NEXUS-7 sería un segundo env que no sea 5 celdas de juguete. KPI de la escalera: Q/T del primero arrancan mejor que Q=0; si no, no hay transferencia que publicar.
5. **Akida**, si hay placa: sensing, nunca VERIFY. Cerradura 0 = simulador primero.
6. Cosas que **no** hacer: planner siempre on; córtex que predice s'; publicar T=0.9964 como world model; IG(question) como float (el +80/−80 ya es la ganancia); umbrales mágicos 1/100/1000 (primero T_CONF, ya existe); árbol de directorios “amígdala / hipocampo”.

### 12.3 Límites honestos del juguete actual

- 32 celdas, o 5. No es el mundo.
- 3 acciones. No es un cuerpo.
- El planner no aporta mérito en este anillo. En otro geometría podría. Por eso el módulo se queda y el default es 0.
- Desde casa (celda 0) el agente greedy **no arranca**: Q está a cero y wait gana el desempate. Preguntar cambió el valor del misterio, no el mapa hasta la puerta.
- JUMP a `conf=3` pediría ~1024 turnos (n=8). El banco no se alargó.
- El “neocórtex” es un stub. Nadie ha visto a echoAI discutir. Ha visto a echoAI **caminar, preguntar una palabra comprobable, y corregir un mapa**.
- E[6] no es un sentimiento.
- `R_AVOID_OK = +8` hace racional “entra en la amenaza y luego esquiva” cuando esa es la única vía al premio. No es un bug de Q; es el premio que hay.

---

## 13. Preguntas buenas para el futuro (no para reabrir este directorio a escondidas)

1. Si enchufamos un LLM, ¿qué decisión concreta tiene que cambiar para que CortexROI no sea teatro?
2. ¿El sueño debe compactar T, o también soñar contrafactuales con el planner (que en el anillo no pagó)?
3. ¿El siguiente mundo es otro pasillo discreto, un grid, o ya un sensor real?
4. ¿PREGUNTAR a un humano (archivo / stdin no interactivo ya existe como `--oracle PATH`) es el producto, o lo es PREGUNTAR a otro proceso echoAI?
5. ¿Hay que romper `R_AVOID_OK` en mundos donde “pasar por el fuego” no debería ser la política estable, o es una lección que se queda?
6. ¿El visor debe mostrar N/S/δ por turno (hoy el jsonl no lleva esas banderas; el informe sí), o se deja como está?
7. ¿echOS 2.1 alguna vez embebe el bucle, o echoAI se queda host?

Cualquier respuesta que requiera “el LLM escribe hechos”, “Akida hace VERIFY”, “T=0.9964 es inteligencia” o “esto ya es AGI” es una respuesta mala.

---

## 14. Cómo está organizado el trabajo humano

- **Roger / Rogex Laboratories** — dueño, tesis, qué se cita y qué no.
- **Grok** — arquitecto: revisa informes, escribe el siguiente contrato, no implementa el laboratorio.
- **Claude** — implementador: un KPI por slice, no rediseña el anillo.
- **ChatGPT researcher** — firmó la tesis situada y el orden (T_CONF → inverso → escalada/ΔQ → N/S/δ → oráculo fuera → pasillo).
- **Gemini** — interlocutor del *futuro*, no del código congelado. Este archivo es tu contexto.

Flujo que funcionó: Claude implementa → Grok revisa contra código y tests → prompt siguiente, un KPI. Los candados no se negocian.

---

## 15. Comandos de humildad (qué no decir en público)

**Sí:**

- “El agente funciona con el córtex apagado.”
- “Preguntar una vez cambió +80 por −80.”
- “No piensa siempre: 36/256.”
- “Aprendió un salto que la aritmética del anillo no conoce.”
- “Cuando el pasillo cambió, el mapa viejo siguió valiendo donde el mundo no cambió, y se enteró del cambio equivocándose.”
- “Un LLM, si se enchufa, no puede escribir hechos.”

**No:**

- “Tenemos AGI.”
- “Tenemos un neocórtex.” (tenemos un enchufe)
- “T = 99.64 % es un modelo del mundo.”
- “El planner es inútil.” (es inútil *siempre-on en este anillo*; el módulo llega a c9 y 8→11)
- “E[6] son emociones.”
- “Akida es el cerebro reptiliano.”
- “echOS 2.1 ya piensa.”

---

Fin del briefing. El código que cierra los números está en `echoai/nexus0/` y `echoai/docs/STATUS.md`. El animal se mira con `python3 -m echoai.nexus0.demo`.
