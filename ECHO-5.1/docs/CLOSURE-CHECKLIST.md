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
| Verde de ejecución; resultado nulo | Comparación S/I2/F/E | 24/24 episodios, auditoría válida de 860 recibos. Cada brazo pasa 2/6: intervalos y paginación. 22.412 tokens; cero ventaja de acierto observada. |
| Verde | Software y revisión | 162 tests PCWorld y 59 regresiones seleccionadas; cinco hallazgos importantes reproducidos y corregidos. |
| Pendiente | Superioridad o ahorro atribuibles a ECHO | No basta ejecutar más agentes ni pasar tests de infraestructura. Requiere contraste y suficiente incertidumbre medida. |
| Pendiente | Crítica y reparación en tareas independientes | Cero contraejemplos retenidos en el piloto: 15 entradas elegibles no refutaron y tres quedaron fuera del dominio. Investigar prompt, selección de casos y continuación sin modificar este resultado congelado. |
| Pendiente | Ablaciones de memoria, crítico y control basal | Mismo modelo, herramientas y presupuesto; aislar qué mecanismo aporta una mejora. |
| Pendiente | Ampliación y confirmación independiente | Más tareas/familias y repeticiones, dimensionar muestra, fijar contrato y reservar casos nuevos. No reciclar este desarrollo como examen ciego. |
| Parcial | T20: conceptos reutilizables | Registro y cuarentena unitarios; extracción, transferencia y promoción todavía sin demostración. Biblioteca del piloto vacía. |
| Pendiente | Release experimental reproducible en otra máquina | Probar instalación y restauración fuera de este host, publicar artefactos sin claves privadas y definir alcance de release. |
| Aplazado | S6 | No se reabre; queda para después de ECHO-5.5. |

Detalles: [piloto local](LOCAL-PILOT-20261013.md),
[T01–T20](ACCEPTANCE.md), [verificación](PHASE2-VERIFICATION.json) y
[ejecución reproducible](RUNBOOK.md).

Menor conocido: el estimador `--dry-run` supone cuatro brazos incluso si se
seleccionan menos; sobrestima esos diagnósticos. La estimación del piloto principal
de cuatro brazos es correcta.
