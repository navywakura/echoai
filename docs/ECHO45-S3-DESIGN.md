# ECHO-4.5 · S3 (el juego como objetos) · contrato (fijado el 2026-09-25, antes de construir) y cierre: VERDE

Roger: «sigue con S3». Roadmap: `ECHO45-DECISIONES.md`. Se desarrolla y mide **solo** en los 8
juegos de desarrollo (bp35, g50t, lp85, m0r0, s5i5, sk48, su15, wa30). Los 16 juegos de examen de
ECHO-4.5 no se tocan.

## Qué construye S3

Un agente **v3** sobre ECHO v2, con cuatro piezas nuevas. Todo son hechos observados por ECHO,
nunca información del juego que no vea un humano.

1. **«Yo» por contingencia (BOUNDARY por objetos).** El objeto que se desplaza de forma consistente
   con cada tecla es el propio cuerpo. Medido antes de construir: se identifica en 5 de 5 juegos de
   teclas de desarrollo.
2. **Reglas de acción por objeto.** Qué desplazamiento produce cada tecla y cuándo queda
   **bloqueado** (el cuerpo no se mueve): el mapa de muros se aprende.
3. **Reloj del juego.** Las casillas que cambian solas paso a paso (marcadores de energía o de
   pasos, también fuera del borde) salen del estado y **nunca se tocan con un clic**. Motivo
   observado: en vc33, ECHO v2 hizo clic en la barra de energía.
4. **Clic dentro del objeto.** El objetivo de un clic es una casilla que **pertenece** al objeto,
   no su centro medio, que en un anillo o una L puede caer fuera.

Exploración: en los juegos de teclas, ECHO explora el **espacio de posiciones de su cuerpo** (qué
casillas ha visitado y qué movimientos quedan por probar), no todos los fotogramas posibles.

## Criterio (fijado antes de medir)

En los 8 juegos de desarrollo, con 2000 acciones por juego y la **puntuación oficial correcta**
(cada nivel al cuadrado y niveles ponderados):

| Id | Condición |
|---|---|
| G1 | puntuación oficial media de v3 **>** v2 (0,506) |
| G2 | niveles completados por v3 **≥** v2 (7) |
| G3 | la repetición de todas las partidas de v3 da 0 diferencias |

**S3 verde = G1 ∧ G2 ∧ G3.** La inferencia de metas es S4: aquí solo se mide si ver el juego como
objetos hace que ECHO gaste menos acciones y complete lo mismo o más.

## Cierre (2026-09-26): S3 VERDE con v3

8 juegos de desarrollo, 2000 acciones por juego, puntuación oficial correcta:

| Agente | Niveles | Puntuación oficial media | Repetición |
|---|---|---|---|
| v2 (base) | 7 | 0,506 | — |
| **v3: reloj del juego + clic dentro del objeto** | **7** | **0,678** | 8 partidas, 0 diferencias |
| v3b: v3 + «yo», reglas de acción, muros y exploración por posiciones | 7 | 0,678 | — |

**G1** (0,678 > 0,506) ✅ · **G2** (7 ≥ 7) ✅ · **G3** (0 diferencias) ✅ → **S3 verde**, con el agente
`Arc3EchoV3` de `echo_arc/agent.py`.

**Lo que no funcionó, declarado:**
- **Descubrir el cuerpo jugando:** en la prueba aparte salía en 5 de 5 juegos de teclas; jugando de
  verdad sale en 3 (g50t, wa30, bp35). Falla en **m0r0**, que tiene dos cuerpos iguales en espejo y
  el detector los descarta por ambiguos, y en **sk48**.
- **Explorar el espacio de posiciones sin meta no suma niveles.** En wa30 reduce la variedad de lo
  explorado (313 fotogramas distintos frente a 1838): ECHO da vueltas por el mismo sitio.
- **Lectura:** saber quién eres y dónde están los muros solo sirve con una **meta**. El módulo v3b se
  conserva y pasa a S4, donde se usará para planificar el camino hacia la meta. Los cuerpos
  múltiples se arreglarán allí.
