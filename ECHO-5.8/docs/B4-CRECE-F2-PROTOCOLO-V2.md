# CRECE F2 v2 · corrección del presupuesto de salida

21/10/2026. Se fija antes de lanzar v2. Hereda íntegramente el diseño,
brazos, puerta, parada, repeticiones y análisis de
[F2 v1](B4-CRECE-F2-PROTOCOLO.md), salvo estos cambios explícitos:

1. Límite de salida: **12000 tokens**, para ambos modelos y todos los brazos
   con LLM. Temperatura 0 y mismo endpoint. Sin modificar razonamiento por
   parámetros propios del proveedor. Una respuesta no válida cuenta como
   candidatura fallida; no se repara código manualmente.
2. Semillas: se añade **100000000** a todas las fórmulas de v1. Así b vale
   100000000 para el principal y 150000000 para la réplica. Macros 1,2,
   generaciones 1…5 y tamaños de muestras sin cambios. La memoria inicial
   conserva start_memory(m), común a todos los brazos.
3. Artefactos nuevos en `lab/echo58/crece/f2-v2`. v1 queda conservada con
   manifest, código exacto, intentos y marca de interrupción. No se mezclan
   sus propuestas, promociones ni datos con v2.

Motivo y evidencia: ambas primeras propuestas con fichas del principal en
v1 llegaron truncadas (`finish_reason=length`, máximo 3000); las dos sin
fichas terminaron con `stop`. Con el mismo prompt fallido y cambiando solo
el máximo a 12000, el diagnóstico devuelve una función completa, AST válida
y `stop`. Los recibos detallan 4921 tokens de entrada, 8524 totales y 90 de
salida visible: el límite previo se agotaba antes de acabar la respuesta.
No se interpreta esto como evidencia de que esa pieza mejore ECHO: no se
ha evaluado su rendimiento. Los errores HTTP 503 son un problema separado
y mantienen el mismo máximo de tres intentos por propuesta.

El diagnóstico tiene presupuesto propio de seis intentos máximo entre los
dos modelos y ningún mundo. V2 mantiene **≤180 intentos** de generación;
no es una ampliación ilimitada hasta obtener verde. Una curva roja se
conserva y no abre un examen de este protocolo.

Documentación del endpoint y del razonamiento por defecto consultada:
https://ai.google.dev/gemini-api/docs/openai . La prueba real, guardada en
`api-diagnostic-v2`, fundamenta este cambio concreto; no se deduce una cuota
diaria ni se garantiza disponibilidad del servicio.
