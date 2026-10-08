# Claude — XFER-1b: cerrar la identidad y los controles

XFER-1 tiene un resultado causal prometedor y **no se rediseña**:

```text
B: 208 frente a 152, gain +56
C: 224 frente a 152, gain +72
agregado +128
Pattern transfer 96/96; PATTERN-0 sigue 80/40/+40
```

Pero Codex reprodujo tres falsos verdes. Hasta cerrarlos, XFER-1 no cierra
ECHO-1.

El tajo único es **XFER-1b**, auditoría y controles. No cambies la física,
las recompensas, los turnos, las posiciones, el riff ni las cifras para hacer
pasar la puerta.

---

## 1. Probar el mismo `Agent`, no sólo las mismas memorias

Contraejemplo actual:

```python
old = new_agent()
school(old)

reborn = new_agent()
reborn.cam = old.cam
reborn.q = old.q
reborn.t = old.t
reborn.pattern_memory = old.pattern_memory

id(old) != id(reborn)                       # es otro cuerpo
identities(old) == identities(reborn)       # hoy pasa como el mismo animal
```

`same_agent_across_worlds` se deriva sólo de los cuatro objetos internos.
Eso demuestra memoria conservada, no que el `Agent` no fue reconstruido.

Cierre:

- conserva una referencia real al `Agent` nacido, además de referencias a
  CAM/Q/T/PatternMemory;
- compara con `is`, no con parecido ni con snapshots;
- el informe sigue sin imprimir direcciones crudas, para conservar
  determinismo;
- publica `same_agent_object=true` y exige esa clave en `green()`;
- el contraejemplo anterior debe dar `same_agent_object=false` aunque las
  cuatro memorias sean exactamente las antiguas;
- añade un mutante requerido independiente: «Agent nuevo con las cuatro
  memorias antiguas injertadas».

No quites las cuatro comprobaciones de identidad existentes: cuerpo y
memorias son afirmaciones distintas.

---

## 2. Atar `gain` a las recompensas dentro de `green()`

Contraejemplo actual, reproducido:

```python
r = experiment()
r["gain_B"] = 1
r["gain_C"] = 1
r["aggregate_transfer_gain"] = 2
green(r) is True
```

Las recompensas siguen implicando +56/+72, pero los campos gain ya dicen
otra cosa y la puerta lo acepta.

Exige simultáneamente:

```text
gain_B == transfer_reward_B - scratch_reward_B
gain_C == transfer_reward_C - scratch_reward_C
aggregate_transfer_gain == gain_B + gain_C
gain_B > 0
gain_C > 0
```

Añade dos mutantes independientes con gains positivos pero desligados de las
restas. No basta probar `gain=0`: las otras cláusulas ya lo rechazan.

---

## 3. Emparejar los flags de los brazos que realmente corren

`matched_flags` se calcula hoy comparando el animal transferido con un
`Agent()` ajeno al control. No inspecciona el scratch ni el control de edad.
Por eso puede seguir en `true` aunque el scratch real nazca, por ejemplo, con
`ask=True`, `cortex=True` y PatternMemory apagada.

Construye una firma de protocolo antes de cada ventana para transfer,
scratch y age. Debe incluir al menos:

```text
n_actions
ask_enabled
cortex_enabled
pattern_memory enabled
plan_depth
escalate_enabled
conflict_attend
Q.trace / Q.remainder / Q.explore_flat
env.seed
```

En B y C:

```text
transfer_signature == scratch_signature == age_signature
```

El layout/`void` no forma parte de esa igualdad: es precisamente la variable
del brazo de edad. Registra firmas deterministas, no ids.

Suma `false_facts`, `destroyed`, `cortex_calls` y rechazos de **todos** los
brazos ejecutados, no sólo del transferido. `llm_calls=0` no puede ser una
constante que ignore un control con córtex encendido.

Mutantes independientes:

- scratch con PatternMemory apagada;
- scratch con cortex/ask encendidos;
- scratch con remainder o explore_flat distinto;
- age con flags distintos;
- semilla distinta aunque esta física determinista no cambie el reward: se
  mata por protocolo, no por desenlace.

---

## 4. Aislar la utilidad de PatternMemory de la disponibilidad de CAM

El 96–0 actual no aísla PatternMemory. El scratch no tiene ranuras para R0/R1/R2:

```text
learned PatternMemory + CAM scratch vacía -> 0 hits, 96 unknown
scratch actual                           -> 0 hits, 96 unknown
```

Es decir, ese cero puede explicarse completamente por no poder mapear los
puntos a slots, antes de consultar la memoria de patrón.

Añade una ablación perceptualmente emparejada:

- usa exactamente los mismos tuples enteros `(prev_slot, slot, action,
  next_slot)` ya resueltos por una CAM que conoce el riff;
- compara la PatternMemory entrenada con una PatternMemory nueva y vacía;
- ninguna de las dos sondas puede escribir CAM, T, Q o PatternMemory;
- ambas tienen el mismo número de slots conocidos y los mismos targets;
- `None` sigue siendo fallo y permanece en el denominador.

KPI:

```text
pattern_probe_mapping_matched_B/C     true
pattern_probe_known_slots_B/C         == pattern_entry_points_B/C
trained_pattern_hits_B/C              > empty_pattern_hits_B/C
pattern_probe_writes                  0
```

Puedes conservar la fila scratch original, pero no usar su CAM vacía como
prueba de utilidad **propia** de PatternMemory.

Añade el mutante inverso: PatternMemory entrenada con CAM incapaz de resolver
los slots da 0; la puerta debe rechazar que se cite esa fila como ablación
emparejada.

---

## 5. Probar que PatternMemory recibe la misma transición que T

El mutante actual llamado «PatternMemory no recibe las mismas transiciones
que T» construye `half = PatternMemory()` y recorre un bucle cuyo cuerpo no
inserta nada. En la práctica compara memoria entrenada contra memoria vacía;
no audita el canal compartido.

Instrumenta una corrida corta:

- registra cada llamada real a `T.observe(slot, action, next_slot)`;
- registra cada llamada real a
  `PatternMemory.observe(prev_slot, slot, action, next_slot)`;
- tras cada `clear_context`, Pattern omite exactamente la primera transición;
- en las restantes, la proyección `(slot, action, next_slot)` debe coincidir
  elemento por elemento con T;
- si `self_model.observe_step` rechaza una transición, ninguno de los dos
  aprende.

Publica una comprobación recomputada y crea un mutante que altere o quite una
transición de Pattern sin apagar toda la memoria.

---

## 6. Corregir una afirmación muerta del control de edad

El texto dice que PARK_VOID tiene «un riff cuyos sucesores se alternan»,
pero `aged_agent()` nunca entra en el riff y `_successor()` devuelve siempre
`options[0]`; no alterna. El resultado de edad sigue siendo válido porque el
control no pisa R0/R1/R2.

Elige una sola verdad y mídela:

- recomendado: elimina la afirmación y el código de riff alternante no usado;
  declara que el control de edad nunca entra al riff, como ya prueban los
  tests;
- o implementa alternancia real y haz que el protocolo la ejercite, sin
  entregarle la regularidad verdadera.

No dejes una regularidad de control afirmada pero no ejecutada.

---

## Cierre XFER-1b

Conserva todos los KPI anteriores y añade:

```text
same_agent_object                         true
gains_equal_reward_differences            true en B y C
protocol_signatures_match                 true en B y C, tres brazos
all_arms_cortex_calls / false_facts       0 / 0
pattern_probe_mapping_matched             true en B y C
pattern_channel_matches_t                 true
```

La batería mantiene la disciplina TALK-1c: requeridos completos, entradas
válidas, sin duplicados, ningún vivo presente o futuro y contadores
recalculados desde la lista.

No cambies PARK_A/B/C, rewards, `SCHOOL_TURNS`, `RIFF_TURNS`, `WINDOW_TURNS`,
`TURN_BASE`, Q/T/PatternMemory ni las cifras para cerrar esto. `pattern.py`
permanece intacto. El hook de `loop.py` sólo se toca si la prueba del canal
descubre un error real.

Banco:

```bash
PYTHONPATH=. python3 -m echoai.nexus0.xfer1
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.pattern0
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.nexus0.signc
PYTHONPATH=. python3 -m echoai.nexus0.graph
PYTHONPATH=. python3 -m echoai.nexus0.room1
PYTHONPATH=. python3 -m echoai.nexus0.bench
```

Reporta los contraejemplos antes/después, tests focales, suite, batería,
mutantes en fuente, determinismo del informe y archivos tocados.

Si cualquiera de estos contraejemplos sigue pasando: **XFER-1 sigue rojo y
ECHO-1 no está cerrado**. No empieces VITA-1 ni ECHO-2.
