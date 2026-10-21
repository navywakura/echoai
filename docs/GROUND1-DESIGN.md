# GROUND-1 — de observación física a WSP, sin oráculo ni segundo bus

Estado: **contrato aprobado** (2026-09-11), con las enmiendas 1, 2 y
3 aprobadas antes del lock (la 3, tras la revisión independiente). Orden ECHO-3: cuarto tajo, tras SIM-3,
FLIGHT-1S (verde v6) y SENSOR-1S (verde v3). Mismo método: contrato → Nav
aprueba → implementación → revisor independiente → lock → cadena.

## Pregunta única

¿Las observaciones físicas que entrega SENSOR-1S producen, **dentro del
consumidor aislado**, un flujo de paquetes WSP de 16 B que (1) depende sólo de
lo que los sensores entregan, (2) sale por un único cable y (3) conserva la
información física que dice llevar, medida contra la verdad privada?

No pregunta si el agente decide bien, ni lo pone a volar (eso es PX4-1). No
reconoce objetos (PATTERN-1R) ni fusiona evidencias en creencias (FUSION-1).

## Por qué hace falta

Hoy la percepción del Agent es `encode_cell(cell.index, cell.kind)`: el
mundo le da el tipo de celda y su índice viaja en `seq`. En un mundo físico
las dos cosas serían verdad del simulador. SIM-3 lo dejó escrito: «`SDF →
Cell(kind=GOAL)` no se admite como percepción. Queda para GROUND-1».

## Qué ya se midió (datos de SENSOR-1S v3, sin vuelos nuevos)

- Distancia verdadera al obstáculo en ±30° al frente, 6 030 barridos: sólo dos
  bandas en estos vuelos, **< 4 m** y **≥ 4 m o sin retorno**; «cerca» aparece
  en los mundos 0–3 y 7, y la banda sólo cambia al despegar o aterrizar. El 93.7 %
  de acuerdo del mínimo crudo que decía el borrador se midió con la verdad 0.24 m
  baja; corregida, y con la ambigüedad vertical, el mínimo acierta el 100 % de los
  barridos juzgados en 52 vuelos honestos (44 de SENSOR-1S v3, 8 de desarrollo). Por eso el estadístico fijado es el mínimo
  (enmienda 3).
- Pulso en la IMU: pico horizontal 3.37–3.42 m/s² en 40 perturbados; fuera de
  su ventana y en el aire, máximo 0.98 (perturbados) y 1.15 m/s² (nominales).
  Al tocar suelo, picos de contacto de hasta ~300 m/s² (enmienda 2; el borrador
  omitía «en el aire»).
- CAM asigna ranura por los 16 bytes exactos del paquete (`cam.get`; si no
  está, `allocate(..., key=wsp)`, como `loop.Agent._slot_for`). El vértice de
  16 bits (simhash del paquete) sólo entra en `nearest()` y en las métricas de
  Hamming. (Corregido por la enmienda 1: el borrador decía que CAM separa por
  vértice.)

## Traducción (cerrada, entera, en la jaula)

Un paquete por barrido LiDAR (10 Hz), calculado sólo con los registros ya
recibidos (causal), con `navi10_wsp.pack`:

| Campo | Valor |
|---|---|
| `src`, `time` | `YO`, `AHORA` |
| `rel` | `CAMBIAR` si la aceleración horizontal se aparta > 2.0 m/s² de su mediana en [t − 1.1 s, t − 0.1 s) en algún registro de [t − 100 ms, t]; `DESCONOCIDO` si falta un LiDAR válido y fresco; si no, `OBSERVAR` |
| `dst` | `ALLI` si el obstáculo frontal (±30°, mínimo de los haces finitos, fijado en desarrollo; enmienda 3) está a < 4.0 m; `FUERA` si está más lejos o no hay retorno; `DESCONOCIDO` con `rel=DESCONOCIDO` |
| `E` | `C` = 40 si desde el paquete anterior llegó algún registro, de cualquier fuente, con hueco declarado, obsoleto o inválido; si no, 100 (enmienda 3); `U` = 40 cerca, 0 lejos; `A` = 80 con `CAMBIAR`, 10 sin él; `V = D = B = 0` |
| `flags`, `style`, `slot`, `seq` | 0, fijos: ni contador ni índice de lugar |
| `domain`, `generator` | `7` (físico, declarado aquí; `lex` no se toca), `0x06` |

Los flotantes de los sensores se cuantizan a enteros antes de decidir. `E[V]`
no lleva nada: ni recompensa ni δ.

## Criterios verdes

| Grupo | Rojo si |
|---|---|
| SENSOR-1S heredado | cualquier grupo de SENSOR-1S v3 rojo en el mismo vuelo |
| Sólo sensores | el flujo WSP del consumidor ≠ la traducción recalculada por el evaluador desde las muestras crudas privadas (byte a byte) |
| Un solo cable | la salida del consumidor contiene algo más que la lista de paquetes de 16 B y el recuento de SENSOR-1S, o más de una línea en stderr, o algún byte de vuelta por el socket (enmienda 3) |
| Campos fijos | un paquete fuera del conjunto cerrado de la tabla |
| CAM | el flujo emitido, pasado por la ruta de ranuras del Agent sobre una CAM real, pone un mismo paquete en dos ranuras, dos paquetes distintos en la misma, o `destroyed ≠ 0`. La distancia de vértice se publica, no se juzga (enmienda 1). Comprobación estructural del núcleo: sólo puede fallar con > 4096 paquetes distintos (enmienda 3) |
| Distancia | exactitud < 0.95 por etapa (agregada) o < 0.90 por episodio. Cada barrido utilizable cuenta y acierta si `dst` es la banda verdadera; uno no utilizable acierta sólo con `DESCONOCIDO`; un paquete indescifrable es fallo. Se excluyen los ambiguos: verdad a menos de 0.15 m del umbral, o banda que cambia con el sensor ±5 cm en vertical (enmienda 3) |
| Pulso | un perturbado sin evento de fuerza o sin `CAMBIAR` en [pulso, +400 ms], o `CAMBIAR` fuera de [pulso, +2 s] y de [toque − 100 ms, +2 s], o en un vuelo sin fuerza fuera de [toque − 100 ms, +2 s] (enmienda 3). Toque: primera muestra de verdad tras `recover` con el cuerpo a < 20 mm de su altura de reposo (enmienda 2) |
| Certeza | `C` distinto de la regla de la tabla en algún paquete, juzgado contra los marcadores de los registros entregados; que esos marcadores son exactos frente a los fallos inyectados lo juzgan los grupos de SENSOR-1S del mismo vuelo (enmienda 3) |
| Mutantes | alguno aceptado. Cuenta como detectado sólo si se pone rojo su caso concreto (no un informe ausente o desalineado) en un vuelo con ejecución y esquema verdes (enmienda 3) |

## Enmienda 1 (2026-09-11, antes de implementar el evaluador; aprobada)

El criterio CAM del borrador («dos perceptos distintos a ≤ 3 bits de
vértice») no mide lo que el núcleo hace: el Agent separa por clave exacta de
16 B, no por vértice. Además fallaba por construcción con la traducción
aprobada: en el conjunto cerrado de 10 paquetes, `C = 100` y `C = 40` del
mismo percepto quedan a 0–1 bits de vértice y cerca/lejos a 3. El criterio
pasa a ser la identidad de ranura por la ruta real del Agent.

Límite que queda declarado: un módulo futuro que agrupe por `nearest()`
(vértice ≤ 3 bits) no separaría esos perceptos. Es asunto de quien consuma el
vértice (PATTERN-1R, FUSION-1), no de esta traducción.

## Enmienda 2 (2026-09-11, antes de volar; aprobada)

El recálculo de la traducción sobre los 44 vuelos honestos de SENSOR-1S v3
(4 controles incluidos) da `CAMBIAR` al aterrizar en todos: de +12 ms a
+1.47 s tras el toque verdadero (la revisión encontró después +6 ms y picos
anteriores a la muestra de verdad; enmienda 3), con picos de contacto de Gazebo de hasta
~300 m/s². El borrador lo ponía rojo porque su dato («máximo 1.15 m/s² fuera
del pulso») se midió sólo en el aire. El toque es un cambio físico real: la
traducción no cambia y `CAMBIAR` se **permite, no se exige**, en [toque,
+2 s]. El resto del vuelo sigue juzgado; fuera del pulso y del toque el
máximo en esos 44 vuelos es 1.15 m/s² frente al umbral de 2.0.

## Enmienda 3 (2026-09-11, tras la revisión independiente; aprobada)

El revisor independiente encontró 14 problemas antes del lock. Cuatro dejaban
pasar a un consumidor mentiroso o a un mutante roto. Cambios:

- **Toque**: la ventana empieza 100 ms antes de la muestra de verdad. Cada
  paquete mira la IMU en [t − 100 ms, t] y la verdad se muestrea cada ~21 ms:
  en 5 de 54 vuelos el pico de contacto precede a esa muestra (−8 a −1 ms), y la
  fase del LiDAR daba ~14 % de probabilidad de un rojo falso en 44 vuelos honestos.
- **Pulso**: un vuelo perturbado sin evento de fuerza es rojo (antes caía en
  la rama «sin fuerza»); un vuelo sin fuerza con evento de fuerza, también.
- **Distancia**: sin suelo de cobertura, un consumidor que dijera
  `DESCONOCIDO` o paquetes fuera del conjunto en el 95 % de los barridos pasaba.
  Ahora cada barrido utilizable cuenta (indescifrable o `DESCONOCIDO` = fallo) y
  uno no utilizable acierta sólo con `DESCONOCIDO`. La exactitud agregada por
  etapa (0.95), que estaba en el contrato, no se aplicaba; ahora sí.
- **Verdad de distancia**: los fallos honestos eran rayos que rozan la tapa de
  una caja (la verdad pasa 0–46 mm por encima y el LiDAR la toca). Un barrido
  cuya banda cambia moviendo el sensor ±5 cm en vertical es ambiguo. Elegido
  con datos vistos (v3 y desarrollo): declarado post hoc.
- **Certeza**: el texto pasa a la regla implementada (marcadores de los
  registros entregados). Límites declarados: un retraso no es marcador; una
  pérdida se marca en la ventana donde el siguiente registro declara el hueco;
  una fuente que calla del todo no baja `C`; un LiDAR muerto da silencio, no
  `DESCONOCIDO`.
- **Un solo cable**: se cuentan las líneas de stderr y los bytes que el
  consumidor escribe de vuelta en el socket (su stdout); antes sólo se leía la
  última línea. El stderr entero debe ser, byte a byte (hash), la línea JSON
  que el evaluador predice (recuento reconstruido del transcript y paquetes
  recalculados), y el código de salida 0: ni separadores ocultos, ni espacios,
  ni orden de claves, ni tipos (`1.0` por `1`) como canal. El ritmo de lectura
  del consumidor sigue siendo un canal de tiempo, acotado por los límites de
  espera (p99 2 ms, máx 30 ms) y fuera de alcance, como en SIM-3.
- **Sólo sensores**: además de la igualdad byte a byte, la traducción
  alimentada registro a registro debe emitir cada paquete en su barrido y no
  revisar ninguno (sin futuro). La igualdad sola no lo probaba: compara el
  mismo fichero consigo mismo.
- **Mutantes**: un informe ausente o desalineado ya no cuenta como detección;
  hace falta el caso concreto y un vuelo sano.
- **CAM**: se declara estructural. Usa `loop.Agent._slot_for` real; no puede
  fallar con menos de 4097 paquetes distintos, y `navi10_cam` nunca incrementa
  `destroyed`.
- **Lock**: el inventario cubre `nexus0/*.py` y los `navi10_*.py` del repo
  padre; la historia incluye `SENSOR1S-V3-RESULTS.md` (con su adenda).

## Mutantes obligatorios

`constant_percept` (siempre `FUERA`), `imu_blind` (nunca `CAMBIAR`),
`certainty_lie` (siempre `C = 100`), `seq_counter` (contador en `seq`),
`lookahead` (usa el barrido siguiente) y `extra_channel` (añade un campo a la
salida). Cada uno debe poner rojo su caso concreto con el vuelo completo.

## Muestra

La de SENSOR-1S v3, con su canal y su evaluador: A 16 vuelos + 4 controles sin
fuerza; banco (si A pasa) 24 + 6 mutantes. Desarrollo en A libre y conservado
para fijar el estadístico de distancia; se congela antes de validación.
Semillas 20261101 (A) y 20261102 (banco).

## Límites que ya se saben

Sólo dos bandas de distancia aparecen en estos vuelos. «Cerca» sí aparece (mundos
0–3 y 7 en rehearsal, 20–100 % de los barridos), pero el agente todavía no mueve
el dron: la distancia cambia sólo con el despegue y el aterrizaje. El banco usa los 12 mundos de
rehearsal. Un verde significaría traducción física → WSP sin oráculo en SITL;
no percepción de objetos, decisiones, vuelo del agente ni sensores reales.
