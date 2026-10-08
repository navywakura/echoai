# S6-B9 · reparación guiada por contradicciones

Estado: **cerrado sin promoción**, 29 septiembre 2026, 05:07 UTC.
**S6 sigue sin acreditar el verde.** Auditoría independiente válida: las
18 propuestas, peticiones y veredictos se reconstruyeron en otra caché/proceso.

Modelo Qwen fijado, backend CPU int8 declarado; ECHO y FIJO parten de SEMILLA vacía. El control humano no entra en prompts.

| Brazo | Suma A, tres semillas | Mejoras aceptadas |
|---|---:|---:|
| ECHO | 534 | 0 |
| FIJO | 534 | 0 |

Se completaron 18 propuestas y dos calibraciones en CPU gratuita, con
Qwen fijado y cuantización int8 declarada. Todas las propuestas eligieron
`REVALIDATE_NOOP`; cuatro lo desactivaron con valor 0. Hubo seis propuestas
distintas, ninguna cambió acciones y las 18 se rechazaron en V3. La tercera
ronda repitió exactamente las seis propuestas de la primera pese al feedback.

El diagnóstico sobre los registros completos de la base A, con paridad de
comportamiento comprobada en B10, cuenta 2654 contradicciones: **ninguna de
las 18 condiciones coincide con alguna de ellas**. La comprobación conserva
hashes de la base, el perfil y el piloto; se limita a trayectorias observadas.
[Recibo](../lab/seed/s6b10-20260929/b9-guard-diagnosis.json).

El operador funciona en el control humano auditado, pero B9 no aprendió
condiciones que produjeran una mejora. Esto localiza un problema de formulación
y adaptación de propuestas, sin demostrar que el modelo haya aprendido a
reparar al actor. El control humano no cuenta como éxito autónomo.

No se ejecutó la campaña ni se abrió la reserva 24700–24759. ARC oficial
no se ha vuelto a medir. Siguiente hipótesis: [B10](ECHO45-S6-B10-DESIGN.md),
comprobación mecánica de condiciones sobre observaciones conjuntas y exclusión
de propuestas idénticas ya probadas, igual para ambos brazos.

[Contrato](ECHO45-S6-B9-DESIGN.md) · [Piloto](../lab/seed/s6b9-20260929/pilot.json) ·
[Auditoría](../lab/seed/s6b9-20260929/pilot-audit.json) ·
[Estado](../lab/seed/s6b9-20260929/status.json).
