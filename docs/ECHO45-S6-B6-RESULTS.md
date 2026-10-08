# S6-B6 · piloto SIN PROMOCIÓN

FIJO consiguió una reparación +3 A sin regresión protegida. ECHO consiguió +8 A, pero falló conservación B; se rechazó. Ocho de las doce propuestas conservaron HOLD=40, el valor nativo.

Medición y auditoría independiente completas. **S6 todavía no está VERDE**: este piloto no abre examen ni sustituye B1–B5.

| Brazo | Suma A de las tres parejas |
|---|---:|
| FIJO | 537 |
| ECHO | 534 |

Aceptaciones ECHO en la historia de esta condición: **0**. Promoción: **SIN PROMOCIÓN**.

| Brazo | Nuevas propuestas de esta etapa | Veredictos |
|---|---:|---|
| FIJO | 6 | {'accepted': 1, 'V3': 5} |
| ECHO | 6 | {'V3': 5, 'V4': 1} |

A tiene 40 partidas por pareja y 200 niveles posibles; las sumas anteriores agregan tres réplicas de políticas sobre A. No son resultados ARC oficiales ni un examen nuevo.

B de desarrollo se conserva protegido: los prompts solo reciben la señal de rechazo, sin partidas, índices ni resultados B. Las propuestas humanas de controles anteriores no entraron en los prompts.

La auditoría reconstruye las peticiones, las respuestas y los veredictos en procesos nuevos; valida fuentes, replay y composición de las políticas. La comprobación adicional de inferencia compara el JSON decodificado y reconstruye exactamente el wrapper original, conservando su serialización y hash.

No se redujeron umbrales ni se transformó un rechazo en aceptación. GPU gratuita, pago desactivado; no se reabre B5 ni se consume un examen final para escoger una política.

[Contrato](ECHO45-S6-B6-DESIGN.md) · [Piloto](../lab/seed/s6b6-20260928/pilot.json) · [Auditoría](../lab/seed/s6b6-20260928/audit.json) · [Inferencia](../lab/seed/s6b6-20260928/inference-audit.json).
