# E4-BENCH-ARC3-LLM · un modelo de lenguaje juega ARC-AGI-3, con y sin ECHO — contrato (APROBADO por Roger el 2026-09-24)

2026-09-24. Aprobado por Roger el 2026-09-24. Contratos previos: `ECHO4-BENCH-ARC3-DESIGN.md`
y `ECHO4-BENCH-ARC3-D-DESIGN.md`. Los resultados de ECHO solo (`ECHO4-BENCH-ARC3-RESULTS.md`)
son **referencia**, no la pregunta.

## Pregunta

¿Un modelo de lenguaje completa más niveles de ARC-AGI-3 cuando juega **con ECHO** que cuando
juega solo? El modelo es el que juega; ECHO le da percepción, memoria verificada y ejecución.

## Brazos (mismo modelo, mismos juegos, mismo presupuesto)

| Brazo | Qué recibe el modelo en cada llamada | Qué puede devolver |
|---|---|---|
| **L** | la rejilla 64×64 en texto, las acciones permitidas y lo que pasó con su última jugada (como la plantilla oficial de agentes LLM) | una secuencia de hasta 16 acciones |
| **L+P** | lo mismo que L, más la **percepción** de ECHO: la lista de objetos (color, tamaño, posición) y qué cambió | lo mismo que L |
| **L+ECHO** | lo mismo que L+P, más la **memoria de ECHO**, marcada como HECHO (visto por ECHO) o HIPÓTESIS (dicho por el modelo): <br>– qué objetos mueve cada acción y cuáles se mueven solos (BOUNDARY); <br>– qué acciones no hacen nada y cuáles acabaron la partida; <br>– cuántos estados conoce y cuáles quedan por probar; <br>– las reglas que propuso el modelo y si la experiencia las confirmó o las refutó | lo mismo que L, más dos órdenes para ECHO: `explore(n)` (ECHO explora n acciones por su cuenta) y `goto(estado)` (ECHO vuelve a un estado conocido por el camino más corto) |

- **L+P** es el control, como **M+R** en el bloque A: si L+ECHO solo gana a L pero empata con
  L+P, la mejora venía de describir mejor la pantalla, no de la memoria ni de la verificación.
- **Cortafuegos:** una regla que propone el modelo **nunca** se guarda como hecho. Solo pasa a
  «confirmada» si la experiencia de ECHO la respalda.
- Se registra cuántas acciones decidió el modelo y cuántas ejecutó `explore`, para que se vea si
  el modelo juega o solo delega en ECHO.

## Presupuesto por juego (igual para los tres brazos)

- **60 llamadas al modelo** y **como mucho 2000 acciones**.
- Temperatura 0, sin razonamiento extendido y sin herramientas.
- Referencias ya medidas, sin coste: ECHO v2 solo (13 niveles) y RANDOM (2 niveles de media).

## Modelo y coste

- **Qwen3-30B-A3B-Instruct-2507** por OpenRouter. Es de la familia del Qwen local de ECHO y el
  más barato de los que ya medimos (≈0,08 $ por millón de tokens en el desarrollo del bloque A).
- **Cálculo:** unos 5000 tokens por llamada × 60 llamadas × 3 brazos.
  - Desarrollo, 8 juegos: ≈0,6 $.
  - Examen, 16 juegos: ≈1,2 $.
  - **Total: ≈2 $** de los 7,87 $. Tope duro con `--budget-usd 2.5`: si se alcanza, el bloque
    se para y se publica lo que haya.
- Un modelo más fuerte (GPT-5.4 mini, DeepSeek) costaría unas 10 veces más. Queda fuera de este
  bloque.

## Método

Contrato → aprobación → desarrollo con los 8 juegos de desarrollo (ajuste de los textos de
cada brazo) → contrato D con umbrales → aprobación → examen con los 16 juegos de examen →
auditoría.
- **Recibos:** cada llamada guarda el texto enviado, la respuesta y su coste. Cada partida guarda
  sus acciones y la huella de cada fotograma.
- **Auditoría:** repite las acciones en el entorno local sin llamar al modelo y recalcula
  todos los números a partir de los recibos.

## Umbrales propuestos para D (se fijan antes del examen)

| Id | Condición | Tipo |
|---|---|---|
| D1 | niveles de L+ECHO > niveles de L | principal: ECHO mejora al modelo |
| D2 | niveles de L+ECHO > niveles de L+P | principal: no es solo mejor percepción |
| D3 | la auditoría da 0 diferencias | custodia |
| D4 | niveles de L+ECHO frente a ECHO v2 solo (13) | se informa: ¿el modelo aporta algo sobre ECHO? |

**Verde = D1 ∧ D2 ∧ D3.** La puntuación oficial se publica siempre, sin umbral.

## Qué no afirma

- Nada sobre el conjunto privado ni sobre el premio ARC.
- Nada sobre modelos más fuertes que Qwen3-30B-A3B.
- Si D4 sale peor que ECHO solo, se publica tal cual: significaría que el modelo estorba.

## Desarrollo (2026-09-25, `lab/arc3/llm-dev-v1`, 8 juegos de desarrollo)

| Brazo | Niveles | Coste |
|---|---|---|
| L (Qwen solo) | 0 | 0,16 $ |
| L+P (con la percepción de ECHO) | 0 | 0,18 $ |
| L+ECHO | **2** (lp85 1 con puntuación 12,5; su15 1 con 0,43) | 0,20 $ |

- **Total: 0,54 $.** Auditoría por repetición: 24 partidas, 0 diferencias.
- **Comportamiento visto:**
  - Qwen solo repite casi siempre la misma tecla 16 veces, con reglas inventadas distintas en
    cada llamada.
  - Con ECHO, el modelo decide la gran mayoría de las acciones: `EXPLORE` fue entre 0 y 110 de
    unas 950 por juego. No es ECHO jugando solo.
- No se ajustaron los textos tras el desarrollo: el arnés se congela tal cual.

## Contrato D (APROBADO por Roger el 2026-09-25, antes del examen)

- **Arnés congelado:** `lab/arc3/llm-exam-v1/arc3_llm-v1.py`, sha256
  `2ad09a5ca70dee0e530d816430d619c6ad2d5ef96d690bbcae53416e271b3168`.
- **Examen:** los 16 juegos de examen × 3 brazos. Mismo modelo y presupuesto que en el
  desarrollo. Coste esperado ≈1,1 $, con suelo de crédito en 5,37 $.
- **Umbrales:** D1, D2 y D3 tal como están arriba. Verde = D1 ∧ D2 ∧ D3.
- **Si D1 y D2 empatan a 0**, es rojo: ECHO no ayudó a este modelo en este examen.
