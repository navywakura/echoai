# CLAUDE — ROOM-1 (pegar tal cual)

SELF-1 está **verde**. No lo reabras. No toques `self1.py` ni
`lab/nexus0_self1_report.json`. No toques `body3d.experiment` /
`body3d.green` / el cubo que ya cobra. No retunees R/α/γ. No 4ª
acción, no `domain` como `room_id`, no uint16 en `seq`, no subir CAM.
No descargues un LLM. No toques kernel, ISO, `parse_reply`,
`constants.py`, `graph.py`, `sign.py`, `board.py`, `thought.KEYS`,
`plan.py` default 0, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/body3d.py` (cubo 162), `echoai/nexus0/encoder.py`
(`seq = index & 0xFF`, domain=0), `echoai/nexus0/graph.py` (transfer
HOME→SHIFT), `echoai/docs/CHATGPT_ECHO1_VERDICT.md` § frames / DynamicAlias.

Eres implementador. Un slice. Un KPI. Córtex **apagado**.
Este es el segundo tajo de **ECHO-1**.

---

## Qué está demostrado (no lo reabras)

```
pulpo     open 64 / block 42 / desvío 11=horizonte / explore_flat opt-in
self-1    offset motor=1 world=0 / gap=1 / T 56>46 / slip=2 → 2
anillo    [-12,+5,0] +80  33/1/217  remainder off  explore_flat off
techo     encode_cell(0) == encode_cell(256)     se MIDE, no se agranda
```

CAM 4096 no es el tamaño del mundo. Es el número de estados cognitivos
distintos. Dos sitios que **se comportan igual** deben compartir
paquete. Eso es compresión, no un bug.

---

## El KPI

Dos habitaciones **idénticas** (el cubo open de PULPO, dos veces).
El `frame` vive en el **env**, no en el WSP.

```
encode_cell(pose, kind) es el mismo en A y en B
domain sigue 0
DynamicAlias = 0     # mismo WSP ⇒ mismo sucesor T
train en A, teleport a B (nada de Q/T/CAM se resetea)
exam greedy START en B: goal_hits > 0
CAM ocupada en A+B  ≲  CAM de una sola habitación, no el doble
córtex 0 · false_facts 0 · destroyed 0 · questions 0
```

Control: un Agent **sin** haber visto A, soltado en B. No cobra (o
cobra menos). El transfer_gain es `exam_B_transferred > exam_B_scratch`.

`green()` exige eso + `packets_across_rooms == 162` (no 324) +
`domain_is_zero` + el techo 256 intacto.

---

## Qué construyes

Archivo **nuevo** `echoai/nexus0/room1.py`. No hinches `body3d.py`.
Reutiliza `Body3DEnv` / el cubo open. Informe:
`lab/nexus0_room1_report.json`. Nunca pisa pulpo / self1 / anillo.

```
Room1Env(frame=0|1, layout="open")
  cell().index     = pose local 0..161     # lo que entra en encode_cell
  env.frame        = 0 o 1                 # FUERA del paquete
  step             = la física del cubo en ESE frame
```

No hay portal en este tajo (un portal con paquete local-only **es**
un alias en esa celda; se mide en ROOM-2, no se “arregla” aquí).
El paso A→B es `teleport` al START de B, como WORLD-3.

Entrenamiento: curriculum inverso de `body3d._curriculum` sobre A,
remainder on, `explore_flat` on, córtex off. Luego:

1. Cuenta paquetes distintos en A, en B, en A∪B.
2. DynamicAlias: pares (pose_A, pose_B) con el mismo WSP cuya
   física `approach` **difiere**. En habitaciones idénticas = 0.
3. Examen greedy START en B, mismo Agent.
4. Control scratch en B.
5. Mutante **corrido**, no narrado: B con el tapón `(2,1,0)`.
   Mismos paquetes, física distinta en 4 poses.
   `dynamic_alias_with_hole > 0`. **No lo arregles** metiendo
   `frame` en `domain` ni en `seq`. El número se reporta. Ese
   hueco es el de ROOM-2 / el encoder, no de este verde.

### Lo que no es

- `ext.domain = frame`. Test: todos los WSP de room1 tienen domain 0.
  Grep de `room1.py` + de lo que toques en `encoder.py`: si asignas
  domain desde frame, rojo.
- `seq = frame * 162 + pose`. Eso explota el techo (324 > 256) y
  **impide** compartir. El punto de este tajo es compartir.
- Pintar las dos rooms con `kind` distinto para distinguirlas.
- Córtex, GUI, objetos, ABRIR.
- Olvidar rooms (I6 `destroyed=0`). Comprimir ≠ podar.

---

## Informe (`lab/nexus0_room1_report.json`)

```
frames                         2
local_poses                    162
packets_in_A / packets_in_B / packets_across
dynamic_alias                  0
dynamic_alias_with_hole        >0     # mutante corrido
domain_is_zero                 true
packet_ceiling_holds           true   # encode_cell(0)==encode_cell(256)
exam_B_transferred_goal_hits   >0
exam_B_scratch_goal_hits       (control)
transfer_gain                  transferred - scratch  > 0
cam_occupied_A
cam_occupied_AB                ≲ cam_occupied_A * 1.2   (comparten)
t_known_in_B_before_a_step     >0     # como WORLD-3 conoce B
false_facts destroyed cortex_calls questions
green
```

---

## Tests (`TestRoom1`)

1. `env.frame` existe; `encode_cell` no lo ve: mismo pose ⇒ mismo WSP
   en A y B, 16 B, domain 0.
2. `packets_across == 162`.
3. `dynamic_alias == 0` en el par idéntico.
4. `dynamic_alias_with_hole > 0` y **domain sigue 0** en ese mutante.
5. `exam_B_transferred_goal_hits > 0` desde START canónico.
6. `transfer_gain > 0`.
7. `cam_occupied_AB <= cam_occupied_A + margen` (no el doble).
8. Fuente de `room1.py`: no `WSP_DOM`, no `domain =`, no `style = frame`.
9. Anillo `[-12,+5,0]` +80. Pulpo y self1 reports byte-idénticos
   antes/después del runner.
10. `encode_cell(0) == encode_cell(256)` sigue.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d    # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1     # rc=0
PYTHONPATH=. python3 -m echoai.nexus0.room1     # rc=0 solo si green()
```

Si B cobra porque reentrenaste en B: **rojo**. Si las rooms no
comparten paquete: **rojo**. Si para el hueco cambiaste domain:
**rojo**. Si subiste el cubo a 4³: **rojo**.
