# TRANSFER-3 v7 — la escuela no ve lo suficiente, y más presupuesto no lo arregla

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Resultado negativo.**
Diseño fijado antes de ejecutar: [contrato v7](TRANSFER3-V7-DESIGN.md). No se
generó ni abrió B/C. Inventario congelado de v4 comprobado ruta a ruta.

## La curva

Cuatro presupuestos de escuela, misma escuela reparada, mismas cuatro salas,
mismas 64 salas de examen, criterio de v4 sin modificar.

| Presupuesto | Features | Pares muestreados | Pares posibles | Features con una sola acción | Pares en conflicto |
|---:|---:|---:|---:|---:|---:|
| 128 | 27 | 38 | 108 | 19 | **0** |
| 256 | 27 | 38 | 108 | 19 | **0** |
| 512 | 27 | 38 | 108 | 19 | **0** |
| 1024 | 29 | 40 | 116 | 21 | **0** |

**Ocho veces el presupuesto compra dos features y dos pares.** La cobertura se
satura en el primer presupuesto: 27 de las 144 codificaciones planares
utilizables, 38 de 108 pares. El bono de fallo no disparó en ninguna corrida,
así que ningún retorno quedó desplazado y el recuento de conflictos es limpio.

## Las dos predicciones registradas fallan

| Predicción | Resultado |
|---|---|
| Si manda la cobertura, crece con el presupuesto y el cribado cruza | La cobertura **no crece**; el cribado no cruza |
| Si manda el conflicto, los pares contradictorios crecen | Hay **cero** en los cuatro presupuestos |

| Presupuesto | `baseline` W/L | Fallos nuevos | `pessimistic` W/L | Fallos nuevos | Coste total mejor brazo | Cribado |
|---:|---|---:|---|---:|---:|---|
| 128 | 11/13 | 2 | 8/10 | 2 | 1258 | no |
| 256 | 11/13 | 2 | 8/10 | 2 | 1386 | no |
| 512 | 10/10 | 3 | 7/8 | 2 | 1633 | no |
| 1024 | 11/10 | 3 | 8/8 | 2 | 2139 | no |

`scratch` gasta 1065 movimientos y no entrena. Ningún brazo pasa a ningún
presupuesto. El coste total sólo se aleja.

## Por qué se satura

La escuela es **on-policy sobre cuatro salas fijas**. El agente sigue su propio
plan codicioso, así que vuelve a los mismos estados y repite las mismas
acciones: a 128 movimientos son 14 episodios, a 1024 son 114 episodios que
recorren casi exactamente el mismo conjunto. Las 70 parejas no muestreadas no
son difíciles de aprender: son **inalcanzables por este procedimiento de
recogida de datos**, y repetirlo más veces no las alcanza.

La Q sí sigue cambiando —el rango de valores pasa de [−7, 25] a [−9, 36]—
pero el **orden dentro de cada fila**, que es lo único que lee el desempate,
se estabiliza antes de los 128 movimientos: los exámenes de 128 y 256 son
idénticos misión a misión. La tabla converge a una preferencia estable que
resulta ser peor que no tener ninguna.

## Qué queda descartado

Tres explicaciones quedan fuera con datos, no por argumento:

1. **No es el convenio de signo.** V6 lo midió: optimismo y pesimismo pierden
   por razones opuestas y ninguno pasa.
2. **No es el presupuesto.** Ocho veces más movimientos no mueven la cobertura
   ni el cribado, y empeoran la amortización.
3. **No es contradicción interna de la representación.** Cero pares reciben
   retornos opuestos en los cuatro presupuestos: sobre lo que la escuela ha
   visto, la feature sí determina la consecuencia.

Matiz importante: esto **no** contradice los 14 pares con órdenes opuestos que
midió v5. Aquel recuento es sobre qué acción es *mejor* según distancia local
en estados distintos con la misma feature; éste es sobre si una misma acción
produce un retorno *consistente*. Son dos preguntas distintas y ambas medidas
siguen en pie.

## Qué queda

Lo que falla es la **distribución de datos**, no la tabla, ni la recompensa, ni
el desempate, ni el presupuesto. Cuatro salas on-policy cubren el 19 % del
espacio de features utilizable y el 35 % de los pares, y ese techo es
estructural del procedimiento de recogida.

Eso convierte el punto 2 del plan —ampliar las geometrías— en un prerrequisito
de aprender algo, no sólo en una cuestión de tener salas independientes para
B/C. Con 126 formas canónicas en la familia actual y 84 ya gastadas en público,
**el generador nuevo es ahora el camino crítico**, y hay que decidir además
cómo se recogen los datos: cuatro salas recorridas con la política propia no
producen un conjunto de entrenamiento, por mucho presupuesto que se les dé.

## Verificación

Artefacto: `lab/transfer3/curve-v7.json`, `isolated=true`, hash canónico
`072b69e1c1d58b70b2ec6a613bbf59eaa5122eceaffbf0e748cfd73aa8ccb38f`.

Su auditoría **falló**, y no por desacuerdo de resultados: `inventory()`
fotografía todo el árbol `nexus0/**/*.py`, y `rooms_v8.py` se creó mientras la
auditoría estaba en vuelo, así que el manifiesto reconstruido no coincide con
el guardado. El defecto del arnés se analiza en
[resultados v8](TRANSFER3-V8-RESULTS.md). `lab/transfer3/curve-v7-stable.json`
repite la curva sobre el árbol estable, con resultados idénticos, y es el
artefacto auditable: hash
`ba071694d8fa6c53b3aebf1de9978cff99a2c16b76f249ffbdba623a38b20d5d`,
`replay_valid=true`, exit 0.

16 tests v7 nuevos; regresión TRANSFER-3 en 119 tests al cerrar v7, y en 130
al cerrar v8.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_v7 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.curve_v7 audit lab/transfer3/curve-v7-stable.json
```

Ocho cribados contra el mismo banco público no son ocho pruebas
independientes; se declaró en el contrato y se repite aquí. Ninguno pasó, así
que no hay nada que confirmar prospectivamente.

TRANSFER-3 sigue en rojo. No hay candidato. ECHO-3 permanece en 13/15.
