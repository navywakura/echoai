# ECHO-4.5 · S5 (ARC3-GYM: simulador propio de juegos) · contrato (fijado el 2026-09-26, antes de medir)

Roger: «ve y haz S5». Roadmap (`ECHO45-DECISIONES.md` §5): «solo hay 8 juegos de desarrollo y sin
él se sobreajusta».

## Por qué S5 ahora

S4 salió verde en desarrollo, pero con un límite declarado: sus tres iteraciones se desarrollaron y
midieron en los **mismos 8 juegos**. S5 construye juegos nuevos, generados por código, para:
1. comprobar si lo que ganó S4 **generaliza** a juegos que el agente nunca vio;
2. tener un banco donde **ajustar sin tocar** los juegos de desarrollo ni los de examen.

## Qué es ARC3-GYM (`echoai/seed/arc3gym.py`)

- **Juegos por turnos** de 64×64 píxeles y 16 colores, con las mismas acciones y la misma interfaz
  que ARC-AGI-3. `echo_arc.runner.play` los juega **sin cambios**.
- **Siete familias de mecánicas**, fijadas aquí. Se inspiran en tipos de juego comunes (laberintos,
  interruptores, empujar cajas, luces), **no** en copiar los juegos de desarrollo:

  | Familia | Acciones | Mecánica |
  |---|---|---|
  | K1 laberinto | teclas | llegar a la meta evitando muros |
  | K2 interruptor | teclas | pisar el interruptor abre la compuerta; después, la meta |
  | K3 palanca | teclas + ACTION5 | ACTION5 sobre la palanca abre la compuerta |
  | K4 caja | teclas | empujar una caja hasta su casilla |
  | C1 luces | clic | encender todas las luces (hay objetos que no hacen nada) |
  | C2 flechas | clic | cuatro flechas mueven un cuerpo hasta la meta |
  | M1 mixto | teclas + clic | clic en el interruptor abre la compuerta; con las teclas, a la meta |

- **Cada juego:**
  - colores al azar, así que las reglas de color se tienen que **aprender**, no memorizar;
  - tamaño de casilla de 3 a 6 píxeles;
  - 5 niveles de tamaño creciente;
  - barra de energía en el borde. Si se acaba, GAME OVER y se repite el nivel.
- **Solucionador exacto** (búsqueda en anchura sobre el estado del juego):
  - cada nivel se genera **solo si tiene solución**;
  - en K2, K3 y M1, solo si **no** tiene solución sin la causa (la compuerta cerrada);
  - la referencia de acciones de cada nivel es el **mínimo exacto**. Es más duro que la referencia
    humana de ARC-AGI-3.
- **Particiones fijas:**
  - **gym-train:** semillas 0–39 (40 juegos);
  - **gym-test:** semillas 1000–1059 (60 juegos).

## Criterio (fijado antes de medir)

2000 acciones por juego, 3 semillas del agente por juego, puntuación con la fórmula oficial.

| Id | Condición |
|---|---|
| V1 | validez: el 100 % de los niveles tiene solución; el mismo juego generado dos veces da los mismos fotogramas; `runner.play` juega los 100 juegos sin errores |
| V2 | no trivial: el azar completa **< 15 %** de los niveles de gym-test y el solucionador, el 100 % |
| V3 | S4 generaliza: en gym-test, v5 **>** v3 en niveles **y** en puntuación oficial media (3 semillas) |
| V4 | sirve para ajustar: la variante de v5 elegida **solo** con gym-train supera a v5 en gym-test **y no baja** de 0,849 de media en los 8 juegos de desarrollo |

**S5 verde = V1 ∧ V2 ∧ V3 ∧ V4.** Si sale rojo, se publica igual, diciendo qué falló.

## Límites declarados

- Las familias las diseñó quien diseñó v5. Para reducir ese sesgo:
  - se fijan en este contrato **antes** de medir;
  - mezclan juegos de teclas, de clic y mixtos;
  - no se cambian después de ver resultados.

  Aun así, un simulador propio **no sustituye** al examen con los 16 juegos oficiales no tocados.
- La referencia de acciones es el óptimo, no un humano: las puntuaciones del gym no se comparan
  con las de ARC-AGI-3.

## Variantes para V4 (fijadas el 2026-09-26, antes de medir en gym-train)

Solo parámetros de clase, con `runner --agent "v5:ATTR=N"`:

| Variante | Cambio |
|---|---|
| A | v5 tal cual |
| B | `MIN_EVIDENCE=4`: encontrar el «yo» con menos pruebas |
| C | `BABBLE=2`: probar cada tecla dos veces al empezar |
| D | `WALL_MIN=2`: un color es muro con 2 choques en lugar de 3 |
| E | `WARMUP=15`: aprender el reloj del juego en 15 pasos en lugar de 30 |
| F | `MAX_PER_TARGET=120`: más paciencia por objetivo |

Se elige la de mayor puntuación oficial media en gym-train (3 semillas). En caso de empate, gana A.

## Resultados (2026-09-26) — ROJO según el contrato; el gym cumplió su función

Datos: `lab/seed/arc3gym/` (`v{1,2}-{train,test}-AGENTE-r{0,1,2}/summary.json`, `run.sh`). Juegos de
desarrollo: `lab/arc3/s4-it3/v51C-r*`.

**Gym v1 (el contratado)**
- **V1 ✅:** 100 juegos y 500 niveles, todos resueltos por el solucionador. La generación es
  determinista.
- **V2 🔴:** el azar completa el **27 %** de los niveles de gym-test (el límite era 15 %). Los
  niveles eran demasiado fáciles.

**Gym v2 (declarado después de ese rojo; mismas familias)**
- Niveles más grandes, soluciones de al menos 8 acciones, barra de energía de 2× el óptimo + 10, y
  luces que también cambian las vecinas.
- **V1 ✅:** 500 de 500.
- **V2 ✅:** el azar completa el **4,9 %**.

**V3 (v5 frente a v3 en gym-test, 3 semillas):**

| Agente | Gym v2: niveles | Gym v2: puntuación | Gym v1: niveles | Gym v1: puntuación |
|---|---|---|---|---|
| azar | 14 · 16 · 14 | 0,01 | 81 · 81 · 74 | 0,32 |
| v3 | 206 · 193 · 201 | 1,12 | 260 · 270 · 277 | 3,90 |
| v5 (S4) | 169 · 164 · 157 | 1,28 | 208 · 210 · 218 | 4,19 |

**V3 🔴 en los dos gyms:** v5 puntúa algo más, pero **completa menos niveles** que v3.

**Qué encontró el gym** (depurado **solo en gym-train**; gym-test no se miró para corregir):
1. **v5 toma el suelo por su cuerpo.** Cuando el cuerpo se mueve, el agujero que deja desplaza un
   píxel el centro del suelo con cada tecla, así que la evidencia basada en centros no los distingue.
   Arreglo: «yo» tiene que moverse **rígido** (las mismas celdas, trasladadas).
2. **La hipótesis de meta se leía del nivel nuevo** (heredado de v4) y podía ser el suelo; el agente
   la perseguía para siempre. Arreglo: se lee del fotograma anterior a ganar, nunca con el color más
   común de la zona de juego ni con un color de muro.

Los 8 juegos de desarrollo no mostraban ninguno de los dos fallos. Es el sobreajuste que S4 declaraba
como riesgo.

**v5.1** (`Arc3EchoV51`, los dos arreglos) y **V4**: variantes fijadas antes de medir, elegidas en
gym-train v2:

| Variante (sobre v5.1) | Niveles en gym-train | Puntuación en gym-train |
|---|---|---|
| A tal cual | 141 · 159 · 152 | 9,28 |
| B `MIN_EVIDENCE=4` | 146 · 157 · 166 | 10,18 |
| **C `BABBLE=2`** | 148 · 161 · 167 | **10,39** ← elegida |
| D `WALL_MIN=2` | 144 · 153 · 155 | 9,39 |
| E `WARMUP=15` | 142 · 159 · 153 | 9,27 |
| F `MAX_PER_TARGET=120` | 143 · 164 · 152 | 9,27 |
| v5 | 101 · 115 · 122 | 0,68 |
| v3 | 146 · 150 · 162 | 1,12 |

**v5.1 C en gym-test y en desarrollo:**

| | Gym v2: niveles | Gym v2: puntuación | Gym v1: niveles | Gym v1: puntuación | Desarrollo (media de 3 semillas) |
|---|---|---|---|---|---|
| v5.1 C | 192 · 190 · 179 | **7,74** | 272 · 272 · 284 | **9,61** | **0,926** (8 · 7 · 8 niveles) |

- **V4 ✅:**
  - supera a v5 en gym-test v2 (7,74 frente a 1,28, y más niveles);
  - no baja de 0,849 en desarrollo (0,926).
- **Por familias (gym v2, test):** v5.1 C resuelve **todos** los laberintos (K1: 5,0 niveles de 5
  frente a 4,5) con **7,6 veces** la puntuación de v3. **Pierde** en las familias de causa (K2
  interruptor 1,8 frente a 2,5; K3 palanca 1,2 frente a 2,5) y en K4 caja (0,5 frente a 0,8). La
  exploración a ciegas de v3 pisa el interruptor por casualidad más a menudo. El módulo de causas de
  v5 no lo compensa.

**Veredicto S5:** V1 ✅, V2 🔴 en v1 y ✅ en v2 (versión declarada), **V3 🔴**, V4 ✅. **S5 rojo según
el contrato.**

Lo que sí deja S5:
- un simulador válido y difícil (gym v2);
- dos fallos reales de v5 corregidos sin tocar los juegos de desarrollo ni los de examen;
- un agente, v5.1 C, que **puntúa 6,9 veces más que v3** en juegos nuevos, pero completa ~4 % menos
  niveles;
- una lista precisa de lo que falta: **causas** (interruptor, palanca) y **empujar**.

**Aviso sobre S4:** el v5 con el que S4 salió verde tenía estos dos fallos. La puntuación de S4 en
desarrollo sigue siendo válida (es lo que se midió), pero S5 muestra que no generalizaba tan bien
como sugería.

## Iteración de causas (2026-09-26): v5.2 — VERDE en las versiones declaradas

Depurado **solo en gym-train v2** (juegos de interruptor y palanca donde v5.1 no pasaba ningún
nivel). Agente `Arc3EchoV52` (`runner --agent v5.2`), sobre v5.1 con `BABBLE=2`:

1. **Una causa se confirma al repetirla:** si al volver al mismo sitio el mundo cambia igual, la
   hipótesis queda confirmada. Antes la prueba empezaba un paso tarde y se refutaba sola.
2. **Lo que ya sé que abre el camino, lo hago primero** en cada intento (después de un GAME OVER),
   y luego exploro lo nuevo. Antes las causas solo se usaban si ya se conocía la meta.
3. **Un salto no enseña muros:** después de un reinicio, el cuerpo «salta» al inicio y v5 lo
   contaba como un movimiento de la tecla, así que aprendía que los muros se podían atravesar.
   Ahora solo cuenta un desplazamiento igual a la regla de la tecla.
4. **Tocar y probar:** al pisar un objeto de un color no probado, pulsa allí las teclas de acción.

**Resultados (3 semillas):**

| | Gym v2 test: niveles | Gym v2 test: puntuación | Gym v1 test: niveles | Gym v1 test: puntuación | Desarrollo |
|---|---|---|---|---|---|
| v3 | 206 · 193 · 201 | 1,12 | 260 · 270 · 277 | 3,90 | 0,629 (7 · 7 · 7) |
| v5 | 169 · 164 · 157 | 1,28 | 208 · 210 · 218 | 4,19 | 0,849 (8 · 8 · 8) |
| v5.1 C | 192 · 190 · 179 | 7,74 | 272 · 272 · 284 | 9,61 | 0,926 (8 · 7 · 8) |
| **v5.2** | **237 · 228 · 216** | **10,01** | **271 · 282 · 280** | **10,09** | **0,960 (8 · 8 · 8)** |

Por familias (gym v2 test, niveles/5):

| | laberinto | interruptor | palanca | caja | luces | flechas | mixto |
|---|---|---|---|---|---|---|---|
| v3 | 4,5 | 2,5 | 2,5 | 0,8 | 5,0 | 4,4 | 2,8 |
| **v5.2** | **5,0** | **4,4** | **3,5** | 0,6 | 5,0 | 4,4 | 2,8 |

- **V3 (repetido con v5.2):** ✅ en los dos gyms. v5.2 completa **más niveles** que v3 (227 frente
  a 200 de media en v2; 278 frente a 269 en v1) y puntúa **9 veces más** en v2.
- **V4 (con v5.2):** ✅. Supera a v5 en gym-test y en desarrollo sube a **0,960**, con 8 niveles
  en cada semilla.
- **Repetición en desarrollo:** 24 partidas, 0 diferencias.

**Veredicto:**
- **S5 sigue ROJO según el contrato original**, porque el v5 contratado no generalizaba y el gym
  v1 era demasiado fácil.
- **Con las versiones declaradas después de los rojos (gym v2 y v5.2), todas las condiciones
  V1–V4 se cumplen.**
- Todo lo corregido se encontró en gym-train; gym-test y los juegos de desarrollo solo se usaron
  para medir.

**Límites:**
- **Caja (K4):** sin resolver. Ningún agente planifica empujes; los niveles salen por azar, tras
  unas 1500 acciones.
- **Juegos con clic:** C1, C2 y M1 usan el comportamiento de v3, sin cambios.
- **sk48 y wa30** siguen en 0 en desarrollo.
- **El gym lo diseñamos nosotros,** y v5.2 se ajustó en gym-train. La prueba de verdad sigue
  siendo el examen con los 16 juegos oficiales no tocados.

## Después de S5-D: caja y juegos de clic (2026-09-26) — v5.6

Encargo de Roger: «mejora la caja y los juegos de clic en el gym». Todo se desarrolló **solo en
gym-train v2**; gym-test y los 8 juegos de desarrollo solo se usaron para medir.

| Versión | Qué añade | Resultado en gym-train |
|---|---|---|
| v5.3 | modelo del cuerpo también en juegos con clic | **descartada**: mejora el mixto del gym, pero en desarrollo bp35 pierde su nivel en las 3 semillas y m0r0 cae en una |
| v5.4 | **empujar**: un objeto que se mueve rígido conmigo cuando lo piso es «empujable»; plan en el modelo (mi cuerpo + el objeto, muros como colores) para llevarlo a cada candidato; el color que gana queda como meta | caja 0,5 → **4,5** niveles |
| v5.5 | **clics que son teclas**: si hacer clic en un objeto quieto mueve otro objeto siempre igual, ese clic es una tecla, y se usa todo el modelo del cuerpo | flechas 4,4 → **5,0** niveles, muchos al óptimo |
| v5.6 | **modelo de clics**: efecto de cada clic píxel a píxel; los píxeles que cambian juntos son una unidad; al ganar, «todas las unidades en un color» es la meta; después, plan en el modelo | luces: puntuación 0,7 → **9,3** |

Fallos encontrados por el camino y corregidos:
- el plan de empuje se descartaba para siempre si se intentaba antes de conocer todas las teclas;
- la barra de energía se tomaba por un objeto del mundo (se excluye el borde: BOUNDARY);
- el efecto del clic ganador se medía contra el nivel nuevo;
- una causa se borraba al subir de nivel mientras se probaba (fallo antiguo de v5).

**Medición (3 semillas):**

| | Gym v2 test: niveles | Puntuación | Desarrollo (media) |
|---|---|---|---|
| v3 | 206 · 193 · 201 | 1,12 | 0,629 |
| v5.2 | 237 · 228 · 216 | 10,01 | 0,960 |
| **v5.6** | **277 · 270 · 258** | **21,45** | **1,033** (9 · 8 · 8 niveles; lp85 llega a 4 en una semilla) |

Por familias (gym v2 test, niveles/5 · puntuación):

| | laberinto | interruptor | palanca | caja | luces | flechas | mixto |
|---|---|---|---|---|---|---|---|
| v5.2 | 5,0 · 45,8 | 4,4 · 5,2 | 3,5 · 0,2 | 0,6 · 0,0 | 5,0 · 0,5 | 4,4 · 0,3 | 2,8 · 0,0 |
| v5.6 | 5,0 · 45,8 | 4,4 · 5,2 | 3,5 · 0,2 | **4,5 · 18,1** | 4,9 · **10,0** | **4,7 · 42,3** | 2,8 · 0,0 |

**Límites:**
- el mixto sigue en v3, porque v5.3 empeoraba los juegos reales;
- la palanca va a 3,5 de 5;
- en luces se pierde un nivel de vez en cuando (4,9);
- v5.6 no ha pasado por un examen congelado como S5-D. Sus cifras son de gym-test, que ya se había usado para medir v5.2.

## Gym v3 (estado oculto) y v5.7 (2026-09-26/27)

A partir de la revisión externa de Roger: los juegos profundos tienen estado que no se ve. **ARC3-GYM
v3** añade cuatro familias ocultas, y los v1 y v2 quedan idénticos (400 juegos comparados antes y
después):
- **H1:** orden de dos interruptores;
- **H2:** compuerta con temporizador;
- **H3:** tres entradas al interruptor;
- **H4:** una copia idéntica que repite tu camino tras la tecla 5, como en g50t. Su referencia es una
  cota superior: ir al interruptor, pulsar 5 e ir a la meta.

**Punto de partida (gym-test v3, niveles/5):**

| Agente | Total | H1 | H2 | H3 | H4 |
|---|---|---|---|---|---|
| azar | 7 | 0,1 | 0,0 | 0,2 | 0,1 |
| v3 | 38 | 0,4 | 1,1 | 0,9 | 0,2 |
| v5.6 | 123 | 1,2 | 5,0 | 2,0 | 0,2 |

**v5.7** (`Arc3EchoV57`, desarrollado solo en gym-train v3):
- **Tecla de reinicio:** si una tecla de modo me lleva siempre al mismo sitio, es un reinicio. Solo
  se pulsa a propósito (tocar y probar) o cuando ya no queda nada que explorar, y nunca durante 40
  pasos tras una prueba.
- **Identidad con gemelos:** «soy el cuerpo que está donde predice MI movimiento». Si estoy pegado
  a mi copia (una sola mancha de mi color), estoy en las celdas que predice mi movimiento.
- **Un gemelo quieto no es la meta** si tengo una tecla que deja copias de mí.
- **Lo que funcionó viaja:** los colores cuya prueba cambió algo a distancia se vuelven a probar en
  cada nivel y después de cada GAME OVER.
- **Juegos con clic:** sin cambios.

**Resultados (3 semillas):**

| | gym-train v3: niveles | H4 (niveles/5) | Desarrollo (media) | g50t |
|---|---|---|---|---|
| v5.6 | 104 · 117 · 103 | 0,6 | 1,033 | 3/3 semillas (1973, 61 y 113 acciones) |
| v5.7 | 117 · 133 · 119 | **2,7** | 1,000 | 2/3 semillas (**59** y **59** acciones) |

**Lectura:**
- v5.7 resuelve mucho mejor la copia en el gym.
- En el g50t real **gana en menos acciones, pero pierde una semilla**, así que la media de
  desarrollo baja un poco (1,033 → 1,000).
- H1 (orden) y H3 (contar) siguen sin módulo propio.
- **Pendiente:** medir v5.7 en gym-test v3 y decidir el agente para el examen congelado S5-E.

**v5.7 en gym-test v3 (juegos no usados para ajustar, 3 semillas):**

| | Niveles | Puntuación | H1 | H2 | H3 | H4 |
|---|---|---|---|---|---|---|
| v3 | 38 · 34 · 41 | 0,18 | 0,4 | 1,1 | 0,9 | 0,2 |
| v5.6 | 127 · 118 · 124 | 3,13 | 1,2 | 5,0 | 2,0 | 0,2 |
| **v5.7** | **173 · 158 · 163** | **4,86** | 1,2 | 5,0 | 2,0 | **2,9** |

**Actualización 2026-09-27: S5-E cerrado VERDE.** En 60 juegos v3 nuevos y tres
reps, v5.7 logra 475 niveles frente a 399 de v5.6; puntuación 3,7604 frente a
2,2658. Solucionador 300/300, azar 4,1 %, fuentes intactas y replay exacto.
Los 76 niveles adicionales son de H4; orden y conteo no cambian.
[Contrato](ECHO45-S5-E-DESIGN.md) · [Resultados](ECHO45-S5-E-RESULTS.md).
