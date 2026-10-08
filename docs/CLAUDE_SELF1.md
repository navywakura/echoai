# CLAUDE — SELF-1 (pegar tal cual)

PULPO-C está **verde**. No lo reabras. No toques `body3d.experiment`,
`body3d.green`, `lab/nexus0_pulpo_report.json`, ni el cubo/tapón que
ya cobra. No retunees `R_*`, α, γ. No traces, no n-step, no 4ª acción,
no átomo CONCIENCIA, no segundo CAM, no `domain` como etiqueta. No
descargues un LLM. No toques kernel, ISO, `parse_reply`, `encoder.py`,
`constants.py`, `graph.py`, `sign.py`, `board.py`, `thought.KEYS`,
`plan.py` default 0, ni `lab/nexus0_report.json`.

Lees **antes**: `echoai/nexus0/body3d.py` (env 3×3×3, remainder,
`explore_flat`), `echoai/nexus0/world.py` (T), `echoai/docs/CHATGPT_ECHO1_VERDICT.md`
§ SELF-1, `echoai/lab/nexus0_pulpo_report.json`
(`exam_open_goal_hits_after_readapt` — olvido, un solo mapa).

Eres implementador. Un slice. Un KPI. Córtex **apagado**.
Este es el primer tajo de **ECHO-1**.

---

## Qué está demostrado (no lo reabras)

```
pulpo open    64 cobros  corto
pulpo block   42 cobros  desvío 11 = horizonte 11
control       64 / 0     explore_flat off
T             56/56 vs stepper 4/56
anillo        [-12,+5,0] +80  33/1/217
olvido        after_readapt open cobra 42 por el DESVÍO, no 64 por el atajo
```

El pulpo cambia de estrategia porque un curriculum le vuelve a enseñar
el cubo tapado. Eso no es atribuir. ECHO-1 empieza aquí: **la misma
observación “predije mal” puede ser el cuerpo o el suelo**, y el
animal tiene que tratarlas distinto **sin que nadie le ponga un letrero**.

---

## El KPI

Dos brazos ciegos, mismo entrenamiento, luego se parte el Agent
(copia Q/T/CAM). Ningún brazo recibe `MOTOR` / `WORLD` en el WSP,
ni en `kind`, ni en `extract`.

| brazo | perturbación | el agente debe | el control (sin self-model) |
|---|---|---|---|
| **A** | el **motor** resbala: `approach` avanza por `(h+slip)%6`, cubo igual | `body_offset == slip` y T del cubo **sin** resbalón se conserva | reescribe T como si el mundo hubiera cambiado |
| **B** | el **suelo** cambia: un voxel de pasillo se hace piedra, motor intacto | `body_offset == 0` y T no afectadas se conservan | igual de local — el hueco no está aquí |

```
SelfAttribution_agent  = 1  si (A: offset==slip) ∧ (B: offset==0)
SelfAttribution_control = 0  (no hay offset; siempre 0)
SelfAttribution_agent - SelfAttribution_control  > 0

RecoveryRate
  exam_motor_goal_hits  > 0     greedy, START canónico, córtex 0
  exam_world_goal_hits  > 0     idem
  control_motor_t_world_preserved < agent_motor_t_world_preserved
```

`t_world_preserved` = filas T de `approach` que **siguen** prediciendo
la cinemática del cubo **sin** resbalón, en poses que el suelo no tocó.

Sin recuperación (cobra 0 en A o en B) el slice es rojo aunque acierte
el offset. Sin atribución (offset mal, o el control conserva igual de
T) es rojo aunque cobre. Los dos números.

`green()` exige eso + `false_facts=0` `destroyed=0` `cortex_calls=0`
`questions=0` `actions=3` `explore_flat` default **False** en `Agent()`.

---

## Qué construyes

Archivo **nuevo** `echoai/nexus0/self1.py`. No hinches `body3d.py`.
Reutiliza `Body3DEnv` del cubo **open** (el corto que ya anda). El
tapón de PULPO-C puede ser la perturbación B; no hace falta otro
laberinto. Informe propio: `lab/nexus0_self1_report.json`. Nunca pisa
`nexus0_pulpo_report.json` ni `nexus0_report.json`.

### Planta

Un entero en el Agent, no un WSP:

```
body_offset ∈ {0,1,2,3,4,5}     # default 0
```

Significa: “mi approach empuja por `(h + body_offset) % 6`”.
Seis hipótesis. Cero floats. Cero átomos nuevos.

Perturbación A, en el **env** (física, no etiqueta):

```
slip = 1     # approach se traduce por DIRS[(h+1)%6]; heading de la pose no gira
```

El cubo, el GOAL, el START `(0,0,0,+X)` no cambian. Todas las
transiciones `approach` cambian. Las de `avoid`/`wait` no.

Perturbación B: un voxel del pasillo corto se hace piedra (el tapón
`(2,1,0)` vale). Motor `slip=0`. Pocas transiciones cambian
(`approach_diff` ya existe).

### Cómo atribuye, sin letrero

Tras el entrenamiento en el cubo intacto (remainder on, `explore_flat`
on, córtex off, curriculum inverso del open — puedes llamar a
`body3d._curriculum` sobre `LAYOUT_OPEN`):

1. Congela una copia del Agent. Mide T contra la cinemática **sin**
   resbalón: eso es `T_world`.
2. Enchufa A o B. **No** resetee Q/T/CAM.
3. Ventana corta de observación (explora, no greedy; cota que tú fijas
   y documentas; no 65 k turnos). Cada turno: predicción vs pose vista.
4. Para cada `k` en `0..5` cuenta cuántos errores de `approach` de la
   ventana explicaría “el cuerpo empuja por `(h+k)%6`”.
5. `body_offset ← argmax_k explained[k]`. Empate → 0 (mundo, no yo).
6. Si `body_offset != 0`, **no** reescribas las filas T que el offset
   ya explica. Si es 0, T se actualiza como siempre (el suelo cambió).

El control es el mismo Agent **sin** el paso 4–6: T se actualiza en
cada sorpresa, `body_offset` no existe o queda 0.

Después: examen greedy desde START, remainder on, córtex off, en el
env perturbado. En A el cuerpo tiene que **compensar** el resbalón
con giros (avoid) para que el approach resbalado apunte al pasillo.
Eso es RecoveryRate, no un `if slip: avoid`.

### Lo que no es

- Un bit `MOTOR_FAILURE` en `style` / `kind` / extract.
- Dos cables WSP.
- `if n_errors > K: offset = 1` clavado al slip del banco. El argmax
  sobre 6 enteros tiene que ganar también si pruebas `slip=2` en un
  test aparte (aunque el KPI del informe sea slip=1).
- Reabrir PULPO-C: no cambies geometría ni `green()` del pulpo.
- Córtex. El 4B no atribuye.

---

## Informe (`lab/nexus0_self1_report.json`)

```
slip                         1
world_plug                   [2,1,0]     (o el voxel que uses)
body_offset_motor            (agente A)
body_offset_world            (agente B)
self_attribution_agent       0 o 1
self_attribution_control     0
attribution_gap              agent - control
t_world_preserved_motor_agent
t_world_preserved_motor_control
t_world_preserved_world_agent
exam_motor_goal_hits
exam_world_goal_hits
exam_motor_control_goal_hits     # puede cobrar reescribiendo T; no es el KPI
observe_turns
false_facts destroyed cortex_calls questions
cam_occupied
green
```

Control y agente se corren de verdad cada vez, no se narran.

---

## Tests (`TestSelf1`)

Sin GGUF.

1. `Agent().q.explore_flat` False, `body_offset` 0 o inexistente.
2. WSP de una pose **igual** en A y en B (mismo `encode_cell`). La
   perturbación no viaja en el paquete.
3. `body_offset_motor == slip` y `body_offset_world == 0`.
4. `attribution_gap > 0`.
5. `exam_motor_goal_hits > 0` y `exam_world_goal_hits > 0`.
6. `t_world_preserved_motor_agent > t_world_preserved_motor_control`.
7. Mutante: el env pone `kind=THREAT` o un extract `"motor"` → el
   test lee el fuente de `_attribute` / equivalente y **prohíbe**
   esas cadenas. Atribución lee predicción vs pose, nada más.
8. Anillo `policy_after [-12,+5,0]`, +80. `self1.py` no importa
   córtex/gguf.
9. `nexus0_pulpo_report.json` byte-idéntico antes/después del runner.
10. `slip=2` (test corto, no tiene que cobrar): el argmax sigue
    eligiendo 2, no 1.

---

## Banco

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.body3d    # sigue rc=0
PYTHONPATH=. python3 -m echoai.nexus0.self1     # rc=0 solo si green()
```

Si A cobra reescribiendo todo T y el offset queda 0: **rojo**. Eso es
el control, no el slice. Si el offset acierta y greedy no llega al
GOAL: **rojo**. No bajes el START del examen a un vecino del premio.
