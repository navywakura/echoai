# S6-B22 — implementación y resultados

Actualización: 07-10-2026 14:32 Madrid. Estado: **CLOSED**.

Primera etapa: B22-V y piloto B22-S de ocho pares. Límite de 15.336 partidas;
cuatro procesos CPU locales, cero llamadas LLM. Cada medición tiene replay y
auditoría en proceso y caché independientes. Los intentos fallidos conservan su coste.

Reservadas: 11976; iniciadas: 11976; completadas: 11976.

- v-micro: PASS; 52 → 56 niveles; pérdidas []; auditado.
- v-broad: FAIL; 740 → 748 niveles; pérdidas [144, 154]; auditado.

| Recorrido S | Intentos auditados | Reparaciones | Primer pase |
|---|---:|---:|---|
| R22-822173 | 18 | 0 | ninguno |
| R22-822211 | 18 | 0 | ninguno |
| M22-822129 | 18 | 2 | ninguno |
| R22-822191 | 18 | 0 | ninguno |
| M22-822101 | 18 | 2 | ninguno |
| M22-822143 | 18 | 8 | ninguno |
| R22-822117 | 18 | 0 | ninguno |
| M22-822211 | 18 | 8 | ninguno |
| R22-822129 | 18 | 0 | ninguno |
| M22-822117 | 18 | 6 | ninguno |
| M22-822191 | 18 | 2 | ninguno |
| R22-822101 | 18 | 0 | ninguno |
| R22-822143 | 18 | 0 | ninguno |
| M22-822173 | 18 | 8 | ninguno |
| M22-822157 | 18 | 4 | ninguno |
| R22-822157 | 18 | 0 | ninguno |

Resultado del piloto emparejado: `{"capped_rank_to_first_pass": {"M22": [19, 19, 19, 19, 19, 19, 19, 19], "R22": [19, 19, 19, 19, 19, 19, 19, 19]}, "conditional_95pct_hoeffding_interval": [-0.9603227913199207, 0.9603227913199207], "directional_pilot_evidence": false, "failures_censored_at": 18, "generalization_confirmed": false, "interval_assumption": "independent seed streams, fixed development panel; conservative bound", "mcnemar_exact_two_sided": 1.0, "no_pass_rank": 19, "outcomes": {"M_only": 0, "R_only": 0, "both": 0, "neither": 8}, "pairs": 8, "success_rate_difference_M_minus_R": 0.0, "unit": "paired complete search run, not candidate or replay"}`.

Transferencia de finalistas: `{}`.

B22-V: **FAIL**. B22-S: **INCONCLUSIVE** (confirmación nueva pendiente).

B22-N y B22-E: **NOT_RUN**, fuera del presupuesto inicial. Requieren sus
contratos de modelo, confirmación, piloto/campaña y examen desde SEMILLA.
**S6 sigue abierto.** Un resultado V/S no acredita B1–B5 ni una puntuación ARC.

[Contrato](ECHO45-S6-B22-DESIGN.md) · [Implementación](ECHO45-S6-B22-IMPLEMENTATION.md) ·
[Estado](../lab/seed/s6b22-20261006/status.json) · [Pruebas](../lab/seed/s6b22-20261006/tests-final.log).
