# DRONE-3 — resultados (SITL)

2026-09-20. Contrato prospectivo: [DRONE3-DESIGN.md](DRONE3-DESIGN.md), escrito
antes de abrir B. Hardware: [traspaso](DRONE3-HARDWARE-HANDOFF.md).
**Este informe cubre sólo SITL.** No hay placa, dron, sensores reales ni jaula:
`drone3_hil_green` y `drone3_cage_green` son `false` y por tanto `drone3_green`
también. ECHO-3 sigue en 14/15 y DRONE-METAVERSE sigue cerrado.

## Qué se ejecuta en un vuelo

Una sesión PX4 v1.15.4 + Gazebo Harmonic por vuelo, con la imagen congelada de
FLIGHT-1S v6 y el X500 con la montura de COMPOSE-1. Dentro de la misma sesión:
despegue y armado del operador, relevo, y después, por cada paso, esta cadena:

```text
observación asentada (LiDAR, 4 profundidades, RGB, estimador PX4, tensión de batería, ≤80 ms)
  → agente enjaulado: percepción congelada de COMPOSE → FUSION con la calibración C1
  → POWER decide continuar/volver/aterrizar → COMPOSE compone la ruta
  → WSP de 16 B + predicción publicada
  → gate epistémico (dos familias, C≥80, misma observación)
  → gate energético (paso + retorno por celdas recorridas + aterrizaje + reserva)
  → supervisor SAFE (salud, lease, enclavamiento) → gateway de celdas
  → MAV_CMD_DO_REPOSITION → ACK ≠ llegada → tres muestras asentadas
  → observación siguiente → atribución → replanificación
```

Al final: retorno por celdas ya ocupadas, aterrizaje normal y desarme; o, tras
un veto, PX4 aterriza por su failsafe de enlace sin orden externa.

## Desarrollo (A)

A1 (12 vuelos) sólo sirvió para medir consumo. `calibrate` ajustó la tabla
POWER con 129 recibos, en ‰ de la franja utilizable del pack simulado:

| Fase | n | Nominal | Máximo | Cota |
|---|---:|---:|---:|---:|
| paso de misión | 79 | 14 | 17 | 22 |
| paso de retorno | 41 | 15 | 17 | 22 |
| aterrizaje | 9 | 21 | 27 | 34 |

A2 repitió las tres salas con esa tabla y el código definitivo: **12/12 en
verde**, 6/6 misiones factibles alcanzadas, 3/3 abortos correctos por reserva y
3/3 fallos contenidos; cero colisiones, holgura mínima 1.274 mm, reserva final
mínima 175 ‰, restricciones duras a cero. Llegada real p50/p99/máx =
169/407/417 mm. Latencia del agente p50/p99 = 62/87 ms. Memoria del agente
26 MB.

### Lo que A corrigió antes de congelar

1. **Frescura del latido de PX4.** Con RTF 0,48–0,89 la regla de 2 s en tiempo
   de pared heredada de PX4-1/SAFE-1 rechazaba latidos vivos y vetaba sin causa.
   DRONE-3 la mide en tiempo simulado.
2. **Energía.** PX4 SITL no publica corriente ni capacidad. Se usa la carga
   simulada entre el 20 % y el 100 % del pack, leída de la tensión; el 20 %
   inferior queda para los umbrales propios de PX4.
3. **Batería y desarme.** PX4 rellena el pack simulado al desarmar y la tensión
   filtrada sube antes de que el latido lo muestre: la reserva al tocar suelo es
   el mínimo de esa ventana, no la última muestra.
4. **Revisión independiente antes del lock.** Un revisor en sólo lectura
   encontró, entre otros: que B contenía la geometría de los pilotos; que la
   contradicción se disparaba por reloj sin evidencia de que el agente hubiera
   visto la abertura; que la prueba de manipulaciones no podía fallar; que la
   auditoría no ataba cada propuesta a la intención del agente; que la custodia
   del lock era incompleta; que las restricciones duras sólo podían dar cero; y
   que el umbral de llegada real era incompatible con el criterio de PX4-1.
   Todo se corrigió en A y está en el contrato.

Lock: `094bc35fe2a16c7a3410208ac0cc3c44dfd981896c1b397286ab66d51a38a10c`.
Salas B: 20267001, 20267003, 20267004 (la 20267002 se descarta por compartir
geometría con los pilotos). Salas C: 20268001, 20268003, 20268004.

## Validación (B) y confirmación (C)

B voló una vez con el lock; C se abrió una sola vez, después, atada al resumen
de B (`f23ccb87…`). **Las dos etapas salen 12/12.**

| Medida | B | C |
|---|---|---|
| Vuelos correctos | 12/12 (Wilson 95 % [0,758; 1]) | 12/12 |
| Misiones factibles alcanzadas | 6/6 | 6/6 |
| Abortos correctos por reserva | 3/3 | 3/3 |
| Fallos contenidos | 3/3 | 3/3 |
| Desplazamientos ejecutados | 147 | 133 |
| Inspecciones por giro | 0 | 4 |
| Colisiones / muestras inseguras | 0 | 0 |
| Holgura mínima al obstáculo | 1.247 mm | 1.259 mm |
| Failsafe de PX4 en vuelos sin fallo | 0 | 0 |
| Reserva al tocar suelo (mínimo) | 180 ‰ | 140 ‰ |
| Llegada real p50/p99/máx | 200 / 357 / 401 mm | 186 / 360 / 423 mm |
| Error del estimador en la llegada (máx) | 216 mm | 204 mm |
| Aterrizaje en casa p50/máx | 191 / 307 mm | 199 / 306 mm |
| Veto tras el fallo | 207 / 1.009 / 1.009 ms | 167 / 1.010 / 1.017 ms |
| Desarme tras el veto | 21,1–23,1 s | 19,9–30,7 s |
| Decisiones descartadas por evidencia vieja | 3 | 3 |
| Edad máxima de la evidencia al proponer | 169 ms | 175 ms |
| Sondas de rechazo bloqueadas | 228/228 (19 por vuelo) | 228/228 |
| Restricciones duras | todas 0 | todas 0 |

Latencias, memoria y cadena causal:

| Medida | B | C |
|---|---|---|
| Decisión del agente p50/p95/p99 | 62,2 / 85,3 / 89,9 ms | 63,3 / 83,3 / 90,2 ms |
| Observación → envío p50/p99 | 66 / 89 ms | 67 / 90 ms |
| Envío → ACK p50/p99 | 20 / 32 ms | 21 / 48 ms |
| ACK → llegada confirmada p50/p99 | 5.152 / 6.491 ms | 5.157 / 6.150 ms |
| Memoria máxima del agente | 26,4 MB | 26,2 MB |
| Celdas en memoria espacial (máx) | 22 | 22 |

**Atribución** (publicada, no es criterio): el movimiento propio se atribuye
bien en 144/144 pasos de B y 130/130 de C. Las marcas de cambio externo son
ruidosas: 102 en B, de las cuales 37 caen tras el cambio de mundo, y 79 en C,
30 tras el cambio. Es decir, el agente marca cambios externos también donde no
los hay, por variación del ángulo de visión. Se informa como está.

## Controles, mutantes y manipulaciones

Ningún control se vuela: todos se calculan sobre las observaciones, la batería
y la salud grabadas.

| Control | B | C |
|---|---|---|
| Enlace que toma el ACK por llegada: llegadas prematuras | 147/147 | 133/137 |
| Distancia real al objetivo en el instante del ACK (mediana) | 3.041 mm | 3.041 mm |
| Planificador sin evidencia: propuestas a celda ocupada real | 51, todas bloqueadas por el gate | 43, todas bloqueadas |
| Calibración C1 coherente con el cuerpo (estimador de C1) | 12/12 vuelos | 12/12 |
| Admisiones que cambiaría una montura errónea (1, 0) | 947 de 1.417 celdas | 963 de 1.437 |
| Decisiones en que el porcentaje fijo difiere del coste | 13 | 14 |
| SAFE sin vida del agente: ¿vetaría el cuelgue? | no | no |
| SAFE sin enclavamiento: sondas de recuperación admitidas | 2 por vuelo de fallo | 2 |
| Gemelo funcional de las mismas salas: Q reactiva alcanza | 0/3 | 0/3 |
| Gemelo funcional: completo y horizonte uno alcanzan | 3/3 y 3/3 | 3/3 y 3/3 |

Horizonte uno diverge del completo en 4 de 9 vuelos de B y 4 de 9 de C; la Q
reactiva diverge en casi todos, a menudo en la primera decisión. En el gemelo
funcional el completo llega en 8, 6 y 6 pasos donde horizonte uno necesita 20,
10 y 6. **No se reclama superioridad de velocidad**: la hipótesis es funcional.

**Mutantes**, todos detectados: pasarela sin TTL, sin geocerca, con el ACK como
llegada y sin secuencia (12/12 vuelos cada uno); gate que admite lo desconocido
y gate sin reserva (12/12); supervisor sin gate epistémico y sin gate energético
(12/12); supervisor sin enclavamiento (3/3 vuelos de fallo) y sin vida del
agente (2/2 vuelos de cuelgue); y un agente distinto —Q reactiva— que diverge de
las respuestas grabadas en los 6 vuelos factibles.

**Manipulaciones**, las ocho rechazadas por la propia auditoría:

| Manipulación | La auditoría la delata por |
|---|---|
| WSP de la intención | `proposal_is_not_the_intention`, `relay_0` |
| ACK alterado | `ack_replay`, `false_arrival` |
| Observación omitida | `agent_replay`, `ack_replay` |
| Propuesta duplicada | `duplicate_proposal` |
| Tensión de batería, con el diario recalculado | `agent_replay_0`, `battery_binding` |
| Propuesta sustituida con objetivo coherente | `proposal_is_not_the_intention` |
| Un byte del ULog | `ulog_hash` |
| Pose privada desplazada | `arrival_not_physical`, `collision_envelope` |

## Certificado

`lab/echo3_drone3_report.json`, certificado
`c44402dffce9f3809b0a6ed3145d9e6e6f7c8c9b7451fe1cf0811e02a7cd2e03`, lock
`094bc35fe2a16c7a3410208ac0cc3c44dfd981896c1b397286ab66d51a38a10c`.

```json
{"custody": true, "drone3_sitl_green": true, "evidence_valid": true,
 "hard_constraints_zero": true, "manipulations_rejected": true,
 "mutants_detected": true, "probes_blocked": true,
 "drone3_hil_green": false, "drone3_cage_green": false, "drone3_green": false}
```

Custodia comprobada en la certificación: los resúmenes de B y C siguen
idénticos a los del cierre, ambos bajo el mismo lock, y C se abrió después de un
B verde.

**Segunda auditoría, en proceso nuevo y sólo lectura:** reconstruye el informe
entero desde los datos crudos y reproduce el mismo certificado,
`reproduced: true`, `c44402df…`.

**El árbol previo está intacto:** los 41.606 ficheros inventariados antes de
empezar DRONE-3 siguen byte a byte iguales, sin ninguno perdido
(`lab/drone3/preflight/`, inventario `0eace362…`). Comprobado antes de
actualizar los documentos de estado, que sí cambian.

### Enmienda 1 al lock

Al certificar, `copytree` falló al copiar una carpeta de vuelo: PX4 deja
enlaces simbólicos rotos en `out/wd`. La copia ahora conserva los enlaces como
enlaces. Es una corrección del arnés: no toca runner, agente, puertas,
supervisor, pasarela, protocolo, auditor ni criterios, no repite ningún vuelo y
no reescribe evidencia. Queda registrada en `lab/drone3/amendments.json` con
motivo, alcance, diff y hashes antes y después, y el informe la publica.

## Las auditorías anteriores siguen en pie

Ejecutadas en sólo lectura con DRONE-3 ya en el árbol:

| Hito | Resultado |
|---|---|
| PX4-1 | válida, `342ca3aa…` |
| SAFE-1 v2 | válida, `eecb77b8…` |
| POWER-1 | válida, `6a05ad4c…` |
| HOST-1 | válida, `18d4a4fa…` |
| FUSION-1 | ejecutada, salida 0 |
| COMPOSE-1 v4 | válida, sin hallazgos |
| TRANSFER-3 | los dos manifiestos de campaña, intactos |
| CAUSE-1 | **no arranca**: «frozen implementation changed» |

El caso de CAUSE-1 no lo causa DRONE-3. Sus 305 entradas congeladas siguen
byte a byte iguales, pero su verificador expande el inventario a todo `nexus0`,
y hoy hay 109 ficheros de más: 52 de TRANSFER-3, 18 de DRONE-3, 11 de SAFE-1,
9 de HOST-1, 8 de POWER-1, 8 de PX4-1 y 3 de SAFE-1 v2. Sin DRONE-3 seguiría
fallando igual. Es el defecto que PX4-1 ya documentó: no se reescribe aquel lock
ni su certificado.

## Límites

- Simulación: mundo estático salvo la intervención declarada, sensores y batería
  simulados, celdas de 3 m y vuelo a altura fija. No acredita hardware, HIL,
  vuelo real ni DRONE-METAVERSE.
- La energía es carga simulada que baja con el tiempo armado, no julios ni
  consumo medido.
- La hipótesis de coordenada de la estación es exacta y delata el eje de la
  sala; no se prueba búsqueda con hipótesis errónea.
- HOST-1 no participa; DYNAMIC-1 y PATTERN-1R no se declaran integrados.
- La calibración C1 aplicable a este cuerpo es la identidad; su canal se
  demuestra vivo por control, no por un desplazamiento distinto de cero.
- La percepción congelada de COMPOSE no distingue «celda no vista» de «celda
  bloqueada» cuando la pared llena la celda.
- Tres vuelos por condición y etapa: los intervalos son descriptivos y no
  estiman fiabilidad de producción.
