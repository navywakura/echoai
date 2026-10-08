# Claude — PATTERN-0: descubrir un riff temporal que T de un paso no ve

TALK-1 está verde y no se reabre: 423 tests, 31 focales TALK, subtítulos
póstumos fieles, aislamiento causal y ninguna entrada viva de la batería
compatible con `green=true`.

El siguiente y único tajo es **PATTERN-0**.

## Pregunta única

¿Puede una memoria temporal entera y acotada descubrir, sin etiquetas ni
LLM, una regularidad de contexto que prediga mejor que `T(s,a)→s'` en una
secuencia futura no usada para entrenar?

```text
entrada                       secuencia observada de slots/acciones/sucesores
baseline                      World T(s,a), entrenado en los mismos pasos
patrón                        contexto corto observado, enteros, memoria fija
frecuencia                    supera umbral fijado antes del examen
held-out prediction gain      > 0 en los mismos puntos de decisión
aprendizaje durante examen    0
etiquetas humanas / LLM       0 / 0
```

No es reconocimiento de palabras ni los n-gramas del encoder. Es dinámica
temporal: el mismo estado y la misma acción pueden tener dos sucesores, y
el historial reciente decide cuál.

## Mundo mínimo que hace necesaria la memoria

Construye una secuencia sin semántica humana, con celdas/paquetes EMPTY y
acciones normales. La forma mínima puede ser una gramática como:

```text
... B → A → C → A → B → A → C → A ...
```

En `A`, para la misma acción, T de un paso ve unas veces `B` y otras `C`.
No puede decidir por construcción. El contexto sí:

```text
B, A  → C
C, A  → B
```

No hardcodees A/B/C en el detector: son sólo slots enteros creados a partir
de observaciones. El mundo/fixture puede definir la física; la memoria debe
aceptar cualquier secuencia de enteros.

Puedes usar otra secuencia si demuestra mejor la misma propiedad, pero
debe existir al menos un `(s,a)` ambiguo para T y determinista bajo contexto.
Reporta los conteos de cada sucesor; no afirmes ambigüedad por diseño.

## Memoria: extensión de T, no segundo cerebro

Crea una pieza pequeña, por ejemplo `nexus0/pattern.py`, que recuerde un
contexto de orden 2:

```text
(slot_anterior, slot_actual, acción) → slot_siguiente
```

Puede generalizarse internamente, pero PATTERN-0 sólo necesita demostrar
el orden mínimo que gana. Requisitos:

- sólo enteros y arrays/listas de capacidad fija;
- capacidad declarada y constante;
- sin `dict` creciente, LRU, borrado ni overwrite silencioso;
- si se llena, incrementa `dropped`; no inventa que recordó;
- conteos saturados y KCC/incumbente explícito ante contradicción;
- `predict()` devuelve `None` hasta alcanzar `PATTERN_MIN_HITS`;
- frecuencia/confianza salen de observaciones, no de nombres del mundo;
- no almacena WSP, frases, kinds, recompensas ni hechos duplicados de CAM;
- no crea otro thought-bus ni modifica `thought.KEYS`.

Es una extensión explícita del predictor: cuando el contexto no es maduro,
la evaluación cae a la predicción normal de T. No reemplaces ni escribas
`World.pred/n/alt`. No integres todavía esta pieza en el hot path default de
`Agent`; XFER-1 decidirá qué memoria merece cruzar mundos después de verla
medida. Un wrapper/compositor de predicción opt-in es suficiente.

## Entrenamiento y examen

T y el patrón reciben exactamente las mismas transiciones de entrenamiento.
Después:

1. captura hash/snapshot de ambas memorias;
2. congela ambas;
3. ejecuta uno o más segmentos held-out;
4. antes de revelar cada sucesor, pide ambas predicciones;
5. puntúa las dos sobre los mismos puntos ambiguos;
6. usa el sucesor real sólo para avanzar el contexto, no para aprender;
7. comprueba cero llamadas `observe()` y hashes idénticos durante examen.

El examen no puede ser un slice de la misma lista ya entregada al detector.
Genera segmentos nuevos desde la regla y usa varias rotaciones/fases con el
contador local reiniciado. Así un mutante `turn % periodo` no puede acertar
todas. El API del predictor no recibe turno, índice de examen, nombre de
mundo ni respuesta futura.

Puntúa con enteros:

```text
decision_points
t_hits
pattern_hits
prediction_gain_hits = pattern_hits - t_hits
```

Puedes añadir ratios para humanos, pero `green()` se decide con conteos.
Exige cobertura del patrón en los puntos ambiguos; `None` no es acierto ni
se elimina del denominador.

## Controles causales

### 1. Sin contexto

Un predictor mutante que ignora `slot_anterior` debe colapsar hacia T y
perder la ganancia. El campo anterior tiene que ser load-bearing.

### 2. Sin regularidad

Alimenta contextos con sucesores balanceados/contradictorios. Ningún patrón
debe alcanzar confianza madura ni producir ganancia positiva. Diseña los
conteos, no confíes en azar accidental.

### 3. Una sola observación

Con frecuencia por debajo de `PATTERN_MIN_HITS`, `predict()` devuelve
`None`. Un recuerdo único no es un patrón.

### 4. Sin fuga del examen

Un mutante que llama `observe()` durante el examen debe mover hash/contador
y caer. Otro que precarga respuestas held-out también debe quedar expuesto
por el límite de entrenamiento o la instrumentación. No uses el resultado
del examen para decidir el umbral.

### 5. Sin reloj absoluto

Evalúa rotaciones distintas con turno local cero. Un predictor de
`turn % 2/3/4` debe fallar; idealmente el núcleo ni recibe `turn`.

### 6. Memoria llena

Introduce más claves contextuales que la capacidad. `size` no supera el
límite, lo existente no se borra y `dropped>0` lo hace visible.

## Informe propio

Crea un runner, por ejemplo `nexus0/pattern0.py`, y sólo su informe:

```text
lab/nexus0_pattern0_report.json
```

Campos mínimos:

```text
world / rule_description
context_order
capacity / size / dropped
min_hits
train_transitions
exam_transitions
exam_rotations
ambiguous_state_counts          sucesores observados por T
pattern_context_counts          frecuencia de los contextos maduros
decision_points
t_hits
pattern_hits
prediction_gain_hits
pattern_unknown
observes_during_exam            0
t_hash_before/after             iguales
pattern_hash_before/after       iguales
no_pattern_mature               true
no_pattern_gain_hits            <= 0
absolute_clock_control_fails    true
human_labels                    0
llm_calls / cortex_calls        0 / 0
false_facts / destroyed         0 / 0
green
```

No pongas `green=true` basándote en una descripción. Recalcula los conteos,
las coberturas, hashes y controles. Si incluyes una batería de mutantes,
aplica la lección de TALK-1c: nombres requeridos, entradas válidas, todos
los elementos reales muertos y resúmenes recontados desde la lista.

## Mutantes mínimos

1. ignora el slot anterior;
2. usa sólo `(s,a)` y se hace pasar por patrón;
3. usa `turn % periodo`;
4. aprende durante el examen;
5. precarga o consulta el futuro del examen;
6. activa tras una sola observación;
7. puntúa sólo casos cubiertos y elimina `None` del denominador;
8. compara T y patrón en turnos distintos;
9. memoria sin límite o `dict` creciente;
10. capacidad llena sobrescribe una regla existente;
11. `dropped` no aumenta;
12. el control sin regularidad madura una regla;
13. el patrón escribe T/CAM/Q o guarda WSP;
14. `green()` deja de exigir ganancia, frecuencia o congelación;
15. se borra un mutante requerido pero los resúmenes siguen verdes.

Los mutantes deben ser funciones/clases alternativas o salidas dobladas,
no comentarios ni búsqueda de palabras únicamente.

## Candados que no se mueven

```text
WSP                           16 bytes, único bus
CAM                           4096, sin LRU, destroyed 0
World T                       semántica y tablas intactas
default Agent                 pattern off / sin coste nuevo observable
N_ACTIONS                     3
thought.KEYS                  22
anillo default                [-12,+5,0], +80, 33/1/217, cortex_calls 0
anillo --cortex               36/256
TALK-1 / SIGN-C               informes y comportamiento intactos
```

No hay LLM, Qwen, prosa, etiquetas `pattern`, nombres A/B/C dentro del
detector, segunda CAM ni nueva clave de diario. No toques el encoder para
codificar fase. No conviertas el tiempo absoluto en una observación.

## Entrega

```bash
PYTHONPATH=. python3 -m echoai.nexus0.pattern0
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.talk1
PYTHONPATH=. python3 -m echoai.nexus0.signc
```

Reporta tabla train/held-out, conteos de los dos contextos ambiguos,
predicciones por rotación, memoria/capacidad, hashes antes/después,
mutantes, tests y archivos tocados. No empieces XFER-1.

Si T ya puede resolver el examen, hay aprendizaje durante held-out, el
contexto no es load-bearing o la memoria crece con la corrida,
**PATTERN-0 es rojo**.
