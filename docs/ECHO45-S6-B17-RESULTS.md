# S6-B17 — síntesis acotada y control temporal

Estado: **MICRO_AUDITED_NO_PROMOTION**. S6 sigue abierto.

Tres brazos: B16, síntesis sin LLM e híbrido. Ocho propuestas por brazo; mismo techo de partidas.
Solo desarrollo A. Una mejora sin pérdidas requiere replay e independiente antes de proponer piloto.

| Brazo | Propuestas | Mejor total A | Pasan V3 A | Primera mejora |
| --- | ---: | ---: | ---: | ---: |
| b16 | 8 | 378 | 0 | None |
| hybrid | 8 | 383 | 0 | None |
| synth | 8 | 383 | 1 | 5 |

Auditoría independiente: {"independent_execution":true,"valid":true,"verdicts_rebuilt":24}

[Contrato](ECHO45-S6-B17-DESIGN.md) · [Estado](../lab/seed/s6b17-20261004/status.json).

Investigación posterior, 5 de octubre: la guarda válida estaba disponible
en las siete llamadas de refinamiento del híbrido. El ranking y el resumen
temporal omiten estados creados por los candidatos; tres intentos repiten
comportamientos. Doce partidas de diagnóstico separadas, con replays
idénticos, confirman el efecto de añadir `pending_effect=0` en A42 y A53.
Esta evidencia no cambia el resultado B17 ni acredita conservación protegida.
[Informe, limitaciones y próximos cambios](ECHO45-S6-B17-FORENSICS.md).
