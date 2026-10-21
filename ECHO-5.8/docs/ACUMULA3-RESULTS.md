# B v3 · ACUMULA-3 — resultados del examen

20 de octubre de 2026. Contrato: [ACUMULA3-DESIGN.md](ACUMULA3-DESIGN.md)
(aprobado, enmienda 1 antes de `preflight`). Examen corrido **una vez**:
70 trabajos (7 brazos × 10 macros), 19:38–21:51 UTC, 0 fallos de ejecución.
Datos: `lab/echo58/acumula3/exam/*.json`; informe `lab/echo58/acumula3/results.json`
(sha256 `5411952cb3e7a229…`); congelación `lab/echo58/acumula3/preflight.json`
(semillas `e29cb5a2…`).

## Veredicto: **VERDE** (Q1 ∧ Q2 ∧ Q3, `destroyed == 0`) — confirmado por verificador independiente

El verificador recalculó la congelación (17 claves idénticas), las semillas (`e29cb5a2…`) y Q1–Q5 con su propio Wilcoxon exacto + Holm, revisó los controles en el código, repitió `vacia_online` m03 y `fija` m05 (idénticos byte a byte salvo `secs`) y pasó los 8 tests. Notas menores: los JSON de `vacia_online` no llevan `destroyed` (no editan; cuenta 0); el primer trabajo terminó a las 19:55 (19:38 es el `preflight`).

## Curva de la sonda (media sobre 10 macros, fallidos/daño, 120 episodios por macro)

| Brazo | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| **recursiva** | 94,3/58,6 | 35,4/3,9 | 22,3/0 | 21,0/0 | 15,8/0 | **13,8/0** |
| azar | 94,3/58,6 | 85,7/49,6 | 81,8/46,4 | 76,6/39,4 | 73,6/39,2 | 66,4/30,5 |
| sin_acumular | 94,3/58,6 | 35,4/3,9 | 32,0/4,2 | 38,1/5,2 | 43,8/7,8 | 43,3/10,3 |
| fija | 94,3/58,6 | 93,7/58,3 | 94,2/56,6 | 93,5/54,3 | 94,0/52,7 | 94,1/51,8 |
| lote_final | — | — | — | — | — | 43,2/10,3 |
| vacia_online | 77,0/39,9 | | | | | 77,0/39,9 |
| piezas_dadas (se informa) | 70,6/58,6 | 20,2/7,0 | 15,2/0 | 16,1/0 | 14,6/0 | 13,3/0 |

## Predicciones

- **Q1 · mejora sucesiva — PASA.** 5 de 5 transiciones bajan estrictamente y
  el daño no sube en ninguna (racha 5; hacían falta 3).
- **Q2 · mejor que los controles — PASA.** Los cinco Wilcoxon dan
  p = 0,00098 (10 de 10 macros a favor frente a cada control); los cinco
  pasan Holm (α = 0,01).
- **Q3 · sin regresión — PASA.** Banco de examen de A, misma memoria final:
  base daño 78,3 / éxito 68,4 → final daño 0 / éxito 184,0.
- **Q4 (se informa):** en 10 de 10 macros entra en r ≥ 2 alguna edición que
  ya se había probado y rechazado antes (las más frecuentes:
  `commit+no_repick` 8, `verify (14,PICK,0)` 8, `verify (0,PICK,0)` 8,
  `order` 7, `no_retoggle` 6, `clear` 6).
- **Q5 (se informa):** `recursiva` 13,8 frente a `piezas_dadas` 13,3 en r5;
  ni una gana a la otra (p 0,80 y 0,33).
- **Q6 (se informa):** r1 casi siempre `refine` de ENTER (10/10 macros, son
  las ediciones de memoria de la lava/agua); r2 `order`, `verify` de PICK y
  `commit+no_repick`; r3 `verify` y `no_retoggle`; r4 `verify` de TOGGLE y
  `clear`.
- `destroyed` = 0 en los 70 trabajos.

## Por familia (suma de 10 macros, fallidos de 300)

| Familia | recursiva r0 → r5 | azar r5 |
|---|---|---|
| LavaCrossingS11N5 | 294 → 3 | 134 |
| DistShift2 | 292 → 6 | 215 |
| ObstructedMaze2Dlh | 266 → 26 | 185 |
| DynObsRandom5 | 91 → **103** | 130 |

## Lo que esto dice y lo que no

1. **Dice:** ECHO, a partir de sus propios fallos medidos, elige y encadena
   ediciones de memoria y piezas de política durante cinco rondas seguidas,
   cada una mejor que la anterior en mundos nuevos, y gana a los cinco
   controles en las 10 macros. El riesgo 1 del contrato no se dio: la mejora
   no se quedó en un escalón.
2. **No dice que ECHO invente conductas.** Las piezas las diseñé yo (Claude)
   mirando trazas de desarrollo. Dárselas todas desde el principio
   (`piezas_dadas`) acaba igual (13,3 frente a 13,8). El mérito medido es
   **elegir, ordenar y acumular**, no crear piezas.
3. La primera bajada (94 → 35) son ediciones de memoria, como en B v2; lo
   que B v3 añade son las mejoras 2 a 5.
4. **DynObsRandom5 empeora un poco** (91 → 103 fallidos en 300): ninguna
   pieza ayuda con obstáculos que se mueven y la memoria final la perjudica
   algo. No cuenta en contra de las predicciones (se miden sobre la suma),
   pero es un defecto real.
5. ObstructedMaze2Dlh, que el contrato temía inalcanzable (riesgo 2), baja
   de 266 a 26.

Este verde no reetiqueta B v1 (roja en examen) ni B v2 (cerrada roja en
desarrollo).
