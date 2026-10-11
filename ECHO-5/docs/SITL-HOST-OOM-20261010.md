# Interrupción externa durante SITL de desarrollo r4

A las 23:33:29 del 10 de octubre, el kernel del equipo registró un OOM global
y terminó `agy`, PID 38912, perteneciente a otra terminal. El registro indica
9.737.016 KiB de memoria anónima residente. No era un proceso del banco ECHO-5.
No se terminó ni modificó ninguna aplicación ajena desde este trabajo.

El primer vuelo r4, `0000-echo32`, perdió el latido de seguridad durante una
pausa de 7,659 segundos entre registros, con el reloj de simulación inmóvil en
33,991 segundos. Terminó con `heartbeat lease expired`, sin aterrizaje ni
desarmado observados. Su recibo sigue siendo inválido. La coincidencia temporal
y el evento del kernel respaldan una interrupción del host; no constituyen una
comparación cognitiva entre brazos ni rehabilitan ese vuelo.

Se registró el plan de interrupción en
`artifacts/host-oom-recovery-20261010-r1/plan.json`. El monitor dejó terminar
el siguiente episodio y detuvo el lanzador en un límite entre episodios, cuando
no tenía procesos hijos. El control `0000-one_step` terminó válidamente,
alcanzó la meta, regresó y se desarmó. Se preservaron los dos episodios y se
construyó un informe parcial explícitamente identificado; su denominador sigue
siendo 18. No se sustituyó la observación fallida por una ejecución posterior.

La auditoría independiente de r4 reprodujo los dos registros y señaló los
16 recibos no ejecutados. `valid:false` y `denominator:false` se mantienen.
El kernel, el script de interrupción, sus identidades y el cierre están en
`artifacts/host-oom-recovery-20261010-r1/`. La campaña r4 no abre confirmación.

El coordinador `artifacts/closure-pipeline-20261010-r3/` registra una repetición
completa en `artifacts/sitl-development-20261010-r5/`. Arrancó a las 23:39,
con 9.951.559.680 bytes disponibles según el kernel. Conserva agentes,
semillas, mundos, límites, criterios y fuentes `d58d620d…`. Se reutilizan
checks r6, navegador r6 y desarrollo CPU r5 tras comprobar su identidad.
Todos los vuelos r5 serán nuevos; ningún resultado parcial r4 los sustituye.

El nuevo coordinador guarda una muestra de recursos del host por segundo.
Un incremento del contador global `oom_kill` detiene las fases posteriores,
conservando los resultados obtenidos. La caducidad del latido, las tolerancias
de vuelo y las puertas científicas no se han relajado. La confirmación sigue
reservada hasta completar y auditar desarrollo.
