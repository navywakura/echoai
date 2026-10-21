# DYNAMIC-1 — movimiento externo y predicción corta

Estado: **borrador de contrato**, pendiente de Aprobado:. Sin
código, sin lock, sin vuelos. Orden ECHO-3: se adelanta a PATTERN-1R por
Decisión (2026-09-12), porque la identidad entre vistas descansa en
seguir objetos, que es la pregunta de este tajo
([PATTERN1R-RESULTS.md](PATTERN1R-RESULTS.md)).

## Pregunta única

¿El consumidor aislado, que sólo recibe los sensores por un cable, distingue
**qué parte del mundo se mueve** y predice **dónde estará medio segundo
después**, sin oráculo, sin pose propia y sin un segundo canal?

No pregunta si el agente decide, planifica o esquiva. No reconoce objetos
(PATTERN-1R) ni fusiona evidencias (FUSION-1).

## Qué ya se comprobó (sin vuelos nuevos)

- Los mundos de SIM-3 son estáticos por perfil (`sdf_model_not_static`), así
  que no hay movimiento por física. Pero el arnés **sí puede mover un modelo**
  durante la simulación: medido en el contenedor, una pared pasó de x = −3.0 a
  x = −1.0 m con el servicio `set_pose`, y el mundo publica su pose en
  `/world/<w>/pose/info`, que es la verdad privada del móvil.
- El servicio responde `false` aunque el efecto ocurre; el arnés no se fía de
  la respuesta y comprueba la pose publicada.
- Una pared a 5 m que se mueve a 0.5 m/s cambia de rumbo 0.57° por barrido, muy
  por debajo de lo que la continuidad sigue (medido en PATTERN-1R).

## El banco

Vuelo de FLIGHT-1S v6 sin reconocimiento: despegue, estabilización y
estacionario. Durante una ventana declarada, el arnés mueve **una** pared en
línea recta a velocidad constante; la otra pared y la estación no se tocan y
son el control dentro del mismo vuelo. El cuerpo está quieto: descontar el
movimiento propio queda fuera de alcance y se declara.

El movimiento es cinemático, no físico: la pared no empuja ni colisiona. Se
declara como limitación, igual que SIM-3 declara sus cajas.

## Qué emite el consumidor

Por cada barrido y cada silueta seguida (el seguidor de PATTERN-1R, reutilizado):

| Campo | Significado |
|---|---|
| `capture_ns` | sello de captura del barrido |
| `bearing_mdeg`, `range_mm` | dónde está ahora, en el marco del sensor |
| `moving` | 0/1: su posición cambia de forma sostenida |
| `pred_bearing_mdeg`, `pred_range_mm` | dónde estará 500 ms después |

Todo entero. Sin pose, sin identificadores, sin verdad. La salida sigue siendo
un único cable: el recuento de SENSOR-1S, los paquetes WSP de GROUND-1 y estos
registros.

## Criterios verdes

| Grupo | Rojo si |
|---|---|
| Heredados | cualquier grupo de SENSOR-1S v3 o GROUND-1 v2 rojo en el mismo vuelo |
| Sólo sensores | los registros del consumidor ≠ los que el evaluador recalcula desde las muestras crudas |
| Un solo cable | la salida lleva algo más, o el stderr no es la línea canónica |
| Detección | la pared que se mueve no queda marcada `moving` en la mayoría de sus barridos de la ventana, o una pared quieta queda marcada en más de un umbral pequeño |
| Predicción | error de la predicción a 500 ms por encima del umbral, contra la verdad privada del móvil proyectada al marco del sensor |
| Reposo | con la pared quieta (controles), alguna marca de movimiento |
| Mutantes | alguno aceptado |

Los umbrales de detección y de predicción se fijan **en una enmienda antes del
lock**, con los vuelos de desarrollo, como se acordó en PATTERN-1R: elegirlos a
ciegas arriesga un rojo ajeno a la pregunta.

## Enmienda 1 (2026-09-12, tras el desarrollo; umbrales fijados)

Volado el banco, se corrigió una cosa y se fijaron los umbrales con los ocho
vuelos de desarrollo, como se acordó.

- **La pared cruza su propia cara, no se desliza a lo largo de ella.** Una
  pared que se mueve en su propia dirección apenas cambia de silueta: medido,
  sólo el 14 % de sus barridos salían marcados. Cruzándola, 87–97 %.
- **Qué emite el consumidor**: `[captura, x, y, se_mueve, x_previsto,
  y_previsto]` en el marco del sensor, en milímetros enteros. El borrador decía
  rumbo y alcance; en coordenadas no hace falta trigonometría y es lo mismo.
- **Cómo decide**: cada pista guarda 10 barridos (un segundo) y se llama móvil
  si se ha desplazado más de 120 mm en esa historia. La predicción es la
  extrapolación lineal de ese desplazamiento a 500 ms.

Umbrales, por debajo del peor caso de la tanda:

| Criterio | Umbral | Peor caso medido |
|---|---|---|
| Detección del móvil | ≥ 0.80 | 0.873 (media 0.934) |
| Quietos marcados, con algo moviéndose | ≤ 0.30 | 0.241 |
| Quietos marcados, sin nada moviéndose | ≤ 0.15 | 0.093 |
| Diferencia entre ambos | ≥ 0.50 | 0.667 |
| Error de predicción, mediana | ≤ 90 mm | 58 mm (enmienda 2) |
| Error de predicción, p95 | ≤ 160 mm | 102 mm (enmienda 2) |

**Límite que esto declara**: el cuerpo en estacionario deriva, y sin pose no
puede descontar su propio movimiento. Por eso un 9 % de los registros sale
marcado aunque no se mueva nada: ese es el suelo de este banco, no un fallo del
consumidor. El límite del episodio sube a 600 s. El servicio `set_pose`
responde `false` aunque mueve el modelo; el arnés comprueba la pose publicada.

## Enmienda 2 (2026-09-12, tras la revisión independiente; antes del lock)

El revisor encontró dos cosas que habrían impedido un veredicto y una que lo
habría falseado:

- **La cadena no habría escrito informe.** La agregación por etapa llamaba a
  una función que este evaluador no reexportaba, y una variable local pisaba
  un parámetro. Ambas corregidas; además, una congelación fallida ya no deja
  escrito nada que impida reintentarla.
- **La predicción se juzgaba contra la velocidad mandada, no contra la real.**
  El arnés pide 500 mm/s, pero `set_pose` arrastra y el mundo mueve la pared a
  unos 225 mm/s. Con la verdad tomada de las poses publicadas, el error honesto
  baja de 155 a 58 mm de mediana, y un consumidor que prediga quietud marca
  118 mm. Los umbrales pasan a 90 mm de mediana y 160 de p95: el honesto entra
  con holgura y la mentira queda fuera.
- **Un barrido sin pose de verdad corría la correspondencia** entre registros y
  objetos para el resto del vuelo. Ahora esos registros se saltan contándolos, y
  un solo caso pone rojo el grupo.

Otros cambios de la misma revisión: el mutante `frozen_world` vuela con la
configuración de control, como dice este contrato; cada etapa comprueba además
que los vuelos que debían mover algo lo movieron; y la comprobación de
«enteros» rechaza booleanos, que en Python son enteros.

**Declarado**: la velocidad real del móvil no es la mandada, y la cadena juzga
la real. La evidencia de desarrollo entra en la historia del lock, así que
volar desarrollo después de congelar abortaría las etapas.

## Mutantes obligatorios

`no_motion` (nunca marca movimiento), `always_motion` (lo marca siempre),
`copy_current` (predice la posición actual, no la futura), `replay` (repite el
registro anterior), `frozen_world` (marca movimiento en el control) y
`extra_channel` (añade un campo a la salida). Cada uno debe poner rojo su caso
concreto con el vuelo completo, y su gemelo honesto del mismo mundo pasar.

## Muestra

Validación A: 8 mundos con movimiento + 2 controles sin movimiento. Banco (si A
pasa): 12 mundos + 6 mutantes. Semillas 20261301 (A) y 20261302 (banco). Mundos
de la familia de PATTERN-1R, que ya tiene dos paredes separadas y visibles.

## Límites que ya se saben

El movimiento es cinemático y sin física. El cuerpo está en estacionario: este
tajo no demuestra separar el movimiento propio del ajeno con el cuerpo en
marcha. La predicción es a 500 ms y en línea recta: no hay maniobras, ni
oclusión deliberada, ni varios móviles a la vez.
