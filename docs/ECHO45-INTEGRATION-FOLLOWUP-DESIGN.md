# Seguimiento de V2 sin nuevos ajustes

La revisión de desarrollo pasó de 2/64 a 4/64 en ARC-1, sin pérdidas respecto a
V1 sin vistas; todos los brazos de ARC-2 quedaron en 0/64. El refinamiento
explica la ganancia observada. Memoria, tamaño de guía, vistas y consistencia
no aportaron nuevos aciertos. La comparación anterior suma 128 ocurrencias,
124 IDs distintos por cuatro coincidencias entre los dos pools.

Antes de seleccionar este seguimiento se fijan las fuentes V2 existentes,
sus nueve brazos, el techo de 2.000 programas y los otros límites. No habrá
otra modificación orientada por los resultados del seguimiento en esta serie.

Se seleccionan por hash 64 tareas de ARC-1 training y 64 de ARC-2 training,
sin duplicados entre pools, con semilla
`echo45-integration-confirmation-20261002-v1`. Se excluyen las 84 tareas de
adquisición, los 124 IDs de desarrollo y toda la reserva del gimnasio. Las
tareas se seleccionan entre los IDs de entrenamiento autorizados.

Este seguimiento es independiente de los ajustes de esta revisión. Usa datos
públicos que pudieron aparecer en investigaciones anteriores del laboratorio:
no constituye una reserva secreta nueva ni una puntuación ARC oficial.

Para respaldar la promoción de desarrollo, V2 debe mantener todos los aciertos
de V1 sin vistas y añadir al menos uno. El criterio es por tarea, no solo por
suma. El refinamiento, memoria, vistas, consistencia y guías se contrastan por
sus ablaciones; un empate no acredita aportación. Se conservan coste y CPU.
Cada ejecución tiene replay en otro proceso y paridad con un V1 ejecutado por
separado. Si falla, se documenta la hipótesis y no se marca verde el candidato.
