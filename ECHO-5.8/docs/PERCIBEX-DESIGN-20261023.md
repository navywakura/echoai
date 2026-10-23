# PERCIBE-X r1 — identidades aprendidas en vivo y una inspección ejecutada

Fecha: 2026-10-23. Estado previo a medida: candidato por implementar.
Autorización: completar P de ECHO-5.8/5.8.2 autónomamente; sin publicar,
instalar modelos, reabrir exámenes ni editar fuentes/certificados históricos.

## Pregunta y alcance mínimo

¿Puede el consumidor aislado aprender familias anónimas de LiDAR mientras
llegan los frames, usar esas familias como claves del motor MEMORIA-X y
evitar repetir una inspección física que PX4 ya ejecutó?

La inspección es un barrido acotado de yaw, seguido de retorno al yaw inicial,
con desplazamiento angular observado en Gazebo y aceptación MAVLink de PX4.
No atribuye una función intrínseca desconocida a una pared. El recorrido de
48 poses pertenece al arnés; ECHO decide únicamente ejecutar u omitir ese
barrido en cada oportunidad. El resultado no acredita navegación general,
hardware, reconocimiento semántico general ni roles dinámicos de objetos.

## Componentes que se importan

* `nexus0/pattern1r_v4/assets/consumer.py`: Ground, framing y firmas binarias.
* `nexus0/pattern1r_v4/memory.py`: AbstainingPatternMemory, sobre PATTERN-1.
* `echo58/memx/memory.py`: Memory, sin modificar ni copiar su algoritmo.
* `nexus0/pattern1r_v4/session.py`, TAP y runner: vuelo y transporte existentes.
* `echo58/wspfiles`: conservación de WSP16 y memoria, cuando proceda.

Los imports del consumidor aislado se empaquetan como zipapp junto a las
fuentes originales byteidénticas y un adaptador nuevo. Las fuentes originales
se inventarían por SHA-256. No se copia el bucle Agent ni se crea otro bus de
pensamiento. No hay LLM, API, Akida ni dependencia del proyecto legacy.

## Fronteras y representación

El único puente de la jaula sigue siendo el socket de sensores ya existente.
Se declara un contrato nuevo que admite WSP16 de fase, oportunidad y recibo
en ese mismo puente, y respuestas de acción WSP16. No se hereda el certificado
histórico de cero bytes de retorno. El informe final de stderr es evidencia
pasiva y no vuelve al agente. El arnés registra orden de entrada/salida y
bytes completos de los controles; los sensores conservan sus hashes.

El aprendiz PATTERN sólo recibe `(signature, 0)` en escuela y `signature` en
reconocimiento. No recibe pose, geometría, mundo, índice de vista, identidad
privada ni etiquetas del juez. Una señal pública inicia escuela antes de la
pose 0 y congela al terminar la 31; las poses 32–47 son validación congelada.
Las fases sólo contienen modo y secuencia del protocolo, sin información de
identidad. No se espera EOF para actualizar ni para responder acciones.

Memory recibe `ident=family+1`, `sig=(family & 15) | ((family & 48) << 1)`,
`act=TOGGLE`, `hand=0`. Esta codificación inyectiva para las 64 familias deja
bit4 a cero y evita que la normalización automática de L2 borre bits de clave;
una prueba recorre las 64 claves tras las normalizaciones reales de L1/L2.
Ambas claves derivan de la identidad anónima reconocida, no de la etiqueta
privada o distancia. El vocabulario heredado `PASS` se interpreta aquí como
«barrido ejecutado y retorno observado». Tras tres recibos PASS y proporción
≥85%, la política omite una inspección ya completada. NOOP registra un fallo;
no se simula éxito. En validación no se escriben PATTERN ni Memory.

La política considera familias reconocidas en los últimos 1000 ms de LiDAR,
elige circularmente entre las visibles y pide inspección si su regla no dice
PASS. Sin familia madura se abstiene. El arnés traduce sólo INSPECT a un
objetivo yaw NED basal observado +0,40 rad y retorno al mismo heading basal.
Gazebo se puntúa independientemente por delta angular respecto al yaw ENU
basal, con magnitud 0,28–0,52 rad y retorno ≤0,12 rad. El gate rechaza códigos inesperados,
secuencias incoherentes y órdenes sin oportunidad activa.

## Pruebas y controles fijados antes de volar

Máximo tres vuelos de desarrollo por candidato fijo. El primer candidato
r1 usa mundos nuevos de la familia rehearsal ya conocida (sin llamarlos C).
Tras desarrollo, un lock nuevo fija fuentes, parámetros, mundos y seis vuelos
de validación: dos mundos × {MEMX, EMPTY, VISITS}. EMPTY recibe los mismos
sensores y aprende el mismo PATTERN; siempre solicita inspección cuando hay
identidad. VISITS es una caché simple que omite tras tres solicitudes por
familia. Si todas las inspecciones tienen éxito puede empatar con MEMX; no se
reclama ventaja exclusiva del motor de memoria. La pertenencia al mundo y
etiquetas privadas sólo las usa el juez offline.

Controles adversos offline sobre el transcript nuevo: colapsar familias,
retrasar aprendizaje hasta EOF, escribir tras freeze, eliminar/alterar recibos,
alterar acción o procedencia sensorial, y cambiar el informe sin cambiar datos.
Sus resultados se distinguen de vuelos físicos de control.

## Puertas por componente

1. **Cable/aislamiento:** namespaces reales disponibles, fuentes empaquetadas
   idénticas, sin canarios privados ni esquema fuera de contrato; cada respuesta
   vinculada al WSP de oportunidad anterior, antes de EOF.
2. **Aprendizaje en vivo:** actualización PATTERN antes de la primera respuesta
   con identidad y antes de freeze/EOF; reconstrucción completa en proceso nuevo
   del orden sensores/controles y del estado final. Cero escrituras tras freeze.
3. **Reconocimiento:** ≥75% acierto, ≤15% confusión, dos familias diferentes,
   pureza escolar ≥60%, ≥20 observaciones escolares y de examen de cada pared.
   El mapa de nombres del juez usa sólo escuela y el modelo final congelado.
   Desconocidos cuentan en el denominador. Se informan rojos individuales.
4. **Claves conductuales:** Memory conserva recibos reales por familia,
   decisiones reconstruibles, ninguna inspección omitida sin tres éxitos
   previos durante escuela. Control colapsado debe revelar pérdida de
   especificidad, o el alcance de identidad queda pendiente.
5. **Autoridad física mínima:** ≥3 inspecciones exitosas por familia seleccionada
   en escuela; aceptación de comandos, delta yaw observado 0,28–0,52 rad y retorno
   ≤0,12 rad. MEMX ejecuta menos barridos en examen que EMPTY en ambos mundos;
   no se exige superar VISITS. Todas las oportunidades y fallos se conservan.
6. **Conservación:** fuentes históricas intactas, WSP16, cortex_calls=0,
   Memory.destroyed=0 y auditor offline nuevo sin hallazgos.

VERDE estrecho requiere las seis puertas. Una puerta roja no se sustituye por
una prueba grid, un mock, transporte correcto ni prosa. El informe separa
validez de evidencia y resultado científico, conserva desarrollo y no amplía
la muestra para hacer pasar el candidato.

## Observabilidad

En desarrollo se abre mini terminal leyendo decisiones, recibos y resultados
reales. Son exportaciones pasivas; no monólogo ni entrada al aprendiz. La
validación nueva queda congelada con su propio transcript técnico, sin añadir
instrumentación a campañas anteriores.

## Adenda de recursos tras reinicio, antes de cualquier resultado

El primer vuelo de desarrollo `dev-w0` quedó interrumpido por el reinicio del
host. El coordinador identificó OOM. Persisten plan, bundles y metadata; no hay
episodio, sensores, bridge, resultado ni muestras del directorio temporal
anterior. Se conserva como `INTERRUPTED_NO_RESULT`, sin puntuación. No se
reinterpreta como vuelo aprobado ni se elimina del número de intentos.

La recuperación declarada `development-recovery1` repetirá los dos mundos
originales con el mismo bundle de consumidor y las mismas fuentes de
percepción, PATTERN, controlador online y MEMORIA-X, comprobados por igualdad
SHA-256. Junto al intento interrumpido consume los tres intentos de
desarrollo permitidos. Sólo cambian la supervisión de recursos y su registro:
Podman `--cpus=1.5 --memory=3g --memory-swap=3g --pids-limit=128`, y valores 1
para LP/GALLIUM/OMP/MKL/OPENBLAS threads. La jaula hereda afinidad a un único
CPU permitido y `RLIMIT_AS=512 MiB` antes de ejecutar bubblewrap. Este último
es límite de espacio virtual por proceso; no se describe como cgroup propio.
Los contenedores sí reciben límites cgroup explícitos de Podman.

Los wrappers viven bajo el artefacto de esta ejecución y se inventarían por
hash; no cambian la configuración global ni archivos de nexus0. No se ejecuta
la recuperación hasta la señal del coordinador, cuando C y E hayan terminado.
Un fallo por límites se conserva como fallo; no se suben límites en silencio.

Antes de recuperar y sin datos de P observados, la revisión detectó una
dependencia errónea del actor: pedía heading MAVLink 0,40 y comparaba yaw
Gazebo absoluto 0,40/0. Se corrige el actor para leer ATTITUDE de PX4, mandar
heading basal NED +0,40 (normalizado en ±π), volver al mismo basal y medir
delta ENU contra su basal independiente. Se comprueba offset, wrap ±π y
rechazo de giros de 2 rad. El bundle antiguo del runner se conserva; el nuevo
lleva hash distinto y una adenda de custodia. No es ajuste a un vuelo medido.
El campo heading de DO_REPOSITION está en radianes y la implementación fijada
lo consume directamente: [MAVLink](https://mavlink.io/en/messages/common.html#MAV_CMD_DO_REPOSITION),
[PX4 fijado, navigator](https://github.com/PX4/PX4-Autopilot/blob/99c40407ffd7ac184e2d7b4b293f36f10fe561ef/src/modules/navigator/navigator_main.cpp#L293).

La unidad del supervisor es `echo58-p-recovery.service`: MemoryMax 2G,
MemoryHigh 1536M, swap 0, CPUQuota 150%, TasksMax 256 y Nice 10, con exclusión
mutua `/tmp/echo58-heavy.lock`. Antes del preflight y de cada vuelo se espera
MemAvailable≥6 GiB; esperar recursos no es un fallo científico. Los
contenedores llevan etiqueta `echoai.study=percibex-recovery-20261023` para
identificarlos sin operar sobre contenedores de otros trabajos.

### Adenda operativa de limpieza, anterior a los vuelos recuperados

`resources.cleanup_owned_containers(reason)` usa sólo stdlib. Lista con el
filtro de etiqueta exacta, acepta únicamente IDs hexadecimales completos de
64 caracteres y verifica la etiqueta en descubrimiento y de nuevo antes de
`stop --time=2`. Sólo después de otra verificación permite `rm --force`.
Cada comando tiene timeout de cinco segundos. No usa `prune`, selección global
para mutaciones ni nombres/IDs recibidos del agente.

Los recibos contienen IDs, etapas y códigos de retorno; no incluyen entorno,
stdout/stderr de herramientas ni valores de etiquetas ajenas. Un fallo al
inspeccionar después de detener se registra como no inspeccionable, no como
eliminación confirmada. Los tests fuerzan IDs inválidos, otra etiqueta con el
mismo prefijo, cambios de propiedad, JSON inválido y timeout del listado;
ninguna mutación alcanza un contenedor ajeno o no verificado.

El adaptador nuevo intercepta `TimeoutExpired` de `subprocess.run` con un proxy
local, limpia antes del join/collect heredado y restaura todos los bindings.
También limpia al devolver fallo o propagarse una excepción. Una limpieza
incierta o una excepción aborta la etapa antes de lanzar otro contenedor y
conserva los registros. No cambia fuentes históricas, aprendiz, criterios ni
imágenes. El bundle del consumidor y el runner corregido conservan sus bytes.

SIGKILL/OOM puede impedir cualquier `finally` de Python. El watcher externo
del coordinador invoca el mismo helper sólo para la unidad de P tras fallo o
suelo de RAM; no se afirma que el adaptador sobreviva a SIGKILL. Tras fallo de
unidad hay que esperar a que el watcher termine antes de relanzar. Esta adenda
se inventaría en `resource-cleanup-review.json` antes de medir.

### Vinculación del contrato al inventario, anterior a medida

El inventario obligatorio de `prepare` incluye este DESIGN y el PLAN junto a
los recibos previos de reinicio, revisión del actor, limpieza operativa y
no-op real del coordinador. `contract-freeze-review.json` documenta esta
enmienda y referencia los hashes de esos recibos anteriores; no contiene su
propio hash. El plan de campaña, creado después, fija el hash del recibo nuevo.
Así no hay ciclo de hashes ni se reescriben revisiones anteriores.

Una prueba usa `prepare` sobre una fixture nueva, modifica el contrato de la
fixture y comprueba que el auditor devuelve `source_checks=false` para ese
archivo conservando los demás. No modifica el contrato real ni ejecuta un
simulador. Después de `prepare`, DESIGN y PLAN no se editan; medidas, fallos y
avances se escriben sólo en RESULTS. Esta vinculación no cambia aprendiz,
actor, umbrales ni puertas de aceptación.
