# S6-PROBE1 · resultados

Control de capacidad. 0 llamadas al modelo; B y examen sin tocar.
Sus soluciones no se atribuyen a ECHO ni se muestran a ningún modelo.

No encontramos solución con este presupuesto (200 individuales, 50 pares). No demuestra que el lenguaje esté agotado.

```json
{
 "B_measured": false,
 "at": "2026-10-01T07:30:49.473028+00:00",
 "b12_soundness": {
  "predicted_effect_vs_measured_change": {
   "[false,false]": 8,
   "[true,false]": 14,
   "[true,true]": 36
  },
  "violations": []
 },
 "budget": {
  "at": "2026-10-01T07:28:59.143857+00:00",
  "cap": 26000,
  "includes": "training, replay, audit, exam; interrupted scheduled work still counts",
  "scheduled_games": 22160
 },
 "conclusion": {
  "pair_passes": 0,
  "single_passes": 0,
  "text": [
   "No encontramos soluci\u00f3n con este presupuesto (200 individuales, 50 pares). No demuestra que el lenguaje est\u00e9 agotado."
  ]
 },
 "e0": {
  "candidates": 70208,
  "classes_by_operator": {
   "COOLDOWN_CAP": 5080,
   "HOLD": 9000,
   "REVALIDATE_NOOP": 1374
  },
  "decisions": 39269
 },
 "e0_inert": 154,
 "exam_opened": false,
 "gain_histogram_singles": {
  "-1": 3,
  "-2": 3,
  "-4": 1,
  "-5": 2,
  "0": 162,
  "1": 27,
  "4": 1,
  "5": 1
 },
 "model_calls": 0,
 "pairs": 50,
 "passes_by_stratum": {},
 "profile_sha256": "a3fe045bf9b036c31223421f98d89a174eefe1a1d4d9965616f12191374c99cb",
 "replay_failures": [],
 "sample_counts_by_stratum": {
  "B12_POSITIVE": 5,
  "COOLDOWN_CAP": 60,
  "HOLD": 105,
  "REVALIDATE_NOOP": 30
 },
 "singles": 200
}
```

[Contrato](ECHO45-S6-PROBE1-DESIGN.md).
