# E · reparación de búsqueda · desarrollo r1

22/10/2026. **Beam8, puerta prospectiva: ROJA EN DESARROLLO.**
Auditoría: `recorded_result_consistency_pass`; **sin replay completo de búsqueda**. Se verifican
programas devueltos ejecutándolos, predicciones, juez externo, diario,
contadores, límites, fuentes e identidad de tareas. Esto no prueba por separado
que se enumeraran todos los candidatos del frente retenido.

Contrato: [E-BUSQUEDA-REPAIR-DESIGN.md](E-BUSQUEDA-REPAIR-DESIGN.md).
Interfaz original `echo5.solver.solve`, sin cambios al motor ni a ECHO-5.0.
Nueva orquestación `echo58/searchrepair`; revisión independiente y11 pruebas
pasando antes de congelar y generar casos. Diario original de ARC reutilizado,
con hechos del solver, sin crear un segundo thought-bus ni un monólogo.

## Contraste fijado antes de generar

32 tareas independientes nuevas:4 por cada una de6 familias soportadas y2
controles;128 resoluciones pareadas. Agenda por hash con base37000000,
ledger inicial20M, usado0 y contadores vacíos. Seed ledger comprometido antes
de resolver: trabajo 4736. Casos, respuestas del evaluador
y hashes se congelaron antes de la primera resolución.

Cada actor recibe solo demostraciones y entradas de consulta. Nunca recibe
familia, semilla, expected, escenas, testigo o respuestas de consulta.
Los4 brazos conservan326 átomos, profundidad4, máximo12000 candidatos y
2M unidades de trabajo lógico, certified/ranking_bound y caché interned.
Sin biblioteca, propuestas ni aprendizaje. `test_verified` sigue siendoFalse.

## Resultados

| Anchura | Exactos /32 | Erróneos | Falsas afirmaciones | Trabajo lógico | Estados |
|---|---|---|---|---|---|
| 24 | 14 | 0 | 0 | 34534021 | {"ambiguous": 4, "budget_exhausted": 10, "solved": 14, "unsolved": 4} |
| 4 | 15 | 0 | 0 | 13412532 | {"ambiguous": 5, "solved": 15, "unsolved": 12} |
| 48 | 7 | 0 | 0 | 40520844 | {"ambiguous": 4, "budget_exhausted": 17, "solved": 7, "unsolved": 4} |
| 8 | 15 | 0 | 0 | 18939198 | {"ambiguous": 5, "solved": 15, "unsolved": 12} |

Las8 tareas de control requieren abstención; sin falsas afirmaciones, el
máximo de exactos en el conjunto es24/32.

Exactos por familia:

| Familia | Beam24 | Beam8 (propuesto) | Beam4 | Beam48 |
|---|---|---|---|---|
| ambiguous_reflection | 0 | 0 | 0 | 0 |
| below_recolor_reflect | 3 | 4 | 4 | 3 |
| fill_extract_tile | 4 | 0 | 0 | 0 |
| inside_erase_crop | 0 | 3 | 3 | 0 |
| outline_extract_scale | 3 | 0 | 0 | 0 |
| pack_reflect | 4 | 4 | 4 | 4 |
| right_erase_crop_rotate | 0 | 4 | 4 | 0 |
| unsupported_new_color | 0 | 0 | 0 | 0 |

| Condición prospectiva de beam8 | Resultado |
|---|---|
| Más exactos totales que beam24 | cumple |
| Trabajo total no mayor que beam24 | cumple |
| Ninguna familia soportada pierde exactos | no cumple |
| Cero respuestas erróneas y falsas afirmaciones | cumple |
| Mejora inside_erase_crop o right_erase_crop_rotate | cumple |

La ganancia total15 frente a14 oculta una regresión importante: beam8 gana
inside_erase_crop (0→3/4) y right_erase_crop_rotate (0→4/4), pero pierde
fill_extract_tile (4→0/4) y outline_extract_scale (3→0/4). Por eso queda ROJA.
Beam4 empata los15 exactos con menos trabajo; comparte esas regresiones.
La comparación demuestra un intercambio entre familias bajo presupuesto;
no identifica el linaje de cada prefijo descartado ni justifica un selector
que reciba el nombre de familia. Un buscador que preserve los aciertos
anteriores necesita otro diseño prospectivo, no elegir anchura después de
ver las respuestas.

Beam8 fue el candidato principal antes de medir; los controles4/48 pueden
superarlo y eso no permite reemplazarlo retrospectivamente. Un frente más
estrecho declara su poda; no es búsqueda exhaustiva. Agotar presupuesto
mantiene la abstención incluso con alguna hipótesis compatible encontrada.

## Coste y cierre de niveles

| Anchura | Casos con nivel final completo | Candidatos intentados | Profundidades finales (casos) | CPU (s) | Pared (s) |
|---|---|---|---|---|---|
| 24 | 22 | 31192 | {3: 10, 2: 14, 1: 8} | 10.95 | 10.98 |
| 4 | 32 | 10762 | {4: 12, 3: 4, 2: 8, 1: 8} | 3.94 | 3.95 |
| 48 | 15 | 23101 | {2: 19, 3: 5, 1: 8} | 11.08 | 11.10 |
| 8 | 32 | 19399 | {4: 10, 3: 6, 2: 8, 1: 8} | 6.31 | 6.32 |

«Nivel final completo» es el indicador final de cada caso; no suma todos los
niveles recorridos. CPU y pared son descriptivos; las unidades lógicas no
son FLOPs, julios ni tiempo. Trabajo del generador/oráculo/recibos separado:
`{"generation": 905303, "oracle": 78603, "receipt": 1211324}`. Copia pública:
115081; evaluación externa y ejecución de
programas: 684610. Desglose completo por tipo de
trabajo y por familia en `audit.json`.

## Alcance y custodia

Se conserva el resultado histórico12/18 y sus seis agotamientos. No se han
repetido esas tareas ni abierto campañas antiguas: esta medición estudia
casos nuevos de las mismas familias. No acredita ARC general ni arregla por
declaración los seis episodios históricos.

Artefactos: `lab/echo58/searchrepair/dev-20261022-r1/`. Compromiso de
preparación SHA256 `fc556d39bd80412a4ff86e5e48007abadf17ffc518ffdc8b7e8689507bfc535f`; fuentes/archivos custodiados,
casos, diarios y recibos verificados. Hashes finales en `final-manifest.json`.
No se han omitido fallos instrumentales ni ajustado límites después de medir.
Sin LLM, examen o publicación. Se preserva el resultado completo y se cierra
esta comparación; cualquier continuación distinta necesita versión prospectiva.
