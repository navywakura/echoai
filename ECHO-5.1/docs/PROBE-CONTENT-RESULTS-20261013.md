# Sondeos CSV y orden topológico · resultados y checklist ECHO-5.1

**E=8/12, F=8/12, S=6/12, I2=6/12. No hay desempate en tareas resueltas.**
Los cambios corrigen el contenido de los sondeos, pero no consiguen reparar
CSV ni Dependencias. ECHO-5.1 sigue pendiente de cierre científico y de las
obligaciones de implementación indicadas en la checklist de este mismo informe.

Implementación local `3964d54`, contrato `0.8.0-development`,
[plan congelado](PROBE-CONTENT-PLAN-20261013.md). Suite: **219 tests** en 83,635 s.
Revisión previa sin bloqueos; 27 archivos congelados permanecieron idénticos.
48/48 episodios, **2.445 recibos**, dos auditorías válidas, `destroyed == 0`,
sin timeouts del proveedor, errores de episodio ni exceso de presupuesto.

## Qué se cambió y qué se mantuvo

- CSV: ejemplo neutral `alpha,beta` en `format.input`, separado del esquema
  JSON; instrucciones explícitas sobre comillas y un único registro. Aplicado
  tanto al crítico de E/F como a la autorrevisión de S. No se insertó un caso
  final ni una salida esperada. El ejemplo de dos filas propuesto inicialmente
  habría incumplido el dominio de un solo registro.
- Dependencias: `reverse-alphabetical-edges` exige un grafo acíclico con alguna
  arista contraria al orden alfabético. Usa `nodes`/`edges`, no `deps`.
  Disponible para F y E; E la prioriza ante llamadas AST a `sorted()`/`.sort()`.
- F conserva la permutación por SHA-256 y semilla 20261013, sin buscar un orden
  que lo perjudique. Son seis categorías en Dependencias, cinco en las demás
  familias. Los perfiles antiguos conservan sus categorías; reproducir sus
  prompts exige sus revisiones congeladas anteriores.
- Misma matriz de doce variantes conocidas, semilla 47; S/I2/F/E,48 episodios
  contrabalanceados. Verificado que ejemplos públicos, casos finales y oráculos
  son idénticos a 0.7. No constituye un examen independiente.
- Mismo 14B Q4_K_M y revisión/hash, llama.cpp b11577, contexto 4096, salida 768,
  temperatura 0,2. Techos: 25k tokens, 50 herramientas, 12 llamadas LLM,6 críticas,
  128 fuel, 300 s CPU y 900 s de pared por episodio. Máximo dos reparaciones.
  Se mantiene la aceptación final común y la cobertura informativa.

## Resultado y coste completo

| Brazo | Aceptadas | Tokens observados | Llamadas LLM | Herramientas | Tiempo de episodios |
|---|---: |---: |---: |---: |---: |
| S | 6/12 | 20.082 | 32 | 254 | 386,069 s |
| I2 | 6/12 | 9.428 | 24 | 238 | 252,293 s |
| F | 8/12 | 52.459 | 52 | 383 | 589,135 s |
| E | 8/12 | 50.318 | 51 | 412 | 595,685 s |

| Familia | S | I2 | F | E |
|---|---: |---: |---: |---: |
| Intervalos | 2/2 | 2/2 | 2/2 | 2/2 |
| Registros | 0/2 | 0/2 | 2/2 | 2/2 |
| Rutas | 2/2 | 2/2 | 2/2 | 2/2 |
| CSV | 0/2 | 0/2 | 0/2 | 0/2 |
| Paginación | 2/2 | 2/2 | 2/2 | 2/2 |
| Dependencias | 0/2 | 0/2 | 0/2 | 0/2 |

E−S y E−I2: 2 victorias, 10 empates, 0 pérdidas. Ambas victorias están en
Registros; son dos variantes correlacionadas de una familia. Diferencia
observada: 16,67 puntos porcentuales. E−F: 12 empates. No confirma H1 ni H4
en general; tampoco demuestra que un agente único sea incapaz de reparar.

E gasta **4,08% menos tokens** que F (2.141 menos), pero **7,57% más
herramientas** (412 frente a 383), 1,11% más tiempo de episodios y más trabajo
lógico de consulta de memoria (1.024 frente a 481). No mejora todos los costes.
Total: 132.287 tokens observados y 159 llamadas LLM; sin cargos de uso desconocido.
La diferencia de tokens no es el 18,93% del piloto anterior y no se hereda
como una ventaja estable del router.

| Medida de crítica/reparación | F | E |
|---|---: |---: |
| Críticas realizadas | 30 | 27 |
| Refutaciones nuevas del crítico confirmadas | 5 | 6 |
| Intentos de reparación totales | 10 | 12 |
| Reparaciones adoptadas tras comprobación | 4 | 4 |
| Rechazos por categoría | 2 | 1 |
| Rechazos fuera de dominio | 1 | 0 |
| Sondeos duplicados | 6 | 6 |

Los cuatro parches aceptados de cada brazo corresponden a Registros y Rutas.
Los contadores `counterexamples` conservan también dos fallos públicos de Rutas
por brazo (F=7,E=8); no se atribuyen esos dos al descubrimiento del crítico.
S encontró además dos contraejemplos CSV mediante autorrevisión.

## Autopsia de las correcciones

**CSV: se resolvió el copiado observado, no la tarea.** Los seis sondeos CSV
nuevos de S/F/E son datos válidos; 0/6 copian el enunciado y 0/6 copian exactamente
`alpha,beta`. En 0.7 se observaban 21 copias del enunciado en 24 propuestas CSV
(sumando autorrevisión y críticos). Las longitudes de los episodios cambian,
por lo que estas tasas son descriptivas, no observaciones independientes.

E descubre comas entrecomilladas en la primera crítica de ambas variantes:
por ejemplo, `"alpha, beta",gamma`. F también encuentra refutaciones con campo
único entrecomillado y la categoría de espacios. S encuentra campos
entrecomillados. Los tres brazos con revisión realizan dos reparaciones por
variante y no las aceptan; I2 tampoco resuelve CSV.

En CSV00 E, el primer parche termina a mitad del argumento `quotechar` y no
es Python completo. El segundo utiliza un carácter de comilla incorrecto y
sigue fallando el testigo. No agotó 25k tokens: usó 2.445, conservó el candidato
anterior y obtuvo 1/6 comprobaciones finales. No hay evidencia para atribuir
estos errores a lentitud de GPU ni para afirmar que más GPU los resuelva.

**Dependencias: E elige una prueba discriminante, pero la reparación falla.**
En ambas variantes, E empieza por `reverse-alphabetical-edges` y produce
`z→a, y→b, x→c`. La referencia exige `x,c,y,b,z,a`; el candidato devuelve la
ordenación global `a,b,c,x,y,z`, incompatible con esas dependencias.

El primer parche sigue ordenando globalmente el resultado. El segundo elimina
esa ordenación, pero usa una cola FIFO que no garantiza el menor orden
lexicográfico entre los topológicos válidos. Rompe el ejemplo público: en 00
produce `c,n,l` en vez de `c,l,n`; en 01, `k,s,r` en vez de `k,r,s`.
Ambos parches se rechazan y el candidato retenido no supera el examen final.

F00 prueba una cadena alfabética y aristas duplicadas, obtiene dos categorías
soportadas y se detiene sin descubrir el fallo de orden. F01 sí alcanza la
categoría nueva, descubre una refutación y falla sus dos reparaciones de forma
análoga. La categoría nueva, por tanto, beneficia potencialmente a ambos brazos.

**Limitación adicional encontrada en el catálogo heredado.** En F01, el texto
de `disconnected-lex-order` no explicita que el validador exige un nodo aislado
además de aristas. El modelo ofrece, entre otros, dos cadenas desconectadas
sin nodos aislados: es un grafo desconectado, pero el detector lo rechaza.
No debe describirse sin matices como un fallo semántico del modelo. Hace falta
alinear la definición y su guía o ampliar justificadamente el detector en una
versión posterior, con controles y nueva medición. No se cambió a mitad de
esta campaña ni se recalificaron episodios retrospectivamente.

En ese episodio F usa 7.132 tokens frente a 3.637 de E: 3.495 de diferencia,
más que el ahorro global de 2.141 (en el resto E gasta 1.354 más). Esto impide
atribuir el ahorro completo a una ventaja general del router. La auditoría
actual confirma aplicación consistente del detector, no que su definición
sea exhaustiva o coincida con toda interpretación del texto.

**Resto de familias: ** Intervalos, Rutas y Paginación pasan en todos; Registros
pasa después de crítica/reparación en E/F y falla en S/I2. No hay aciertos
nuevos respecto a 0.7. El beneficio medido de coordinación continúa localizado.

## Integridad, recursos y cierre de la ejecución

La auditoría principal y una segunda ejecución del mismo comando `audit`
validan 48 episodios/2.445 recibos sin discrepancias. Es replay autenticado de
propiedades con referencia independiente, no nueva inferencia ni repetición
física completa. Los 27 archivos congelados permanecen sin cambios.

Kaggle privado, versión 2, solo inferencia; candidatos y verificadores locales
en el rootfs fijado y Bubblewrap/cgroups. T4 con 49/49 capas cargadas en GPU.
477 solicitudes del transporte, todas HTTP200. Worker completado y detenido;
supervisor, broker y túnel inactivos. No hay procesos de inferencia pendientes.

Incidencia de arranque: el primer paquete subido usó `inference-relay.py`
en lugar de `inference_relay.py`. Se conservó y se generó la versión 2 con
ese nombre corregido antes del primer episodio. No se descartaron tareas ni
se cambió el protocolo. La cuota consumida incluye ese arranque, no se oculta.

Worker correcto: 1.988,955 s (**33 min 09 s**), incluidos 158,819 s de preparación.
Cuota mostrada antes/después: 24,71 h → **24,12 h**, diferencia aproximada 0,59 h
incluyendo la incidencia. La cuota está redondeada; no es una medida eléctrica.
No se hizo push ni publicación. S6 permanece aplazado.

Artefactos locales preservados:

- `ECHO-5.1/artifacts/probe-content14b-pilot-20261013`: resultados, diarios,
  tareas congeladas, evidencia y auditoría.
- `ECHO-5.1/artifacts/probe-content-control-20261013`: manifiesto, configuración,
  segunda auditoría, análisis y registro de transporte. Contiene credenciales
  privadas; no exportar la carpeta completa.
- `ECHO-5.1/artifacts/kaggle-probe-content14b-output`: evidencia del worker.
  Su entrada incluye la capacidad temporal del puente detenido; no publicar.

Hashes:

- `result.json`: `c7c065381cabd08f75e8b96b917f7550e8a62ec843599f320280463f9bddc58c`
- `audit.json`: `6c338425f7e2f2cae333ccf681d90c70f8880067b1eb04cf8162feca1d1b4b7e`

## Qué debe verificarse después

Primero aislar la reparación en microensayos: código completo y manejo correcto
de comillas CSV; en grafos, preservar dependencias y escoger el mínimo entre
nodos disponibles en cada paso. Medir con casos públicos y contraejemplos
observados; no inyectar las soluciones finales reservadas ni ampliar recursos
solo a E. Corregir también la ambigüedad del catálogo heredado antes de atribuir
coste a su selección. Son próximos experimentos, no correcciones ya medidas.

Después, nuevas familias y repeticiones preregistradas, junto a ablaciones de
memoria/selección y controles fuertes. El cambio actual demuestra que generar
mejores pruebas puede aumentar refutaciones sin aumentar soluciones. No justifica
seguir ampliando categorías indefinidamente ni declarar verde por aproximación.

## Checklist de ECHO-5.1: alcance y obligaciones

Esta checklist reúne el contrato T01–T20 y las hipótesis H1–H4. «Comprobado»
se refiere a los casos y al host ensayados. La infraestructura permite medir;
no acredita por sí sola transferencia, invulnerabilidad ni ventaja del router.

| Estado | Elemento | Evidencia o verificación pendiente |
|---|---|---|
| [x] Comprobado | T01–T02: una frontera de ejecución | PCWorld, MCP y modos localdev pasan por Bubblewrap/cgroup v2; backend ausente falla sin ejecutar fuera del sandbox. |
| [x] Comprobado con límites | T03–T04: archivos y autoridad | Snapshots, enlaces, rutas, workspace de solo lectura y capacidades de parche. No protege contra un administrador del host; la captura no es atómica ante todo escritor concurrente. |
| [x] Comprobado | T05: custodia de recibos | HMAC, encadenamiento, ancla externa y recuperación autenticada. Es consistencia bajo el modelo de amenaza, no seguridad absoluta. |
| [x] Comprobado | T06–T07: evidencia e identidad | Se separan ejecución, propiedad y resultado; cambian las identidades al cambiar bytes, modos o directorios. Exit 0 no equivale a tarea resuelta. |
| [x] Comprobado acotado | T08: runtime hermético | Rootfs Python exportable sin montar `/usr` del host para reparación. Kernel y hardware quedan fuera; rutas legacy siguen declaradas no herméticas. Falta reproducción en otra máquina. |
| [x] Comprobado | T09: recuerdos revisables | Un fallo similar recuperado no veta una nueva solución sin volver a comprobarla. |
| [x] Comprobado acotado | T10: caché exacta persistente | Solo propiedades puras sobre resultados observados, identidad completa y testigos; el candidato vuelve a ejecutarse. Caché desactivada en la comparación principal. |
| [x] Comprobado | T11: crítico no fiable | Dominio, propiedad, precondiciones, oráculo y etiqueta se validan fuera del LLM; propuestas inválidas no cuentan como refutaciones. |
| [x] Comprobado acotado | T12: reparación CEGIS | Testigo reproducido, feedback entrada/salida/contrato, guardas públicas y de contraejemplos, rollback y máximo dos reparaciones. Funciona en ejemplos medidos; no implementa minimización automática del contraejemplo. |
| [x] Comprobado | T13–T14: contabilidad y límites | Reservas antes de llamadas, preflight nativo, cargos de errores, fuel, cuotas y plazos. Un supervisor; no contabilidad distribuida. |
| [x] Comprobado acotado | T15–T16: persistencia y orden | Recuperación autenticada, capacidad de recibos, WSP y replay; supervisor secuencial. Sin reanudación arbitraria a mitad de operación ni scheduler distribuido demostrado. |
| [x] Comprobado acotado | T17: límites reales | Pared, CPU, procesos, memoria, salida y tmpfs probados. Granularidad del watchdog registrada; memoria de cgroup no es medición eléctrica. |
| [x] Implementado y ejecutado | T18: S/I2/F/E comparables | Mismo modelo, tareas, herramientas, techos y criterio final; orden contrabalanceado. S tiene autorrevisión, I2 dos propuestas. No gastan lo mismo; falta estudiar curvas de éxito frente a coste. |
| [x] Comprobado | T19: núcleo basal | Control sin LLM en NEXUS-0, CAM/WSP/gate existentes y registro observable. Router heurístico explícito, no política aprendida; tiempo y ejecuciones Python no son deterministas byte a byte. |
| [ ] Parcial | T20: biblioteca de conceptos | Registro y cuarentena unitarios. Faltan extracción, validación de transferencia, promoción y demostración de reutilización. Biblioteca vacía en la comparación. |
| [x] Implementado | Proveedor e inferencia real | 7B CPU y 14B Q4_K_M en T4 con revisión/hash y configuración fijados. Candidatos y oráculos permanecen locales, separados del servicio de inferencia. |
| [x] Implementado y probado | Remediación 0.8 | Ejemplo CSV de datos separado del esquema; categoría inversa acíclica compartida; señales AST, validación y auditoría. 219 tests pasan. No presupone que el modelo genere buenos sondeos. |
| [x] Ejecución auditada | Campaña 0.8 | 48 episodios, 2.445 recibos, dos auditorías válidas, 27 hashes sin cambios; E=F=8/12, S=I2=6/12. |
| [ ] Pendiente | Reparación completa de CSV y grafos | Los nuevos testigos detectan fallos; los parches no satisfacen contrato y no-regresión. Ambos 0/2 en E/F. |
| [ ] Pendiente | Semántica de categoría heredada | Alinear la guía de `disconnected-lex-order` con su requisito de nodo aislado y medir de nuevo sin recalificar esta campaña. |
| [ ] Pendiente | H1: ventaja frente a agente único fuerte | La muestra de desarrollo describe diferencias. Falta confirmación preregistrada en nuevas familias, repeticiones y estimación de incertidumbre; no reutilizar estas doce variantes como examen ciego. |
| [ ] Pendiente | H2: aporte de memoria compartida | Ablación con/sin recuerdos manteniendo los demás componentes, presupuesto y tareas. Medir repetición de errores y falsos vetos. |
| [ ] Pendiente | H3: utilidad neta del crítico | Separar descubrimiento, reparación y coste; compararlo con autorrevisión/alternativas fuertes bajo presupuesto comparable. Más refutaciones no garantizan más soluciones. |
| [ ] Pendiente | H4: aporte del router basal | Repetir órdenes y semillas, congelar criterios y aislar selección de categorías del uso de memoria. Un desempate en desarrollo no sería confirmación causal general. |
| [ ] Pendiente | Corpus externo y confirmación | Nuevas estructuras y familias o fallos reales con oráculo independiente. Aquí los bugs son inducidos en seis familias conocidas. Congelar protocolo antes de abrir la confirmación. |
| [ ] Pendiente | Reproducibilidad fuera de este host | Instalación/restauración de runtime, modelo, fuentes y auditoría en otro Linux; documentar dependencias admitidas y verificar sus identidades. |
| [ ] Pendiente | Alcance de release y cierre | Definir qué capacidades son obligatorias, cerrar o delimitar T20 y emitir manifiesto auditable. Preparar exportación sin credenciales privadas. No hay push ni publicación en esta entrega. |
| Aplazado | S6 | Sigue fuera de este trabajo, hasta después de ECHO-5.5; no es el bloqueo actual de PCWORLD-1. |

El cierre científico requiere evidencia para las hipótesis que se decida
reivindicar. Una release acotada de infraestructura podría tener otro alcance,
pero no debe etiquetarse como demostración de superioridad general de ECHO.
