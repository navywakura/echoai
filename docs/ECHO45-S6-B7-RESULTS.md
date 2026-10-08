# S6-B7 · piloto SIN PROMOCIÓN

B7 añade un paso real de refinamiento por pareja, con su propio feedback después de B6. Ocho llamadas nuevas (seis propuestas y dos calibraciones); historia total de 22 llamadas. La condición B6 se conserva cerrada por separado.

Medición y auditoría independiente completas. **S6 todavía no está VERDE**: este piloto no abre examen ni sustituye B1–B5.

| Brazo | Suma A de las tres parejas |
|---|---:|
| FIJO | 537 |
| ECHO | 537 |

Aceptaciones ECHO en la historia de esta condición: **1**. Promoción: **SIN PROMOCIÓN**.

La pareja 613001 acepta `HOLD=20` condicionado a cuerpo conocido, reinicio
conocido y reinicio útil. ECHO pasa de 178 a 181 niveles A, sin pérdidas
individuales de niveles/puntuación en A ni B y con replay exacto. La suma de
las tres parejas iguala a FIJO; no demuestra superioridad del selector ECHO.

El feedback del verificador ya consigue una corrección útil. Falta que ese
mecanismo supere la petición genérica con presupuesto comparable y conserve
la ventaja en un examen nuevo de SEMILLA/FIJO/ECHO/SIN FILTRO.

| Brazo | Nuevas propuestas de esta etapa | Veredictos |
|---|---:|---|
| FIJO | 3 | {'V3': 3} |
| ECHO | 3 | {'accepted': 1, 'V3': 2} |

A tiene 40 partidas por pareja y 200 niveles posibles; las sumas anteriores agregan tres réplicas de políticas sobre A. No son resultados ARC oficiales ni un examen nuevo.

B de desarrollo se conserva protegido: los prompts solo reciben la señal de rechazo, sin partidas, índices ni resultados B. Las propuestas humanas de controles anteriores no entraron en los prompts.

La auditoría reconstruye las peticiones, las respuestas y los veredictos en procesos nuevos; valida fuentes, replay y composición de las políticas. La comprobación adicional de inferencia compara el JSON decodificado y reconstruye exactamente el wrapper original, conservando su serialización y hash.

No se redujeron umbrales ni se transformó un rechazo en aceptación. GPU gratuita, pago desactivado; no se reabre B5 ni se consume un examen final para escoger una política.

[Contrato](ECHO45-S6-B7-DESIGN.md) · [Piloto](../lab/seed/s6b7-20260929/pilot.json) · [Auditoría](../lab/seed/s6b7-20260929/audit.json) · [Inferencia](../lab/seed/s6b7-20260929/inference-audit.json).

[Auditoría de composición](../lab/seed/s6b7-20260929/composition-audit.json) · [Roadmap actualizado](ECHO4-ECHO5-TIMELINE.md).
