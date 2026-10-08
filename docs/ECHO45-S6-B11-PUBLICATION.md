# S6-B11 · publicación del cierre

El coordinador original sigue piloto → auditoría → campaña → auditoría →
examen de cuatro brazos. Sólo continúa cada promoción si cumple el contrato.
No se cambian sus fuentes, modelo, muestras, filtros ni criterios.

Un supervisor separado espera **el recibo terminal y estado CLOSED**, leyendo
sólo estado y resultados ya terminados. No observa ni instrumenta partidas.
Al cerrar valida hashes de fuentes, estrategias y auditorías; publica sólo
métricas agregadas y el informe. Nunca exporta programas, trayectorias
protegidas, peticiones, respuestas reservadas ni código ECHO.

Para publicar verde exige simultáneamente: promoción de piloto y campaña,
auditorías independientes válidas, reserva abierta según contrato y B1–B5
verdaderos en el examen final. Un recibo contradictorio se rechaza. Un cierre
negativo conserva el rojo y la investigación pendiente. Dos pruebas stdlib
comprueban esas dos rutas y el rechazo de criterios incompletos.

La publicación usa un checkout aislado del repositorio web y una lista de
cuatro archivos permitidos. Rechaza un checkout sucio o un remoto distinto.
Guarda el commit antes de push; si la red hace el envío incierto, se conserva
el recibo para inspeccionarlo antes de repetir. No crea commits duplicados.

El explorador y resumen de la web derivan el color de ese resultado. Un cierre
S6 verde **no modifica las puntuaciones ARC oficiales ni convierte todos los
módulos de ECHO-4.5 en verdes**. ARC-2, ARC-3 y transferencia de memoria tienen
criterios independientes.

Implementación privada: `harness/s6_publication.py`. Estado/logs:
`lab/echo-nexus/s6-publication/`. Repositorio público: sólo la web y el arnés.
