# E4-BENCH-1 A · el mismo modelo con y sin ECHO — contrato

2026-09-24. Plan general: [ECHO4-BENCH1-PLAN.md](ECHO4-BENCH1-PLAN.md).

## Pregunta

Con **el mismo modelo**, ¿la capa de verificación de ECHO reduce las respuestas inventadas
en preguntas de hechos? ¿Y ese efecto se debe al cortafuegos de ECHO, y no solo a darle al
modelo más información?

## Qué hace ECHO aquí (su mecanismo, no un truco nuevo)

La regla de siempre: **VERIFY exige extracto; sin extracto, DESCONOCIDO.**

- ECHO busca en Wikipedia **él mismo** y guarda los extractos como hechos en su CAM, con
  su huella y su procedencia.
- La respuesta del modelo es una **hipótesis**.
- ECHO la acepta solo si uno de **sus** extractos la contiene. Si no, responde «no lo sé».
- ECHO **no añade conocimiento**: solo puede quitar respuestas, nunca crear una correcta
  nueva. Esto se comprueba como propiedad estructural.

## Brazos (SimpleQA)

| Brazo | Qué es | Para qué |
|---|---|---|
| **M** | el modelo solo (libro cerrado) | línea base |
| **M+R** | el modelo con los **mismos** extractos que obtiene ECHO, sin cortafuegos | separa el efecto de «más información» del efecto de ECHO |
| **M+R+ECHO** | la respuesta de M+R pasada por el cortafuegos de ECHO | el tratamiento |
| **Trivial** | un agente que dice siempre «no lo sé» | control: abstenerse siempre da 0 errores y no vale nada |

M+R+ECHO usa la **misma respuesta** que M+R: la única diferencia es el cortafuegos.

## Métricas (las oficiales de SimpleQA)

Cada respuesta se clasifica como **correcta**, **incorrecta** o **no intentada**. Con eso
se calculan:
- el % de incorrectas, que es la métrica principal;
- la precisión cuando responde;
- el F-score oficial.

Se publican todas, también las que empeoren: abstenerse más baja la cobertura, y eso es un
coste real.

## Control negativo

Una muestra de MMLU-Pro con los mismos brazos. Se espera:
- que ECHO **no suba** los aciertos, algo que la construcción ya impide;
- que muestre el coste de abstenerse cuando no encuentra evidencia.

GSM8K (matemáticas) se mide solo como M frente a M+ECHO, que no tiene forma de verificar
cálculos. Se espera que se abstenga, y lo publicamos como límite.

## Muestras y método

- **Desarrollo:** 50 preguntas de SimpleQA, para ajustar la búsqueda y la verificación.
- **Examen:** 200 preguntas **distintas**, fijadas por semilla antes de ejecutar, más 100
  de MMLU-Pro y 50 de GSM8K.
- **Umbrales:** se fijan en un contrato D aparte, **después** del desarrollo y **antes**
  del examen.
- **Recibos:** cada respuesta del modelo y cada extracto de Wikipedia se guardan con su
  huella. La auditoría reconstruye todo **sin volver a llamar** al modelo ni a Wikipedia,
  como en SITUATE-2.
- **Corrector:** SimpleQA usa oficialmente un corrector basado en un LLM (GPT-4o). Aquí:
  ver la decisión 2.
- **Gráficas** (matplotlib), listas para rxlabs.org:
  - barras de correctas, incorrectas y no intentadas por brazo;
  - precisión frente a cobertura;
  - coste en tiempo y llamadas con y sin ECHO.

## Decisiones (2026-09-24)

- **Dónde corre el modelo:** OpenRouter, con su clave (BYOK), leída de `~/.config/openrouter/key`.
  La clave nunca aparece en recibos, salidas ni documentos.
- **Modelos** (cada uno se compara consigo mismo, con y sin ECHO; no es un ranking entre
  modelos). IDs de OpenRouter, fijados antes del desarrollo:
  - `qwen/qwen3-30b-a3b-instruct-2507`, la misma familia «2507» que el Qwen3-4B local;
  - `google/gemini-3.5-flash`;
  - `anthropic/claude-sonnet-5`;
  - `openai/gpt-5.4-mini`;
  - `deepseek/deepseek-v4.1-flash`.

  Coste estimado de desarrollo más examen: unos 3 $ en total.
- **Corrector:** determinista, con coincidencia normalizada; declarado como más estricto que el oficial.

### Opciones que se le presentaron

1. **Dónde corre el modelo.** Qwen3-4B en esta CPU va a ~4 tokens/s. El examen completo
   llevaría **~8–10 horas** en local (de noche). La alternativa es OpenRouter con tu clave:
   minutos y unos céntimos.
2. **Corrector.**
   - Determinista: coincidencia normalizada con la respuesta oficial. Es reproducible, pero
     más estricto que el oficial.
   - LLM: más fiel al protocolo oficial, pero necesita una API.

## Qué no afirma

- Que ECHO haga más inteligente al modelo: no puede, por construcción.
- Nada fuera de SimpleQA, MMLU-Pro y GSM8K en esta fase. AgentDojo y SWE-bench van en
  B y C.

## Datos y muestras congelados (antes del desarrollo)

- **Archivos oficiales** (Hugging Face), con su sha256:
  - SimpleQA `basicv8vc/SimpleQA`, `simple_qa_test_set.csv`: `feee3f7e…`;
  - GSM8K `openai/gsm8k`, `main/test`: `ee7b8da9…`;
  - MMLU-Pro `TIGER-Lab/MMLU-Pro`, `data/test`: `0e24a191…`.
- **Muestras** por semilla 20260924, en `lab/echo4/bench1-data/samples.json`, sha256
  `a068c4f5db9223107f2c435a2664d3e86375a679f59d0d155f745e9e1f3b6238`:
  - **desarrollo:** 50 preguntas de SimpleQA, 20 de MMLU-Pro y 10 de GSM8K;
  - **examen:** 200 de SimpleQA, 100 de MMLU-Pro y 50 de GSM8K;
  - desarrollo y examen son disjuntos. Las preguntas del examen no se miran hasta el examen.
- **Declarado:** el desarrollo incluye 20 preguntas de MMLU-Pro y 10 de GSM8K, además de las
  50 de SimpleQA previstas, solo para comprobar que el banco funciona.

---

# E4-BENCH-GENERAL · benchmarks frontera (PLAN, aprobado en parte por Nav el 2026-09-24)

**Estado:**
- Nav aprueba **MMLU + HLE + FrontierScience**, **ARC-AGI-2** (como prueba real de si
  ECHO sube la puntuación), **ARC-AGI-3** y **Opus 5.5 vía Claude Code**.
- Queda fuera por ahora: el piloto de SWE-bench.
- **No se gasta nada todavía:** A también espera. Primero el plan.

2026-09-24. Pedido por Nav: los benchmarks que usa toda la industria, con el mismo método
que A (el mismo modelo con y sin ECHO), vía OpenRouter y, para código, el servidor MCP de
E4-CODE-1. **No sustituye a A: se añade.**

## La regla honesta

ECHO no sabe más ni razona mejor que el modelo. En estos benchmarks se mide dónde **no**
ayuda (controles) y dónde **sí** puede ayudar (verificar antes de afirmar o de actuar).
Se publica todo.

| Benchmark | Qué mide | Qué hace ECHO | Qué esperamos |
|---|---|---|---|
| **MMLU** (`cais/mmlu`) | conocimiento académico en 57 áreas | cortafuegos con evidencia de Wikipedia, como en A | control negativo: no sube los aciertos; puede subir la precisión y bajar la cobertura |
| **Humanity's Last Exam** (`cais/hle`, con acceso condicionado) | preguntas de nivel frontera | el mismo cortafuegos; casi nunca encontrará evidencia | control: mostrará sobre todo abstención; interesa la precisión cuando responde |
| **FrontierScience** (`openai/frontierscience`) | ciencia de olimpiada (100) y de investigación (60) | el mismo cortafuegos | control, como HLE |
| **ARC-AGI-2** (`arcprize/ARC-AGI-2`, evaluación pública) | abstracción y razonamiento nuevo | **verifica** los programas que propone el modelo ejecutándolos sobre los ejemplos resueltos, y le devuelve la contradicción (ver «ARC-AGI-2 con ECHO») | **la prueba de verdad** de si ECHO sube la puntuación |
| **ARC-AGI-3** (juegos interactivos) | descubrir reglas jugando | el núcleo de ECHO juega (percibir, predecir, actuar, aprender), solo o con córtex | ver «ARC-AGI-3» |
| **SWE-bench Verified** | arreglar incidencias reales de GitHub | **sí**: el agente con el MCP de E4-CODE-1 (verifica los tests antes de decir «arreglado» y vigila los comandos) | la prueba de verdad del producto: incidencias resueltas, **falsos «arreglado»** y comandos bloqueados |

## Correctores

- **MMLU:** la letra, de forma determinista.
- **HLE y FrontierScience-olimpiada:** coincidencia normalizada, solo en las preguntas de
  respuesta exacta o de opción múltiple. Las de respuesta libre necesitan un juez LLM: se
  declaran fuera o, opcionalmente, con juez y su coste aparte.
- **FrontierScience-investigación:** se corrige con rúbrica y un juez LLM (opcional).
- **ARC-AGI-2:** coincidencia exacta de la rejilla.
- **SWE-bench:** el arnés oficial en Docker.

## Presupuesto estimado (OpenRouter, precios del 2026-09-24; los 5 modelos juntos) — *primera versión, reemplazada por el presupuesto actualizado de más abajo*

**Supuestos:**
- Gemini 3.5 Flash y DeepSeek-V4.1-Flash **razonan por defecto**, medido el 2026-09-24:
  unos 290–380 tokens ocultos por pregunta corta, y muchos más en preguntas difíciles.
- En Gemini no se puede desactivar. Se usan todos los modelos tal como vienen.
- Gemini es, con diferencia, el más caro de los cinco.

| Bloque | Muestra | Coste estimado (5 modelos) |
|---|---|---|
| **A** (ya aprobado): SimpleQA + MMLU-Pro + GSM8K | desarrollo 80 + examen 350 | **≈ 5 $** (3–7) |
| MMLU | 500 | ≈ 5 $ (3–7) |
| Humanity's Last Exam (solo texto) | 200 | ≈ 13 $ (8–25) |
| FrontierScience-olimpiada | 100 | ≈ 7 $ (4–15) |
| ARC-AGI-2 (evaluación pública), solo el brazo M | 120 | ≈ 17 $ (10–30); con los brazos de ECHO, ver abajo |
| **Subtotal sin SWE-bench** | | **≈ 42 $ (25–75)** |
| SWE-bench Verified, **piloto** | 20 incidencias × 2 brazos × 2 modelos | ≈ 10–40 $ |
| SWE-bench Verified, completo | 50 incidencias × 2 brazos × 5 modelos | ≈ 100–250 $ |

**SWE-bench, además del dinero:**
- necesita Docker y unos 100 GB de disco;
- tarda **muchas horas** en este portátil, por el arnés de evaluación;
- conviene empezar por el piloto.

**Opus 5.5 (opcional), dos vías:**
- **OpenRouter** (4 $ / 20 $ por millón de tokens): unos 1,5 $ en A, 10–20 $ en GENERAL
  sin SWE-bench, y 60–190 $ en SWE-bench completo.
- **Claude Code con la suscripción de Nav:** 0 $ adicionales, pero consume su cuota.
  Iría en **sesiones sin interfaz separadas** (`claude -p`), nunca en la conversación que
  desarrolla ECHO: esa sesión no debe ver las preguntas del examen.

## Orden propuesto

1. A: desarrollo y examen.
2. MMLU + HLE + FrontierScience.
3. ARC-AGI-2.
4. Piloto de SWE-bench.
5. SWE-bench completo, si el piloto lo justifica.

Cada bloque tiene su contrato D con umbrales, su examen y su auditoría, como siempre.


## ARC-AGI-2 con ECHO: la prueba de verdad

**Idea:** en ARC cada tarea trae **ejemplos resueltos** (entrada → salida). Es la misma
situación que en DREAM: el modelo **propone** y el núcleo **comprueba contra lo vivido**.

- El modelo propone una **transformación como programa**, `transform(grid)`. Es una hipótesis.
- ECHO la **ejecuta él mismo** sobre todos los ejemplos resueltos. Si reproduce todas las
  salidas, la hipótesis queda **verificada** (VERIFY = observación propia). Si falla, ECHO
  le devuelve al modelo en qué ejemplo y en qué celdas falló (contradicción), y el modelo
  vuelve a proponer, hasta *k* intentos.
- Solo se envía una respuesta **verificada**. Si ninguna lo está, ECHO no inventa.

| Brazo | Qué es | Para qué |
|---|---|---|
| **M** | el modelo responde la rejilla directamente | línea base oficial |
| **P** | el modelo escribe un programa, sin verificar, 1 intento | separa el efecto de «pensar en código» |
| **P×k** | *k* programas sin verificar, con el mismo presupuesto de llamadas; se envía el último | separa el efecto de «más intentos» |
| **P×k+ECHO** | *k* intentos con verificación y retroalimentación de ECHO | el tratamiento |

- **Métrica oficial:** acierto con 2 intentos por salida de prueba (pass@2), sobre las 120
  tareas de la evaluación pública.
- **Además:** la precisión de los programas verificados (¿aciertan la prueba cuando pasan
  los ejemplos?) y el coste por tarea.
- **Seguridad:** el código del modelo es ajeno y se ejecuta **aislado**:
  - solo una función `transform` sobre listas;
  - análisis previo del código, sin importaciones, archivos, `exec` ni atributos internos;
  - un proceso aparte con límites de CPU y memoria, sin red y con tiempo máximo.
- **Qué esperamos, sin inflarlo:** ARC-AGI-2 es muy difícil y los modelos puntúan bajo.
  Si ECHO ayuda, será porque **filtra hipótesis falsas y devuelve la contradicción**, no
  porque sepa más. Si P×k empata con P×k+ECHO, lo publicaremos: significaría que el efecto
  viene de los intentos, no de la verificación.

## ARC-AGI-3: juegos interactivos (el mundo natural de ECHO)

ARC-AGI-3 son **juegos por turnos** (repositorio oficial `arcprize/ARC-AGI-3-Agents`,
licencia MIT; entornos que pueden ejecutarse en local). El agente ve fotogramas (rejillas
de colores), hace acciones (`ACTION1…7`, incluido clic) y tiene que **descubrir las reglas
jugando**. Se mide cuántos **niveles completa** y con cuántas acciones.

Es lo que ECHO hace desde ECHO-1: percibir, predecir las consecuencias (T), decidir (Q),
aprender del error (δ) e intervenir para saber qué depende de él (BOUNDARY).

| Brazo | Qué es |
|---|---|
| **Aleatorio** | el agente de referencia oficial |
| **LLM** | un modelo de lenguaje juega solo (plantilla oficial) |
| **ECHO solo** | el núcleo de ECHO juega **sin modelo de lenguaje**: fotograma → WSP → CAM/T/Q/gate |
| **ECHO + córtex** | el modelo propone reglas («creo que el bloque azul abre la puerta»); ECHO las **verifica actuando** y solo se cree las que se confirman |

**Qué hay que construir:**
- un codificador de fotograma a WSP: objetos, colores y posiciones en una rejilla de 64×64;
- la correspondencia con las acciones;
- el bucle de juego con recibos.

Es una fase grande: prácticamente ECHO-4 en un mundo nuevo. Va **después** de ARC-AGI-2.

**Necesita:** una clave de ARC-AGI-3 (`ARC_API_KEY`, de arcprize.org/platform), o bien los
entornos locales del paquete oficial.

**Qué esperamos:** no lo sabemos, y por eso es interesante. Es el primer banco externo en
el que ECHO **sin modelo de lenguaje** puede competir.

## Opus 5.5 vía Claude Code (suscripción de Nav)

- Se ejecuta en **sesiones sin interfaz separadas** (`claude -p`), **sin herramientas**,
  con salida JSON y un recibo por llamada. La conversación que desarrolla ECHO **nunca**
  ve las preguntas del examen.
- **Declarado:** Claude Code añade su propio prompt de sistema y su entorno de agente. No
  es exactamente el mismo modelo «desnudo» que por API. Se compara consigo mismo (con y sin
  ECHO), nunca en ranking frente a los modelos por API.
- **Coste:** 0 $ adicionales, pero consume la cuota de la suscripción.

## Presupuesto actualizado (sin gastar nada todavía)

| Bloque | Estado | Coste estimado |
|---|---|---|
| A: SimpleQA + MMLU-Pro + GSM8K (5 modelos) | aprobado, en espera | ≈ 5 $ (3–7) |
| MMLU + HLE + FrontierScience (5 modelos) | aprobado | ≈ 25 $ (15–45) |
| ARC-AGI-2 con los 4 brazos (120 tareas, 5 modelos, *k* = 4) | aprobado | ≈ 60–130 $ |
| ARC-AGI-2 reducido (60 tareas o 3 modelos) | alternativa | ≈ 30–65 $ |
| ARC-AGI-3: brazo ECHO solo | aprobado | 0 $ |
| ARC-AGI-3: brazos LLM y ECHO+córtex (1–2 modelos) | aprobado | ≈ 10–40 $ |
| Opus 5.5 vía Claude Code | aprobado | 0 $ (cuota de la suscripción) |
| **Total aprobado** | | **≈ 100–220 $**, o **≈ 70–150 $** con ARC-AGI-2 reducido |

**Orden:**
1. A.
2. MMLU + HLE + FrontierScience.
3. ARC-AGI-2.
4. ARC-AGI-3.

Cada bloque tiene su contrato D con umbrales, su examen y su auditoría. **Antes de gastar en
cada bloque, Nav da la orden.**
