# CRECE F2 v4 · restaurar la información exigida por el método

21/10/2026. Corrige una omisión de implementación detectada antes de la
segunda generación de v3: el §4 del método exige mostrar al LLM las piezas
rechazadas con sus motivos y lo que hicieron las piezas activas. F2 estaba
enviando `previous=None` y omitía los eventos del enchufe de las fichas.
La omisión favorece repetir una propuesta sin conocer su rechazo; no prueba
por sí sola por qué el modelo eligió esa propuesta. V3 se conserva incompleta,
con código exacto, recibos y marca de interrupción. Ningún examen abierto.

Se hereda [v3 Groq](B4-CRECE-F2-PROTOCOLO-V3-GROQ.md), y por ella el diseño,
controles, población de sorteo y puerta de v1. Cambios fijados antes de v4:

- Las solicitudes crece y sin_relevo reciben todas sus propuestas previas
  rechazadas (máximo cuatro), fuente y hash, identidad de su campeón, resultado
  mecánico y motivo derivado de la puerta. Se dan deltas globales de éxito y
  daño y motivos de regresión, **sin nombres de familias ni semillas**.
  Un fallo API no se presenta como rechazo del código. Un rechazo sigue
  siendo contextual: no se prohíbe para siempre ese código.
- La ficha incluye los eventos reales del enchufe en sus últimos 20 pasos;
  cada pieza activa se identifica por el mismo nombre/hash que sus eventos.
  El paso es el ordinal real de la acción (también en la traza), no el
  contador interno de decisiones. Enganches, efectos, acciones y ámbitos
  se serializan por sus nombres; el observador no cambia decisiones.
- sin_fichas mantiene API y ejemplos, sin episodios ni recibos de puertas.
  Por tanto, este control retira el conjunto de información empírica dado
  al modelo; no permite atribuir una diferencia exclusivamente a las trazas
  frente a los motivos de rechazo. Se declara este alcance de la comparación.
- Semillas nuevas: fórmulas de v1 con **b=300000000**. Artefactos nuevos:
  `lab/echo58/crece/f2-v4-feedback/`.

Sin cambios de modelo, temperatura, máximo de tokens, puertas, curva mínima,
generaciones, macros ni presupuesto: 30 propuestas, hasta 90 intentos HTTP,
separados al menos 60 segundos. El código propuesto no se edita a mano.
Si vuelve a haber cuota insuficiente, el protocolo queda técnicamente
incompleto; no se inventan intentos ni se transforma la espera en rechazo.

Esta corrección está dentro de la autorización de implementación de Nav.
No rebaja un umbral por un resultado medido. El lote confirmatorio de F3 y
el examen siguen pendientes de que el desarrollo pase su puerta.
