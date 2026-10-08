# S5-E · v5.7 · VERDE · 2026-09-27

Examen cerrado: v5.7 supera a v5.6 en estado oculto del gym, con fuentes
intactas y replay exacto. La implementación ya existía antes de esta sesión.
Contrato fijado antes: [S5-E](ECHO45-S5-E-DESIGN.md).

60 juegos nuevos (semillas 7000–7059), cinco niveles, tres semillas del agente,
2000 decisiones del agente por partida: 900 niveles posibles sumando las
repeticiones. El runner registra además reinicios automáticos tras GAME_OVER;
no consumen ese presupuesto ni incrementan `actions_per_level`. La puntuación
usa la fórmula oficial aplicada a ese contador congelado, no un scorecard
de competición. Se aplica la misma convención a los tres agentes.

| Agente | Niveles por rep | Total | % de niveles | Puntuación media /100 |
|---|---|---:|---:|---:|
| v5.6 | 134 · 138 · 127 | 399 | 44,3 % | 2,2658 |
| v5.7 | 159 · 162 · 154 | **475** | **52,8 %** | **3,7604** |
| Azar | 12 · 13 · 12 | 37 | 4,1 % | 0,3642 |

Son **76 niveles más (+19,0 %)** y una puntuación un 66,0 % mayor.

| Criterio | Evidencia |
|---|---|
| E1 | 300/300 niveles del solucionador; generación repetida idéntica |
| E2 | Azar 4,1 %, por debajo del 15 % |
| E3 | 475 > 399 niveles |
| E4 | 3,7604 > 2,2658 |
| E5 | Replay de las 60 partidas de v5.7 rep 0 idéntico en acciones y frames; fuentes intactas |

**E1 ∧ E2 ∧ E3 ∧ E4 ∧ E5: VERDE.**

La ganancia es concreta: sumando las tres reps, la familia de copia H4 pasa
de 15 a 91 niveles. H1 (orden) queda en 107, H2 (temporizador) en 157 y H3
(conteo) en 120 para ambos agentes. No se ha añadido un módulo propio de orden
o conteo.

Datos: `lab/seed/arc3gym/s5e/`, con registros por partida, acciones, hashes
de frames, informes de cada rep, validación y `audit.json`.
Congelación: `lab/kaggle/s6b0-20260927/evaluation-freeze.json`.

Límites: son juegos de nuestro simulador; no es el examen oficial de 112
niveles ni una medición del objetivo R3. Sigue declarada la caída conocida de
desarrollo oficial de v5.7 (1,033 → 1,000 frente a v5.6, pierde una semilla
de g50t). No ha cambiado el resultado rojo de S6-A ni prueba por sí solo que
un modelo mejore a ECHO.
