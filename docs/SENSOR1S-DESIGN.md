# SENSOR-1S — sensores simulados con tiempo, ruido, latencia, pérdida y fuente

Estado: **borrador de contrato**, pendiente de aprobación de Roger. Sin código,
sin lock, sin vuelos. Orden ECHO-3: tercer tajo, tras SIM-3 y FLIGHT-1S (verde
bajo v6). Trabajo sin Codex: Claude diseña e implementa; Roger aprueba este
contrato; un revisor independiente (subagente sin este contexto) intenta
romper código, denominadores y certificado antes del lock.

## Pregunta única

¿Los sensores simulados del X500 —IMU, cámara RGB, cámara de profundidad y
LiDAR 2D— llegan al consumidor aislado como registros con **fuente, tiempo de
captura, latencia, pérdida, validez y modelo de ruido explícitos**, sin verdad
del simulador, y esos campos coinciden con lo que ocurrió en el lado privado?

No pregunta si el agente entiende nada. Traducir observaciones a WSP es
GROUND-1. Aquí el consumidor es un probe instrumental, como en SIM-3.

## Lo que ya se midió (sonda de ingeniería, 2026-09-11)

En la imagen PX4 v1.15.4, Gazebo Harmonic headless renderiza por CPU: cámara
RGB 320×240 a 10 Hz (27 colores distintos), profundidad 160×120 con mínimo
2.500 m frente a una cara situada a 2.5 m, `gpu_lidar` de 360 rayos con 22
impactos en una caja de 1 m a 2.5 m (±11°, geométricamente correcto) y mínimo
2.500 m, e IMU a ~100 Hz con 9.8 m/s² en reposo. Sellos en tiempo de
simulación. No hay LiDAR de fábrica en los modelos PX4; OakD-Lite (1920×1080 y
640×480 a 30 Hz, sin ruido declarado) es demasiado pesado para CPU.

## Invariantes heredados

WSP 16 B, único bus cognitivo; SENSOR-1S no escribe WSP, CAM, T ni Q
(`wsp_writes=0`, `cortex_calls=0`). El canal de sensores es transporte, no
thought-bus. La verdad del simulador vive en el lado privado (SIM-3). PX4
conserva estabilización y failsafes; la configuración de vuelo es la de
FLIGHT-1S v6 sin cambios. Todo resultado dice `simulated_sensors`.

## Cuerpo: `x500_sensor1s`

X500 de fábrica (IMU 250 Hz con ruido y deriva declarados en su SDF, barómetro,
navsat) más, **sobre `base_link` sin enlaces, masa ni geometría nuevas**:

| Fuente | Tipo | Resolución | Frecuencia | Ruido declarado |
|---|---|---|---:|---|
| `imu` | imu (de fábrica) | — | 250 Hz | el del SDF PX4 |
| `rgb` | camera | 320×240 RGB8 | 15 Hz | ninguno |
| `depth` | depth_camera | 160×120 R_FLOAT32 | 15 Hz | gaussiano σ = 10 mm |
| `lidar` | gpu_lidar horizontal | 360 rayos, 0.1–30 m | 10 Hz | gaussiano σ = 10 mm |

Sin masa añadida el vuelo es dinámicamente el de v6; se comprueba igualmente.
El SDF del modelo vive en el repositorio y entra en el inventario del lock.

## Registro y canal

Cada mensaje de sensor que cruza al consumidor es una trama con cabecera JSON
(≤ 512 B, sin campos extra) y carga binaria (≤ 256 KiB):

```text
v=2  source  seq  capture_ns  delivered_ns  gap  status  noise_ref
     shape  format  payload_len  payload_sha256
```

- `capture_ns`: sello del propio sensor (cabecera Gazebo), tiempo de simulación.
- `delivered_ns`: tiempo de simulación observado cuando el supervisor la envía.
- `seq`: contador por fuente del lado privado; `gap`: registros perdidos desde
  el anterior entregado. `status ∈ {ok, stale, invalid}`.
- Prohibido: nombre de mundo, paquete, split, seed, entidades, poses reales,
  AABB, roles. El tick v1 de SIM-3 no cambia.

El consumidor, en la jaula `bwrap` de SIM-3, valida esquema y hash, cuenta
huecos, obsoletos y latencias por fuente y devuelve sus recuentos por el canal
unidireccional al evaluador. El evaluador los compara con el registro crudo
privado.

## Variable manipulada: fallos inyectados en el lado privado

El inyector actúa entre Gazebo y el canal, nunca sobre la física. Calendario
fijado por semilla antes de volar, invisible al consumidor:

| Fallo | Efecto | Respuesta correcta |
|---|---|---|
| `drop` | se retienen k registros de una fuente | `gap` suma exactamente k |
| `delay` | se retrasan d ms de simulación | latencia medida = base + d (±1 paso) |
| `freeze` | se repite la carga y el sello anteriores | `status=stale` en cada repetición |
| `corrupt` | bytes alterados tras calcular el hash | `status=invalid` |

## Criterios verdes (todos, en cada etapa)

| Grupo | Rojo si |
|---|---|
| Ejecución | falta un vuelo o firma PX4 (regla de reinicio pre-tratamiento v6) |
| Esquema | un registro incumple la cabecera o lleva un campo prohibido |
| Tiempo | `capture_ns` ≠ sello crudo, o no monótono por fuente, en cualquier registro |
| Tiempo causal | en un perturbado, el inicio del pulso de 7 N en la IMU dista del instante privado de la wrench más de un periodo IMU (4 ms) |
| Pérdida | `gap` reportado ≠ pérdidas inyectadas + naturales privadas, por fuente y episodio |
| Latencia | un `delay` no se refleja en ±1 paso, o la P99 limpia supera la cota fijada en el lock |
| Validez | un `freeze` sin `stale`, un `corrupt` sin `invalid`, o una marca en un registro limpio |
| Fuente | una carga atribuida a otra fuente (hash contra el registro crudo) |
| Ruido | IMU en reposo: σ por eje fuera de [0.8, 1.25]× lo declarado. LiDAR y fila central de profundidad frente a rayos trazados contra la geometría privada: |sesgo| > 10 mm o σ fuera de [0.8, 1.25]× 10 mm |
| Aislamiento | autocomprobación de la jaula falla o un canario de verdad aparece en la transcripción |
| Mutantes | alguno aceptado |
| Congelado | código, historia o protocolo cambian |

RGB no tiene comprobación de ruido contra verdad; sólo tiempo, pérdida,
validez y fuente. Se declara como límite. La cota de latencia limpia se fija
con datos de desarrollo en A y queda en el lock antes de validación.

## Mutantes obligatorios (el auditor debe rechazarlos)

`hide_loss` (pierde sin `gap`), `delivery_stamp` (sella con la entrega),
`wall_clock` (sella con reloj real), `source_swap` (intercambia profundidad y
LiDAR), `leak_pose` (añade la pose real a la cabecera), `fresh_stale` (no
marca el congelado), `noise_lie` (declara σ menor que la aplicada), más las
mutaciones de informe de v6 (omitir, cambiar medida, verde inventado, etc.).

## Muestra

- Desarrollo en A: libre, conservado, no cuenta.
- Validación A: 4 mundos × 2 repeticiones × {limpio, con fallos}, todos
  perturbados = 16 vuelos + 4 controles limpios sin fuerza.
- Banco (sólo si A pasa): 12 mundos rehearsal × {limpio, con fallos} = 24 vuelos
  + mutantes. Semillas 20261001 (A) y 20261002 (banco).
- Mismo coordinador robusto de v6: agregación sin excepciones, reinicio
  pre-tratamiento, `start` desacoplado, sin reintentos tras el heartbeat.

## Enmienda previa al lock (aprobada por Roger, 2026-09-11)

Fijada con vuelos de desarrollo en A (`lab/sensor1s/dev/`, conservados, no
cuentan), antes de cualquier vuelo de validación:

| Punto | Contrato inicial | Lock | Base |
|---|---|---|---|
| Inicio del pulso en la IMU | ≤ 1 periodo (4 ms) | 0–12 ms (3 periodos) | 8 pulsos: 4, 1, 3, 3, 5, 2, 1, 1 ms; Gazebo aplica la wrench 1–5 ms tras el mensaje y la IMU muestrea cada 4 ms. Con 4 ms, un vuelo de 8 caería rojo sin error de sello. El sello exacto se comprueba aparte |
| P99 limpia captura→entrega | «cota del lock» | IMU 10, RGB 50, depth 60, LiDAR 150 ms | observado 1 / 20 / 30 / 67 ms; es sobre todo tiempo de render |
| Registro retenido (`delay`) | ±1 paso | sale ≤ 2 ms tras max(llegada, liberación) | observado ≤ 1 ms |
| Ruido | — | ≥ 200 residuos por episodio para juzgarlo; ≥ 1000 por etapa, agrupados | reposo asentado: 1368–5550 por episodio |

Precisiones de implementación, sin cambio de criterio: PX4 v1.15 elige el
modelo por `PX4_SIM_MODEL`; el runner de SENSOR-1S lo fija sólo en el entorno
de PX4. El reposo excluye la caída tras el spawn (cuerpo quieto 0.5 s a ±1 mm).
Una repetición congelada oculta el registro real que sustituye: cuenta en `gap`
del siguiente registro genuino. `invalid` lo marca el consumidor por hash.
La latencia medida es la edad del dato cuando el supervisor lo envía.

Desarrollo: 3 vuelos limpios o con fallos y 7 mutantes. Los recuentos del
consumidor coincidieron con lo inyectado en cada fuente; el control sin
fuerza no dio marcas; cada mutante puso rojo su grupo objetivo con el vuelo
completo.

## Segunda enmienda previa al lock (aprobada por Roger, 2026-09-11)

Un revisor independiente (subagente sin el contexto del implementador) atacó
el evaluador antes del lock con adaptadores mentirosos reconstruidos desde la
evidencia de desarrollo. Reprodujo falsos verdes reales: latencia tomada del
propio adaptador (entregas «antes» de que el tap recibiera el mensaje), verdad
filtrable por campos permitidos (`shape`, `format`, `noise_ref`), `noise_ref`
juzgado sólo en el primer registro, duplicados y registros fabricados
aceptados y pérdida silenciosa al principio o al final del flujo. Todos se
reprodujeron y hoy son pruebas de regresión.

Cambios de método, sin mover umbrales salvo los dos aprobados:

- El evaluador ya no recorre el registro del adaptador. Cada registro de la
  transcripción del host se empareja con exactamente una captura cruda del tap
  por (fuente, `capture_ns`, hash). Toda captura que el inyector no retiró se
  entrega una vez. Los campos que no son medidas quedan fijados por fuente
  (`noise_ref`, `shape`, `format`, `payload_len`, `seq` contiguo). El recuento
  del consumidor se recalcula desde la transcripción y debe coincidir.
- Las inyecciones deben coincidir exactamente con el calendario planificado.
- **Aprobado:** para todo registro, espera = entrega − max(llegada al tap,
  liberación) ≥ 0, p99 ≤ 2 ms por fuente y máximo ≤ 30 ms. Sustituye a
  «retenido ≤ 2 ms»: el host se detiene hasta 23 ms en el 0,1 % de los
  registros y un retenido llegó a 2,0 ms. Un canal de tiempo encubierto por
  debajo de estas cotas queda fuera de alcance, como en SIM-3.
- **Aprobado:** σ de LiDAR y profundidad = dispersión temporal de cada haz en
  reposo; sesgo = media de haz contra la geometría trazada. El error
  geométrico sistemático por haz (3–9 mm según distancia e incidencia)
  inflaba el σ de residuos hasta 1,33× sin ser ruido. Banda [0.8, 1.25] y
  |sesgo| ≤ 10 mm sin cambios.
- La pérdida natural cuenta todos los intervalos; un mutante sólo se da por
  detectado si su caso concreto cae rojo y su gemelo honesto del mismo mundo
  pasa; `run()` escribe siempre el informe; el auditor re-escanea canarios en
  la transcripción y guarda la autocomprobación de la jaula.
- Límite declarado: el banco usa los 12 mundos rehearsal, incluidos los 4 de
  A donde se fijaron los números. No es un examen reservado.

## Qué significaría un verde

Que en SITL estos cuatro sensores simulados llegan al consumidor aislado con
metadatos correctos y verificables, fallos inyectados visibles y sin verdad
filtrada. No significa sensores físicos, calibración real, percepción, WSP ni
autonomía echoAI.
