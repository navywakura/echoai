# ECHO-4.5 · S4 (inferir la meta y planificar) · contrato (fijado el 2026-09-26, antes de construir) · VERDE EN DESARROLLO (iteración 3)

Roger: «S4 ahora». Se desarrolla y mide **solo** en los 8 juegos de desarrollo. Los 16 juegos de
examen de ECHO-4.5 no se tocan.

## Por qué S4

- S3 demostró que ECHO gasta menos acciones al ver el juego como objetos.
- También demostró que **saber quién eres no sirve sin una meta**: explorar posiciones a ciegas no
  sumó niveles.
- Con la fórmula oficial (cada nivel al cuadrado), un nivel completado con pocas acciones vale
  muchísimo más que uno completado explorando.

## Qué construye S4 (agente v4, sobre v3 + el módulo del «yo» de v3b)

1. **«Yo» con varios cuerpos.** Si hay varios objetos iguales que se mueven a la vez con cada tecla
   (m0r0), todos son «yo».
2. **Curiosidad por objetos, antes de ganar nada.** Como haría una persona, ECHO **va a tocar los
   objetos**:
   - primero los que se parecen a él (mismo color o forma), después los de colores raros;
   - planifica el camino más corto en su mapa aprendido (reglas de cada tecla y muros), en lugar de
     explorar casilla a casilla.
3. **Meta inferida al ganar un nivel.** Se guarda **qué tipo de objeto** tenía cerca (o sobre qué
   tipo hizo clic) justo al completarlo. Eso es una **hipótesis de meta**, nunca un hecho. En el
   nivel siguiente se prueba primero; si vuelve a ganar se confirma, y si no, se refuta y se sigue
   con la curiosidad.
4. **Juegos de clic:** los tipos de objeto sobre los que hizo clic justo antes de ganar pasan a ser
   los primeros candidatos en el nivel siguiente.

## Criterio (fijado antes de medir)

8 juegos de desarrollo, 2000 acciones por juego, puntuación oficial correcta:

| Id | Condición |
|---|---|
| G1 | niveles completados por v4 **>** v3 (7) |
| G2 | puntuación oficial media de v4 **>** v3 (0,678) |
| G3 | la repetición de todas las partidas de v4 da 0 diferencias |

**S4 verde = G1 ∧ G2 ∧ G3.** Se informa además cuántas hipótesis de meta se confirmaron y cuántas
se refutaron.

## Iteración 1 (2026-09-26): v4 y v4.1 — ROJO

| Agente | Niveles | Puntuación oficial (semilla original) |
|---|---|---|
| v3 (base S3) | 7 | 0,678 |
| v4: curiosidad por objetos + camino planificado | 7 | 0,412 |
| v4.1: «yo» que puede cambiar de cuerpo + meta por semejanza + sin meta se comporta como v3 | **8** | 0,425 |

- v4 **no se activaba** al principio: ECHO solo había probado 2 de sus 4 teclas. Se añadió el
  **balbuceo motor**: probar cada tecla al empezar, como hace una persona con un juego nuevo.
- En m0r0 la meta por semejanza **perseguía a su propio gemelo**. Arreglo: un objeto idéntico a mí
  solo es meta si **se queda quieto** cuando yo me muevo.
- v4.1 completa por primera vez un nivel de **g50t**, pero tras 1817 acciones, así que vale casi 0.

## Iteración 2 (2026-09-26): medir con 3 semillas y entender g50t — ROJO

**Tres semillas por juego** (desarrollo; el criterio de S4 no cambia), con el balbuceo reducido a una
pulsación por tecla:

| | Semilla 0 | Semilla 1 | Semilla 2 | Media |
|---|---|---|---|---|
| v3 | 0,678 · 7 | 0,619 · 7 | 0,590 · 7 | **0,629** |
| v4.1 | 0,542 · 7 | 0,618 · 7 | 0,046 · 8 | **0,402** |

- La puntuación depende casi solo de **lp85** (de 0,16 a 3,27 según la semilla) y **m0r0** (de 0,10
  a 4,76). Los demás juegos aportan casi 0.
- El nivel de g50t sale en **1 de 3** semillas: fue suerte.
- **v4.1 no mejora a v3 de media.**

**Qué es g50t** (visto repitiendo la partida y dibujando los fotogramas, en
`lab/arc3/s4-dev/v41/g50t-5849a774.json`):
1. ACTION5 deja una **copia** del cuerpo donde está y devuelve el cuerpo al inicio.
2. Con una copia sobre el **extremo de la tubería celeste** (el interruptor), la **compuerta** de la
   izquierda cambia de forma y deja pasar.
3. El cuerpo pasa la compuerta, baja por el pasillo y entra en el **marco en U** del mismo color y
   con el mismo punto → nivel completado. El nivel 2 es un laberinto nuevo con la misma idea.

**Lectura:** ganar exige **entender la mecánica causal** («mi copia sobre el interruptor abre la
compuerta»). Ir hacia la meta sin ella no basta.

## Iteración 3 (2026-09-26): modelo del mundo verificado y planificar en él — VERDE en desarrollo

**Plan reescrito** tras revisar lo que funciona en ARC-AGI-3 (agentes con modelo del mundo
ejecutable, verificación por repetición exacta, simplificación y planificar en el modelo; Rodionov
2026, arXiv 2605.05138 y 2607.15439). Lo que se adopta, sin LLM y en CPU (agente **v5**,
`echo_arc/agent.py::Arc3EchoV5`):

1. **Predicción verificada:** antes de cada tecla el modelo predice si «yo» me moveré, y se compara
   con el fotograma real. Cada transición es una prueba de repetición, hecha paso a paso.
2. **Simplificación:** los muros se aprenden como **colores** (un color que me frenó al menos 3
   veces y me dejó pasar menos del 10 %). Es una regla en lugar de un caso por (posición, tecla), y
   viaja al nivel siguiente.
3. **Planificar en el modelo:**
   - los caminos se buscan sobre el fotograma actual con los colores-muro;
   - si no hay meta, se explora **en el modelo**: se va a la posición alcanzable más cercana que no
     se ha visitado, en vez de explorar estados a ciegas.
4. **Causas:** un cambio en la zona de juego que no es mi cuerpo y que ocurre **a distancia** (no
   lo he empujado) es una sorpresa.
   - Dónde estaban mis cuerpos en ese momento queda como **hipótesis causal**, nunca como hecho.
   - Si la meta es inalcanzable, se va primero a la causa, se comprueba y se prueban allí las teclas
     de modo (dos pasos).
5. **El «yo» con toda la evidencia:** en un pasillo solo me muevo en una dirección durante mucho
   tiempo. v4.1 no me encontraba en g50t por eso; v5 me encuentra en las 3 semillas.
6. **En los juegos con clic, v5 se comporta exactamente como v3.** Si hay clic, el cuerpo no es
   todo el juego: los módulos de cuerpo de v4.1 empeoraban bp35 y m0r0. Es una regla ajustada **en
   desarrollo**, después de ver esos dos juegos.

**Resultados (8 juegos de desarrollo, 2000 acciones, 3 semillas):**

| | Semilla 0 | Semilla 1 | Semilla 2 | Media | Niveles |
|---|---|---|---|---|---|
| v3 (base S3) | 0,678 | 0,619 | 0,590 | 0,629 | 7 · 7 · 7 |
| v4.1 | 0,542 | 0,618 | 0,046 | 0,402 | 7 · 7 · 8 |
| **v5** | **0,6785** | **1,065** | **0,803** | **0,849** | **8 · 8 · 8** |
| v5 sin explorar en el modelo (ablación) | 0,678 | 0,619 | 0,592 | 0,630 | 7 · 7 · 8 |

- **g50t:** v5 completa el nivel 1 en las **3 semillas**, con 1973, **61** y 113 acciones (la
  referencia humana es 78). v4.1 lo sacó en 1 de 3, con 1191.
- **La ablación** dice de dónde sale la mejora: **explorar en el modelo**. Sin eso, g50t vuelve a
  0 · 0 · 1.
- **Repetición:** 24 partidas repetidas, **0 diferencias** en acciones y fotogramas.

**Criterio:**

| Id | Condición | Resultado |
|---|---|---|
| G1 | niveles > 7 | ✅ 8 en cada semilla |
| G2 | puntuación oficial > 0,678 | ✅ media de 3 semillas 0,849 (lectura estricta propuesta). Con la lectura original de una semilla: 0,6785, que pasa por muy poco |
| G3 | repetición con 0 diferencias | ✅ |

**S4 verde en desarrollo.** Límites que declaramos:
- **Sobreajuste.** Las tres iteraciones se desarrollaron y midieron en los **mismos 8 juegos**, y la
  regla de los juegos con clic se decidió después de ver bp35 y m0r0. La prueba de verdad es el
  examen de ECHO-4.5 con 16 juegos no tocados.
- **Concentración.** La mejora viene de **un juego** (g50t), y la semilla 0 lo saca casi en el
  límite de acciones.
- **Modelo débil.** En g50t, el modelo acierta entre el 58 % y el 73 % de las predicciones. No
  modela la copia que repite mis movimientos (ACTION5). Visto al repetir la partida: la copia no se
  queda quieta donde la dejo, sino que **repite el camino grabado**.
- **Causas sin demostrar.** Se proponen y algunas se confirman (12 en la semilla 2), pero no hay
  ablación que demuestre que ayudan. No afirmamos que ECHO haya entendido la mecánica de g50t.
- **Sin cambios en** sk48 ni wa30 (0 niveles), y los juegos de clic son v3.

Datos: `lab/arc3/s4-it3/` (`v5f-r*`, `v5f-replay-r*`, `v5f-noexp-r*`, `run.sh`).
