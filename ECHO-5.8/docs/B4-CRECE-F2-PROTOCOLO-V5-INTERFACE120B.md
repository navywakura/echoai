# CRECE F2 v5 · interfaz explícita y alternativa Groq 120b

21/10/2026. Protocolo de desarrollo fijado antes de sus llamadas o partidas.
Se ejecutará después de cerrar y archivar v4, con recibos independientes.
V4 lleva cuatro generaciones sin promociones de crece en ambas macros; por
tanto ya no puede alcanzar su puerta de dos mejoras consecutivas en cinco.
Su quinta generación y controles se terminan y su resultado se conserva.

## Motivo y alcance

Las propuestas observadas confunden en varios casos `DROP` (enganche) con
la acción de soltar, cuyo símbolo público es `DROP_ACTION`. Las trazas de la
política original usan el nombre histórico `DROP`. Aunque el prompt enumera
ambos símbolos, la traducción de la traza a la interfaz deja esa ambigüedad.
Se clarifica la presentación; no se corrige a mano ninguna pieza del modelo.

Además, la comprobación de disponibilidad ha actualizado el traspaso:
`openai/gpt-oss-120b` responde HTTP 200. Una petición con un prompt de
desarrollo existente, 2048 tokens/low, terminó con `stop` y AST válido
(5224 tokens de entrada, 323 de salida total). No se ha medido su rendimiento
ni instalado esa propuesta. Recibo: `groq-120b-code-probe/result.json`.

Esta versión prueba **la configuración completa**, con dos cambios a la vez.
Una diferencia frente a v4 no podrá atribuirse exclusivamente al modelo ni
exclusivamente al formato. Es desarrollo exploratorio, no examen ni una
comparación causal entre modelos. La autorización de Nav para corregir y
avanzar, manteniendo facturación y usando Groq, cubre este piloto acotado.

## Cambios fijados

- Modelo único `openai/gpt-oss-120b`, proveedor Groq, temperatura 0,
  `reasoning_effort=low`, `max_completion_tokens=2048`.
- En la ficha serializada, el primer campo de una intención histórica
  `DROP` se muestra como `DROP_ACTION`, igual que en la API. El resto de
  campos, orden y valores son los observados. La traza original y su hash
  se conservan; la observación no modifica decisiones ni resultados.
- Los efectos serializados también nombran esa acción `DROP_ACTION`.
  El prompt explica expresamente que `DROP` es el enganche y `DROP_ACTION`
  es la acción. La aclaración se incluye en todos los brazos con LLM,
  también sin_fichas. Se explicita además que `c.intent[1]` es una celda,
  `c.intent[2]` un id entero opaco y BAN recibe un id, conforme a la API ya
  existente. No incorpora una regla de corrección diseñada a mano.
- Semillas: las fórmulas de v1 con **b=400000000**. Directorio nuevo
  `lab/echo58/crece/f2-v5-interface120b/`. Se archivan las fuentes exactas de
  v4 antes de modificar código.

## Lo que se conserva y regla de cierre

Se hereda la información de rechazo y efectos de [v4](B4-CRECE-F2-PROTOCOLO-V4-FEEDBACK.md),
el régimen de API de [v3](B4-CRECE-F2-PROTOCOLO-V3-GROQ.md), y todas las puertas,
familias, tamaños, controles y reglas de sorteo de [v1](B4-CRECE-F2-PROTOCOLO.md).
Dos macros, cinco generaciones, siete brazos, 30 propuestas con LLM, hasta
90 intentos HTTP y al menos 60 segundos entre llamadas. Memoria persistente
fija y partidas emparejadas. Cada brazo conserva su presupuesto original.

La puerta sigue siendo un descenso estricto de fallos en dos transiciones
consecutivas de la sonda agregada. No se relajan daño, éxito por familia,
errores del runtime ni comprobación mecánica. Ninguna propuesta se reescribe
por un humano antes de evaluarla.

Un solo piloto adicional de esta configuración: si no supera desarrollo,
se publica como rojo y no se abre examen ni se inicia una búsqueda automática
de ajustes hasta obtener verde. Si pasa, F3 deberá fijar entrenamiento y
examen nuevos, con tamaño suficiente y revisión, antes de jugar la reserva.
Google/Gemma siguen pendientes por cuota; sus resultados no se imputan a
este modelo ni se mezclan con él. No se cambian facturación ni permisos.
