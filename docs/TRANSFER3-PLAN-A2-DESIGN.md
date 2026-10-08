# TRANSFER-3 Plan A2 — enmienda 3: generador ampliado y confirmación prospectiva

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Contrato fijado
**antes** de ejecutar nada. Enmienda 3 sobre
[A1](TRANSFER3-PLAN-A1-DESIGN.md) y [A1 v2](TRANSFER3-PLAN-A1-V2-DESIGN.md), que
quedan congelados. No genera ni abre B/C, no pide secretos y **no puede poner
`transfer3_green=true`**: esto es el nivel 2 del contrato —confirmación pública
prospectiva—, no la campaña sellada.

## Qué se ha cerrado antes de llegar aquí

A1 v2 midió, con controles no degenerados, que el término de **giro** transfiere
y el de **base** perjudica a un planificador de horizonte acotado, con un
diagnóstico monótono en la asimetría (+130 / +12 / −950). De ahí sale un
candidato distinto del probado, que **no se midió** para no seleccionar sobre
datos usados. Aquí se congela y se confirma.

## Generador ampliado

Misma ontología: salas extruidas planas y estáticas, celdas unitarias, inicio en
el origen, una estación, PRNG de geometría independiente de toda política. Lo
nuevo es una **segunda pared con su propio hueco**.

Medido antes de usarlo, sobre anchos 7–13 y alturas 3–6:

| | |
|---|---:|
| Formas canónicas de dos paredes (traslación y D4) | **11 638** |
| Solapamiento con las 92 formas públicas ya gastadas | **0** |
| Muestra de 400: viables / sin ruta / fuera de capacidad | 392 / 0 / 0 |
| Distancia oráculo mínima / mediana / máxima | 6 / 17 / 28 |

Toda sala A2 es **estructuralmente nueva por construcción**, no sólo no vista.
La exclusión frente a las 92 gastadas se aplica igualmente de forma explícita y
queda en el ledger, junto con cada rechazo y su motivo.

La topología se escogió porque la ontología la admite y porque una pared con un
hueco había agotado su familia —quedaban 34 formas—, no para favorecer a ningún
candidato. Contra ese riesgo, la confirmación lleva un **control negativo** con
giro 0: si el generador favoreciera espuriamente al candidato, ese control lo
enseñaría.

**Filtro de viabilidad, independiente del brazo:** alcanzable, dominio ≤ 256
celdas y `240 ≥ 2·d·4 + 10`. No depende de ninguna calibración y se aplica igual
a todos los brazos.

## Candidato congelado

**`turn_only`: se aprende el término de giro y la base se deja en el prior
nominal.** Cinco enteros, sin mapa, sin geometría, sin Q. Su forma queda fijada
en este contrato antes de ejecutar; no se elige después de ver ningún examen.

## Aislamiento real, y un defecto de A1 corregido

A1 no podía enjaularse: `planner_a1` importaba de `body_a1`, que **contiene el
simulador `CostSpace`**, así que montar el planificador habría montado el mundo.
No es un defecto de estilo sino de aislamiento.

A2 separa el vocabulario de costes en `costs_a2`, que no sabe nada de mundos. La
jaula monta 17 módulos, de los cuales sólo tres son de `transfer3`
—`__init__`, `costs_a2`, `planner_a2`—, y el transporte **rechaza arrancar** si
`space_a2`, `body_a1`, `rehearsal_v2` o cualquier `space.py` aparecen en el
árbol montado. Una prueba recorre lo montado en vez de fiarse de esta frase.

El examen corre bajo bubblewrap sin red, PID, IPC ni UTS propios, con el
consumidor como pid 1 y montaje de sólo lectura. La calibración entra congelada
y se vuelve a leer al terminar cada misión para comprobar que no cambió.

## Diseño

| | |
|---|---|
| Salas de escuela | 8, semilla `20264801`, disjuntas de todo lo gastado |
| Salas de examen | **128**, semilla `20265001`, disjuntas de lo gastado **y** de la escuela |
| Presupuesto de escuela | 16 movimientos ejecutados, como en A1 |
| Condición primaria | base (4,4,4,4), giro 4 |
| Control negativo | base (4,4,4,4), **giro 0** |
| Brazos | `nominal` y `candidate`; mismo ejecutable, sensores, planificador y gates |
| Reserva | constante 4, idéntica en ambos brazos |
| Coste primario | energía simulada en éxitos conjuntos |
| Examen | enjaulado, aprendizaje congelado |

## Criterio de paso

`plan_a2_confirmation_pass` exige **todas**:

1. cero colisiones, violaciones de reserva, hechos falsos, escrituras imaginadas
   y calibración alterada en el examen;
2. `new_failures == 0` frente a `nominal`;
3. energía en éxitos conjuntos estrictamente menor que `nominal`;
4. energía de escuela + el mismo bloque de examen menor que la de `nominal`;
5. **control negativo limpio**: con giro 0 el candidato no debe ahorrar nada;
6. signo de una cola con **α ≤ 1/240**.

Sobre el punto 6: con un único criterio primario, 1/60 —el estándar del repo—
sería defendible y no haría falta corrección por multiplicidad. **Se mantiene
1/240**, el umbral de A1 v2, para que el nivel de evidencia no baje nunca entre
enmiendas. Si el efecto es real con 128 salas, lo cruzará de sobra.

El punto 5 es una regla de invalidación, no un segundo candidato: **una ganancia
bajo giro 0 anula la corrida entera**, gane lo que gane la condición primaria.

## Qué seguiría sin estar demostrado si pasa

Aprobar esto es **nivel 2**: candidato confirmado prospectivamente. No es la
campaña A→B→C, no acredita custodia externa y no autoriza `transfer3_green`.
Siguen fuera de alcance el hardware, HIL, vuelo real y DRONE-3, y sigue siendo
energía simulada, nunca julios físicos.

## Regla de parada

Una sola corrida. No se repite la confirmación hasta que salga favorable: si
falla, el fallo se publica y se pasa a Plan B, y cualquier intento posterior
exige protocolo independiente y registro de éste. No se depura sobre estas
salas: si se usaran para depurar, dejarían de ser confirmación.
