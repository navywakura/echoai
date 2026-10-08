# E4-BENCH-ARC3-LLM · resultados del examen (2026-09-25)

Contrato: `ECHO4-BENCH-ARC3-LLM-DESIGN.md` (D aprobado antes del examen).
- **Modelo:** Qwen3-30B-A3B-Instruct-2507, por OpenRouter.
- **Juegos:** los 16 de examen.
- **Presupuesto:** 60 llamadas y como mucho 2000 acciones por juego.
- **Arnés:** congelado en `lab/arc3/llm-exam-v1/arc3_llm-v1.py` (sha256 `2ad09a5c…`).

## Veredicto: VERDE según el contrato

| Id | Condición | Resultado |
|---|---|---|
| D1 | niveles de L+ECHO > niveles de L | 4 > 0 **VERDE** |
| D2 | niveles de L+ECHO > niveles de L+P | 4 > 1 **VERDE** |
| D3 | la repetición da 0 diferencias | 48 partidas, 0 **VERDE** |
| D4 (se informa) | L+ECHO frente a ECHO v2 solo | 4 frente a 13: **el modelo estorba** |

## Totales

| Brazo | Niveles (de 112) | Puntuación oficial media | Acciones del modelo / de ECHO | Coste |
|---|---|---|---|---|
| L (Qwen solo) | 0 | 0 | 14 998 / 0 | 0,33 $ |
| L+P (con la percepción de ECHO) | 1 (tn36) | **0,89** | 15 166 / 0 | 0,37 $ |
| L+ECHO | **4** (lf52 1, r11l 1, vc33 2) | 0,23 | 12 413 / 2088 | 0,41 $ |
| *ECHO v2 solo (referencia, sin modelo)* | *13* | *1,00* | *0 / todas* | *0 $* |
| *RANDOM (referencia)* | *2* | *1,09* | — | *0 $* |

Coste del examen: 1,11 $. Coste del bloque con el desarrollo: 1,65 $.

## Quién completó cada nivel (lo que hay que leer antes de citar el verde)

- **Examen, L+ECHO:** los 4 niveles los completó una acción de `EXPLORE`, es decir, ECHO
  explorando por orden del modelo. El modelo decidió cuándo delegar, pero **ninguna jugada
  suya completó un nivel**.
- **Examen, L+P:** el nivel de tn36 lo completó el propio modelo en 10 acciones, con puntuación
  14,3. Es la jugada más eficiente del bloque.
- **Desarrollo, L+ECHO:** un nivel lo completó `EXPLORE` (lp85) y otro el modelo (su15).

## Lectura honesta

- **Con ECHO, Qwen pasa de 0 a 4 niveles.** Es lo que pedía el contrato, y es verde.
- **El mecanismo no es que Qwen entienda mejor el juego.** Qwen aprende a pedirle a ECHO que
  explore, y es la exploración de ECHO la que completa los niveles.
- **ECHO solo completa 13 niveles; con Qwen al mando, 4.** Un modelo de este tamaño gasta la
  mayoría de las acciones en jugadas propias que no llevan a nada: **estorba**. Lo declaramos
  como el contrato pedía.
- **En la puntuación oficial, L+P (0,89) supera a L+ECHO (0,23).** Esa diferencia sale de un
  solo nivel en tn36.
- **Queda sin responder** si un modelo que de verdad infiera las reglas mejoraría con ECHO.
  Este bloque no lo mide: Qwen3-30B no infiere las reglas de estos juegos.

## Qué no afirma

- Nada sobre modelos más fuertes, sobre el conjunto privado de ARC-AGI-3 ni sobre el premio.
- La puntuación la calcula nuestro código con la fórmula publicada. No es una puntuación
  enviada a ARC Prize.

## Corrección (2026-09-25): la puntuación oficial estaba mal calculada

Con la fórmula de ARC Prize (cada nivel al cuadrado y niveles ponderados por su número), la
puntuación oficial es:
- **L:** 0,00 (antes 0);
- **L+P:** **0,22** (antes 0,89);
- **L+ECHO:** **0,005** (antes 0,23).

Los niveles y el veredicto (basado en niveles) no cambian. Ver `ECHO4-BENCH-ARC3-RESULTS.md`.
