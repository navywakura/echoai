# ECHO-3 — revisión de estado del 14 de septiembre de 2026

**8 de 15 hitos con certificado verde en su alcance software; 7 pendientes.** ECHO-1 y
ECHO-2 conservan sus cierres. Este recuento de hitos no representa porcentaje
de esfuerzo ni cierra la validación física: no hay hardware en el laboratorio.

## Estado completo y orden de trabajo

Los números identifican los quince hitos del contrato, no versiones de código.
DYNAMIC-1 se ha adelantado respecto al orden inicial por el fallo de PATTERN-1R.

| ID | Hito | Estado comprobado | Qué queda o qué demuestra |
|---:|---|---|---|
| 1 | SIM-3 | ✅ Verde | Mundos declarativos, física Gazebo y aislamiento; no conducta autónoma |
| 2 | FLIGHT-1 / FLIGHT-1S | ✅ Software: v6 | PX4 despega, mantiene, recupera y aterriza; no vuelo decidido por echoAI ni hardware |
| 3 | SENSOR-1 / SENSOR-1S | ✅ Software: v3 | IMU, RGB, profundidad y LiDAR con procedencia, tiempos y fallos; límites de evaluación LiDAR publicados |
| 4 | GROUND-1 | ✅ v2 | Traducción física → WSP en consumidor aislado; no reconocimiento de objetos ni integración conductual completa |
| 7 | DYNAMIC-1 | ✅ v2 software | 29 vuelos; 250 comprobaciones válidas; seguimiento de la normal de una cara desde hover, no navegación |
| 5 | PATTERN-1R | ✅ v4 software | 28 vuelos; 242 comprobaciones válidas; dos familias LiDAR, aprendizaje/examen por replay; no navegación integrada |
| 6 | FUSION-1 | ✅ Funcional y replay reducido | 864 episodios + 240 ventanas de doce vuelos anteriores; procedencia, caducidad y conflicto; no navegación integrada |
| 8 | COMPOSE-1 | ✅ v4, segunda auditoría válida | 6.144 misiones funcionales; ventaja de movimientos frente a horizonte uno en B/C. 32 vuelos PX4 decididos por WSP; completo 6/6 metas, Q 0/6; energía abstracta |
| 9 | CAUSE-1 | ❗ Plan | Atribuir efecto propio frente a cambio externo mediante controles emparejados |
| 10 | PX4-1 | ❗ Plan | Conectar decisiones del agente a objetivos acotados, con gate y autoridad PX4 |
| 11 | POWER-1 | ❗ Plan | Coste previsto de misión, retorno, aterrizaje y reserva; abandono oportuno |
| 12 | SAFE-1 | ❗ Plan | Contención integrada de fallos de sensores, procesos, comunicaciones y propuestas |
| 13 | HOST-1 | ❗ Plan | Signos y silencio con consecuencias observadas de una fuente, no recompensa directa del botón |
| 14 | TRANSFER-3 | ❗ Plan | Transferencia conductual A→B/C frente a scratch, sin mapa ni identidad del mundo y con aprendizaje congelado |
| 15 | DRONE-3 | ❗ Plan; tramo físico pendiente de hardware | Misión integrada, trazabilidad, SITL y posteriormente HIL/jaula |

Los siete hitos pendientes siguen como alcance de roadmap sin cierre propio
localizado. Tener componentes reutilizables de ECHO-1/2 o el ejecutor PX4 de
COMPOSE no los cierra. Siguiente: CAUSE-1.

## Qué versión utilizar

| Familia | Historial conservado | Referencia actual |
|---|---|---|
| FLIGHT-1S | v1/v2 rojas; v3 desarrollo; v4 interrumpida roja; v5 no cerró y su resumen tiene `evidence_valid=false` | [v6 verde](FLIGHT1S-V6-RESULTS.md), `nexus0/flight1s_v6/`, `lab/echo3_flight1s_v6_report.json` |
| SENSOR-1S | v1 roja por latencia; v2 roja por evaluación de ruido LiDAR | [v3 verde](SENSOR1S-V3-RESULTS.md), `nexus0/sensor1s_v3/`, `lab/echo3_sensor1s_v3_report.json` |
| GROUND-1 | v1 roja por carrera temporal en el emisor | [v2 verde](GROUND1-V2-RESULTS.md), `nexus0/ground1_v2/`, `lab/echo3_ground1_v2_report.json` |
| PATTERN-1R | v1/v2/v3 rojas conservadas; v4 verde | [v1](PATTERN1R-RESULTS.md), [v2](PATTERN1R-V2-RESULTS.md), [v3](PATTERN1R-V3-RESULTS.md), [v4 verde](PATTERN1R-V4-RESULTS.md), `nexus0/pattern1r_v4/`, `lab/echo3_pattern1r_v4_report.json` |
| DYNAMIC-1 | [v1 roja](DYNAMIC1-RESULTS.md): A 10 vuelos, banco no autorizado | [v2 verde](DYNAMIC1-V2-RESULTS.md), `nexus0/dynamic1_v2/`, `lab/echo3_dynamic1_v2_report.json`; v1 y desarrollo conservados |
| FUSION-1 | Primera cadena funcional y replay reducido, verde | [Resultados](FUSION1-RESULTS.md), `nexus0/fusion1/`, `lab/echo3_fusion1_report.json` |
| COMPOSE-1 | v1 cinemática roja; v2/v3 B rojos válidos, C sin abrir; todos conservados | [v4 verde](COMPOSE1-V4-RESULTS.md), banco `nexus0/compose1_v4/`, agente congelado `nexus0/compose1_v3/`, `lab/echo3_compose1_v4_report.json` |

Los sufijos no significan que haya que ejecutar todas las versiones antes de
avanzar. Las versiones antiguas conservan evidencia y dependencias importadas;
no deben borrarse. Un diseño aprobado, tests verdes o un replay favorable
tampoco equivalen a una cadena nueva aprobada.

## GROUND-1 ya está antes de PATTERN-1R

El propio diseño PATTERN-1R parte de GROUND-1 v2. No hace falta implementar
GROUND-1 desde cero después de PATTERN: ya cerró A 16+4 y banco 24+6.
Su resultado es acotado: 21 233 barridos juzgados acertados, 0 entregas antes
de la llegada en 739 915 envíos y traducción a WSP. La CAM comprobada es
estructural; no acredita todavía el loop completo aprendiendo a pilotar.

PATTERN-1 de **ECHO-2** y PATTERN-1R de **ECHO-3** son tareas distintas.
La memoria ya existente se reutiliza, pero no demuestra identidad visual
entre vistas de un objeto físico. El desarrollo original de PATTERN-1R falló esa pregunta: seis mundos,
quince ajustes, mejor media de acierto 0.407 y colapso de familias persistente.
La revisión posterior encontró además defectos de alineación y del juez;
esas cifras históricas no son comparables directamente con v4. V4 sí cerró
su banco de dos familias LiDAR, con 94,35 % de acierto en el examen.
Los vuelos de reconocimiento son guionizados por el arnés, aunque los ejecute
PX4; no certifican navegación autónoma de echoAI ni PX4-1.

## Por qué ahora DYNAMIC-1 y qué aún no resuelve

DYNAMIC-1 v1 confundía cambios del punto de una silueta con velocidad real.
Falló uno de sus diez vuelos de A: detección 0.684. V2 sigue la normal y la
distancia de una cara plana. Existe desarrollo en seis mundos móviles, dos
quietos y siete mutantes; también material anterior a la enmienda 3.
**Actualización posterior a la revisión inicial:** Roger autorizó la ejecución
el 2026-09-14. La cadena v2 cerró verde: 29 vuelos, 250 comprobaciones sin
hallazgos, siete mutantes y siete manipulaciones detectados. Certificado
`c9cf5675…`; [resultados](DYNAMIC1-V2-RESULTS.md).

La tabla válida del diseño es la de la enmienda 3, no la propuesta inicial de
mediana de desplazamientos, que se descartó. Esa revisión cambia límites y
evaluación: predicción en componente normal a la cara, p95 hasta 350 mm y
posición juzgada por mediana hasta 500 mm. Se conservan limitaciones de colas,
muestras pequeñas y mundos ya usados para ajustar. Un replay verde de v1
con ese evaluador es desarrollo, no confirmación independiente.

El cierre de v2 no demuestra por sí solo seguimiento general con
oclusiones y ego-movimiento: su banco mueve una pared con velocidad constante
y observa la componente perpendicular. PATTERN-1R v4 cerró sus propias
condiciones en vuelos nuevos; ninguno de los dos bancos demuestra seguimiento
general con oclusiones y movimiento propio.

Orden operativo:

```text
GROUND-1 v2 cerrado
→ DYNAMIC-1 v2 cerrado
→ PATTERN-1R v4 cerrado
→ FUSION-1 cerrado
→ COMPOSE-1 v4 verde → CAUSE-1 siguiente → PX4-1 → POWER-1
→ SAFE-1 → HOST-1 → TRANSFER-3 → DRONE-3
```

## Límites del cierre y trabajo sin hardware

El PC permite seguir implementando y validando la parte SITL. HIL, jaula,
sensores físicos, electrónica de vuelo y AKD1500 siguen pendientes; una
simulación verde no los sustituye. Los verdes FLIGHT/SENSOR son los sufijos
**1S**. El contrato final DRONE-3 todavía incluye HIL y jaula: ECHO-3 no puede
declararse completamente cerrado en ese alcance sólo con el PC.

Los mundos A/B/C rehearsal de infraestructura son públicos; no equivalen al
C sellado del examen conductual de TRANSFER-3. No se ha localizado una
confirmación conductual sellada completada. Metaverso avanzado, GUI final,
órdenes libres y otros cuerpos siguen después de ECHO-3.

## Alcance de la revisión inicial (antes de ejecutar DYNAMIC-1 v2)

Se contrastaron roadmap, diseños/enmiendas, resultados, namespaces, tests y
artefactos locales. Los 12 resúmenes JSON `lab/echo3*report.json` presentes
coinciden con sus hashes. Los inventarios de código de FLIGHT v6 (82 entradas),
SENSOR v3 (101), GROUND v2 (202) y DYNAMIC v1 (225) no presentan diferencias
respecto a sus locks. Se leyeron las auditorías publicadas: SIM-3 416,
FLIGHT v6 1428, SENSOR v3 426 y GROUND v2 418 comprobaciones, sin hallazgos.

Esta revisión no ha repetido los vuelos ni todas las auditorías físicas, y
no convierte las cifras de tests de sesiones anteriores en resultados nuevos.
Sí se ejecutaron los tests focales actuales:

```bash
PYTHONPATH=.. python3 -m unittest echoai.tests.test_pattern1r echoai.tests.test_dynamic1 echoai.tests.test_dynamic1_v2 -q
```

Resultado: **39 tests, OK, 142.077 s**. Leen evidencia existente; no añaden
vuelos de aceptación ni convierten el desarrollo en un certificado.

Los diseños/resultados incluidos en locks se conservan sin editar; se corrigen
las páginas de estado, el roadmap y la cabecera del contrato general.

## Seguimiento de ejecución del 2026-09-14

La revisión inicial anterior queda como historial. Después se ejecutó DYNAMIC-1
v2 completo, bajo lock `7a30c4cf…`: once suites, 652 pruebas con un fallo
esperado declarado; A 8+2 y banco 12+7, evidencia válida y cierre verde.
PATTERN-1R se retoma en una versión separada: se han detectado desalineación
de firmas y un recorrido con sólo 155–366 mm de separación de pared para una
envolvente de 400 mm. Sus cifras históricas no son una estimación fiable de
la identidad hasta corregir esos defectos; tampoco se convierten en un verde.

PATTERN-1R v2 conservó un rojo por deriva vertical; v3 corrigió inicialización
y aprendizaje, pero conservó un rojo por etiquetado del juez. V4 corrigió sólo
esa evaluación y cerró una cadena nueva: seis desarrollos verdes, A 8+2 y banco
12+6, 28 vuelos de aceptación completos, 242 comprobaciones sin hallazgos, seis
mutantes y siete manipulaciones detectados. Certificado `95acf440…`;
[resultados y límites](PATTERN1R-V4-RESULTS.md).

FUSION-1 cerró después con 15 tests, 864 episodios funcionales y 240 ventanas
de replay; ocho mutantes y siete alteraciones detectados, auditoría válida.
No hubo vuelos nuevos. COMPOSE-1 continuó con nueve tests y 384 misiones
cinemáticas: `functional_green=true`, `compose1_green=false`. En confirmación
llega a 14/16 metas accesibles frente a Q 0/16, pero horizonte uno y ausencia
de caducidad empatan al completo. Falta evidencia específica de composición
y ejecución Gazebo/PX4. Ese resultado v1 permanece rojo.

**Actualización posterior: COMPOSE-1 v4 tiene certificado verde**, `b5974a9e…`,
con reconstrucción válida sin hallazgos. Segunda auditoría en proceso nuevo
válida, exit 0. V2 y v3 fallaron el test de signos de B (p=0,02973 y p=0,025051,
umbral 0,025) y conservaron sus C sin abrir. V4 reutiliza el agente v3 y
declara antes del examen un tamaño mayor, con semillas nuevas y los mismos
criterios: 6.144 misiones, 512/512 metas accesibles del completo; ventaja de
movimientos frente a horizonte uno confirmada por separado en B y C.

32 vuelos nuevos, todos válidos y con ejecución verde: completo 6/6 metas,
Q 0/6; los ocho casos de poca energía abandonan en origen sin desplazamientos
de misión. Completo/horizonte uno/convencional: 70/78/70 movimientos. Son
salas extruidas con altura fija y posición estimada disponible, no autonomía
general ni prueba de superioridad sobre el convencional. El coste energético
es abstracto y los abandonos se deciden tras el despegue del arnés. Los diez
vuelos A y trece controles de v3 se reutilizan por hash y no se cuentan como
nuevos. [Resultados, límites y auditoría](COMPOSE1-V4-RESULTS.md).

**Siguiente: CAUSE-1**, sin consumir el C físico sellado de TRANSFER-3.
