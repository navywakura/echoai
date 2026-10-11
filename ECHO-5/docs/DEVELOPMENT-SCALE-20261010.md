# Comprobación de escala antes de confirmación

Plan registrado antes de ejecutar, en
`artifacts/development-scale-20261010-r1/plan.json`. Fuentes
`f6fdf885be552cf519667a63bfcd63d1c5f2028d5b7bec2880307509c8fab98c`.
Se mantienen algoritmos, generadores, gramática, costes y umbrales. Se amplían
los casos de desarrollo para examinar dos dudas que la muestra pequeña no
resolvía: amortización de adquisición y repetición del aprendizaje temprano.
La auditoría en otro proceso terminó con `valid:true` y fuentes conservadas.

| Transferencia, 72 casos por condición | Aciertos en 48 compatibles | Predicciones en 24 controles | Trabajo total |
|---|---:|---:|---:|
| Biblioteca adquirida | 43 | 0 | 89.779.080 |
| Biblioteca fija | 43 | 0 | 87.387.403 |
| Biblioteca vacía, con caché | 43 | 0 | 98.662.228 |
| Biblioteca irrelevante, mismo número de registros | 43 | 0 | 112.822.948 |
| Vacía sin caché | 43 | 0 | 200.968.594 |
| Búsqueda poco profunda | 0 | 0 | 45.626.440 |
| Representación anterior | 0 | 0 | 53.633.333 |

La memoria reduce un 9,00 % el trabajo completo frente a biblioteca vacía y
un 20,42 % frente a biblioteca irrelevante. También reduce el trabajo semántico;
la diferencia no procede sólo de metadatos. Frente a la biblioteca fija paga
un 2,74 % más e iguala aciertos: cumple la no inferioridad del contrato V2,
pero no demuestra superioridad frente a ese conocimiento suministrado. La
caché ahorra aproximadamente la mitad del trabajo conservando resultados.
Se incluyen adquisición, preparación, generación y evaluación.

Tres familias compatibles obtienen 12/12. `pack_rotate_scale` obtiene 7/12;
queda documentada esa limitación. Las dos familias de control producen cero
respuestas, lo cual sólo acredita abstención en esos casos concretos. Los
resultados son sintéticos y no son una puntuación oficial ARC.

El currículo amplía la semilla de desarrollo ya declarada a 32 ejecuciones
emparejadas, con tres consultas al profesor y ocho problemas de evaluación
por ejecución. El criterio principal sigue siendo la media de exactitud tras
cada consulta, tratando la ejecución como unidad estadística. Los problemas
de evaluación no retroalimentan la selección. No se cuentan prefijos o
problemas correlacionados como ejecuciones independientes.

| Condición | Aciertos finales | Trabajo total equivalente por brazo |
|---|---:|---:|
| Adaptativa | 256/256 | 27.721.021 |
| Aleatoria | 193/256 | 27.573.122 |
| Secuencial | 233/256 | 27.627.037 |

La adaptativa cumple los umbrales numéricos de aprendizaje temprano,
incertidumbre, regresiones y coste del contrato, con aproximadamente 0,54 %
de sobrecoste medio relativo por ejecución frente al azar. Los aciertos
finales siguen siendo una medida descriptiva en V2. Se conservan los resultados
anteriores de cuatro ejecuciones, donde todos los brazos terminaron empatados.

El banco exhaustivo común representa el 97,35 % del trabajo adaptativo. Si se
considera sólo el trabajo exclusivo de selección y aprendizaje, el adaptativo
gasta 734.357 unidades frente a 586.458 del aleatorio: un 25,22 % más. El
sobrecoste total del 0,54 % pertenece al protocolo con banco compartido; no
demuestra que el selector sea barato para cualquier despliegue. El ledger
tampoco mide julios ni incluye toda la instrumentación y auditoría. Las cuatro
ejecuciones de la muestra anterior están incluidas en las 32; no son 36
réplicas independientes. La revisión acotada está en
`artifacts/scientific-review-20261010-r1/REVIEW.md`.

Estos datos permiten preparar una confirmación; no la sustituyen. La
partición reservada no se ha ejecutado durante este ensayo. Los recibos de
medición y auditoría están en el mismo directorio y conservan el plan, el
script de lanzamiento, fuentes, contratos, diarios y controles completos.
