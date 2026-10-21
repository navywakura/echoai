# E4-BENCH-ARC3-LLM2 · el modelo resuelve ARC-AGI-3 usando ECHO como laboratorio — contrato

2026-09-25. **Segunda versión** del bloque con modelo de lenguaje, declarada **después** de ver
el examen de la primera (`ECHO4-BENCH-ARC3-LLM-RESULTS.md`). Idea de Nav: el que resuelve es
el modelo, y tiene que aprender a usar las capacidades de ECHO-4 como ayuda.

## Qué se aprendió de la v1

- Qwen3-30B no deduce las reglas: pasó de 0 a 4 niveles con ECHO solo porque delegó en
  `EXPLORE`.
- ECHO solo completa 13 niveles.
- Hace falta un modelo capaz de deducir reglas, y que ECHO le sirva para **comprobarlas**, no
  solo para explorar en su lugar.

## Modelos (Nav: «los dos»)

| Modelo | Vía | Coste |
|---|---|---|
| **Claude Opus 5.5** | Claude Code sin interfaz (`claude -p`) en modo limpio: sin herramientas, sin ajustes, sin servidores MCP y sin comandos. Solo ve nuestro texto (comprobado: 467 tokens de entrada en una llamada de prueba). | 0 $ (cuota de la suscripción de Nav) |
| **GPT-5.4 mini** | OpenRouter, temperatura 0 | ≈5 $, con suelo de crédito |

Cada modelo se compara **solo consigo mismo**, nunca en ranking con el otro.

## Brazos (para cada modelo)

| Brazo | Qué tiene el modelo |
|---|---|
| **L** | la rejilla en texto, lo que hicieron sus últimas acciones, sus **propias notas** (las escribe él y le vuelven en la llamada siguiente, sin verificar) y su **manual propio** (ver «Aprendizaje») |
| **L+ECHO** | todo lo de L, más ECHO como laboratorio (ver abajo) |

Los dos brazos tienen memoria propia y el mismo tipo de aprendizaje. **La única diferencia es
ECHO.**

## ECHO como laboratorio (solo en L+ECHO)

1. **Hechos:** percepción por objetos y lo que ECHO ha visto: qué mueve cada acción, qué no
   hace nada, qué acabó la partida y qué se mueve solo. Todo marcado como HECHO.
2. **Prueba de reglas:** el modelo escribe una regla y una predicción comprobable:
   - `change` / `no_change` / `level_up` / `game_over`;
   - `moves <color> <dx> <dy>`: algún objeto de ese color se desplaza así.

   ECHO ejecuta las acciones y marca la regla **CONFIRMADA** o **REFUTADA**. Las reglas y su
   historial pasan de un nivel al siguiente. Una regla del modelo **nunca** se convierte en
   HECHO; solo acumula confirmaciones.
3. **Historial de capacidades, con los números del propio juego:** cuántos niveles y cambios
   lograron las jugadas del modelo y cuántos `EXPLORE`. Así el modelo sabe de qué es capaz ECHO.
4. **Órdenes:** `EXPLORE n` (ECHO explora por su cuenta) y `GOTO sK` (volver a un estado
   conocido).

## Aprendizaje sin tocar pesos

- Al terminar cada juego de desarrollo, el propio modelo escribe **5 lecciones**: en L, sobre
  cómo jugar; en L+ECHO, sobre cómo jugar y cómo usar ECHO.
- Las lecciones de los 8 juegos de desarrollo se juntan en un **manual por modelo y brazo**, de
  como mucho 2000 caracteres, recortado por orden. Se congela con su sha256 antes del examen.
- **No se ajustan pesos.** Si el examen sale verde, las partidas buenas podrán servir después
  para reentrenar un modelo propio (otro bloque).

## Presupuesto por juego (igual en todos los brazos y modelos)

- **30 llamadas** al modelo y como mucho 2000 acciones. Hasta 16 acciones por llamada.
- **Opus:** esfuerzo `low` para contener el tiempo y la cuota. Se declara.
- **GPT-5.4 mini:** sin razonamiento extendido.

**Coste de GPT-5.4 mini** (≈0,005 $ por llamada):
- desarrollo, 8 juegos × 2 brazos × 30 llamadas: ≈1,2 $ (incluidas las lecciones);
- examen, 16 × 2 × 30: ≈4,8 $;
- suelo de crédito: 0,30 $.

**Esto gasta prácticamente todo el saldo (6,22 $). El examen A queda sin fondos hasta que se
recargue.**

**Opus:** unas 1500 llamadas en total. Puede tardar horas y chocar con el límite de uso de la
suscripción. Si se corta, se reanuda donde quedó; las partidas terminadas se guardan.

## Método

Contrato → aprobación → desarrollo con los 8 juegos de desarrollo (y escritura del manual) →
contrato D → aprobación → examen con los 16 juegos → auditoría por repetición.

## Umbrales que se propondrán en D

| Id | Condición | Tipo |
|---|---|---|
| D1 | niveles de L+ECHO > niveles de L, **para cada modelo** | principal |
| D2 | la auditoría da 0 diferencias | custodia |
| D3 | quién completó cada nivel: jugada del modelo o `EXPLORE` | se informa |
| D4 | L+ECHO frente a ECHO solo (13 niveles) y puntuación oficial | se informa |

La v1 queda publicada tal cual. Esta v2 no la sustituye.

## Aprobación (Nav, 2026-09-25): «GPT solo en 8 juegos»

- **Opus 5.5:** desarrollo con los 8 juegos de desarrollo; examen con los 16.
- **GPT-5.4 mini:** desarrollo con 4 juegos de desarrollo y examen con 8 juegos de examen,
  elegidos por semilla (`sha256(juego + "llm2-gpt")`, los 8 primeros) antes de ver nada:
  - desarrollo: bp35, g50t, sk48, su15;
  - examen: cn04, dc22, r11l, re86, tn36, tr87, tu93, vc33.
- **Coste esperado de GPT:** ≈3,6 $. Suelo de crédito: 2,40 $.
- **Las lecciones** (una llamada extra al final de cada juego de desarrollo) no cuentan dentro de
  las 30 llamadas.
