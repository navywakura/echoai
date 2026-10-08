# S6-B17 — por qué el híbrido dejó sin probar una guarda válida

Investigación privada del 5 de octubre de 2026. B17 está cerrado como
`MICRO_AUDITED_NO_PROMOTION`. Su auditoría independiente es válida. S6 sigue
abierto; el piloto posterior, la campaña, la conservación protegida y el
examen no se han ejecutado para esta condición.

El bloqueo observado está en la selección de experimentos y en la evidencia
que recibe ese selector. Existe una mejora expresable con el lenguaje actual:
el sintetizador sin LLM la encontró en su quinto intento. El híbrido tuvo una
variante válida disponible en sus siete llamadas de refinamiento y nunca la
eligió. No se ha demostrado un techo de capacidad de ECHO ni que aumentar el
tamaño del modelo resuelva este fallo.

| Brazo B17 | Mejor total en las 80 partidas A | Propuestas que pasan V3 A | Resultado |
| --- | ---: | ---: | --- |
| Control B16 | 378 | 0/8 | No supera la base |
| Síntesis sin LLM | 383 | 1/8 | Mejora sin pérdidas, encontrada en el intento 5 y auditada |
| Híbrido | 383 | 0/8 | Conserva una pérdida de score en A42 en su mejor descendiente |

Los cinco niveles adicionales equivalen al 1,32 % del total de desarrollo de
378. No son un porcentaje nuevo de ARC oficial. Alcanzar 383 con una pérdida
individual sigue incumpliendo V3 aunque el score agregado aumente.

Se revisaron código, ocho propuestas de cada brazo, prompts realmente
entregados, gramáticas, rankings, trayectorias, resultados y auditoría. Además,
se prerregistraron y ejecutaron doce partidas de diagnóstico: tres políticas
por dos casos de desarrollo A, cada uno con replay. Los seis pares coinciden
exactamente. Base e híbrido reproducen B17; la variante conocida reproduce
los registros anteriores de PROBE2, descontando la telemetría añadida en B17.
No hubo llamadas nuevas al modelo, partidas B ni examen. Las 192 fuentes del
perfil congelado permanecen intactas. El recibo `analysis.json` valida este
diagnóstico acotado, no certifica S6 ni constituye otra auditoría independiente.

**La condición útil estaba disponible.** En forma legible, la variante
`HOLD=1` ya verificada en PROBE2 es:

```python
if reset_known == 1 and world_events <= 16 and pending_effect == 0:
    HOLD = 1
# Fuera de la guarda se conserva el valor del programa base.
```

El sintetizador B17 encontró la misma guarda con `HOLD=0`. Esto introduce una
diferencia de valor entre brazos, pero el control conocido con `HOLD=1`
también alcanza 383 sin pérdidas en las 80 partidas A. Por tanto, fijar el
primer valor elegido por el híbrido en 1 no explica por sí solo el fracaso.

La reconstrucción de las llamadas muestra lo siguiente. Los índices de
partida conservan la numeración de los artefactos, empezando por cero. Todas
las propuestas del híbrido fijan `HOLD=1`.

| Intento | Guarda elegida | Niveles | Partidas con pérdida | Puesto elegido / puesto de la guarda válida |
| ---: | --- | ---: | --- | --- |
| 1 | `order_known=0, reset_known=1, reset_useful=1` | 374 | 51, 59, 68, 76, 77 | Sin shortlist; válida en la gramática |
| 2 | `reset_known=1, reset_useful=1, world_events≤20` | 383 | 42, 51, 59 | 7 / 5 |
| 3 | `reset_known=1, reset_useful=1, world_events≤16` | 383 | 42, 59 | 1 / 5 |
| 4 | `reset_known=1, world_events≤16` | 383 | 42 | 2 / 4 |
| 5 | `reset_known=1, world_events≤20` | 383 | 42, 51 | 6 / 3 |
| 6 | `reset_pending=1, world_events≤16` | 383 | 42 | 2 / 3 |
| 7 | `reset_pending=1, world_events≤20` | 383 | 42, 51 | 5 / 2 |
| 8 | `world_events≤16` | 383 | 42 | 1 / 2 |

Las siete listas y sus gramáticas permitían explícitamente la guarda válida.
Los prompts del híbrido utilizaron entre 1359 y 1662 tokens de entrada,
dentro del límite de 3072, sin recurrir a variantes recortadas. Las respuestas
fueron sintácticamente válidas. El objetivo de refinamiento avanzó por los
descendientes 1, 2, 3 y 4; conservar el mejor descendiente sí funcionó.
No encontramos un fallo de transporte, de truncamiento ni de cambio de
operador como los que afectaron condiciones anteriores. Los JSON emitidos
no permiten saber el razonamiento interno del modelo. Atribuirlo a su tamaño,
cuantización o una preferencia psicológica sería especulativo.

**El ranking conserva los casos fallidos, pero consulta estados de la base.**
En `echo_arc/guard_synthesis.py:73`, la función `ranked` toma del historial
las partidas ganadoras y la unión de pérdidas del linaje. Sin embargo,
cuenta las activaciones de cada guarda sobre las lecturas del programa base.
Su orden de reparación es lexicográfico:

```text
(-partidas ganadas cubiertas,
 lecturas cubiertas en partidas con pérdidas,
 número de condiciones,
 representación canónica)
```

Esto deja fuera estados nuevos creados por la propia intervención. En A42,
la guarda amplia del intento 4 y la guarda válida coinciden en tres lecturas
de la base. Sobre la trayectoria del candidato fallido cubren cinco y cuatro
lecturas, respectivamente. La lectura adicional ocurre con
`pending_effect=1`. Después del intento 4, la puntuación del ranking basada
en la base empata ambas guardas en cobertura positiva y carga negativa, y
favorece la que tiene menos condiciones.

No son guardas equivalentes en todas las trayectorias de la base: difieren
en otras partidas. El problema concreto es que su puntuación de utilidad
empata y la base de A42 no contiene el contraejemplo decisivo. Una firma
calculada solo sobre la base no puede certificar su equivalencia.

**La evidencia temporal mostrada se detiene demasiado pronto.**
`echo_arc/consumption_timeline.py:70` registra un enlace por partida: el primer
consumo diferente antes de que diverjan las acciones respecto a la base.
`temporal_feedback`, en `echo_arc/guard_synthesis.py:128`, resume hasta dos
enlaces, priorizando una pérdida y una ganancia. Es una descripción prudente
del prefijo común, pero insuficiente para refinar una política cuyo daño
aparece más tarde.

Para A42, el prompt muestra el consumo en el índice de acción 55:
`world_events=6`, `pending_effect=0`, cambio de `HOLD` de 40 a 1. La primera
divergencia de acciones frente a la base está en 81. La trayectoria del
candidato llega después a otra lectura, índice 106, con
`world_events=8` y `pending_effect=1`. Esa lectura queda fuera del resumen.
La partida ganadora A53 también se resume mediante una lectura con
`pending_effect=0`. Los dos ejemplos entregados no separan la condición
que permitiría conservar la mejora y evitar la regresión.

`pending_effect` indica que `actor._tried_at` sigue abierto; no es una etiqueta
de éxito ni una respuesta del examen (`echo_arc/precise_patch.py:49`). En el
consumidor de `HOLD`, `echo_arc/agent.py:1741`, el valor limita la repetición
de ciertas pruebas del reinicio conocido. No detiene todos los movimientos
del agente. La guarda estrecha mantiene el valor base 40 cuando queda ese
efecto pendiente y permite 1 en los contextos seleccionados.

Para comprobar su efecto mantuve `HOLD=1` y cambié únicamente la condición
`pending_effect=0`, frente a la guarda del intento 4:

| Caso | Política | Niveles | Score | Replay |
| --- | --- | ---: | ---: | --- |
| A42 | Base | 5 | 1,627703493 | Idéntico |
| A42 | Guarda amplia, intento 4 | 5 | 1,416285565 | Idéntico |
| A42 | Misma guarda + `pending_effect=0` | 5 | 1,673423433 | Idéntico |
| A53 | Base | 1 | 0,302785989 | Idéntico |
| A53 | Guarda amplia, intento 4 | 5 | 1,772652226 | Idéntico |
| A53 | Misma guarda + `pending_effect=0` | 5 | 2,535943464 | Idéntico |

Entre ambas políticas, A42 comparte el prefijo hasta el consumo 106; allí
los valores son 1 y 40, y las acciones divergen en 107. En A53 ocurre en
los índices 124 y 125. El contraste controlado acredita el efecto de cambiar
la guarda en esos dos casos. No identifica cuánto del score final se debe
exclusivamente a esa primera lectura: cambian también consumos y recorridos
posteriores. Aislar cada evento requeriría otras intervenciones.

La regresión de A42 no es un error de cálculo por contar acciones totales.
El score pondera niveles y el cuadrado de la eficiencia respecto a la
referencia, como implementa `official_game_score` en `echo_arc/runner.py:33`.
El segundo nivel consume 59 acciones en la base, 250 con la guarda amplia
y 112 con la estrecha. Ganar eficiencia en otros tramos no garantiza mejorar
esa función. El score total de las 80 partidas del híbrido sube, pero la
pérdida individual de A42, 0,211417928, infringe el criterio prerregistrado.

**El presupuesto se gasta sin garantizar que se visiten las opciones útiles.**
El LLM puede escoger cualquiera de las ocho opciones. No hay una obligación
de cubrirlas en un plazo acotado. Tampoco se eliminan todas las repeticiones
de comportamiento: los ocho intentos producen solo cinco comportamientos
distintos. El 6 repite el 4; el 7 repite el 5; el 8 repite el 4 y el 6.

`prune_repeated_failures`, en `echo_arc/repair_memory.py:204`, aplica un
criterio conservador sobre características de decisiones completas. Dos
guardas pueden diferir donde `HOLD` nunca se consume y aun así ejecutar
exactamente la misma política. Un análisis retrospectivo de los consumos
reales de los candidatos anteriores detecta las tres repeticiones antes de
sus llamadas respectivas, sin clasificar la guarda válida como repetida.
Esto orienta una corrección; todavía hace falta demostrar y probar que ese
certificado es seguro para el consumidor y lenguaje concretos. No debe
generalizarse a otros operadores ni basarse solo en trayectorias de la base.

Se hicieron dos reconstrucciones adicionales sin jugar ni llamar al modelo:

1. Manteniendo la primera propuesta real del híbrido y eligiendo después
   siempre el primer elemento del ranking B17, se llega a la guarda válida
   `HOLD=1` en el intento 6. Cada resultado intermedio existe en los artefactos
   medidos; el último corresponde al control 33 de PROBE2. El presupuesto
   de ocho intentos no era intrínsecamente insuficiente para ese recorrido.
2. Al recalcular la carga negativa con los consumos de los propios candidatos
   fallidos, conservando los contraejemplos del linaje, la guarda válida pasa
   de los puestos `5,5,4,3,3,2,2` a `5,1,1,1,1,1,1` en las llamadas 2–8.
   Solo se usa el historial disponible antes de cada llamada. La regla de
   recuento retiene la frecuencia máxima por caso y vector observado para
   que repetir un fracaso no multiplique artificialmente su peso.

Ambos análisis son retrospectivos. Conocíamos la solución PROBE2 al diseñar
la investigación. No constituyen descubrimientos autónomos nuevos, ni una
medición prospectiva del beneficio de otro selector o prompt.

**El avance existe, pero no equivale al objetivo pendiente.** El control B16
se queda en 378; el sintetizador B17 recupera 383 sin pérdidas; el híbrido
recupera los cinco niveles y reduce sus pérdidas hasta una sola partida.
Eso localiza mejor el fallo y acredita capacidad disponible. No acredita
ventaja del híbrido sobre el control sin LLM, transferencia a B ni examen.
La base se mantiene en 378 porque el micro compara candidatos contra un
programa fijo y sus mejoras de desarrollo no se promocionan automáticamente.

Hay también una limitación de ingeniería en B17: se registró más información
temporal, pero la selección de evidencia volvió a descartar estados
necesarios para reparar. Se confió al modelo una selección finita sin
garantía de cobertura. Las pruebas del instrumento no incluían una prueba
funcional de reparación cuyo contraejemplo apareciera después de abandonar
la trayectoria original. Tener tests y auditoría correctos permitió creer
los resultados; no garantizó que el algoritmo de investigación fuera eficaz.

No procede explicar este resultado por falta de 500.000 unidades, ausencia
de una operación expresable o necesidad demostrada de otro LLM. Esas
hipótesis requieren otros contrastes. Tampoco procede presentar varias
rondas humanas sobre las mismas partidas A como aprendizaje general del
agente. El dominio actual es un lenguaje pequeño de controles; las futuras
afirmaciones de autonomía y transferencia necesitan pruebas nuevas.

La siguiente condición debe abordar estas causas antes de otra campaña:

1. Alimentar la priorización con consumos de candidatos fallidos y estados
   nuevos, además de los de la base. Mostrar al modelo varios contraejemplos
   temporales, conservando explícitamente la incertidumbre causal.
2. Separar la propuesta de mecanismo de la cobertura de guardas. ECHO debe
   ejecutar una búsqueda acotada y verificable, con presupuesto y regla de
   cobertura declarados, aunque el modelo prefiera repetir otra opción.
3. Certificar equivalencias de consumo solo donde el código permite probarlas
   y comprobarlas con casos de regresión. No colapsar propuestas por una firma
   incompleta de la base.
4. Probar primero escenarios nuevos con daño tardío, cambios de umbrales y
   condiciones, y casos sin solución. Después comparar control B16,
   sintetizador e híbrido con presupuestos y herramientas equivalentes,
   contabilizando también el coste del LLM. Mantener el control sin LLM
   aunque gane. Conservar V3, conservación protegida y B1–B5.

Estas correcciones están propuestas, no integradas en B17 ni evaluadas en una
condición nueva. B17 permanece cerrado y no hay campaña posterior en marcha.

Los artefactos reproducibles son el [plan del diagnóstico](../lab/seed/s6b17-forensics-20261005/PLAN.md),
el [script de análisis y contrastes](../lab/seed/s6b17-forensics-20261005/analyze.py),
el [recibo de las doce partidas](../lab/seed/s6b17-forensics-20261005/analysis.json),
el [análisis de llamadas](../lab/seed/s6b17-forensics-20261005/call-analysis.json),
la [reconstrucción del selector](../lab/seed/s6b17-forensics-20261005/greedy-counterfactual.json),
el [reordenamiento con consumos propios](../lab/seed/s6b17-forensics-20261005/candidate-consumption-ranking.json)
y su [implementación](../lab/seed/s6b17-forensics-20261005/rerank.py).
El [resultado original](ECHO45-S6-B17-RESULTS.md), el
[contrato B17](ECHO45-S6-B17-DESIGN.md) y su
[auditoría](../lab/seed/s6b17-20261004/micro-audit.json) conservan su alcance.
