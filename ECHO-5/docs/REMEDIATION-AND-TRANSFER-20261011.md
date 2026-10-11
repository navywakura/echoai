# ECHO-5: diagnóstico contrastado y plan de mejora

11 de octubre de 2026. Revisión de código, contratos, informes y recibos de
desarrollo disponibles. Este documento propone intervenciones posteriores;
no modifica las fuentes ni los criterios de la campaña activa, no acredita
capacidades nuevas y no reabre S6. Los dos revisores auxiliares trabajaron en
lectura, sobre ámbitos distintos. No se abrieron exámenes reservados.

La dificultad de transferencia es real. El diagnóstico recibido también
mezcla versiones, denominadores y garantías. El contrato S6 consultado está
fechado el 26 de septiembre de 2026 y el diseño ejecutable de ECHO-5 el 10 de
octubre. Esas fuentes no respaldan «dos años de S6» ni «un mes de ECHO-5».
B24 es una etiqueta de revisión; no equivale a 24 ensayos independientes y
completos. El historial conserva descubrimientos parciales y resultados
negativos sin acreditar automejora global.

| Afirmación | Qué permite decir la evidencia |
|---|---|
| Determinismo garantiza ausencia de errores y generalización | Repetir un algoritmo determinista también puede repetir un error. La exactitud del replay verifica repetibilidad dentro de su contrato. |
| Todo ECHO se reproduce byte a byte | Los recibos lógicos tienen contratos de replay; Gazebo/PX4 usa física y tolerancias, sin promesa de igualdad binaria entre vuelos. |
| Causalidad explícita equivale a explicación causal correcta | Existe trazabilidad de observación, propuesta y consecuencia. Atribuir una causa requiere intervenciones y controles; DRONE3 ya documentó marcas espurias de cambio externo. |
| ECHO no alucina | El solver devuelve `test_verified: false` incluso con consenso en las demostraciones. No existe garantía universal de respuestas correctas ni certificación de uso crítico. |
| 500.000 neuronas | La guía de 500k corresponde a capacidad asociativa. El diagnóstico LIF del panel ejecuta 256 unidades y no gobierna esos episodios. |
| ARC-1 sólo mejora un 55 % | 20/400 → 31/400 son +11 tareas y +2,75 puntos porcentuales; 55 % es la mejora relativa. Es un resultado limitado de aquel candidato, no una puntuación actual de ECHO-5. |
| ARC-3 empeora en todas las métricas | 13/112 → 11/112 pierde niveles; el score local del contrato aumentó. Ambas métricas deben conservarse separadas. |
| La robótica real ha fracasado | Hay resultados negativos y positivos en simulación; no se ha evaluado aquí un robot físico. |

Las referencias históricas están en [el inventario de cierre de 4.5](../../docs/ECHO45-CLOSURE-EVIDENCE-20261009.md),
[el contrato S6](../../docs/ECHO45-S6-AUTOMEJORA-DESIGN.md),
[el diseño ECHO-5](IMPLEMENTATION-DESIGN.md) y [DRONE3](../../docs/DRONE3-RESULTS.md).
Los resultados cognitivos auditados de ECHO-5 —48/48 compatibles, 54/56 en
MiniGrid/BabyAI y 256/256 en el currículo adaptativo— mantienen los límites
del [checklist](CLOSURE-CHECKLIST.md). MiniGrid/BabyAI es un entorno externo,
aunque su selección de misiones y adaptador también requieren evaluación.
No se deduce ni generalización abierta ni ausencia completa de transferencia.

En robótica, la corrección actual aborda un problema instrumental concreto:
PX4 podía terminar antes de cerrar el ULog. El parser rechazó correctamente
el archivo truncado. Se añadió un cierre acotado del logger y comprobación
independiente del orden y coherencia de sus recibos. La repetición completó
6/6 criterios y su auditoría confirmó `valid=true`, `calibration_pass=true`.
La cadena continuó con desarrollo. El [estado vivo](CLOSURE-RUN-STATUS.md)
prevalece sobre ese corte. Los casos de batería baja ya exigían aterrizar
seguro sin completar la misión: forzar la meta habría roto el contrato.
La confirmación física anterior permanece negativa.

El principal cambio de método consiste en localizar dónde se pierde una
solución antes de ampliar el sistema. Esta clasificación debe poder terminar
en «causa no determinada»; no debe inventar una explicación para cada fallo.

| Etapa | Diagnóstico que distingue causas | Corrección condicionada al resultado |
|---|---|---|
| Percepción y objetos | Sobre desarrollo conocido, comprobar si una representación independiente conserva las entidades necesarias para un programa testigo. | Comparar varias segmentaciones tipadas —conectividad y objetos multicolor, por ejemplo—, manteniendo incertidumbre y contabilizando todas las vistas. |
| Lenguaje de programas | Probar un testigo conocido con el ejecutor separado. Una búsqueda agotada no prueba que el lenguaje sea incapaz. | Añadir la mínima operación relacional necesaria sólo cuando exista una familia identificada que la necesite. |
| Búsqueda | Si un testigo ejecutable resuelve la tarea pero el buscador no lo alcanza, registrar su prefijo, profundidad, coste y punto de descarte. | Reservar presupuesto para prefijos diversos; comparar el orden actual con búsqueda por objetivos intermedios y composición bidireccional. |
| Selección y generalización | Varios programas encajan en las demostraciones pero difieren fuera de ellas. | Retener alternativas y contrastarlas con ejemplos de desarrollo independientes; abstenerse cuando la evidencia no discrimine. |
| Ejecución | El plan es admisible pero fallan observación, ACK, llegada o exportación de evidencia. | Reparar el adaptador o el estimador responsable, preservando el criterio de seguridad y la evidencia negativa. |

El código da motivos concretos para investigar estas etapas. `grounding.py`
segmenta objetos monocromos de conectividad cuatro, con fondo estimado por el
borde y papeles de una lista finita. `programs.py` define un lenguaje cerrado
de hasta 16 pasos. La síntesis de `solver.py` usa, por defecto, profundidad 4,
frontera 24 y 12.000 candidatos; sus máximos admitidos también son finitos.
Ordena estados por diferencias de forma y píxel sobre las demostraciones.
Una composición útil puede necesitar un intermedio con peor puntuación, por
lo que esa ordenación no garantiza retener su prefijo. Es un mecanismo
posible de fallo; aún no está demostrado que explique los porcentajes ARC.

La síntesis declara `consensus_scope=first_matching_retained_tier` y
`search_space_exhaustive=false`: consenso dentro de la frontera examinada.
La biblioteca de `concepts.py` conserva programas y evidencia, con un máximo
de 64 conceptos. Reutilizar un programa no inventa por sí solo nuevas
operaciones ni sus condiciones universales de aplicación. Aprender
subprogramas parametrizados podría ampliar la reutilización, pero exige
comprobar transferencia frente a una biblioteca fija y otra del mismo tamaño.
DreamCoder ofrece un antecedente de aprendizaje conjunto de biblioteca y
guía de búsqueda, no una garantía para ECHO.
[Ellis y colaboradores](https://arxiv.org/abs/2006.08381).

La primera intervención prioritaria es mejorar el aislamiento de las
comparaciones. Ya hay controles, auditorías y separación de salidas reservadas;
no procede afirmar que faltan por completo. Sí hay cuatro límites específicos:

| Prioridad | Hallazgo comprobado | Intervención propuesta y evidencia exigida |
|---|---|---|
| P1 | En `sandbox.py`, `passive` sólo gira/avanza; `no_planning` no implementa depositar para `putnext`. La comparación mezcla planificación, exploración y habilidades disponibles. | Añadir un control con los mismos parser, memoria, acciones, manipulación y planificación, cambiando únicamente `_explore` por frontera cercana o aleatoria. Conservar los controles anteriores como referencias. Comparar éxito, acciones y trabajo por familia con pares y presupuesto iguales. |
| P1 | `transfer.py` genera familias estructurales, pero dentro de plantillas limitadas. `curriculum.py` selecciona la regla verdadera del mismo conjunto finito de 16 programas que recibe el aprendiz. | Un segundo generador independiente debe variar topología, número de objetos y distractores dentro de la semántica soportada. Separar identificación de reglas conocidas, composición nueva y operaciones fuera de lenguaje. Los casos fuera de lenguaje se evalúan como reconocimiento de límites, no como soluciones exigibles. |
| P2 | El coste del currículo está condicionado a tablas exhaustivas compartidas, limitación ya documentada. | Comparar también controles secuencial/aleatorio que calculen sólo los candidatos elegidos. Publicar coste de preparación, selección, consultas, inferencia y auditoría por separado. No atribuir ahorro sobre un control optimizado sin medirlo. |
| P2 | En misiones personalizadas, actor y evaluador usan `parse_mission`; la instrucción nativa se deriva de ese parseo. | Construir referencias semánticas independientes para orden, localización y referentes, con trayectorias que deben aceptar/rechazar. Un error común podría pasar el replay; cualquier falso éxito frente a la referencia exige corrección. Esto no demuestra fuga de etiquetas ni invalida automáticamente las misiones nativas. |

Los puntos de integración existentes son `sandbox.ObservationActor.choose`
y `_explore`, `sandbox_eval.ExternalEnvironment`, `transfer.run_benchmark`
y `curriculum.run_benchmark`. Las interfaces y los controles nuevos se
especificarán en otra revisión. Se conservarán WSP, Recorder y el verificador.

Para el nuevo protocolo se proponen mínimos por familia, además del agregado.
Una media del 75 % en cuatro familias equilibradas podría ocultar cero en una
de ellas; no se ha observado ese cero en la confirmación 48/48. La propuesta
es exigir al menos 75 % en cada familia soportada y medir la caída entre
generadores; una caída mayor de diez puntos sería un fallo de robustez de
esa extensión. Son umbrales propuestos para una revisión nueva, no cambios
retroactivos al contrato vigente ni porcentajes prometidos.

La utilidad de la exploración se evaluará con intervalos emparejados y un
margen de interés registrado antes de confirmar. Un piloto sirve para
estimar variabilidad, coste y tamaño de muestra; un intervalo amplio queda
inconcluso. No basta una victoria neta para declarar superioridad general.
Se informarán errores y cobertura además de abstenciones: rechazar todos
los problemas puede evitar respuestas falsas sin resolver ninguno.
CoinRun es un antecedente de por qué separar entrenamiento y evaluación
procedurales y ampliar las instancias no elimina automáticamente el
sobreajuste. [Cobbe y colaboradores](https://arxiv.org/abs/1812.02341).

La autopsia ARC usará primero tareas de desarrollo ya expuestas y distinguirá
`NO_PROGRAM`, presupuesto agotado, ambigüedad, predicción incorrecta y error
del instrumento. El último lote V3 de calibración dio 0/16 ARC-1 y 0/16 ARC-2,
35 salidas absteniéndose en 32 tareas y cero errores/timeouts. Eso no prueba
imposibilidad del DSL ni una regresión emparejada frente al candidato 31/400.
La existencia de un testigo sólo acredita expresividad en esos casos; el
testigo permanecerá fuera del investigador. No se diseñarán reglas usando
salidas de examen. ARC mide adquisición de habilidades en tareas nuevas;
una cifra de entrenamiento no sustituye esa medición.
[ARC Prize](https://arcprize.org/arc-agi).

S6 conserva el aplazamiento hasta después de ECHO-5.5. La evidencia disponible
ya distingue causas: B22-S no usó LLM; en B23-R4 hubo 16 propuestas duplicadas,
12 inactivas y ocho activas con pérdidas. Los dos modelos alcanzaron 61→65
niveles, pero no conservaron el score individual. El brazo LLM no utilizó el
reparador M23 y recibía detalles del último intento en lugar del padre
pertinente. Pasar de 7B a 14B no eliminó esas limitaciones. El control humano
61→67 demuestra expresividad local, no descubrimiento autónomo.

Cuando se retome S6, el diagnóstico debe comparar enumeración acotada,
investigador corregido y controles, con el mismo lenguaje, oportunidades y
presupuesto. Debe entregar evidencia del padre pertinente, medir activación
real, mantener ramas conservadoras y comprobar cada hijo completamente.
B24 ya propone correcciones relacionadas: habrá que reconciliar sus recibos
antes de duplicarlas. No se relanza en esta revisión. Sus archivos locales
del 10 de octubre conservan `CHECKPOINT_READY` y `WAITING_GPU_QUOTA`; no
constituyen un nuevo fracaso científico cerrado ni un pase.

La secuencia propuesta es terminar la validación actual con su contrato,
cerrar el informe con el resultado que produzca y abrir después una revisión
separada de controles y transferencia. Cada cambio tendrá ablación propia;
no se mezclarán nueva representación, buscador, varios agentes y otro LLM en
un solo ensayo. Si la corrección no mejora su métrica registrada, se conserva
el negativo y se reconsidera el mecanismo. El número de versión no será
evidencia de progreso.

La propuesta de valor demostrable a corto plazo es un controlador experimental
auditable para misiones acotadas, con memoria, planificación, abstención y
supervisión de seguridad en simulación. Coste lógico bajo, coste de CPU,
consumo eléctrico, corrección formal y aptitud para despliegue son afirmaciones
distintas. Ningún resultado de esta revisión acredita medicina, finanzas,
defensa, autonomía física general ni ausencia universal de errores.
