# CLAUDE — GUI-3.5 (pegar tal cual)

GUI-3 está **verde** y se ve mal para un humano: tres plantas 2D,
la tira de 105 celdas, el diario escondido en bloques, y Play
que se acaba a los 64 turnos. Eso no se maquilla: se sustituye
la *vista*. No se reabre el animal.

No toques `room1.py`, `self1.py`, `body3d.experiment` / `green()`,
ni los JSON de pulpo / self1 / room1. No retunees R/α/γ. No 4ª
acción. **Sigue prohibido:** npm, CDN, Three.js, Babylon, Qt,
WebSocket, segundo bus. No descargues un LLM. No toques kernel,
ISO, `parse_reply`, `qtable.py`, `encoder.py`, `constants.py`,
`graph.py`, `sign.py`, `plan.py` default 0, ni
`lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/board.py` (CUBE_CSS, CUBE_JS,
`--follow`), `echoai/nexus0/body3d.py` (`thought_walk`,
`--thought`), `echoai/nexus0/thought.py` (KEYS 22).

Eres implementador. Un slice. Tres cosas a la vez, un runner.
Córtex **apagado**. El bicho no aprende nada nuevo: **se le ve**.

---

## Qué está demostrado (no lo reabras)

```
KEYS 22     x,y,z,heading,frame  (null en el anillo)
--thought   64 turnos greedy tras la escuela, thought_body3d.jsonl
board       3 rebanadas z=0,1,2  +  tira cell_count=105
--follow    poll 200 ms, Play se PARA en el último turno
```

`board.py` no importa `loop` / `qtable` / `world` / `attend` /
`body3d`. Eso se queda. Las paredes siguen sin estar en el log:
un voxel no pisado es aire, no un ladrillo inventado.

---

## El KPI (los tres, o rojo)

1. **Voxel 3D de verdad.** Perspectiva, se orbita con el ratón
   (arrastrar), no tres plantas 2D como vista principal. 27
   cubos CSS `preserve-3d` (seis caras cada uno) o un `<canvas>`
   WebGL **vanilla en el HTML**. Cero `three`, cero `importmap`,
   cero URL de red en el HTML.
2. **Diario de pensamiento.** Un panel `#thought` que lista el
   turno actual y los anteriores, con lo que el log ya trae:
   `turn  pose  action  wsp  T  Q  r  δ  s`. Se scrollea. En
   vivo, se pega al final. **Prohibido** prosa inventada
   (“giré porque la pared”).
3. **No se acaba.** `body3d --live` escolariza una vez y luego
   **no sale**: greedy, mismo Agent, GOAL devuelve a START,
   cada turno se appende al jsonl. Ctrl-C para. El tablero
   `--follow` se queda en la cola; Play en un replay finito
   **repite** (al último turno vuelve a 0), no se muere.

```
PYTHONPATH=. python3 -m echoai.nexus0.body3d --live
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl --follow
# http://127.0.0.1:8765/  — cubo orbitabile, log que crece, el bicho no para
```

`--thought` (64 turnos, rc=0) **sigue existiendo** para tests.
`--live` es el que se mira.

---

## Qué construyes

### 1. El escenario voxel (sustituye las tres plantas)

Quita `.slice` / `.voxrow` como vista principal. En su lugar,
un escenario:

```
#stage3d   perspective: 600px;  el usuario arrastra → rotateX/Y
#world     transform-style: preserve-3d
  27 × .cell3d   translate3d((x-1)*S, (1-y)*S, (z-1)*S)
    6 caras por voxel ocupado
```

- No pisado → no se dibuja (aire / pared, igual que ahora).
- Pisado → cubo opaco.
- Aquí → cubo caliente + marca de heading (una cara más
  brillante o una púa; el rumbo sale de `heading` del log).
- GOAL → borde verde cuando `kind==GOAL`.
- Rueda del ratón: zoom (scale). Botón “reset view”.
- Las tres plantas 2D, si quedan, son un minimapa **opcional**
  y pequeño. El KPI se juega en el escenario 3D.

Test: el HTML del cubo contiene `preserve-3d` o un `<canvas>`;
**no** es suficiente con tres `.slice` solas. `board.py` sigue
sin `FLOOR`, `BLOCKED`, `pose_of`, `body3d`.

Anillo: sin pose, **no** hay escenario 3D (el mutante
“inventa un cubo” sigue rojo).

### 2. El pensamiento, de verdad

Panel a la derecha del cubo (o debajo en estrecho):

```
#thought  max-height ~ 280px; overflow: auto; font 11px
una línea por turno, construida SOLO con claves del log:

  12  (0,2,0,+Y)  approach  YO → UNIR → AQUI  T=40  Q[3,-1,0]  r=0  δ=1  s=0
```

`wsp` ya es la frase compacta. Action es 0/1/2 → approach /
avoid / wait, leyenda local como ahora. Si `s=1`, la línea
se marca (predijo mal). Si `reward==16`, se marca cobro.

En `--follow`, si el usuario no ha hecho scroll hacia arriba,
el panel sigue la cola. Si scrubea el slider, el resalte va
a ese turno (el historial no se borra).

Cero claves nuevas en `thought.KEYS` si puedes. Si hace falta
una, tiene que ser entero o null, y el anillo la escribe null.

### 3. Vida que no termina

`body3d --live`:

- Misma escuela que `--thought` (curriculum, remainder,
  explore_flat, córtex off).
- Abre (o crea) `lab/thought_body3d.jsonl`. **No** lo borres
  al arrancar si quieres un diario continuo; para tests,
  empiézalo vacío en un tmp.
- Bucle: `ag.turn(..., greedy=True)` para siempre.
  GOAL ya teleporta a START: el pasillo se recorre una y
  otra vez. Eso es el “infinito”: tiempo, no espacio.
- Cada ~N turnos `flush`. Ctrl-C rc=0.
- No reescribe `nexus0_pulpo_report.json`.

El tablero en `--follow`:

- Abre en la cola (como GUI-2).
- **No** pares el timer de Play al llegar al último si
  siguen llegando líneas; las nuevas tiran de `i` al final
  si el usuario estaba al final (`wasEnd` ya existe).
- Replay **estático** (`file://`, sin live): Play al acabar
  vuelve a 0 y sigue. Un checkbox “loop” default on.

La tira de 105 celdas: **ocúltala** cuando hay cubo. Es el
índice 1D y miente a la vista. El anillo la conserva.

---

## Tests (`TestGui35`)

1. HTML de un log de cubo: hay escenario 3D (`preserve-3d`
   o `<canvas>`), hay `#thought`, hay al menos una línea de
   pensamiento que contiene un `wsp` del log. Las tres
   plantas no son el único cubo.
2. HTML de un log de anillo: **cero** `.cell3d` / canvas de
   voxel. Tira de 32 sigue.
3. `#thought` no contiene frases tipo “porque la pared” /
   “decidí girar”. Solo campos del rec.
4. `--thought` sigue rc=0, 64 líneas, no pisa el informe
   pulpo (bytes+mtime, como GUI-3).
5. `--live`: arranca en un hilo, espera a que el jsonl
   crezca **más** de 64 líneas, mata, rc del kill no importa
   (SIGTERM). El tablero `--follow` GET `from=` ve una línea
   nueva con `x,y,z` enteros.
6. Replay estático: el JS de Play, al final, no hace solo
   `stop()`; hay loop (lee el fuente de `board.py` / el HTML
   generado y busca que al último turno se vuelva a 0, o un
   flag `loop`).
7. `board.py` no importa body3d/loop/qtable; no hay
   `three` / `cdn` / `unpkg` / `jsdelivr` en el HTML.
8. Anillo `[-12,+5,0]` +80. KEYS: si no las tocas, 22.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d              # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.body3d --thought    # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1
PYTHONPATH=. python3 -m echoai.nexus0.room1
# a mano, para verlo:
PYTHONPATH=. python3 -m echoai.nexus0.body3d --live
PYTHONPATH=. python3 -m echoai.nexus0.board echoai/lab/thought_body3d.jsonl --follow
```

Si el “3D” son otra vez tres plantas con CSS `rotate` de
adorno y no se puede orbitar: **rojo**. Si el pensamiento
es un párrafo generado: **rojo**. Si `--live` para a los
64: **rojo**. Si Three.js por CDN: **rojo**. Si el cubo se
inventa para el anillo: **rojo**.
