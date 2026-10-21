# SENSOR-1S v3 — el sesgo del LiDAR, sólo donde la verdad puede juzgarlo

Estado: **prerregistro aprobado** (2026-09-11), anterior a cualquier
vuelo v3. V1 y v2 se conservan rojas e intactas.

## Por qué v3

V2 eliminó la parada del adaptador (espera máxima 6 ms en A y banco) y cayó
en el banco por un solo motivo: el sesgo del LiDAR por episodio en 2 de 12
mundos (+12.2/+13.0 mm en `fc7b66ad…`, +83 mm en `3d98a13f…`), con σ correcto y
profundidad perfecta en esos mismos mundos
([SENSOR1S-V2-RESULTS.md](SENSOR1S-V2-RESULTS.md)).

## Investigación (sobre la evidencia de v2, sin vuelos nuevos)

- **No es el modelo de verdad.** Ajustando un desvío global de guiñada por
  vuelo, el mejor valor es 0.0° en 29 de 45 vuelos honestos y el resto se
  reparte entre −0.4° y +0.4° sin signo constante. Un error de pose o de
  montaje daría el mismo desvío en todos los mundos. La profundidad comparte
  montaje y pose y tiene 1.4–2 mm de error sistemático en los mundos que fallan.
- **Es el LiDAR de GPU, haz a haz.** En los mundos que fallan, cada haz
  sensible se explica mejor con un desvío distinto que alterna de signo
  (−0.4, +0.2, +0.5, −0.3, +0.25…), siempre dentro de ±0.5°, compatible con un
  LiDAR que muestrea una textura renderizada en vez de trazar rayos exactos.
- **La geometría lo amplifica.** En caras casi rasantes el rango cambia
  ~r·cot θ por radián: 0.5° a 14° y 7 m son ~0.2 m. En un extremo de 200 mm el
  haz real pasa junto al borde y mide el muro de detrás.

## Cambio

Sólo el evaluador, en `nexus0/sensor1s_v3/evaluate.py`, copia del de v1:

- El **sesgo del LiDAR** se juzga sólo en haces cuya verdad trazada cambia
  ≤ 10 mm al girar el haz ±0.5°. Hacen falta ≥ 200 muestras juzgables por
  episodio; si no, el sesgo no se juzga en ese episodio y lo dice. En la etapa
  se agrupan (≥ 1000).
- El **σ del LiDAR** se sigue juzgando con todos los haces: es dispersión
  temporal de cada haz en reposo y un error fijo de dirección no la cambia.
- **Profundidad** sin cambios: su imagen es una proyección por píxel.
- El resto del evaluador es el de v1 byte a byte (las pruebas lo comparan
  función a función). El canal y su sesión son los de v2, importados.

Umbrales, ventanas, cotas de latencia, espera máxima 30 ms, tamaños (A 16 + 4,
banco 24 + 7) y mutantes: los de v1 con sus dos enmiendas. Semillas nuevas:
20261021 (A) y 20261022 (banco).

## Límites declarados

El filtro y sus dos números (0.5°, 10 mm) se eligieron **después** de ver el
banco de v2 en rojo, con sus datos. Retrospectivamente, sobre los 44 vuelos
honestos de v2, el sesgo filtrado queda ≤ 7.2 mm y en `cb83617b…` quedan 46
muestras por episodio (sesgo no juzgado ahí). V3 vuela todo de nuevo, pero
sobre los mismos 12 mundos de rehearsal: no es un examen reservado. El filtro
hace que el sesgo del LiDAR no se certifique en geometría rasante o de borde
estrecho; eso se publica como alcance, no se oculta.

Un verde v3 significaría sensores simulados con metadatos correctos en SITL y
un sesgo de LiDAR ≤ 10 mm donde la geometría permite juzgarlo; no sensores
físicos, percepción, WSP ni autonomía.
