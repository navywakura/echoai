# S6 · reparación de predicciones de transición

Control humano completado el 29 de septiembre a las 01:28 UTC.
**Instrumento positivo y auditado; S6 todavía no está VERDE.** Auditoría
independiente del ganador terminada a las 01:36 UTC, con otra caché/proceso,
base A/B fresca y repetición completa del candidato. Ninguna propuesta del
modelo ni reserva final en este control.

El observador registró 2654 ocasiones en A donde el modelo de transiciones
predecía un cambio y la acción no lo produjo. Los dos grandes bloqueos estaban
en partidas conocidas v3/11 y v3/19. El arreglo revisa una predicción obsoleta
solo después de observaciones repetidas; conserva los hechos históricos.

| Control preregistrado | A antes → después | Pérdidas individuales A | B antes → después | Pérdidas individuales B | Veredicto |
|---|---:|---:|---:|---:|---|
| reinicio conocido, estancamiento ≥8, umbral 1 | 178 → 186 | 0 | 181 → 184 | 1 | Rechazado V4 |
| cuerpo conocido, estancamiento ≥8, umbral 1 | 178 → 186 | 0 | 181 → 184 | 1 | Rechazado V4 |
| estancamiento ≥8, umbral 2 | 178 → 186 | 0 | 181 → 184 | 1 | Rechazado V4 |
| estancamiento ≥16, umbral 4 | **178 → 186** | **0** | **181 → 181** | **0** | **Aceptado** |

Cada conjunto tiene 40 partidas y 200 niveles posibles. La mejora del control
aceptado en A es **+8 niveles, +4,49% relativo, +4 puntos porcentuales** de
niveles posibles (89%→93%). No es una puntuación ARC oficial. A/B y sus replays
coinciden; cuatro pruebas del operador pasan. La base y el control desactivado
conservan comportamiento nativo.

En las mismas 40 partidas A, los registros del control aceptado muestran:

| Medida de desarrollo | SEMILLA | Control humano | Cambio relativo |
|---|---:|---:|---:|
| Partidas con los cinco niveles resueltos | 33 | 35 | +6,06% |
| Acciones emitidas, incluidos reinicios automáticos | 21594 | 18567 | −14,02% |

Son medidas descriptivas de esta batería conocida. Las contradicciones
observadas pasan de 2654 a 67, pero las trayectorias también cambian: ese
descenso no se interpreta como un porcentaje de precisión del modelo ni
como transferencia a ARC. [Base A](../lab/seed/s6-transition-capacity-20260929/measurements/baseline/A.json)
· [Control A](../lab/seed/s6-transition-capacity-20260929/measurements/controls/stuck_4/A.json).

El umbral mayor estaba entre los cuatro controles fijados antes de medir.
No se cambió después de los rechazos. B9 ya integra este operador en la
gramática, el generador y la verificación. Para atribuir automejora a ECHO
falta que lo proponga a partir de sus observaciones, verificar la mejora y
superar los tres comparadores en un examen nuevo. El control humano ganador
no se incorpora a los prompts.

[Contrato](ECHO45-S6-TRANSITION-CONTROL.md) ·
[Resultados íntegros](../lab/seed/s6-transition-capacity-20260929/summary.json) ·
[Auditoría](../lab/seed/s6-transition-capacity-20260929/audit.json) ·
[Siguiente experimento S6-B9](ECHO45-S6-B9-DESIGN.md).
