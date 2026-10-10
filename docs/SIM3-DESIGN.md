# SIM-3 — mundos declarativos y frontera de información

**Estado: implementado; banco verde en un host el 2026-09-10.** Este archivo
sigue siendo el diseño congelado y no se reescribe. Lo medido está en
[SIM3-RESULTS.md](SIM3-RESULTS.md) y en `lab/echo3_sim3_report.json`.
Fecha de diseño: 2026-09-10.
Contrato superior: [ECHO-3-ACCEPTANCE.md](ECHO-3-ACCEPTANCE.md).

## 1. Pregunta y alcance

¿Puede el mismo ejecutable cargar geometrías distintas, ejecutar física real
en Gazebo y mantener la verdad del mundo fuera del proceso consumidor?

SIM-3 construye el suelo experimental para la futura transferencia A→B/C.
Su verde demuestra infraestructura y aislamiento bajo las pruebas descritas;
no demuestra que echoAI vuele, reconozca una estación o componga un plan.
No requiere hardware, Akida, Qwen ni una API externa.

Entregables de implementación:

1. Validación de paquetes SDF/manifiesto y protocolo común.
2. Lanzador de Gazebo, reloj controlado y prueba física instrumental.
3. Separación de procesos y permisos comprobada con un consumidor adversarial.
4. Preparación y sellado de particiones, sin abrir el examen C real.
5. Banco, auditor independiente e informe reproducible.

No se implementan todavía vuelo/PID, sensores, traducción sensorial a WSP,
planificación, energía, recompensa por cargar ni GUI nueva. PX4 SITL será el
controlador del cuerpo a partir de FLIGHT-1; PX4-1 certificará después la
interfaz de intención y sus límites. SIM-3 no necesita arrancar PX4 para
certificar que un mundo existe y que una esfera cae en él.

## 2. Compatibilidad con el código actual

`nexus0/loop.py:Agent` consume `env.cell()` y `Cell.kind`; `Cell.extract` puede
incluir índice y tipo. El loop también consulta `env.kind` para métricas.
Entregarle un wrapper del mundo en el mismo proceso expondría verdad global.
No se admitirá `SDF → Cell(kind=GOAL)` como percepción física.

`greedy=True` evita exploración, pero `Agent.turn()` sigue actualizando T/Q y
puede crear memoria/PATTERN. Tampoco implementa el examen congelado. Además,
la configuración vital actual impide combinar planificación y supervivencia.
SIM-3 no debe corregir estos contratos a escondidas: quedan como dependencias
explícitas de GROUND-1, COMPOSE-1 y TRANSFER-3.

El consumidor de SIM-3 es un **probe instrumental**, no otro agente cognitivo.
Recibe sólo el reloj y responde al protocolo del arnés. Una regresión del Agent
existente se ejecuta aparte, en su entorno actual, sin atribuirle Gazebo.
GROUND-1 conectará las observaciones físicas al WSP existente. No se crea un
segundo loop de cognición ni un bus de pensamientos JSON.

Los float de SDF/Gazebo pertenecen a física externa. WSP permanece en 16 bytes
y el núcleo rápido permanece entero; SIM-3 no modifica sus representaciones.

## 3. Arquitectura y permisos

```text
Custodio (Roger)     protocolo + partición + secretos C
       │
       ▼
Supervisor privado ── paquete SDF/manifiesto ── Gazebo
       │                  │                      │
       │                  └──── verdad ──► evaluador privado
       │                                         │
       └── filtro por lista permitida ◄── reloj ──┘
                         │ socket heredado, frames limitados
                         ▼
                  consumidor aislado

Evaluador ── informe/verdad ──► auditor y visor del operador
                               (sin retorno al consumidor)
```

| Componente | Puede leer | No puede recibir |
|---|---|---|
| Supervisor/Gazebo | mundo, seed, pose real, manifiesto | escrituras cognitivas |
| Evaluador | verdad, protocolo, trazas de ejecución | autoridad para decidir por el agente |
| Filtro | entradas necesarias y esquema permitido | reglas de ruta por sala |
| Consumidor SIM-3 | mensajes `tick`, configuración pública común | mapas, roles, índices de entidad, recompensas oracle |
| Agente futuro | sensores filtrados y propio estado | SDF, manifiesto, seed, split, poses ground-truth |
| Visor operador | verdad opcional, rotulada como oracle | canal de respuesta hacia política durante examen |

La separación no consiste sólo en ocultar atributos Python. Usar lanzamiento
`exec` limpio, filesystem aislado de sólo lectura con el código necesario,
directorio efímero propio, entorno y descriptores permitidos explícitamente.
No montar repo completo, `lab/`, paquetes, cachés ni logs privados. Aislar red
y PID para impedir acceso a Gazebo Transport, servicios de entidades, `/proc`
del supervisor, puertos y procesos hermanos. El único enlace será un socket
preabierto (o mecanismo equivalente comprobado). Sin privilegios de host.

El implementador elegirá una herramienta disponible de namespaces/contenedor
y fijará su configuración en el lock de ejecución. Si el sistema no permite
aplicar estas restricciones, `isolation=not_run`: un mock de permisos no pasa.
Esto cubre fugas accidentales y accesos directos del probe; no demuestra
resistencia a escapes de kernel ni a todos los canales laterales temporales.

### Transporte mínimo de SIM-3

Una línea JSON UTF-8 de hasta 256 bytes por tick, sin campos extra:

```json
{"v":1,"seq":0,"sim_time_ns":0}
```

`seq` y tiempo son enteros no negativos, arrancan en cero por episodio y
avanzan un paso de 1.000.000 ns. Respuesta: `{"v":1,"ack":0}`. Cierre por EOF.
El supervisor toma el tiempo observado de Gazebo: nunca fabrica un reloj
para sustituir un backend que no arrancó. Incluir el tick inicial y 1.000 pasos
da 1.001 frames. ACK no es una acción de vuelo. Campo extra, mensaje demasiado
largo, orden incorrecto o timeout producen fallo registrado y cierre de sesión.
Timeout de ACK: 2 s de reloj real; límite de lanzamiento: 60 s; sin reintentos
silenciosos. El servicio de control de Gazebo queda en el lado privado.

No extender este transporte con `goal`, `free_path` o `object_type` para hacer
una demo. SENSOR-1/GROUND-1 definirán sensores y su adaptación, manteniendo
este transporte como infraestructura y WSP como único bus cognitivo.

## 4. Paquete y fuente de verdad

```text
suite/                         privado al supervisor
  protocol.json                reglas comunes, sin ajustes por mundo
  runtime-lock.json             versiones reales, generado al implementar
  assignment.json              partición/seed/hash; custodia separada para C
  packages/<id-opaco>/
    world.sdf                   única geometría y poses físicas
    manifest.json               referencias y roles de evaluación
```

Los esquemas verificables están en:

- [sim3-manifest.schema.json](schemas/sim3-manifest.schema.json).
- [sim3-protocol.schema.json](schemas/sim3-protocol.schema.json).
- Ejemplo público: [world.sdf](examples/sim3/world.sdf),
  [manifest.json](examples/sim3/manifest.json),
  [protocol.json](examples/sim3/protocol.json).

JSON Schema valida estructura. Las reglas geométricas, hashes, igualdad de
protocolo y permisos requieren un validador semántico y pruebas de procesos.

### Perfil SDF `sim3-boxes-v1`

Se elige SDF **1.8**, un subconjunto usado en la documentación de Harmonic.
La versión del lenguaje SDF no es la versión de libsdformat.

- Un `<sdf version="1.8">` con un único `<world name="sim3">`.
- Gravedad fija `0 0 -9.81`; física común `max_step_size=0.001`,
  `real_time_factor=1`, `type=ignored`. El backend real va fijado en el lock.
- Entre 3 y 64 modelos estáticos: suelo, al menos una barrera, una estación.
  Cada modelo tiene una pose explícita, un link, una collision y una visual.
  Ambas geometrías son cajas coincidentes y sin offsets internos.
- Posiciones y dimensiones en metros, representables exactamente en mm
  mediante análisis decimal; tamaños positivos; rotaciones cero en v1.
  Todos los AABB deben caber en `x,y ∈ [-8,8] m`, `z ∈ [-0.2,4] m`.
- Materiales comunes monocromos. La estación puede distinguirse del muro por
  geometría y gris, pero ese convenio es igual en todas las particiones.
- Mundo sin `<include>`, URI, mesh, `<plugin>`, GUI, scripts, sensores, joints,
  actores, modelos anidados, `relative_to` ni recursos remotos. Rechazar
  elementos y atributos no soportados, no ignorarlos. DTD/entidades XML y
  archivos de más de 1 MiB se rechazan antes de analizarlos.
- El árbol permitido completo es el del ejemplo, con repetición de `model`.
  Nombres únicos; links/colisiones/visuales locales `body/solid/shape`.
  Los materiales sólo contienen `ambient` y `diffuse`, RGBA gris entre 0 y 1.

El supervisor añade a una copia de ejecución los sistemas Physics,
UserCommands y SceneBroadcaster de una lista fija y versionada; puede omitir
SceneBroadcaster en headless si queda registrado. El mundo no elige plugins.
El rig de la prueba física se inserta desde código/asset de confianza común.
Guardar hash del SDF fuente y del SDF efectivo: nunca confundirlos.

### Manifiesto

El manifiesto enlaza el SHA-256 de los bytes exactos de `world.sdf`. Sus roles
`floor/barrier/charging_station` son para evaluación, nunca observaciones.
Debe asignar exactamente un rol a cada modelo, un suelo y una estación.
No repite poses de objetos. `spawn_mm` es una condición inicial privada;
la estación se localiza exclusivamente por la pose del modelo referenciado.
No incluye camino óptimo, forma de Q, nombres de acciones ni receta de meta.

`protocol_sha256` referencia los bytes exactos del protocolo común. Una pareja
de mundos con distinto protocolo no forma una comparación válida. El perfil
fija provisionalmente un volumen esférico de radio 250 mm **para validar
geometría**, no un modelo aerodinámico ni la envolvente definitiva del X500.
FLIGHT-1 deberá fijar su cuerpo y revalidar mundos y accesos.

La estación v1 es una caja sólida estática: no carga baterías al tocarla. Su
punto de aproximación de prueba se deriva de su cara superior más el radio y
100 mm de separación. Un flood-fill privado a resolución 100 mm comprueba
conectividad de spawn a ese punto tras inflar obstáculos por radio + 50 mm.
Se incluyen bordes del dominio como límites; sólo verifica esta aproximación
geométrica discreta, no navegación continua segura. La ruta nunca se exporta
al consumidor. Rechazar spawn dentro de sólidos y metas bloqueadas en el
banco base. Casos sin acceso serán bancos posteriores rotulados, no fallos
del generador escondidos como dificultad.

Conectar spawn y punto de aproximación a centros de celda vecinos sólo si el
segmento de conexión queda libre en la geometría inflada. No redondear una
posición atravesando una pared. El suelo debe cubrir la columna del rig y el
punto de aproximación; las barreras no pueden invadir esas columnas. Para
metamorfismos, validar de nuevo el paquete transformado antes de ejecutarlo.

Comprobar hashes antes del parseo; rechazar JSON con claves duplicadas,
campos desconocidos, números no finitos y rutas/symlinks que salgan del paquete.
`world.sdf` es el único nombre permitido, no una ruta que se concatena libremente.

## 5. A/B/C: aislamiento y examen sin consumir

Hay dos niveles diferentes:

| Conjunto | Propósito | Quién puede verlo |
|---|---|---|
| `rehearsal-A/B/C` | probar SIM-3 y su maquinaria | desarrolladores; datos públicos |
| A de una campaña conductual | aprender y ajustar | desarrolladores y entrenamiento |
| B de esa campaña | validación de parámetros congelados | se abre tras freeze |
| C de esa campaña | examen final reservado | custodio hasta freeze final |

**SIM-3 sólo corre rehearsal.** La letra C de ensayo no es evidencia reservada
de TRANSFER-3. No generar el C final en un árbol que Claude/Codex pueden leer.
Cada campaña posterior registra su propia partición; inspeccionar resultados
para diseñar COMPOSE-1 consume esos mundos para confirmación independiente.

Procedimiento de una campaña final:

1. Congelar generador, ontología, reglas, controles, N, KPI y umbrales en un
   protocolo versionado. Fijar hash de código y dependencias. Registrar quién
   tiene acceso a B/C. La ontología es común, no la geometría.
2. El custodio genera un secreto aleatorio de 256 bits. Publica el compromiso
   `SHA256(b"SIM3/v1/commit\0" + protocol_digest_bytes + secret_bytes)`.
   Deriva seeds con `HMAC-SHA256(secret, b"SIM3/v1/seed\0" + split_ascii +
   b"\0" + index_uint32_be)`, usando los primeros 8 bytes como uint64 big-endian.
   Los secretos y asignaciones se quedan fuera del acceso de los agentes.
3. Generar cada paquete con un PRNG/versión documentados y sin consulta a la
   política. Rechazos geométricos consumen índices y quedan en un ledger;
   máximo 100 intentos por caso, después fallo explícito.
4. Publicar antes del aprendizaje compromiso de los paquetes B/C: SHA-256 de
   un inventario canónico de hashes ordenados y su salt aleatorio de 256 bits.
   Formato exacto: `SHA256(b"SIM3/v1/inventory\0" + salt + inventory_bytes)`;
   inventario JSON UTF-8, claves ordenadas, sin espacios, sólo enteros/strings.
   Salt e inventario permanecen privados hasta apertura. Registrar compromiso
   fuera del repo editable por el implementador, con fecha y custodio.
5. Entrenar en A. Antes de B congelar snapshot, política, código, reglas y
   criterios. B mide validación; ajustar después de verlo exige nuevo freeze
   y convierte ese B en desarrollo. No retocar C para arreglar B.
6. Abrir C una vez bajo el freeze final. Publicar todas las corridas, fallos,
   seeds, inventario y hashes al terminar. C queda consumido. Una corrección
   posterior requiere nueva campaña, conservando el resultado anterior.

SIM-3 prueba estos pasos con secretos públicos de ensayo. El secreto real no
se pide en el prompt a Claude. El hash por sí solo no prueba custodia: registrar
accesos y responsable; si hubo acceso no autorizado, invalidar independencia.

La apertura requiere transición persistida `sealed → opened → consumed`,
exclusión mutua y escritura atómica. Un crash después de abrir conserva el
estado consumido para independencia; puede reanudarse como reproducción
rotulada, nunca como examen nuevo. No permitir dos procesos abriendo C a la vez.

### Geometrías distintas e información equivalente

Rechazar clones renombrados: huella de geometría con AABB/material/rol
ordenados, ignorando nombres y orden XML. Para el banco v1 comprobar además
que las tres geometrías base no son iguales bajo traslación, reflexión o giros
de 90° en el plano. Semillas distintas por sí solas no prueban mundos nuevos.
El generador puede construir conectividad; no puede entregar su solución.

El consumidor siempre ve el alias `sim3`, directorio de trabajo y argv comunes,
sin split, nombre de paquete, seed o hash. Se conserva la misma imagen de
ejecutable y configuración en todos los casos. El tiempo de lanzamiento no
se usa como entrada cognitiva. Que un sensor futuro permita reconocer una
sala por su aspecto es percepción legítima; pasarle `room_id` sería fuga.

Para TRANSFER-3 se diseñará una lista explícita de escrituras: parámetros
aprendidos congelados frente a pose, tracks y creencias actuales mutables.
Antes de cada episodio B/C se vacían mapas y estado episódico de A. El snapshot
permitido no puede arrastrar ranuras de Q/T indexadas por coordenadas o CAM de
A bajo el nombre de política. Ese formato es trabajo futuro; SIM-3 no declara
que el snapshot actual ya separa esas cosas. Transferencia no es herencia:
GEN-1f conserva únicamente su presupuesto de evidencia aprobado.

## 6. Banco de cierre preregistrado

Banco de infraestructura v1: 12 paquetes válidos de ensayo (4 por partición),
dos ejecuciones frescas por paquete; 24 ejecuciones de Gazebo. Seeds públicas
0–11 y asignación 0–3 / 4–7 / 8–11. Estos enteros son fixtures directos;
la derivación sellada se prueba aparte con un secreto público fijo de 32 bytes
`0x01`. No mezclar estos resultados con aprendizaje ni generalización.

| Prueba | Criterio verde | Rojo / no ejecutado |
|---|---|---|
| Paquetes | 12/12 parsean con libsdformat y validador propio; hashes/roles/coherencia correctos | parser sustitutivo o geometría descartada silenciosamente |
| Distinción | 3 bases no equivalentes; 12 paquetes reproducibles por seed y PRNG fijados | cambio sólo de nombre o resultado según orden de lectura |
| Física real | 24/24 avanzan 1.000 pasos y observan caída/contacto del rig | backend ausente, tiempo fabricado o pose reproducida desde fichero |
| Repetición | mismo lock: hash estático exacto y pose final del rig a ≤2 mm entre parejas | tolerancia ajustada al ver el resultado |
| Aislamiento | todos los accesos prohibidos fallan y el canal permitido funciona en 24/24 | declarar aislamiento sólo por inspección de clases |
| Renombrado | 12 pares renombrados/reordenados mantienen geometría y transcript de ticks idénticos | nombre modifica configuración o contenido permitido |
| Pared movida | 12 pares con una barrera trasladada 500 mm cambian AABB/colisión privados, sin filtrar al consumidor | hash cambia pero simulador ignora cambio |
| Sellado | compromiso, apertura y consumo único funcionan; toda alteración se detecta | C visible al implementador o reabierto como examen nuevo |
| Regresión | banco existente relevante mantiene sus candados | cambios de WSP, aprendizaje o córtex para acomodar SIM-3 |

Rig común: esfera de radio 50 mm, masa 0,1 kg, soltada sin velocidad, con el
centro a 1 m sobre el suelo en una columna libre verificada por el evaluador.
Registrar z inicial, z a 200 ms, contactos y z final a 1 s; caída a 200 ms entre
0,15 y 0,25 m y centro final a radio ±10 mm sobre suelo, con contacto observado.
Backend/solver/material del rig deben fijarse antes de certificar. El contacto
y la caída no demuestran aerodinámica. La prueba de pared movida consulta
colisión/entidad del backend, no sólo el parser del SDF.

Los 24 runs principales no incluyen los pares metamórficos adicionales.
Los probes de permisos intentan leer manifiesto, SDF, secrets, `lab/`, entorno
y argv del supervisor, `/proc`, symlinks, Gazebo Transport y sockets de host.
Introducir canarios privados distintos y comprobar que no aparecen en frames,
argv, entorno, stdout ni archivos visibles al consumidor. Probar también que
un mensaje extra del consumidor no habilita servicios de entidades.

Mutantes obligatorios: hash SDF cambiado; rol inexistente/duplicado; clave JSON
duplicada; seed/split filtrado; include remoto; plugin inyectado; XML con DTD;
symlink fuera del paquete; spawn sólido; copia renombrada como mundo nuevo;
backend desconectado; estadísticas sin avance; fallo de sandbox; reapertura C;
hash de runtime distinto entre mundos; informe con resultado/contador/traza
alterados. Cada uno debe fallar por su causa, desde un control positivo válido.

Medir tiempo de lanzamiento, RTF, RSS máximo de supervisor/Gazebo/consumidor y
latencias con unidades y muestras. Son descriptivos en SIM-3: no inventar una
ventaja edge ni julios a partir de tiempo de CPU. No usar 24 runs para prometer
una cola P99 estable. No se exige identidad bit a bit de física entre GPU/host
distintos. Una nueva plataforma exige nuevo lock y repetir el banco.

## 7. Informe y dependencias

Salida propuesta: `lab/echo3_sim3_report.json`, artefactos en directorio por run.
Campos mínimos: `schema_version`, `scope="simulation_infrastructure"`,
`dataset_kind="rehearsal"`, hashes de protocolo/código/lock/paquetes,
comandos exactos, host, backend real, seeds, `test_id`, resultados por caso,
conteos, causas de fallo, referencias/hash de trazas, métricas y limitaciones.

Cada grupo usa `pass|fail|not_run`; falta de dependencia nunca es `pass`.
`evidence_valid` requiere estructura, integridad y reconstrucción por auditor;
no significa éxito. `sim3_green` exige todos los grupos obligatorios en pass y
regresión aprobada. Un informe rojo puede contener evidencia perfectamente
válida. `hardware_status="not_available"` y `agent_in_gazebo=false` son
obligatorios en esta versión. No sumar fotos, mock tests o un C de ensayo como
transferencia física.

El auditor recalcula métricas desde trazas y hashes, no cree en `green:true`.
Compara con el compromiso externo del protocolo: reescribir informe y hashes
juntos no debe equivaler a evidencia independiente. Auditoría sintética puede
tener fixtures positivas, pero deben quedar rotuladas y no generar el informe
de certificación como si Gazebo hubiera corrido.

Base propuesta: Gazebo Harmonic en entorno compatible. `runtime-lock.json`
registrará sistema operativo, arquitectura, versiones exactas de gz-sim,
libsdformat, transporte, plugin/solver de física, Python, dependencias, imagen
y digest si usa contenedor, hashes de binarios/assets/código y límites del
sandbox. No usar `latest` ni descargar Fuel durante el banco. PX4 se fijará
por commit y assets cuando se incorpore; no inventar ahora un digest instalado.

Al diseñar, `gz` no está disponible en PATH. Por tanto sólo puede validarse el
esquema y el ejemplo con las herramientas locales; la compatibilidad efectiva
con libsdformat, física y aislamiento queda pendiente de implementación.

*Al implementar (2026-09-10):* Gazebo Harmonic entró por una imagen podman
construida en local desde `ubuntu:24.04` fijado por digest — gz-sim 8.15.0,
libsdformat 14.9.0, DARTsim 7.8.0, bubblewrap 0.11.0 en el host. Nada se
instaló en la máquina. Versiones exactas en `lab/sim3/runtime-lock.json`.

## 8. Orden de implementación

1. Validador, ejemplos y tests de rechazo; freeze del protocolo de ensayo.
2. Preflight/lock y Gazebo real con rig; sin conectar Agent.
3. Sandbox, transporte mínimo y pruebas adversariales.
4. Generador declarativo, particiones de ensayo y sellado.
5. Banco completo, auditor, regresión e informe; revisión independiente.

Si falta Gazebo o sandbox, completar lo independiente y publicar `not_run` en
lo pendiente. No modificar la definición de verde para cerrar el tajo.

## 9. Referencias técnicas verificadas

Consultadas el 2026-09-10; las versiones concretas se fijan al implementar.

- [Gazebo Harmonic: SDF worlds](https://gazebosim.org/docs/harmonic/sdf_worlds/):
  estructura SDF, paso físico y sistemas cargados por plugins.
- [SDFormat specification](https://sdformat.org/spec/): lenguaje SDF y versiones.
- [PX4: Gazebo simulation](https://docs.px4.io/main/en/sim_gazebo_gz/): integración
  SITL y selección de mundos; referencia para FLIGHT-1, no prueba presente.
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/json-schema-core):
  formato de los esquemas adjuntos.
