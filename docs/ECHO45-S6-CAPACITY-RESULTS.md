# Control de capacidad S6 — resultados

2026-09-28. Solo desarrollo; control humano, sin LLM.

Estado: **NO_POSITIVE_IN_BOUNDED_SEARCH**. S6 sigue **ROJO**.

Se mantuvieron como requisitos +2 niveles A y ausencia de pérdidas individuales A/B. Ningún candidato cumplió ambos. No se abrió un examen.

| Control | A | Pérdidas A | Partidas activadas | Acciones distintas | Veredicto |
|---|---:|---:|---:|---:|---|
| body16 | 178→184 | 16 | 40 | 32 | V3 |
| body12 | 178→182 | 17 | 40 | 32 | V3 |
| body10 | 178→179 | 15 | 40 | 28 | V3 |
| motor16 | 178→183 | 17 | 40 | 33 | V3 |
| keys16 | 178→184 | 16 | 33 | 32 | V3 |
| click16 | 178→177 | 1 | 7 | 1 | V3 |
| after1 | 178→167 | 3 | 20 | 3 | V3 |
| after2 | 178→167 | 3 | 20 | 3 | V3 |
| count_first | 178→178 | 3 | 23 | 6 | V3 |
| order_first | 178→173 | 6 | 23 | 15 | V3 |
| probe4 | 178→178 | 0 | 23 | 0 | V3 |
| probe12 | 178→178 | 0 | 23 | 0 | V3 |
| probe16 | 178→178 | 0 | 23 | 0 | V3 |
| order_support | 178→178 | 3 | 4 | 4 | V3 |
| count_support | 178→178 | 6 | 16 | 7 | V3 |
| count_only | 178→178 | 6 | 23 | 8 | V3 |
| order_only | 178→163 | 15 | 23 | 19 | V3 |
| hold80 | 178→178 | 0 | 6 | 0 | V3 |
| hold20 | 178→181 | 0 | 6 | 3 | V4 |
| babble4 | 178→189 | 19 | 40 | 32 | V3 |

El más cercano, `hold20`, gana tres niveles A sin pérdidas allí. En B mantiene
187 niveles, pero empeora la puntuación de una partida; se rechaza por V4.
Los 20 candidatos y sus replays terminaron a las 15:31 Madrid, en 46 minutos.
El piloto condicionado se omitió automáticamente, con cero llamadas al modelo.

Una mejora manual valida la capacidad del instrumento; no demuestra automejora ni transferencia.
Una búsqueda sin control positivo solo descarta estos 20 candidatos bajo este presupuesto.

[Contrato](ECHO45-S6-CAPACITY-CONTROL.md) · [Evidencia](../lab/seed/s6-capacity-20260928/summary.json)
