# S6-B10 · condiciones compatibles con observaciones

Estado: **PILOTO SIN PROMOCIÓN**. S6 verde: **no**.

ECHO 534, FIJO 534; aceptaciones ECHO 0. Piloto auditado, reserva sin abrir.

Estas medidas son del banco sintético de desarrollo; no son puntuaciones ARC oficiales.
Una ganancia agregada con regresión individual se rechaza. Solo B1–B5 permiten cerrar S6.

## Piloto

Suma A: ECHO **534**, FIJO **534**. Aceptaciones ECHO: **0**. Auditoría independiente: **válida**.

Veredictos: V4: 18.

| Brazo | Semilla | Propuesta (ID original) | Veredicto | A: antes→después | Pérdidas A/B |
|---|---:|---:|---|---:|---:|
| fijo | 655001 | 0 | V4 | 178→186 | 0/1 |
| echo | 655001 | 0 | V4 | 178→186 | 0/1 |
| fijo | 655017 | 0 | V4 | 178→186 | 0/1 |
| echo | 655017 | 0 | V4 | 178→186 | 0/1 |
| fijo | 655029 | 0 | V4 | 178→186 | 0/1 |
| echo | 655029 | 0 | V4 | 178→186 | 0/1 |
| fijo | 655001 | 1 | V4 | 178→186 | 0/1 |
| echo | 655001 | 1 | V4 | 178→186 | 0/1 |
| fijo | 655017 | 1 | V4 | 178→186 | 0/1 |
| echo | 655017 | 1 | V4 | 178→186 | 0/1 |
| fijo | 655029 | 1 | V4 | 178→186 | 0/1 |
| echo | 655029 | 1 | V4 | 178→186 | 0/1 |
| fijo | 655001 | 2 | V4 | 178→186 | 0/1 |
| echo | 655001 | 2 | V4 | 178→186 | 0/1 |
| fijo | 655017 | 2 | V4 | 178→186 | 0/1 |
| echo | 655017 | 2 | V4 | 178→186 | 0/1 |
| fijo | 655029 | 2 | V4 | 178→186 | 0/1 |
| echo | 655029 | 2 | V4 | 178→186 | 0/1 |

[Artefacto pilot](../lab/seed/s6b10-20260929/pilot.json) · [Auditoría](../lab/seed/s6b10-20260929/pilot-audit.json).

[Contrato](ECHO45-S6-B10-DESIGN.md) · [Recuperación](ECHO45-S6-B10-RECOVERY.md) ·
[Estado](../lab/seed/s6b10-20260929/status.json) · [Plan posterior](ECHO45-POST-S6-PLAN-20260929.md).

**Diagnóstico posterior:** ninguna propuesta pierde niveles individuales A/B;
todas pierden eficiencia en una misma partida B, que sigue resolviendo 5/5.
Esa pérdida basta para V4 bajo el contrato vigente. Los 13 programas distintos
producen seis comportamientos distintos en las partidas medidas. El cierre
no cambia. [Investigación completa y próximos controles](ECHO45-S6-DIAGNOSIS-20260929.md).
