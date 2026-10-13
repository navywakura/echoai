# PCWORLD-1 · aceptación y límites

Este cuadro incorpora la continuación del 13 de octubre. «Comprobado» significa
que pasó la realización descrita, no una garantía universal. El piloto local
terminó: S/I2/F/E empatan en 2/6. La transferencia general y la superioridad
multiagente siguen sin demostrarse; ver [informe](LOCAL-PILOT-20261013.md).

| ID | Realización | Estado y alcance |
|---|---|---|
| T01 | `test_pcworld_runner`, `test_pcworld_mcp`, `test_pcworld_legacy_runner`: PCWorld, MCP y los tres modos localdev cruzan el mismo ejecutor | Comprobado en este Linux. No se ejecutan candidatos en el proceso del supervisor. |
| T02 | Backend ausente y fallo propagado sin reintentar fuera de aislamiento | Comprobado; no cubre todas las configuraciones de kernel/systemd. |
| T03 | Vecinos, enlaces, archivos especiales, cambio de rutas durante lectura y escritura | Comprobado en los casos de snapshots y ejecución. El workspace debe permanecer quieto al capturarlo; no es un snapshot atómico del sistema de archivos ante cualquier escritor concurrente. |
| T04 | Workspace sólo lectura; padres, credenciales y autoridad de recibos sin montar; parches limitados a capacidades exactas | Comprobado. No protege frente a un administrador o a otro proceso host con autoridad sobre el supervisor. |
| T05 | HMAC, ancla externa, eliminación de sufijos, reescritura de cadena, reinicio y recuperación autenticada | Comprobado para `ReceiptStore` de PCWorld. El diario histórico de CodeMemory conserva su formato anterior y no equivale a esta custodia. |
| T06 | Exit cero, JSON de éxito autodeclarado y diagnósticos de tests alterados | Comprobado: observación y propiedad se separan; sólo referencias del host evalúan los valores. Los tests generados son datos no fiables. |
| T07 | Mismo HEAD, cantidad y longitud de archivos, con bytes diferentes | Comprobado: cambia la identidad de snapshot. También cuentan modos y directorios. |
| T08 | Cambio de contenido, suite, acción, política, semilla, dataset, proveedor y dependencias | Comprobado para `repair-v1`: rootfs Python íntegro sin `/usr` del host; exportación/restauración conserva identidad. El modo legacy sigue declarado no hermético. Kernel y hardware no están empaquetados. |
| T09 | Reparación posterior a un fallo similar y reproducción del caso en la nueva versión | Comprobado: recuperar un recuerdo no bloquea ni certifica la nueva solución. |
| T10 | Caché persistente exacta, precondiciones, dependencias del checker, custodia y coste de consulta | Comprobado para propiedades puras sobre resultados observados. Reinicio conserva los aciertos; cambio de identidad invalida; ausencia de testigos hace fallar auditoría. Se repite siempre el código candidato; no se presupone determinismo de Python arbitrario. |
| T11 | Propiedad inventada, dominio inválido, oráculo/precondiciones incompatibles y abstención del crítico | Comprobado; no se convierten en contraejemplos válidos. |
| T12 | Fallo numérico real, conservación del input, nueva ejecución en la reparación y aceptación que incluye todos los casos retenidos | Comprobado con procesos aislados y un diagnóstico sembrado con Qwen: 1/1, 51 recibos auditados. El piloto independiente no encontró contraejemplos. No se implementó minimización automática del contraejemplo. |
| T13 | Dos reservas concurrentes sobre el último saldo; liquidaciones y costes que exceden reserva | Comprobado con un único supervisor y su objeto `Budget` compartido. No es contabilidad distribuida entre supervisores. |
| T14 | Parsing inválido, vacíos, reintentos, fuel finito, cuotas y deadlines | Comprobado en pruebas y 24 episodios reales de Qwen: plantilla/tokenización exactas, esquema de salida y contabilidad. Tres inputs del crítico quedaron fuera del dominio; no se ejecutaron como contraejemplos. Los fallos con uso incoherente cargan toda la reserva o más si el servidor informa exceso. |
| T15 | Capacidad 4096 de recibos; identificadores WSP mayores de 255; escrituras interrumpidas y recuperación | Comprobado en las realizaciones unitarias. El piloto no agota físicamente CAM. No se ofrece reanudación de episodios a mitad de una operación ni persistencia general de usuario. |
| T16 | Barrera con orden determinista y replay WSP exacto de cada episodio | Comprobado para supervisor secuencial. La barrera se prueba por separado; no se ha ensayado un scheduler distribuido. |
| T17 | Límites reales de pared, CPU agregada, procesos, memoria, salida y tmpfs; hijos terminados | Comprobado en pruebas acotadas. El watchdog CPU tiene granularidad de 50 ms y se registra el exceso; MemoryPeak es cargo de cgroup, no RSS exacto ni energía eléctrica. |
| T18 | S/I2/F/E con entradas, herramientas, cuotas y checker comunes; S con autorrevisión, crítico una vez por versión | Comprobado con fixtures y 24 episodios reales, 860 recibos auditados. Cada brazo: 2/6 tareas; E−S y E−F = 0. Compartir techo presupuestario no equivale a consumir lo mismo; costes publicados por brazo y episodio. No acredita superioridad. |
| T19 | Control sin LLM; importación del CAM, WSP, ATTEND y gate existentes; replay lógico | Comprobado. El router es fijo, no una Q aprendida; las ejecuciones y tiempos no son reproducibles byte a byte. |
| T20 | Biblioteca persistente de recetas reparadas y procedencia; registro antiguo de cuarentena | Parcial: 0.9 publica la reparación de A y tres receptores reutilizan el código en una variante del mismo contrato, pasando sin reparar. Restauración y custodia comprobadas; no hay abstracción parametrizada, promoción/cuarentena integrada ni transferencia general demostrada. Ver COLEARNING-RESULTS-20261013.md. |

El criterio global de implementación de toda la investigación **no se declara
verde** mientras las obligaciones parciales no se cierren o se delimite un
contrato de release explícito. Pasar esta suite acredita esta entrega de
infraestructura, con los límites de arriba.
