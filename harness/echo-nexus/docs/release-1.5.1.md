# echo-nexus 1.5.1 · meta observada

El informe de ECHO distingue ahora el destino activo de las hipótesis visuales
aprendidas tras una victoria. Una meta alcanzada permanece en el contador de
la sesión aunque la siguiente acción tenga `level_up: false`.

En el mundo de desarrollo, `target: null` indica que no hay un destino activo
para el siguiente plan; no borra el hecho de que ECHO haya alcanzado la meta
ni su hipótesis de color. `/echo`, `/ask`, `/why` y el árbol de telemetría usan
la misma explicación basada en los registros recibidos. Las respuestas del
asesor siguen sin actuar sobre el motor.

Se conserva el mapa y el agente del experimento. Esta versión no atribuye
una mejora de ruta ni un nuevo resultado ARC o S6. Las 25 pruebas del arnés
pasan, incluida la transición victoria → siguiente acción y el reinicio del
contador en una sesión nueva.
