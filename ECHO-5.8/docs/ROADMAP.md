# ECHO-5.8 · roadmap oficial: poner en verde lo que falló

20 de octubre de 2026. Estado: **PLAN APROBADO el 20/10/2026**
(orden A → B → C; D y E en paralelo). Nada de lo que sigue está implementado
salvo donde se dice; cada pista necesita su contrato antes de medir. Sustituye como
marco general al roadmap candidato WSP del 17/10
(`echoai-pcworld1/docs/research/wsp58-20261017/ROADMAP.md`), que pasa a ser
la pista W de este documento sin cambiar su contenido.

## 0. Regla de la versión

Un rojo histórico **sigue rojo**. 5.8 no rebaja umbrales ni reabre contratos
cerrados: cada intento es un contrato nuevo, con nombre nuevo, predicciones
escritas antes de medir, control que pueda ganar y revisor independiente.
Si un intento sale rojo, 5.8 lo publica y aprende qué *no* sirve. Que ECHO
no valga para algo es un resultado válido.

Invariantes intactos: WSP 16 B, 0 FPU en el paso rápido, CAM `destroyed == 0`,
testimonio nunca es hecho, nada nuevo bajo `nexus0/`, córtex apagado en los
bancos del núcleo.

## 1. Inventario de rojos y abiertos (20/10)

| # | Qué falló | Dónde | Número |
|---|---|---|---|
| R-a | Automejora del selector (S6) | ECHO-4.5, B3…B24 | B7: ECHO 537 = FIJO 537; ninguna campaña promueve |
| R-b | Mejora recursiva (RSI-1) | banco DSL sintético | recursivo 99/144 = sin acumular 99; azar 101 |
| R-c | Memoria compartida entre agentes | 5.1 SWE-bench | 0 lecciones publicadas, 0 recuperadas |
| R-d | Memoria entre juegos/mundos | ARC, 5.5 | no existe; E1 (libro de efectos, por partida) 39,06 vs 48,00 |
| R-e | LLM + ECHO en tareas difíciles | 5.1, 5.5 F2, 4.5 R2/R3 | SWE 1/24 vs 2/24; ARC F2 E1–E3 dentro del ruido (banda 10,03); ARC-2 0/120; ARC-3 11 vs 13/112 |
| R-f | Especialistas / multiagente | 5.1 brazos S/I2/F/E | sin ventaja (2/24 vs 1/24) |
| R-g | EGO-MEMORIA condición 2 | ECHO-4.5 | M5 15/16 (la 3E es verde) |
| R-h | Identidad perceptiva | PATTERN-1R | ~~cerrado rojo~~ **corrección 20/10: v4 VERDE el 14/09** en SITL (4591/4866 identidades, 45 confundidas, 230 desconocidas; v1–v3 rojos conservados). Abierto: aprende por *replay*, no en vuelo autónomo; solo dos paredes → pista P |
| R-i | DYNAMIC-1 v2 | ECHO-3 | ~~sin congelar~~ **corrección 20/10: ya VERDE el 14/09** (`docs/DYNAMIC1-V2-RESULTS.md`); no es deuda |
| R-j | Búsqueda | ECHO-5.0 | 6 agotamientos de presupuesto sin resolver |
| R-k | Coste del veto en retorno | SHIELD-1 | P5a/P5b rojos (65 %, 57 %); CarGoal2 5/50 episodios sobre presupuesto, causa sin analizar |
| R-l | Gridworlds sin daño visible | SHIELD-1 G4 | 5 entornos idénticos a ECHO-Q |
| R-m | Hardware real | DRONE-3 HIL/jaula, Akida | falso: no hay placa ni montaje |
| R-n | Deudas de publicación | ECHO-4.5, ARC | 4.5 sin cerrar ni publicar (HF pendiente); 2 envíos finales ARC antes del 1/11 |

## 2. Diagnóstico: por qué fallan

He agrupado los rojos por causa. Es una lectura mía de los resultados, no una
medida.

**C1 · Proponer sin saber por qué se falla (R-a, R-b).** Las propuestas
(LLM o gramática) se generan sin un diagnóstico medido del fallo y se juzgan
en un banco pequeño y ruidoso. Por eso el azar empata o gana. PROBE2 es la
excepción que lo confirma: sus dos reglas buenas salieron de trazas de fallo
concretas.

**C2 · Memoria que solo aprende de éxitos y se guarda en prosa (R-c, R-d,
R-g).** En 5.1 los donantes no resolvieron nada y no hubo lección que
publicar. En ARC el conocimiento entraba como texto en el prompt y costaba
tokens y caché. Lo que **sí** transfirió (SHIELD-1, TRANSFER-3, operadores de
5.0) era pequeño, entero, verificado por consecuencias y tenía una clave que
existe igual en el mundo nuevo.

**C3 · ECHO compite con un LLM fuerte en el terreno del LLM (R-e).** Cuando el
modelo ya razona bien, lo que ECHO le añade es redundante y paga tokens.
Además, en ARC el ruido entre corridas iguales (10 puntos) es mayor que
cualquier efecto plausible de una pieza. Donde ECHO sí aportó fue en
**vetar** (SHIELD-1, LINK-3), no en resolver.

**C4 · Más agentes con el mismo cerebro y el mismo presupuesto (R-f).**
Repartir un modelo en especialistas solo divide el gasto. Un enjambre aporta
cuando sus agentes ven **cosas distintas** y lo juntan.

**C5 · Deudas de ingeniería y de decisión (R-i, R-j, R-k, R-n).** No son
problemas de la idea: falta tiempo, un análisis o un sí de Nav.

**C6 · Falta de material (R-m).** Sin compra, no hay medida.

## 3. ¿Vale la pena?

| Causa | ¿Vale la pena en 5.8? | Por qué |
|---|---|---|
| C2 memoria entre mundos | **Sí, primero** | Es el patrón que ya funcionó; CPU, sin dinero; si sale verde desbloquea C1 y C4 |
| C1 automejora | **Sí, pero rehecha** | Solo sobre la memoria de C2 y con propuestas nacidas de fallos medidos; S6 tal como era se cierra |
| C4 enjambre | **Sí, después de C2** | Tiene sentido cuando hay memoria que compartir; LINK-3 ya protege frente al mentiroso |
| C5 deudas | **Sí, son baratas** | Horas, no semanas |
| C3 LLM+ECHO por puntuación | **No como carrera de puntos** | El efecto esperado está por debajo del ruido; se cambia la pregunta: ECHO como **veto** de un agente LLM, donde ya ganó |
| C6 hardware | **No en 5.8** | Bloqueado por compra |

Conclusión: **sí vale la pena**, siempre que 5.8 apueste por lo que ECHO hace
bien (aprender consecuencias, vetar, acumular memoria entera) y deje de
pedirle que haga mejor que un LLM lo que el LLM ya hace.

## 4. Pistas y puertas

Orden: A → B → C; D, E y P corren en paralelo en huecos de CPU; W según su propio
roadmap. Ninguna pista toca la campaña ARC antes del 1/11.

### A · MEMORIA-X: memoria de consecuencias entre mundos (ataca R-c, R-d, R-g)

> **20/10/2026: VERDE en examen.** «Se mueve solo ⇒ daña» y puerta/llave transfieren; la lava en A2 y el rol de ASG no; P5 falsa. `docs/MEMORIAX-RESULTS.md`.

- **Qué:** una memoria persistente en disco, append-only y con recibos. Cada
  entrada guarda el **rol** de algo, no su identidad: «tocar X reinicia»,
  «esta acción no cambia nada», «esto se mueve solo», «esto abre algo»,
  «esto duele». La clave es un símbolo WSP abstracto que significa lo mismo en
  otro mundo. Aprende también de los fallos. Una entrada solo actúa cuando su
  cota inferior de evidencia la sostiene (la misma idea que el
  `(k − isqrt(n))·100 ≥ 50n` de SHIELD-1).
- **Mundos:** familias distintas para entrenar y examinar. Candidatas que ya
  están instaladas: MiniGrid/BabyAI (ECHO-5.0), AI Safety Gridworlds y
  Safety-Gymnasium (SHIELD-1). Se fija cuál es entrenamiento y cuál examen
  antes de medir.
- **Brazos:** memoria vacía · memoria aprendida · **memoria barajada**
  (mismas entradas, claves permutadas) · referencia sin ECHO.
- **Puerta (a fijar con números en el contrato):** en la familia de examen,
  la memoria aprendida supera a la vacía **y** a la barajada en pasos hasta la
  meta o en daño, con semillas reservadas y diferencias pareadas. Si la
  barajada empata, no hay transferencia y la pista es roja.

### B · ACUMULA: automejora sobre la memoria (ataca R-a, R-b)

> **20/10/2026: v1 ROJA en examen** (Q1 racha 2 < 3; Q2 y Q3 pasan: sonda 0 daños frente a ~30 de los controles, familias de A daño 85 → 0). Todo el daño de la sonda estaba en una familia → curva en escalón. Siguiente: B v2. `docs/ACUMULA-RESULTS.md`.
> **20/10/2026: B v2 cerrada ROJA en desarrollo** (sin examen): con rondas estacionarias ECHO corrige todos sus errores de memoria en la ronda 1 (311 → 34 fallos) y gana a todos los controles, `lote_final` incluido (51 frente a 127), pero no hay segunda ni tercera mejora: lo que queda son límites de la política base. `docs/ACUMULA2-DEV-NOTE.md`. **Siguiente: investigación B v3** (cómo actúa ECHO y por qué se atasca), `docs/B3-INVESTIGACION.md`.

> **20/10/2026: prototipo B v3 en desarrollo** (sin contrato ni examen): menú de memoria + piezas de política genéricas propuestas desde señales de sus fallos. Sonda 267 → 118 → 84 → 63 → 38 → 39 (4 mejoras seguidas; daño 173 → 0); piezas rechazadas en r1 y aceptadas después. Pero «todas las piezas dadas desde r0» acaba igual (43): ECHO elige y ordena, las piezas las diseñé yo. Siguiente: contrato B v3 (pendiente de Nav). `docs/B3-INVESTIGACION.md` §6.

> **20/10/2026: B v3 (ACUMULA-3) VERDE en examen**, verificado independientemente: sonda 94,3 → 35,4 → 22,3 → 21,0 → 15,8 → 13,8 (5 mejoras seguidas, daño 58,6 → 0); gana a los 5 controles en 10/10 macros (p 0,00098, Holm); Q3 daño 78,3 → 0. Límites: `piezas_dadas` empata (13,3), las piezas las diseñó Claude; DynObsRandom5 empeora (91 → 103). B v1 y B v2 siguen rojas. **Con A y B verdes, ECHO-5.8 cumple §5.** `docs/ACUMULA3-RESULTS.md`.

- **Qué:** rondas 1…k. Al final de cada ronda ECHO propone cambios a sus
  propias reglas de memoria (umbrales, qué rol abrir, cuándo olvidar), pero
  **solo a partir de fallos medidos** en esa ronda. Un cambio entra si mejora
  en un banco de validación con las puertas de siempre.
- **Brazos:** ECHO recursivo · sin acumular · **propuestas al azar con el
  mismo número de intentos** · fijo.
- **Puerta:** la velocidad de aprendizaje en un mundo nuevo mejora en ≥ 3
  rondas seguidas y el brazo recursivo supera al azar. Es exactamente donde
  cayó RSI-1.
- **Requisito:** A en verde.

### C · ENJAMBRE: experiencia compartida (ataca R-f)

> **21/10/2026: C v1 (ENJAMBRE-1) VERDE en examen**, verificado independientemente (primer diseño cerrado en desarrollo; rediseño aprobado). 4 ECHO con memoria privada + global por WSP y ayuda: puntuación 691 frente a 920 sin global, 937 barajada, 989 sin privada, 1685 sin ayuda, 1866 aislados; gana 20/20 salvo barajada 19/20 y sin_privada 11 ganadas + 9 empates. Límites: la ayuda solo cuenta en los mundos de placa (sin ellos 445 = 445); la ventaja de la privada se concentra en 2 macros; los mundos y el protocolo de ayuda los diseñó Claude. Siguiente: C v2 con mentiroso (LINK-3). `docs/ENJAMBRE1-RESULTS.md`.

- **Qué:** N agentes ECHO en mundos **distintos** escriben en la misma
  memoria por WSP (pila LINK). Uno de ellos puede mentir.
- **Comparación justa:** a igual experiencia total, el enjambre no debe
  ganar por arte de magia. Lo que se mide es (1) tiempo de reloj hasta la
  misma calidad de memoria y (2) que el mentiroso no degrada la memoria más
  allá de un límite fijado (la jerarquía de riesgo de LINK-3 bajó su efecto
  de 181 a 1).
- **Requisito:** A en verde.

### D · CÓRTEX VIGILADO (replantea R-e)

- **D1, veto de agentes LLM.** Un agente LLM con herramientas, con y sin el
  gate de ECHO, en un banco de seguridad de agentes (AgentDojo o equivalente).
  Necesita un LLM gratuito: modelo local (llama-server en la CPU/iGPU) o una
  API gratuita; OpenCode no sirve fuera de su cliente.
- **D2, una línea de memoria al LLM.** Tras A, el LLM recibe pocas líneas de
  MEMORIA-X: sin memoria · memoria · memoria barajada.
- **ARC después del 1/11:** solo como D2 y con una banda de ruido medida
  antes; no más piezas sueltas sobre M2.

### E · DEUDAS BARATAS (R-i, R-j, R-k, R-n)

1. ~~DYNAMIC-1 v2~~ y ~~PATTERN-1R~~: los dos ya verdes el 14/09 (corrección 20/10). Lo que sigue de PATTERN es la pista P.
2. SHIELD-1: autopsia de los 5 episodios de CarGoal2 sobre presupuesto;
   MODIFY orientado a la meta para atacar P5 en un **SHIELD-2** nuevo.
3. ECHO-5.0: autopsia de los 6 agotamientos de búsqueda.
4. ECHO-4.5: decidir Hugging Face, cerrar y publicar con sus rojos.
5. ARC: los dos envíos finales antes del 1/11 (campaña 5.5, no 5.8).

### P · PERCIBE-X: identidad percibida + memoria de roles (desbloqueada el 20/10)

- **Por qué:** MEMORIA-X recibe identificadores opacos que le da el mundo.
  PATTERN-1R v4 ya produce identidades anónimas desde LiDAR (familias), pero
  aprende por *replay* y solo con dos paredes. Juntas cerrarían el hueco
  «percibo algo que no conozco → sé qué hace → actúo» sin nombres.
- **Qué (PLAN, sin contrato):**
  - **P1 · en vuelo:** PATTERN-1R aprendiendo en vuelo autónomo en SITL,
    no por replay. Puerta: la misma identidad del banco v4 sin degradarse
    más de lo que se fije en el contrato.
  - **P2 · más familias:** más de dos tipos de objeto por mundo; vigilar el
    colapso de familias (la trampa medida de v1).
  - **P3 · PERCIBE-X:** las familias de PATTERN como identificadores de
    MEMORIA-X en Gazebo/PX4 (un objeto que se mueve solo o que daña al
    acercarse). Brazos: memoria vacía, aprendida, barajada, e identidad por
    PATTERN frente a la identidad verdadera (techo).
- **Requisitos:** A verde (hecho). No toca hardware real. Usa el mismo
  SITL que ECHO-3 (sus locks pinchan código: enmiendas por sus cauces).

### W · WSP (roadmap del 17/10, sin cambios)

R1 contrato, R2 compresión justa (≥ 15 % frente al mejor JSON), R3 ARC
pareado después del 1/11 y solo si R2 pasa. La rama de audio de R4 ya está
cubierta por LINK-1/2/3.

### Aparcado

S6 en su forma antigua (lo sustituye B), ARC-2, la carrera de puntos de ARC
con piezas ECHO y hardware real (DRONE-3 HIL, Akida).

## 5. Qué sería «ECHO-5.8 verde»

A en verde, y además B **o** C en verde, con cada pista publicada con sus
números, sus controles y sus rojos. D, E y W suman pero no deciden la versión.
Si A sale roja, 5.8 se publica como resultado negativo y B y C no se abren.

## 6. Decisiones pendientes 

1. ~~Aprobar este roadmap~~: aprobado el 20/10/2026.
2. ~~Familias de mundos para A~~: fijadas en el contrato de MEMORIA-X (aprobado) y examinadas; A verde.
3. ~~Congelar DYNAMIC-1 v2~~: no hacía falta, ya estaba verde (corrección 20/10).
4. LLM para D1: Nav dio claves de Groq y Google AI Studio el 20/10 (en ficheros de su home; nunca en el repo). Probado: llamada a herramientas OK en gpt-oss-20b (Groq), gemma-4-31b-it, gemini-3.5-flash-lite y gemini-3.5-flash; gpt-oss-120b y qwen3.8-27b bloqueados en la organización de Groq. **Elegido por Nav el 20/10:** gemini-3.5-flash como modelo principal y gemma-4-31b-it como réplica de pesos abiertos; antes del contrato se mide la cuota gratuita de Google con una prueba pequeña.

## 7. Lo que queda al implementador

Formato exacto de la memoria en disco, símbolos de rol concretos, número de
semillas y tamaños de efecto de cada puerta (se fijan en el contrato de cada
pista, antes de medir), estructura de carpetas (`echoai/echo58/`,
`echoai/lab/echo58/`, nunca bajo `nexus0/`).
