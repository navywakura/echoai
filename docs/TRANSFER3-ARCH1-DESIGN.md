# TRANSFER-3 ARCH-1 — contrato: ¿es el compromiso de plan lo que falta?

2026-09-18. **Desarrollo público. TRANSFER-3 no cerrado.** Filtro previo a
campaña, fijado antes de ejecutar. Sin escuela, sin jaula, sin candidato, sin
B/C. Roger autoriza explícitamente tocar el planificador, que hasta ahora se
trataba como fijo; la extensión es **versionada, acotada y documentada**, no un
núcleo cognitivo nuevo.

No es el Plan C de la propuesta —calibración perceptiva—, que sigue sin abrirse.
Es una investigación sobre la arquitectura, numerada aparte para no confundirlas.

## De dónde sale

Plan A y Plan B aprendieron cada uno una propiedad del cuerpo **con exactitud** y
ninguna sirvió. La explicación que ofrecí es arquitectónica:

> El planificador replanifica desde cero en cada paso sobre un horizonte corto.
> Eso lo hace robusto al error de modelo e incapaz de rentabilizar su precisión:
> un plan que habría descarrilado no cuesta nada si se descarta antes de
> ejecutarlo.

Una explicación así no vale nada mientras no se pueda refutar. Esto la pone a
prueba.

Dato previo que acota la palanca: en A1 quedó medido que **la profundidad no es
la palanca**. Subir `max_depth` de 4 a 8 con presupuesto 128 no cambió ni un
resultado, porque el horizonte útil lo acota la visibilidad —el agente no puede
expandir la búsqueda a celdas que no ha observado—. Lo que se varía aquí es el
**compromiso**, no la profundidad.

## La extensión

`planner_arch1.CommittedPlanner` permite comprometerse con hasta `commitment`
acciones del plan encontrado. El compromiso **no regala nada**:

- **Ningún gate se salta.** Una acción comprometida pasa exactamente las mismas
  comprobaciones de admisibilidad, trayectoria de ráfaga, evidencia y reserva
  que una recién buscada, sobre la observación del paso que la ejecuta. Un plan
  comprometido es una propuesta, nunca una licencia.
- **Un plan descarrilado se abandona.** Si el cuerpo no aterriza donde el modelo
  predijo, el resto del compromiso se tira y se replanifica. Eso es lo que hace
  caro un modelo inexacto, que es justamente el punto.

`commitment = 1` reproduce la conducta histórica exactamente, así que el brazo
que representa la arquitectura de hoy es **el mismo código con un parámetro**.

## Diseño

Se reutiliza el cuerpo de ganancia de [B1](TRANSFER3-PLAN-B1-FILTER.md), donde
el error de modelo es grande y consecuente: el nominal cree avanzar una celda y
avanza dos o tres.

| | |
|---|---|
| Salas | 24 del generador de dos paredes, semilla `20268001` |
| Condiciones | `flat` (1,1,1,1), `gain2` (2,1,1,1), `gain3` (3,1,1,1) |
| Brazos | `nominal` (cree 1) y `oracle` (ganancias verdaderas servidas) |
| Compromisos | **1, 2, 3, 4, 6** |
| Reserva | 6, idéntica en todos los brazos |

El `oracle` recibe las ganancias directamente, sin escuela: es **cota superior
de cualquier aprendiz**. Si con compromiso no gana, ningún aprendizaje lo hará.

## Predicción registrada

**La ventaja del oráculo sobre el nominal es cero con compromiso 1 y crece con
el compromiso**, porque un modelo equivocado descarrila un plan comprometido y
uno correcto no.

## Regla de retractación

**Si la ventaja se mantiene plana al crecer el compromiso, la explicación
arquitectónica queda refutada y se retira de los informes de A y B**, donde
figura como interpretación y no como hecho medido. En ese caso el fracaso de
ambos planes se queda sin explicación común y hay que buscar otra.

Esta regla se escribe antes de ver los números precisamente porque la
explicación es mía y me conviene que sea cierta.

## Qué no demuestra si la predicción se cumple

Que el compromiso sea la palanca **no produce candidato ni transferencia**.
Diría dónde buscarla, no que exista. Cualquier campaña posterior necesitaría su
propio contrato, escuela real, jaula y confirmación prospectiva. Y un compromiso
largo tiene su propio coste —actuar sobre observaciones más viejas—, que habría
que medir, no suponer.

Sigue siendo software y simulación: ni julios físicos, ni hardware, ni HIL, ni
vuelo real, ni DRONE-3.
