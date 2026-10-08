# S6-B12-R1 · recuperación declarada del límite de ejecución

30 septiembre 2026. Adenda previa a cualquier nueva inferencia. No modifica
el contrato, código ni resultados originales de B12. El resultado que siga
esta adenda se identificará como **B12-R1**, con su coste adicional explícito.

## Evidencia de la interrupción

B12 completó c0 y c1. Ambos brazos aceptaron el mismo cambio: 365 → 378
niveles en las 80 partidas de desarrollo A, sin pérdidas individuales en A
ni en la validación protegida. Diez propuestas evaluadas por brazo, una
aceptada por brazo. El empate no satisface la promoción ECHO > FIJO.

c2 se envió a las 06:27:47 UTC y se observó CANCEL_ACKNOWLEDGED a las
07:28:35 UTC. Tenía un límite de ejecución configurado de 3600 segundos.
La última respuesta guardada aparece en el segundo 3276 del registro. Hay
cinco respuestas FIJO y dos ECHO; faltan tres ECHO. Los diez contextos
pasaron el control remoto; máximos FIJO 4646 y ECHO 3105, ambos bajo 6000.
La API no proporciona un motivo de cancelación más detallado. Los tiempos
son compatibles con agotar el límite, no prueban una excepción del modelo.

## Condición adicional de recursos

Se permiten cuatro trabajos privados CPU, c2–c5, de hasta **7200 segundos**
cada uno, con referencias nuevas y un único envío por referencia. El máximo
acumulado programado es 3 × 3600 + 4 × 7200 = **39600 segundos de ejecución
remota**, contando los tres trabajos originales. Esto sustituye para R1 el
presupuesto temporal original; no se presenta como una campaña terminada
dentro de seis horas. Continúan prohibidos GPU y gasto de API.

c2 ejecuta exactamente los bytes del programa original, con los mismos
pesos, tokenizer, prompts, gramática, lotes de dos, semillas y sampling.
Se vuelve a calcular el trabajo completo porque no se conservó un checkpoint
del generador aleatorio. Antes de incorporar cualquier resultado se exige
igualdad exacta de las siete respuestas ya guardadas, su uso de tokens y el
perfil de ejecución. Una discrepancia detiene la continuación: no se elige
la respuesta que puntúe mejor. Se preservan los siete originales y la
cancelación. Son siete respuestas repetidas adicionales como mínimo, más
el cómputo interrumpido no completado; no se declaran como coste cero.

Los otros tres trabajos conservan el generador B12 íntegro. El número de
propuestas lógicas de la campaña sigue siendo 60, más dos calibraciones;
no se añaden propuestas ni se seleccionan semillas nuevas. Se conservan
los límites 6000/900 tokens, cuatro hilos, backend Q8, datos A/B, verificador,
presupuesto local de 64000 partidas y todos los criterios B1–B5.

## Procedencia y auditoría

La adenda, el ejecutor, el transporte y sus pruebas se congelan en un perfil
separado antes del primer envío. También se fijan los hashes de las dos
rondas terminadas y de los artefactos originales c2. Cada trabajo conserva
fuente original, transporte LZMA, recibo de envío, recibos remotos, prompts,
tokens y respuestas. La auditoría independiente reconstruye los veredictos
y valida esta cadena, incluida la reproducción exacta de c2.

El examen permanece sin abrir hasta una campaña con promoción y auditoría
válida, incluida la adenda. No cambia la reserva ni se mira para elegir
políticas. Un empate o una derrota no se convierte en verde. Un nuevo fallo
de inferencia se conserva y detiene el servicio, sin otra repetición automática.

[Contrato B12](ECHO45-S6-B12-DESIGN.md) · [Seguimiento](ECHO45-S6-B12-LIVE.md).
