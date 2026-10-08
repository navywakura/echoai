# S6-B19 — cierre sin promoción

Comprobado el 5 de octubre de 2026 a las 20:22, hora de Madrid. Kaggle confirma
COMPLETE. La medición terminó a las 15:57 y la auditoría independiente a las
16:59. La descarga y revisión aritmética local terminaron a las 17:01.
El ensayo consumió aproximadamente tres horas desde su envío a las 13:57.

Se evaluaron 36 propuestas, doce por brazo, sobre el cribado dirigido de doce
casos, con 1188 ejecuciones físicas incluyendo replays y auditoría. Hubo una
generación LLM compartida inicialmente por control e híbrido; los refinamientos
los calculó el núcleo. La base del cribado sumaba 52 niveles. Estas cifras
pertenecen al banco procedural S6, no al benchmark ARC oficial.

| Resultado representativo | Niveles | Ganancia | Casos con pérdida de score |
| --- | ---: | ---: | ---: |
| Buscador anterior, propuesta 3 | 60 | +8 | 2 |
| Híbrido nuevo, propuesta 2 | 56 | +4 | 1 |
| Sintetizador sin LLM, propuesta 3 | 53 | +1 | 0 |

El híbrido alcanzó también 60 niveles, pero esas propuestas conservaron al
menos dos pérdidas. Ninguna de sus doce propuestas pasó el criterio completo.
El sintetizador obtuvo varios +1 sin pérdidas, por debajo del mínimo +2.
El criterio exigía simultáneamente mejora suficiente y cero regresiones.

La propuesta híbrida 2 gana en dos casos, pero reduce el score de v3/28027
en 0,2062953541. Sus condiciones son `HOLD=1` cuando `world_events<=8`.
El control anterior recupera la guarda B18 y vuelve a perder score en
v3/28027 y v3/28039. La conservación sigue siendo el bloqueo concreto.
Estos resultados no demuestran que la gramática sea incapaz de resolverlo.

El resultado es científico negativo con instrumento válido: la auditoría
reconstruyó las solicitudes, políticas, trayectorias y veredictos. La revisión
local verificó 1188 registros de caché y 111 archivos de medición. Hubo
reconexiones del monitor de logs; no interrumpieron las partidas ni sus
auditorías y ambos servicios locales terminaron con código cero.

Al no pasar ningún brazo el cribado, no se ejecutaron los 160 casos de
desarrollo ampliado ni los 80 protegidos nuevos. Tampoco arrancaron piloto,
campaña o examen. No queda trabajo B19 corriendo y no hay un tiempo restante
para su cierre. **S6 permanece abierto, sin verde.** Las correcciones están
implementadas y probadas, pero no consiguieron la conservación exigida.

[Cierre](../lab/seed/s6b19-20261005/kaggle-results/closed.json) ·
[Auditoría](../lab/seed/s6b19-20261005/kaggle-results/micro-audit.json) ·
[Revisión aritmética](../lab/kaggle/s6b19-20261005/arithmetic-review.json) ·
[Contrato](ECHO45-S6-B19-DESIGN.md).
