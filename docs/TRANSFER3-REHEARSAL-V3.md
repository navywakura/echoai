# TRANSFER-3 v3 — captura única, recompensa y cobertura por separado

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.**
Diseño fijado antes de ejecutar: [protocolo v3](TRANSFER3-V3-DESIGN.md).
Código anterior e informes v1/v2 conservados sin modificaciones.

## Corrección de la doble contabilización

`school_v3.Student.update` incorpora una captura sólo una vez. La llamada
posterior de `decide` sobre exactamente esa misma captura no vuelve a
incrementar visitas ni evidencia. Una captura diferente con igual timestamp,
o una anterior, produce error. Una captura posterior en la misma posición
sí cuenta como observación nueva.

En el episodio que reprodujo el problema: **6 movimientos, 7 timestamps,
7 incorporaciones y 7 visitas**, en lugar de las 13 actualizaciones de v2.
Las seis consultas duplicadas se identifican, pero no son evidencia nueva.
Las doce escuelas corregidas suman **125 capturas únicas, 125 incorporaciones
y 125 visitas**. El aprendizaje sigue ocurriendo tras la consecuencia y
antes de la siguiente decisión. No se cambia la fórmula de recompensa ni
el código de selección en `corrected`, pero sí su entrada: las visitas
alimentan el coste del planificador. La equivalencia conductual no es estructural.

Resultado importante: **la Q final corregida es idéntica a la de v2**, con
16/16 empates en el examen. En este banco la anomalía existía, pero corregirla
no explica ni mejora el resultado conductual. No se atribuye una ganancia
inexistente a la reparación.

El control primario omitido en la primera redacción es **corrected frente
a scratch: 3 victorias, 3 derrotas y 10 empates**. Los 260 frente a 262
movimientos agregados no demuestran ventaja de la escuela.

## Dos intervenciones independientes

Mismas cuatro salas de entrenamiento, tres pasadas, límites por episodio y
dieciséis salas públicas de examen. Cinemática, representación Q, planificador
y gates compartidos. No se ha probado una combinación de ambas variantes.

| Brazo | Cambio respecto a corrected | Metas | Movimientos en examen |
|---|---|---:|---:|
| Scratch | Q sin entrenar | 15/16 | 262 |
| Corrected | Sólo reparación de captura | 15/16 | 260 |
| Reward only | Elimina el término de progreso L1: `-1 + 32*arrival` | 15/16 | 245 |
| Coverage only | Cada cuarta búsqueda propone una acción admisible poco muestreada | 15/16 | 248 |

Son **64 misiones aisladas**. Cero colisiones, hechos falsos y violaciones
de reserva observados; parámetros congelados en las 64. Los movimientos
totales incluyen abandonos, por lo que no bastan para declarar eficiencia:
la comparación por caso prioriza llegada y sólo compara movimientos entre
dos llegadas; dos fallos son empate.

### Sólo recompensa

Frente a corrected: **4 victorias, 1 derrota y 11 empates**.

- `20264503`, `20264504` y `20264507`: ahorra dos movimientos en cada sala.
- `20264514`: llega en 22 movimientos donde corrected abandona tras 56.
- **`20264511`: nuevo fallo**, abandona tras 56 donde corrected llegaba en 31
  y scratch en 25: corrected ya era peor que scratch en esa sala.

No aumenta el número de metas: cambia cuál falla. No es una mejora uniforme
ni queda aprobada como reemplazo del candidato. Frente a scratch también
resulta 4/1/11; siguen siendo datos públicos ya usados para investigar.

### Sólo cobertura de acciones

Frente a corrected: **1 victoria, 0 derrotas y 15 empates**.
La ganancia de navegación está concentrada en `20264511`: pasa de 31 a
21 movimientos. En el fallo compartido `20264514` abandona tras 54 en vez
de 56; esos dos movimientos menos **no cuentan como victoria**.
Frente a scratch: 4 victorias, 2 derrotas y 10 empates.

## Coste y cobertura del entrenamiento

| Brazo | Movimientos A | Coste simulado | Características | Pares característica–acción probados | Características con una sola acción |
|---|---:|---:|---:|---:|---:|
| Corrected | 113 | 452 | 27 | 38 | 19 |
| Reward only | 111 | 444 | 27 | 41 | 16 |
| Coverage only | 159 | 636 | 32 | 59 | 16 |

Las tres escuelas llegan en sus 12 episodios. La cobertura adicional no es
gratis: **46 movimientos y 184 unidades simuladas más** que corrected.
Produce 33 propuestas de exploración. Los conteos se incrementan sólo tras
ejecuciones observadas y no se exportan al examen.

La escuela es on-policy: recompensa y exploración cambian decisiones y,
por tanto, datos posteriores. Es una prueba de un factor de configuración
por vez, no una comparación con cantidades de muestras idénticas ni una
prueba aislada del valor de cada muestra. No se alegan julios físicos.

## Verificación

Informe completo: `lab/transfer3/rehearsal-v3.json`. Incluye el hash del
informe v2, comprobación de sus fuentes por inventario guardado, protocolo,
hashes de fuentes/tests/diseño, geometrías, ledger, observaciones de escuela,
actualizaciones, conteos, políticas exportadas, exámenes y comparaciones.

Auditoría completa en un proceso nuevo, repitiendo las escuelas y las 64
misiones con consumidor aislado: `replay_valid=true`, exit 0. Hash canónico:
`e31770e7d900379863a2ee3eb7581b33813f10e9441a159930c2a703bc57ad00`.
No es un certificado de TRANSFER-3.

**59 tests pasan**, incluidos 13 nuevos. Comprueban la no duplicación de
evidencia y visitas, rechazo de capturas conflictivas, aceptación de nuevas
capturas, equivalencia de decisiones sin aprendizaje, recompensa de llegada
(no propagación de `terminal=True`, ausente en esta versión),
separación de factores, exploración condicionada a evidencia/reserva,
conteos de ejecuciones, clasificación de fallos y rechazo de alteraciones
del informe. La regresión incluye las versiones previas y COMPOSE v3/v4.

Reproducción desde `echoai/`, con permisos de namespaces para Bubblewrap:

```sh
PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rehearsal_v3 audit lab/transfer3/rehearsal-v3.json
PYTHONPATH=.. python3 -m unittest echoai.tests.test_transfer3_v3 echoai.tests.test_transfer3_v2 echoai.tests.test_transfer3 echoai.tests.test_transfer3_custody echoai.tests.test_compose1_v3 echoai.tests.test_compose1_v4 -q
```

## Conclusión

Reparación implementada y ambas pruebas ejecutadas por separado. La nueva
recompensa tiene un resultado mixto con un nuevo fallo; la cobertura mejora
un caso con mayor coste de escuela. **Ninguna queda promovida automáticamente**.
No se han modificado criterios, escogido nuevas salas tras ver resultados,
combinado intervenciones ni abierto una confirmación reservada.

Antes de cerrar TRANSFER-3 falta una ventaja robusta, con su coste incluido,
y un protocolo final justificado. C final sigue sin generarse; Nav aún no
necesita preparar secretos. ECHO-3 permanece en 13/15.
