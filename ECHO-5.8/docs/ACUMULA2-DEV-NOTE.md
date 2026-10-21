# B v2 · ACUMULA-2 · nota de desarrollo (antes de contrato y examen)

20 de octubre de 2026. Diseño tras la revisión de Argon
(`research/ARGON-ACUMULA-V2-20261020-REVIEW.md`): mismas rondas en todas las
rondas (DistShift1, LavaCrossingS9N3, KeyCorridorS3R2, BlockedUnlockPickup),
métrica = episodios fallidos en la sonda, controles nuevos `lote_final` y
`vacia_online`, puerta estricta. Código `echo58/acumula2/` (importa v1 sin
tocarla). Datos: `lab/echo58/acumula2/dev-20261020T183421.json` (3 macros,
semillas 5 000 000+, sonda de desarrollo LavaCrossingS9N1, LavaCrossingS9N2,
ObstructedMaze-1Dlh, KeyCorridorS3R3). No hay contrato ni examen.

## Resultado de desarrollo (suma de 3 macros, episodios fallidos / daño en sonda)

| Brazo | r0 | r1 | r2 | r3 | r4 | r5 |
|---|---|---|---|---|---|---|
| **recursiva** | 311/173 | **34/14** | 34/0 | 51/0 | 57/0 | 51/0 |
| azar | 311/173 | 193/173 | 209/152 | 220/149 | 212/118 | 144/66 |
| sin_acumular | 311/173 | 34/14 | 60/17 | 103/21 | 108/29 | 127/33 |
| fija | 311/173 | 189/170 | 203/163 | 216/153 | 220/150 | 224/148 |
| lote_final | = fija hasta r4 | | | | | 127/33 |
| vacia_online | 154/25 (constante) | | | | | |

## Lectura

1. **Q1 (≥ 3 mejoras seguidas) es inalcanzable con este agente, por
   estructura.** Con las rondas estacionarias ECHO ve todos sus errores de
   memoria en la ronda 1 y los corrige a la vez (`refine` de las clases 8 y 12
   por rango 0): un escalón 311 → 34. Lo que queda (pelota que tapa la puerta,
   llave dentro de una caja, KeyCorridor) son límites de la **política base**,
   no creencias de memoria: ninguna edición del menú los toca.
2. **Lo que sí se ve, y es nuevo:** corregir ronda a ronda gana a corregir todo
   al final (`recursiva` 51 frente a `lote_final` 127), a no acumular (127), a
   más datos sin edición (224), al azar (144) y a empezar sin memoria (154).
   La memoria aprendida con sus correcciones es mejor que ninguna memoria; sin
   correcciones es peor (311 frente a 154).
3. **Para ver automejora sucesiva haría falta que ECHO pudiera editar su
   política** (no solo cómo lee la memoria), de modo que cada arreglo destape
   el siguiente atasco. Es el terreno de RSI-1 (biblioteca DSL), que salió
   rojo.

## Opciones (decide Roger)

| Opción | Qué es | Coste / riesgo |
|---|---|---|
| **1 · Cerrar B v2 en rojo en desarrollo e ir a C (ENJAMBRE)** | El roadmap dice «5.8 verde = A + (B o C)». A ya está verde | Recomendada |
| 2 · B v3 con ediciones de política | Menú de primitivas genéricas de comportamiento que ECHO pueda combinar | Grande; historial rojo (RSI-1) |
| 3 · Redefinir B como «autocorrección que gana a todos los controles» | Q1 fuera; Q2 con `lote_final` y `vacia_online` | Probablemente verde, pero es una afirmación **más débil** que la del roadmap y debe llamarse así (no «automejora recursiva») |
