# GROK_HANDOFF — copiloto de Claude (echoAI)

Pégame este archivo + `NOW.md` al despertar. Es la memoria del arquitecto.
**Relevo 2026-09-04:** Grok en pausa (cupo). Interino: ChatGPT Codex,
contrato `CHATGPT_CODEX.md`, mapa `ROADMAP.md`. No reimplementes el anillo.
GUI-3.5 cerrado. OBJ-1b **verde Grok**. OPEN-1 entregado, **sin** review Grok.
Siguiente trabajo del arquitecto: revisar OPEN-1, no escribir SIGN-C todavía.

**Fecha de cierre de esta memoria:** 2026-09-04  
**Repo:** `/home/roger/REALRXOS/RXos` · workspace `echoai/`  
**Dueño:** Roger / Rogex Laboratories  
**Sesión viva:** `echoai/docs/NOW.md`. CORTEX-1 y GUI-1 **cerrados**.
Qwen-0 **verde**. WORLD-3 **verde**. GUI-2 **verde**. CREDIT-1 **verde**.
PULPO-C **verde**. SELF-1 **verde**. ROOM-1 **verde**. GUI-3.5 **verde**.
OBJ-1b **verde** (vaso (0,1,0)→mesa (1,0,0), collect 10, control 0).
Siguiente: **OPEN-1**.
Para amigos: `echoai/docs/FOR_FRIENDS.md`. WALK-1 sin resto sigue rojo.
ECHO-1 **no cerrado**: OPEN-1 → SIGN-C → TALK-1 → PATTERN-0 → XFER-1.
ECHO-2 mapa (ChatGPT, Grok aceptó el eje): `CHATGPT_ECHO2_VERDICT.md`.
`H` en el Agent, muerte = episodio, Q/T persisten, control reset.
No implementar. Primer tajo futuro: VITA-1, después de XFER-1.

---

## 1. Quién hace qué

| Rol | Quién | Qué |
|---|---|---|
| Dueño, tesis, qué se cita | Roger | Un KPI por vez. Candados no se negocian. |
| Arquitecto / copiloto de Claude | **Grok**, en pausa. **ChatGPT Codex** hasta que Roger restaure a Grok. Contrato: `CHATGPT_CODEX.md`. | Revisa informes de Claude contra código y tests. Escribe el **siguiente prompt**, paste-ready. No implementa el laboratorio salvo empaquetar/docs de puente. |
| Implementador | **Claude** | Un slice. Lee `echoai/CLAUDE.md` + `echoai/CLAUDE_SITUATED.md`. No rediseña. |
| Investigador externo | ChatGPT (modo investigador) | Firmó la tesis situada. Luego entregó el informe de escalado (4B local, CORTEX-1, GUI Qt, grafo). Grok **corrigió** ese informe en `NEXT_APPROACH.md`. |
| Gemini | interlocutor de futuro | Briefing: `ECHOAI_FOR_GEMINI.md`. No es contrato de código. |

Flujo que funcionó:

```
Claude implementa → Roger pega el informe → Grok revisa código/tests/candados
 → veredicto + prompt siguiente (un KPI) → Roger lo pega a Claude
```

No más prompts a Claude “por si acaso”. Roger dice cuándo.

---

## 2. Qué es el proyecto (una frase)

echoAI = agente de **dos relojes** que funciona **con el córtex apagado**. Cable único WSP 16 B. Un LLM, si se enchufa, propone hipótesis. Nunca escribe hechos.

No es AGI. No es chatbot. No es SNN+LLM. No es echOS 2.1 (el unikernel **no** embebe echoAI). No es Akida (0 placas). No es `navi10 --ask` ni el teseracto `--tui`.

Analogía de trabajo (no anatomía): si hay neocórtex, es un LLM **detrás del firewall**. Lo construido es el animal **sin corteza**. El enchufe existe. Está vacío.

Tesis: situated learning, no “SNN+LLM”.  
Prueba ya hecha en miniatura: el pasillo (T transferida, se equivoca donde el mundo cambió, se entera equivocándose).

---

## 3. Programa situado: CERRADO

Orden ChatGPT que el lab ejecutó, todo verde:

1. T_CONF 0–3  
2. Inverso I(s,s')→a  
3. Escalada 0/2 + ΔQ → `search_strictly_better=0` (ChatGPT tenía razón: nivel 2 copia a Q en este anillo)  
4. N ≠ S ≠ δ → `surprise_known=1` (fase F, celda 5, mismo slot)  
5. Oráculo fuera → `RingEnv.ask()` **no existe**; +80 se mantiene  
6. Pasillo HOME/SHIFT → transferido conoce B al entrar; control no  

**No reabrir** planner always-on, inverse, escalate, T_CONF, oracle, el anillo de 32 como único mundo.

`plan.py` se **queda** como módulo (c9, 8→11). Default `plan_depth=0`.  
Niveles 1/3/4 de `escalate.py` nombrados, no cableados (T ya corre; ASK es `_ask()`; CORTEX es ATTEND).

---

## 4. Candados del banco default (sin flags)

Si un slice los mueve, está rojo. Informe opt-in = **otro** JSON, nunca pisa `lab/nexus0_report.json`.

```
policy_after                 [-12, +5, 0]
false_facts                  0
destroyed                    0
cortex_calls                 0
novel_approach_return        +80        (--no-ask: −80)
questions                    1
surprise_known               1
cam_misses / surprises / deltas    33 / 1 / 217
encoder_beats_fnv            True
t_beats_ring                 True      (citar JUMP, no 0.9964 como world model)
level_search                 0
oracle_source                sensor
oracle_rejected              0
search_strictly_better       0
```

`--cortex` wakes **36/256**, no ha subido. Tests **155**. Lex **235**, `gen_lex --check` in sync.

Ver: `python3 -m echoai.nexus0.demo --short` (córtex apagado, terminal).

---

## 5. Piezas (no reinventar)

| Pieza | Dónde | Nota |
|---|---|---|
| WSP 16 B | encoder, `wsp.h` | único cable. I17 |
| CAM 4096 | `navi10_cam` import | `put()` siembra hits=1 → N es `hits<=1` |
| T + conf + I | `world.py` | I ya está. Conflicto impide T_CONF=3 |
| Q[4096][3] | `qtable.py` | δ no vive en E[V]. margin() = ΔQ |
| gate | `gate.py` | |
| ATTEND | `attend.py` | no lee E[C]; 36/256 |
| PREGUNTAR | `loop._ask()` | no es 4ª marcha |
| oráculo | `oracle.py` | reply → accept → `env.reveal`. accept ≠ parse_reply |
| planner | `plan.py` | default off |
| escalate | `escalate.py` | 0 vs 2; strictly_better=0 |
| córtex stub | `cortex.py` | `NAVI_CORTEX_CMD` subprocess; parse_reply átomos/hex; prosa=None. Stub = PREGUNTAR. ROI≈0 |
| anillo | `env.py` | 32 celdas, JUMP (5,21), NOVEL 11, fase F 7→8 |
| pasillo | `corridor.py` | HOME A→B→C→D / SHIFT A→B→X→D. Tabla, no (i+1)%n. KPI 4: approach en B **sigue ganando**; aprende “entra en X y esquiva” |
| visor | `view.py` + `demo.py` | ANSI. `thought.KEYS` es conjunto exacto en tests |
| Agent | `loop.py` | admite `env=` |

Firewall: córtex no tiene CAM, no `allocate`, no `has_fact`. I14.

Hoy, si parse_reply devuelve UNIR/TEMER/OBSERVAR, el loop **lo ignora**. Solo si rel=PREGUNTAR llama `_ask()`. **Ese cable falta** y es el corazón de CORTEX-1.

---

## 6. Números que se citan / que no

**Sí:** JUMP (T ≠ i±1); preguntar +80/−80; ATTEND 36/256; pasillo conoce-B vs no; surprise_known=1; strictly_better=0.

**No:** T=0.9964 como world model; “el planner es inútil” (es inútil *siempre-on en este anillo*); E[6]=emoción; Akida=cerebro reptiliano; echOS 2.1 piensa; AGI.

Pasillo KPI 4: no se retuneó `R_AVOID_OK`. Documentado en STATUS.

---

## 7. Informe ChatGPT (escalado) y veredicto Grok

ChatGPT propuso: Qwen3-4B-Instruct-2507 + llama.cpp + GBNF; CORTEX-1 env con letrero lingüístico; GUI PySide6/QML fuera del loop; mundo = grafo procedural no grid; sleep determinista sin LLM y más tarde; no dos modelos ahora; no Akida para cuerpo.

**Aceptado el eje.** Correcciones en `echoai/docs/NEXT_APPROACH.md`:

1. Inverso ya existe — no es paso 6.  
2. Escalera 0–4 ya existe — no reconstruir. Search copió a Q.  
3. Córtex debe proponer acción al **gate** (UNIR/TEMER/OBSERVAR → approach/avoid/wait). Hipótesis, no hecho. `@AHORA` obligatorio para parse_reply.  
4. CI **sin pesos**: script que habla átomos. 4B solo en informe ROI. Anillo default `cortex_calls=0`.

Letrero: lo entrega el **env** (como el extracto de una celda). El LLM interpreta y emite acción. No escribe hecho “amber=goal”. El rápido no parsea español: por eso hace falta corteza.

No contar PREGUNTAR como “el córtex cambió algo”: el stub ya pregunta.

GUI: extra, `nexus0/` sigue stdlib. Ampliar `thought.KEYS` es slice GUI, no efecto secundario de CORTEX-1. Replay jsonl; no WebSocket; no segundo bus.

Mundo grande: grafo 256–4096 **después** de CORTEX-1. CORTEX-1 cabe en 4–8 celdas. No resetear T al transferir (el pasillo conservó T/CAM/Q). Alias WSP vs dinámica = KPI del mundo grande.

Sleep: en 32 celdas ROI≈0. Compactar sirve cuando hay más episodios que reglas. No ahora.

Dos LLM, API, 70B, MiniGrid, 8 acciones, ISO, FAISS, planner always-on: no.

---

## 8. Siguiente slice cuando Roger despierte: CORTEX-1

Único trabajo. Un KPI.

- Env **nuevo**, no el anillo.  
- Letrero en lenguaje; rápido ciego; córtex propone UNIR o TEMER.  
- Cable: parse_reply → si acción, `proposed` al gate; si PREGUNTAR, `_ask()`; si reject, Q.  
- No toca parse_reply, accept, plan.py, candados del anillo.  
- Informe: `lab/nexus0_cortex1_report.json`.  
- KPI: `false_facts=0` ∧ ≥1 decisión ≠ Q y ≠ PREGUNTAR ∧ reward córtex > rápido ∧ CortexROI>0 ∧ anillo default intacto.  
- Modelo real opcional vía `NAVI_CORTEX_CMD`; tests con stub determinista.

CORTEX-1 **cerrado** (2026-09-03, verificado por Grok: 173 tests OK,
bench candados, `spoke` guarda el eco OBSERVAR/TEMER). Prompt:
`echoai/docs/CLAUDE_CORTEX1.md`. Informe: `lab/nexus0_cortex1_report.json`.

GUI-1 **cerrado** (2026-09-03, verificado: 185 tests, KEYS 17, sum n/s/δ
= 33/1/217, board.html 112321 B / 352 turnos, placa SIGN 2 celdas y
CORTEX en dashed). Prompt: `echoai/docs/CLAUDE_GUI1.md`.

CORTEX-1 y GUI-1 **cerrados**. Sesión 2026-09-04: el 4B **sí** se enchufa
hoy (informe de operador, harness en `tools/qwen_cortex.py`, CI sin
pesos). Claude implementa **WORLD-3** (`docs/CLAUDE_WORLD3.md`). No
mezclar los dos en el mismo PR mental: archivos distintos.

Bicho → pulpo (WORLD-3 + cuerpo WSP, Qwen **off**) → “humano” de lab
(pulpo + 4B desenchufable). El rápido nunca es un humano. Astra/GPT-4
no son el banco. Ver `NOW.md`.

---

## 9. Archivos que debes leer al recuperar

Orden:

1. Este archivo (`echoai/docs/GROK_HANDOFF.md`)
2. `echoai/docs/NOW.md` — sesión viva (Qwen-0 + WORLD-3)
3. `echoai/docs/CLAUDE_WORLD3.md` — prompt de Claude
4. `echoai/docs/NEXT_APPROACH.md` — contrato
5. `echoai/CLAUDE.md` + `echoai/CLAUDE_SITUATED.md` (programa **cerrado**)
6. `echoai/docs/STATUS.md` — números
7. `echoai/docs/CHATGPT_REVIEW.md`
8. `echoai/README.md` + `echoai/WATCH.md`
9. Código: `loop.py` (`_attend`, `_ask`, `_propose`), `cortex.py`, `oracle.py`, `corridor.py`, `attend.py`, `escalate.py`

Briefings para humanos/otros modelos (no son spec de código):

- `echoai/docs/ECHOAI_FOR_GEMINI.md`  
- `echoai/docs/ECHOAI_FOR_CHATGPT_RESEARCHER.md` (lo que se le subió a ChatGPT; un solo markdown)

MVP: `PYTHONPATH=. python3 -m echoai.nexus0.demo --short`

---

## 10. Invariantes que ganan a cualquier idea brillante

I3 0 FPU en el **rápido** (el córtex puede ser float).  
I11 banco principal cortex_calls=0.  
I14 hipótesis nunca has_fact=1.  
I15 CAM ≠ Q.  
I16 δ no en E[V].  
I17 un solo cable.  
I8 Akida ausente se niega.  
I12 echoAI no entra en ISO 2.1 por este plan.

VERIFY = Hamming≤3 ∧ extracto.  
Oráculo: prosa/JSON/hex WSP → accept None.  
Córtex: prosa → parse_reply None.  
El string `YO → PREGUNTAR → DESCONOCIDO @AHORA` pasa parse_reply y **falla** accept.

---

## 11. Cómo escribirle a Claude (cuando toque)

- Un slice. Un KPI.  
- Lista de lo **cerrado** que no se toca.  
- Candados por valor, no por desigualdad, cuando ya están medidos.  
- Informe opt-in = fichero propio.  
- Tests que fallen si el mérito es teatro (monkeypatch, source=, strictly_better, etc.).  
- “Si X dímelo claro / el slice no está verde.”  
- No IG_q float, no CortexROI del stub, no alargar BENCH_TURNS, no kernel/ISO.

Estilo de los prompts que funcionaron: español, contrato, anti-teatro, números.

---

## 12. Lo que Roger quiere del copiloto

Optimismo con los pies en el suelo. No vender AGI. Conservar el juguete que ya se ve pensar. El pulpo nace sin LLM. El 4B es neocórtex desenchufable, no el animal.

Pegar `NOW.md` + `CHATGPT_CODEX.md` + `ROADMAP.md`. Un KPI por tajo.

Fin. (Grok, 2026-09-04 — nos vemos la semana que viene.)
