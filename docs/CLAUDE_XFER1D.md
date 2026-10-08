# Claude — XFER-1d: cerrar el grafo completo de evidencia

XFER-1c cerró los seis falsos verdes escritos en su prompt. El resultado
causal y el animal siguen intactos:

```text
B                         208 vs 152 · gain +56
C                         224 vs 152 · gain +72
agregado                  +128
patrón transfer           96/96
PATTERN-0                 80/40/+40
suite                     477 OK · expectedFailure=1
```

No cambies `loop.py`, mundos, física, rewards, turnos, posiciones, riff,
CAM/Q/T/PatternMemory ni ninguna cifra. Este tajo es sólo del certificado.

Codex reprodujo cinco contradicciones residuales que todavía dan
`green=True`:

```python
r = xfer1.experiment()

# El contador nuevo contradice el resumen de silencio.
b = deepcopy(r)
b["channel"]["refused_t_observations"] = 1
green(b) is True

# Las tres firmas coinciden, pero ya no describen el protocolo prometido.
b = deepcopy(r)
for arm in ("transfer", "scratch", "age"):
    b["rows"][PARK_B]["protocol_signatures"][arm].pop("ask_enabled")
green(b) is True

# Un predictor vacío deja de declarar sus None y el denominador no lo ve.
b = deepcopy(r)
b["rows"][PARK_B]["ablation"]["empty"]["unknown"] = 0
green(b) is True

# Ablación de 95 puntos citada junto a la sonda de entrada de 96.
b = deepcopy(r)
ab = b["rows"][PARK_B]["ablation"]
ab["points"] = ab["known_slots"] = 95
ab["trained"]["hits"] = 95
ab["trained"]["unknown"] = 0
b["pattern_probe_known_slots_B"] = 95
b["trained_pattern_hits_B"] = 95
green(b) is True

# El protocolo crudo cambia, pero su booleano sigue diciendo matched.
b = deepcopy(r)
b["rows"][PARK_B]["transfer"]["turn_first"] += 1
green(b) is True
```

Un sexto contraejemplo muestra que igualdad no basta:

```python
b = deepcopy(r)
for layout in (PARK_B, PARK_C):
    for arm in ("transfer", "scratch", "age"):
        b["rows"][layout]["protocol_signatures"][arm]["ask_enabled"] = True
green(b) is True
```

Los tres brazos son iguales entre sí, pero los tres incumplen el protocolo
de XFER-1: córtex y preguntas apagados. `signatures_match()` demuestra
igualdad, no corrección.

---

## 1. Firma completa y canónica

Define una sola firma esperada, derivada de `protocol_signature(new_agent())`
antes de correr brazos, o de una constante fijada contra esa función. Cada
firma de B y C debe:

- tener exactamente las claves canónicas;
- llevar tipos correctos (`bool` no cuenta como `int`);
- ser igual a las otras dos firmas de su frontera;
- ser igual al protocolo esperado de XFER-1: `ask=false`, `cortex=false`,
  PatternMemory encendida, `plan_depth=0`, `escalate=false`,
  `conflict_attend=false`, Q sin trace/remainder/explore-flat, semilla
  canónica, tres acciones y `WINDOW_TURNS`.

Prueba por separado:

1. falta la misma clave en los tres brazos;
2. los tres brazos llevan `ask=true`;
3. una firma difiere de las otras.

Las tres deben caer aunque todos los booleanos resumen digan `true`.

---

## 2. Protocolo derivado de las caminatas

No creas `matched_turn_values` ni `matched_entry_cell`. Recomputa desde
`row["transfer"]`, `row["scratch"]` y `row["age"]`:

```text
entry_cell
turns
turn_first
turn_last
turn_fingerprint
```

Los tres brazos de cada frontera deben coincidir; `turns == WINDOW_TURNS` y
`entry_cell == SEAT`. Ata los booleanos de fila y los resúmenes superiores a
esa recomputación, o elimina los redundantes.

Incluye mutantes donde cambia sólo `turn_first`, sólo el fingerprint, sólo el
asiento y donde cambia el brazo de edad. Ninguno puede pasar conservando el
booleano `matched_* = true`.

---

## 3. Denominadores completos de Pattern

Valida tipos, rangos y relaciones desde las filas. Para cada sonda
`transfer/scratch/age` y cada brazo `trained/empty`:

```text
points >= 1
0 <= hits <= points
0 <= unknown <= points
hits + unknown <= points       # el resto son predicciones erróneas
observes == 0
```

Además, en este cierre medido:

```text
todos los probes usan los mismos 96 puntos
ablation.points == pattern entry points
ablation.known_slots == ablation.points
trained.points == empty.points == ablation.points
trained.hits == points · trained.unknown == 0
empty.hits == 0 · empty.unknown == points
ablation.writes == trained.observes + empty.observes == 0
```

Las filas de entrada mantienen la tabla publicada: transfer `96/96/0`,
scratch y age `0/96 unknown`, todos sin escrituras. `None` sigue dentro del
denominador.

Mutantes mínimos:

- `empty.unknown=0` con `points=96`;
- `trained.observes=1` dejando `writes=0`;
- ablación de 95 puntos con todos sus resúmenes movidos coherentemente;
- scratch o age con otro número de puntos;
- `hits`/`unknown` negativos, booleanos o mayores que `points`.

---

## 4. Canal derivado de sus contadores

El nuevo `refused_step_silences_both` se calcula bien en
`channel_audit()`, pero `green()` todavía cree el booleano. Derívalo otra vez:

```text
refused_t_observations == 0
refused_pattern_observations == 0
refused_step_silences_both ==
    (refused_t_observations == 0 and refused_pattern_observations == 0)
```

Valida además el protocolo honesto del canal:

```text
turns == 64
t_observations == turns
cuts == len(skipped_after_cuts) == 2
skipped_after_cuts == [0, 32]
pattern_observations == t_observations - cuts
counts_match is true
projection_matches is true
```

`channel_audit(leak_at_slot=1234)` sigue siendo el mutante ejecutable. Añade
el falso verde literal: mover sólo `refused_t_observations` a 1 dejando el
resumen en `true` debe caer.

---

## 5. Identidad de las memorias en cada frontera

Las filas aún contienen `same_objects`. Exige `true` en B y C y átalo a la
afirmación superior de continuidad. Conserva los tests directos con `is`
para el `Agent` y sus cuatro memorias; no imprimas direcciones en el informe.

---

## 6. Una matriz, no otro resumen

Haz una tabla declarativa de hojas requeridas y relaciones, o validadores
pequeños por estructura (`signature_evidence`, `walk_evidence`,
`pattern_evidence`, `channel_evidence`). La condición es que cada hoja que
el informe usa como evidencia tenga:

1. forma y tipo validados;
2. una relación recomputada;
3. un contraejemplo que pueda romper esa relación;
4. ningún booleano autodeclarado como autoridad final.

`green()` debe devolver `False`, no lanzar, ante hojas ausentes, tipos
incorrectos o valores fuera de rango.

La batería mantiene la disciplina TALK-1c: requeridos completos, nombres
únicos, entradas válidas, ningún vivo presente o futuro y contadores
recalculados desde la lista.

---

## Cierre XFER-1d

Reproduce los seis contraejemplos de este prompt y los seis de XFER-1c:
todos deben devolver `False`. La corrida honesta debe conservar exactamente:

```text
B 208 / 152 / +56
C 224 / 152 / +72
agregado +128
trained 96 / empty 0 / writes 0
channel 64 / 62 / cuts 2 · refused 0 / 0
PATTERN-0 80 / 40 / +40
```

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

Reporta falsos verdes antes/después, tests focales, suite, batería,
determinismo y archivos tocados. Hasta que el grafo completo sea coherente:
**XFER-1 sigue rojo y ECHO-1 sigue abierto**.
