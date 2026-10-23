# CRECE F2 v3 · piloto independiente con Groq

21/10/2026. Nav mantiene facturación gratuita y señala Groq como alternativa.
Se conserva v1 (truncamiento) y v2 (cuota diaria de Google agotada: 20
peticiones del principal). Ambas están incompletas; no tienen resultado de
examen. Código exacto y recibos archivados en sus directorios.

Este piloto adopta el diseño y la puerta del protocolo F2 v1, con estas
diferencias fijadas antes de ejecutarlo:

- **Modelo único: openai/gpt-oss-20b, proveedor Groq.** Se informa por su
  nombre, sin atribuirle resultados a Gemini. La réplica Gemma sigue pendiente;
  no se mezclan modelos ni se cuentan como macros adicionales.
- Temperatura 0, `reasoning_effort=low`, `max_completion_tokens=2048`.
  Prueba previa sobre el mismo prompt de desarrollo: HTTP 200, `stop`, función
  AST válida, 4455 tokens de entrada y 141 de salida total. No se ha usado
  su rendimiento para elegir este presupuesto.
- Dos macros, cinco generaciones, los siete brazos, una propuesta por brazo
  con LLM y generación: **30 propuestas, hasta 90 intentos HTTP**. Fallos y
  duplicados siguen contando; no se edita manualmente el código propuesto.
- Semillas: las fórmulas de v1 con **b=200000000**. Memoria inicial idéntica
  entre brazos de la misma macro. Nuevos artefactos en `f2-v3-groq/`.
- Las fichas muestran también los campos reales `terminated` y `truncated`
  de cada observación. Esos campos ya existían en la traza, pero estaban
  omitidos en la ficha. Se incluyen para que el modelo pueda distinguir el
  final del episodio. No se le añade una regla de corrección diseñada a mano.
- Un único limitador compartido por los workers deja al menos 60 segundos
  entre llamadas al proveedor. Ante 429 respeta `retry-after`. Si el servicio
  exige más de cinco minutos, se interrumpe para continuar cuando haya cuota;
  no se transforma ese bloqueo en una candidatura científica rechazada.

Disponibilidad medida: endpoint de Groq responde a `gpt-oss-20b`. Cabeceras
1000 peticiones/día y 8000 tokens/minuto. El primer intento con urllib sin
User-Agent de aplicación recibió un error no JSON; el diagnóstico se conserva
como reserva consumida. Con User-Agent de aplicación, listado y generación
responden HTTP 200. No se cambian facturación ni límites de la organización.

Todos los umbrales de rendimiento, incluido el descenso en dos transiciones
consecutivas de sonda, permanecen. Si no pasa, este protocolo no abre examen.
Si pasa, F3 deberá fijar nuevas trayectorias completas por macro: dos pilotos
no sostienen el Wilcoxon confirmatorio previsto. Fuentes:
https://console.groq.com/docs/api-reference y
https://console.groq.com/docs/rate-limits .
