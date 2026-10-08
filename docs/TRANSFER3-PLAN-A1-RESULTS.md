# TRANSFER-3 Plan A1 — la calibración se aprende exacta; la ventaja no generaliza

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Cribado en rojo.**
Contrato: [Plan A1](TRANSFER3-PLAN-A1-DESIGN.md), fijado antes de implementar.
No se generó ni abrió B/C. Software y simulación: nada aquí acredita hardware,
HIL, vuelo real ni DRONE-3.

## Qué se probó

Familia de costes declarada `base[a] + giro·[cambio de rumbo]`, con el término
de giro elegido porque un coste direccional puro es **conservativo** y no
distingue rutas —medido antes de implementar: dispersión 0 entre rutas de
longitud mínima en las 64 salas, incluso con asimetría (2,6,3,5)—. La
calibración se estima sólo de la energía observada entre tramas, se congela y
entra **directamente en la valoración del plan**, no en un tercer desempate.

Cuatro campañas declaradas de antemano, 64 salas de examen, escuela de 16
movimientos justificada por identificabilidad.

## La calibración se aprende exacta y barata

| Condición | Verdad | Aprendido | Error absoluto | Escuela |
|---|---|---|---:|---|
| `flat` | base 4,4,4,4 · giro 0 | idéntico | **0** | 16 mov · 64 u |
| `turn4` | base 4,4,4,4 · giro 4 | idéntico | **0** | 16 mov · 84 u |
| `turn8` | base 4,4,4,4 · giro 8 | idéntico | **0** | 16 mov · 104 u |
| `skew_turn6` | base 3,5,4,4 · giro 6 | idéntico | **0** | 16 mov · 90 u |

Identificabilidad demostrada: 16 movimientos bastan. Cobertura real publicada:
rectas `[4,1,1,5]`, giros `[2,1,0,2]` — la acción 2 nunca se observa girando, y
aun así el término de giro se identifica porque es compartido.

## Resultado por condición

| Condición | Brazo | Metas | Energía examen | Giros | Violaciones reserva | Fallos nuevos | Ahorro conjunto | Amortiza | p (una cola) |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| `flat` | nominal | 61/64 | 4124 | 408 | 0 | — | — | — | — |
| `flat` | learned | 61/64 | 4124 | 408 | 0 | 0 | **0** | no | 1.0 |
| `turn4` | nominal | 59/64 | 5448 | 383 | 0 | — | — | — | — |
| `turn4` | learned | **62/64** | **4932** | **257** | 0 | **0** | **+152** | **sí** | **0.0098** |
| `turn8` | nominal | 55/64 | 6812 | 371 | 32 | — | — | — | — |
| `turn8` | learned | 59/64 | 6072 | 264 | 21 | 3 | +128 | sí | 0.0083 |
| `skew_turn6` | nominal | 57/64 | 6213 | 380 | 38 | — | — | — | — |
| `skew_turn6` | learned | 54/64 | 7434 | 1288 mov | 1 | **8** | **−950** | no | 0.988 |

Cero colisiones, cero hechos falsos, cero escrituras imaginadas y calibración
sin cambios en las 1.280 misiones.

**Ninguna condición pasa el cribado.** `plan_a1_development_pass = false` en las
cuatro.

## El control negativo funciona, y eso valida el aparato

En `flat` no hay nada que aprender —el giro vale 0— y el brazo aprendido es
**idéntico al nominal hasta la unidad**: misma energía (4124), mismos
movimientos (1031), mismos giros (408), mismas metas (61). El montaje no
fabrica ventaja donde no la hay. Es la evidencia de validez más importante del
informe.

## Dos de mis controles no probaban nada

Hallazgo contra mi propio diseño, demostrable sin datos:

- **`permuted` es la identidad siempre que la base es uniforme.** Rota el vector
  de bases; rotar `[4,4,4,4]` devuelve `[4,4,4,4]`. Lo es en `flat`, `turn4` y
  `turn8`: tres de cuatro condiciones. El criterio «superar a `permuted`» era
  **insatisfacible por construcción**, y es el único que `turn4` incumple.
- **`crossed` es la identidad en `skew_turn6`**, porque declaré esa condición
  como fuente del control cruzado. Se compara consigo misma.

No son resultados: son defectos del contrato. Se corrigen en la enmienda 2 y se
vuelve a ejecutar; el rojo de esta corrida se conserva sin reescribir.

Para `turn4`, sin embargo, la pregunta de contenido **sí queda contestada** por
el control cruzado, que allí no es degenerado: una calibración real pero
equivocada (la de `skew_turn6`) gasta 6900 unidades, **peor que el nominal**
(5448), mientras la correcta gasta 4932. Tener «unos números» perjudica; tener
los correctos ayuda.

## Multiplicidad: ni `turn4` ni `turn8` sobreviven

Declaré cuatro campañas antes de ejecutar, pero no preespecifiqué la corrección.
Con α = 1/60 por condición ambas pasan (1/102 y 1/120). Con un umbral familiar
de Bonferroni sobre cuatro campañas, 1/240, **ninguna pasa**. Se publican los
dos números y el resultado se trata como **no confirmatorio**.

## El resultado más interesante es el negativo

En `skew_turn6` el brazo aprendido es **peor que la ignorancia uniforme**: 1221
unidades más, tres metas menos, ocho fallos nuevos. Y `learned` es **idéntico a
`oracle`**, así que no es error de estimación: los costes verdaderos, exactos,
llevan al planificador a peores misiones.

El mecanismo es visible en los movimientos: 1288 frente a 977 del nominal. Con
base `(3,5,4,4)` el planificador prefiere la acción barata (coste 3) y evita la
cara (coste 5); con horizonte de profundidad 4 eso explota localmente la
dirección barata y produce rutas más largas que acaban costando más y perdiendo
metas.

**Conocer el coste real con un planificador miope puede ser peor que no
conocerlo.** Es una conclusión sobre el acoplamiento entre calibración y
horizonte, no sobre la calidad del aprendizaje.

## El gate de reserva queda fuera de envolvente

La enmienda 1 fijó la constante de reserva en 4 porque el peor caso declarado
(14) hacía inviables dos tercios de las misiones. La consecuencia, ahora
medida: con giro 8 el nominal acumula **32 violaciones de reserva** y con
`skew_turn6` **38**. La regla subestima el coste real cuando se cobran giros.
Es idéntica en todos los brazos, así que no sesga la comparación, pero
`turn8` y `skew_turn6` están fuera de la envolvente segura de ese gate y su
criterio 1 falla por esa razón, no por el aprendizaje.

## Verificación

Artefacto: `lab/transfer3/plan-a1-screen.json`, hash canónico
`0553dc7e10c54e317301a5bf4e8758213706dfeb6c32729f352d01727f7f3d76`.
Auditoría completa en proceso nuevo, ejecutada **antes** de la enmienda 2:
`replay_valid=true`, exit 0, mismo hash. 21 tests A1 nuevos, todos en verde.

Como en v6 y v7, repetir esa auditoría después de añadir módulos fallará por el
defecto conocido de `inventory()`, que fotografía todo el árbol `nexus0` en vez
de las dependencias de la corrida. El código y el contrato de A1 quedan
congelados: la enmienda 2 vive en ficheros nuevos.

Sonda de identificabilidad y margen, previa a toda implementación:
`lab/transfer3/plan-a1-margin.json`, hash
`704f7f87a7e02877ad0f10445ebb5a363b8e695899e8267312bd530acad29061`, generada por
`lab/transfer3/plan_a1_margin.py`. El generador vive **fuera** de `nexus0/`
precisamente para no entrar en `inventory()` y no invalidar ninguna auditoría;
comprobado: los manifiestos de A1 y de la enmienda 2 siguen con cero rutas
alteradas tras añadirlo. Confirma sin agente ni aprendizaje que
`per_action_costs_are_conservative = true` y `turn_term_is_not = true`.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_a1 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.screen_a1 audit lab/transfer3/plan-a1-screen.json
```

## Razonamiento auditable

- **Hipótesis y predicción.** Una calibración de costes aprendida en A baja la
  energía de misión en salas nuevas. Predicción: ahorro positivo, sin fallos
  nuevos, amortizado contra el mismo bloque.
- **Evidencia.** Se cumple en `turn4` (+152, 0 fallos nuevos, amortiza, alcanza
  el techo oracle). Se incumple en `turn8` (3 fallos nuevos, 21 violaciones) y
  se invierte en `skew_turn6` (−950, 8 fallos nuevos).
- **Explicación rival.** La ventaja de `turn4` podría venir de tener cualquier
  vector distinto del prior, no del correcto. **Descartada** por el control
  cruzado: un vector real pero equivocado empeora el nominal en 1452 unidades.
- **Explicación rival 2.** El daño en `skew_turn6` podría ser error de
  estimación. **Descartada**: el brazo aprendido es idéntico al oracle.
- **Prueba discriminante pendiente.** Si el daño es miopía, acortar la asimetría
  de base o alargar el horizonte útil debería reducirlo; el horizonte, medido,
  lo acota la visibilidad y no `max_depth`, así que la prueba barata es variar
  la asimetría de base con el giro fijo.
- **Autorrevisión.** Dos controles degenerados —falta mía— y una constante de
  reserva fuera de envolvente en dos condiciones. Ninguno favorece al candidato:
  el control degenerado es precisamente el que le impide pasar. La corrida se
  hizo sobre salas públicas ya usadas en v4, así que es desarrollo, no
  confirmación.
- **Actualización.** Abandono la creencia de que una calibración correcta ayuda
  por sí sola: ayuda sólo cuando su estructura no empuja al planificador miope
  a rutas largas. Mantengo que el término de giro es identificable, barato y
  transferible.
- **Siguiente decisión.** Enmienda 2: sustituir los dos controles degenerados y
  repetir. Es la segunda y última revisión de este mecanismo permitida por el
  contrato. Si tras ella `turn4` sigue siendo la única condición con efecto y no
  sobrevive a multiplicidad, Plan A queda cerrado como efecto acotado y se pasa
  a Plan B.

TRANSFER-3 sigue en rojo. Esto es un **efecto público observado** en una de
cuatro condiciones, no un candidato confirmado. ECHO-3 permanece en 13/15.
