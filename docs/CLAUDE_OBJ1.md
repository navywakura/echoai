# CLAUDE — OBJ-1 (pegar tal cual)

GUI-3.5 está **verde**. No lo reabras. No toques `board.py`,
`thought.KEYS` (22), `body3d.experiment` / `green()`, `self1.py`,
`room1.py`, ni los JSON de pulpo / self1 / room1. No retunees R/α/γ.
No 4ª acción. No `ABRIR`. No bit `carrying` en `ext.style` / `domain`.
No pose compuesta `(agente × objeto)` en `seq`. No MiniGrid. No
descargues un LLM. No toques kernel, ISO, `parse_reply`, `qtable.py`,
`constants.py` (`N_ACTIONS` sigue 3), `graph.py`, `sign.py`,
`plan.py` default 0, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/body3d.py` (`Body3DEnv`, `NEXT`,
`GOAL_POSES`, `_payoff`, `_curriculum`), `echoai/nexus0/encoder.py`
(`encode_cell`, `CELL_ATOMS`, `seq = index & 0xFF`),
`echoai/nexus0/env.py` (`Cell`, `KIND_*`, `_reward`),
`echoai/docs/CHATGPT_ECHO1_VERDICT.md` § objeto X→Y.

Eres implementador. Un slice. Un KPI. Córtex **apagado**.
Este es el tajo de **ECHO-1** que enseña que el mundo tiene
cosas, no solo un yo. OPEN-1 (tapa / `ABRIR`) **no** es este tajo.

---

## Qué está demostrado (no lo reabras)

```
pulpo     open 64 / block 42 / desvío 11=horizonte / 162 poses
self-1    offset motor=1 world=0 / gap=1 / T 56>46
room-1    324 sitios / 162 paquetes / domain=0 / alias con agujero=2
gui-3.5   preserve-3d 27×6 / #thought / --live / KEYS 22
anillo    [-12,+5,0] +80  33/1/217  remainder off  explore_flat off
techo     encode_cell(0) == encode_cell(256)     se MIDE, no se agranda
```

El cubo cobra cuando **el cuerpo** llega a `(2,2,1)`. Eso ya está.
OBJ-1 cobra cuando **la cosa** llega. Sentarse en la mesa no paga.

---

## El KPI

Un ítem con pose. Tres acciones. `approach` al ítem **acopla**.
GOAL paga `object_at_Y`, no `agent_at_Y`.

```
examen greedy, START canónico (0,0,0,+X), ítem en X, córtex 0
  object_hits  > 0          # cobros = la cosa está en Y al approach
  agent_at_Y_without_object no cobra nunca
control (paga agent_at_Y, ignora el ítem): object_hits == 0
mutante corrido: si el env paga en Y vacío, el cuerpo deja el vaso
                 y ese número NO es el verde
acciones = 3
index del agente 0..161     # no 162×27
domain 0, style 0
false_facts 0  destroyed 0  cortex_calls 0  questions 0
```

`green()` exige eso + el techo 256 intacto + el anillo intacto.

---

## Qué construyes

Archivo **nuevo** `echoai/nexus0/obj1.py`. No hinches `body3d.py`.
Reutiliza el cubo **open** (suelo, `DIRS`, `bumps`, `is_floor`).
Informe: `lab/nexus0_obj1_report.json`. Nunca pisa pulpo / self1 /
room1 / anillo.

### Geometría (no la cambies)

Mismo cubo 3×3×3, layout `open`, mismo START.

```
ITEM_XYZ = (2, 0, 0)     # en el pasillo corto, no START, no DEST
DEST_XYZ = (2, 2, 1)     # la mesa: el voxel que en el pulpo era GOAL
```

Camino más corto, medido a mano, **8** acciones ≤ horizonte 11:

```
(0,0,0,+X) → → (2,0,0,+X) acopla
           avoid +Y → → (2,2,0,+Y)
           avoid +Z → (2,2,1,+Z)
           approach cobra
```

Si alargas el acarreo por encima de 11, Q no ve el premio: eso
ya se midió. No subas el cubo. No uses `block`.

### Física (llevar, no Sokoban)

El ítem es un voxel, sin heading.

```
env.obj      = (ox, oy, oz)     # default ITEM_XYZ
env.coupled  = (agent_xyz == obj)
```

- `approach` que **aterriza** en el voxel del ítem → `coupled = True`.
- Mientras `coupled`, `obj` sigue al agente (mismo voxel).
- No hay soltar. Se desacopla al cobrar o en `reset`.
- No se empuja a la celda de delante. No se queda atascado en un rincón.
- Piedra y borde: igual que el pulpo (`R_THREAT` al chocar).

Cobro, **antes** de mover, como el pulpo:

```
if approach and agent_xyz == DEST and obj == DEST:  # object_at_Y
    r = R_SUCCESS
    luego: agente → START, obj → ITEM_XYZ, coupled = False
else:
    r = bump ? R_THREAT : 0     # Y vacío no paga
```

`wait` / `avoid` en la mesa **no** cobran. Un GOAL que se pisa no
es una bomba; un vaso que se deja, tampoco.

### Lo que ve el rápido (sin bit carrying)

El agente solo observa el WSP de **su** celda. Si acoplado y
vacío-de-manos pintan el mismo paquete, Q promedia y el tajo es
teatro. Por eso el ítem es un `kind`, no un flag en `ext`:

```
KIND_OBJECT = 4
KIND_NAME   gana "OBJECT"
```

`cell()` pinta `KIND_OBJECT` en las seis headings del voxel donde
está el ítem **ahora**. El resto, `KIND_EMPTY`. **DEST no se pinta
`KIND_GOAL`**: eso es exactamente el mutante (el cuerpo llega y cobra).

`encode_cell` necesita una entrada nueva, si no `CELL_ATOMS.get`
cae a EMPTY y acoplar es invisible:

```
CELL_ATOMS[KIND_OBJECT] = (OBSERVAR, OTRO)    # percepción, no verbo
```

`YO → OBSERVAR → OTRO`. No `UNIR` (eso es approach). No `ABRIR`.
No `CONCIENCIA`. E del objeto **no** copia la de GOAL (`V=40,C=80`):
el vaso no es el premio. `seq` sigue siendo `index & 0xFF`.

Paquetes: como mucho 162 EMPTY + 162 OBJECT. CAM 4096 aguanta.
El techo que **no** se toca es el wrap de `seq` en 256, no el
número de pares `(pose, kind)`.

`thought.KEYS` **sigue 22**. El log ya trae `kind`. No se añade
`object_x`. El visor no es este tajo; `board.py` no se redibuja
salvo una letra `O` en `SYMBOL` si `KIND_NAME` crece, para que
un jsonl futuro no reviente. Nada de cubo-copa, nada de KEYS 23.

### Mina: no llames a `Body3DEnv.step`

`NEXT[open][approach][GOAL_POSES] = START`. Si reúsas el `step`
del pulpo, **approach en la mesa teleporta a casa sin el vaso**.
Eso convierte OBJ-1 en el pulpo.

Escribe `step` / `_payoff` / `reset` **propios**. Reusa `DIRS`,
`bumps`, `is_floor`, `pose_of`, `index_of`. El `self.kind` de 162
enteros tiene que **repintarse** cuando el ítem se mueve: el
`Agent` lee `env.kind[j]`.

`teleport` a una pose sobre el ítem deja `coupled=True`. Eso es
lo que el curriculum necesita.

### Escuela

Remainder on, `explore_flat` on, córtex off. Curriculum inverso,
dos etapas, **sin nombrar el camino**:

1. **Ya acoplado.** Inunda distancia-al-cobro sobre el sucesor
   del cubo (el ítem sigue al cuerpo, así que es distancia de
   pose a DEST + el approach que cobra). Cerca → lejos.
   `episode_turns(d)` del pulpo.
2. **Soltero.** Ítem en `ITEM_XYZ`, `coupled=False`, mismo
   reverse desde START.

Examen: greedy, START canónico, ítem en `ITEM_XYZ`, `coupled=False`.
No bajes el START a un vecino de la mesa.

Control, **corrido** no narrado: el mismo schedule, mismo cubo,
pero `_payoff` cobra `agent_at_Y` (como el pulpo) e ignora
`obj`. Luego se examina en el env **real**. Tiene que irse a
la mesa con las manos vacías: `object_hits == 0`.

---

## Lo que no es

- `ext.style = 1` / `domain = 1` / `seq = pose + 162*carrying`.
- `index = pose * 27 + voxel_del_item` (4374 > 4096, wrap sucio).
- 4ª marcha `PICK` / `DROP` / `ABRIR`. `UNIR` **sigue** siendo approach.
- `if pose == DEST: return R_SUCCESS`.
- Pintar DEST `KIND_GOAL` y llamar a `_reward`.
- Empujar tipo Sokoban.
- Dos ítems, hambre, `H`, veneno, ECHO-2.
- Córtex, GUI nueva, `thought.KEYS` 23, reabrir PULPO/SELF/ROOM.
- Waypoints, `if i == …`, lista de poses del camino.

---

## Informe (`lab/nexus0_obj1_report.json`)

```
item                           [2, 0, 0]
dest                           [2, 2, 1]
actions                        3
coupled_is_env_not_wsp         true
dest_is_not_kind_goal          true
domain_is_zero                 true
style_is_zero                  true
seq_is_the_local_pose          true
packet_ceiling_holds           true
packets_empty / packets_object / packets_across
index_max                      161
shortest_collect               ≤ 11          # 8 medido
exam_start_is_canonical        true
exam_item_starts_at_item       true
exam_object_hits               > 0
exam_agent_at_Y_without_object_reward_sum    0
exam_collections_are_object_at_Y             true
control_object_hits            0
control_went_to_dest           true          # el niño se sienta en la mesa
mutant_pays_empty_Y            true          # el mutante se corre
mutant_object_hits             0             # deja el vaso
false_facts destroyed cortex_calls questions
cam_occupied
green
```

Control y mutante se ejecutan de verdad cada vez.

---

## Tests (`TestObj1`)

Sin GGUF.

1. `ITEM_XYZ != START`, `DEST_XYZ` es el voxel del pulpo, layout
   `open`. `N_ACTIONS == 3`. `Agent().q` default remainder /
   explore_flat **False**.
2. Mismo pose, distinto kind: `encode_cell(p, EMPTY) !=
   encode_cell(p, OBJECT)`, 16 B, domain 0, style 0,
   `seq == p`. `encode_cell(0)==encode_cell(256)` sigue.
   `index` del agente nunca ≥ 162.
3. Acoplar: `approach` aterriza en el ítem → `coupled`. El
   siguiente `approach` que no choca mueve **los dos**. `avoid`
   gira el cuerpo y el ítem no se cae.
4. Y vacío: agente en DEST, ítem en ITEM, `approach` → `r !=
   R_SUCCESS`, `obj` no se mueve. Y lleno: los dos en DEST,
   `approach` → `R_SUCCESS`, reset a START + ITEM.
5. `exam_object_hits > 0` desde START canónico. Cada cobro del
   examen tiene `obj == DEST` en ese turno.
6. Control: `control_object_hits == 0` y pisó DEST.
7. Mutante corrido: un env que paga `agent_at_Y` cobra y deja
   el vaso (`mutant_object_hits == 0`). El env real no.
8. Fuente de `obj1.py`: no `WSP_DOM`, no `domain =`, no
   `style =`, no `carrying`, no `ACTION_` cuarto, no `ABRIR`,
   no `KIND_GOAL` en `_payoff`, no `NEXT[`, no `subprocess` /
   `gguf` / `minigrid` / `gym`. Grep de **formas de uso**, no
   de la palabra en comentarios (el diario de GUI-3.5 ya se
   quemó con `because`).
9. Anillo `[-12,+5,0]` +80. Informes pulpo / self1 / room1
   byte-idénticos antes/después del runner. `thought.KEYS`
   sigue 22.
10. `body3d` rc=0, `self1` rc=0, `room1` rc=0. DEST en el
    pulpo **sigue** `KIND_GOAL`. Este tajo no se lo come.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d    # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.room1     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.obj1      # rc=0 solo si green()
```

Si cobra porque DEST es `KIND_GOAL`: **rojo**. Si cobra porque
el START del examen es la mesa con el vaso en la mano: **rojo**.
Si el control también trae el vaso: **rojo** (no era un control).
Si para que Q vea el acarreo metiste `carrying` en el WSP:
**rojo**. Si `Q` pasó a 4 columnas: **rojo**. No piques OPEN-1
en el mismo tajo.
