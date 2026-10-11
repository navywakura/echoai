# ECHO-5: integración robótica discreta

10 de octubre de 2026. Implementación independiente dentro de ECHO-5;
reutiliza fuentes históricas sin modificarlas. No ejecuta campañas antiguas,
exámenes sellados, vuelos nuevos, LLM ni hardware. No necesita paquetes externos.

## Frontera implementada

`robotics.RoboticsBridge` compone mediante `echo5.legacy.module`:

- `nexus0.compose1_v3.controller.Composer`, con sus bases v2/v1 y `Effects`
  (CAM, T y Q existentes). El controlador no se copia.
- `nexus0.fusion1`: reducción por familias, conflictos, antigüedad y gate basal.
- `nexus0.drone3.contract`: intenciones WSP canónicas de 16 bytes.
- `nexus0.drone3.gates`: admisión independiente del siguiente desplazamiento
  y ruta de regreso por posiciones ya ocupadas.

El evaluador importa `nexus0.compose1_v3.space.Space` sólo al iniciar un
episodio. Entrega al actor el objetivo público y observaciones públicas;
no entrega semilla, condición, mapa, obstáculos privados, distancias del
oráculo ni consecuencias privadas. Construir el actor en un proceso limpio
no importa `Space`. La separación es de interfaz y datos; no es una jaula de
seguridad frente a código Python malicioso.

El prior nuevo contiene dos desplazamientos sintéticos declarados por cada
acción horizontal: este/oeste/norte/sur. Se construye con `Effects.observe_effect`;
no se lee ninguna escuela, memoria, certificado ni calibración histórica.
Q no recibe recompensas de entrenamiento; se informa el prior como sintético,
sin atribuirle aprendizaje desde vuelos. La planificación no escribe en CAM/T/Q.

No se integra aquí el `MissionAgent` completo, batería PX4, supervisor SAFE,
gateway de vuelo, LiDAR/depth físicos ni la proyección de imágenes crudas.
COMPOSE conserva su energía abstracta: desplazamiento de coste 4 y reserva 10.
El gate adicional exige poder volver desde el destino por posiciones ocupadas.

## API

```python
from echo5.budget import Budget
from echo5.robotics import RoboticsBridge, observation_from_scan, run_benchmark

actor = RoboticsBridge([4, 0, 0], budget=Budget(10_000), mode="echo32",
                       journal=None)
# scan es únicamente el resultado público de Space.scan(), nunca el mundo.
observation = observation_from_scan(scan, sequence=0)
response = actor.decide(observation, now_ns=receiver_clock_ns)

report = run_benchmark(seed=40813, cases=24, budget=10_000, journal=None)
```

`response` contiene `action`, `wsp`, `prediction`, `status`, `gate` y trabajo
consumido. Las propuestas aceptadas conservan además plan, candidatos, errores
de predicción y huella del modelo del controlador existente. Un veto conserva
`proposed_wsp` y `proposed_prediction`; la predicción ejecutable es quedarse
en la última posición admitida. STOP es la acción 6, no una orden de aterrizaje
físicamente validada. Antes de la primera observación válida, su predicción
es `None`, porque no se conoce una posición fiable.

`journal` admite el `Recorder` existente y su método `write(kind=..., **facts)`.
Registra observación aceptada, respuesta real, consecuencia del simulador y
resultado. Entrega copias al observador; no lee sus textos ni introduce otro
bus cognitivo. Los eventos rechazados registran la respuesta de parada y su
causa, sin copiar datos arbitrarios de la entrada rechazada. Los diarios pueden
mostrarse con el visor existente; no se añade instrumentación a exámenes.

## Sensores, procedencia y límites

La observación tiene exactamente `schema`, `sequence`, `capture_ns`,
`delivered_ns`, `odometry`, `energy`, `station_observed`, `cells`, `sha256`.
Cada celda tiene `position`, `sources`; cada fuente tiene `source`, `wsp`,
`capture_ns`, `delivered_ns`, `raw_sha256`. Campos adicionales se rechazan.

El hash de fuente enlaza posición, identidad de fuente, WSP y tiempos mediante
SHA-256 del JSON ordenado, compacto y sin NaN. El hash exterior cubre toda la
observación salvo `sha256`. **Son comprobaciones de integridad, no firmas ni
autenticación física.** Un productor que invente datos y hashes coherentes
puede engañar a esta frontera; requeriría un transporte autenticado externo.

- El reloj `now_ns` lo proporciona el receptor. Captura <= entrega <= reloj,
  antigüedad máxima 250 ms inclusiva. Captura de frame y reloj avanzan; la
  secuencia empieza en 0 y aumenta exactamente de uno en uno. No se renuevan
  los tiempos de las fuentes al consultar memoria.
- Máximo 128 celdas por frame, tres fuentes distintas por celda, 256 posiciones
  acumuladas, 64 decisiones aceptadas por misión. Coordenadas enteras entre
  -8 y 8, con z=0; energía entera entre 0 y 1000. Booleanos no son enteros.
- WSP perceptivo canónico: predicado BARRIER, región/época de transporte 0,
  certeza 40 por fuente conocida o 0 para UNKNOWN. No se normaliza otro
  predicado hasta convertirlo accidentalmente en evidencia de paso libre.
- Fuentes permitidas: depth, rgb, lidar. Depth y rgb son la misma familia.
  FUSION requiere dos familias concordantes, y mantiene su ventana relativa
  de 100 ms: fuentes frescas pero demasiado separadas no autorizan movimiento.
- Un movimiento necesita admisión en el frame actual, aunque el controlador
  conserve evidencia todavía fresca del destino. La predicción debe coincidir
  exactamente con la intención WSP y un desplazamiento horizontal de una celda.

Una entrada inválida o caducada genera STOP antes de llamar al controlador;
no cambia su memoria ni consume un número de secuencia. El desbordamiento de
presupuesto genera STOP con `status="budget_exhausted"`. Si el presupuesto
falla durante la construcción, se propaga `BudgetExceeded` y no hay actor.

`observation_from_scan` sólo envuelve lecturas del simulador discreto. No debe
usarse para retimbrar sensores físicos: un adaptador físico futuro debe aportar
la captura real, entrega real, identidad y calibración de sus sensores.

## Costes, controles y auditoría

Un `budget` entero de `run_benchmark` significa **trabajo por caso y por modo**.
Así, 24 casos, tres modos y 10.000 unidades tienen un techo total de 720.000.
Si se pasa un objeto `Budget`, su saldo es un techo total compartido y se
divide en partes iguales entre los episodios. Ambos significados figuran en
`costs.budget_semantics`. Las cargas al registro padre preceden a la operación.

Se cobran inicialización, ocho observaciones del prior, cada scan, recibos,
validación de celdas/fuentes, decisiones, gates, pasos y adjudicaciones. La
búsqueda reserva 32 candidatos antes de llamar al controlador; el informe
también conserva el número de candidatos realmente generado. No se devuelve
la reserva sobrante. Son operaciones lógicas acotadas, no ciclos de CPU,
memoria residente, vatios ni julios. El tiempo de observación no se usa como
presupuesto; importación y escritura del diario no tienen un cargo separado.

Plan fijado antes del banco solicitado por el padre:

| Parámetro | Valor |
|---|---|
| Semilla | 40813 |
| Casos | 24; semilla de caso = 40813 + índice |
| Condiciones | static, dynamic, closed, low_energy, repetidas seis veces |
| Principal | echo32: horizonte 4, hasta 32 candidatos |
| Control 1 | one_step: horizonte 1, mismo techo externo |
| Control 2 | conventional: COMPOSE con Q neutralizada, mismo techo |
| Reinicio | Mundo, CAM/T/Q, evidencia y presupuesto propios por episodio |
| Éxito | reached, posición final = objetivo, marcador observado, cero colisiones y violaciones de reserva |

Los modos reciben el mismo objetivo, generador, semilla, condición, sensores y
acciones disponibles. Las observaciones posteriores pueden diferir porque las
trayectorias difieren. `closed` y `low_energy` no se eliminan del denominador:
una parada segura es fallo de completar la tarea. El prior carece de Q
entrenada, por lo que conventional puede empatar exactamente con echo32.

Cada fila tiene `status`, `budget_exhausted`, `budget_limit`, `cost`, `costs`,
`final_position`, `goal`, `station_observed`, colisiones y violaciones de
reserva. Los tres últimos datos de llegada los produce el evaluador, fuera
del actor. Si no se creó mundo, posición/objetivo son `None`; si no hubo una
observación de la posición final, `station_observed` es `None`. Si no se creó
actor, `model_unchanged` es `None`. Ninguno equivale a una comprobación positiva.
Un caso incompleto tiene `success=False` y permanece en el denominador.

El auditor puede recalcular éxito con esos campos, comprobar cada suma de
costes y techo, los tres conjuntos de filas y las comparaciones emparejadas.
`controls[modo].wins/losses/ties` se expresan desde echo32 frente al control.
`cost` superior suma sólo echo32; `costs.used` suma los tres modos.
El informe es JSON portable y determinista, sin tiempos de pared embebidos.

## Comprobaciones realizadas

TDD: importación roja por módulo ausente; primera implementación con 11 tests
verdes. Dos tests nuevos fallaron por presupuesto dividido incorrectamente
(33 frente a 100) y registro padre todavía en 0 durante trabajo; ambas causas
se corrigieron. La prueba de campos de auditoría falló por ausencia de
`final_position` antes de añadirlos.

Última comprobación específica: **18/18 tests pasan**, incluidos los campos
de auditoría, en 11,95 s bajo Python 3.12.13.

Comprobación unitaria manual: primera decisión de movimiento con dos celdas,
dos sensores por celda y construcción del modelo: **52 unidades**. Esto permite
elegir el techo de 10.000 sin mirar las semillas de confirmación; no garantiza
que cualquier episodio largo quepa.

La fixture de desarrollo de cuatro casos, semilla 20261010 y 10.000 por
caso/modo, produjo:

| Modo | Llegadas | Colisiones | Violaciones de reserva | Trabajo |
|---|---:|---:|---:|---:|
| echo32 | 2/4 | 0 | 0 | 9.244 |
| one_step | 2/4 | 0 | 0 | 8.946 |
| conventional | 2/4 | 0 | 0 | 9.244 |

Trabajo total: 27.434 / 120.000 unidades, 12 episodios. echo32: static 8 pasos,
dynamic 14, closed 50 y regreso a casa, low_energy parada inicial. Costes de
esos cuatro episodios: 1.476, 2.325, 5.314 y 129. Cero agotamientos en los tres
modos. Cuatro empates frente a cada control; no se demuestra ventaja de echo32.
El informe de fixture tardó aproximadamente 3,29 s en este host; no es una
medición de latencia de vuelo. Estas cifras no son el banco de 24 casos.

El banco de confirmación 40813/24 pertenece al ejecutor y auditor del padre;
esta integración no lo ha ejecutado ni ha ajustado umbrales a sus resultados.
No se reabrió ninguna prueba histórica. Se comprobaron 44 fuentes importadas
contra hashes del inventario: cero diferencias. Reinicios con `-I -B`, cwd
`/tmp` y procesos nuevos producen informes JSON iguales, sin importar campañas.

Comandos de comprobación (desde ECHO-5):

```sh
make check
.venv/bin/python -I -B scripts/dev.py test
.venv/bin/python -I -B -c 'import sys, unittest; sys.path.insert(0,"src"); suite=unittest.defaultTestLoader.discover("tests",pattern="test_robotics.py"); sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())'
```

El primer pase global durante trabajo paralelo contó 48 tests correctos y dos
errores de importación ajenos a esta integración: `echo5.concepts` y
`echo5.interaction`, todavía pendientes en ese instante. Una vez incorporados
los módulos paralelos, el último pase global dio **83/83 correctos en 13,49 s**.
`make check` pasó con Python 3.12.13. Las comprobaciones específicas incluyen movimiento del
controlador real, reserva, fallo de predicción, correlación/conflicto/skew,
caducidad exacta, repetición, campos privados, hashes, predicado equivocado,
veto con evidencia en caché, límites, costes y el Recorder heredado.

## Gazebo/PX4: disponibilidad y siguiente prueba propuesta

Inspección sólo de lectura: `gz`, `gazebo` y `px4` no están en PATH. Sí existen
`/usr/bin/podman`, `/usr/bin/bwrap` y el binario
`/home/roger/px4/PX4-Autopilot/build/px4_sitl_default/bin/px4`.
`podman images` muestra `localhost/echoai-sim3-gz:harmonic` y las imágenes
PX4 v1.15.4, gpseph y gpsaccuracy. ID de gpsaccuracy observado:
`5364c865ebf08b1dd19ee7a6a46ca3c3911056269974e7d9db2ced4a74201d27`.
La instalación del sistema encuentra pymavlink y pyulog; no son dependencias
ni prueba de disponibilidad dentro de la `.venv` aislada de ECHO-5.

Hay recursos suficientes para proponer esta comprobación nueva de arranque
SITL, acotada a 45 segundos, con imagen local y directorios de trabajo
efímeros. **Propuesta no ejecutada**; no arma, despega ni valida el puente:

```sh
timeout --signal=TERM --kill-after=5s 45s \
  podman run --rm --pull=never --network=none --read-only \
  --tmpfs /tmp:rw,exec --tmpfs /run:rw --tmpfs /root:rw \
  --tmpfs /out:rw,exec --workdir /out \
  -e HEADLESS=1 -e PX4_SYS_AUTOSTART=4001 \
  -e PX4_SIM_MODEL=gz_x500 -e PX4_GZ_MODEL=x500 -e PX4_GZ_WORLD=default \
  -e PX4_GZ_MODELS=/opt/PX4-Autopilot/Tools/simulation/gz/models \
  -e PX4_GZ_WORLDS=/opt/PX4-Autopilot/Tools/simulation/gz/worlds \
  -e GZ_SIM_RESOURCE_PATH=/opt/PX4-Autopilot/Tools/simulation/gz/models \
  5364c865ebf08b1dd19ee7a6a46ca3c3911056269974e7d9db2ced4a74201d27 \
  /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4 \
  /opt/PX4-Autopilot/build/px4_sitl_default/etc \
  -s etc/init.d-posix/rcS -i 0 -d -w /out
```

El timeout termina un proceso que normalmente sigue ejecutándose; su salida
124 no certifica un fallo de vuelo. Habría que inspeccionar reloj Gazebo y
telemetría PX4 para evaluar ese arranque. Un ensayo de vuelo ECHO-5 posterior
necesita adaptador de sensores crudos, transporte y supervisor, con PX4 a cargo
de estabilización y failsafes. Las fixtures discretas de este documento no
acreditan vuelo, aerodinámica, sensores reales, HIL, jaula ni consumo físico.
