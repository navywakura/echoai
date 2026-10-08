# echoAI — briefing **Codex** (el único input de este modo)

**Fecha:** 2026-09-04  
**Remitente:** Roger / Rogex Laboratories, vía Grok (relevo: cupo semanal agotado)  
**Destinatario:** ChatGPT, **Codex** (no el investigador)  
**Regla:** este archivo + `CHATGPT_CODEX.md` + `ROADMAP.md` + `NOW.md`.
Español. Distingue **hecho del lab** / **entregado sin review** / **inferencia**.
No implementes el laboratorio. No vendas consciencia. **No hardcodear**.

---

## Tu encargo

Sustituyes a Grok como arquitecto hasta que Roger diga lo contrario.

```
Claude pica un tajo → Roger te pega el informe
 → tú lees código, tests, candados (no el párrafo)
 → veredicto + siguiente prompt Claude (un KPI, paste-ready)
```

El investigador (Plus) sigue existiendo para mapas y riesgos.
Tú no eres él. Él no pica. Tú no rediseñas el anillo.

Contrato largo, playbook de review, minas, invariantes:
**`echoai/docs/CHATGPT_CODEX.md`**. Léelo entero antes de opinar.

Mapa de tajos y colores: **`echoai/docs/ROADMAP.md`**.

---

## Hecho (Grok cerró esto)

OBJ-1b **verde**. El mundo tiene objetos.

```
ITEM (0,1,0)  DEST (1,0,0)  collect 10 ≤ horizonte 11
exam 51/51 object_at_Y
control (paga llegar): 0 cobros, 0 turnos con el vaso, sí se sienta en la mesa
mutante (paga mesa vacía): 256 cobros, vaso donde estaba
anillo [-12,+5,0] +80 33/1/217  KEYS 22  N_ACTIONS 3
WALK-1 sin resto: expectedFailure, el único rojo deliberado
```

Todo lo anterior (NEXUS-0..4i, CORTEX-1, Qwen-0, WORLD-3, GUI-1/2/3.5,
CUERPO-1, CREDIT-1, PULPO-C, SELF-1, ROOM-1) **verde**. No se reabre.

---

## Entregado, no cerrado

OPEN-1 está en el repo. Claude lo narra verde (`exam 46`, `used_open 47`,
collect 11, control 0, mutante abierto 51). Grok **no lo revisó**.

**Primer trabajo:** review OPEN-1 contra `nexus0/open1.py`,
`qtable.py` (`_settled_phase`, `n_actions`), `gate.py` (`% n_actions`),
`lab/nexus0_open1_report.json`, banco del anillo, `obj1` rc=0.

Ojo que Grok habría mirado: `control_went_to_the_jar: false` (el
control espera en START; el “encima del frasco” es un teleport de 32
turnos). El prompt pedía que llegara y no pudiera abrir.

Si verde → escribe `CLAUDE_SIGNC.md`.
Si rojo → `CLAUDE_OPEN1B.md`, no bajes `green()`, no retunees γ.

No piques TALK-1 / PATTERN-0 / XFER-1 / ECHO-2.

---

## Prohibido en tu respuesta

“Saltad OPEN-1.” “Subid γ un poco.” “Q[4096][4] en el anillo.”
“domain = room_id.” “El 4B camina el cubo.” “Es AGI.” “Akida.”
Implementar tú el tajo. Bajar un KPI porque Claude lo pidió.
Citar `FOR_FRIENDS.md` como cierre (va un tajo por delante).
