# TRANSFER-3 Plan A2 — confirmación prospectiva fallida; Plan A cerrado

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Confirmación en rojo.**
Contrato: [enmienda 3](TRANSFER3-PLAN-A2-DESIGN.md), fijado antes de ejecutar.
Una sola corrida, no repetida. No se generó ni abrió B/C.

## Veredicto

| Criterio | | Valor |
|---|---|---|
| Restricciones duras | **no** | 72 violaciones de reserva del candidato (nominal 114) |
| `new_failures == 0` | **no** | 5 nuevos, 16 recuperados |
| Ahorra energía en éxitos conjuntos | **no** | **−80** |
| Amortiza escuela + examen | sí | 15 344 < 16 584 |
| Control negativo limpio | sí | idéntico al nominal |
| Signo de una cola α ≤ 1/240 | **no** | p = 0,34 · W/L 29/25 |

`plan_a2_confirmation_pass = false`. **El candidato no queda confirmado.**

## Números

128 salas de examen nuevas de dos paredes, enjauladas, aprendizaje congelado.

| Condición | Brazo | Metas | Energía | Giros | Viol. reserva |
|---|---|---:|---:|---:|---:|
| primaria (giro 4) | nominal | 92/128 | 16 584 | 1179 | 114 |
| primaria (giro 4) | candidato | **103/128** | **15 264** | **797** | 72 |
| control negativo (giro 0) | nominal | 101/128 | 13 116 | 1360 | 0 |
| control negativo (giro 0) | candidato | 101/128 | 13 116 | 1360 | 0 |

Escuela: 16 movimientos, 80 unidades, calibración aprendida exacta (giro 4).
Cero colisiones, hechos falsos y escrituras imaginadas; calibración sin cambios
en las 512 misiones.

## El control negativo es perfecto, y eso es lo que más vale del informe

Con giro 0 no hay nada que aprender, y el candidato es **idéntico al nominal
hasta la unidad**: 13 116 y 13 116 de energía, 1360 giros ambos, 0 victorias,
0 derrotas, 128 empates.

Importa más de lo que parece. Al elegir una topología de dos paredes **después**
de saber que el candidato era de giro, introduje un riesgo real de escoger un
generador que lo favoreciera. El control negativo era la defensa declarada
contra eso, y sale limpio: el aparato no fabrica ventaja donde no hay nada que
aprender.

## La tensión, dicha sin usarla para rescatar nada

El candidato alcanza **once metas netas más** (103 frente a 92), gasta menos
energía total (15 264 frente a 16 584), da un tercio menos de giros y comete
menos violaciones de reserva. Y aun así **falla**.

La razón es que su ventaja vive casi toda en salas donde el nominal fracasa: 16
recuperadas frente a 5 perdidas. Entre las **87 salas que ambos completan**, el
resultado es ruido —29/25, ahorro total −80, mediana 0, rango de −60 a +76—, y
el criterio primario que registré de antemano mide exactamente ese subconjunto.

**No se reinterpreta.** Medir la mejora en metas es una hipótesis distinta y
exigiría su propia confirmación prospectiva sobre salas frescas, con el
criterio fijado antes de mirarlas. Cambiar el criterio ahora, después de ver el
examen, invalidaría la confirmación entera y es exactamente lo que el contrato
prohíbe. Queda anotado como hipótesis candidata, no como resultado.

## El gate de reserva está fuera de envolvente, y se anunció antes

La constante de reserva es 4 —la histórica, idéntica en ambos brazos—, pero el
coste real con giro 4 llega a 8 por movimiento. En salas de dos paredes, más
largas que las históricas, eso rompe: **14 de 128 salas** acumulan alguna
violación con el nominal y **11 de 128** con el candidato.

Es una limitación del arnés, no del aprendizaje: afecta a los dos brazos, el
candidato tiene *menos* violaciones, y el riesgo se declaró explícitamente antes
de ejecutar. Pero el criterio 1 exige cero y no se relaja.

## Un defecto de aislamiento de A1, corregido y verificado

A1 no era enjaulable: `planner_a1` importaba de `body_a1`, que **contiene el
simulador `CostSpace`**. Montar el planificador habría montado el mundo.

A2 separa el vocabulario de costes en `costs_a2`, que no conoce mundos. La jaula
monta 17 módulos, sólo tres de `transfer3`, y el transporte se niega a arrancar
si aparece cualquier simulador en el árbol montado. Una prueba recorre el grafo
de importación **por AST** —no por grep sobre el texto, que daba un falso
positivo con el propio docstring— y comprueba que el cierre transitivo del
agente es exactamente `{planner_a2, costs_a2}`.

## Generador ampliado

Dos paredes con un hueco cada una, misma ontología. Medido antes de usarlo:
**11 638 formas canónicas** bajo traslación y D4, **solapamiento cero** con las
92 formas públicas gastadas. Toda sala es estructuralmente nueva por
construcción. El filtro de viabilidad es independiente del brazo y cada rechazo
queda en el ledger. Distancia oráculo del examen: 8 / 15 / 25.

Esto resuelve el cuello que arrastraba la serie desde v8 —quedaban 34 formas—,
y sigue disponible para lo que venga.

## Razonamiento auditable

- **Hipótesis.** El candidato `turn_only`, congelado tras A1 v2, baja la energía
  de misión en geometrías nuevas frente al mismo agente con prior nominal.
- **Evidencia.** Falla el criterio primario: entre éxitos conjuntos el ahorro es
  −80 con p = 0,34. Gana en metas, giros y energía total, que no eran el
  criterio.
- **Explicación rival 1.** Que el generador favorezca al candidato. **Descartada
  por el control negativo**, idéntico hasta la unidad.
- **Explicación rival 2.** Que las violaciones de reserva expliquen el fallo del
  criterio primario. **Descartada parcialmente**: el candidato tiene menos
  violaciones que el nominal, así que no puede estar penalizándole en energía;
  pero sí explican por sí solas el fallo del criterio 1.
- **Autorrevisión.** Escogí la topología sabiendo la forma del candidato: riesgo
  real de selección, cubierto por el control negativo declarado de antemano. El
  gate de reserva quedó corto y lo anuncié, pero no lo corregí antes de
  ejecutar; hacerlo ahora sería mover el listón después del resultado.
- **Actualización.** Abandono la hipótesis de que la calibración de coste baja la
  energía entre misiones comparables. Lo que sobrevive, sin confirmar, es que
  reduce giros y **convierte fracasos en llegadas**.
- **Decisión.** Regla de parada aplicada: una sola corrida, sin repetir.
  **Plan A queda cerrado.** Lo siguiente es Plan B —calibración del modelo de
  ejecución—, con contrato propio.

## Verificación

Artefacto: `lab/transfer3/plan-a2-confirmation.json`, hash canónico
`cd87bd6c481cdba9c733d88349af68bbac6cc71c021d40c70ac3a65c1317e4c5`.
Auditoría completa en proceso nuevo, repitiendo las 512 misiones enjauladas:
`replay_valid=true`, exit 0, mismo hash. 21 tests A2 nuevos, todos en verde.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_a2 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.confirm_a2 audit lab/transfer3/plan-a2-confirmation.json
```

TRANSFER-3 sigue en rojo. No hay candidato confirmado. Custodia externa intacta,
sin secretos pedidos. ECHO-3 permanece en 13/15.
