# TRANSFER-3 v6 — optimismo por cero: diseño fijado antes de ejecutar

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Ningún brazo queda
promovido por este documento. No se genera ni se abre B/C. No se toca ninguna
fuente congelada: v1–v5 y sus inventarios se conservan intactos.

## Hipótesis

A igual presupuesto, entrenar perjudica. El cribado v4 sobre 64 salas lo dice
sin ambigüedad:

| Brazo v4 | W/L/T vs scratch | Fallos nuevos | Movimientos ahorrados en éxito conjunto | Cribado |
|---|---:|---:|---:|---|
| corrected | 11/13/40 | 2 | −40 | no |
| coverage_only | 12/14/38 | 4 | −4 | no |
| reward_only | 11/7/46 | 1 | −12 | no |

El diagnóstico v5 da la causa candidata. De las 372 decisiones de `corrected`
sensibles a Q, **244 eligen una acción sin ninguna muestra en esa feature**, y
sólo 59 tienen todas las acciones ofrecidas muestreadas. Con recompensa de
deriva negativa, toda acción muestreada converge a un valor negativo mientras
la no muestreada permanece en 0. El desempate `-values[path[0]]` prefiere
entonces, de forma sistemática, la acción sobre la que no hay evidencia.

**Hipótesis v6: el cribado no falla por falta de exploración sino porque el
cero de una acción no muestreada se lee como valor aprendido.** Es una
ambigüedad de transporte, no de política.

## Intervención — un solo factor, en la exportación

Al exportar la Q de la escuela, para cada feature con al menos una muestra:

- acción muestreada → su valor aprendido, sin tocar;
- acción no muestreada → suelo por fila `min(valores muestreados) − 1`,
  recortado en −127.

No cambia el planificador, ni la recompensa, ni la escuela, ni el esquema
`transfer3-relative-q-v2`, ni el examen, ni el consumidor enjaulado. El
payload sigue pasando por `policy.validate` congelado. Si el suelo recorta en
−127 puede empatar con una acción muestreada de ese valor; se declara y no se
corrige con un segundo mecanismo.

## Brazos

Un solo factor entre brazos. `baseline` y `pessimistic` comparten **una misma
corrida de escuela** y difieren únicamente en la exportación.

| Brazo | Escuela | Exportación |
|---|---|---|
| `scratch` | ninguna | Q vacía |
| `baseline` | reparada v5, 128 movimientos | estándar |
| `pessimistic` | la misma corrida | con suelo |

Escuela reparada = `repair_v5.episode`: terminalidad real, un `scan` por
timestamp, asignación CAM comprobada, reserva adjudicada por función común,
bono de fallo −32. Recompensa de progreso, idéntica a `corrected` de v4.

## Predicción registrada de antemano

`baseline` debe reproducir exactamente el cribado de `corrected` en v4
(11/13/40, 2 fallos nuevos). Las reparaciones de v5 no deberían mover nada en
estas salas: no hay fallos en la escuela, así que el bono −32 nunca dispara, y
la terminalidad en la llegada no cambia el arranque porque la fila Q del estado
meta es cero. **Si `baseline` no replica, la corrida queda anulada** y el
desacuerdo se investiga antes de leer `pessimistic`.

## Criterio

Se importa `rehearsal_v4.screen` sin modificarlo ni copiarlo. Un brazo pasa el
cribado de desarrollo si y sólo si:

- cero colisiones, violaciones de reserva, hechos falsos, escrituras imaginadas
  y modelos alterados en las 64 misiones;
- cero fallos nuevos respecto a scratch;
- victorias > derrotas;
- movimientos ahorrados en éxito conjunto > 0;
- signo de una cola con α ≤ 1/60.

Presupuesto de escuela 128 movimientos, igual en todos los brazos, y el coste
de entrenamiento se reporta sumado al de examen en `train_plus_exam_moves`.

## Salas

Las 64 salas de examen de v4 (`20264601`+) y las semillas de escuela de v3, sin
volver a seleccionar nada. El inventario congelado de v4 se comprueba ruta a
ruta antes de ejecutar. `isolated=True`, mismo consumidor enjaulado que v4.

## Qué no prueba

No prueba aliasing de representación, ni mundos dinámicos, ni geometría nueva,
ni custodia, ni vuelo. Aprobar este cribado **no pone TRANSFER-3 en verde**: es
el cribado público de desarrollo a igual presupuesto, un prerrequisito del
protocolo final, no el examen A→B→C.

## Regla de parada

Si `pessimistic` no pasa, la explicación restante es aliasing de representación
—los 14 pares con órdenes opuestos que midió v5— y el siguiente experimento es
un cambio de feature observable, no más episodios con las mismas features.
