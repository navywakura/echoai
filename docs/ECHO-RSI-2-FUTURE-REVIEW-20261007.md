# ECHO-RSI-2 investigación de evolución y especialización verificadas

7 de octubre de 2026. Investigación privada para la línea ECHO-5 → ECHO-5.1 → ECHO-5.5 → ECHO-RSI-1 → ECHO-RSI-2. Complementa el [plan de RSI-2](ECHO-RSI-2-RESEARCH-PLAN.md). Sus experimentos y presupuestos son propuestas; este informe no inicia trabajos GPU, publica artefactos ni concede cierres.

La propuesta de Roger reúne cuatro intervenciones que merecen medirse: memoria de investigación, evolución de programas, especialización de colaboradores y entrenamiento de adaptadores. Colab y Kaggle permiten empezar a investigarlas con pocos modelos y tareas acotadas. Un laboratorio que consigue mejoras repetidas y transferibles sería un resultado útil. La aceleración exponencial, la equivalencia con modelos frontier y una personalidad adquirida requieren evidencia adicional; no se deducen de un torneo ganado ni de cambiar una etiqueta de rol.

Los vídeos aportados se consideran escenarios narrativos. Se examinan los mecanismos descritos en el resumen del propietario; no se ha recuperado su contenido audiovisual completo para verificar las atribuciones o marcas de tiempo. Las decisiones técnicas siguientes se fundamentan en los registros locales y las fuentes primarias enlazadas.

**El antecedente de ECHO es más concreto que la analogía del vídeo.** [DREAM-D v3](ECHO4-DREAM1-D-V3-RESULTS.md) cerró su perfil WORLD-1 restaurado con 900/960 diagnósticos. El brazo sin Qwen también obtuvo 900/960. Hubo una promoción inicial y conservación posterior, no una sucesión de mejoras: existe utilidad de selección basada en historia, mientras la contribución del modelo permanece sin demostrar en ese perfil. [ROLES v5](ECHO4-ROLES1-V5-RESULTS.md) dedujo competencias y redujo consultas en una tribu discreta; su resultado neto no superó al reparto fijo. Estos límites obligan a medir productividad además de coordinación.

PROBE2 cribó 874 propuestas y encontró dos elegibles en desarrollo A, con 10.048 partidas contabilizadas y cero llamadas LLM. Sus trazas localizaron posibles consumos de HOLD; los efectos se obtuvieron ejecutando las políticas modificadas. [Resultado](../lab/seed/s6probe2-20261001/result.json), [cribado y verificación](../seed/s6probe2.py), [ejecutor](../seed/s6probe1.py). RSI1-R1 mantuvo rojo su examen de capacidad y productividad: el sistema recursivo no superó al control aleatorio y el examen del investigador no produjo promociones. [Resultados](ECHO-RSI1-RESULTS.md), [recibo](../lab/research/echo-rsi1-recovery1-20261002/result.json).

La validación amplia del ganador B21 ilustra el problema de transferencia: 740 → 748 niveles, pero con pérdidas en los casos 144 y 154. El instrumento y su auditoría fueron válidos; la conservación exigida falló. [Recibo B22-V](../lab/seed/s6b22-20261006/v-broad.json). Este informe no convierte esa cohorte ya consultada en un examen nuevo.

**La evidencia externa más próxima es la evolución del investigador.** Darwin Gödel Machine conserva un archivo de variantes, modifica código de agentes y evalúa su rendimiento empíricamente. Justifica estudiar caminos alternativos y herramientas mejoradas; sus resultados no garantizan crecimiento indefinido. [DGM, publicación original](https://arxiv.org/abs/2505.22954). Hyperagents amplía ese planteamiento permitiendo modificar el mecanismo que genera futuras mejoras y estudia transferencia entre dominios. Es especialmente pertinente para separar mejora del resolutor y mejora del investigador. [Hyperagents](https://arxiv.org/abs/2603.19461).

La escala de esos ensayos importa. El apéndice D.2 de Hyperagents estima aproximadamente 33 millones de tokens para 100 iteraciones de automodificación, excluyendo evaluación. Nuestro primer ensayo debería reproducir un mecanismo pequeño, con un límite de oportunidades y coste. La tabla de modelos y el presupuesto del trabajo no permiten atribuir sus resultados directamente a un 7B local. [Configuración y coste](https://arxiv.org/html/2603.19461v1).

| Idea recibida | Interpretación ejecutable en ECHO | Condición para conservarla |
|---|---|---|
| Selección natural de agentes | Archivo de programas, selectores y adaptadores con linaje; empezar con 2–4 candidatos colaboradores | Superar búsqueda aleatoria y un proponente con más muestras, igualando presupuesto total |
| Reescritura recursiva | Cambios candidatos en biblioteca, elección de ejemplos y código del investigador, evaluados fuera de la versión estable | El investigador evolucionado descubre mejoras posteriores en tareas nuevas mejor que el inicial |
| Memoria acumulativa | Índice de experiencias con versión, contexto, coste, propuesta y resultado comprobado | Reducir repetición inútil y aumentar utilidad en datos nuevos frente a memoria retirada |
| Subagentes y alianzas | Compartir tareas parciales y recibos; repartir trabajo según competencia medida | Ganar calidad o eficiencia frente a ejecución secuencial con el mismo cómputo |
| Comunicación por vectores | Investigación posterior con modelos locales e interfaces compatibles | Ventaja medida frente a mensajes tipados, incluidos alineamiento y entrenamiento |
| Hacer más con menos | Caché exacta, selección de episodios y uso de modelos pequeños donde bastan | Menor coste por solución correcta, incluyendo evaluación y mantenimiento |
| Respaldos y continuidad | Checkpoints privados y restauración tras interrupciones accidentales | Restauración comprobada; una parada explícita se aplica a todas las instancias |

**Dreaming necesita un ejecutor de transiciones.** Una trayectoria que registra derecha → puerta no dice qué habría pasado al ir a la izquierda. Se puede consultar sin nuevos pasos una rama que ya existe y cuyo estado coincide. Para una rama nueva se necesita restaurar estado completo y continuar en el simulador, o reiniciar el episodio. El estado incluye RNG, temporizadores, entorno, memoria y versión de la política. Si falta una transición, su resultado queda desconocido.

Una siguiente condición DREAM-EXEC-1 compararía ejecución completa con ejecución desde checkpoint en las mismas acciones candidatas. Exigiría coincidencia de observaciones, resultados y estado relevante, incluiría divergencias, RESET, temporizadores y casos terminales, y mediría ahorro efectivo. El ahorro solo existe cuando restaurar y continuar cuesta menos que recomenzar. Cero tokens LLM durante la evaluación conserva el coste de CPU, memoria y almacenamiento. Si se aprende un modelo del mundo, sus predicciones son hipótesis: se contrastan en el entorno independiente antes de una promoción.

DreamCoder aporta un mecanismo cercano a nuestro problema de DSL: aprender abstracciones de programas y entrenar una guía de búsqueda mediante ciclos wake-sleep. DreamerV3 aporta planificación y aprendizaje a través de un modelo aprendido del mundo. Ambos estudian mecanismos distintos; reutilizar un archivo histórico no implementa automáticamente ninguno de ellos. [DreamCoder](https://arxiv.org/abs/2006.08381), [DreamerV3](https://arxiv.org/abs/2301.04104).

El almacén debe conservar los caminos realmente ejecutados y las hipótesis pendientes con estados distintos. Guardaría resúmenes y hashes de todos los intentos, y trazas completas de promociones, anomalías y una muestra fijada. La memoria de rechazos se condiciona por base, programa normalizado y dominio: una propuesta rechazada en un caso no queda prohibida universalmente. Las notas visibles describen observaciones, hipótesis, acciones y resultados; no inventan una experiencia subjetiva o una cadena de pensamiento privada.

**La puntuación de especialización debe depender de efectos verificados.** Un fallo de compilación del propio agente no acredita competencia como inspector. Discrepar muchas veces tampoco acredita que tenga razón. Para un sintetizador, el crédito procede de cambios útiles que sobreviven al evaluador. Para un crítico, procede de errores reales detectados en propuestas o escenarios válidos, descontando falsas alarmas y rechazos incorrectos. Los fallos autoinducidos no generan puntos por repararlos.

La fricción puede ser una señal de dificultad, incertidumbre o mala representación. Mantendría un vector con competencia, falsos positivos, fallos de formato, novedad efectiva y coste por rol/contexto. Una función de utilidad propuesta sería:

```text
U(i, rol, contexto) = contribución marginal verificada
                     − λt · tiempo
                     − λg · coste de GPU
                     − λe · coste de evaluación
                     − λf · falsas alarmas
```

Las unidades se normalizan y los coeficientes se fijan antes del ensayo. No se resta cada fallo científico como si fuera un error del instrumento: un contraejemplo útil puede justificar coste de exploración. La atribución es parcial; retirada de un colaborador y pruebas de reemplazo en una muestra fijada permiten estimar contribuciones sin asumir que el último mensaje causó todo el éxito.

Un selector por bandits contextuales podría explorar roles y explotar competencias observadas, con límites de reasignación para evitar oscilaciones. Su aplicación a ECHO es una hipótesis de ingeniería, apoyada en el marco de aprendizaje por recompensas contextuales, no un resultado establecido para nuestros agentes. [LinUCB](https://arxiv.org/abs/1003.0146). La discrepancia dialéctica ayuda a priorizar una prueba; solo su desenlace recibe crédito. Cambiar temperatura o instrucciones tampoco demuestra que el modelo haya adquirido una capacidad nueva.

Conservaría la exploración cuando haya incertidumbre sobre su utilidad, y registraría una recomendación de cambio de rol como hipótesis hasta medirla. SITRA mantiene el evaluador y sus umbrales custodiados; TIKKUN genera reparaciones dentro del presupuesto. Un estancamiento no autoriza al reparto de roles a relajar el criterio de aceptación. En este diseño, el inspector LLM es un colaborador; el juez final conserva independencia.

La afirmación de que los roles emergentes son superiores a roles fijos debe probarse. El estudio *Towards a Science of Scaling Agent Systems* encuentra ventajas y pérdidas según estructura de la tarea, incluidos costes de coordinación y propagación de errores. Recomienda contrastes específicos, no aumentar el número de agentes por defecto. [Estudio controlado](https://arxiv.org/abs/2512.08296).

Un ensayo ROLE-POLICY-1 propuesto compararía un agente secuencial, varios proponentes independientes, roles fijos, roles adaptativos por efectos y roles adaptativos por desacuerdo. Todos compartirían modelo, herramientas, tareas y límite total de generación/evaluación. Se medirían soluciones exactas, aportación marginal, precisión de la crítica, diversidad útil, latencia y coste. Una segunda cohorte cambiaría la distribución de problemas para comprobar reasignación. Solo una mejora estable en esa cohorte respaldaría especialización adaptativa; seguiría sin demostrar personalidad subjetiva.

**La comunicación inicial debe aprovechar la representación existente.** El núcleo conserva WSP y sus invariantes; la coordinación de propuestas utiliza mensajes tipados y referencias a recibos mediante las interfaces existentes. No se crea un segundo bus. Activaciones, embeddings y KV caches de modelos diferentes no constituyen un idioma compatible por defecto. Hay que alinear espacios, escoger interfaces y evaluar cuánto cuesta ese alineamiento. Una API de chat corriente tampoco entrega libremente estados ocultos internos.

Coconut estudia razonamiento en un espacio latente bajo una arquitectura y un entrenamiento definidos. No valida comunicación universal de vectores entre Claude, Qwen y ECHO. [Coconut](https://arxiv.org/abs/2412.06769). COMMS-LATENT-1 sería una intervención experimental posterior: comparar mensajes tipados con un canal latente local, sumando entrenamiento y codificación al coste. Su prioridad queda por debajo de transferencia y mejora del investigador.

**La evolución de pesos comienza con datos y un adaptador.** Cada ejemplo registra entrada permitida, propuesta, feedback comprobado, versión y procedencia. Los datos de entrenamiento incluyen resultados propios de desarrollo; las reservas permanecen fuera. Un ejemplo puede contener una justificación breve explícita, sin exigir razonamiento privado de terceros. Los datos de un profesor externo se identifican por separado y se comprueban sus términos de uso antes de incorporarlos.

El primer método sería SFT con QLoRA de una base abierta congelada. Una vez existan preferencias comparables para el mismo problema se estudiaría DPO. GRPO exige muestreo de grupos, recompensas y actualizaciones de política; un torneo de propuestas no lo implementa por sí solo. Su coste incluye generación, simulación y entrenamiento. [QLoRA](https://arxiv.org/abs/2305.14314), [DPO](https://arxiv.org/abs/2305.18290), [GRPO en DeepSeekMath](https://arxiv.org/abs/2402.03300).

La publicación de QLoRA muestra una configuración de 65B en 48 GB; no garantiza cualquier contexto, arquitectura o ajuste por refuerzo en esa memoria. Los adaptadores ocupan memoria y son específicos de bases compatibles. vLLM admite seleccionar y cargar LoRA por solicitud, con configuración y límites; hay coste de carga y de memoria. El piloto puede alternar entrenamiento e inferencia en una única GPU, manteniendo cada trabajo fijado a una versión. [vLLM](https://docs.vllm.ai/en/latest/features/lora/).

La comparación de pesos reutiliza el factorial del plan RSI-2: biblioteca inicial/evolucionada × modelo base/ajustado. Añadiría LLM sin núcleo, pesos sin acumulación y una condición con igual presupuesto adicional gastado en muestreo en vez de entrenamiento. Su coste de entrenamiento se amortiza a un número de usos declarado; un modelo ajustado que ahorra tokens solo después de muchos usos debe mostrar ese punto de equilibrio. La segunda generación debe demostrar utilidad del estado retenido respecto a reiniciar, manteniendo controles equivalentes.

| Escala propuesta | Peso ideal a 4 bits, sin sobrecostes | Primer objetivo de entrenamiento |
|---|---:|---|
| 7B | 3,5 GB | Adaptador piloto, contexto y lote acotados; perfilar en una T4 o L4 |
| 14B | 7 GB | Adaptador sobre L4 si el perfil cabe; A100 como alternativa |
| 32B | 16 GB | Perfilar en A100 de 40/80 GB; ajustar contexto, rango y lote antes de comprometer una corrida |

Estas cifras son un cálculo mínimo `parámetros × 4/8` en GB decimales. Se añaden metadatos de cuantización, adaptadores, activaciones, buffers y, para inferencia, KV cache. Caber los pesos no demuestra que quepa el entrenamiento ni determina tokens por segundo. No se ha perfilado todavía esta propuesta en la cuenta Colab del propietario.

Para un ajuste completo convencional con pesos de 2 bytes, copia maestra de 4, dos momentos Adam de 4 cada uno y gradientes de 2–4, los estados suman aproximadamente 16–18 bytes por parámetro antes de activaciones: 112–126 GB para 7B, 224–252 GB para 14B y 512–576 GB para 32B. Son supuestos de un optimizador concreto; offload, particionado o estados cuantizados cambian esa necesidad y añaden otros costes. Transformers documenta 18 bytes con gradientes FP32. El objetivo de ajuste completo exige un perfil distinto al primer piloto con adaptador. [Memoria de entrenamiento](https://huggingface.co/docs/transformers/main/en/model_memory_anatomy).

Kaggle documenta la opción T4 ×2. Cada T4 tiene 16 GB nominales; los dos dispositivos mantienen memoria separada. Se puede servir un 7B cuantizado en cada uno, o distribuir un modelo con un motor que lo soporte, pero dos tarjetas no se convierten automáticamente en una GPU de 32 GB. Replicar el modelo para data parallel también replica sus estados. Para el piloto priorizaría trabajos independientes con base compartida por versiones, mientras un 32B se perfila en una GPU de mayor memoria. [Kaggle Notebooks](https://www.kaggle.com/docs/notebooks), [NVIDIA T4](https://www.nvidia.com/en-us/data-center/tesla-t4/).

Colab aporta las 200 unidades mensuales declaradas para el plan AI Pro elegible. La oferta de GPU y los límites varían: este plan no presupone acceso continuo a H100/A100 de 80 GB. Se registrarán acelerador real, VRAM utilizable y tasa de consumo de unidades. Los beneficios del código de regalo deben verse en la misma cuenta de Colab; no se ha accedido a ella en esta investigación. [Google AI Pro](https://support.google.com/googleone/answer/14534406?hl=en), [Colab](https://research.google.com/colaboratory/intl/es/faq.html).

Con las equivalencias proporcionadas por el propietario —200 unidades ≈26 h de A100 o ≈100 h de L4—, una asignación mensual orientativa sería:

| Uso | Unidades | Equivalente A100 | Equivalente L4 |
|---|---:|---:|---:|
| Perfilado y puesta a punto | 20 | 2,6 h | 10 h |
| Inferencia y comparación de modelos | 60 | 7,8 h | 30 h |
| Ajuste de adaptadores | 80 | 10,4 h | 40 h |
| Evaluación y reproducción | 40 | 5,2 h | 20 h |
| Total | 200 | 26 h | 100 h |

Las dos columnas son alternativas bajo las tasas supuestas, no recursos simultáneos. Seis asignaciones mensuales serían 1.200 unidades y doce serían 2.400: aproximadamente 156/312 h A100 o 600/1.200 h L4 a esas tasas. Son sumas de asignaciones, no una garantía de acumulación de créditos o disponibilidad. Cargar, preparar datos y esperar con la GPU asignada también puede consumir saldo. Los bancos CPU y el parser deben prepararse antes de pedir acelerador.

Kaggle añade recursos sujetos al saldo y la disponibilidad de su cuenta. Su documentación describe sesiones acotadas y una promoción experimental de horas adicionales para Colab Pro/Pro+; no se asume que AI Pro reciba automáticamente esa promoción. Los resultados y checkpoints deben guardarse en almacenamiento persistente privado. Kaggle y Colab son ejecutores de trabajos reanudables; la cola, el registro y la custodia del evaluador pueden permanecer locales o en un VPS pequeño.

La infraestructura inicial necesita control CPU, ejecutor GPU por horas y un registro privado de datos/modelos, que pueden funcionar por turnos. Un clúster NVLink/InfiniBand solo se justifica si el método y la escala finalmente exigen varias GPU estrechamente acopladas. No se requieren servidores en distintos países para ajustar un adaptador o cambiar de neocórtex. El respaldo conserva integridad y continuidad tras fallos; una parada deliberada revoca el reinicio en la cola y todas sus réplicas.

Actualización del propietario del 7 de octubre: el techo previsto de cómputo e infraestructura es **1.300 €**, conservando al menos 700 € de una beca de 2.000 €. La beca futura es una expectativa, no saldo disponible ni autorización de contratación. Este reparto sustituye la asignación exploratoria anterior y se desarrolla en el [plan de familia y SaaS](ECHO-PRODUCT-FAMILY-AND-SAAS-PLAN-20261007.md):

| Hito de gasto propuesto | Techo orientativo |
|---|---:|
| Alpha/Gamma: perfiles, ajuste y pilotos | 200 € |
| Beta: perfil y ajuste viable | 250 € |
| Theta: perfil y entrenamiento viable | 350 € |
| Confirmación independiente y reproducción | 200 € |
| VPS y almacenamiento | 150 € |
| Reserva para incidencias y divisa | 150 € |
| Total máximo | 1.300 € |

Se liberarían etapas según evidencia, usando antes los recursos incluidos en las suscripciones. El [plan de familia y SaaS](ECHO-PRODUCT-FAMILY-AND-SAAS-PLAN-20261007.md) reúne las tarifas consultadas, los escenarios de GPU por demanda y la diferencia entre entrenamiento y alojamiento continuo. La elección exige medir coste por solución o por actualización, además del precio por hora; los techos incluyen servicios adicionales, impuestos y divisa.

**El primer movimiento científico sigue siendo una comparación pequeña del neocórtex.** B23 podría cruzar 7B/14B con feedback ausente/presente y añadir un generador sin LLM. Un piloto orientativo de tres semillas y doce oportunidades por condición daría hasta 180 propuestas entre las cinco condiciones. El formato, lenguaje de cambios, ejemplos, contexto y techo de generación serían iguales cuando corresponda; se medirían también GPU-segundos y coste real, porque iguales tokens no implican igual cómputo. Esta cifra es propuesta para calibrar viabilidad, no el contrato definitivo ni una confirmación con potencia suficiente.

Cada retry, reparación, crítica y evaluación consume presupuesto. Se registran propuestas válidas, AST distintos, intervenciones efectivas, mejoras aceptadas, pérdidas, éxito en casos nuevos y coste. El piloto decide qué condición merece confirmación, no cambia retrospectivamente el umbral ni el conjunto reservado. Las condiciones empiezan desde el estado previsto en su contrato; preinstalar el ganador humano o de PROBE2 no acredita descubrimiento desde SEMILLA.

Después vendrían los siguientes contrastes, reutilizando módulos del plan vigente:

| Orden | Experimento | Evidencia necesaria para avanzar |
|---|---|---|
| 1 | **PROPOSE-2 / B23** | Mejores propuestas útiles por presupuesto; separar tamaño del modelo, feedback y errores del controlador |
| 2 | **DREAM-STORE-1 / DREAM-EXEC-1** | Reconstrucción con procedencia y equivalencia de ejecuciones restauradas; ahorro efectivo medido |
| 3 | **RSI-1 del investigador** | El investigador cambiado encuentra mejoras nuevas más eficientemente que el inicial con el mismo modelo |
| 4 | **ARENA-1 / ROLE-POLICY-1** | Especialización supera controles de muestreo y reparto fijo en una cohorte nueva |
| 5 | **WEIGHTS-1** | Adaptador supera su propia base y conserva capacidades bajo evaluación independiente |
| 6 | **CORTEX-MUX-1** | Router mejora coste/calidad frente a ruta fija; cada trabajo tiene modelo/versionado reproducibles |
| 7 | **RSI2-CYCLE-1** | Al menos dos ciclos completos con controles de acumulación y productividad del siguiente investigador |
| 8 | COMMS-LATENT-1 opcional | Ventaja adicional del canal latente contando adaptación, interfaces y memoria |

La unidad estadística de autonomía es el recorrido independiente del investigador; propuestas, partidas y replays del mismo recorrido no son réplicas independientes. El contrato debe fijar margen relevante, número de réplicas, intervalo, regresiones permitidas y corrección por múltiples contrastes. Familias y repositorios no vistos ofrecen una prueba más fuerte que cambiar solamente semillas de la misma receta. Los datos usados para reparar dejan de ser una reserva nueva; la confirmación se custodia separadamente.

RSI-2 compararía biblioteca y pesos por separado y mediría si la segunda generación produce mejores mejoras con un presupuesto comparable al de un sistema reiniciado. El modelo base, entrenamiento y evaluación conservarían manifiestos; los trabajos en curso se fijarían a una versión y la promoción solo afectaría trabajos nuevos. El evaluador determinista puede tener errores y certifica su banco definido, no corrección universal. GPU y muestreo pueden introducir variación; se conservarían semillas, checkpoints y réplicas en lugar de exigir que dos modelos diferentes produzcan idénticas acciones.

Octubre–diciembre de 2026 puede usarse para resolver los bloqueos actuales y preparar datos, perfiles e integración. Q1 de 2027 es una ventana de investigación propuesta para los primeros ciclos RSI-2 si las dependencias están validadas. La fecha no sustituye sus pruebas. El resultado defendible con este presupuesto sería una adaptación especializada y un bucle de investigación reproducible con transferencia medida; equivalencia frontier, vida subjetiva y automejora indefinida seguirían siendo preguntas abiertas.
