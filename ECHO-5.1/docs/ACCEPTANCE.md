# PCWORLD-1 · aceptación y límites

Este cuadro aplica a la primera entrega de desarrollo. «Comprobado» significa
que pasó la realización descrita, no una garantía universal. Los resultados de
calidad de un LLM, transferencia y superioridad multiagente siguen pendientes.

| ID | Realización | Estado y alcance |
|---|---|---|
| T01 | `test_pcworld_runner`, `test_pcworld_mcp`, `test_pcworld_legacy_runner`: PCWorld, MCP y los tres modos localdev cruzan el mismo ejecutor | Comprobado en este Linux. No se ejecutan candidatos en el proceso del supervisor. |
| T02 | Backend ausente y fallo propagado sin reintentar fuera de aislamiento | Comprobado; no cubre todas las configuraciones de kernel/systemd. |
| T03 | Vecinos, enlaces, archivos especiales, cambio de rutas durante lectura y escritura | Comprobado en los casos de snapshots y ejecución. El workspace debe permanecer quieto al capturarlo; no es un snapshot atómico del sistema de archivos ante cualquier escritor concurrente. |
| T04 | Workspace sólo lectura; padres, credenciales y autoridad de recibos sin montar; parches limitados a capacidades exactas | Comprobado. No protege frente a un administrador o a otro proceso host con autoridad sobre el supervisor. |
| T05 | HMAC, ancla externa, eliminación de sufijos, reescritura de cadena, reinicio y recuperación autenticada | Comprobado para `ReceiptStore` de PCWorld. El diario histórico de CodeMemory conserva su formato anterior y no equivale a esta custodia. |
| T06 | Exit cero, JSON de éxito autodeclarado y diagnósticos de tests alterados | Comprobado: observación y propiedad se separan; sólo referencias del host evalúan los valores. Los tests generados son datos no fiables. |
| T07 | Mismo HEAD, cantidad y longitud de archivos, con bytes diferentes | Comprobado: cambia la identidad de snapshot. También cuentan modos y directorios. |
| T08 | Cambio de contenido, suite, acción, política, semilla, dataset, configuración de proveedor y snapshots archivados | Parcial: la identidad compuesta cubre esos campos; `/usr` es un runtime host sin imagen hermética. Su huella no identifica todas sus dependencias. |
| T09 | Reparación posterior a un fallo similar y reproducción del caso en la nueva versión | Comprobado: recuperar un recuerdo no bloquea ni certifica la nueva solución. |
| T10 | Caché exacta con precondiciones, flag de hermeticidad y coste de consulta | API unitaria comprobada. Caché persistente de ejecuciones desactivada; falta runtime hermético para habilitarla. |
| T11 | Propiedad inventada, dominio inválido, oráculo/precondiciones incompatibles y abstención del crítico | Comprobado; no se convierten en contraejemplos válidos. |
| T12 | Fallo numérico real, conservación del input, nueva ejecución en la reparación y aceptación que incluye todos los casos retenidos | Comprobado con procesos aislados. No se implementó minimización automática del contraejemplo. |
| T13 | Dos reservas concurrentes sobre el último saldo; liquidaciones y costes que exceden reserva | Comprobado con un único supervisor y su objeto `Budget` compartido. No es contabilidad distribuida entre supervisores. |
| T14 | Parsing inválido, vacíos, reintentos, fuel finito, cuotas y deadlines | Comprobado. Las llamadas HTTP se prueban con respuestas locales simuladas, no con un proveedor LLM real. |
| T15 | Capacidad 4096 de recibos; identificadores WSP mayores de 255; escrituras interrumpidas y recuperación | Comprobado en las realizaciones unitarias. El piloto no agota físicamente CAM. No se ofrece reanudación de episodios a mitad de una operación ni persistencia general de usuario. |
| T16 | Barrera con orden determinista y replay WSP exacto de cada episodio | Comprobado para supervisor secuencial. La barrera se prueba por separado; no se ha ensayado un scheduler distribuido. |
| T17 | Límites reales de pared, CPU agregada, procesos, memoria, salida y tmpfs; hijos terminados | Comprobado en pruebas acotadas. El watchdog CPU tiene granularidad de 50 ms y se registra el exceso; MemoryPeak es cargo de cgroup, no RSS exacto ni energía eléctrica. |
| T18 | S/I2/F/E con entradas, herramientas, cuotas y checker comunes; S con autorrevisión, crítico una vez por versión | Comprobado con fixtures. No demuestra equivalencia de modelos desplegados ni superioridad de calidad. |
| T19 | Control sin LLM; importación del CAM, WSP, ATTEND y gate existentes; replay lógico | Comprobado. El router es fijo, no una Q aprendida; las ejecuciones y tiempos no son reproducibles byte a byte. |
| T20 | Registro de recetas con alcance y cuarentena; biblioteca principal vacía | Parcial: mecanismo unitario de metadatos. No hay extracción de conceptos, validación automática de su transferencia ni promoción de biblioteca. |

El criterio global de implementación de toda la investigación **no se declara
verde** mientras las obligaciones parciales no se cierren o se delimite un
contrato de release explícito. Pasar esta suite acredita esta entrega de
infraestructura, con los límites de arriba.
