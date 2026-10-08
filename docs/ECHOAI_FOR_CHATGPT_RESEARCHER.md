# echoAI — briefing único para ChatGPT (modo investigador)

**Fecha:** 2026-09-03  
**Remitente:** Roger / Rogex Laboratories  
**Destinatario:** ChatGPT en modo investigador  
**Regla de este archivo:** es **el único** documento que recibes. No hay repo adjunto, no hay PDF extra, no hay código. Todo lo que necesitas para razonar está aquí. Si algo no está, dilo; no lo inventes como si estuviera medido.

---

## 0. Tu encargo (léelo antes que el resto)

Eres investigador, no implementador y no marketer.

El laboratorio acaba de **cerrar** un programa situado: un agente de dos relojes que funciona con el córtex apagado, en un anillo de 32 celdas y en un pasillo de 5. Es un **juguete real y funcional**. No es AGI. Ahora queremos **escalar** con cuidado.

Debes investigar y proponer **la aproximación más óptima** para, en este orden de prioridad:

1. Meter la **primera LLM** y conectar la corteza (el enchufe ya existe).
2. Una **GUI real** (no solo terminal ANSI) donde cada componente de echoAI sea un objeto gráfico; cuando una parte se dispare, se subraye o cambie de color.
3. **Expandir el mundo** (hoy 32 celdas / 5 celdas) — cómo simular un mundo grande sin romper el bucle entero.
4. **Hacerla descansar** (sueño / compactar lo vivido) y decir **qué utilidad tiene compactar**.
5. El **interlocutor caro detrás del muro** (que la charla no se vuelva hecho).
6. **Cuerpo**: ¿hace falta Akida? ¿robótica, cámara, lidar? ¿qué falta de verdad?
7. **Futuro** y cómo se escala un juguete que ya corre.

Responde en español. Distingue siempre:

- **Hecho del laboratorio** (copiado de este briefing, con número).
- **Inferencia tuya** (márcala).
- **Recomendación** (con alternativas, costes, y por qué no las otras).
- **Lo que no sabes** (no rellenes).

Al final, una **hoja de ruta de 4 a 8 pasos**, un KPI por paso, que un implementador pueda ejecutar sin rediseñar el anillo. El primer paso tiene que ser enchufar la corteza de forma que **se note**, no teatro.

Si una idea tuya choca con un invariante de la §9, **gana el invariante**. Propón otra idea.

---

## 1. Qué es echoAI (una frase)

echoAI es un agente cognitivo de **dos relojes** cuyo núcleo funciona **con el córtex apagado**: percibe, recuerda, predice, actúa y aprende sobre un único cable discreto de **16 bytes** (WSP). Un modelo de lenguaje, si se enchufa, es el reloj lento: **propone hipótesis**. Nunca escribe hechos.

Tesis que este laboratorio aceptó (tú mismo, en una lectura previa, la firmaste en sustancia):

> EchoAI **no** se investiga como “SNN + LLM”. Se investiga como arquitectura de aprendizaje **situada**: WSP/QN espacio discreto compartido, CAM memoria, T dinámica, Q política, ATTEND cuándo gastar cómputo cortical, córtex hipótesis que deben sobrevivir al basal.

Hipótesis operativa:

> Intelligence ≈ representation + memory + prediction + action + learning + information acquisition.

Prueba que el programa cerrado ya hizo en miniatura:

> El agente cambia de comportamiento **correctamente** después de descubrir que su modelo del mundo estaba equivocado — en un mundo que **no** es solo el anillo de 32 — sin dejar de preguntar, sin planificar de más, sin córtex si lo barato basta.

Eso es el **pasillo** (HOME A→B→C→D vs SHIFT A→B→X→D). Detalle en §6.

---

## 2. Qué no es (no lo conviertas en esto)

- **No es AGI.** La escalera termina en NEXUS-7 (transferencia de tarea abierta). **No hay NEXUS-8 “AGI”.** AGI no es KPI.
- **No es un chatbot.** No hay conversación con el usuario en el bucle. No hay HTTP en el camino caliente.
- **No es “SNN + LLM” como producto.** Esa etiqueta se descartó.
- **No es un cerebro humano.** No hay emoción sentida, no hay consciencia. E[6] no es un sentimiento.
- **No es echOS 2.1.** El unikernel es otro artefacto. echoAI no entra en la ISO. Corre en host Python e importa primitivas; no envuelve `navi10_engine.think`.
- **No es Akida.** Hay **0 placas** AKD1000. El bucle rápido es software. Akida no es prerrequisito para cuerpo, GUI, LLM ni mundo grande.
- **No es navi10 `--ask`.** Eso es un router. echoAI no se construye alrededor.
- **No es el teseracto de `./navi10 --tui`.** Ver pensar echoAI es un visor ANSI del log `thought.jsonl`, ahora también `python3 -m echoai.nexus0.demo`.

Frase **prohibida** como world model: “T = 99.64 %”. En el anillo liso T acierta casi tanto como la aritmética i±1. El resultado que **sí** se cita es **JUMP**: dos celdas saltan +2 y T las aprende; la aritmética no.

---

## 3. Si el LLM es el neocórtex, ¿qué hay ahora?

Analogía de trabajo (no anatomía, no marketing de “cerebro reptiliano”):

> Si en este sistema hay un neocórtex, es un **LLM detrás de un firewall**, apagado por defecto, que solo emite hipótesis en el cable de 16 bytes. El resto del sistema nervioso **tiene que funcionar con ese neocórtex desenchufado**. Eso es lo construido.

**Tenemos el animal sin corteza. Funciona. La corteza es un enchufe vacío. El muro ya está.**

---

## 4. Glosario: qué es cada parte

Usa estos nombres. No inventes módulos nuevos si uno de estos ya cubre la función.

### 4.1 El cable — WSP (16 bytes)

Único idioma del sistema. Un paquete:

```
src  →  rel  →  dst  @ time    más E[6] int8 (V A D C U B)
```

Ejemplos reales del banco:

- Celda vacía: `YO → OBSERVAR → AQUI @AHORA`
- Premio: `YO → DESEAR → AQUI @AHORA`
- Trampa: `YO → TEMER → PELIGRO @AHORA`
- Pregunta: `YO → PREGUNTAR → DESCONOCIDO @AHORA`

No hay segundo bus de “pensamiento”. I17.

### 4.2 Encoder

Texto o celda del mundo → 16 B. Un miss es **DESCONOCIDO**, no un hash FNV. El hash existe como baseline a **perder**. Banco vendor 6/6 rel vs FNV 0/6. Lex 235 filas, en sync con una tabla C del kernel (`wsp_lex.c`). No la toques para “meter el LLM”.

### 4.3 CAM (4096 ranuras)

Memoria de lo **percibido**. “¿He visto este paquete?” Guarda episodio, extracto, `has_fact`, `source`, hits. No es la política. I15: CAM ≠ Q.

`source=` es procedencia:

| paquete | source |
|---|---|
| una celda del anillo | `nexus0-env` |
| la pregunta PREGUNTAR | `sensor` (default) o `file` (`--oracle PATH`) |

Nunca al revés.

### 4.4 T — modelo del mundo

Tabla `T[s][a] → s'`. Enteros. “Si en este sitio hago esta acción, ¿adónde caigo?”

Lleva conteos `n`, un alternativo `alt`/`alt_n`, `conflicts`. Un conflicto no borra al ganador hasta que el nuevo valor **gana en conteo** (KCC).

**T_CONF ∈ {0,1,2,3}:** nunca / una vez / consistente / muy consistente (n≥8 y sin conflicto). Un conflicto **impide el 3 para siempre** en esa fila.

**Inverso I(s,s')→a:** “¿qué acción me trajo aquí?” Solo vecinos observados, lista corta por slot (máx 8), nunca una matriz 4096×4096.

### 4.5 Q — política / hábito

`Q[4096][3]` int8, 12 KiB. Tres acciones:

| id | nombre | átomo | premio típico |
|---|---|---|---|
| 0 | approach | UNIR | +16 GOAL; −16 THREAT; NOVEL −16 hasta preguntar, +16 después |
| 1 | avoid | TEMER | +8 en THREAT (`R_AVOID_OK`) |
| 2 | wait | OBSERVAR | 0 |

Aprendizaje: `δ = r + ((7 * max Q[s']) >> 3) - Q[s,a]`; `Q += δ>>2` (α=1/4, γ=7/8). δ **no** vive en E[V]. I16.

Desempate de `best()`: empate total o parcial prefiere **wait**. En *entrenamiento*, empate total de `select()` prefiere **approach** para que el anillo se recorra. No los mezcles.

### 4.6 Gate

Veto o modificación de la acción propuesta. Puede bloquear (p. ej. flag inhibit → wait).

### 4.7 E[6] — modulación, no emoción

V A D C U B, int8 ±100. Certainty C y urgency U existen. **ATTEND ya no usa E[C] para despertar** (el poster del paquete traía C=15 constante y despertaba el 73 % de los turnos). La certeza que cuenta es Q y T reales.

### 4.8 ATTEND — cuándo gastar el reloj lento

Predicado entero. OR de razones. Off por defecto en el banco (`cortex_calls=0`).

Razones cableadas:

| código | nombre | cuándo |
|---|---|---|
| 0 | off | el rápido basta |
| 1 | miss | CAM no tenía el paquete |
| 2 | no_extract | no hay extracto |
| 3 | low_C | Q no tiene preferencia (fila empatada y no “asentada”) |
| 4 | novel | la celda es KIND_NOVEL |
| 5 | no_map | T no conoce la acción preferida |

CONFLICT / GOAL_COMPLEX / HUMAN están en la spec de NEXUS-4 y **no** están cableados. No los fíngas.

Con `--cortex`: **36 wakes / 256 turnos**. Ese número no se ha movido en T_CONF, inverso, escalate, N/S/δ, oráculo ni pasillo. Si una propuesta de LLM dispara córtex en casi todos los turnos, es un router, no dos relojes.

### 4.9 PREGUNTAR y el oráculo (fuera del mundo)

PREGUNTAR **no** es una 4ª marcha. No mueve al agente. `_ask()` es la única puerta.

Orden, tres cosas, y no otro:

```
oracle.reply()       texto crudo de fuera. No toca env, Q, T, CAM.
oracle.accept(t)     VERIFY. Solo el token NOVEL_CLEAR, o None.
                     Prosa, vacío, JSON, multilínea, hex WSP → None.
RingEnv.reveal(x)    física. Solo se llama si accept pasó.
RingEnv.ask()        NO EXISTE. Se borró.
```

`accept` **no** es `parse_reply`. Test: el string `YO → PREGUNTAR → DESCONOCIDO @AHORA` lo **acepta** parse_reply (es un paquete hipótesis) y lo **rechaza** accept (no es un extracto). Puertas distintas.

Default: callable in-process `Sensor` que sabe una sola palabra (`NOVEL_CLEAR`), `source=sensor`. Un archivo que el banco se escribe y se lee sería teatro. `--no-ask` es silencio (`oracle is None`), no un oráculo mudo. `--oracle PATH` lee una línea (humano u otro proceso).

Si VERIFY falla, la pregunta **sigue abierta** y se vuelve a hacer en la siguiente visita. En un brazo de prosa/ausente: 66 rechazos, retorno −80, `false_facts=0`. No se suavizó.

### 4.10 Planner (`plan.py`)

Lookahead sobre T, profundidad 1 o 2. **Módulo. Default off** (`plan_depth=0`).

- Sirve: ve un GOAL a distancia 2 que Q miope no ve (c9; 8→11).
- En el anillo de 320 turnos, **siempre-on está refutado**: wait 58 % porque `T(s,wait)=s`.
- Escalada ΔQ (`escalate.py`): si el margen Q es pequeño (≤ `ESC_MARGIN=4`), se consulta profundidad 2. Resultado: `search_strictly_better = 0`. Los 183 “differs” son un **desempate** wait vs approach, no mérito. Actuar el escalate empeora política `[-12,+5,0]→[-7,+5,0]` y retorno +80→+48.

Niveles 1/3/4 (T one-step, ASK, CORTEX) están **nombrados, no cableados**. T ya corre cada turno; ASK es `_ask()`; CORTEX es ATTEND. No dupliques.

### 4.11 Córtex — el enchufe (vacío)

No hay LLM in-process. Contrato ya escrito:

**Entrada** (si `NAVI_CORTEX_CMD` está definido): un JSON por stdin, un turno, con al menos:

```
turn, reason, wsp_in, wsp_out, slot, ham, q_row, t_pred, extract
```

Timeout 10 s. Subprocess. **No HTTP. No SDK. No default.**

**Salida:** stdout → `parse_reply`:

- 32 caracteres hex (16 B), o
- una línea de átomos conocidos `SRC → REL → DST @ TIME` con `| E[...]` opcional.

Todo lo demás (prosa, JSON, “VERIFY: …”, átomos inventados) → `None` → se conserva la observación / el stub. `cortex_rejected++`.

**Stub actual** (`propose`): si la razón es NOVEL, emite el mismo PREGUNTAR que el rápido ya sabe enviar al oráculo. Cualquier otra razón: devuelve el paquete de entrada. **ROI del stub ≈ 0.** Medir CortexROI ahora sería teatro.

Firewall I14: el módulo córtex **no tiene handle de CAM**, no llama `allocate`, no pone `has_fact`. Aunque el LLM alucine, el loop no puede convertir esa alucinación en hecho por este camino. Un hecho nuevo solo entra por extracto verificado (oráculo / sensor).

Banco principal: `cortex_calls = 0`. El flag `--cortex` enciende ATTEND+stub, no un modelo.

### 4.12 thought.jsonl y el visor actual

Una línea JSON por turno (claves fijas, enteros y átomos, sin prosa). Visor ANSI:

```
python3 -m echoai.nexus0.demo            # en vivo, 352 turnos, 5 fps
python3 -m echoai.nexus0.demo --short    # 48 turnos
python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --fps 5
```

Leyenda: `G` premio, `T` trampa, `N` misterio, `·` vacío, `@` agente (fila propia, no tapa la N), `<` acción, barras = Q de esa celda, `ATTEND OFF` casi siempre.

**No hay GUI** con objetos por componente. Eso es una de las cosas que te pedimos diseñar ( (§11.2) ).

### 4.13 N ≠ S ≠ δ (tres aprendizajes)

Ya no son una palabra.

| contador | significado | default 352 turnos |
|---|---|---|
| `cam_misses` (N) | primera vez que el agente **pisa** este origen | 33 |
| `surprises` (S) | T tenía predicción **y** estaba mal | 1 |
| `deltas` (δ) | Q se movió | 217 |
| `surprise_known` | S sin N (sitio conocido, mapa mal) | **1** |
| `novel_no_surprise` | N sin S | 33 |
| `delta_only` | δ sin N ni S | 208 |

N no es KIND_NOVEL. T_MISS no es sorpresa (es ignorancia). `Cam.put()` siembra `hits=1`, así que N se lee `hits<=1` tras asignar.

### 4.14 El anillo (mundo 1)

32 celdas. JUMP en 5 y 21 (approach +2). NOVEL en 11 (bit oculto). Amenazas en 7 y 19. GOALs en 3, 15, 27. Tras 256 turnos, fase F mueve la amenaza 7→8 y hay 64 turnos más (352). Semilla `20260903`.

### 4.15 El pasillo (mundo 2) — qué es

**No es el anillo pintado.** Es cinco celdas y una tabla de sucesores, nunca `(i+1)%n`.

```
HOME    A → B → C → D     D = GOAL,  C = EMPTY
SHIFT   A → B → X → D     X = THREAT, C fuera del camino
```

A, B, D conservan índice **y** tipo → el mismo paquete WSP → CAM/T/Q se arrastran. C y X son **índices distintos**. `home.kind == shift.kind` (nada se repinta; el repintado era fase F en el anillo).

Al **entrar** en SHIFT, antes de caminar:

| | T(B, approach) | conf | sin ver de {A,B,D} |
|---|---|---|---|
| transferido | **C** (conocido) | 3 | **0** |
| control Q=T=0 | **None** | 0 | **3** |

Primeras visitas en la ventana: transferido **1** (solo X), control **4**. `surprise_known` 14 vs 0. Primer paso equivocado: turno 97, mismo slot de B, KCC no voltea con una observación.

KPI 4 **no** salió como se predijo y **no se retuneó**: approach en B sigue ganando. El agente aprende “entra en X y luego esquiva”, porque la única ruta a D pasa por X y avoid en amenaza paga +8, así que max Q[X] se queda positivo. Q[B,approach] cae 4→1; Q[X]=[-3,+5,0].

Esto **no es AGI**. Es: una T aprendida sigue siendo cierta donde el mundo no cambió, se equivoca donde sí, y se entera **equivocándose**.

`_ask()` sigue cableado y no dispara (`questions=0`): no hay NOVEL en el pasillo.

---

## 5. Un turno, en orden

```
S_t → A_t → Ŝ_{t+1} → S_{t+1} → δ_t → aprendizaje
```

1. Ver celda → WSP 16 B → CAM (¿nuevo?).
2. Si `--cortex`: ATTEND ¿despierto?
3. Si NOVEL y ask on: PREGUNTAR → oráculo fuera → accept → maybe reveal.
4. Q (o planner/escalate si se pidió) propone acción.
5. Gate.
6. T predice s'.
7. El mundo ejecuta; recompensa entera.
8. `T.observe`; `Q.update` (devuelve δ).
9. Opcional: una línea `thought.jsonl`.

El córtex, cuando exista de verdad, entra **solo** en el paso 2, emite ≤3 paquetes WSP de hipótesis, y **no** sustituye 6–8.

---

## 6. Números que puedes citar (cerrados)

Banco default **sin flags** (352 turnos):

```
policy_after                 [-12, +5, 0]
false_facts / destroyed      0 / 0
cortex_calls                 0
novel_approach_return        +80     (ciego: −80)
questions                    1
surprise_known               1
cam_misses / surprises / deltas    33 / 1 / 217
encoder_beats_fnv            True
t_beats_ring                 True    (JUMP; no cites 0.9964 como world model)
level_search                 0
oracle_source                sensor
oracle_rejected              0
search_strictly_better       0       (si se fuerza --escalate: still 0)
```

`--cortex`: 36/256 wakes. Tests: 155. Lex: 235, in sync.

Otros brazos (informes **propios**, no pisan el candado): `--no-ask`, `--plan-depth 2`, `--trace`, `--cortex`, `--thought`, `--escalate`, `--oracle PATH`, `python3 -m echoai.nexus0.corridor`.

---

## 7. Escalera NEXUS (dónde estamos)

```
NEXUS-0   memoria + política + aprendizaje     CERRADO
NEXUS-1   T gana al baseline                    CERRADO (JUMP)
NEXUS-2   planner módulo; siempre-on REFUTADO   CERRADO
NEXUS-3   PREGUNTAR +80/−80                     CERRADO
NEXUS-4   córtex: ATTEND, stub, firewall        CERRADO como socket vacío
NEXUS-4i  pasillo (miniatura de transferencia)  CERRADO
NEXUS-5   sueño / consolidación                 NO HECHO
NEXUS-6   cuerpo / Edge                         NO HECHO
NEXUS-7   transferencia de tarea abierta        NO HECHO (el pasillo es la miniatura)
```

No hay NEXUS-8 AGI.

Spec de sueño ya escrita, no implementada:

> WAKE: percibir, actuar, aprender. SLEEP: episodios → si S,A→S' de forma consistente, T se marca estable; Q no se reentrena con prosa.  
> Puerta: tras sleep, `prediction_accuracy` sube **sin** turnos nuevos WAKE. `chat.jsonl` es input de sleep, no de `--ask`.

Spec de cuerpo:

> SKU Edge: WSP+Q6+CAM+Q+gate, **sin LPU**. Sensores/actuadores reales o el mismo env. USB/Akida **si hay placa**. Puerta: el **mismo** bucle corre importando el C de Q6. No es ISO 2.1.

---

## 8. Akida, en tres líneas (para que no lo pongas en el camino crítico)

- 0 placas. El switch del kernel se **niega**.
- Digital, event-based, enteros. Edge learning BrainChip ≠ STDP de rxOS.
- Si algún día: **sensing** (tensor → 3 acciones), Cerradura 0 = simulador primero. **Nunca VERIFY, nunca hechos, nunca veto, nunca IRQ/disco.** No diseñes echoAI como si AKD1000 ejecutara la LLM.

**No hace falta Akida para dar cuerpo, GUI, mundo grande ni corteza.**

---

## 9. Invariantes (si tu plan los rompe, el plan está mal)

| # | Contrato |
|---|---|
| I1–I2 | WSP = 16 B, layout congelado |
| I3 | 0 FPU en el paso **rápido** (el córtex puede ser float: es el reloj lento) |
| I4 | CAM/Q estáticos; sin malloc en el step rápido |
| I5 | VERIFY = Hamming≤3 ∧ extracto |
| I6 | `destroyed==0` |
| I7 | umbral neuronal no cierra IRQ/disco/#PF |
| I8 | Akida ausente se niega; no fingir silicio |
| I11 | banco principal `cortex_calls==0` |
| I12 | unikernel ≠ host; echoAI no entra en ISO 2.1 por este plan |
| I14 | hipótesis de córtex **nunca** `has_fact=1` |
| I15 | CAM ≠ Q |
| I16 | δ no vive en E[V] |
| I17 | un solo cable |

También: no vector DB / embeddings float / FAISS en el bucle caliente; no segundo event-bus; no envolver `navi10_engine.think`; no prosa → hecho.

Candados del banco sin flags: los de la §6. Un plan de escalado **no** los mueve. Los brazos nuevos escriben **otro** JSON.

---

## 10. Constantes (no las cambies en el primer paso)

```
N_SLOTS 4096   N_ACTIONS 3   WSP 16 B   HAM_LIMIT 3
γ=7/8   α=1/4   Q int8 ±127
R_SUCCESS +16   R_THREAT −16   R_AVOID_OK +8
C_PLASTIC 20   ATTEND_SETTLED_HITS 2   ESC_MARGIN 4
JUMP_CELLS (5,21)   N_CELLS 32   BENCH_TURNS 256   SEED 20260903
T_CONF_HIGH_N 8   INV_MAX_ENTRIES 8
NAVI_CORTEX_CMD timeout 10 s
lex 235
```

---

## 11. Preguntas que debes investigar

Contesta **todas**. Separa hecho / inferencia / recomendación. Ordena alternativas. Di qué **no** harías.

### 11.1 Primera LLM — conectar la corteza (prioridad 1)

Hoy el enchufe es: ATTEND decide → `complete()` lanza `NAVI_CORTEX_CMD` → stdin JSON de un turno → stdout → `parse_reply` → 16 B o nada. Stub = PREGUNTAR. Default off.

Investiga y recomienda:

1. **Qué tipo de LLM** (no una marca de moda por sí sola):
   - ¿Local (llama.cpp, MLX, GGUF) vs API (OpenAI/Anthropic/Google/xAI)?
   - El laboratorio hoy **prohíbe HTTP en el camino caliente**. ¿Mantener subprocess local, o un *wrapper* local que hable con una API **fuera** del loop? Consecuencias para I11, latencia, reproducibilidad del banco.
   - ¿Modelo pequeño que se deja forzar a átomos, o modelo potente que razona y luego hay que **comprimir** a 16 B?
   - ¿Instruct, reasoner (o1/r1-like), code model, MoE?
   - Contexto: el modelo **no** debe ver Wikipedia del mundo; debe ver el JSON del turno (q_row, t_pred, extract, reason). ¿System prompt que solo permita átomos?
2. **Qué pasaría si metemos un modelo potente** (70B+, reasoner, multimodal):
   - Latencia vs ATTEND 36/256 (si cada wake tarda 2 s, el animal se para).
   - Alucinación vs firewall: el muro aguanta; ¿el wake se vuelve inútil porque todo se rechaza (`cortex_rejected`)?
   - Riesgo de convertir ATTEND en “llama siempre, por si acaso”.
   - Coste. Energía. Reproducibilidad (el banco tiene semilla).
3. **¿Dos modelos que se corrijan y razonen entre sí?**
   - ¿Encaja en dos relojes o es un tercer reloj?
   - ¿Quién tiene la última palabra: parse_reply, el gate, T, o el debate?
   - ¿Debate **dentro** del subprocess (un binario que ya hace A/B) vs dos CMD?
   - ¿Eso paga CortexROI o duplica coste para ROI≈0?
   - El lab ya tiene un “segundo voto”: el **oráculo** (hechos) ≠ córtex (hipótesis). No los fusiones.
4. **KPI para que el primer enchufe no sea teatro.** El lab ya dijo: CortexROI = Δreward / cortex_calls vs `cortex=False`, **solo** cuando `complete()` cambia una decisión. El stub no cambia ninguna. Propón:
   - un mundo o una celda donde el rápido **no** basta (el anillo, hoy, el planner tampoco aportó mérito);
   - una salida WSP legal que el rápido no habría emitido;
   - cómo se mide que cambió la acción o la pregunta, con `false_facts=0`.
5. **Aproximación óptima, concreta**, 2026: modelo(s), tamaño, local vs no, formato de prompt, cómo se obliga a átomos (constrained decoding / grammar / rechazo), dónde vive el proceso, qué **no** se toca (`parse_reply`, ATTEND, oráculo, Q, T).

El primer slice no puede ser “integrar LangChain”. Tiene que ser: un binario, un flag, un número que no sea 36 wakes haciendo el mismo PREGUNTAR.

### 11.2 GUI real (prioridad 2, no bloquea la corteza)

Hoy: terminal ANSI, un anillo, barras Q, una línea de átomos.

Queremos una GUI **real** donde **cada componente** de la §4 sea un objeto gráfico (nodo, bloque, órgano — elige metáfora y defiéndela; **no** un árbol `amygdala.py`). Colores. Cuando esa parte **dispara en un turno**, se subraya / cambia de color / pulsa.

Componentes que deben poder “encenderse” (lista mínima):

CAM hit/miss · N · S · δ · T predict · T conflict · Q update · gate veto · ATTEND on+razón · PREGUNTAR · oracle accept/reject · reveal · córtex wake · parse_reply ok/reject · planner (si opt-in) · JUMP · fase F

Investiga:

- ¿Web (un visor local que lee thought.jsonl / websocket del demo) vs nativo (Qt, wgpu, egui)? El visor actual es stdlib a propósito.
- ¿La GUI es **replay** del jsonl (seguro, no toca el loop) o se engancha en vivo?
- ¿Hay que **añadir campos** al jsonl (N/S/δ por turno hoy no van en thought.KEYS) para que la GUI no mienta?
- Cómo no meter pygame/electron en el paso rápido.
- Un mockup en texto (layout) basta; no pidas que implementemos tres frameworks.

### 11.3 Falta mundo — cómo se expande

Hoy: 32 celdas cíclicas, o 5 con tabla de sucesores. Discreto. Enteros. WSP por (índice, kind).

Investiga cómo **simular un mundo mucho más grande** sin:

- floats en el loop rápido,
- vector DB,
- convertir T en una red neuronal,
- romper Heap-0 (4096 ranuras).

Opciones que debes comparar, no solo listar:

- Grid 2D discreto (mismas 3 acciones: norte implícito en approach?).
- Grafo / pasillos múltiples (el pasillo ya es un grafo de 5).
- Procedural pero **símbolos** (tipos de celda, no coordenadas float).
- Varios anillos / habitaciones con puertas = celdas JUMP generalizadas.
- MiniWorld / ViZDoom / Habitat: ¿el sensor debe **ya** emitir WSP, o es otro proyecto?

CAM 4096 es el techo de estados *distintos en memoria*, no del mundo. Un mundo de 10⁵ celdas con 20 tipos puede colapsar a pocos paquetes (si el encoder ignora posición) o explotar (si cada índice es un paquete, como ahora: `encode_cell` usa seq). **Ese trade-off es el problema.** Analízalo.

NEXUS-7 pide: segundo env, mismas 3 acciones, T/Q del primero mejor que Q=0. El pasillo ya lo cumplió en 5 celdas. ¿Cuál es el **siguiente** env que no sea teatro y no sea “el mundo real”?

### 11.4 Descansar / compactar (NEXUS-5) — y la pregunta personal

Spec: SLEEP lee episodios; si S,A→S' es consistente, T se marca estable; Q no se reentrena con prosa; `prediction_accuracy` sube **sin** turnos WAKE.

Preguntas:

1. **Qué necesita** para compactar lo que vivió (estructura de datos: ¿el jsonl, la tabla T+n, traces, thought.log?). ¿Hace falta un LLM para dormir, o es precisamente el punto que **no**?
2. **Qué utilidad tiene compactar** (pregunta personal de Roger — contéstala con honestidad, no con romance):
   - ¿Ahorra ranuras CAM?
   - ¿Sube T_CONF de 2 a 3 sin 1024 turnos?
   - ¿Evita que fase F / el pasillo necesiten n=4 vs alt=1 para no voltear mal?
   - ¿O es estética de “sueño” que el juguete no necesita todavía?
   - Relación con el planner: en el anillo el planner no pagó. ¿Dormir contrafactuales sería reabrir NEXUS-2 por la noche?
3. Cómo no convertir sleep en “reentrenar Q con un resumen en inglés”.

Si concluyes que compactar **aún no paga** en 32 celdas, dilo. El lab prefiere eso a teatro.

### 11.5 Interlocutor caro detrás del muro

Ya hay dos muros:

- Oráculo: extracto o nada (hechos).
- Córtex: 16 B átomos o nada (hipótesis).

“Interlocutor caro” = la LLM. Investiga:

- Cómo se **habla** con ella (si se habla) sin que esa charla escriba CAM factual.
- ¿Un canal humano (`--oracle PATH` ya es un humano lento) distinto del córtex?
- ¿La GUI muestra hipótesis en gris y hechos en sólido?
- Qué pasa si el usuario dice en prosa “la celda 11 es segura”: hoy eso es reject. ¿Debe seguir siéndolo **siempre**?
- Dos LLMs que se corrigen: ¿quién habla con el humano? ¿Ninguna, y el humano solo escribe extractos?

La frase del lab: *el muro impide que la charla se vuelva hecho de verdad.* Tu plan debe **conservar** eso, no “suavizarlo un poco para UX”.

### 11.6 Cuerpo — ¿Akida, robótica, cámara, lidar?

Contesta con claridad:

- **No hace falta Akida para un cuerpo.** Confírmalo o refútalo con argumentos; el lab cree que no.
- Un cuerpo mínimo compatible con 3 acciones: ¿qué es? (adelante / retroceder / quedarse; un motor; un simulador de robot de diferencial).
- Cámara / lidar: tendrían que **nacer WSP** (un encoder perceptual), no tensores float en Q/T. ¿Dónde vive ese encoder? ¿Eso es NEXUS-6 o un proyecto aparte?
- ¿El primer cuerpo es **simulado** (el mismo Agent, otro `env=`) o hardware?
- Relación con echOS / unikernel: **no** meter echoAI en la ISO en este plan.

### 11.7 Cómo se escala un juguete real

El juguete **ya corre**. Escalar no es “añadir capas hasta que parezca un cerebro”.

Propón una definición de escala con **métricas**:

| eje | hoy | siguiente no-teatro |
|---|---|---|
| mundo | 32 / 5 celdas | ? |
| acciones | 3 | ? (subir acciones rompe Q[4096][3] y el gate) |
| memoria | 4096 slots | ? |
| corteza | stub | 1 wake que cambia una decisión |
| cuerpo | ninguno | ? |
| GUI | ANSI | ? |

Di qué eje **no** tocar primero (el lab sospecha: no acciones, no ISO, no Akida, no planner-siempre-on).

### 11.8 Futuro (horizonte, no profecía)

Un párrafo de 5–10 años **honesto**: qué podría ser echoAI si se respeta el muro (agente de borde que pregunta, duerme, lleva un mapa entero, corteza opcional). Qué **no** será (ChatGPT con spikes, consciencia, echOS pensante).

---

## 12. Formato de tu respuesta (obligatorio)

1. **Resumen ejecutivo** (≤20 líneas). Qué enchufar primero y por qué.
2. **Corteza: recomendación única** (tipo de modelo, tamaño, local/API, cómo habla átomos, KPI del primer slice). Luego 2 alternativas y por qué pierden.
3. **Dos modelos que se corrigen:** sí / no / no ahora. Condiciones.
4. **Qué pasaría con un modelo potente** (tabla: gana / pierde / riesgo).
5. **Compactar:** necesita / utilidad real / ¿ahora o después?
6. **Mundo grande:** diseño siguiente env, trade-off CAM vs identidad.
7. **GUI:** stack, qué se pinta, qué hay que añadir al jsonl, que **no** toca el loop.
8. **Cuerpo y Akida:** respuesta directa.
9. **Interlocutor y muro:** cómo se habla sin hacer hechos.
10. **Hoja de ruta** 4–8 pasos, un KPI cada uno, el 1 = corteza no-teatro.
11. **Lo que no harías** (lista).
12. **Lo que este briefing no te deja saber** y necesitarías del lab.

No entregues código de producción. Pseudocódigo o contratos (JSON in / átomos out) sí. No propongas borrar `parse_reply`, `accept`, ATTEND, ni `RingEnv.ask()` (ya no existe).

---

## 13. Qué es una mala respuesta (para que no la des)

- “Usad GPT-5 / Gemini / Claude como cerebro y listo.”
- “Akida es el cuerpo.”
- “Hay que meter embeddings y RAG.”
- “El planner siempre on, ahora con LLM.”
- “T=99.64 % prueba que entiende el mundo.”
- “Dos agentes LLM en debate sustituyen T y Q.”
- “La prosa del usuario se escribe en CAM porque UX.”
- “Meter echoAI en la ISO 2.1 para el demo.”
- “CortexROI del stub.”
- Un framework de agentes (LangGraph, AutoGPT, etc.) como núcleo.
- Inventar emociones a partir de E[6].

---

## 14. Nota de procedimiento

Roger te pasa **solo este archivo**. Tú razonas e investigas. Tu respuesta volverá al arquitecto del laboratorio (Grok) para convertirla en el siguiente contrato de implementación, un KPI, sin rediseñar el anillo.

El juguete se mira hoy con:

```
PYTHONPATH=. python3 -m echoai.nexus0.demo --short
```

Córtex apagado. 3 acciones. 16 bytes. Eso es lo que hay que **conservar** al crecer.

Fin del briefing.
