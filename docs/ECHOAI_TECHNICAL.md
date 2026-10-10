# echoAI — Qué es, con detalle técnico

**Fecha:** 2026-09-03. **Córtex:** OFF. **Hardware:** ninguno.
**Fuente:** `echoai/docs/{02-INVARIANTS,03-HYPOTHESIS,
05-NEXUS-0-SPEC,07-AKIDA,STATUS}.md`, `echoai/nexus0/*.py`, `echoai/README.md`.

> echoAI no es un chatbot. No es "SNN + LLM". No es el unikernel
> echOS 2.1 (que no lo embebe). Es un agente de dos relojes cuyo
> **núcleo funciona con el córtex apagado**.

---

## 1. La hipótesis científica

> echoAI es un agente cognitivo híbrido de dos escalas temporales en
> el que una representación discreta compartida (WSP/Q_N) conecta
> percepción, memoria, predicción y acción; un sistema rápido entero
> mantiene el estado, aprende de consecuencias y ejerce control; un
> sistema cortical lento genera hipótesis y planes; y un mecanismo de
> verificación y veto impide que las hipótesis del córtex se
> conviertan directamente en hechos o acciones.

Ciclo núcleo (córtex fuera salvo incertidumbre/novedad/complejidad):

```
S_t → A_t → Ŝ_{t+1} → S_{t+1} → δ_t → learning
```

**Por qué no "LLM más grande":** el salto que se busca no viene de
parámetros, viene de que ese ciclo siga vivo con la LLM apagada —
reactividad, memoria persistente, predicción, aprendizaje online,
selección de acción, incertidumbre, planificación y adquisición activa
de información, sin depender de un `AGI_SCORE`.

### 1.1 Firewall epistémico

```
FACT CHANNEL:        WSP → CAM → VERIFY | DESCONOCIDO
HYPOTHESIS CHANNEL:  WSP → cortex → proposal (también WSP)
```

Una hipótesis del córtex **nunca** se escribe como hecho en CAM.
`FACT ∈ {VERIFY, DESCONOCIDO}`. La prosa, por convincente que sea, no
cambia eso.

### 1.2 Tres canales que no se mezclan

```
REPRESENTACIÓN   ¿qué ocurre?     WSP 16 B + vértice Q_N
EPISTEMOLOGÍA    ¿lo sé?          VERIFY = (d_H ≤ 3) ∧ extracto
CONTROL          ¿qué hago?       Q[s,a] + gate OK|MODIFY|BLOCK
```

CAM = "qué pasó". Q-table = "qué debo hacer". No son la misma tabla.

---

## 2. Sustrato de control rápido (Fast Control Substrate)

Nombre que sustituye a "cerebro reptiliano" en la prosa del proyecto:

```
Q6/Q_N , CAM , E[6] , STDP , Q-table , GATE , WSP
```

AKD1000 sería, en el diseño, un acelerador de **algunas** poblaciones
de este sustrato — nunca el sustrato entero, y nunca de VERIFY ni de
WSP (§7).

### 2.1 El paquete WSP — el único cable

16 bytes, layout congelado en `kernel/include/wsp.h` (compartido con
echOS, ver el documento del ecosistema): `src, rel, dst, time, E[6]
int8 ±100, flags, ext{domain, generator, style, slot, seq}`.

`E[6]` — neuromodulación entera, **no** un dict float:

| Eje | Letra | Control |
|---|---|---|
| valence | V | no se sobrecarga con δ |
| arousal | A | I_STIM extra (`A // 20`) |
| dominance | D | reservado |
| certainty | C | `C < 20` → plasticidad ON |
| urgency | U | `U ≥ 60` → fuerza geodésica Hamming |
| bond | B | reservado |

---

## 3. Invariantes (I1–I17)

Fuente: `echoai/docs/02-INVARIANTS.md`. Romper uno es bug de producto,
no estilo.

| # | Contrato |
|---|---|
| I1 | `sizeof(wsp_packet_t) == 16` |
| I2 | Layout WSP congelado |
| I3 | 0 FPU en el paso rápido — enteros, `>>`, popcount |
| I4 | Heap-0 en CAM/Q6/Q — 4096 ranuras estáticas, sin malloc en el step |
| I5 | VERIFY = (d_H ≤ 3) ∧ extracto; si falta uno, DESCONOCIDO |
| I6 | `destroyed == 0` — el CAM no poda (KCC) |
| I7 | Umbral neuronal no decide IRQ / disco / #PF / `G_rxos` |
| I8 | Akida ausente se niega (`neurocpu akida`); no se finge silicio |
| I9 | Edge learning de BrainChip ≠ STDP propio (en prosa y comentarios) |
| I10 | Julios: RAPL/shunt real de un chasis, o silencio — QEMU no inventa mJ de NPU |
| I11 | LLM/LPU atada o apagada — banco NEXUS-0: `cortex_calls == 0` |
| I12 | Unikernel ≠ host — echoAI no entra en la ISO 2.1 |
| I13 | Q6 1-bit no baja de 48/48 |
| I14 | Firewall epistémico — hipótesis de córtex nunca `has_fact=1` |
| I15 | CAM ≠ Q — episodios en CAM, política en Q-table |
| I16 | δ no vive en `E[V]` — actualiza `Q[s,a]` |
| I17 | Un solo cable — no hay segundo event-bus de pensamiento |

### 3.1 Constantes numéricas

```
CAM_SLOTS     = 4096
HAM_LIMIT     = 3
WSP_BYTES     = 16
Q8_N          = 256          # neuronas LIF del spoke
VTH           = 40
LEAK_NUM/DEN  = 7/8
I_STIM        = 40
W_EDGE        = 32
T_MAX         = 16
C_PLASTIC     = 20           # C < 20 abre plasticidad
U_SHORT       = 60           # U ≥ 60 fuerza geodésica
WSP_E_MIN/MAX = -100 / 100
WSP_ATOM_PRIM = 32           # 0..31 primitivos SPEC
WSP_ATOM_MAX  = 48           # 32..47 derivados + pads
```

`Q[4096][3]` int8 = 12 288 B. NEXUS-0 indexa por **ranura CAM**
(0..4095), no por vértice de 16 bits completo (65536 no es
Heap-0-amigable para este experimento).

---

## 4. Arquitectura de software (`echoai/nexus0/`)

| Módulo | Rol |
|---|---|
| `constants.py`, `types.py` | contratos numéricos e I3–I4 |
| `encoder.py` | texto/evento → WSP 16 B semántico (n-gramas + banco vendor; FNV como baseline a perder) |
| `qtable.py` | política `Q[4096][3]` int8, γ=7/8, α=1/4, clip [-127,127] |
| `world.py` | `T[slot][a] → uint16`, KCC (mayoría de conteos, nunca borra), `conf()`, `inverse()` |
| `gate.py` | reglas OK/MODIFY/BLOCK, función pura |
| `env.py` | entorno sintético (anillo de 32 celdas, §5) |
| `loop.py` | bucle de un turno: observar → codificar → CAM → predecir → proponer → gate → actuar → aprender |
| `attend.py` | ATTEND — cuándo despertar el córtex (opt-in) |
| `escalate.py` | niveles Q/T/SEARCH/ASK/CORTEX vía margen ΔQ (opt-in) |
| `plan.py` | lookahead sobre T, `plan_depth` (default 0, apagado) |
| `oracle.py` | sensor externo que responde PREGUNTAR (fuera del mundo simulado) |
| `corridor.py` | segundo entorno (topología distinta) para probar transferencia |
| `cortex.py` | stub — sin CAM handle, sin `allocate`, sin `has_fact`; no puede VERIFY |
| `thought.py`, `view.py` | log de pensamiento + visor ANSI en terminal (stdlib puro) |
| `demo.py` | MVP interactivo — `python3 -m echoai.nexus0.demo` |
| `bench.py` | banco de KPI → `echoai/lab/*.json` |

Imports desde la raíz del repo (host, `PYTHONPATH=.`), **no copiados**:
`navi10_qn.py`, `navi10_cam.py`, `navi10_wsp.py`, `navi10_stdp.py`,
`navi10_spoke.py`, `navi10_dag.py`, `kernel/include/wsp.h`,
`kernel/navi/wsp_lex.c` (~150 n-gramas).

### 4.1 Bucle de un turno

```
observar celda → encoder.wsp_from_cell (no FNV)
              → vertex, lat = encode_event(wsp)
              → CAM lookup / allocate
              → ŝ' = T.predict(slot, a_prev) si hay
              → a_prop = Q.select(slot, turn)
              → decision, a = gate(...)
              → r, cell_next = env.step(a)
              → observe T(slot, a, slot_next)
              → e = d_H(ŝ', s') si había predicción
              → Q.update(slot, a, r, slot_next)
              → grabar episodio en CAM
              → metrics++
```

---

## 5. Entorno sintético — no es un robot, no es EEG

Anillo de 32 celdas (`env.py`), estado del agente = índice `i`. Cada
celda tiene un `kind` (GOAL, THREAT, EMPTY, NOVEL) con recompensa por
acción. `approach`: `i ← i+1 mod 32` tras cobrar la recompensa de la
celda actual. `avoid`: `i ← i-1 mod 32`, evitar una amenaza paga +8.
`wait`: no mueve, r=0. El entorno entrega un **extracto** verificable
de la celda — el agente no afirma hechos que el entorno no confirmó.
Semilla fija `20260903`.

Fases del banco: A (Q≈0) · B (256 turnos) · C (THREAT+approach
acumula δ<0) · D (probe en THREAT) · E (greedy no elige approach) ·
F (se mueve el THREAT 7→8) · G (64 turnos más, generalización).

---

## 6. Estado de cierre — la escalera NEXUS

Fuente: `echoai/docs/STATUS.md`. Cada rung cierra con un número
reproducible, no con una afirmación.

| Rung | Estado | El número que lo cierra |
|---|---|---|
| **NEXUS-0** — memoria, política, aprendizaje, gate | **cerrado** | `policy_after = [-12, +5, 0]`: approach en la fila THREAT es negativo y pierde contra avoid. `false_facts=0`, `destroyed=0`, `cortex_calls=0`, `encoder_beats_fnv` True (banco vendor 6/6 rel vs FNV 0/6) |
| **NEXUS-1** — world model ≠ fórmula del entorno | **cerrado** | `t_beats_ring` True: con 2 celdas JUMP a +2, T anota 0.9964 contra el baseline aritmético (i±1) de 0.9715, mismos 281 turnos puntuados |
| **NEXUS-2** — planificador como módulo | **cerrado** | Distancia 2: `T(13,approach)=14`, `T(14,approach)=15`, `Q[15,approach]=80` → `plan.scores(13,depth=2)=[70,0,0]` → approach; depth 1 = wait. No muta Q ni T. Opt-in, `plan_depth=0` por defecto |
| NEXUS-2 en el anillo de 320 turnos | **refutado** | plan-2 espera el 58 % de los turnos porque `T(s,wait)=s` hace que el lookahead de wait sea el máximo de su propia fila. Descontando ese self-loop (no aplicado), plan-2 es idéntico a `Q.best` |
| **NEXUS-3** — preguntar es una habilidad | **cerrado** | `novel_approach_return = +80` preguntando vs **−80** a ciegas, mismos 320 turnos y semilla. Una sola pregunta vale un vuelco de 160 puntos |
| **NEXUS-4i** — transferencia de topología (corridor) | **cerrado** | Mismo agente, entorno de 5 celdas distinto (no el anillo). Al entrar en SHIFT: `T(B,approach)=C` transferido, conf 3; el control no sabe nada. Primeras visitas en la ventana: 1 vs 4. No es AGI — se documenta así |

### 6.1 Sub-hallazgos honestos (medidos, no publicados como mejora)

- El plan-2 tiene `action_success` peor que el default (0.0969 vs
  0.2938 — un agente que espera no llega al GOAL) y `policy_after[0]`
  de −7 en vez de −12 (menos approach en la amenaza es menos castigo,
  no mejor política).
- El agente ciego de NEXUS-3 pisa la celda NOVEL 66 veces contra 5 del
  vidente: eso es parálisis (aprendió `wait`), no curiosidad.
- **`novel_hits_greedy = 0`** en ambos brazos: preguntar cambia el
  *valor* de la celda, no el *mapa* hacia ella — desde la celda 0 el
  agente greedy nunca inicia el viaje.
- **La pared de valor** (6↔7): el planificador desde c0 nunca cruza la
  celda 7 a ninguna profundidad; c11 es alcanzable *desde c8*, no
  desde home.

### 6.2 NEXUS-4 — atención al córtex, sin encenderlo

`attend(slot_hit, extract_ok, E, kind_novel, ham) -> (bool, reason)`:
predicado entero — MISS(1) NO_EXTRACT(2) LOW_C(3) NOVEL(4), evaluado
como OR. Con `--cortex`: **36/256** despertares (fue 187 en el primer
corte, corregido tras medir que `E[C]`=15 estaba bajo `C_PLASTIC` en
casi toda celda EMPTY/GOAL). Default: **0**. `cortex.py` no puede
escribir hechos — no tiene handle de CAM, `allocate` ni `has_fact`, y
un test lo comprueba.

El stub sólo sabe una cosa: en NOVEL propone el mismo paquete
PREGUNTAR que el loop rápido ya conoce; en cualquier otro `reason`
devuelve la observación sin cambios. `cortex.parse_reply` acepta
**sólo** 32 hex o una línea compacta de átomos conocidos — una frase,
un JSON, una claim VERIFY, todo eso vuelve `None` y el loop conserva
la observación (`cortex_rejected` lo cuenta). `cortex.complete()`
puede correr un subproceso local vía `NAVI_CORTEX_CMD` (JSON in/out,
timeout 10 s, sin shell); sin esa variable, no hay cliente HTTP en el
árbol y responde el stub.

### 6.3 NEXUS-4h — el oráculo vive fuera del mundo

`RingEnv.ask()` ya no existe. Reemplazado por tres pasos separados:
`oracle.reply()` (texto crudo, no toca env/Q/T/CAM) →
`oracle.accept(text)` (VERIFY: `NOVEL_CLEAR` o `None`) →
`RingEnv.reveal(x)` (física, sólo tras `accept`). `oracle.accept` es
deliberadamente **distinto** de `cortex.parse_reply`: una respuesta
que pasa el parser del córtex no pasa la verificación del oráculo —
"YO → PREGUNTAR → DESCONOCIDO @AHORA" lo prueba en ambos sentidos.

### 6.4 Otros mecanismos cerrados

- **T_CONF (NEXUS-4d):** confianza 0–3 leída de contadores enteros
  (`n`, `alt_n`) que `observe()` ya mantiene, sin float nuevo.
- **Inversa I(s,s') → a (NEXUS-4e):** 36/36 filas de T con evidencia
  recuperan su acción desde la tabla inversa; tamaño real 36 entradas
  (no 4096², que nunca se construyó).
- **Trazas de elegibilidad (NEXUS-3b):** opt-in, `z[4096][3]` entero,
  extiende el crédito 3 celdas atrás en el corredor — con el coste
  medido de diluir la señal de amenaza (`policy_after` pasa de
  [-12,+5,0] a [-1,0,0]); por eso quedan apagadas por defecto.
- **N ≠ S ≠ δ (NEXUS-4g):** novedad, sorpresa y delta de aprendizaje
  se cuentan como tres hechos distintos del turno, no un solo
  `novelty` conflacionado como antes.

---

## 7. Hardware — Akida, sin placa

**Estado de laboratorio: 0 placas.** `neurocpu akida` existe y **se
niega**. NEXUS-0 no espera silicio: 100 % software LIF + tablas
enteras. Roadmap de BrainChip 2026 (GenAI, TENNs, LLM-on-chip): fuera
del laboratorio hasta que ese silicio esté en mesa.

Piezas ya en el árbol padre (compartidas con echOS, ver documento del
ecosistema): IDs de backend `SOFTWARE|AKIDA|LOIHI`
(`kernel/event/rx_backend.h`), switch que marca `akida available =
false`, `cmd_neurocpu` que se niega con frase honesta, probe PCI
`drivers/npu/akida.c` (`1e7c:bca1`; sin placa = *absent*).

Cinco "cerraduras" documentadas antes de que Akida decida algo, ninguna
cerrada: 0) Host MetaTF (quantizeml → cnn2snn → `.fbz` → `akida run`,
sólo simulador), 1) descubrir silicio (sin pila USB en rxOS hoy), 2)
HardwareDriver bare-metal, 3) codec WSP/Q6 → tensor uint8, 4) energía
comparada RAPL CPU vs NPU en el mismo chasis. Akida, si llega, **no**
decide VERIFY, hechos, veto, IRQ, disco ni `G_rxos` — puede proponer
un `a*`, el gate en CPU manda.

---

## 8. Qué está explícitamente prohibido en el núcleo

Bus de eventos nuevo, `internal_state` en float, vector DB /
embeddings float / FAISS / Pinecone, importar `navi7_lab`/`navi9_self`/
`navi75_voice`/`navi86_skills` al núcleo, llamar LPU/LLM/`think()` de
navi10 en el banco principal, clonar `Layer256`/`navi_q6_step` (se
importan, no se copian), meter δ en `E[V]`, driver Akida/MetaTF/`.fbz`,
tocar `kernel/`/ISO/`userland/`, afirmar julios de NPU sin placa,
relabelar edge learning de BrainChip como STDP propio, crear
`brainstem.py`/`amygdala.py`/un `nexus/` paralelo.

---

## 9. Cómo verlo y reproducirlo

```bash
cd /home/roger/REALRXOS/RXos
export PYTHONPATH=.

python3 -m echoai.nexus0.demo            # en vivo, 352 turnos, 5 fps
python3 -m echoai.nexus0.demo --short    # 48 turnos
python3 -m echoai.nexus0.demo --replay   # repite echoai/lab/thought.jsonl

PYTHONPATH=. python3 -m echoai.tests.test_nexus0   # KPI verdes
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.bench --cortex     # lab/nexus0_cortex_report.json
PYTHONPATH=. python3 -m echoai.nexus0.bench --escalate   # lab/nexus0_escalate_report.json
PYTHONPATH=. python3 -m echoai.nexus0.bench --oracle PATH
PYTHONPATH=. python3 -m echoai.nexus0.corridor            # lab/nexus0_corridor_report.json
```

Candados del banco por defecto (sin flags), leídos de `README.md`:

```
policy_after              [-12, +5, 0]
false_facts / destroyed / cortex_calls   0 / 0 / 0
novel_approach_return     +80
surprise_known             1
encoder_beats_fnv          True
t_beats_ring                True
```

---

## 10. Qué es cada nombre (para no confundir)

| Nombre | Qué es |
|---|---|
| echOS | unikernel (cuerpo). 2.1 **no** embebe echoAI |
| echoAI | este workspace: el agente de dos relojes |
| NEXUS-0…4i | rungs sucesivos del mismo experimento, no marcas distintas |
| NAVI 10 | motor host (`./navi10`, Python/TUI); NEXUS-0 importa piezas suyas, no construye alrededor de su `--ask` |

---

## 11. Qué sigue, y qué no es esto

El programa situado de este directorio **está cerrado**: no es el
final de un sistema nervioso, es el final de esta tesis (NEXUS-0 →
corredor, §6). Lo que sigue —sueño/consolidación, una LLM real detrás
del firewall, un cuerpo, Akida— es una línea posterior del proyecto. No se usa la palabra AGI como
objetivo en este árbol.

---

*Generado a partir de `echoai/README.md`,
`echoai/docs/{02-INVARIANTS,03-HYPOTHESIS,05-NEXUS-0-SPEC,07-AKIDA,
STATUS}.md` y lectura de `echoai/nexus0/*.py`. 2026-09-03.*
