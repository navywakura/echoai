# CLAUDE — GUI-1 (pegar tal cual)

CORTEX-1 está **verde**. No lo reabras. No descargues un LLM. No toques
`sign.py`, el cable `last_cortex_action`, `parse_reply`, `plan.py`,
kernel, ISO, ni los candados del anillo.

Lees: `echoai/CLAUDE.md`, `echoai/WATCH.md`, `echoai/nexus0/view.py`,
`echoai/nexus0/thought.py`, `echoai/docs/NEXT_APPROACH.md` § GUI.

Eres implementador. Un slice. Un KPI.

---

## Qué construyes

Una **placa**, no un cerebro 3D. Replay de `thought.jsonl`. Cada pieza
es un bloque que se enciende con el turno: CAM, WSP, T, Q, GATE,
ATTEND, CORTEX, ORACLE. Sólido = hecho. Gris = hipótesis. Rojo = reject.

El demo ANSI **se queda**. Este slice no lo sustituye. CI no necesita un
navegador.

`nexus0/` sigue stdlib. **Cero** imports nuevos en `loop.py` (no Qt, no
websocket, no segundo bus). La GUI **lee el jsonl**. No llama a Q, T,
ATTEND, CAM.

---

## El log (aquí sí se toca `thought.KEYS`)

Hoy `KEYS` es conjunto exacto de 12 campos. Faltan N, S, δ y si el
córtex **propuso** este turno — el visor no puede pintar lo que no está.

Añade **exactamente** estos campos, ni uno más:

```
n                 0|1   cam_miss de este turno (el n_fact que el loop ya calcula)
s                 0|1   surprise de este turno (s_fact)
delta             0|1   Q.update != 0
cortex_action     null | 0|1|2   propuesta consumida este turno, o null
gate_decision     0|1|2          GATE_OK / MODIFY / BLOCK
```

Tipos: enteros y `null`. Nada de prosa. Nada de `events[]` anidado (eso
se puede derivar en el visor). Actualiza `thought.build` **y** la
llamada en `loop.turn`. Actualiza el test `set(rec) == set(thought.KEYS)`.

Replay de un jsonl **viejo** (sin las claves nuevas): `view.py` y el
tablero no crashean; tratan ausente como 0 / null. Hay test de eso.

No cambies el significado de las 12 claves que ya existen.

---

## El tablero (`echoai/nexus0/board.py`)

```
PYTHONPATH=. python3 -m echoai.nexus0.bench --thought
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
# escribe echoai/lab/board.html  (un fichero, autocontenido)
```

- Un HTML **autocontenido**: CSS+JS embebidos. Cero CDN. Cero red.
- Stdlib para generarlo (`html`/`json`/`pathlib`). El JSON va **dentro**
  del HTML (array), para que `file://` funcione sin servidor.
- Controles: anterior / siguiente / play. Sin WebSocket. Sin `tail`.
- Cada bloque lista lo del turno, no una metáfora:
  - CAM: hit/miss (`n`)
  - WSP: el compact del registro
  - T: `t_pred` o “—”
  - Q: las 3 barras (enteros)
  - GATE: ok / modify / block
  - ATTEND: on/off + `reason_name`
  - CORTEX: `cortex_action` o gris; si `attend_on` y action null → despertó
    y no propuso (el eco del stub)
  - ORACLE: `questions` subió este turno o no
- El anillo de 32 (o el `cell` del registro) se pinta como en `view.py`:
  G/T/N/· y `@`. No hace falta entender SIGN para el banco default.
- Si el jsonl viene de `sign` (2 celdas), no asumas `N_CELLS=32`: usa
  `max(cell)+1` o el conjunto de celdas vistas. Test con un jsonl de SIGN.

**Prohibido:** PySide6, QML, Flask, FastAPI, matplotlib, pygame,
WebSocket, abrir el navegador desde el test.

`demo.py` no se convierte en GUI. WATCH.md gana una sección de tres
líneas: cómo abrir `lab/board.html`.

---

## KPI (todos a la vez)

```
false_facts = 0, destroyed = 0
banco default: cortex_calls=0, policy_after [-12,5,0], +80, surprise_known=1
anillo --cortex: 36/256, cortex_actions=0
CORTEX-1 sign: sigue verde (python3 -m echoai.nexus0.sign)
thought.KEYS = las 12 de antes + las 5 nuevas (17), conjunto exacto
board.html se genera y contiene tantos objetos como líneas del jsonl
view.py sigue pintando (test de render no crashea con claves nuevas)
jsonl viejo (solo 12 claves) no tira board ni view
0 imports de board/qt en loop.py
```

---

## Tests (`TestGui1` en `test_nexus0.py`)

1. `test_keys_are_exactly_seventeen` — `set(KEYS)` es el contrato.
2. `test_loop_writes_the_new_fields` — un turno con `--thought`; `n`∈{0,1},
   `cortex_action` null en el anillo default.
3. `test_sign_turn_records_cortex_action` — prize greedy + stub:
   `cortex_action == ACTION_APPROACH`.
4. `test_old_jsonl_does_not_crash_view` — un dict con solo las 12 claves
   antiguas entra en `view.render`.
5. `test_board_embeds_every_line` — genera HTML de un jsonl de 3 líneas;
   el HTML contiene 3 turnos; no contiene `http://` ni `cdn`.
6. `test_board_does_not_import_the_loop` — `board.py` como texto no
   importa `loop`, `qtable`, `world`, `attend`.
7. `test_ring_locks` — `run()` default, mismos candados.

No alargues `BENCH_TURNS`. No toques `SETTLED_HITS`. No PySide.

---

## Qué no tocas

`parse_reply`, `sign.py` (salvo si el jsonl de sign necesita las claves
nuevas: eso sale de `loop.turn`, no del env), `oracle.accept`, `plan.py`,
`escalate.py`, geometría del anillo, `attend.py` razones, `cortex.gbnf`,
descargar pesos, kernel, ISO.

---

## Verificación que me pegas

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.sign
PYTHONPATH=. python3 -m echoai.nexus0.bench --thought
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
```

Pega: nº de tests, candados del bench, `KEYS` final, tamaño de
`board.html`, archivos tocados.

Si para pintar N/S/δ hace falta un campo que no esté en la lista de 5,
dímelo claro: no inventes `events[]` por tu cuenta. El slice no está
verde si `loop.py` importa Qt o si el anillo se mueve.
)
