# E4-BENCH-1 — un modelo con ECHO frente al mismo modelo sin ECHO (PLAN)

2026-09-24. Pedido por Roger: demostrar con métricas, gráficas y benchmarks oficiales en
qué mejora un LLM cuando se conecta a ECHO. **Es un plan, no un contrato.** Los umbrales se
fijarán en un contrato aparte, antes de ver ningún resultado.

## La idea clave, sin adornos

ECHO **no es un modelo de lenguaje**. No sabe más historia, ni más matemáticas, ni programa
mejor. Por eso:

- En los benchmarks de **conocimiento o razonamiento puro** (MMLU-Pro, GPQA, GSM8K, MATH,
  HumanEval), ECHO **no debe mejorar nada**. Si sale mejor ahí, sospecharemos del banco.
  Los mediremos igualmente como **control negativo**: demuestran que no hacemos trampa y
  que ECHO no empeora al modelo.
- Donde ECHO **sí puede aportar** es en lo que mide su diseño:
  1. **No afirmar lo que no se ha verificado.** Si no hay evidencia, se abstiene.
  2. **Clasificar afirmaciones** en respaldadas, contradichas o inverificables (el cortafuegos).
  3. **No actuar sin verificar**: el gate, el veto y los recibos.
  4. **No obedecer instrucciones inyectadas**: el testimonio no es una orden.
  5. **Memoria con procedencia** que ni se borra ni se inventa.

## Benchmarks propuestos (todos públicos y usados por la industria)

| Qué mide | Benchmark | Métrica principal | Qué esperamos de ECHO |
|---|---|---|---|
| Alucinación en preguntas de hechos | **SimpleQA** (OpenAI, 2024) | incorrectas, no intentadas, F-score | **Menos incorrectas**, más «no lo sé». Hay que publicar el intercambio |
| Veracidad | **TruthfulQA** (MC1/MC2) | exactitud | Pequeña o nula; mide si el cortafuegos filtra mitos |
| Verificación de afirmaciones | **FEVER** (Supported / Refuted / NotEnoughInfo) | exactitud por etiqueta | Es exactamente la tarea del cortafuegos; la tabla más directa |
| Agente de código | **SWE-bench Verified** (a través de E4-CODE-1) | resueltos y **«arreglado» falso** | Mismos resueltos o algo más; **casi cero falsos «tests pasan»** |
| Inyección de instrucciones | **AgentDojo** | éxito del ataque frente a utilidad | **Menos ataques con éxito** con una utilidad parecida |
| Memoria larga | **LongMemEval** o **LoCoMo** | exactitud en memoria | Mejor recuperación y menos memorias inventadas |
| Control negativo | **MMLU-Pro** y **GSM8K** (muestra) | exactitud | **Igual** con y sin ECHO |

## Método (el mismo rigor que ECHO-4)

1. **Harness oficial**, no uno nuestro: **Inspect AI** (UK AI Security Institute) o
   **lm-evaluation-harness** (EleutherAI), con sus prompts y su puntuación.
2. **Mismo modelo, misma temperatura (0), mismos prompts y mismo presupuesto**. La única
   diferencia es la capa ECHO.
3. **Contrato previo**: muestra, semillas, umbrales e intervalos de confianza (bootstrap),
   fijados antes de mirar.
4. **Modelos**:
   - Locales: Qwen3-4B y Phi-3.5-mini (gratis, en CPU y lentos).
   - Por API (**OpenRouter**, con una sola clave): un modelo pequeño y uno de frontera.
5. **Todo se publica**:
   - las salidas crudas, como un dataset en Hugging Face;
   - los recibos;
   - el coste en tokens y la latencia **con y sin** ECHO: ECHO añade llamadas y tiempo, y
     eso también se mide;
   - las gráficas en rxlabs.org: barras con intervalos, curva de abstención frente a
     exactitud, tasa de ataques y coste.
6. **Si un benchmark sale en rojo, se publica.** No se eligen solo los que salen bien.

## Qué hay que construir antes (y por qué aún no hay números)

- El cortafuegos actual solo entiende **afirmaciones sobre ECHO mismo** (los átomos de
  SITUATE-2). Para SimpleQA y FEVER hace falta:
  - un **extractor de afirmaciones** (lo hace el LLM; su salida es hipótesis);
  - una **fuente verificable**: un volcado local de Wikipedia o una búsqueda con recibo;
  - que ECHO decida respaldada, contradicha o desconocida con esa evidencia.
- Para SWE-bench y AgentDojo hace falta **E4-CODE-1**: el servidor MCP con
  `verify_claim`, `check_action` y `receipts`, que ejecuta los tests antes de aceptar un
  «arreglado».

Orden propuesto:
1. **E4-CODE-1 A**: el servidor MCP local; es también la «API local» para Claude Code,
   Codex u OpenRouter.
2. **E4-BENCH-1 A**: FEVER y SimpleQA con Qwen3-4B, más el control negativo.
3. **E4-BENCH-1 B**: API con dos modelos y AgentDojo.
4. **E4-BENCH-1 C**: SWE-bench Verified, una muestra fijada de antemano.

## Qué no se afirmará

- Que ECHO hace «más inteligente» a un modelo.
- Nada fuera de lo medido.
- Nada sin su intervalo, su coste y sus rojos.
