# TRANSFER-3 v8 — la diversidad de salas sí mueve la cobertura, y no basta

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Sin candidato.**
Diseño fijado antes de ejecutar: [contrato v8](TRANSFER3-V8-DESIGN.md). No se
generó ni abrió B/C. Inventario congelado de v4 comprobado ruta a ruta.

## Predicciones 1 y 2: confirmadas

El brazo de 4 salas replica exactamente `baseline` de v6 y `corrected` de v4
(11/13/40, 2 fallos nuevos, −40). La corrida es válida.

A **presupuesto constante de 128 movimientos**, cambiar sólo el número de
salas distintas:

| Salas | Features | Pares muestreados | Pares posibles | Pares en conflicto |
|---:|---:|---:|---:|---:|
| 4 | 27 | 38 | 108 | 0 |
| 8 | 39 | 60 | 156 | 0 |
| 12 | 39 | 66 | 156 | 0 |

**La cobertura casi se duplica sin gastar un movimiento más.** V7 había
mostrado que ocho veces el presupuesto sobre cuatro salas compra dos pares;
aquí, triplicar las salas con el mismo presupuesto compra veintiocho. Queda
confirmado que el techo lo ponía la distribución de datos, no el gasto. El
conflicto de retornos sigue en cero en los tres conjuntos.

## Predicción 3: falla, y falla por una sola razón

| Salas | Brazo | Metas | Movimientos examen | W/L/T | Fallos nuevos | Ahorro conjunto | Coste total | Cribado |
|---:|---|---:|---:|---|---:|---:|---:|---|
| — | `scratch` | 62/64 | 1065 | — | — | — | 1065 | — |
| 4 | `baseline` | 62/64 | 1130 | 11/13/40 | 2 | −40 | 1258 | no |
| 8 | `baseline` | 62/64 | 1088 | **17/14/33** | 2 | −14 | 1216 | no |
| 12 | `baseline` | 62/64 | 1086 | **17/16/31** | 2 | −12 | 1214 | no |
| 4 | `pessimistic` | 60/64 | 1135 | 8/10/46 | 2 | −18 | 1263 | no |
| 8 | `pessimistic` | 61/64 | 1116 | 13/11/40 | 3 | −20 | 1244 | no |
| 12 | `pessimistic` | 60/64 | 1180 | 11/15/38 | 4 | −56 | 1308 | no |

Cero colisiones, violaciones de reserva, hechos falsos, escrituras imaginadas
y modelos alterados en las 448 misiones.

`baseline` mejora de forma clara y monótona con la diversidad: de 11 victorias
a 17, y el déficit de eficiencia se reduce de −40 a −12. Pero **ningún brazo
pasa**, y siempre por el mismo motivo: `new_failures = 2`.

## Los dos fallos son siempre los mismos

`scratch` falla en `20264674` y `20264680`. **Todo brazo entrenado con
exportación estándar falla en `20264670` y `20264695`, con 4, 8 o 12 salas**, y
recupera a cambio las dos de scratch. El intercambio es exactamente 2 por 2 en
los tres conjuntos: más cobertura no lo deshace.

No es ruido de muestreo: es un modo de fallo reproducible que el entrenamiento
introduce y la diversidad no corrige. El criterio de v4 rechaza cualquier
brazo con un fallo nuevo, así que **esas dos salas son, hoy, el único
obstáculo entre el mejor brazo y el cribado**. Antes de tocar nada más hay que
saber qué ocurre en ellas.

La exportación pesimista empeora con la diversidad —de 2 a 4 fallos nuevos—,
como predijo el mecanismo de v6: ordenar lo desconocido al final suprime el
desvío no explorado, y con más features hay más sitios donde eso muerde.
Queda descartada como dirección.

## Los dos fallos son **un solo valor aprendido**

Reproducidas las dos salas paso a paso contra `scratch`, el mecanismo es
idéntico en ambas y se localiza en una entrada de la tabla:

| Sala | Divergencia | Posición | Distancia a meta | `scratch` | Entrenado |
|---|---:|---|---:|---|---|
| `20264670` | paso 12 | (−2, −4, 0) | 6 | acción 1 → llega en 18 | acción 2 → abandona tras 54 |
| `20264695` | paso 14 | (−4, −4, 0) | 6 | acción 1 → llega en 20 | acción 2 → abandona tras 48 |

Las dos divergencias ocurren en **la misma feature, el código 504**, cuya fila
Q es `[−3, 1, 3, 0]`: la acción 2 gana el desempate con +3. `scratch` no tiene
preferencia y cae en el orden de camino, que aquí acierta.

El código 504 significa: meta con **x menor** y **y mayor** que la posición, z
igual, acción 3 bloqueada, acciones 0–2 libres. Con `DIRECTIONS` planares
`[(+1,0),(−1,0),(0,+1),(0,−1)]`, tanto la acción 1 como la 2 **reducen la
distancia L1**: las dos son avances legítimos y las dos cobran +7 en la
escuela. La feature no puede decir cuál de las dos entra en un callejón,
porque la pared está a más de una celda y la máscara sólo ve el anillo
inmediato.

La fila cambia con la diversidad —`[−3, 0, 1, 0]` con 4 y 8 salas,
`[−3, 1, 3, 0]` con 12— pero la acción 2 gana en los tres casos, y por eso los
dos fallos sobreviven a duplicar la cobertura.

**Esto es aliasing, no cobertura.** El par está muestreado; el valor está
aprendido; el problema es que la representación mete en la misma celda dos
situaciones con respuestas opuestas. También explica por qué el medidor de
conflicto de v7 marcó cero: dentro de la escuela el par `(504, acción 2)`
siempre dio retornos consistentes, porque allí era correcto. La contradicción
sólo aparece fuera de la distribución de entrenamiento, y un medidor calculado
dentro de la escuela no puede verla por construcción.

El discriminador que falta es observable sin oráculo: la longitud de tramo
libre en cada dirección más allá del anillo inmediato, que el agente ya tiene
en sus creencias (`free()` sobre celdas observadas). Es un cambio de
representación, no un ajuste, y no se implementa aquí sin contrato aprobado.

## Coste del banco público

Esta corrida consume **8 de las 42 formas canónicas** que quedaban en la
familia de una pared con un hueco; quedan 34. Las salas nuevas son
`20264706, 20264710, 20264717, 20264721, 20264725, 20264727, 20264729, 20264735`.
Se declaró en el contrato antes de ejecutar.

Con 34 formas restantes no hay margen para un examen prospectivo de 64 salas
más una confirmación reservada. **El generador ampliado es el camino crítico**,
y ahora lo es por dos motivos independientes: hacen falta salas para B/C y
hacen falta salas para que la escuela aprenda algo.

## Verificación

Artefacto: `lab/transfer3/rooms-v8.json`, `isolated=true`, hash canónico
`7019d0eb60eebae9fbdc42ca6ddc2da2c683f82f920917eb141317b999d67164`.
Auditoría completa en proceso nuevo: `replay_valid=true`, exit 0, mismo hash.
11 tests v8 nuevos; regresión TRANSFER-3 en **130 tests**.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_v8 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rooms_v8 audit lab/transfer3/rooms-v8.json
```

### Un defecto del arnés, encontrado al auditar

`rehearsal.inventory()` hashea **todo** el árbol `nexus0/**/*.py`, no las
dependencias de la corrida. Consecuencia: añadir cualquier módulo nuevo
invalida la reproducción de todos los informes anteriores, aunque ninguna de
sus dependencias haya cambiado. La primera auditoría de v7 falló exactamente
por eso —se creó `rooms_v8.py` mientras estaba en vuelo—, y no por un
desacuerdo de resultados.

No se corrige aquí: `inventory()` pertenece al inventario congelado de v2, v3
y v4, y tocarla rompería esas auditorías. Queda anotado para el protocolo
final, que debería fijar el conjunto de dependencias de cada corrida en vez de
fotografiar el árbol. Los artefactos `screen-v6-stable.json` y
`curve-v7-stable.json` regeneran v6 y v7 sobre el árbol estable para que los
tres puedan auditarse a la vez.

Seis cribados más contra el mismo banco público no son pruebas independientes.
Ninguno pasó, así que no hay nada que confirmar prospectivamente.

TRANSFER-3 sigue en rojo. ECHO-3 permanece en 13/15.
