# CLAUDE — OPEN-1 (pegar tal cual)

OBJ-1b está **verde**. No lo reabras. No toques `obj1.py` (salvo
importar), `ITEM_XYZ` / `DEST_XYZ` de obj1, `body3d.experiment` /
`green()`, `self1.py`, `room1.py`, `board.py`, `thought.KEYS` (22),
ni los JSON de pulpo / self1 / room1 / obj1. No retunees R/α/γ.
No MiniGrid-8. No `carrying` en `ext`. No descargues un LLM. No
toques kernel, ISO, `parse_reply`, `constants.N_ACTIONS` (**sigue
3**), `graph.py`, `sign.py`, `plan.py` default 0, ni
`lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/obj1.py` (vaso, acoplar, mesa),
`echoai/nexus0/qtable.py` (`select` / `is_explore` / `% N_ACTIONS`),
`echoai/nexus0/gate.py` (`proposed % 3`), `echoai/nexus0/loop.py`
(`_propose`, `turn`), `echoai/docs/CHATGPT_ECHO1_VERDICT.md` § ABRIR.

Eres implementador. Un slice. Un KPI. Córtex **apagado**.
Verbo nuevo **⇔** física nueva. Sin tapa, no hay `ABRIR`.

---

## Qué está demostrado (no lo reabras)

```
obj-1     ITEM (0,1,0) DEST (1,0,0)  collect 10  alone 1
          exam 51/51 object_at_Y · control 0 y no toca el vaso
          mutant 256 cobros / 0 vasos · Q 65 vs 0 (fuera de green)
pulpo     open 64 / block 42 / desvío 11=horizonte
anillo    [-12,+5,0] +80  33/1/217  remainder off  explore_flat off
          Q[4096][3]  N_ACTIONS=3  KEYS 22
techo     encode_cell(0)==encode_cell(256)
```

El mundo tiene un vaso. Todavía no tiene una **herramienta**.
`ABRIR` ya existe como átomo (25). No existe como marcha.

---

## El KPI

Un frasco con tapa. Hasta que no se abre, el vaso no se coge.
`ABRIR` es la 4ª acción **solo** en este mundo, por flag.
El anillo sigue en 3.

```
examen greedy START canónico, frasco cerrado, córtex 0
  object_hits     > 0          # el vaso llega a la mesa
  used_open       > 0          # ABRIR se ejecutó sobre el cerrado
  shortest_collect ≤ 11        # 10 de OBJ-1 + 1 ABRIR, inundado
control  Q de 3 columnas, mismo frasco cerrado: object_hits == 0
mutante  frasco ya abierto, 3 columnas: object_hits > 0
         (sin tapa el verbo no hacía falta: es OBJ-1 otra vez)
anillo   Agent().q.row(0) tiene longitud 3
         policy_after [-12,+5,0]  +80  33/1/217
acciones del default 3 · false_facts 0 · cortex_calls 0
```

`green()` exige eso + techo 256 + obj1 no se tocó.

---

## Qué construyes

Archivo **nuevo** `echoai/nexus0/open1.py`. No hinchas `obj1.py`.
Reusa `Obj1Env`, `ITEM_XYZ`, `DEST_XYZ`. Informe:
`lab/nexus0_open1_report.json`. Nunca pisa obj1 / pulpo / anillo.

### Física (frasco, no puerta)

El ítem de OBJ-1 nace **cerrado**.

```
env.lid_open = False          # reset: cerrado, vaso en ITEM, no acoplado
```

- Cerrado: aterrizar en el ítem **no** acopla. Puedes estar encima
  con las manos vacías. Ese estado no existía en OBJ-1 y aquí es
  el que pide el verbo.
- `ABRIR` (acción 3) **sobre el voxel del ítem cerrado**:
  `lid_open = True`. Si el cuerpo está ahí, ahora es un vaso
  abierto → acopla (estar sobre el abierto = llevarlo), igual
  que OBJ-1.
- `ABRIR` en cualquier otro sitio: no-op, r=0. No abre a
  distancia. No paga.
- Abierto: la física de OBJ-1, tal cual. Entregar cobra
  `object_at_Y` y resetea **también** `lid_open = False`.
- `avoid` no suelta. No hay 5ª marcha CERRAR.

Geometría: **las constantes de obj1**. No muevas la mesa otra
vez. Collect inundado = 11 (los 10 + el ABRIR encima del vaso).
11 es el horizonte: cabe, no sobra. Si alargáis el frasco, Q
no ve el premio.

### Lo que ve el rápido

Paquete distinto para el cerrado, si no Q no puede aprender
`ABRIR` ahí:

```
KIND_CLOSED = 5
KIND_NAME gana "CLOSED"
CELL_ATOMS[KIND_CLOSED] = (OBSERVAR, CERRAR)   # percepción, no verbo
```

`YO → OBSERVAR → CERRAR`. No `ABRIR` en el rel del paquete
(eso es la marcha). E idéntica a EMPTY, no a GOAL. `seq` sigue
`index & 0xFF`. Domain 0, style 0.

Cerrado: las seis headings del ítem pintan `KIND_CLOSED`.
Abierto y acoplado: `KIND_OBJECT`, como OBJ-1.
Mesa: sigue sin ser `KIND_GOAL`.

`thought.KEYS` **22**. `ACTION_NAME` puede ganar `"open"` para
no IndexError si un log ve action=3. No es una clave nueva.

### La 4ª columna (flag, como remainder)

`constants.N_ACTIONS` **no se toca**. Es 3. El anillo vive de eso.

```
QTable(..., n_actions=None)     # default N_ACTIONS
Agent(..., n_actions=None)      # default 3; open1 pide 4
```

Arrays de Q / rem / z: ancho `n_actions`. `get`/`set`/`update`
módulos a **ese** ancho, no a `N_ACTIONS`.

Tres minas, las tres convierten ABRIR en approach y el tajo
es teatro:

1. `qtable.select`: `return int(turn) % N_ACTIONS` → `% self.n_actions`.
   Con explore_flat y ancho 3, ABRIR **nunca** se prueba en fila
   plana. Es el huevo y la gallina.
2. `qtable.is_explore`: `row[0]==row[1]==row[2]` vale mientras el
   ancho sea 3. Con 4, el empate es las **cuatro**. Default 3:
   el bytecode del anillo es el de siempre.
3. `gate.py`: `a = int(proposed) % 3`. ABRIR (3) entra y sale
   APPROACH (0). El env nunca ve el verbo. Ancho por argumento,
   default 3. Las reglas de amenaza no cambian. ABRIR no es
   amenaza; `GATE_OK` lo deja pasar.
4. `loop._propose` / `turn`: `% N_ACTIONS` en la acción que se
   da al env tiene que ser el ancho de **ese** Agent. El banco
   default sigue siendo 3, byte a byte.

`explore_flat` on y remainder on en open1, como obj1. Default
del Agent: off, ancho 3.

UNIR **sigue** siendo approach. ABRIR no reusa UNIR.

### Escuela

Curriculum de obj1 (holding / soltero) **más** una etapa
cerrada: teleport encima del frasco cerrado, `lid_open=False`,
para que ABRIR se vea. Sin nombrar el camino. Examen greedy,
START canónico, frasco cerrado, ítem en ITEM, n_actions=4.

Control, corrido: **el mismo** env con tapa, Agent n_actions=3.
No puede abrir. `object_hits == 0`. No bajes el START.

Mutante, corrido: `lid_open=True` al nacer (no hay tapa).
Agent n_actions=3. Cobra. Si este también cobra 0, el verbo
no era la puerta.

---

## Lo que no es

- `N_ACTIONS = 4` en `constants.py`.
- Q[4096][4] en `Agent()`.
- `ABRIR` que abre el frasco desde START (a distancia).
- Pintar el cerrado `KIND_GOAL` / `KIND_NOVEL`.
- Puerta que cambia `NEXT` del pulpo (eso sería otro tajo).
- 8 acciones, PICK, CERRAR, palo, MiniGrid.
- Córtex eligiendo ABRIR. SIGN-C no es este tajo.
- Retunear γ porque 11 aprieta. Si no cabe, **parar**.
- Reabrir OBJ-1 / PULPO.

---

## Informe (`lab/nexus0_open1_report.json`)

```
item dest                          los de obj1
actions_default                    3
actions_this_world                 4
lid_starts_closed                  true
shortest_collect                   ≤ 11     # 11 medido
exam_object_hits                   > 0
exam_used_open                     > 0
exam_collections_are_object_at_Y   true
exam_start_is_canonical            true
control_n_actions                  3
control_object_hits                0
control_went_to_the_jar            true     # llegó; no pudo abrir
mutant_already_open_object_hits    > 0
mutant_already_open_used_open      0        # no hacía falta
probe_closed_approach_does_not_couple
probe_open_on_jar_couples
probe_open_elsewhere_is_noop
domain_is_zero style_is_zero packet_ceiling_holds
false_facts destroyed cortex_calls questions
green
```

Control y mutante se ejecutan de verdad.

---

## Tests (`TestOpen1`)

Sin GGUF.

1. `Agent().q.row(0)` longitud 3. `N_ACTIONS==3`.
   `Open1Env` n_actions 4. Remainder / explore_flat default False.
2. Cerrado: teleport al ítem, `coupled==False`, kind `CLOSED`,
   `approach` no acopla. `ABRIR` ahí: `lid_open`, `coupled`,
   kind `OBJECT`. `ABRIR` en START: no-op, el frasco sigue
   cerrado.
3. `encode_cell(p, CLOSED) != encode_cell(p, OBJECT) !=
   encode_cell(p, EMPTY)`, 16 B, domain 0, style 0, seq=p.
   `encode_cell(0)==encode_cell(256)` sigue.
4. `exam_object_hits > 0`, `exam_used_open > 0`, collect ≤ 11,
   START canónico, cada cobro es `object_at_Y`.
5. Control 3 columnas: `object_hits==0` y estuvo en el ítem.
6. Mutante ya abierto: 3 columnas, `object_hits>0`,
   `used_open==0`.
7. Fuente de `open1.py`: no `N_ACTIONS = 4`, no `carrying`, no
   `WSP_DOM`, no `minigrid`, no `KIND_GOAL` en `_payoff`.
   Grep de **formas de uso**. `ACTION_OPEN` / `ABRIR` como
   marcha **sí** pueden aparecer: este tajo es ese verbo.
8. Anillo `[-12,+5,0]` +80. `obj1.green` sigue. Informes pulpo /
   self1 / room1 / obj1 byte-idénticos tras el runner.
   `thought.KEYS` 22.
9. Mutante de código corrido: si `gate` sigue haciendo `% 3`,
   un `proposed=3` sale 0 — el test llama a `gate` con ancho 4
   y exige que 3 sobreviva. Con ancho default 3, `proposed=5`
   sigue saliendo `2` como hoy (`5%3==2`).
10. `body3d` / `self1` / `room1` / `obj1` rc=0. DEST del pulpo
    sigue `KIND_GOAL`.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d
PYTHONPATH=. python3 -m echoai.nexus0.obj1      # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.open1     # rc=0 solo si green()
```

Si cobra porque el frasco nace abierto: **rojo**. Si cobra
porque `gate` convirtió ABRIR en approach y aterrizar acopla:
**rojo** (eso es OBJ-1). Si `Agent().q` tiene 4 columnas:
**rojo**. Si para que quepa subiste γ: **rojo**. No piques
SIGN-C en el mismo tajo.
