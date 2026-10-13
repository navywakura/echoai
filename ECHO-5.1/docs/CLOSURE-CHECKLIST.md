# ECHO-5.1 · checklist de desarrollo

Actualización: 13 de octubre de 2026. El verde se aplica al alcance comprobado
de cada fila; no equivale a una ventaja científica ni al cierre de ECHO-5.1.

| Estado | Entrega | Evidencia y límite |
|---|---|---|
| Verde | Frontera de ejecución Linux compartida | Bubblewrap/cgroup v2; sin fallback. NEXUS-0 y sus invariantes conservados. |
| Verde acotado | T08: entorno del piloto independiente | Rootfs Python íntegro y exportable; sin montar `/usr` host. No empaqueta kernel ni hardware. Las rutas legacy conservan su etiqueta no hermética. |
| Verde acotado | T10: caché persistente de propiedades puras | Identidad de candidato, resultado, dominio, política, runtime y checker; reinicio, invalidación y testigos comprobados. Todo código candidato vuelve a ejecutarse. |
| Verde | Proveedor local real | Qwen2.5-Coder-7B-Instruct Q4_K_M, revisión/hash fijados, llama.cpp CPU. Preflight exacto y esquemas públicos. El 4B no interviene. |
| Verde | Contabilidad | 25k tokens por tarea/brazo; reservas antes de llamadas; errores e inconsistencias no son gratis. CPU del LLM separada de la del candidato. |
| Verde acotado | Crítico → contraejemplo → memoria → reparación → verificación | Un diagnóstico real sobre `sum_positive`: 1/1, 1.704 tokens, 51 recibos auditados. El defecto inicial es sembrado. |
| Verde | Corpus nuevo de reparación | Seis familias distintas de las cuatro fixtures: intervalos, registros, rutas, CSV, paginación y dependencias. Bugs inducidos comprobados; no benchmark externo. |
| Verde de ejecución; ventaja no demostrada | Comparación S/I2/F/E `repair-v2` | 48/48 episodios, auditoría válida de 2.049 recibos. S=4/12, I2=4/12, F=2/12, E=2/12. E no supera a F (10 empates, 2 pérdidas frente a S); produjo más contraejemplos que F, pero no más reparaciones aceptadas. 250.444 tokens totales. |
| Verde | Software y revisión | 255 tests PCWorld tras memoria persistente, transferencia A→B y orquestación del ensayo 32B con comprobación de identidad/carga; 59 regresiones seleccionadas en una tanda anterior. Revisión completada antes de lanzar. |
| Verde de ejecución; empate | Piloto 14B con dos puertas | 12/12 episodios y 580 recibos auditados. Todos 2/3. E=20.372 tokens; F=22.378; S=5.212; I2=2.352. Cuota de críticas agotada en Registros E/F; evaluación final no ejecutada allí. |
| Verde de ejecución; ventaja limitada al piloto | Piloto 14B con evaluación común | 12/12 episodios, 619 recibos auditados y auditoría repetida válida. E=F=3/3 frente a S=I2=2/3. Registros pasa tras crítica y reparación en E/F; ambos completan dos categorías. E=16.174 tokens, F=16.049; no hay ventaja de E frente a F. Tres tareas conocidas, no confirmación independiente. |
| Verde de implementación | Cobertura informativa y graduación del candidato | Criterio final común a los cuatro brazos, sin cambiar oráculos; agotamiento de críticas no implica corrección. Pruebas positivas y negativas del candidato graduado; no se reserva una séptima crítica. En 0.6 no se necesitó; en 0.7 F Rutas01 se graduó con una categoría y pasó 4/4. F CSV01 se graduó pero fue rechazado. |
| Verde de ejecución; resultado parcial | Cinco categorías y seis familias, protocolo 0.7 | 48/48 episodios, 2.362 recibos auditados. E=F=8/12 frente a S=I2=6/12. Ambos ganan en Registros; CSV y Dependencias siguen fallando. E gasta 54.310 tokens frente a 66.993 de F; un error de presupuesto de herramientas en CSV01 F. Sin timeouts. |
| Verde de implementación | Memoria de críticas rechazadas y auditoría del catálogo | E recupera observaciones y fallos en una sola consulta cobrada; avanza de categoría tras tres rechazos. La auditoría comprueba orden, reintentos, etiquetas, novedad y vínculo con propuesta o replay. El orden F se fija por semilla, sin colocarlo deliberadamente en desventaja. |
| Pendiente | Superioridad o ahorro atribuibles a ECHO | En 0.10 con 32B, S=F=E=E_shared=12/12 e I2=10/12. E usa 4,09% menos tokens que F, pero 6,74% más herramientas; S resuelve lo mismo con 53,09% menos tokens que E. La memoria ahorra 5,94% en receptores, pero cuesta 46,22% más incluyendo adquisición. No se cierran H1/H2/H4 generales. |
| Verde de implementación | Reparación con testigos y rechazo de regresiones | Feedback explícito con esquema de I/O y stderr observado, dos intentos, restauración transaccional del candidato retenido; E congela el crítico durante la reparación y lo reabre tras un parche comprobado para completar dos categorías. Pruebas de software; no implica ventaja del modelo. |
| Negativo en desarrollo | Microensayo local de reparación r1 | Registros y Rutas: 0/2 reparaciones, 0/2 pases finales, sin timeout; 140 recibos auditados. r2 también 0/2, con 154 recibos válidos. |
| Parcial; cerrado el diagnóstico | Microensayo 14B en Kaggle | GPU 49/49 capas, 1/2 tareas completas. Registros 5/5 a la primera; Rutas 4/5 tras el segundo intento, rechazada por un caso final. Auditorías locales válidas. No demuestra ventaja S/I2/F/E. |
| Verde acotado | Reparación desde contrato y error observado | Registros pasa tras dos propuestas del 7B; Rutas falla. 1/2, 108 recibos auditados. Testigos suministrados, sin mérito de descubrimiento del crítico. |
| Parcial | Crítica adversarial y reparación | E retuvo 6 contraejemplos válidos frente a 2 de F, pero la aceptación fue 2/12 para ambos; siete episodios agotaron el plazo del proveedor (F=5, E=2). Hubo respuestas de categoría incorrecta y duplicados (F=11/6; E=1/3), sin entradas fuera de dominio. Hace falta mejorar la conversión de refutaciones en reparación y repetir en una muestra nueva. |
| Verde acotado con 32B | Sondeos y resolución de CSV | En 0.10, 2/2 en los cinco brazos. El candidato E de CSV00 usa csv.reader. El fracaso 0.8 con 14B se conserva: E/F/S 0/2 pese a sondeos refutatorios. No se demuestra ventaja específica de E. |
| Verde acotado con 32B | Sondeos y resolución de grafos | En 0.10, 2/2 en los cinco brazos. E/F/S reparan; los dos receptores con receta pasan sin reparar. El resultado 0.8 E=F=0/2 con 14B sigue siendo histórico; no se modificaron los oráculos. |
| Pendiente | Semántica de categoría heredada | `disconnected-lex-order` exige un nodo aislado en su detector, pero la guía no lo explicita. Alinear definición y guía antes de atribuir ahorro al router; sin recalificar episodios ya congelados. |
| Pendiente | Ablaciones de memoria, crítico y control basal | Mismo modelo, herramientas y presupuesto; aislar qué mecanismo aporta una mejora. |
| Pendiente | Ampliación y confirmación independiente | Más tareas/familias y repeticiones, dimensionar muestra, fijar contrato y reservar casos nuevos. No reciclar este desarrollo como examen ciego. |
| Parcial; recetas transferidas | T20: conceptos reutilizables | En 0.10 se publican dos recetas con AST/procedencia y cuatro receptores compatibles pasan sin reparar. Código idéntico en Registros y mismo AST en Dependencias, dentro del mismo contrato. Faltan abstracción, adaptación, promoción/cuarentena integrada y transferencia a familias nuevas. |
| Parcial; ahorro marginal | H2: memoria compartida | 0.10: E_shared=E=12/12, reparaciones 0 frente a 4; 40.254 frente a 42.795 tokens. Incluyendo los seis donantes, 62.573 tokens y coste mayor. No hay ventaja de acierto ni amortización demostrada; faltan controles fuertes y confirmación independiente. |
| Verde de ejecución; empate con control único | Escalado 32B y memoria, protocolo 0.10 | 255 tests, 66 episodios, dos auditorías válidas y 32 fuentes intactas. 65/65 capas en ambas T4; S=F=E=E_shared=12/12, I2=10/12. Kaggle COMPLETE y servicios de cómputo apagados; 22,94 h GPU restantes. [Resultados y checklist](SCALING32-RESULTS-20261013.md). No cierra ECHO-5.1. |
| Pendiente | Release experimental reproducible en otra máquina | Probar instalación y restauración fuera de este host, publicar artefactos sin claves privadas y definir alcance de release. |
| Aplazado | S6 | No se reabre; queda para después de ECHO-5.5. |

Detalles: [piloto local](LOCAL-PILOT-20261013.md),
[T01–T20](ACCEPTANCE.md), [verificación](PHASE2-VERIFICATION.json) y
[ejecución reproducible](RUNBOOK.md), [protocolo adversarial](ADVERSARIAL-ROUTING-20261013.md)
y [resultados adversariales](ADVERSARIAL-ROUTING-RESULTS-20261013.md).

El estimador `--dry-run` ya cuenta los brazos y familias seleccionados y el
plazo explícito de episodio. Detalle de la remediación: [brecha de reparación](REPAIR-GAP-20261013.md).

Resultados de remediación: [informe de reparación](REPAIR-GAP-RESULTS-20261013.md).

La reparación funciona en los casos de desarrollo descritos; su transferencia y ventaja específica siguen abiertas. Los diagnósticos locales y Kaggle terminaron; no se publicó ni se hizo push a GitHub.

Piloto anterior, protocolo 0.5: [dos puertas](TWO-GATE-RESULTS-20261013.md).
S=I2=F=E=2/3 y 580 recibos válidos. Se conserva esa puntuación histórica.

Piloto anterior, protocolo 0.6: [evaluación común](GRADUATION-RESULTS-20261013.md).
E=F=3/3, S=I2=2/3; 619 recibos válidos. Registros reparado y evaluado;
sin errores de episodio ni timeouts. 202 tests pasan. ECHO-5.1 sigue abierto
para confirmación independiente. Quedaron 25,33 h GPU al terminar ese piloto.

Piloto anterior, protocolo 0.7: [discriminación de categorías](CATEGORY-DISCRIMINATION-RESULTS-20261013.md).
E=F=8/12, S=I2=6/12; 214 tests y 2.362 recibos válidos. Duración del worker:
37 min 13 s; consumo de cuota aproximado 0,62 h. GPU, supervisor, broker y
túnel apagados; 24,71 h GPU restantes. ECHO-5.1 continúa abierto para las
hipótesis científicas. No se relanzó, publicó ni hizo push.

Piloto anterior, protocolo 0.8: [sondeos CSV/grafos y checklist completo](PROBE-CONTENT-RESULTS-20261013.md).
E=F=8/12, S=I2=6/12. 219 tests, 48 episodios y 2.445 recibos válidos; auditoría
repetida y 27 hashes conservados. 132.287 tokens; ningún error de episodio ni
timeout. Worker 33 min 09 s; cuota total aproximada 0,59 h incluyendo corrección
del empaquetado inicial. Kaggle COMPLETE, supervisor/broker/túnel apagados;
24,12 h GPU restantes. Sin push ni publicación. H1/H4 y T20 siguen abiertos.
El informe enlazado reúne qué está comprobado y cada obligación pendiente.

Piloto anterior, protocolo 0.9: [co-learning A→B y checklist](COLEARNING-RESULTS-20261013.md).
240 tests, siete episodios ejecutados, auditoría repetida válida sobre 347 recibos
de episodios y custodia del estudio/bibliotecas. Treinta fuentes congeladas intactas.
Receptores: compartido 3/3 sin reparación; aislado 1/3 con una reparación.
Dos controles fallan por copiar `format.content`; no se atribuye toda la diferencia
al aprendizaje de duplicados. 21.021 tokens totales y 0,14 h GPU aproximadas.
Kaggle COMPLETE y servicios de cómputo apagados; 23,98 h GPU restantes.
Recuperación persistente implementada, H2/T20 generales todavía parciales. Sin push.

Último piloto, protocolo 0.10: [32B y memoria compartida](SCALING32-RESULTS-20261013.md).
S=F=E=E_shared=12/12, I2=10/12; 66 episodios y 255 tests. Auditoría repetida
válida, 32 fuentes congeladas intactas, 179.731 tokens totales. La memoria evita
cuatro reparaciones y ahorra 5,94% de tokens en receptores; incluyendo adquisición
cuesta 46,22% más que E sin memoria. S alcanza el mismo acierto con menos coste.
Worker 61 min 51 s; consumo aproximado 1,04 h GPU, 22,94 h restantes. Kaggle COMPLETE,
servicios de cómputo apagados; sin push ni publicación. H1–H4 y T20 generales abiertos.
