# Claude — SIGN-Cb: un conflicto, un despertar, una sola línea verdadera

SIGN-C demuestra el mecanismo causal central. **No lo reabras ni cambies
el mundo GOAL**: la tabla `placements` ya prueba que THREAT no discrimina
porque el gate obtiene `avoid +8` sin córtex. Tampoco cambies el código 6,
el latch, el stub, los mutantes causales ni la latencia de un turno.

SIGN-C aún no está cerrado. El diario atribuye el mismo despertar a dos
turnos. Reproducción auditada:

```text
turn 512 · cell 174 · attend_on true · reason conflict · calls 1 · cortex_action null
turn 513 · cell 251 · attend_on true · reason conflict · calls 1 · cortex_action 0
```

La segunda línea no despertó el córtex: sólo consumió la propuesta de la
primera. `thought.py` promete «one line per turn, as the loop actually saw
it» y `board.py` traduce `attend_on=true` como `ON` / `woke`. TALK-1 leerá
ese jsonl, por lo que no puede empezar sobre un evento fantasma.

## Pregunta única

**¿puede el diario distinguir el turno que despertó por conflicto del
turno siguiente que solamente consumió su propuesta?**

## KPI — todo a la vez

```text
conflict turn
  s                            1
  attend_on                    true
  reason_name                  conflict
  cortex_calls delta           +1
  cortex_action                null

consume turn
  attend_on                    false
  reason_name                  off
  cortex_calls delta           0
  cortex_action                approach
  action / reward              approach / +16

whole arm
  conflict_wakes               1
  cortex_calls                 1
  proposal_consumed_next_turn  true
  CortexROI                    +16
  false_facts / destroyed      0 / 0
```

`last_attend` debe describir el turno actual. Cuando
`conflict_suppressed` evita el ATTEND ordinario del turno de consumo,
déjalo explícitamente en `(False, REASON_OFF)` antes de escribir el
diario. La procedencia de la hipótesis consumida ya está en
`cortex_action`; no inventes una clave 23 ni una segunda memoria.

## Cierre del runner

Corrige `signc.arm()` y `green()` para que **no** exijan
`attend_reason_at_landing == conflict`. El informe debe exponer por
separado las dos líneas anteriores y exigir `off` en consumo.

El `green()` de SIGN-C también debe incorporar el benchmark canónico,
no la mini-corrida `256/31/0/168` como sustituto. Puede llamar
`bench.run()` sin escribir su informe y cerrar explícitamente:

```text
policy_after                 [-12, +5, 0]
novel_approach_return        80
cam_misses/surprises/deltas  33 / 1 / 217
surprise_known               1
cortex_calls                 0
false_facts/destroyed        0 / 0
encoder_beats_fnv            true
t_beats_ring                 true
ring --cortex wakes          36 / 256
```

La suite ya protege esos números; aquí se pide que el JSON que dice
`green:true` los proteja también. No pises `lab/nexus0_report.json` ni
ningún informe anterior.

## Tests que deben fallar antes del arreglo

1. Captura las dos líneas reales de `thought.jsonl`: exactamente una
   tiene `attend_on=true` y `reason_name=conflict`.
2. La línea de consumo tiene `attend_on=false`, `reason_name=off`,
   `cortex_action=approach`, acción `approach`, recompensa `+16` y el
   contador acumulado sigue en 1.
3. Si se elimina la supresión, hay dos llamadas o cambia la razón: rojo.
4. Prosa o silencio se consumen una vez y el turno de consumo también
   queda `off`; no dejan una razón pegada.
5. `signc.green()` cae si se muta cualquiera de los candados canónicos.
6. `thought.KEYS == 22`, `N_ACTIONS == 3`, flag default off.

No arregles el test esperando dos líneas `conflict`: eso consagraría la
mentira. No añadas `proposal_reason`, `events`, otro bus ni prosa al log.

## Puerta de operador

`lab/nexus0_qwen_signc_report.json` actual es honestamente rojo:
`model_configured=false`, `qwen_hits=0`, `CortexROI=0`. No descargues
pesos ni falsifiques esa puerta. Roger correrá el 4B después de SIGN-Cb.
CI sigue usando el stub determinista.

## No tocar

`constants.py`, `encoder.py`, `parse_reply`, CAM/T/Q/gate, recompensas,
`graph.NEXT`, packet de 16 B, `thought.KEYS`, kernel/ISO/userland,
informes anteriores. No empieces TALK-1.

## Banco de entrega

```bash
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.graph
PYTHONPATH=. python3 -m echoai.nexus0.open1
PYTHONPATH=. python3 -m echoai.nexus0.obj1
PYTHONPATH=. python3 -m echoai.nexus0.self1
PYTHONPATH=. python3 -m echoai.nexus0.room1
PYTHONPATH=. python3 -m echoai.nexus0.body3d
```

Entrega el diff, los dos registros auditados, el JSON SIGN-C regenerado,
los candados canónicos y md5 de informes ajenos. Si el turno de consumo
sigue diciendo que despertó, **rojo**. No piques TALK-1.
