# TRANSFER-3 Plan A1 v2 — enmienda 2: controles no degenerados

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Enmienda al
[contrato A1](TRANSFER3-PLAN-A1-DESIGN.md), fijada **antes** de ejecutarla y
**después** de publicar el rojo de A1 en [sus resultados](TRANSFER3-PLAN-A1-RESULTS.md).
El contrato, el código y el artefacto de A1 quedan congelados: esta enmienda
vive en ficheros nuevos y no reescribe ningún rojo.

## Qué se corrige y por qué

Dos de los cinco brazos de A1 eran **vacíos por construcción**, lo cual es
demostrable sin datos y no depende del resultado:

| Control | Defecto | Dónde |
|---|---|---|
| `permuted` | rota el vector de bases; rotar `[4,4,4,4]` devuelve `[4,4,4,4]` | `flat`, `turn4`, `turn8` |
| `crossed` | declaré `skew_turn6` como fuente única, así que esa condición se compara consigo misma | `skew_turn6` |

El criterio «superar a `permuted`» era por tanto insatisfacible en tres de las
cuatro campañas, y es el único que `turn4` incumplía. Corregirlo **endurece** el
cribado: pasa de un control válido y otro vacío a dos controles válidos.

No se toca ninguna métrica, ni el tamaño de muestra, ni el horizonte de
amortización, ni las salas, ni el presupuesto de escuela, ni la constante de
reserva. No se retira ninguna condición.

## Control de contenido nuevo: `turn_ablated`

Conserva la base aprendida y fuerza el giro al prior nominal (0).

Justificación, fijada por la sonda de margen previa a toda implementación: un
coste por acción es **conservativo** y no distingue rutas de longitud mínima
—dispersión medida 0 en las 64 salas, incluso con base (2,6,3,5)—. El término
de giro es la **única** parte de la familia que puede cambiar la ruta elegida.
Ablacionarlo es por tanto el test de contenido correcto, y no es la identidad
en ninguna condición con giro distinto de 0.

En `flat` sí coincide con `learned`, porque allí el giro verdadero **es** 0. Es
correcto y esperado: en esa condición no hay contenido que ablacionar y el
resultado previsto es nulo.

## Fuente cruzada cíclica

`crossed` toma la calibración aprendida bajo otra condición, nunca la propia y
nunca `flat` —cuya calibración coincide exactamente con el prior nominal, lo que
la convertiría en un duplicado del brazo `nominal`—:

| Condición | Fuente cruzada |
|---|---|
| `flat` | `turn4` |
| `turn4` | `turn8` |
| `turn8` | `skew_turn6` |
| `skew_turn6` | `turn4` |

`permuted` se conserva como brazo **reportado pero no criterio**, para que el
registro muestre su degeneración en vez de ocultarla.

## Endurecimiento de la significación

A1 declaró cuatro campañas pero no preespecificó la corrección por
multiplicidad. `turn4` y `turn8` pasaban α ≤ 1/60 individualmente (1/102 y
1/120) y **ninguna** sobrevivía al umbral familiar de Bonferroni 1/240.

A1 v2 exige **α ≤ 1/240**, el umbral corregido para las cuatro campañas
declaradas. Es una exigencia mayor, no menor, y se fija antes de ejecutar.

## Criterio de paso

`plan_a1_v2_development_pass` exige **todas**:

1. cero colisiones, violaciones de reserva, hechos falsos, escrituras
   imaginadas y calibración alterada durante el examen;
2. `new_failures == 0` frente a `nominal`;
3. energía en éxitos conjuntos estrictamente menor que `nominal`;
4. energía de escuela + el mismo bloque de examen menor que la de `nominal`;
5. superar a `turn_ablated` **y** a `crossed` en energía de éxitos conjuntos;
6. signo de una cola con **α ≤ 1/240**.

## Diagnóstico separado: miopía frente a asimetría de base

En A1, `skew_turn6` resultó **peor que la ignorancia uniforme** con una
calibración idéntica al oracle, lo que descarta error de estimación. La
hipótesis es que la asimetría de base empuja a un planificador de horizonte 4 a
explotar localmente la dirección barata y alargar la ruta (1288 movimientos
frente a 977).

Prueba discriminante, con el giro **fijo en 6** y sólo la asimetría variando:

| Etiqueta | Base | Asimetría |
|---|---|---:|
| `diag_skew0` | (4, 4, 4, 4) | 0 |
| `diag_skew1` | (4, 5, 4, 4) | 1 |
| `diag_skew2` | (3, 5, 4, 4) | 2 |

Predicción: si la hipótesis es correcta, el ahorro frente a `nominal` decrece de
forma monótona con la asimetría y cambia de signo.

Este diagnóstico es **explícitamente no candidato**: sólo `nominal` y `learned`,
excluido del criterio de paso y de la cuenta de multiplicidad, y declarado aquí
antes de ejecutarlo. No puede convertir en verde ninguna campaña.

## Regla de parada

Ésta es la **segunda y última** revisión de este mecanismo que el contrato
permite. Si tras ella ninguna condición pasa, Plan A queda cerrado como efecto
acotado y documentado, y se pasa a Plan B —calibración del modelo de
ejecución—, sin una tercera revisión de la calibración de costes.
