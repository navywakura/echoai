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
| Verde | Software y revisión | 202 tests PCWorld tras aceptación común, graduación informativa y parada del crítico por cuota; 59 regresiones seleccionadas en una tanda anterior; cinco hallazgos importantes reproducidos y corregidos. |
| Verde de ejecución; empate | Piloto 14B con dos puertas | 12/12 episodios y 580 recibos auditados. Todos 2/3. E=20.372 tokens; F=22.378; S=5.212; I2=2.352. Cuota de críticas agotada en Registros E/F; evaluación final no ejecutada allí. |
| Verde de ejecución; ventaja limitada al piloto | Piloto 14B con evaluación común | 12/12 episodios, 619 recibos auditados y auditoría repetida válida. E=F=3/3 frente a S=I2=2/3. Registros pasa tras crítica y reparación en E/F; ambos completan dos categorías. E=16.174 tokens, F=16.049; no hay ventaja de E frente a F. Tres tareas conocidas, no confirmación independiente. |
| Verde de implementación | Cobertura informativa y graduación del candidato | Criterio final común a los cuatro brazos, sin cambiar oráculos; agotamiento de críticas no implica corrección. Pruebas positivas y negativas del candidato graduado; no se reserva una séptima crítica. Ningún episodio del nuevo piloto necesitó graduar por cobertura incompleta. |
| Pendiente | Superioridad o ahorro atribuibles a ECHO | El piloto 14B más reciente mejora sobre S/I2 en una de tres tareas conocidas, pero E empata con F y gasta ligeramente más tokens. Faltan independencia, repeticiones y ablaciones; se conservan los resultados negativos de los pilotos anteriores. |
| Verde de implementación | Reparación con testigos y rechazo de regresiones | Feedback explícito con esquema de I/O y stderr observado, dos intentos, restauración transaccional del candidato retenido; E congela el crítico durante la reparación y lo reabre tras un parche comprobado para completar dos categorías. Pruebas de software; no implica ventaja del modelo. |
| Negativo en desarrollo | Microensayo local de reparación r1 | Registros y Rutas: 0/2 reparaciones, 0/2 pases finales, sin timeout; 140 recibos auditados. r2 también 0/2, con 154 recibos válidos. |
| Parcial; cerrado el diagnóstico | Microensayo 14B en Kaggle | GPU 49/49 capas, 1/2 tareas completas. Registros 5/5 a la primera; Rutas 4/5 tras el segundo intento, rechazada por un caso final. Auditorías locales válidas. No demuestra ventaja S/I2/F/E. |
| Verde acotado | Reparación desde contrato y error observado | Registros pasa tras dos propuestas del 7B; Rutas falla. 1/2, 108 recibos auditados. Testigos suministrados, sin mérito de descubrimiento del crítico. |
| Parcial | Crítica adversarial y reparación | E retuvo 6 contraejemplos válidos frente a 2 de F, pero la aceptación fue 2/12 para ambos; siete episodios agotaron el plazo del proveedor (F=5, E=2). Hubo respuestas de categoría incorrecta y duplicados (F=11/6; E=1/3), sin entradas fuera de dominio. Hace falta mejorar la conversión de refutaciones en reparación y repetir en una muestra nueva. |
| Pendiente | Ablaciones de memoria, crítico y control basal | Mismo modelo, herramientas y presupuesto; aislar qué mecanismo aporta una mejora. |
| Pendiente | Ampliación y confirmación independiente | Más tareas/familias y repeticiones, dimensionar muestra, fijar contrato y reservar casos nuevos. No reciclar este desarrollo como examen ciego. |
| Parcial | T20: conceptos reutilizables | Registro y cuarentena unitarios; extracción, transferencia y promoción todavía sin demostración. Biblioteca del piloto vacía. |
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

Último piloto, protocolo 0.6: [evaluación común](GRADUATION-RESULTS-20261013.md).
E=F=3/3, S=I2=2/3; 619 recibos válidos. Registros reparado y evaluado;
sin errores de episodio ni timeouts. 202 tests pasan. ECHO-5.1 sigue abierto
para confirmación independiente. GPU, supervisor, broker y túnel apagados;
25,33 h GPU restantes al terminar.
