# S6-PROBE2 · resultados

Búsqueda dirigida tras PROBE1. Control de capacidad: 0 llamadas al modelo; B y examen sin tocar. Sus soluciones no se atribuyen a ECHO ni se muestran a ningún modelo.

2 propuesta(s) individual(es) HOLD 0/1 pasan V3 en las 80 partidas A con replay idéntico: el lenguaje actual alcanza V3 desde 378 en A (control de capacidad, V4 sin evaluar; no es descubrimiento autónomo ni cierre de S6).

```json
{
 "B_measured": false,
 "at": "2026-10-02T02:16:23.982023+00:00",
 "budget": {
  "at": "2026-10-02T02:14:49.291318+00:00",
  "cap": 14544,
  "includes": "training, replay, audit, exam; interrupted scheduled work still counts",
  "scheduled_games": 10048
 },
 "conclusion": {
  "passes": 2,
  "text": [
   "2 propuesta(s) individual(es) HOLD 0/1 pasan V3 en las 80 partidas A con replay id\u00e9ntico: el lenguaje actual alcanza V3 desde 378 en A (control de capacidad, V4 sin evaluar; no es descubrimiento aut\u00f3nomo ni cierre de S6)."
  ]
 },
 "exam_opened": false,
 "model_calls": 0,
 "profile_sha256": "218a831c634b3d23c2ec1e462779aa408a670546e9a0cbe96559e4341d0c7475",
 "screen_A53_gain_without_any_screen_loss": 2,
 "screen_gain_histogram": {
  "-1": 30,
  "-2": 91,
  "-3": 34,
  "-4": 464,
  "-6": 8,
  "0": 147,
  "2": 7,
  "3": 16,
  "4": 31,
  "5": 46
 },
 "screen_loss_games": {
  "42": 66,
  "51": 814,
  "59": 234,
  "68": 804,
  "76": 814,
  "77": 646
 },
 "screen_replays": 88,
 "screen_with_A53_gain": 874,
 "screened": 874,
 "screened_by_stage": {
  "1": 126,
  "2": 748
 },
 "signatures": 126,
 "soundness_checks": [
  {
   "index": 0,
   "levels": 382,
   "untouched_identical": true
  },
  {
   "index": 200,
   "levels": 383,
   "untouched_identical": true
  },
  {
   "index": 400,
   "levels": 378,
   "untouched_identical": true
  },
  {
   "index": 600,
   "levels": 378,
   "untouched_identical": true
  },
  {
   "index": 800,
   "levels": 374,
   "untouched_identical": true
  }
 ],
 "survivors": [
  28,
  33
 ],
 "survivors_by_stage": {
  "1": 2
 },
 "touching": 874,
 "universe": 1004,
 "verified": [
  {
   "gain_levels": 5,
   "index": 28,
   "levels": 383,
   "loss_games": [],
   "passes_v3": true,
   "replay_ok": true
  },
  {
   "gain_levels": 5,
   "index": 33,
   "levels": 383,
   "loss_games": [],
   "passes_v3": true,
   "replay_ok": true
  }
 ]
}
```

[Contrato](ECHO45-S6-PROBE2-DESIGN.md).
