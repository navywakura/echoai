# TRANSFER-3 v6 — el optimismo por cero no era la restricción activa

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Resultado negativo.**
Diseño fijado antes de ejecutar: [contrato v6](TRANSFER3-V6-DESIGN.md). No se
generó ni abrió B/C. Ninguna fuente congelada se modificó: los inventarios de
v1–v5 se comprueban ruta a ruta antes de cada corrida.

## Control de réplica: exacto

La predicción registrada se cumple. La escuela reparada de v5 —terminalidad
real, un `scan` por timestamp, asignación CAM comprobada, reserva por juez
común, bono de fallo −32— produce un payload **byte a byte idéntico** al
`corrected` de v4, y su cribado replica exactamente:

| | victorias | derrotas | empates | fallos nuevos | ahorro en éxito conjunto |
|---|---:|---:|---:|---:|---:|
| `baseline` v6 | 11 | 13 | 40 | 2 | −40 |
| `corrected` v4 | 11 | 13 | 40 | 2 | −40 |

El bono de fallo no disparó **ninguna vez**: las cuatro salas de escuela se
completan siempre. Hubo 13 actualizaciones terminales. Es decir, las
reparaciones de v5 son correctas y en estas salas no mueven nada, que es lo
que el contrato predijo. La corrida es válida.

## Resultado principal

| Brazo | Metas | Movimientos examen | W/L/T vs scratch | Fallos nuevos | Ahorro conjunto | Coste total | Cribado |
|---|---:|---:|---|---:|---:|---:|---|
| `scratch` | 62/64 | 1065 | — | — | — | 1065 | — |
| `baseline` | 62/64 | 1130 | 11/13/40 | 2 | −40 | 1258 | **no** |
| `pessimistic` | 60/64 | 1135 | 8/10/46 | 2 | −18 | 1263 | **no** |

Cero colisiones, violaciones de reserva, hechos falsos, escrituras imaginadas
y modelos alterados en las 192 misiones. Criterio importado de
`rehearsal_v4.screen` sin modificar.

**La hipótesis v6 queda refutada como explicación suficiente.** Tratar el cero
de una acción no muestreada como «desconocido» y no como «valor aprendido» no
convierte el brazo en candidato.

## Lo que sí hizo el suelo, y lo que costó

La intervención funcionó exactamente en la dirección prevista, y falló por el
lado contrario:

- Entre salas con éxito en ambos brazos, `pessimistic` mejora a `baseline` en
  **9 salas, empeora en 4, neto +22 movimientos**. El déficit de eficiencia
  frente a scratch se reduce de −40 a −18.
- Pero pierde **dos metas**. `baseline` falla en `20264670` y `20264695` y a
  cambio recupera las dos que scratch no alcanza (`20264674`, `20264680`).
  `pessimistic` falla en las cuatro.

El mecanismo es directo: ordenar lo desconocido por debajo de lo conocido
compra eficiencia allí donde hay evidencia y suprime el desvío no explorado
que era el único camino a la meta donde no la hay. En `20264670` scratch llega
en 18 movimientos; `pessimistic` abandona en casa tras 54.

Optimismo y pesimismo pierden por motivos opuestos: uno divaga hacia lo que no
conoce, el otro se niega a explorar cuando debe. Con 27 features, 38 pares
muestreados de 108 posibles y 128 movimientos, **la restricción activa es la
cobertura, no el convenio de signo**. Ninguna regla de desempate sobre una
tabla tan poco muestreada produce un candidato.

## Una restricción estructural del criterio

Descontando el entrenamiento, scratch gasta 1065 movimientos y no entrena. Un
brazo entrenado con presupuesto B necesita un examen por debajo de `1065 − B`
para amortizar. A B=128 eso exige ser un 12 % mejor que scratch; a B=512,
prácticamente la mitad. **Ampliar el presupuesto de escuela aleja la
amortización en vez de acercarla**, mientras el examen siga siendo 64 salas.

Esto no es un defecto del código: es una decisión de protocolo. El protocolo
final debe declarar si la ventaja se mide amortizada contra el mismo examen o
si el coste de escuela se amortiza sobre un despliegue mayor que el banco. Es
tuya, no del banco.

## Verificación

Dos intentos públicos conservados, ambos con resultados idénticos —el jaulado
no cambia la conducta:

| Artefacto | `isolated` | Hash canónico |
|---|---|---|
| `lab/transfer3/screen-v6-isolated.json` | sí | `3e02186bcd16ae6f640c0167cf0b5871b73b2f49ce7978bc033f0256de42e9f7` |
| `lab/transfer3/screen-v6.json` | no | `10e5854109db506580593dc87f9bf1e935d72d5414b7fd22fd1c1976efd71151` |
| `lab/transfer3/screen-v6-stable.json` | sí | `f54c2f4d0b04c030f39a5815e3ba91c204d58db6bd4e67b4be079b595813cade` |

El artefacto aislado se auditó en proceso nuevo al crearse: `replay_valid=true`,
exit 0, mismo hash. Esa auditoría **ya no se puede repetir**: `inventory()`
fotografía todo el árbol `nexus0/**/*.py`, así que los módulos v7 y v8 añadidos
después cambian el manifiesto aunque ninguna dependencia de v6 se haya tocado.
Ver el análisis en [resultados v8](TRANSFER3-V8-RESULTS.md). `screen-v6-stable.json`
repite la corrida sobre el árbol estable, con resultados idénticos, y es el
artefacto auditable hoy.

20 tests v6 nuevos pasan; la regresión de TRANSFER-3 queda en 103 tests al
cerrar v6, y en 130 al cerrar v8.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_v6 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.screen_v6 audit lab/transfer3/screen-v6-isolated.json
```

## Regla de parada, aplicada

El contrato decía: si `pessimistic` no pasa, la explicación restante es
aliasing de representación y el siguiente paso es un feature observable, no
más episodios con las mismas features. Los datos matizan esa regla. Antes de
tocar la representación hay que resolver que **enriquecer el feature empeora
la cobertura a presupuesto fijo**: más bits reparten los mismos 128 movimientos
entre más filas. Los dos problemas que v5 midió por separado —244/372
decisiones sobre acciones sin muestra y 14 pares con órdenes opuestos— tiran
en direcciones contrarias bajo un único presupuesto.

El siguiente experimento debe medir esa curva, no elegir un lado por
argumento: cobertura y aliasing en función del presupuesto, con el coste
contado. Hasta tener esa curva no hay base para proponer un feature nuevo ni
para fijar el tamaño de muestra del protocolo final.

TRANSFER-3 sigue en rojo. No hay candidato. ECHO-3 permanece en 13/15.
