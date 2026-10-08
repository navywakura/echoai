# TRANSFER-3 v3 — corrección y dos pruebas independientes

Protocolo público de desarrollo, fijado antes de ejecutar v3 (2026-09-18).
No es un protocolo final ni un examen reservado. V1/v2 se conservan.

## Corrección

V2 incorpora `after` para aprender y vuelve a incorporarlo al decidir. V3
conserva ese orden causal, pero la segunda consulta de una captura idéntica
no vuelve a actualizar evidencia ni visitas. Timestamp repetido con contenido
distinto, o timestamp anterior, se rechaza. Comprobar por episodio:
`ingestions == unique_captures == sum(visits)`, también en la llegada final.
No se modifica COMPOSE certificado ni el runtime de examen.

## Factores

| Brazo | Recompensa | Selección durante A |
|---|---|---|
| corrected | `8*(L1_before-L1_after)-1+32*arrival` | COMPOSE original |
| reward_only | `-1+32*arrival` | COMPOSE original |
| coverage_only | Igual a corrected | Cada cuarta decisión de búsqueda: acción admisible menos muestreada en esa característica; empate por ID |
| scratch | No entrena Q | Cinemática común y Q vacía |

`arrival` requiere meta y observación posterior. La recompensa nueva elimina
el castigo adicional por alejarse en distancia L1, no todo coste de moverse.
No se prueban combinaciones de recompensa nueva y cobertura nueva.
Cobertura cuenta ejecuciones observadas, no propuestas; utiliza sensores,
camino de retorno conocido y reserva. Pasa por el gate original. Los conteos
no se exportan ni se explora en examen.

Cada variante parte de Q vacía; mismas 4 salas A × 3 pasadas y límite de
64 movimientos por episodio. La escuela es on-policy: al cambiar decisiones
cambian las trayectorias. No es una comparación sobre una cinta idéntica ni
a igual cantidad de muestras. Se publican movimientos, coste simulado,
estados/acciones visitados y todos los fallos para exponer ese coste.

Examen: las mismas 16 salas públicas v2, sin nueva selección. 4 brazos × 16
= 64 misiones con parámetros congelados y mismo consumidor aislado. Comparar
corrected con v2 y scratch; recompensa y cobertura con corrected y scratch.
Priorizar metas, después movimientos sólo en éxitos conjuntos. Dos fallos
son empate; no vender una abstención barata como eficiencia.

No cambiar criterios tras ver resultados, no declarar significación o cierre
por estos datos ya examinados. La auditoría reconstruye escuela, geometrías,
parámetros y misiones. Los hashes de fuentes v2 se verifican por sus entradas
guardadas, sin exigir que no existan archivos nuevos.
