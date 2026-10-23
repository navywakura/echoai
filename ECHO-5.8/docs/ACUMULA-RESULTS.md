# B · ACUMULA (v1) · resultados del examen

20 de octubre de 2026. Examen único sobre `lab/echo58/acumula/preflight.json`
(16:58, semillas `313a0098…`), contrato `ACUMULA-DESIGN.md` + enmienda 1.
Datos: `lab/echo58/acumula/exam/*.json` (5 brazos × 10 macros, 0 caídas),
`lab/echo58/acumula/results.json`. Cálculo: `python3 -m echoai.echo58.acumula.report`.

## Veredicto: **ROJO** (Q1 falla; Q2 y Q3 pasan)

| Predicción | Qué pedía | Resultado | |
|---|---|---|---|
| **Q1** mejora sucesiva | daño medio en sonda de `recursiva` baja en ≥ 3 rondas seguidas sin perder éxito | 29,6 → 29,9 → 29,9 → 26,9 → **0,0** → 0,0; racha máxima 2 | **falla** |
| **Q2** mejor que los controles | daño en sonda tras la ronda 5 < azar, sin_acumular, fija (Wilcoxon, Holm, α = 0,01) | recursiva 0,0 frente a azar 30,7, sin_acumular 29,8, fija 28,8; p = 1/1024 en las tres | **pasa** |
| **Q3** sin regresión | configuración final frente a base en las familias de examen de A (A2) | daño 85,3 → 0,0; éxito 110,9 → 195,9 (de 200) | **pasa** |
| Q4 (informa) | hueco de la lava de A | DistShift2 A2: 49,5 daños → 0,0; 0,4 éxitos → 49,9 | cerrado |
| LLM (informa) | `gpt-oss-120b` elige del mismo menú | daño final 22,9 frente a recursiva 0,0 (p = 1) y azar 30,7 (p = 0,18); 2 errores de API en 50 rondas | no mejor que el azar |

Medias por macro; la sonda son 4 familias × 30 episodios = 120 por ronda.

## Por qué Q1 sale rojo

**Todo el daño de la sonda está en una sola familia**: LavaCrossingS11N5
(296 daños en las 10 macros en la ronda 0). Dynamic-Obstacles-Random-6x6,
BlockedUnlockPickup y ObstructedMaze-1Dl empiezan y acaban con 0 daños en
todos los brazos.

| Daño en sonda, suma de 10 macros | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| recursiva · LavaCrossingS11N5 | 296 | 299 | 299 | 269 | **0** | 0 |
| fija · LavaCrossingS11N5 | 296 | 297 | 296 | 298 | 291 | 288 |

Esa lava tiene la clase morfológica «muchas casillas, sin borde» (firma 12),
que en el entrenamiento era suelo. `recursiva` la separa del suelo con
`refine((12, ENTER, 0), rango 0)` en la **ronda 4**, que es la primera ronda con
una lava de esa clase (LavaCrossingS9N3). Hasta entonces nada en las rondas
culpa a esa clave. Con un único peligro arreglable en la sonda, la curva solo
puede ser un escalón: Q1 no podía ver tres mejoras seguidas.

## Lo que sí muestra (sin cambiar el veredicto)

1. **ECHO corrige sus reglas desde sus fallos y no se degrada.** Tras la
   ronda 5, 0 daños en la sonda en las 10 macros; los tres controles se quedan
   en ~29–31. `fija` (más datos, sin automejora) no arregla nada.
2. **Sus correcciones transfieren** a las familias de examen de A: daño 85 → 0
   y éxito 111 → 196, con la misma memoria. La lava de A2, que A no
   transfería, queda resuelta.
3. **El LLM no propone mejor que el azar** con el mismo diagnóstico y la misma
   puerta.

## Declaraciones

- La enmienda 1 (bits de rango, aprobados por Nav; diagnóstico; K = 6;
  puerta de no inferioridad) se escribió antes de congelar. El riesgo de Q1 se
  declaró antes del examen (§6).
- Q5: varias ediciones aceptadas no hacen nada (p. ej. `verify`/`silence` de
  una clave ya partida); gastan presupuesto de la propia `recursiva`.
- Q3 usa la misma memoria final para la configuración base y la final: mide
  solo el efecto de las ediciones.

## Siguiente

B v1 queda **roja** para siempre. Lo que sigue es **B v2**, con contrato
nuevo, semillas nuevas y predicciones escritas antes. La sonda tiene que
contener varias clases de peligro independientes que se aprendan en rondas
distintas, y la memoria de partida debe empezar sin margen. Así la pregunta
«¿mejora ronda tras ronda?» tiene dónde verse.
