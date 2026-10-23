# PERCIBE-X r1 — resultados del 23 de octubre de 2026

**VERDE EN EL ALCANCE ESTRECHO DECLARADO.** Pasaron los dos desarrollos
recuperados, los seis vuelos fijos de validación y las auditorías nuevas.
Se acreditan identidades anónimas aprendidas en vivo, claves de MEMORIA-X y
una decisión de inspección ejecutada por PX4 y observada en Gazebo. No se
acredita navegación autónoma general ni la función intrínseca de los objetos.

Contrato y puertas anteriores a medida: [DESIGN](PERCIBEX-DESIGN-20261023.md).
Implementación y agenda congeladas: [PLAN](PERCIBEX-PLAN-20261023.md).
[Manifiesto final](../../lab/echo58/percibex/20261023-r1/final-manifest.json).
Artefactos: `lab/echo58/percibex/20261023-r1/`.

## Qué se ejecutó

El consumidor aislado actualizó PATTERN al recibir cada frame LiDAR escolar,
sin esperar EOF ni recibir pose, mundo o etiquetas privadas. Sus familias
anónimas fueron claves del motor MEMORIA-X original. El único puente existente
transportó también los WSP16 públicos de fase, oportunidad, recibo y acción,
según el nuevo contrato dúplex. No se hereda el certificado histórico de
cero bytes de retorno ni se crea otro bus.

El agente eligió ejecutar u omitir una inspección opcional. El actor mandó
heading NED basal +0,40 rad y retorno al mismo basal; el juez reconstruyó el
delta ENU observado en Gazebo, exigió 0,28–0,52 rad y retorno ≤0,12 rad,
y cotejó un segundo log privado de poses. Sólo esos resultados físicos
produjeron recibos PASS. Tres experiencias correctas por clave permitieron
omitir una repetición. PATTERN y MEMORIA-X quedaron congelados en examen.

Cada vuelo arrancó ambas memorias vacías: escuela en las primeras 32 poses y
examen congelado en las últimas 16. Esta r1 mide escuela→examen dentro del
mismo vuelo. La exportación/recarga `.wsp` acredita conservación exacta, sin
transferencia de memoria entre mundos ni arranque del siguiente vuelo desde
memoria exportada. No hereda el verde histórico de transferencia MEMORIA-X.

El recorrido de 48 poses siguió perteneciendo al arnés. La autoridad del
agente se limita al barrido opcional. No se midieron función intrínseca de
paredes, semántica general, roles dinámicos, navegación general ni hardware.
Son vuelos SITL ejecutados en Gazebo/PX4, sin sustituirlos por grid o mocks.

## Desarrollo, interrupción y custodia

El reinicio por OOM interrumpió el intento original `dev-w0`, sin episodio,
sensores, bridge ni puntuación conservados. Plan, metadata y bundles originales
permanecen intactos como `INTERRUPTED_NO_RESULT`. Cuenta como intento; junto
a los dos recuperados consume el máximo de tres. No se sustituyó en silencio.

Antes de recuperar y sin datos observados de un vuelo de P, se corrigió el
actor de heading absoluto a NED basal +0,40 y retorno al basal. El juez pasó
a delta ENU relativo, con límite superior y pruebas de offsets/wrap ±π.
Los recibos previos y `development-recovery1-custody.json` conservan los
hashes anterior y corregido. No cambiaron aprendizaje, consumidor o puertas.

`consumer.pyz` se preservó entero y contiene un `flight.py` antiguo inactivo.
Su entrada importa Ground/Online; el actor ejecutado está en el `flight.pyz`
corregido. La identidad byteidéntica corresponde al bundle consumidor
preservado y a los módulos de aprendizaje activos, no a todos los módulos
del ZIP consumidor frente al árbol actual. Los inventarios distinguen ambos.

| Desarrollo | Semilla | Acierto examen | Confusiones | Desconocidos | Inspecciones escuela | Inspecciones examen |
|---|---:|---:|---:|---:|---:|---:|
| dev-w0-recovery1 | 2026102301 | 353/392 (90,05%) | 0 | 39 | 6 | 0 |
| dev-w1-recovery1 | 2026102302 | 362/385 (94,03%) | 23 (5,97%) | 0 | 7 | 1 |

Todas las inspecciones fueron exitosas y tuvieron testigo en el log privado.
Los objetos reales recibieron 3/3 y 4/3 éxitos escolares respectivamente,
sin exenciones prematuras. Las purezas escolares fueron 91,36% y 91,18%.
Las duraciones de campaña, incluida evaluación local, fueron 310,30 y 515,56 s.

La [auditoría previa](../../lab/echo58/percibex/20261023-r1/development-recovery1-audit.json)
reconstruyó ambos desarrollos: 31 fuentes y 22 artefactos correctos, 18
controles negativos detectados y dos positivos aceptados. Su puerta
comparativa quedó pendiente por diseño: desarrollo sólo contiene MEMX.
No se confundió la salida 0 del auditor de evidencia con un verde compuesto.

## Seis validaciones fijas

Dos mundos rehearsal nuevos de la familia conocida, índices 420/421 y
semillas 2026102311/2026102312, cada uno con MEMX, EMPTY y VISITS. Ningún vuelo
se reemplazó y no se amplió la muestra. EMPTY ignora el recuerdo al decidir
e inspecciona cada familia reconocida; VISITS omite tras tres solicitudes.

| Mundo | Política | Acierto examen | Confusiones | Desconocidos | Inspecciones escuela | Inspecciones examen |
|---|---|---:|---:|---:|---:|---:|
| 420 | MEMX | 369/392 (94,13%) | 20 (5,10%) | 3 | 6 | 2 |
| 420 | EMPTY | 319/385 (82,86%) | 35 (9,09%) | 31 | 29 | 16 |
| 420 | VISITS | 746/774 (96,38%) | 24 (3,10%) | 4 | 7 | 1 |
| 421 | MEMX | 388/392 (98,98%) | 3 (0,77%) | 1 | 8 | 1 |
| 421 | EMPTY | 334/390 (85,64%) | 45 (11,54%) | 11 | 29 | 16 |
| 421 | VISITS | 406/437 (92,91%) | 20 (4,58%) | 11 | 6 | 1 |

Cada fila tiene evidencia válida y supera las puertas congeladas de
reconocimiento y física. Los desconocidos permanecen en el denominador.
Las 122 inspecciones de validación fueron exitosas y tuvieron testigo privado;
la menor separación observada durante inspección fue 985,938 mm, frente al
mínimo fijado de 400 mm. Cada vuelo tuvo 32 oportunidades escolares y 16 de
examen; una abstención por identidad inmadura cuenta como omisión, no éxito.

MEMX hizo menos inspecciones de examen que EMPTY en ambos mundos: 2 frente
a 16 y 1 frente a 16. VISITS hizo una menos que MEMX en el primero y empató
en el segundo. Totales descriptivos: MEMX 3, EMPTY 32, VISITS 2. **No hay
ventaja exclusiva de MEMORIA-X frente a la caché en estos vuelos.** Todas las
inspecciones reales tuvieron éxito; la diferencia ante NOOP se comprobó sólo
en pruebas de software, sin atribuirle una ventaja física medida.

En MEMX los objetos reales recibieron 3/3 y 4/4 éxitos escolares, sin ninguna
exención prematura. La sombra con clave colapsada dio tres exenciones
prematuras por mundo: seis testigos de pérdida de especificidad sobre el
historial observado. Es un control offline condicional, no un vuelo ni una
trayectoria contrafactual ejecutada.

| Vuelo | Frames de transporte | Observaciones de examen puntuables | Tiempo del runner (s) |
|---|---:|---:|---:|
| val-w0-memx | 38.711 | 392 | 513,99 |
| val-w0-empty | 61.356 | 385 | 719,03 |
| val-w0-visits | 46.254 | 774 | 598,45 |
| val-w1-memx | 41.603 | 392 | 497,56 |
| val-w1-empty | 64.258 | 390 | 791,27 |
| val-w1-visits | 39.583 | 437 | 506,70 |

Son ejecuciones separadas del mismo paquete/semilla/recorrido, con duración,
acciones y bytes sensoriales diferentes. Las vistas son correlacionadas de
dos paredes; no son cientos de ensayos independientes ni una reserva C nueva.
El tiempo del runner excluye la evaluación local posterior del anfitrión.

## Auditoría y conservación

La [auditoría final en proceso nuevo](../../lab/echo58/percibex/20261023-r1/validation-audit.json)
aprobó `evidence_valid`, reconocimiento, física, identidad conductual, efecto
frente a EMPTY y controles adversos: `percibex_narrow_green=true`. Verificó
31/31 fuentes y 66/66 artefactos, sin errores. Aceptó dos reconstrucciones
positivas y rechazó 18 alteraciones: aprendizaje retrasado hasta EOF,
escritura tras freeze, recibo omitido/alterado, acción alterada, estado
declarado falso, canal extra, LiDAR alterado y yaw observado borrado.

Se reconstruyó el orden completo de sensores/controles, las claves, el estado
congelado y cada recibo. `cortex_calls=0` y `Memory.destroyed=0`. Pasaron antes
de medir 55 pruebas stdlib: 23 nuevas y 32 regresiones pertinentes. La prueba
de claves recorre las 64 familias tras las normalizaciones reales de MEMX.
Las pruebas de software no sustituyen los vuelos.

Los ocho vuelos completos conservaron `memory.wsp` y `session.wsp`. La
[lectura nueva de conservación](../../lab/echo58/percibex/20261023-r1/wsp-fresh-audit.json)
reabrió los 16 archivos: 98 experiencias de memoria y 13.737 paquetes de
sesión, con bytes y metadata exactos, cabezas y cadenas correctas. Los perfiles
son `memx-replay-v1` y `wsp16-session-v1`; no son un bus adicional ni autoridad
física. El [cotejo independiente del coordinador](../../lab/echo58/closure-20261023/p-cross-check.json)
contrastó las seis validaciones, sus fuentes, archivos WSP y agregados.

DESIGN, PLAN, aprendiz, actor y puertas permanecieron intactos desde prepare.
Las revisiones anteriores están vinculadas al inventario sin ciclo de hashes.
No se editaron fuentes históricas, certificados ni exámenes anteriores; no
se usaron LLM, API externas, Akida o el proyecto legacy, ni se publicó nada.

## Recursos y cierre operativo

Un único vuelo cada vez, con `flock /tmp/echo58-heavy.lock`. Unidades de carga:
CPUQuota 150%, MemoryHigh 1536 MiB, MemoryMax 2 GiB, swap 0, TasksMax 256,
Nice 10, OOMPolicy stop, Restart no y RemainAfterExit yes. Contenedores con
etiqueta exacta del estudio: CPU 150000/100000, memoria 3 GiB, swap adicional
0 y pids 128, verificados en HostConfig y cgroup reales. Jaula: afinidad a un
CPU y RLIMIT_AS 512 MiB, sin llamarlo cgroup propio. Hilos configurables a 1.
El preflight esperó MemAvailable≥6 GiB antes de cada vuelo.

| Unidad | CPU acumulada en su cgroup (s) | MemoryPeak (B) |
|---|---:|---:|
| echo58-p-recovery.service | 75,354 | 529.698.816 |
| echo58-p-audit.service | 26,369 | 290.226.176 |
| echo58-p-validation.service | 297,402 | 1.005.805.568 |
| echo58-p-validation-audit.service | 37,270 | 474.390.528 |

Estos contadores **excluyen los contenedores Podman fuera de esas unidades**;
no son CPU ni memoria total del vuelo. El
[resumen operativo](../../lab/echo58/percibex/20261023-r1/operational-resource-summary.json)
conserva los dos ámbitos separados y los IDs completos.

La captura parcial del primer dev observó `memory.peak=1.150.193.664 B` y
`pids.current=78` aproximadamente al minuto tres. No se conoce su máximo final
ni su pico de pids: `--rm` eliminó el cgroup. El segundo dev tuvo pico de
memoria observado 723.255.296 B. En validación los picos acumulados observados
fueron 711.974.912–713.101.312 B y `pids.peak=82`. Las estimaciones de CPU
entre sondeos de unos 5 s alcanzaron 1528–1534 milésimas de un núcleo; se
conservan como estimaciones muestreadas, junto a la cuota efectiva de 1,5 CPU.
No se inventa el último contador anterior a `--rm`.

El primer observador tuvo un error de plantilla Podman y produjo listas
vacías: se conserva y se excluye de picos. El observador corregido guardó
738 muestras de validación y dos consultas incompletas (inspect no disponible
y PID ya ausente), ambas conservadas; no significan ausencia de un vuelo.
Las muestras que incluyeron memory.events no registraron OOM/oom_kill.

Se archivaron los contadores antes de detener sólo el observador propio.
Las unidades de carga siguen conservadas con RemainAfterExit. Los logs P
quedaron quietos antes del manifiesto. El log compartido del watcher del
coordinador se excluye del manifiesto P y se ancla en el cierre global.
El helper de emergencia revalida etiqueta exacta e ID completo antes de
operar; ninguna limpieza de contenedores ajenos fue necesaria.

Comandos de medida ya ejecutados bajo las unidades limitadas: `campaign
recover-dev`, `campaign validate`, `audit development-recovery1` y `audit
validation` del paquete `echoai.echo58.percibex`. Sus salidas exclusivas y los
logs reales del mini terminal de desarrollo se conservan con el intento
interrumpido. El cierre mantiene el alcance de reconocimiento e inspección
mínima; no lo amplía a capacidades que esta campaña no midió.
