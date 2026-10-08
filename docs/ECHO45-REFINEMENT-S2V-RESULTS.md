# Refinamiento con la biblioteca aprendida S2v

Doce tareas de entrenamiento; ningún examen reservado.

| Brazo | Aciertos | Ajuste exacto de ejemplos | Ambigüedad | Programas probados |
|---|---:|---:|---:|---:|
| one_pass | 2/12 | 2 | 0 | 2391 |
| refinement | 2/12 | 2 | 0 | 24000 |
| multi_view | 2/12 | 2 | 0 | 24000 |
| relations | 2/12 | 2 | 0 | 24000 |

Mismo límite de 2000 programas por tarea y brazo; se informa el gasto real porque una sola pasada puede usar menos.
Estos resultados diagnostican desarrollo, no demuestran transferencia reservada ni un 100 %.

[Contrato](ECHO45-REFINEMENT-S2V-DESIGN.md) · [Datos](../lab/seed/refinement-s2v-dev-20260928/summary.json)

Todos los brazos parten de S2v: 84 primitivas y tres conceptos aprendidos con prioridad por frecuencias.
