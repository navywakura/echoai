# TRANSFER-3 Plan A1 v2 — el término de giro transfiere; el de base perjudica

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado. Cribado en rojo en las
cuatro condiciones.** Contrato: [enmienda 2](TRANSFER3-PLAN-A1-V2-DESIGN.md),
fijada antes de ejecutar y después de publicar
[el rojo de A1](TRANSFER3-PLAN-A1-RESULTS.md), que se conserva sin reescribir.
No se generó ni abrió B/C.

## Los controles corregidos ya no son degenerados

| Condición | `turn_ablated` ≡ `learned` | `crossed` ≡ `learned` | `permuted` ≡ `learned` |
|---|---|---|---|
| `flat` | sí (giro verdadero 0) | no | sí |
| `turn4` | no | no | **sí** |
| `turn8` | no | no | **sí** |
| `skew_turn6` | no | no | no |

`permuted`, el control de A1, sigue siendo la identidad en tres condiciones: se
conserva reportado para que el defecto quede visible, no como criterio.

## Resultado

| Condición | Brazo | Metas | Energía | Giros | Viol. reserva | Fallos nuevos | Ahorro | Amortiza | p |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| `flat` | nominal | 61 | 4124 | 408 | 0 | — | — | — | — |
| `flat` | learned | 61 | 4124 | 408 | 0 | 0 | 0 | no | 1.0 |
| `turn4` | nominal | 59 | 5448 | 383 | 0 | — | — | — | — |
| `turn4` | **learned** | **62** | **4932** | **257** | **0** | **0** | **+152** | **sí** | 0.0098 |
| `turn8` | nominal | 55 | 6812 | 371 | 32 | — | — | — | — |
| `turn8` | learned | 59 | 6072 | 264 | 21 | 3 | +128 | sí | 0.0083 |
| `skew_turn6` | nominal | 57 | 6213 | 380 | 38 | — | — | — | — |
| `skew_turn6` | learned | 54 | 7434 | 380 | 1 | 8 | **−950** | no | 0.988 |

Cero colisiones, hechos falsos y escrituras imaginadas; calibración sin cambios
en las 1.536 misiones de examen.

**`turn4` cumple cinco de los seis criterios** —cero fallos nuevos, cero
violaciones, ahorro positivo, amortización (84 + 4932 = 5016 < 5448) y superar a
ambos controles de contenido— y falla **sólo** el umbral de multiplicidad que la
propia enmienda endureció: 0,0098 frente a 1/240 = 0,00417. Con el α ≤ 1/60 de
A1 habría pasado. No se afloja el umbral endurecido para aprobarlo.

## El contenido transferible es casi un bit

El control cruzado de `turn4` es la calibración de `turn8`: giro 8 donde el
verdadero es 4, equivocada al doble.

| `turn4` | Giro creído | Energía | Metas |
|---|---:|---:|---:|
| `nominal` | 0 | 5448 | 59 |
| `crossed` | 8 | 4940 | 62 |
| `learned` | 4 | **4932** | **62** |

Saber que **girar cuesta algo** vale 516 unidades. Saber **cuánto** vale 8, el
0,16 %. El criterio «supera a `crossed`» se cumple, pero por un margen que no
sostiene la afirmación de que importa el valor calibrado: lo que transfiere es
el hecho cualitativo.

Segundo matiz contra mi propio resultado: en las condiciones de base uniforme,
`turn_ablated` resulta **idéntico al brazo nominal** —ablacionar el giro de
`[4,4,4,4]` devuelve el prior exacto—, así que esa mitad del criterio 5 es
redundante con el criterio 3. El único control de contenido independiente en
`turn4` y `turn8` es `crossed`, con el margen de arriba.

## El diagnóstico confirma la miopía, y es monótono

Giro fijo en 6, sólo varía la asimetría de base. Declarado antes de ejecutarlo y
excluido del criterio y de la multiplicidad:

| Etiqueta | Base | Asimetría | Ahorro frente a nominal | Metas learned/nominal | Movimientos learned/nominal |
|---|---|---:|---:|---|---|
| `diag_skew0` | (4,4,4,4) | 0 | **+130** | 62 / 57 | 972 / 977 |
| `diag_skew1` | (4,5,4,4) | 1 | +12 | 53 / 55 | 1081 / 981 |
| `diag_skew2` | (3,5,4,4) | 2 | **−950** | 54 / 57 | 1288 / 977 |

La predicción registrada se cumple exactamente: el ahorro decrece de forma
monótona con la asimetría y cambia de signo, y los movimientos crecen de forma
monótona (972 → 1081 → 1288). **El término de giro ayuda; el de base perjudica,
y el daño escala con la asimetría.**

El mecanismo queda establecido: con horizonte acotado por la visibilidad, una
base asimétrica hace que el planificador explote localmente la dirección barata
y alargue la ruta hasta perder metas. No es error de estimación —en las cuatro
condiciones la calibración aprendida es **idéntica a la verdadera**, error 0— ni
error de aprendizaje.

La demostración más fuerte está en `skew_turn6`: la calibración **equivocada**
de `turn4` (base uniforme, giro 4) gasta 5499 y alcanza 61 metas, mientras la
**verdadera** gasta 7434 y alcanza 54. Conocer el coste real es peor que
ignorarlo cuando el planificador es miope.

## Razonamiento auditable

- **Hipótesis.** Los controles de A1 eran vacíos por construcción; corregirlos
  dejaría ver si el efecto de `turn4` es de contenido.
- **Evidencia.** Corregidos, `turn4` supera ambos controles y pasa cinco de seis
  criterios. Pero el margen frente al control independiente es 8 sobre 4932.
- **Explicación rival.** Que la ventaja venga de conocer el valor calibrado.
  **Descartada por el propio dato**: una calibración equivocada al doble rinde
  casi igual. La ventaja viene de `giro > 0`, no de su magnitud.
- **Explicación rival 2.** Que el daño en `skew_turn6` sea ruido de muestreo.
  **Descartada** por el diagnóstico monótono en tres niveles de asimetría con el
  giro fijo.
- **Autorrevisión.** `turn_ablated` duplica el brazo nominal en base uniforme:
  control más débil de lo que pretendía. El diagnóstico usa las mismas 64 salas
  públicas ya empleadas en v4, A1 y esta enmienda, así que es desarrollo
  acumulado sobre datos usados, no evidencia independiente. Ninguna de las dos
  debilidades favorece al candidato.
- **Actualización.** Abandono la hipótesis de que una calibración de costes
  completa transfiere. Mantengo, acotado, que **un único parámetro cualitativo
  —que cambiar de rumbo cuesta— se aprende con 16 movimientos, se transfiere en
  cinco enteros sin mapa y baja la energía de misión en salas nuevas**.
- **Decisión.** El contrato permitía dos revisiones de este mecanismo y ésta era
  la segunda. **Plan A queda cerrado** como efecto acotado y documentado.

## Candidato seleccionado, aún sin confirmar

De la evidencia sale un candidato distinto del probado: **calibrar sólo el giro
y dejar la base en el prior nominal**. En `turn4` y `turn8` coincide con el
brazo aprendido, que ya da sus mejores números; en `skew_turn6` sería
`[4,4,4,4]` con giro 6, próximo al cruzado que allí alcanzó 61 metas con 5499
unidades frente a las 57 y 6213 del nominal.

**No se mide aquí.** Proponerlo y evaluarlo sobre las mismas 64 salas sería
selección sobre datos ya usados. Exige confirmación prospectiva: una sola
condición, tamaño y criterio fijados antes, y **geometrías nuevas**, para las
que quedan 34 formas públicas de la familia histórica —insuficientes— y hace
falta el generador ampliado.

## Verificación

Artefacto: `lab/transfer3/plan-a1-v2-screen.json`, hash canónico
`796dc8602d879ad139ce304aba042bf384067975e1016e8c4536195ad0770a55`.
Auditoría completa en proceso nuevo: `replay_valid=true`, exit 0, mismo hash.
16 tests nuevos de la enmienda; **37 tests de Plan A**, todos en verde.

```sh
env PYTHONPATH=.. python3 -m unittest tests.test_transfer3_a1 tests.test_transfer3_a1_v2 -q
env PYTHONPATH=.. python3 -m echoai.nexus0.transfer3.screen_a1_v2 audit lab/transfer3/plan-a1-v2-screen.json
```

TRANSFER-3 sigue en rojo. Lo obtenido es un **efecto público observado**, con su
mecanismo explicado y su límite medido. No es candidato confirmado ni cierre de
custodia. ECHO-3 permanece en 13/15.
