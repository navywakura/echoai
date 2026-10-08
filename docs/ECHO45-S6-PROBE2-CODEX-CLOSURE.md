# PROBE2: revisión del cierre y siguiente condición S6

2 de octubre de 2026. PROBE2 terminó a las 04:16:25 Madrid. He reconstruido
los veredictos desde las mediciones guardadas, sin ejecutar partidas nuevas.
El [recibo de revisión](../lab/seed/s6probe2-20261001-codex-review/receipt.json)
es válido. La revisión de archivos no sustituye una auditoría independiente
por reejecución con caché separada.

Se comprobaron las 147 fuentes congeladas, el hash del plan, las 874 mediciones
de cribado y sus decisiones, los 88 replays, las cinco muestras de solidez,
la base y su replay, las dos verificaciones completas y sus replays, y los
digests y origen DEVELOPMENT_A de los 10.048 registros de caché. El presupuesto
coincide con esos registros y no supera el tope de 14.544. B y el examen
siguen sin abrir; hubo cero llamadas al modelo.

Los candidatos 28 y 33 llegan a **383 niveles frente a 378**, +5 (+1,32 %),
sin pérdida de nivel o score en ninguna de las ochenta partidas. Ambos pasan
V3 y reproducen su propio digest completo. El score total pasa de
4125,4035986891895 a 4166,086749105974 (+0,99 %). Son dos variantes legales
con las mismas ganancias de nivel: +1 en A18 y +4 en A53. No se suman entre
sí ni constituyen dos descubrimientos independientes del agente.

La interpretación cambia respecto al sondeo anterior: el lenguaje vigente
sí contiene una mejora individual que supera el umbral +2 sin regresiones
en A. No hace falta bajar V3 ni permitir dos parches para demostrar esa
capacidad. PROBE1 había muestreado otras guardas; su resultado negativo
continúa siendo válido para su muestra. PROBE2 es una búsqueda dirigida
después de ver PROBE1 y se informa con esa selección.

El siguiente trabajo S6 es auditar por reejecución y prerregistrar un piloto
autónomo que conserve el objetivo de refinamiento entre llamadas, muestre
evidencia pertinente de desarrollo, descarte propuestas inertes o repetidas
y use un control de muestreo de la misma gramática con presupuesto equivalente.
El modelo no recibe las reglas halladas por PROBE2, índices de partidas,
semillas, estados privados ni respuestas del examen. El piloto debe demostrar
que ECHO propone una mejora y que el verificador la acepta bajo V1–V4.
Después hacen falta campaña elegible y examen reservado nuevo de cuatro
brazos con B1–B5 y auditoría. **S6 sigue abierto.**

El experimento privado RSI1-R1 está ejecutándose por separado desde las
04:35:47. La [adenda CPU](ECHO-RSI1-RECOVERY1.md) conserva el bloqueo original
por ROCm, cuenta la llamada fallida y la calibración, y mantiene modelo,
datos y criterios. Su primer resultado real fue una propuesta con formato
inválido, rechazada sin promoción; el transporte terminó correctamente.
El banco continúa. Ningún resultado de RSI1 sustituye las puertas S6.

[Resultados completos](ECHO45-S6-PROBE2-RESULTS.md) ·
[Contrato PROBE2](ECHO45-S6-PROBE2-DESIGN.md) ·
[Revisor de recibos](../lab/tools/s6probe2-result-review.py).
