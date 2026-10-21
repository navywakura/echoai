# E4-ROLES-1 v2 — contrato (aprobado 2026-09-24)

Motivo: [D v1 rojo](ECHO4-ROLES1-D-RESULTS.md) (`168e978b…`). La semilla 264106
quedó atrapada en un empate Q en la fila «falló la contraparte 1». Con
`evidence_greedy=True`, el agente nativo no vuelve a explorar tras agotar el
presupuesto de evidencia, y nada rompe el ciclo.

## Único cambio

El aprendiz de **todos** los brazos se construye con `evidence_greedy=False`.
Tras el presupuesto de evidencia vuelve la **exploración periódica nativa**
(cada 8 turnos, acción `turno % 3`), que ya trae `nexus0` y es igual en todos
los brazos. Los brazos fijos (`rank_follow`, `self_only`) no cambian porque su
propuesta es fija. Se conservan también la corrección del veto de C.

Nada más cambia: física, pagos, deriva, filas (enmienda 1), brazos, umbrales de D,
escenarios C y sus criterios. **No se rebaja ningún umbral.** Se asume el coste
de explorar, que se publica.

## Etapas

1. **Desarrollo nuevo**, semillas **311, 323, 347**: el mismo criterio de
   desarrollo A/B (supera a cada brazo; recupera antes que `cumulative`) y los
   mismos testigos C1–C8. C0 pasa a ser: con `evidence_greedy=True`, la sesión
   v2 reproduce bit a bit la sesión C v1.
2. **D v2** con cohortes nuevas **265001..265008** y **265101..265108**, mismos
   cinco criterios que v1. Solo se abre con la Aprobado:.
3. Auditoría en proceso nuevo. Solo su recibo puede dar `roles1_green=true`.

Las cohortes 264xxx de v1 están quemadas y no se reutilizan. v1 conserva su rojo.
