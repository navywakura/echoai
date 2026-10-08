# echoAI — briefing para ChatGPT (modo investigador)

**Fecha:** 2026-09-04  
**Remitente:** Roger / Rogex Laboratories  
**Destinatario:** ChatGPT en modo investigador  
**Regla:** este es **el único** documento que recibes. No hay repo adjunto. Si algo no está medido aquí, dilo; no lo inventes. Distingue siempre: **hecho del lab** / **inferencia tuya** / **recomendación** / **lo que no sabes**.

Un briefing anterior (2026-09-03) te pedía enchufar la primera LLM, GUI y mundo grande. **Eso ya se ejecutó.** No lo redes. Este encargo es el *siguiente* horizonte.

Responde en español.

---

## 0. Tu encargo

Investigar **cómo escalar** echoAI, un agente de dos relojes que ya vive **con el córtex apagado**, a lo largo de una escalera de **comportamiento**, no de marketing:

```
PULPO (en curso)  →  DELFÍN  →  CHIMPANCÉ
```

Definiciones operativas de Roger (no son especies, no son AGI):

| Rung | Lo que tiene que *hacer*, medible | LLM |
|---|---|---|
| **Pulpo** | Orientación espacial (hoy 2D con heading; **no cerrado hasta 3D**). Acertijos individuales tipo “abrir un frasco / salir del acuario”: un cuerpo, un mapa, predecir, si X entonces Y, equivocarse y corregir. **Sin depender del LLM.** | Apagado. Se llama solo si ATTEND pide neocórtex (letrero, novel, más tarde conflicto). |
| **Delfín** | Autoconciencia, empatía, planificación a futuro, rompecabezas complejos. Todo **operacionalizado** (tests de conducta), nunca “siente que”. | Neocórtex a demanda (Qwen3-4B-Instruct-2507 ya enchufado y verde en letreros). |
| **Chimpancé** | Uso avanzado de herramientas. Un verbo nuevo **solo** si hay física nueva (p.ej. `ABRIR` el día que haya puerta). | Igual: hipótesis en átomos, nunca hechos. |

El 4B **ya está**. No propongas “primero un 70B / API / dos LLM”. Propón **cómo** usarlo (y cuándo **no**) en cada rung.

Temas que tienes que cubrir, con alternativas, costes y por qué no las otras:

1. **Orientación espacial 3D** sobre el cuerpo 2D que ya existe, sin explotar CAM ni el techo de paquete 256.
2. **Amígdala** y “emociones” en **RogexWSP** (E[6] int8). No un `amygdala.py`. Cómo modular sin violar I16 (δ no vive en E[V]) ni fingir sentimiento.
3. **Métodos de entrenamiento** que rompan el horizonte de crédito de 3 pasos (α=1/4 entero) **sin FPU en el rápido**.
4. **Más acciones**: los átomos extra ya existen en el cable; la física no. Cuándo añadir un verbo.
5. **Escalar espacio y cuerpo**: 5×5×4 = 100 poses; CAM 76/4096; techo `index & 0xFF` = 256.
6. **Autoconciencia / empatía / plan a futuro / rompecabezas / herramientas** como KPIs de conducta, no como prosa.

Al final: **hoja de ruta 6 a 12 pasos**, un KPI por paso, implementable sin rediseñar el anillo. El primer paso tiene que ser compatible con **WALK-1** (el lab ya lo tiene como siguiente slice de código: greedy START→GOAL en la tortuga, córtex off, `R_*` iguales).

Si una idea choca con un invariante (§9), **gana el invariante**.

---

## 1. Qué es, en una frase

echoAI = agente de **dos relojes** cuyo núcleo funciona **con el córtex apagado**. Percibe, recuerda, predice, actúa y aprende sobre un único cable de **16 bytes** (RogexWSP). Un LLM, si se llama, **propone hipótesis en átomos**. Nunca escribe hechos.

Tesis del lab (no la reescribas):

> No se investiga como “SNN + LLM”. Se investiga como aprendizaje **situado**: WSP espacio discreto, CAM memoria, T dinámica, Q política, ATTEND cuándo gastar córtex, hipótesis que deben sobrevivir al basal.

> Intelligence ≈ representation + memory + prediction + action + learning + information acquisition.

Analogía de trabajo (**no anatomía, no producto “cerebro reptiliano”**):

> Si hay neocórtex, es un LLM detrás de un firewall. El animal tiene que vivir desenchufado. Eso está construido.

**Prohibido citar como world model:** “T = 99.64 %”. Eso es el anillo liso vs i±1. Se cita **JUMP**, heading y paredes: la aritmética pierde donde hay excepción.

**No es AGI.** No hay NEXUS-8 AGI. Autoconciencia/empatía aquí son *tests de conducta*. El lab no afirma experiencia fenoménica.

---

## 2. Qué no es (no lo conviertas en esto)

- Chatbot. No hay conversación en el bucle.
- “SNN+LLM” de catálogo. Esa etiqueta se tiró.
- echOS 2.1 (unikernel). echoAI no entra en la ISO. Host Python.
- Akida. **0 placas.** No bloquea cuerpo ni escalado.
- navi10 `--ask` (router) ni el teseracto `--tui`.
- MiniGrid / 8 acciones / OSWorld / ExploitBench / ARC-AGI-3 como banco propio.
- Un GPT-4 pequeño. Qwen3-4B no rinde MMLU *dentro* del loop: `parse_reply` tira prosa.

---

## 3. Estado medido (2026-09-04)

Tests **238** OK. Banco anillo default (sin flags):

```
policy_after              [-12, +5, 0]
false_facts               0
destroyed                 0
cortex_calls              0
novel_approach_return     +80     (--no-ask: −80)
questions                 1
surprise_known            1
cam_misses / surprises / deltas    33 / 1 / 217
encoder_beats_fnv         True
t_beats_ring              True     (JUMP, no 0.9964)
search_strictly_better    0
oracle_source             sensor
ATTEND --cortex           36/256, cortex_actions 0
```

### 3.1 Piezas cerradas

| Pieza | Hecho |
|---|---|
| WSP 16 B | un cable. Átomos + E[6] int8 ±100 + ext 5 B |
| Encoder | vendor + lex; miss = DESCONOCIDO; FNV es baseline a perder |
| CAM 4096 | episodios; `put()` siembra hits=1; N se lee hits≤1 |
| T + T_CONF 0–3 + I(s,s′)→a | I: 36/36 en el anillo; no matriz 4096² (`INV_MAX_ENTRIES=8`) |
| Q[4096][3] | approach/avoid/wait. α=1/4 (`ALPHA_SHIFT=2`). γ=7/8 |
| gate | ok / modify / block. En CUERPO-1 `cell.threat` es falso en todo el suelo: el −16 del choque entra en Q **sin** que el gate convierta wait→avoid |
| ATTEND | MISS, NO_EXTRACT, LOW_C, NOVEL. 36/256. `ATTEND_SETTLED_HITS=2` |
| PREGUNTAR | no es 4ª marcha. Oráculo **fuera**. `RingEnv.ask()` no existe |
| parse_reply | hex 16 B o `SRC → REL → DST @TIME`. Prosa → None. `@AHORA` obligatorio |
| plan.py | default off. Always-on en el anillo **refutado** (wait 58 %; `search_strictly_better=0`) |
| CORTEX-1 | cable UNIR/TEMER → gate. Stub SIGN: CortexROI **+16**, `false_facts=0` |
| Qwen-0 | Qwen3-4B-Instruct-2507 Q4_K_M, llama.cpp CPU, GBNF. Host fedora x86_64, Ryzen 5 5500U, 13 GiB, **sin CUDA**. Paráfrasis **6/6** vs stub **0/6**. Canonical prize/trap. rejected 0. ~1.62 s/turno. CortexROI +16. Informe `lab/nexus0_qwen4b_report.json` |
| GUI-1 / GUI-2 | placa HTML. Replay file:// (112 321 B). Live: `board --follow` poll `/turns.json` 200 ms en **127.0.0.1:8765**. Sin WebSocket. `loop.py` no se entera |
| Pasillo | HOME A→B→C→D / SHIFT A→B→X→D. T transferida. Se equivoca donde el mundo cambió |
| WORLD-3 | 256 **direcciones**, spine 16, **una** arista. T 16/16 HOME, 15/16 SHIFT. `transfer_gain=+256` = 32×`R_AVOID_OK(8)`, **0 GOAL en SHIFT**. CAM 17/4096. Techo de paquete: `encode_cell` usa `index & 0xFF` → nodo 256 = nodo 0 |
| CUERPO-1 | **verde hoy.** Tortuga 5×5, heading 0..3 = E,N,W,S (y crece norte). `index=(x+5*y)*4+h`, 100 bins, max 99 < 256. approach = paso al frente (choque −16, no atraviesa). avoid = gira 90° **antihorario**, no traduce. wait = nada. Seis paredes. GOAL (4,4) cobra +16 y vuelve a START (0,0,E). Layout `block`: baldosa (2,2) se vuelve pared; **4** sucesores approach cambian, **0** avoid. T barrido 76/76 vs stepper 12/76 (el stepper contestó y falló 44). Brazo libre: T 10/10 vs stepper 4/10 (pegado a pared este; “x+1” a menudo no contesta). CAM 76/4096. Alcanzables 76 open / 72 block. Entrenamiento: bucle de 10 poses, 42 cobros. **Greedy 128 turnos desde START: reward 0, goal_hits 0, 1 pose.** Q[approach] en el bucle: `0 0 0 0 -4 0 0 4 8 13`. Mismo horizonte de 3. El −4 es el golpe (4,0,E). Llegar a GOAL a propósito es **WALK-1**, no este KPI. `false_facts=0`, `cortex_calls=0`. Tests 238. `lab/nexus0_cuerpo1_report.json` |

Tres aprendizajes, no una palabra: N = primera pisada, S = T tenía predicción y estaba mal, δ = Q se movió. `surprise_known` = S sin N.

### 3.2 El horizonte de crédito (el número que más duele)

Q entero, α=1/4: un δ positivo **menor que 4 se va a cero** al desplazar. El valor viaja **tres** nodos/pasos y se para.

- WORLD-3 spine: `0…0 4 8 13` desde GOAL. Fork tuvo que ir a la posición 13 para que el KPI se pudiera fallar.
- CUERPO-1 bucle de 10: `0 0 0 0 -4 0 0 4 8 13`. Arranque a 9 del GOAL → greedy wait.
- Trazas de elegibilidad (`trace=True`, NEXUS-3b): en el pasillo **no alargan** el horizonte útil; esparcen deuda y dejan el spine lejano **negativo** (greedy avoid al inicio).

Cualquier propuesta de “entrenamiento” tiene que convivir con enteros, α=1/4, γ=7/8, `Q_MIN/MAX=±127`, y **no** retocar `R_SUCCESS=16`, `R_THREAT=-16`, `R_AVOID_OK=8` “para que el KPI salga”.

### 3.3 Techo de representación

```
encode_cell(index, kind)  →  seq = index & 0xFF
nodo/pose 256  ==  paquete del 0     (byte a byte)
CAM_SLOTS = 4096
Q y T se indexan por ranura CAM, no por vértice 16-bit
```

5×5×4 = 100 cabe. Un cubo 4×4×4 con 6 caras = 384 > 256 → **colisión de paquetes**. ANTI-ALIAS es el slice que tiene que mover ese techo (tipos vs instancias), no “subir seq a 16 bit y ya” si eso rompe I2 / WSP 16 B.

---

## 4. RogexWSP (el cable; no lo rediseñes)

16 bytes congelados (`wsp.h` / I1–I2):

- 4 átomos: src, rel, dst, time (uint8, vocabulario 0..47).
- E[6] int8 ±100, ejes oficiales: **V** valence, **A** arousal, **D** dominance, **C** certainty, **U** urgency, **B** bond.
- flags (bit veto 0x80).
- ext 5 B: domain, generator, style, slot, seq.

Primitivos 0..31 incluyen: YO, OTRO, AQUI, ALLI, UNIR, TEMER, OBSERVAR, PREGUNTAR, DESEAR, RECORDAR, OLVIDAR, ABRIR, CERRAR, SUBIR, BAJAR, CAUSA, EFECTO, POSIBLE, IMPOSIBLE, DESCONOCIDO, …

Derivados 32..47: AMOR, SOLEDAD, COMUNICAR, CONEXION, PELIGRO, BIENVENIDA, CONCIENCIA, WIRED, …

**Las 3 acciones de política hoy:** UNIR=approach, TEMER=avoid, OBSERVAR=wait. El resto de átomos **parsean y no cambian política** a propósito. Un verbo nuevo exige física nueva.

E[6] **no es emoción sentida.** Es neuromodulación de cable. I16: **δ no vive en E[V]**; δ actualiza `Q[s,a]`. I7: un umbral neuronal no decide IRQ/disco/hechos.

Cualquier “amígdala” o “emoción WSP” tiene que **usar** V/A/U/B y TEMER/gate, no añadir un segundo bus (I17) ni escribir `has_fact` desde E (I14).

---

## 5. Analogía de sistemas (laboratorio, no anatomía)

No crees `amygdala.py` / `hippocampus.py`. Mapa de lo **ya cableado**:

| Analogía | ¿Está? | Pieza real | Agujero |
|---|---|---|---|
| Tronco + cerebelo | parcial | loop, gate, T(s,a)→s′, 3 primitivas, E[U]/E[A] | T ya predice **pose 2D**, no planta 3D ni inercia continua |
| Ganglios basales | parcial sólido | Q, δ, gate NoGo, q.best | hábito no se actualiza en SHIFT (rebote); SN como dopamina no existe aparte de δ |
| Hipocampo + EC | parcial | CAM, encoder, T, I, transferencia | sin place/grid cells; EC real = ANTI-ALIAS; replay = SLEEP (no hecho) |
| Tálamo-cortical + neuromod | parcial | WSP, ATTEND, E[6] | el LLM no reescribe el tálamo (CAM) |
| TRN | **el análogo más limpio** | ATTEND 36/256 | falta CONFLICT→ATTEND (Q alto ∧ T mal) |
| Broca + premotora | casi vacío en el rápido | parse_reply, GBNF, last_cortex_action, plan.py off | sin LLM, Broca = silencio/stub; secuencias 2–3 = planner opt-in |
| Amígdala | **no como módulo** | TEMER, E[V], gate modify en mundos con `cell.threat`, R_THREAT | en CUERPO-1 el suelo no es THREAT: el miedo es el **choque**. No dupliques |

---

## 6. Neocórtex (Qwen) — cómo está y cómo no usarlo

```
modelo   Qwen3-4B-Instruct-2507 GGUF Q4_K_M (~2.5 GB)
runtime  llama.cpp, CPU, llama-server 127.0.0.1:8080
gramática echoai/nexus0/cortex.gbnf  →  una línea de átomos
cable    NAVI_CORTEX_CMD → stdin JSON (extract, q_row, t_pred, …) → parse_reply
timeout  default 10 s; operador NAVI_CORTEX_TIMEOUT=120
CI       stub de 20 líneas, sin pesos
```

Sirve: **paráfrasis de letreros** que el stub no conoce. No sirve: MMLU, Lean, usar un PC, caminar el laberinto por prosa.

Regla de Roger: el laberinto y la orientación espacial se resuelven **sin** LLM. Si el 4B camina por ti, el híbrido se acaba.

CONFLICT→ATTEND (aún no): despertar córtex cuando Q alto ∧ T mal. Eso es delfín/puente, no pulpo.

---

## 7. Visión: pulpo → delfín → chimpancé

Operacionaliza cada adjetivo. El lab **rechaza** “el modelo es consciente”.

### 7.1 Pulpo (base; no cerrado)

Ya hay: pose 2D + heading, T vs stepper (heading y paredes), choque = amenaza, transferencia de T al tapar un pasillo (4 aristas), mapa (WORLD-3) y cuerpo (CUERPO-1) **sin** segunda ficha.

Falta para **cerrar pulpo** según Roger:

- **Orientación espacial 3D.** Hoy z no existe. Heading es 4 valores en el plano.
- Caminar a propósito: WALK-1 (greedy START→GOAL). El cuerpo *puede* llegar (42 cobros en exploración); greedy no (horizonte 3).
- Acertijo espacial individual: p.ej. “el pasillo se cerró, da la vuelta” con `goal_hits>0` en `block`, córtex off. Hoy no.
- Acertijo tipo frasco: un objeto con física `ABRIR` **cuando haya tapa**, no antes.
- Predicción / si X entonces Y: ya es T e I; hay que verlo en 3D y tras sorpresa (no rebotar).

Un pulpo de lab **no** habla, **no** usa Broca, **no** siente E[V].

### 7.2 Delfín (después del pulpo 3D + WALK)

Traduce a conducta, no a poesía:

| Palabra | Pista de KPI (tú propones la buena; esto es el *tipo*) |
|---|---|
| Autoconciencia | ¿El agente usa YO vs OTRO de forma que un espejo/marca cambie su política? ¿Un modelo de su propia pose (el cuerpo ya *es* pose) vs un modelo de “otro bicho”? No “CONCIENCIA” como átomo mágico. |
| Empatía | OTRO + E[B] bond: ¿la política cambia por el estado de otro agente en el mismo WSP, sin copiar prosa? Preferible 2 cuerpos, no un LLM que diga “te entiendo”. |
| Plan a futuro | `plan.py` existe y **perdió** always-on en el anillo. ¿En la tortuga/3D un lookahead 2 **gana** a Q (`search_strictly_better>0`)? Si no, no lo enciendas. |
| Rompecabezas complejos | Varias reglas (pared + tapa + orden). Córtex solo si hay **letrero**; si no, T/Q. |

### 7.3 Chimpancé (después)

Herramienta = objeto con física + átomo que ya está en wsp.h (`ABRIR`, `SUBIR`, …). **Prohibido** 8 acciones “por si acaso”. MiniGrid no. Un palo que alarga approach, una tapa que exige ABRIR antes de GOAL.

---

## 8. Preguntas concretas (contéstalas)

**A. 3D.** Cómo discretizar (x,y,z,heading o 6 caras) sin matar seq de 8 bits ni CAM 4096. Jerarquía de frames (habitación vs voxel vs heading)? ¿El encoder deja de meter el índice crudo (ANTI-ALIAS) **antes** de 3D, o un 3D minúsculo (p.ej. 3×3×3×6=162) cabe y basta para “orientación tridimensional”? Trade-off.

**B. Entrenamiento / horizonte 3.** Opciones enteras: cambiar α (rompe bancos), trazas (ya midieron y salieron feas), hierarchical Q (opciones), credit assignment por I(s,s′), replay de noche (SLEEP) **sin** LLM, curriculum de distancias. Qué **no** hacer (float TD, PPO, retunear R).

**C. Amígdala y E[6].** Cómo un “miedo” útil (freeze, avoid, U alto) se lee de WSP **sin** módulo nuevo y **sin** poner δ en V. Relación con gate (hoy en el cuerpo el gate **no** ayuda: no hay baldosa THREAT). ¿El choque debería pintar kind THREAT un turno, o eso es teatro?

**D. Más acciones.** Criterio: “átomo ∈ wsp.h ∧ hay física”. Orden: ABRIR, SUBIR, SEPARAR… vs parametrizar destino (`UNIR → ALLI`) sin 4ª marcha. Coste en Q: hoy 4096×3; 4096×k.

**E. Dos cuerpos / OTRO.** ¿Empatía de delfín exige un segundo Agent en el mismo env, paquetes OTRO, E[B]? ¿O es demasiado pronto y es teatro de nombres?

**F. Qwen.** En pulpo 3D: **cero** llamadas. En delfín: CONFLICT→ATTEND + letreros de rompecabezas. Gramática: ¿seguir 4 átomos de política o permitir ABRIR cuando exista la puerta? Riesgo de que el 4B “resuelva” el puzzle en prosa y se rechace (bien) vs que se cuelen hechos (mal).

**G. SLEEP.** El lab dijo: compactar con 32 celdas o 76 poses es teatro. ¿A partir de qué ocupación de CAM / qué 3D tiene sentido NEXUS-5 (predicción baja, WAKE_new=0, sin LLM)?

**H. Autoconciencia.** Propón **un** test estilo espejo/marca o “predicir el efecto de *mi* giro en *mi* bump” que no sea un string CONCIENCIA. Si no hay test honesto, di que el delfín no debe empezar por ahí.

---

## 9. Invariantes (ganan a cualquier idea brillante)

```
I1  WSP = 16 B
I2  layout congelado (átomos + E[6] + flags + ext)
I3  0 FPU en el rápido (el córtex puede ser float)
I4  CAM/Q estáticos, 4096; sin malloc en el step
I5  VERIFY = Hamming≤3 ∧ extracto
I6  destroyed == 0 (CAM no poda)
I7  umbral neuronal no decide IRQ/disco/hechos
I8  Akida ausente se niega
I11 banco default cortex_calls = 0
I12 echoAI ≠ ISO
I14 hipótesis de córtex nunca has_fact=1
I15 CAM ≠ Q
I16 δ no en E[V]
I17 un solo cable
```

`parse_reply` no se toca. Oráculo ≠ córtex. `RingEnv.ask()` no existe. Kernel/ISO no se tocan por este plan.

Candados del anillo (§3) no se mueven. Informes opt-in: fichero propio, nunca `nexus0_report.json`.

---

## 10. Lo que ya se rechazó (no lo repropongas como paso 1)

API / 70B como agente. Dos LLM ahora. Prosa → hecho. MiniGrid / 8 acciones / OSWorld. Planner always-on. Resetear T al transferir. FAISS / embeddings float en el hot loop. VLM que escriba Q. LLM en el bus de spikes. Chat como producto. “NEXUS-8 AGI”. Entrenar el 4B a MMLU dentro del loop. Pintar baldosas THREAT para que el gate haga el trabajo del cuerpo.

Host: 13 GiB, ~5.4 GiB libres, Vega, sin CUDA. El 4B Q4_K_M **cabe y corre**. BF16 ~8 GB no.

---

## 11. Siguiente slice de código ya decidido (no lo sustituyas)

**WALK-1** (después de CUERPO-1, ya verde): greedy desde START llega a GOAL en la tortuga `open`, córtex off, **sin** cambiar `R_*`. El número de hoy a batir: `goal_hits=0` en 128 turnos, Q `0 0 0 0 -4 0 0 4 8 13`.

Tu hoja de ruta puede **preparar** 3D, amígdala-WSP, etc., pero el paso 1 de implementación que el lab va a pegar a Claude es WALK-1 salvo que argumentes, con números de §3.2, que WALK-1 es imposible sin tocar α y entonces hay que un **entrenamiento entero** *antes*. Si argumentas eso, da el KPI de ese pre-paso y el mutante que lo pone rojo.

---

## 12. Formato de tu respuesta

1. Juicio en una página: pulpo 2D qué es / qué no; el salto 3D más barato que no rompa seq=u8.
2. Tabla: cada capacidad delfín/chimpancé → KPI de conducta → pieza existente o slice nuevo → ¿LLM sí/no.
3. Amígdala y E[6]: un diseño de **uso**, no de módulo.
4. Entrenamiento: 2–3 métodos enteros vs horizonte 3, uno recomendado.
5. Acciones y herramientas: regla de oro + 3 verbos candidatos con física mínima.
6. Hoja de ruta 6–12 pasos, un KPI, orden. Marca cuáles son pulpo / delfín / chimpancé.
7. Lo que **no** sabes.

No implementes. No pidas el repo. No vendas consciencia.
