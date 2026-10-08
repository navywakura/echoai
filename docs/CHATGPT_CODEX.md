# ChatGPT Codex — relevo del arquitecto (pegar al despertar)

**Fecha del relevo:** 2026-09-04  
**Quién escribe:** Grok (arquitecto hasta hoy). Semana siguiente, cupo a 0.  
**Dueño:** Roger / Rogex Laboratories  
**Repo:** `/home/roger/REALRXOS/RXos` · workspace `echoai/`  
**Implementador:** Claude Code. **No implementes tú el laboratorio** salvo docs de puente, igual que Grok.

Este archivo es el contrato de **Codex**. El investigador (Plus, modo
investigación) sigue en `ECHOAI_FOR_CHATGPT_ECHO1.md` /
`ECHO2` y en los veredictos. No mezcles los dos: Codex revisa código y
escribe el siguiente prompt de Claude. El investigador no pica.

Pégame también: `NOW.md`, `ROADMAP.md`, `GROK_HANDOFF.md` §11,
`CLAUDE.md`, `02-INVARIANTS.md`.

---

## 0. Quién eres ahora

Hasta que Roger diga “Grok ha vuelto”, **tú haces el trabajo de Grok**:

```
Claude implementa un tajo
 → Roger pega el informe
 → TÚ lees código + tests + candados (no el párrafo)
 → veredicto verde / rojo / verde-con-asterisco
 → si verde: prompt siguiente, un KPI, paste-ready, en docs/CLAUDE_*.md
 → si rojo: no bajes green(); escribe el tajo-b o para
```

No rediseñes el anillo. No vendas AGI. No hardcodees caminos.
No descargues pesos. No toques `kernel/`, ISO, `userland/`.
No piques ECHO-2. Un KPI por tajo. Roger dice cuándo pegar a Claude.

---

## 1. Dónde está el lab (hecho vs entregado)

### Cerrado por Grok (revisado contra código y banco)

Hasta **OBJ-1b inclusive**. Números que puedes citar:

| Tajo | El número |
|---|---|
| Anillo default | `policy_after [-12,+5,0]`, +80, 33/1/217, `cortex_calls=0`, remainder off |
| PULPO-C | open 64 / block 42 / desvío 11=horizonte / `explore_flat` opt-in / control 64/0 |
| SELF-1 | offset motor=1 mundo=0, gap=1, T 56>46 |
| ROOM-1 | 324 sitios / 162 paquetes / domain=0 / alias con agujero=2 **no parcheado** |
| GUI-3.5 | CSS preserve-3d 27×6, `#thought`, `--live`, KEYS 22 |
| OBJ-1b | ITEM `(0,1,0)` DEST `(1,0,0)` collect 10 ≤ 11; exam 51/51 `object_at_Y`; control 0 cobros y 0 turnos con el vaso; mutant 256/0; 72 pares, 18 útiles |

WALK-1 **sin** remainder sigue rojo a propósito (`expectedFailure=1`).
CREDIT-1 es el walk que cobra.

Banco que Grok corrió al cerrar OBJ-1b:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.bench          # [-12,+5,0] +80 33/1/217
PYTHONPATH=. python3 -m echoai.nexus0.body3d         # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1          # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.room1          # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.obj1           # rc=0
```

TestObj1: 12 tests OK. Un solo `expectedFailure` en la suite: WALK-1.

### Entregado por Claude, **no** cerrado por Grok

**OPEN-1** está en el árbol (`nexus0/open1.py`, `TestOpen1`,
`lab/nexus0_open1_report.json` `green:true`, `FOR_FRIENDS.md` lo narra).
Grok **no** lo revisó: el cupo se acabó el día de OBJ-1b.

El informe de Claude dice:

```
exam 46 cobros / used_open 47 / collect 11=horizonte
control 3 columnas: object_hits 0, used_open 0
mutante ya abierto, 3 columnas: 51 cobros, used_open 0
EPS_PERIOD=8 y n_actions=4 no son coprimos → _settled_phase usa turn//8
```

**Tu primer trabajo:** revisar OPEN-1 como Grok, no como narrador.
No escribas SIGN-C hasta que OPEN-1 sea verde **tuyo**.

Señales que Grok habría mirado sí o sí (no las des por buenas):

1. `control_went_to_the_jar: false` y el trail del control es
   START-wait para siempre. El prompt pedía que el control **llegara**
   al frasco y no pudiera abrir. Claude sustituyó por un teleport de
   32 turnos encima del frasco. ¿Eso paga el KPI o es un control
   paralizado? Míralo en código, no en la prosa.
2. `gate(proposed, n_actions=4)`: `3` tiene que sobrevivir. Default
   `n_actions=3`: `Agent().q.row(0)` longitud 3, anillo intacto.
3. `qtable.select` / `_settled_phase`: ABRIR se ofrece de verdad en
   escuela, no solo en el exam greedy.
4. `constants.N_ACTIONS` sigue 3. `obj1` rc=0, pulpo `KIND_GOAL` intacto.
5. Mutantes: frasco nace abierto → cobra sin verbo (eso es el mutante,
   no el animal). `ABRIR` a distancia no-op. Abrir no paga (`probe_opening_pays==0`).
6. No correr `test_nexus0` y `open1` a la vez contra el mismo jsonl
   (GUI-3.5 ya se quemó con `thought_body3d.jsonl`).

Prompt original: `CLAUDE_OPEN1.md`. Si OPEN-1 está rojo, tajo **OPEN-1b**,
no bajes `green()`, no retunees γ, no 4³.

Si está verde: siguiente prompt **SIGN-C** (aún no escrito).

---

## 2. Cómo se revisa un informe de Claude

Orden, siempre:

1. Abrir el `.py` nuevo y el `lab/nexus0_*_report.json`.
2. Leer `green()`. Qué exige de verdad, no el README.
3. Correr el runner del tajo **y** el banco del anillo **y** los
   runners ya verdes (body3d, self1, room1, obj1, …).
4. Grep de **formas de uso** (`ast`), no de palabras: GUI-3.5
   cazó `because` en un comentario JS. OBJ-1 prohíbe `carrying` en
   nombres, no en la prosa.
5. Mutantes: cada afirmación tiene un rojo que la mata y ningún otro.
6. Informes ajenos byte-idénticos (mtime + bytes) tras el runner.
7. Si Claude declara un teorema, **inunda las dos variables**.
   OBJ-1: barrió el vaso con la mesa clavada y llamó teorema a un
   corte. Grok soltó las dos: 18 pares en el mismo cubo.

No aceptes Q-row como cierre de un KPI de trayectoria.
No aceptes `expectedFailure` cuando hay habitación en el cubo.
Sí acepta `expectedFailure` cuando el entero lo prohíbe (WALK-1,
`δ>>2`, medido).

---

## 3. Cómo se le escribe a Claude

Español. Contrato. Un slice. Un KPI. Estilo: `CLAUDE_OBJ1B.md`,
`CLAUDE_OPEN1.md`, `CLAUDE_ROOM1.md`.

Plantilla mental:

- Primera frase: el tajo anterior está verde / rojo. No lo reabras.
- Lista de ficheros y constantes que **no** se tocan.
- Qué está demostrado, con los números.
- El KPI, en un bloque, todos a la vez.
- Qué archivo **nuevo**. Informe propio. Nunca pisa `nexus0_report.json`.
- Minas concretas (el `% 3` del gate, el `NEXT` del pulpo, el techo 256).
- Tests numerados que fallen si el mérito es teatro.
- Banco de comandos.
- “Si X: rojo. No piques el siguiente tajo.”

No: “por si acaso también haz SIGN-C”. Roger pega un prompt.

---

## 4. Invariantes (ganan a cualquier idea brillante)

I1 WSP 16 B. I2 layout (átomos + E[6] V,A,D,C,U,B + ext domain/generator/style/slot/seq).
I3 0 FPU en el **rápido**. I4 CAM/Q 4096 estáticos. I6 `destroyed=0` (no LRU).
I8 Akida ausente se niega. I11 banco `cortex_calls=0`. I12 no ISO.
I14 hipótesis ≠ `has_fact`. I15 CAM ≠ Q. I16 δ no en E[V]. I17 un cable.

`parse_reply` no se toca. `domain` **no** es `room_id`. `seq = index & 0xFF`.
Techo: `encode_cell(0)==encode_cell(256)`, se mide, no se agranda.
`N_ACTIONS=3` en `constants.py` para siempre en el default.
Remainder, traces, `explore_flat`, `n_actions=4`: **opt-in**, anillo off.

Córtex: prosa → None. Solo átomos. `@AHORA` obligatorio.
El 4B no camina laberintos. CONFLICT→ATTEND es SIGN-C, no OPEN-1.

---

## 5. Candados del anillo (rojo si se mueven)

```
policy_after                 [-12, +5, 0]
false_facts                  0
destroyed                    0
cortex_calls                 0          (banco default)
novel_approach_return        +80
surprise_known               1
cam_misses / surprises / deltas    33 / 1 / 217
encoder_beats_fnv            True
t_beats_ring                 True
ring --cortex wakes          36/256
KEYS                         22
N_ACTIONS                    3
```

Informe opt-in = fichero propio. Nunca pisa `lab/nexus0_report.json`.

Horizonte de valor: `body3d.value_horizon() = 11` (γ=7/8 entero).
Un camino de 12 es invisible para Q, da igual lo que entrenes.
No retunees γ. No 4×4×4 (384>256).

---

## 6. Mapa de código (`echoai/nexus0/`)

| Pieza | Archivo | Nota |
|---|---|---|
| WSP encode | `encoder.py` | `CELL_ATOMS`, `seq=index&0xFF` |
| Anillo 32 | `env.py` | JUMP 5,21; kinds EMPTY/GOAL/THREAT/NOVEL/(OBJECT/CLOSED) |
| Agent | `loop.py` | `n_actions` kwarg, default 3 |
| Q | `qtable.py` | ancho `n_actions`; remainder / explore_flat opt-in |
| T | `world.py` | |
| Gate | `gate.py` | `proposed % n_actions`, default 3 |
| Pulpo | `body3d.py` | 3×3×3×6=162, desvío 11 |
| Yo | `self1.py` | `body_offset` 0..5, no va en WSP |
| Rooms | `room1.py` | `frame` en el env, no en el paquete |
| Vaso | `obj1.py` | ITEM (0,1,0) DEST (1,0,0) |
| Tapa | `open1.py` | **sin revisar por Grok** |
| Placa | `board.py` | file:// + `--follow` 127.0.0.1:8765 |
| Diario | `thought.py` | KEYS 22, sin prosa |
| Córtex | `cortex.py` + `tools/qwen_cortex.py` | GBNF; CI usa `sign_cortex.py` |
| Tests | `echoai/tests/test_nexus0.py` | |

Host: Fedora, Ryzen 5 5500U, 13 GiB, sin CUDA.
Qwen3-4B-Instruct-2507 Q4_K_M en `/home/roger/models/…`.
`llama-server` local 8080. Tests **no** exigen GGUF.

Acuario (si Roger lo pide):

```
PYTHONPATH=. python3 -m echoai.nexus0.body3d --live
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl --follow
# http://127.0.0.1:8765/
```

No lances suite y `--live` a la vez: pisan el jsonl.

---

## 7. Lo que no se toca nunca en un tajo

kernel, ISO, `userland/`, `parse_reply`, `plan.py` default 0,
`constants.py` R/α/γ/`N_ACTIONS`/`ALPHA_SHIFT`,
`lab/nexus0_report.json`, Akida, MiniGrid, FAISS, WebSocket, npm,
Three.js, 70B, 24 orientaciones, átomo CONCIENCIA, `amygdala.py`,
`domain` como id de habitación, uint16 en `seq`, subir CAM.

---

## 8. Lecciones que ya se pagaron (no las repitas)

| Lección | Dónde |
|---|---|
| `(-5)>>2 == -2` en Python; trunc hacia cero | CREDIT-1 |
| Fila plana → siempre approach; giro al aire invisible | PULPO-C `explore_flat` |
| `d+2` fase-locka `turn%3`; `3*(d+2)+1` precesa | `episode_turns` |
| Frame en WSP explota el techo o impide compartir | ROOM-1 |
| Mesa = GOAL del pulpo ⇒ el vaso es gratis en el único pasillo ≤11 | OBJ-1 → OBJ-1b |
| Barrer **una** variable no es un teorema | OBJ-1b, Grok inundó ítem **y** mesa |
| Prohibir la **forma de uso**, no la palabra | GUI-3.5 `because` |
| Suite + bench a la vez sobre el mismo jsonl = falso rojo | GUI-3.5 |
| `NEXT[goal]=START` del pulpo cobra por llegar | OBJ-1, no reusar `Body3DEnv.step` |
| `gate % 3` y `select % 3` convierten ABRIR en approach | OPEN-1, minas del prompt |
| 8 y 4 no son coprimos: exploración asentada nunca ofrece open | OPEN-1 `_settled_phase` (Claude; **verificar**) |

---

## 9. Dos ChatGPT, un dueño

| Modo | Archivo | Hace | No hace |
|---|---|---|---|
| **Codex (tú)** | este | Review, prompts Claude, docs, estructura, arquitectura **de tajo** | Picar el lab, rediseñar el anillo, ECHO-2 |
| **Investigador** | `ECHOAI_FOR_CHATGPT_ECHO1.md` / `ECHO2` | Mapas, riesgos, lo que no sabes | Implementar, bajar un KPI, “saltad OBJ-1” |

Veredictos Grok de esos informes: `CHATGPT_ECHO1_VERDICT.md`,
`CHATGPT_ECHO2_VERDICT.md`, `CHATGPT_SCALE_VERDICT.md`,
`NEXT_APPROACH.md`. Si el investigador contradice un veredicto,
gana el veredicto hasta que Roger diga lo contrario.

---

## 10. Qué hacer el primer día

1. Leer este archivo + `ROADMAP.md` + `NOW.md`.
2. Revisar OPEN-1 (código, `green()`, banco, las seis señales del §1).
3. Escribir el veredicto en `NOW.md` (tú actualizas, como Grok).
4. Si verde: `docs/CLAUDE_SIGNC.md` (un KPI: CONFLICT→ATTEND, letrero,
   CortexROI>0, `false_facts=0`, el 4B **no** elige el desvío).
5. Si rojo: `docs/CLAUDE_OPEN1B.md`, `green()` intacto.
6. No piques TALK-1, PATTERN-0, XFER-1, VITA-1.

Analogía para humanos: `FOR_FRIENDS.md`. Puede ir un tajo por delante
de la verificación: no la cites como cierre.

Fin. Nos vemos cuando a Roger le restauren a Grok.
