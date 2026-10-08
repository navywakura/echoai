# CLAUDE — programa situado (post-ChatGPT 2026-09)

Léete esto **después** de `echoai/CLAUDE.md` y `echoai/docs/STATUS.md`.
Eres implementador. No rediseñes el anillo. No LLM. No Akida. No kernel.
No envuelvas `navi10_engine.think`.

También lee, como contexto de investigación (no como spec de código):
`echoai/docs/ECHOAI_FOR_CHATGPT.md` si está en `docs/`,
`echoai/docs/CHATGPT_REVIEW.md`, `echoai/docs/STATUS.md`.

La tesis que ChatGPT firmó y el laboratorio acepta:

> EchoAI **no** se investiga como “SNN + LLM”. Se investiga como
> arquitectura de aprendizaje **situada**: WSP/QN espacio discreto
> compartido, CAM memoria, T dinámica, Q política, ATTEND cuándo gastar
> cómputo cortical, córtex hipótesis que deben sobrevivir al basal.

Resultados que **sí** se citan: JUMP (T ≠ i±1), preguntar +80/−80,
ATTEND 36/256 (“no pensar siempre”).  
Resultado que **no** se cita como world model: T=0.9964 en el anillo liso.

Prueba que perseguimos a medio plazo (no este slice):

> El agente cambia de comportamiento cuando su modelo del mundo estaba
> mal, en un mundo que no sea solo 32 celdas, sin dejar de preguntar,
> sin planificar de más, sin córtex si lo barato basta.

---

## Ya está — no lo reinventes

| Pieza | Dónde |
|---|---|
| T(s,a)→s' + `n` + `conflicts` | `world.py` |
| Surprise `d_H(ŝ',s')` | `loop.py` |
| Novelty / NOVEL | CAM + `KIND_NOVEL` |
| δ | `qtable.update` |
| PREGUNTAR ≠ 4ª marcha | `_ask()`, no `env.step` |
| Córtex no predice s' | stub; T predice |
| `parse_reply` tira prosa | `cortex.py` |
| `cortex_calls=0` default | invariante |
| Planner módulo | `plan.py`; default `plan_depth=0` |
| Escalada 0 vs 2 | `escalate.py`; default off. `search_strictly_better=0` |
| N ≠ S ≠ δ | `Metrics`: cam_misses / surprises / deltas. `surprise_known=1` |
| Oráculo fuera | `oracle.py`; `RingEnv.ask()` no existe; `source=sensor\|file` |
| thought.jsonl ≈ e_t | no hace falta un struct nuevo el primer slice |

El planner **se queda como módulo** (sirve en c9 y en 8→11). Lo que
murió es **planner siempre on**. ΔQ lo midió: en este anillo nivel 2
copia a Q (`search_strictly_better=0`). No lo reabras. No lo borres.

IG(question): **no** inventes un float. +80 vs −80 ya es la ganancia.
CortexROI: **no** lo midas mientras el stub sea el mismo PREGUNTAR
que el rápido. ROI≈0 sería teatro.

Sleep, umbrales 1/100/1000, LLM, Akida: **no ahora**.

---

## Orden de laboratorio (un KPI por slice)

**Programa cerrado.** No abras un slice nuevo aquí.

1. **T_CONF ∈ {0,1,2,3}** — cerrado.
2. **Inverso I(s,s')→a** — cerrado.
3. **Escalada 0–4 + ΔQ** — cerrado. Nivel 2 copia a Q en este anillo.
4. **Informe N / S / δ** — cerrado. `surprise_known=1` (fase F, cell 5).
5. **Oráculo fuera** — cerrado. `RingEnv.ask()` no existe. +80 se mantiene.
6. **Otro pasillo** — cerrado. Transferido conoce B al entrar; control no.

Candados que ningún slice mueve en el bench **sin flags**:

```
policy_after [-12, +5, 0]
false_facts 0  destroyed 0  cortex_calls 0
encoder_beats_fnv  t_beats_ring
novel_approach_return +80
```

---

## Programa cerrado

El pasillo (NEXUS-4i) cerró la tesis que ChatGPT firmó. Empaquetado:
`python3 -m echoai.nexus0.demo`. Briefing de futuro: `docs/ECHOAI_FOR_GEMINI.md`.

**CORTEX-1 cerrado** (cable UNIR/TEMER → gate; stub, no 4B).
Siguiente: **GUI-1**, prompt `echoai/docs/CLAUDE_GUI1.md`.
Contrato largo: `echoai/docs/NEXT_APPROACH.md`.

---

## Archivo: el pasillo (ya implementado, no reabrir)

Último item del programa que ChatGPT firmó. No es NEXUS-7 abierto.
No es AGI. Es: el mismo agente, el mismo cable de 16 B, las mismas 3
acciones, **un mundo que no es el anillo de 32**, y T/Q del primero
frente a Q=0.

Fase F ya hizo “T mal, origen conocido” *dentro* del anillo. Este
slice exige un **segundo env**. Pintar la celda 2 de otra clase en
el anillo no cuenta.

```
HOME   A → B → C → D     D es GOAL. C es EMPTY.
SHIFT  A → B → X → D     X es THREAT. C ya no está en el camino.
```

A, B, D conservan índice y kind → mismo WSP → CAM/T/Q se arrastran.
C y X son celdas distintas (índices distintos), no un recubrimiento
de kind sobre el mismo sitio. Desde B, `approach` en HOME aterriza
en C; en SHIFT aterriza en X.

`corridor.py`: sucesor por tabla, no `(i+1)%n`. Cuatro o cinco
celdas, no 32. Sin NOVEL, sin JUMP, sin oráculo de trampa: el
punto es la geometría. `_ask()` puede quedarse; si no hay
KIND_NOVEL no dispara.

`Agent` admite `env=`. Default sigue siendo `RingEnv()`. El banco
de 352 turnos **no se toca**. Informe propio:
`lab/nexus0_corridor_report.json` (como escalate/oracle: nunca
sobrescribir `nexus0_report.json`).

Protocolo:

1. Entrenar en HOME (el Agent recorre el pasillo, no el anillo).
2. Sin reset de CAM/Q/T, poner `env` = SHIFT, `teleport(A)`.
3. Control: Agent fresco en SHIFT, Q=T=0.

### KPI

1. Al aterrizar en SHIFT, T(B, approach) **conoce** (predice C).
   El control no conoce. Eso es la transferencia.
2. El primer `approach` desde B en SHIFT: origen B mismo slot,
   `surprise_known` sube, N de B no. X sí es paquete nuevo (N del
   destino). Igual que fase F, en otro mundo.
3. KCC: una observación no voltea al titular. Tras suficientes
   X, T(B, approach) pasa a X o `alt_n>0`.
4. Política en B: HOME greedily `approach` (hacia GOAL vía C).
   Tras el golpe en X=THREAT, approach en B deja de ganar.
5. Arranque: el transferido tiene menos `cam_misses` en {A,B,D}
   que el control. Si no, no hay transferencia que publicar.
6. Default del anillo intacto: `policy_after [-12,5,0]`,
   `novel_approach_return +80`, `surprise_known 1`,
   `oracle_source sensor`, `RingEnv` sin `ask`.

### Qué no es este slice

- No CortexROI. No sleep. No LLM. No Akida. No ISO.
- No alargar el bench del anillo. No plan_depth=2 por defecto.
- No toques `plan.py`, `escalate.py`, `oracle.py` (salvo que Agent
  necesite `env=`), `parse_reply`, `view.py`, ATTEND, `conf()`.
- STATUS.md NEXUS-3 aún dice `env.ask()`: una línea, corrígela.

### Tests

- default anillo: candados + N/S/δ 33/1/217/1 + oracle_source sensor
- HOME: T(B,approach)=C, greedy en B es approach
- SHIFT fresco: T(B,approach) unknown
- transferido: T(B,approach) known (C) al entrar; primer approach
  desde B dispara surprise_known; slot de B no cambia
- transferido cam_misses en {A,B,D} < control
- `--cortex` 36/256, `gen_lex --check` in sync

STATUS.md: los dos números (conocido vs no; misses transfer vs
scratch) y una frase: esto no es AGI, es el pasillo que el anillo
no podía ser.
