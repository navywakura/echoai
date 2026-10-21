# PATTERN-1R — identidad de objeto entre vistas, sin oráculo

Estado: **contrato aprobado** (2026-09-12). Los umbrales de
identidad y confusión se fijan en una enmienda **antes del lock**, con los
números de los vuelos de desarrollo: el techo analítico (0.81–0.86) se midió
sin ruido y elegirlos a ciegas arriesga un rojo ajeno a la pregunta. Sin lock
ni vuelos de banco. Orden ECHO-3: quinto tajo, tras SIM-3,
FLIGHT-1S (v6), SENSOR-1S (v3) y GROUND-1 (v2).

## Pregunta única

¿Un mismo objeto, visto desde puntos de vista que no se usaron para formar las
familias, cae en **la misma** familia anónima, y dos objetos distintos en
familias distintas, cuando la firma se calcula dentro del consumidor aislado y
el aprendiz nunca recibe identidad, pose ni verdad?

No pregunta si el agente decide, vuela o planifica. No fusiona evidencias
(FUSION-1) ni sigue objetos en movimiento (DYNAMIC-1).

## Qué se midió antes de escribir esto (sin vuelos nuevos)

Sobre la evidencia de GROUND-1 v2 y por trazado de rayos sobre la verdad:

- Con el perfil de vuelo actual **no hay vistas distintas**: el dron flota. Cada
  barrera se ve con 2–14° de variación de ángulo y menos de 0.6 m de distancia.
- La estación de carga (0.6 × 0.6 × 0.2 m) **no la ve ningún sensor** en los 12
  mundos de rehearsal: los rayos son horizontales y el dron vuela a 1.6 m.
- 4 de los 12 mundos tienen barreras **gemelas** de tamaño idéntico.
- Una firma de 16 bits sobre esos mundos da, en el mejor caso analítico y sin
  ruido, 0.38–0.53 de acierto: el material no distingue objetos.
- Con mundos cuyas paredes difieren en altura y vano, y un reconocimiento a
  tres altitudes, el mismo método da **0.81–0.86** de acierto y 0.05–0.13 de
  confusión (tres semillas, sin ruido). Ese es el techo que este banco puede
  alcanzar.

## Qué cambia respecto a GROUND-1

1. **Familia de mundos propia**: `docs/examples/sim3-families/pattern1r-v1.json`,
   leída por el generador **congelado** de SIM-3 (mismos arquetipos, mismo
   perfil `sim3-boxes-v1`, mismo PRNG). Los rangos se eligen para que dentro de
   cada mundo las barreras difieran al menos 600 mm en altura y 800 mm en vano.
   Sin gemelos. SIM-3 no se toca.
2. **Vuelo de reconocimiento**: copia del runner de FLIGHT-1S v6 que, tras el
   hover, manda a PX4 posiciones acotadas (`MAV_CMD_DO_REPOSITION`) en 6 puntos
   de vista × 3 altitudes (0.9, 1.5, 2.1 m), esperando llegada con cota. PX4
   conserva PID, controladores y failsafes; el agente no vuela
   (`agent_in_gazebo=false`).
3. **Consumidor** (en la jaula, sobre el mismo cable de SENSOR-1S): segmenta
   cada barrido LiDAR en siluetas, asocia entre barridos por continuidad de
   ángulo y rango, y por cada **avistamiento** (un punto de vista completo,
   sus tres altitudes) emite una firma entera de 16 bits:
   - 2 bits: altitud más alta que todavía devuelve eco (monótona ante oclusión);
   - 4 bits: silueta más ancha vista en la ventana, cuantizada.
   El resto de bits queda a cero. Sin FPU en el paso rápido.
4. **Aprendiz**: la memoria PATTERN-1 de ECHO-2 (`nexus0/pattern1.py`,
   capacidad 64, Hamming ≤ 3), **importada, no copiada**. Escuela con
   `observe(firma, 0)`; examen con `predict(firma)`, que sólo recibe la firma.
   Una memoria nueva por vuelo.
5. **Evaluador**: asocia cada avistamiento con el objeto verdadero por rayos
   sobre la verdad privada, y recalcula la firma desde las muestras crudas.

## Escuela y examen, dentro del mismo vuelo

Los 6 puntos de vista se reparten en el contrato, no después: **4 de escuela**
y **2 de examen**, los mismos en todos los vuelos. El examen no escribe.

## Criterios verdes

| Grupo | Rojo si |
|---|---|
| Heredados | cualquier grupo de SENSOR-1S v3 o de GROUND-1 v2 rojo en el mismo vuelo |
| Sólo sensores | la firma del consumidor ≠ la que el evaluador recalcula desde las muestras crudas privadas |
| Un solo cable | la salida del consumidor lleva algo más que el recuento, los paquetes WSP y las firmas |
| Identidad | acierto por etapa bajo el umbral (a fijar en la enmienda tras desarrollo; referencia 0.75, techo analítico 0.81–0.86) |
| Confusión | confusión por etapa sobre el umbral (a fijar igual; referencia 0.15) |
| Congelado | alguna escritura en la memoria durante el examen, `cortex_calls ≠ 0`, `destroyed ≠ 0` |
| Ceguera | el aprendiz recibe algo que no sea la firma de 16 bits |
| Mutantes | alguno aceptado |

## Enmienda 1 (2026-09-12, antes del lock; aprobada)

Implementado el reconocimiento y medido contra la verdad, el planteamiento del
borrador no contesta la pregunta. Lo que se midió:

- Una firma por barrido **no lleva identidad**: la anchura aparente de una
  pared depende del ángulo desde el que se mira, así que los dos objetos de un
  mundo caen en la misma familia en 10–12 de los 12 mundos. El acierto que
  parecía perfecto era un colapso de familias, no un éxito; el criterio del
  borrador no lo detectaba.
- La cámara de profundidad tampoco basta: altura más anchura da 0.64 de
  acierto y 4 de 12 mundos colapsan.
- Con el reconocimiento en **arco continuo** y la anchura **acumulada mientras
  se sigue al objeto**, la longitud verdadera se recupera con 2 cm de error, y
  el resultado analítico (sin ruido) es acierto 1.000, confusión 0 y ningún
  mundo colapsado.

Cambios:

- **Reconocimiento**: arco continuo de 24 posiciones a 5.2 m del centro de los
  objetos, a 1.5 m de altura, 1.2 s de parada en cada una. Empieza por la
  posición más cercana al punto de aparición, para que el primer tramo no
  cruce ninguna pared. El arco lo calcula el arnés con la verdad; el
  consumidor nunca lo ve.
- **Firma**: el consumidor sigue cada silueta por continuidad (centro ±12
  haces, alcance ±0.9 m) y conserva la mayor anchura que le ha visto. La firma
  es el código termómetro de ese tamaño (tramos de 300 mm, 16 niveles), donde
  la distancia de Hamming **es** la diferencia de tamaño. El código Gray del
  borrador no servía: tramos lejanos también quedaban a 3 bits.
- **Escuela y examen**: posiciones 0–15 del arco y 16–23, fijadas aquí.
- **Criterio nuevo, «objetos separados»**: dos objetos no pueden compartir
  familia, y cada objeto debe tener al menos el 60 % de sus avistamientos de
  escuela en la suya. Sin él, un colapso saca examen perfecto.
- **Mundos**: las dos paredes por encima del techo del vuelo (2.4–2.6 m) y con
  longitudes separadas ≥ 1.2 m (2.6–2.8 frente a 4.0–4.2 m).
- **Mutantes**: los del borrador (`oracle_id`, `view_leak`, `span_only`)
  necesitaban verdad o pose que el consumidor no tiene. Los sustituyen
  `range_leak` (firma la distancia), `beam_index` (firma dónde está, no qué
  es) y `replay` (repite la firma anterior), junto a `constant_family`,
  `frozen_write` y `extra_channel`.
- **Límite del episodio**: 900 s, porque el arco no cabe en los 420 s del
  perfil de hover.

Límites declarados que añade esta enmienda: la acumulación es seguimiento por
continuidad, sin oclusión, y eso roza el terreno de DYNAMIC-1; la identidad
descansa sólo en la longitud; el mapeo de ejes (Gazebo ENU, PX4 NED) se midió
en vuelo, no se supuso.

## Enmienda 2 (2026-09-12, antes del lock)

Volado el arco, dos cosas más se midieron y hubo que corregir:

- **El arco se vuela, no se salta.** A 15° entre paradas el rumbo de un objeto
  se mueve más de lo que la continuidad puede seguir sin conocer el propio
  movimiento, y una pista salta de una pared a la otra llevándose su tamaño.
  Ahora son 48 posiciones sin parada, con banda de llegada ancha: el rumbo
  deriva menos de un grado por barrido. La ventana de cada tramo pasa a ser el
  tramo entero, porque el cuerpo mira todo el rato.
- **Dos paredes juntas se funden en una silueta** cuando se alinean con el
  observador, y la pista absorbe las dos. Las paredes se separan (x de −3.0 a
  −2.6 m y de +2.6 a +3.0 m) y la órbita pasa a 5.0 m del centro.

Con el consumidor real sobre órbita densa simulada: acierto 0.894, confusión
0.098, ningún mundo colapsado. Los ajustes que parecían prudentes (hablar sólo
tras estabilizar, ignorar siluetas cortas) empeoran y se descartan: el
consumidor emite cada silueta de al menos 4 haces con el mayor tamaño que le
ha visto.

## Mutantes obligatorios

`oracle_id` (mete el índice verdadero del objeto en la firma), `view_leak`
(mete la pose o la altitud absoluta), `frozen_write` (escribe en el examen),
`constant_family` (una sola firma), `span_only` (ignora la altura) y
`extra_channel` (añade un campo a la salida). Cada uno debe poner rojo su caso
concreto en un vuelo sano, con su gemelo honesto del mismo mundo en verde.

## Muestra

Validación A: 8 mundos nuevos × 1 vuelo + 2 controles sin reconocimiento
(sólo hover), para comprobar que sin vistas no hay identidad que medir. Banco
(si A pasa): 12 mundos × 2 vuelos + 6 mutantes. Semillas 20261201 (A) y
20261202 (banco). Desarrollo libre en A y conservado.

## Límites que ya se saben

Los objetos son cajas grises: la identidad descansa en altura y vano, no en
textura, color ni forma. La estación de carga sigue siendo invisible para estos
sensores. El techo analítico sin ruido es 0.86, así que un verde aquí no
afirma reconocimiento visual de objetos reales, ni identidad persistente en
vídeo, ni invariancia ante oclusión fuerte. La asociación entre barridos es
continuidad simple, no seguimiento (DYNAMIC-1).
