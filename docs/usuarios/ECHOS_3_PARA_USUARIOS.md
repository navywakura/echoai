# echOS 3.0: qué ejecuta y qué protege

**Guía para usuarios · estado contrastado el 18-09-2026.** echOS 3.0.0 es un *unikernel robótico*: un sistema que arranca directamente y reúne el núcleo y las funciones necesarias para su tarea. Tiene su propio runtime de sensores e intenciones, controles de seguridad, diagnóstico y conexión con PX4.

La versión 3.0 ya está construida y su alcance documentado está cerrado. Su [informe de evidencia](../../../docs/ECHOS_3.0_REPORT.md) recoge seis certificados que suman **441 comprobaciones**, todas aprobadas. Son pruebas de software y máquinas virtuales; no una certificación aeronáutica ni una campaña de vuelo físico.

## Qué aporta al conjunto

PRISMA procesa señales. echoAI interpreta observaciones, conserva memoria y propone acciones. echOS aporta una ejecución acotada, con reglas sobre cuánto puede ocupar una cola, cuánto tiempo vale una intención y qué se permite enviar al controlador.

**echOS ya se conecta a PX4 SITL por su propio puente.** Sin embargo, su productor de intenciones actual es una política simple: reacciona a distancia, objetos, batería y enlace. El código la identifica como provisional; no planifica, recuerda ni aprende. Integrar el agente completo de echoAI en ese lugar es un trabajo pendiente y distinto de haber probado cada línea por separado. [Productor y pipeline actuales](../../../kernel/robot/robot.c).

Tampoco hay un LLM dentro de la ISO. El híbrido con el córtex opcional reside en la línea echoAI, en host. El tejido de eventos spiking LIF/Q6 de echOS existe, pero no equivale a tener el agente entero, Qwen o un decoder EEG embebidos.

## El recorrido que está implementado

```text
Registro de sensor → cola acotada → productor de intención
    → cola de intención → safety gate → cola de salida
    → puente MAVLink 2 → PX4
```

La telemetría que devuelve PX4 alimenta registros de sensor. En estas pruebas PX4 SITL corre en el host, fuera de la ISO. PX4 conserva la estabilización, la mezcla de motores y sus failsafes; echOS envía consignas de alto nivel compatibles con el puente implementado.

| Contrato | Tamaño actual | Para qué sirve |
|---|---:|---|
| Sensor ABI | 64 bytes | Registrar una observación con tipo, fuente, tiempo y calidad |
| Intent ABI v1 | **72 bytes** | Proponer una acción con causa, caducidad y límites |
| WSP de echoAI | **16 bytes** | Representación cognitiva del agente; no es el transporte del Intent ABI |

El tamaño de la intención está fijado por la comprobación de compilación `sizeof(intent_t) == 72`. Un comentario antiguo del relleno dice 64; no describe el tamaño real de la estructura. [Sensor ABI](../../../kernel/robot/sensor.h), [Intent ABI](../../../kernel/robot/intent.h).

Una intención puede expresar mantener posición, continuar, acercarse, evitar, volver, aterrizar o abortar. Incluye qué observación la causó, cuándo se midió, cuándo se decidió, hasta cuándo vale y qué velocidad y alcance acepta como límites. **No contiene campos de PWM, servo o acelerador de motor.** Que una acción exista en el ABI no demuestra por sí solo que todos los vehículos o modos de vuelo la soporten.

El campo `confidence` admite 0–1.000, en tantos por mil. Es una valoración declarada por el productor, no una medida de seguridad física ni de confianza subjetiva de la persona.

## Cómo interviene el safety gate

El gate comprueba versión, rangos, antigüedad de la observación, caducidad, batería, enlace, geofence y límites configurados. Mantiene explícito si conoce una variable: una batería desconocida no se interpreta como llena. [Contrato de seguridad](../../../kernel/robot/safety.h).

| Veredicto | Qué sucede | Cómo se cuenta |
|---|---|---|
| **OK** | Pasa la intención intacta | Acierto atribuible al productor |
| **MODIFY** | Se reduce o cambia lo permitido | Corrección atribuible al gate |
| **BLOCK** | No se envía esa intención | Bloqueo registrado con su razón |

Si no llegan intenciones a tiempo, el watchdog puede emitir una intención de mantenimiento de posición. Las degradaciones también contemplan retorno o aterrizaje según condiciones. Estos mecanismos se complementan con el failsafe del autopiloto.

Esto permite detectar propuestas vencidas o fuera de los límites representados. No garantiza reconocer cualquier error semántico: «acercarse al objeto equivocado» puede ser una orden bien formada. Tampoco convierte *hover* en respuesta universalmente segura; depende de localización, energía, entorno y modo del controlador. No hay aquí una detección neural de «el piloto ha perdido la atención».

## Memoria y tiempos que se pueden auditar

Las cuatro colas tienen almacenamiento fijo y contadores de entradas, salidas, descartes, expiraciones y ocupación máxima. En los escenarios registrados hubo **cero llamadas de asignación dinámica en el camino sensor → intención**. Esa afirmación está limitada a ese tramo; no describe toda la memoria del ecosistema ni el proceso Python de echoAI.

El escenario del informe conserva los fallos inyectados: **61 registros = 50 aceptados + 3 rechazados + 8 descartados**; el gate ve **48 intenciones = 43 aceptadas + 4 modificadas + 1 bloqueada**. También registra una expiración y un incumplimiento de plazo. Son resultados esperados de una prueba que ejercita los controles, no una promesa de que nunca se descarte nada.

Hay histogramas de latencia y medidas brutas bajo QEMU. Sus percentiles son cotas de intervalos y cambian entre ejecuciones. No sirven para anunciar un plazo máximo garantizado ni una latencia humana completa. En particular, la salida BIOS «< 0 µs» no debe publicarse como tiempo nulo o negativo: requiere revisar esa representación antes de usarla como cifra de rendimiento.

## Qué cubre el cierre 3.0

| Certificado | Comprobaciones | Alcance |
|---|---:|---|
| CERT-21 BIOS | 130 | Arranque y funciones x86_64 |
| CERT-21 UEFI | 130 | Arranque y funciones x86_64 con OVMF |
| CERT-22 | 20 | GPT/NVMe, persistencia, errores y timeouts |
| CERT-E | 25 | Puente PX4 en x86_64 |
| CERT-G AArch64 | 76 | ARM64 directo y conexión PX4 |
| CERT-G AArch64 UEFI | 60 | Arranque ARM64 con firmware edk2 |
| **Total** | **441** | **Seis certificados del alcance declarado** |

El informe incluye hashes de artefactos, builds reproducibles y dos arranques ARM con los mismos **36 campos declarados deterministas**. La latencia se excluye expresamente de esos 36 campos porque no se mantuvo idéntica.

La integración MAVLink 2 comprueba CRC y secuencias y decodifica un conjunto definido de mensajes. Las ejecuciones citadas registran cero huecos de secuencia y cero errores CRC; eso describe esos enlaces de prueba, no cualquier radio futura. La pérdida de enlace se ensaya y queda registrada por PX4.

## Qué tiene delante un usuario hoy

Puede inspeccionar identidad, dispositivos, memoria, límites y contadores desde la consola. Las órdenes de diagnóstico incluyen `about`, `status`, `limits`, `devices`, `mem`, `report`, `robot` y `px4`; la ayuda de la imagen concreta indica su disponibilidad. ARM utiliza consola serie y una shell reducida, mientras x86 dispone de su interfaz de consola propia.

La versión no ofrece una distribución de escritorio, compatibilidad general con aplicaciones Linux ni un sistema multiprocesador: funciona con un núcleo. En ARM faltan framebuffer, userland completo y enumeración completa de periféricos; no hay lector ACPI. La sonda Akida declara el dispositivo detectado **no soportado**: no ejecuta inferencia acelerada. No hay AKD1000 en el laboratorio.

Para NEURO-DRON falta unir el productor de echoAI a este runtime, conservar causa y tiempo desde PRISMA y validar el conjunto bajo retrasos, pérdida de datos y recuperación. El ABI y el gate existentes son el punto de partida. No hace falta inventar un bus cognitivo nuevo para estudiarlo.

## Preguntas actuales

1. ¿Qué subconjunto de intenciones usa la primera misión y cómo se traduce exactamente a PX4?
2. ¿Cómo se conserva el tiempo original de una señal humana hasta `cause_t_us`?
3. ¿Qué hace cada capa cuando la propuesta está caducada, falta posición o se pierde el enlace?
4. ¿Cómo se comprueba que integrar echoAI conserva el comportamiento acotado y los contadores del runtime?
5. ¿Qué medidas en hardware reemplazarán las cifras de QEMU antes de prometer un plazo?

Lectura adicional: [qué es echOS](https://www.rxlabs.org/docs/echos/que-es), [arquitectura](https://www.rxlabs.org/docs/echos/arquitectura), [evidencia](https://www.rxlabs.org/docs/echos/evidencia). Esta guía documenta artefactos existentes; no vuelve a ejecutar ni amplía sus certificados.
