# CLAUDE — GUI-3 (pegar tal cual)

ROOM-1 está **verde**. No lo reabras. No toques `room1.py`,
`self1.py`, `body3d.experiment` / `green()`, ni los JSON de
pulpo / self1 / room1. No retunees R/α/γ. No 4ª acción, no
WebSocket, no npm, no CDN, no Three.js, no Qt. No descargues
un LLM. No toques kernel, ISO, `parse_reply`, `qtable.py`,
`encoder.py`, `constants.py`, `graph.py`, `sign.py`,
`plan.py` default 0, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/board.py` (GUI-1/2),
`echoai/nexus0/thought.py` (`KEYS` = 17), `echoai/nexus0/loop.py`
(`thought.build` al final de `turn`), `echoai/nexus0/body3d.py`
(`Body3DEnv.cell`), `echoai/docs/FOR_FRIENDS.md` § GUI-3.

Eres implementador. Un slice. Un KPI. Córtex **apagado** en
el cubo. Este tajo es para **ver** al animal, no para
enseñarle nada nuevo.

---

## Qué está demostrado (no lo reabras)

```
GUI-1   file:// board.html, 8 bloques, replay embebido
GUI-2   --follow  127.0.0.1:8765  poll /turns.json  200 ms
KEYS    17, exactas; un log viejo de 12 se rellena
anillo  el tablero pinta `cell` 0..31, no un cubo
body3d  anda, pero thought.jsonl no lleva (x,y,z,h)
```

`board.py` **no** importa `loop`, `qtable`, `world`, `attend`.
Eso se queda.

---

## El KPI

Un log del cubo, el mismo `thought.jsonl` de siempre, abre
la placa **y** un cubo 3×3×3. El bicho se ve andando. Los
ocho bloques siguen leyendo la misma línea.

```
python3 -m echoai.nexus0.body3d --thought
# escribe echoai/lab/thought_body3d.jsonl  (nombre libre, documenta)
# no pisa lab/thought.jsonl del anillo si ese fichero existe

python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl
# file:// : cubo a un lado, placa al otro

python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl --follow
# vivo, el voxel se mueve al append, sin recargar a mano
```

Log del **anillo** (GUI-1/2): el cubo **no** se inventa.
`x` es null → no hay acuario, la placa de 32 celdas sigue.
Sin `--follow`, sigue siendo un HTML autónomo, cero red.

Runner de este tajo: lo que escriba el cubo con `--thought`
tiene al menos un turno con `x,y,z` enteros, y `board` de
ese fichero contiene un elemento del cubo (27 voxeles o 3
plantas 3×3) con el agente en la pose del turno.

---

## Qué construyes

### 1. El diario lleva la pose, o lleva null

`thought.KEYS` se **amplía**. Los tests que clavan 17 se
actualizan: las 17 primeras **siguen en el mismo orden**;
al final, y en este orden:

```
x, y, z, heading, frame
```

Enteros o `null`. Nunca prosa. `thought.build(..., x=None, ...)`.
Un log de 12 u 17 claves se rellena a null, como ya se
rellenaban `n/s/delta`.

El anillo escribe las cinco a `null` (el `set(rec)` sigue
igualando a `KEYS`, si no rompes TestGui1). El cubo escribe
números.

`loop.turn` lee la pose del `cell` **si existe**:

```
x = getattr(cell, "x", None)     # igual y, z, heading
frame = getattr(env, "frame", None)
```

Cero imports de `body3d` en `loop.py`. El anillo no tiene
esos atributos → null.

### 2. `Body3DEnv.cell()` rellena x,y,z,heading

`Cell` gana campos opcionales default `None`. El cubo los
pone. `Room1Env` hereda: `frame` ya vive en el env.

No hace falta pintar las paredes en el log. El cubo de la
placa es 3 plantas 3×3. Visitados = poses que el jsonl ya
trajo. Actual = turno. GOAL cuando `kind==GOAL`. Piedra =
hueco oscuro nunca visitado. Eso basta para ver el pasillo
aparecer. **Prohibido** que `board.py` importe `body3d` para
saber dónde está la piedra.

### 3. La placa: acuario + electrocardiograma

En `board.py`, stdlib, CSS/JS inline como ahora:

- Ancho: cubo a la izquierda (3 rebanadas z=0,1,2, cada una
  3×3), bloques CAM/WSP/T/Q/GATE/ATTEND/CORTEX/ORACLE a la
  derecha. Estrecho: se apilan. Sin framework.
- Heading: una flecha o letra `+X/+Y/+Z/-X/-Y/-Z` en el
  voxel actual, leída del log, no calculada.
- `frame` se escribe si no es null (ROOM-1). No hace falta
  un segundo cubo.
- `--follow` no cambia de protocolo. El poll ya existe; el
  JS coloca el voxel al pintar el turno nuevo.

### 4. `--thought` en el cubo

`body3d` (flag `--thought`) corre el examen open greedy de
siempre con `Agent(..., thought_log=..., remainder=True,
explore_flat=True)` **después** del tren, o un walk corto
desde START. Documenta la ruta del jsonl. No pises
`nexus0_pulpo_report.json`. No pises `thought.jsonl` del
anillo si está.

---

## Tests (`TestGui3`)

1. `thought.KEYS` tiene las 17 de siempre **más** las 5, en
   ese orden. `build()` sin pose → las 5 son `None`.
2. `run(thought_log=...)` del **anillo**: las 5 son `None`.
   `policy_after [-12,+5,0]`.
3. Un Agent en `Body3DEnv` con thought_log: una línea tiene
   `x,y,z,heading` enteros, `frame` null o int.
4. `board` de un log de cubo: el HTML contiene 27 voxeles
   (o 9×3 celdas) y la pose del turno 0 coincide con la
   línea 0. Sin importar `loop`/`qtable`/`body3d` en
   `board.py`.
5. Log de anillo: el HTML **no** exige cubo; la tira de 32
   (o `cell_count`) sigue.
6. `--follow`: jsonl de cubo con 2 turnos, GET, append 3ª
   con otra pose, GET, la 3ª pose está. Mismo truco que
   GUI-2.
7. Sin `--follow`, cero red. Logs viejos de 12 claves no
   crashean.
8. Pulpo / self1 / room1 reports byte-idénticos tras el
   runner de body3d `--thought`.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d           # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.body3d --thought
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl
PYTHONPATH=. python3 -m echoai.nexus0.self1            # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.room1            # rc=0
```

Si el cubo se pinta con una tabla de paredes copiada en
JS: **rojo**. Si KEYS pasa a prosa / `events[]`: **rojo**.
Si el anillo deja de escribir 32 celdas: **rojo**. Si
`--follow` abre un WebSocket: **rojo**. Si body3d `--thought`
pisa el informe del pulpo: **rojo**.
