# CLAUDE OPUS 5 — SIGN-C (pegar tal cual)

OPEN-1 está **verde Codex con asterisco no bloqueante**. No lo reabras.
No toques `open1.py`, `obj1.py`, `body3d.py`, `self1.py`, `room1.py`,
`board.py`, `thought.KEYS`, R/alpha/gamma, `constants.N_ACTIONS`, el parser
de respuestas, kernel, ISO ni informes de tajos anteriores.

Lees antes: `CLAUDE.md`, `docs/05-NEXUS-0-SPEC.md`, `nexus0/loop.py`,
`nexus0/attend.py`, `nexus0/world.py`, `nexus0/graph.py`,
`nexus0/sign.py`, `nexus0/cortex.py`, `nexus0/cortex_turn.py`,
`nexus0/tools/sign_cortex.py` y este archivo entero.

Eres implementador. Un slice. Un KPI. El rápido sigue funcionando sin
LLM. El 4B interpreta un letrero; no navega, no planifica y no escribe
hechos.

---

## Lo ya demostrado

```text
WORLD-3   HOME T conocido 16/16; SHIFT conserva 15/16
          el único error está en el fork; surprise_known sube
CORTEX-1  un extract lingüístico puede producir una propuesta atómica
Qwen-0    8/8; paráfrasis 6/6 frente al stub 0; false_facts 0
OPEN-1    acción opt-in 4; default Agent sigue 3
anillo    [-12,+5,0] · +80 · 33/1/217 · cortex default 0
          --cortex 36/256 · KEYS 22
```

SIGN-C no vuelve a demostrar SIGN ni WORLD-3 por separado. Une las dos
cosas: el mundo contradice una predicción confiada y esa contradicción,
si había lenguaje, despierta el reloj lento.

---

## Pregunta y KPI único

**¿Una contradicción conocida de T, con Q confiada y un letrero presente,
despierta ATTEND una sola vez y mejora la siguiente decisión?**

Todo esto es un único cierre causal:

```text
brazo SIGN-C
  origin was known to T                    true
  origin was not a CAM miss                true
  T prediction contradicted by world       true
  Q margin at origin                       >= ESC_MARGIN
  world-provided language at origin        true
  attend reason                            conflict
  conflict cortex wakes                    1
  atomic proposal consumed next turn       true
  CortexROI                                > 0

control sin córtex, mismo entrenamiento/shift/asiento/turnos
  conflict observado                       true
  cortex wakes/actions                     0 / 0
  reward menor que SIGN-C                  true

mutantes
  mismo conflicto pero extract vacío       0 conflict wakes
  extract presente pero T acierta           0 conflict wakes
  conflicto desde T_MISS                    0 conflict wakes

locks
  false_facts / destroyed                  0 / 0
  ring default                             números exactos intactos
  ring --cortex                            36 / 256
```

Si el córtex despierta por LOW_C, NOVEL, MISS o NO_MAP y no por
`REASON_CONFLICT`, el tajo está rojo. Si el letrero se consulta antes de
que el mundo contradiga T, está rojo. Si el 4B decide una ruta completa,
está rojo.

---

## El banco: WORLD-3 con un letrero local

Crea `nexus0/signc.py`; importa o subclasifica WORLD-3 sin modificar su
informe ni su `green()`.

1. Entrena el mismo `Agent` en HOME.
2. Cambia a SHIFT conservando CAM, T y Q.
3. Entra en el fork B, donde Q prefiere `approach` y T predice C.
4. El mundo entrega X. Esa es la contradicción conocida ya medida por
   WORLD-3.
5. El texto estaba en el **origen** B y explica la inversión local. No
   pintes B como NOVEL/THREAT ni cambies su WSP; el extract queda fuera de
   los 16 bytes como en SIGN.
6. El resultado del córtex es una propuesta atómica para el turno
   siguiente en X. Usa la física que WORLD-3 ya tiene: X es THREAT,
   `avoid` paga +8 y vuelve a B; el control con la fila plana espera y
   cobra 0. No añadas una recompensa o transición para SIGN-C.

El letrero puede decir, en español, que la palanca gira al revés y que hay
que retroceder. La respuesta atómica debe usar los verbos existentes
(`TEMER` → avoid, por ejemplo). No añadas una quinta física ni uses
`ABRIR`: este banco tiene tres acciones.

No hardcodees una lista de nodos o una ruta en el córtex. El stub de CI
puede reconocer la frase canónica, igual que `sign_cortex.py`; el informe
de operador con Qwen debe incluir paráfrasis para demostrar que el 4B lee
lenguaje y no el ID del nodo.

---

## La causalidad temporal

Hoy `Agent.turn()` llama a `_attend()` antes de actuar y sólo conoce la
contradicción después de `env.step()`, al comparar `pred_next` con
`slot_n`. No puedes hacer que una evidencia futura cambie la acción que
la produjo.

Añade un flag opt-in, por ejemplo `conflict_attend=False`, con default
apagado. Cuando esté encendido:

- captura en el origen si Q era confiada (`q.margin(slot) >= ESC_MARGIN`),
  el `extract_text` que puso el mundo y la predicción de T;
- tras observar un sucesor distinto a una predicción conocida, marca un
  conflicto de un turno;
- consulta el mismo córtex por el mismo cable con
  `REASON_CONFLICT` y el registro del origen;
- conserva como máximo una propuesta atómica para que `_propose()` la
  consuma al turno siguiente;
- en el turno de consumo no vuelvas a despertar el ATTEND ordinario por
  LOW_C/NO_MAP: ya hay una consulta causal pendiente; esto vale también
  si la respuesta fue silencio o inválida;
- borra el latch aunque la respuesta sea silencio, inválida o bloqueada.

`Cell.extract` sintetiza `cell=N kind=...` cuando `extract_text` es `None`.
Ese rótulo **no es lenguaje** y no habilita SIGN-C: exige
`extract_text is not None` y texto no vacío. No añadas otro jsonl, otro
paquete, otra CAM ni otra cola. No llames al
córtex dos veces por el mismo conflicto. No cuentes `T_MISS` como
contradicción. La observación del mundo sigue actualizando T por su camino
normal; la salida del córtex no lo toca.

Añade `REASON_CONFLICT` al final de la numeración de `attend.py` y su
nombre. No cambies los códigos existentes. La lógica vieja de ATTEND y su
orden quedan idénticos cuando el flag está apagado.

---

## Ficheros e informes

Nuevos:

- `nexus0/signc.py`
- `nexus0/tools/signc_cortex.py` para CI, sin red ni pesos
- `nexus0/qwen_signc.py`, arnés de operador; no descarga ni arranca pesos
- `lab/nexus0_signc_report.json`
- tests `TestSignC` en `tests/test_nexus0.py`

Informe de operador, separado del green de CI y generado por Roger:

- `lab/nexus0_qwen_signc_report.json`

Puedes ampliar el prompt externo de `tools/qwen_cortex.py` sólo si todos
los tests y el informe Qwen-0 anterior siguen válidos. CI jamás exige
GGUF, servidor, red ni variable de entorno.

El runner determinista cierra el mecanismo. SIGN-C completo requiere
además que el informe de operador mida, con el 4B configurado:

```text
model_configured             true
attend_reason                conflict
qwen_calls                   > 0
qwen_rejected                < qwen_calls
qwen_action_at_X             avoid
qwen_reward_at_X             8
fast_reward_at_X             0
CortexROI                    > 0
paraphrase_qwen_hits         > paraphrase_stub_hits
false_facts                  0
```

El prompt del 4B recibe el letrero, no el grafo ni una lista de nodos. Un
único átomo de acción demuestra lectura local; no se le ofrece una API de
rutas con la que pudiera elegir el desvío.

No pises `lab/nexus0_report.json`, `nexus0_world3_report.json`,
`nexus0_cortex1_report.json`, `nexus0_qwen4b_report.json` ni informes de
ROOM/OBJ/OPEN.

---

## Tests que deben matar el teatro

1. `REASON_CONFLICT` tiene código nuevo y nombre estable; los seis códigos
   anteriores no cambian.
2. El default `Agent()` no tiene la función activa y reproduce el bench
   exacto. `ring --cortex` conserva 36 wakes.
3. El brazo aprende HOME, entra en SHIFT con la fila T conocida y Q margin
   suficiente, ejecuta la predicción, aterriza en X y sólo entonces cuenta
   un wake `conflict`.
4. La propuesta se usa exactamente una vez en el turno siguiente. Una
   respuesta inválida cae a Q; una respuesta válida aún pasa por gate.
5. Mismo conflicto con `extract_text=None`, etiqueta sintética o texto
   vacío: cero wakes de conflicto.
6. Mismo letrero con transición conforme a T: cero wakes de conflicto.
7. T desconocida (`predict is None`) + letrero: cero wakes de conflicto.
8. Control rápido y brazo SIGN-C comparten entrenamiento, estado inicial,
   turnos y física; `CortexROI > 0` se debe a la acción propuesta.
9. El stub no importa echoAI, no mira node ID/kind/layout y sólo lee el
   extract. Un texto no reconocido produce silencio.
10. La salida del córtex no cambia CAM `has_fact`, T ni Q directamente;
    `false_facts=0`, `destroyed=0`.
11. Informe propio y byte/mtime idénticos para todos los informes previos.
12. Suite completa: 342 tests actuales + los nuevos, con sólo el
    `expectedFailure` de WALK-1.

Incluye un test estructural para que el hot path no importe HTTP, SDKs,
torch, transformers ni llama. `cortex.py` puede seguir invocando el
proceso local sólo cuando el operador lo configura.

---

## Deudas que NO pertenecen a este KPI

- TALK-1 y cualquier narración.
- PATTERN-0 / n-gramas.
- XFER-1 de tres mundos.
- soporte del córtex para proponer `ABRIR`.
- planner de cuatro acciones.
- ROOM-2, hambre, muerte, SLEEP, Akida.

Puedes corregir `loop._attend()` para medir una fila plana usando el ancho
real de Q **sólo** con un test que fije byte por byte el comportamiento de
tres acciones. No conviertas esa limpieza en el KPI de SIGN-C.

---

## Banco de entrega

```text
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.sign
PYTHONPATH=. python3 -m echoai.nexus0.graph
PYTHONPATH=. python3 -m echoai.nexus0.open1
PYTHONPATH=. python3 -m echoai.nexus0.signc
```

Entrega: número total de tests, único `expectedFailure`, JSON completo de
SIGN-C, candados del anillo, comparación causal con control y lista de
ficheros modificados. Si un mutante pasa o el wake no es `conflict`, rojo.
No piques TALK-1 en el mismo tajo.
