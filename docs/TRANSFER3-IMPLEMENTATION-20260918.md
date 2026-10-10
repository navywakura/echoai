# TRANSFER-3 — implementación y resultados del 18 de septiembre de 2026

Registro de lo implementado, medido y **no** conseguido en esta etapa. Continúa
las reparaciones de [v5](TRANSFER3-REPAIR-V5.md).

**TRANSFER-3 sigue en rojo. No hay candidato. ECHO-3 permanece en 13/15.**
Nada de lo aquí descrito promueve un brazo, abre una confirmación reservada ni
genera B/C. Ninguna fuente congelada fue modificada: cada corrida comprueba el
inventario de v4 ruta a ruta antes de ejecutar y habría abortado.

## Encargo y alcance

El encargo fue intentar cerrar TRANSFER-3 en verde. No se cerró, y conviene
decir por qué antes de los detalles: el tercer bloqueo —custodia externa con
auditoría A→B→C— **no lo cierra código**. Exige un custodio fuera del
repositorio y secretos que este banco no debe conocer. Se dejó intacto.

El trabajo se concentró en el primer bloqueo: demostrar una ventaja real del
aprendizaje. Se pasó de «ningún candidato supera el cribado y no sabemos por
qué» a una causa localizada en una entrada concreta de la tabla, con tres
explicaciones alternativas descartadas con datos.

## Método

Cuatro experimentos. Cada uno con su contrato fijado **antes** de ejecutar, un
solo factor entre brazos, predicción registrada de antemano que ancla la
corrida, y criterio de cribado importado de `rehearsal_v4.screen` sin copiarlo
ni modificarlo. Todo el código es aditivo: módulos nuevos que reutilizan el
planificador, la Q, la escuela reparada y el consumidor enjaulado existentes.

En los cuatro, la predicción de réplica se cumplió exactamente: el brazo de
control reprodujo `corrected` de v4 byte a byte. Sin eso ninguna comparación
posterior habría sido legible.

## v6 — el cero de una acción no muestreada

**Contrato**: [TRANSFER3-V6-DESIGN.md](TRANSFER3-V6-DESIGN.md) ·
**Resultados**: [TRANSFER3-V6-RESULTS.md](TRANSFER3-V6-RESULTS.md)

Hipótesis: el cribado falla porque una acción sin muestra conserva Q=0 y, con
recompensa de deriva negativa, el desempate prefiere sistemáticamente lo que no
conoce. Intervención únicamente en la exportación: suelo por fila
`min(muestreadas) − 1`, recortado en −127. Una escuela, dos exportaciones.

| Brazo | Metas | W/L/T | Fallos nuevos | Ahorro conjunto | Coste total | Cribado |
|---|---:|---|---:|---:|---:|---|
| `scratch` | 62/64 | — | — | — | 1065 | — |
| `baseline` | 62/64 | 11/13/40 | 2 | −40 | 1258 | no |
| `pessimistic` | 60/64 | 8/10/46 | 2 | −18 | 1263 | no |

**Refutada como explicación suficiente.** El suelo hizo exactamente lo previsto
—9 salas mejor, 4 peor, +22 movimientos netos frente a `baseline`— y perdió dos
metas: ordenar lo desconocido al final suprime el desvío no explorado que era
el único camino donde no hay evidencia. Optimismo y pesimismo pierden por
motivos opuestos.

## v7 — la curva de presupuesto

**Contrato**: [TRANSFER3-V7-DESIGN.md](TRANSFER3-V7-DESIGN.md) ·
**Resultados**: [TRANSFER3-V7-RESULTS.md](TRANSFER3-V7-RESULTS.md)

| Presupuesto | Features | Pares muestreados | Posibles | Conflicto | `baseline` W/L | Coste total |
|---:|---:|---:|---:|---:|---|---:|
| 128 | 27 | 38 | 108 | 0 | 11/13 | 1258 |
| 256 | 27 | 38 | 108 | 0 | 11/13 | 1386 |
| 512 | 27 | 38 | 108 | 0 | 10/10 | 1640 |
| 1024 | 29 | 40 | 116 | 0 | 11/10 | 2152 |

**Ocho veces el presupuesto compra dos features y dos pares.** La escuela es
on-policy sobre cuatro salas fijas: a 1024 movimientos son 114 episodios que
recorren casi el mismo conjunto de estados que a 128. Los valores de Q siguen
moviéndose —de [−7, 25] a [−9, 36]— pero el **orden dentro de cada fila**, lo
único que lee el desempate, se estabiliza antes de los 128: los exámenes de 128
y 256 son idénticos misión a misión.

Cero pares en conflicto en los cuatro presupuestos. El medidor era interno a la
escuela; esa elección resultó ser el punto ciego, y v8 lo demostró.

## v8 — diversidad de salas a presupuesto fijo

**Contrato**: [TRANSFER3-V8-DESIGN.md](TRANSFER3-V8-DESIGN.md) ·
**Resultados**: [TRANSFER3-V8-RESULTS.md](TRANSFER3-V8-RESULTS.md)

Conjuntos anidados R4 ⊂ R8 ⊂ R12, presupuesto congelado en 128 movimientos.

| Salas | Features | Pares | `baseline` W/L/T | Fallos nuevos | Ahorro conjunto | Coste total |
|---:|---:|---:|---|---:|---:|---:|
| 4 | 27 | 38 | 11/13/40 | 2 | −40 | 1258 |
| 8 | 39 | 60 | **17**/14/33 | 2 | −14 | 1216 |
| 12 | 39 | 66 | **17**/16/31 | 2 | −12 | 1214 |

**La cobertura casi se duplica sin gastar un movimiento más.** Queda
confirmado que el techo lo ponía la distribución de datos y no el gasto. La
exportación pesimista, en cambio, empeora con la diversidad —de 2 a 4 fallos
nuevos— y queda descartada como dirección.

Ningún brazo pasa, y siempre por lo mismo: `new_failures = 2`.

## El hallazgo: los dos fallos son un solo valor aprendido

`scratch` falla en `20264674` y `20264680`. **Todo brazo entrenado falla en
`20264670` y `20264695`, con 4, 8 o 12 salas**, y recupera a cambio las dos de
scratch. El intercambio es exactamente 2 por 2 en los tres conjuntos.

Reproducidas paso a paso, las dos divergencias ocurren en **la misma feature,
código 504**:

| Sala | Divergencia | Posición | Dist. meta | `scratch` | Entrenado |
|---|---:|---|---:|---|---|
| `20264670` | paso 12 | (−2, −4, 0) | 6 | acción 1 → llega en 18 | acción 2 → abandona tras 54 |
| `20264695` | paso 14 | (−4, −4, 0) | 6 | acción 1 → llega en 20 | acción 2 → abandona tras 48 |

Fila Q de 504 con 12 salas: `[−3, 1, 3, 0]`. La acción 2 gana el desempate con
+3. `scratch` no tiene preferencia, cae en el orden de camino y acierta.

El código 504 significa: meta con **x menor** y **y mayor** que la posición, z
igual, acción 3 bloqueada, acciones 0–2 libres. Con `DIRECTIONS` planares
`[(+1,0), (−1,0), (0,+1), (0,−1)]`, **tanto la acción 1 como la 2 reducen la
distancia L1**: las dos son avances legítimos y las dos cobran +7 en la
escuela. La feature no puede decir cuál entra en un callejón, porque la pared
está a más de una celda y la máscara sólo ve el anillo inmediato.

La fila cambia con la diversidad —`[−3, 0, 1, 0]` con 4 y 8 salas— pero la
acción 2 gana en los tres casos. Por eso duplicar la cobertura no deshace los
fallos.

**Es aliasing, no cobertura**: el par está muestreado y el valor aprendido. Y
explica por qué el medidor de v7 marcó cero: dentro de la escuela, `(504,
acción 2)` siempre dio retornos consistentes porque allí era correcto. La
contradicción sólo existe fuera de la distribución de entrenamiento, y un
medidor calculado dentro de la escuela no puede verla por construcción.

## Descartado con datos, no con argumentos

1. **No es el convenio de signo.** v6: optimismo y pesimismo pierden por
   razones opuestas y ninguno pasa.
2. **No es el presupuesto.** v7: ocho veces más movimientos no mueven la
   cobertura ni el cribado, y alejan la amortización.
3. **No es contradicción interna de la representación.** v7: cero pares con
   retornos opuestos dentro de la escuela, en los cuatro presupuestos.
4. **No es sólo cobertura.** v8: la cobertura casi se duplica y los dos fallos
   persisten sin cambiar de sala.

## Lo entregado

Módulos nuevos, ninguno modifica fuentes congeladas:

| Fichero | Qué hace |
|---|---|
| `nexus0/transfer3/school_v6.py` | Escuela presupuestada sobre `repair_v5`; exportación con suelo como función pura de (payload, conteos) |
| `nexus0/transfer3/screen_v6.py` | Cribado v6 con criterio de v4 importado |
| `nexus0/transfer3/curve_v7.py` | Curva de presupuesto; medidores de cobertura y conflicto |
| `nexus0/transfer3/rooms_v8.py` | Diversidad de salas anidadas a presupuesto fijo |

Tests: `test_transfer3_v6.py` (20), `test_transfer3_v7.py` (16),
`test_transfer3_v8.py` (11). **Regresión TRANSFER-3: 130 tests, todos verdes.**

Artefactos, todos `isolated=true` salvo el segundo:

| Artefacto | Hash canónico | Auditable hoy |
|---|---|---|
| `lab/transfer3/screen-v6-isolated.json` | `3e02186bcd16ae6f640c0167cf0b5871b73b2f49ce7978bc033f0256de42e9f7` | no |
| `lab/transfer3/screen-v6.json` | `10e5854109db506580593dc87f9bf1e935d72d5414b7fd22fd1c1976efd71151` | no |
| `lab/transfer3/screen-v6-stable.json` | `f54c2f4d0b04c030f39a5815e3ba91c204d58db6bd4e67b4be079b595813cade` | **sí** |
| `lab/transfer3/curve-v7.json` | `072b69e1c1d58b70b2ec6a613bbf59eaa5122eceaffbf0e748cfd73aa8ccb38f` | no |
| `lab/transfer3/curve-v7-stable.json` | `ba071694d8fa6c53b3aebf1de9978cff99a2c16b76f249ffbdba623a38b20d5d` | **sí** |
| `lab/transfer3/rooms-v8.json` | `7019d0eb60eebae9fbdc42ca6ddc2da2c683f82f920917eb141317b999d67164` | **sí** |

Los tres auditables dan `replay_valid=true`, exit 0 y hash idéntico en proceso
nuevo. Suman ~214 MB en `lab/`.

## Defecto del arnés encontrado al auditar

`rehearsal.inventory()` fotografía **todo** el árbol `nexus0/**/*.py` en vez de
las dependencias de la corrida. Consecuencia: añadir cualquier módulo nuevo
invalida la reproducción de todos los informes anteriores aunque ninguna de sus
dependencias haya cambiado.

La primera auditoría de v7 falló exactamente por eso —`rooms_v8.py` se creó
mientras estaba en vuelo—, no por desacuerdo de resultados. Por eso existen
`screen-v6-stable.json` y `curve-v7-stable.json`: repiten v6 y v7 sobre el
árbol estable, con resultados idénticos, para que los tres puedan auditarse a
la vez.

No se corrige aquí: `inventory()` pertenece al inventario congelado de v2, v3 y
v4, y tocarla rompería esas auditorías. **El protocolo final debería fijar el
conjunto de dependencias de cada corrida en vez de fotografiar el árbol.**

## Coste incurrido

- **8 de las 42 formas canónicas públicas restantes**, declaradas en el
  contrato v8 antes de ejecutar: `20264706, 20264710, 20264717, 20264721,
  20264725, 20264727, 20264729, 20264735`. De 126 formas de la familia quedan
  **34**. Insuficientes para un examen prospectivo de 64 salas más una
  confirmación reservada.
- ~214 MB de artefactos JSON.

## No verificado

La suite completa del repositorio **no se pudo cerrar**: agota la memoria en
`tests/test_dynamic1.py`, séptimo fichero por orden, tanto en bloque como
ejecutando fichero a fichero. Los seis anteriores pasan limpios. Es anterior a
este trabajo y no lo toca —los añadidos son ficheros nuevos, y lo único
compartido, `inventory()`, sólo lo llaman módulos de TRANSFER-3, que pasan—
pero **no se declara verificada** y ningún documento de esta serie lo afirma.

## Reproducción

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_v6 tests.test_transfer3_v7 \
    tests.test_transfer3_v8 tests.test_transfer3_v5 tests.test_transfer3_v4 \
    tests.test_transfer3_v3 tests.test_transfer3_v2 tests.test_transfer3 \
    tests.test_transfer3_custody -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.screen_v6 audit lab/transfer3/screen-v6-stable.json
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.curve_v7  audit lab/transfer3/curve-v7-stable.json
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.rooms_v8  audit lab/transfer3/rooms-v8.json
```

`run` rechaza sobrescribir cualquier intento público. Ningún comando genera
salas nuevas de campaña ni abre nada reservado.

## Decisiones pendientes

1. **Cambio de representación.** El discriminador que falta es observable sin
   oráculo: longitud de tramo libre en cada dirección más allá del anillo
   inmediato, que el agente ya tiene en sus creencias (`free()` sobre celdas
   observadas). Desambiguaría la feature 504. **No se implementó**: cambia qué
   significa la política transferida y exige contrato aprobado.
2. **Amortización en el protocolo final.** `scratch` gasta 1065 movimientos y
   no entrena; un brazo con presupuesto B necesita examen por debajo de
   `1065 − B`. Con examen de 64 salas, **ampliar el presupuesto aleja el
   equilibrio**. Hay que declarar si la ventaja se mide contra el mismo examen
   o se amortiza sobre un despliegue mayor que el banco.
3. **Generador de geometrías.** Ahora es camino crítico por dos motivos
   independientes: hacen falta salas para B/C y hacen falta salas para que la
   escuela aprenda algo. Ampliar debería añadir topología —más de una pared,
   más de un hueco, callejones—, no rectángulos mayores: subir width y height
   multiplica la cardinalidad sin aumentar la independencia.

## Lo que no se tocó

Custodia externa, generador final, protocolo final y ventaja amortizada siguen
pendientes. No se encendió el córtex, no se importó navi7–9, no se usó MetaTF,
no se afirmaron julios y no hay placa. `transfer3_green=false` y
`campaign_C_opened=false` en todos los artefactos.
