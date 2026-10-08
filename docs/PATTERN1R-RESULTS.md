# PATTERN-1R — resultados

Estado: **ROJO en desarrollo**. El tajo no llegó a lock ni a cadena: los vuelos
de desarrollo, que son los que deciden si la pregunta se puede contestar,
dicen que con este banco no. Todo el código y toda la evidencia se conservan.
Contrato: [PATTERN1R-DESIGN.md](PATTERN1R-DESIGN.md), con sus enmiendas 1 y 2.

## Qué quedó probado

| Pieza | Medida |
|---|---|
| Mundos propios | familia declarativa leída por el generador **congelado** de SIM-3; 12 mundos, dos paredes por mundo, largos 2.6–2.8 m y 4.0–4.2 m, ambas de 2.4–2.6 m de alto, sin gemelas |
| Vuelo de reconocimiento | 48 objetivos acotados por `MAV_CMD_DO_REPOSITION`; PX4 los aceptó 48/48 y conservó PID, controladores y failsafes; 36–46 tramos alcanzados por vuelo; órbita de 5 m a 1 m/s, 156 s |
| Sólo sensores | las firmas que salen de la jaula se recomputan **byte a byte** desde las muestras crudas privadas (2012 = 2012, 2030 = 2030) |
| Examen congelado | la memoria PATTERN-1 importada no cambia durante el examen: mismo hash antes y después |

## Qué falló

La afirmación central. Con seis mundos y quince combinaciones de ajustes del
consumidor:

| | mejor | peor |
|---|---|---|
| Acierto de identidad | media 0.407 | 0.000 |
| Confusión | media 0.593 | 1.000 |
| Mundos con familias colapsadas | 3 de 6 | 6 de 6 |

Un vuelo suelto llegó a dar 0.845 con confusión 0.155; la tanda completa
demuestra que era ruido. Un vuelo de los seis se pasó del límite de episodio.

## Por qué

Una silueta de LiDAR 2D no identifica a una pared:

- Vista desde un rumbo, su anchura aparente es cualquier valor entre su grosor
  y su largo, así que una firma por barrido mete los dos objetos en la misma
  familia: colapso en 10–12 de 12 mundos en el estudio analítico.
- Acumulando la anchura mientras se sigue al objeto, la longitud verdadera sí
  se recupera (2.68 m medidos frente a 2.70 reales; 4.18 frente a 4.20), y en
  órbita densa **simulada** el resultado es 0.894 de acierto sin colapsos.
- En vuelo real ese resultado no se sostiene. Tres causas medidas: el LiDAR de
  GPU pierde haces en incidencia rasante y parte una pared en trozos; el cuerpo
  se inclina (p95 de 5°, máximos de 35–42°) y el plano de barrido deja de ser
  el simulado; y dos paredes alineadas con el observador se funden en una
  silueta, con lo que la pista se lleva el tamaño de las dos.

La pieza que falta no es una firma mejor: es **seguir un objeto a través de
vistas**, con oclusiones y con el propio movimiento descontado. Esa es la
pregunta de DYNAMIC-1.

## Trampas que costaron los seis vuelos de prueba, y que quedan documentadas

1. Medir sólo el acierto es ciego al colapso: si los dos objetos caen en una
   familia, el examen sale perfecto y no significa nada. El criterio
   «objetos separados» se añadió por eso (enmienda 1).
2. El código Gray no sirve para una memoria que agrupa a 3 bits: tramos
   lejanos también quedan a 3 bits. El termómetro hace que la distancia de
   Hamming **sea** la diferencia de tamaño.
3. El arco hay que volarlo, no saltarlo: a 15° entre paradas una pista salta
   de una pared a otra. Y la llegada debe medirse en distancia, no por eje: una
   banda de 0.8 m por eje deja declarar alcanzado un objetivo a 1.4 m.
4. El eje norte de PX4 es el eje **y** de Gazebo; se midió en vuelo, no se
   supuso.
5. El identificador de mundo no depende de su contenido: dos familias distintas
   con el mismo índice dan mundos distintos con el mismo nombre. PATTERN-1R usa
   índices propios (100–111).

## Qué significa y qué no

Significa que el banco puede volar un reconocimiento guionizado con objetivos
acotados, que lo que sale de la jaula es reproducible desde los sensores, y que
el examen no contamina lo aprendido. No significa identidad de objeto entre
vistas: eso no se ha demostrado, y con el LiDAR 2D de este cuerpo, sin
seguimiento, no parece demostrable.

## Propuesta

Hacer **DYNAMIC-1** antes que PATTERN-1R, porque la identidad entre vistas
descansa en seguir objetos, que es justo su pregunta. PATTERN-1R vuelve
después, reutilizando sus mundos, su vuelo de reconocimiento y su consumidor.

## Reproducir

```bash
PYTHONPATH=.. python3 -m echoai.nexus0.pattern1r.dev <label> --world N --seed S
```

Evidencia: `lab/pattern1r/dev/`. Seis vuelos honestos (`honest-w0`…`honest-w5`)
y siete de prueba (`probe1`…`probe7`), con su registro privado y su transcript.
