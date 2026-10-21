# Propuesta: que el córtex (LLM) invente las piezas — nota de investigación

21 de octubre de 2026. **PLAN, sin contrato ni medida.** Propuesta de Roger:
«que ECHO genere sus mejoras llamando al LLM: que las piezas para corregirse
las invente el LLM (neocórtex)».

## 1. Por qué es la pregunta correcta

B v3 salió verde, pero con un límite declarado: las piezas de política las
diseñé yo (Claude) mirando trazas, y dárselas todas desde el principio acaba
igual (13,3 frente a 13,8). Lo que ECHO aportó fue **elegir, ordenar y
acumular**. Si un LLM inventa las piezas a partir de los fallos que ECHO
mide, el bucle se cierra sin un humano diseñando: ECHO mide y verifica, el
córtex propone. Es exactamente la arquitectura de CLAUDE.md (córtex lento que
genera hipótesis; núcleo rápido con firewall y veto).

## 2. Lo que ya sabemos (y por qué esto es distinto)

- **B v1 (examen):** `gpt-oss-120b` elegía ediciones **de un menú cerrado**
  con el mismo diagnóstico: daño final 22,9 frente a 0,0 de ECHO y 30,7 del
  azar (p = 0,18). **No mejor que el azar.**
- **RSI-1 / S6 (ECHO-4.5):** propuestas de LLM juzgadas en bancos pequeños:
  el azar empata o gana.
- **Diferencia ahora:** el LLM no elige de un menú; **escribe la pieza** a
  partir de **trazas concretas de fallo** (lo que funcionó en PROBE2 y en mi
  propia investigación de B v3), y la puerta estricta de B v2/B v3 ya existe.
  El riesgo es el mismo de siempre: que proponga cosas plausibles que no
  arreglan nada medible.

## 3. Diseño propuesto (B v4 · «PIEZAS-X»)

1. **Señal:** ECHO detecta fallos (las señales de B v3: `pickdrop`,
   `retoggle`, `blockdrop`, `idle`, y otras nuevas) y extrae **trazas cortas**
   del episodio fallido, solo con ids opacos y acciones (sin nombres de
   objetos ni de familias).
2. **Córtex:** el LLM recibe la traza y una API mínima y escribe una pieza
   como una **función pura y entera** sobre el estado del agente
   (`veto(intent, estado) → bool` o `prefer(candidatos, estado) → candidato`),
   en un subconjunto de Python validado por AST: sin imports, sin floats, sin
   bucles sin cota, sin E/S.
3. **Firewall:** la pieza es una **hipótesis**. No entra en la política hasta
   pasar la puerta estricta (5 semillas × 4 familias, sin aprender: el daño no
   sube, el éxito no baja y mejora estrictamente algo). Se guarda con su hash,
   el prompt y la respuesta (cacheados) como recibo. El córtex nunca escribe
   en CAM ni toca el gate, el firewall ni el stop.
4. **Rondas** como B v3: ECHO acumula las piezas aceptadas y vuelve a pedir
   donde siga fallando.

## 4. Controles (para que el resultado signifique algo)

| Brazo | Qué mide |
|---|---|
| **llm_trazas** | el bucle propuesto |
| llm_sin_trazas | el mismo LLM, mismo número de piezas, solo con la descripción del mundo: ¿sirven las trazas de ECHO? |
| llm_azar_aceptación | piezas del LLM aceptadas al azar en lugar de por la puerta: ¿sirve la verificación de ECHO? |
| piezas_claude | las 5 piezas de B v3 (techo diseñado por humano/Claude) |
| sin_piezas | solo ediciones de memoria (B v2) |
| azar_gramática | piezas generadas al azar por la misma gramática restringida |

**Predicción candidata:** `llm_trazas` < `llm_sin_trazas`, `azar_gramática` y
`sin_piezas` en fallos de sonda tras 5 rondas, con ≥ 3 mejoras seguidas; y
`llm_trazas` ≤ `piezas_claude` + margen fijado antes de medir. Que empate con
las piezas de Claude ya sería un buen resultado (mismo nivel sin humano).

## 5. Riesgos

1. **Ruido de LLM:** respuestas distintas con la misma traza. Mitigación:
   temperatura 0, caché por hash, varias semillas de prompt declaradas.
2. **Fuga de conocimiento:** el LLM sabe qué es MiniGrid. Mitigación: ids
   opacos, sin nombres, y una sonda con mundos propios (los de ENJAMBRE).
3. **Coste y cuotas:** gemini-3.5-flash y gemma-4-31b-it (elegidos para D);
   hay que medir la cuota gratuita. Unas 5 rondas × ~3 piezas × 10 macros ×
   2 brazos LLM ≈ 300–600 llamadas.
4. **Seguridad del código generado:** validación AST + intérprete restringido;
   nunca `exec` de código sin validar.
5. **Antecedente rojo:** B v1, RSI-1 y S6 dicen que el LLM no supera al azar
   eligiendo. Si aquí tampoco, se publica rojo.

## 6. Primer paso (mañana)

Prototipo de una sesión, solo desarrollo: 3 trazas de fallo reales de B v3 →
gemini-3.5-flash → 3–5 piezas → validador AST → puerta. Regla de parada: si
ninguna pieza del LLM pasa la puerta en desarrollo, no hay contrato.
