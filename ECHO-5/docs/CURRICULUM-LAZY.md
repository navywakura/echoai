# ECHO-5 lazy curriculum cost comparison

Authorized development revision, 11 October 2026. The existing curriculum
closure r3 and its numerical contract remain historical evidence. This module
does not read that campaign, change its gates, run its confirmation seeds, or
claim that its shared exhaustive prediction table was a lazy control.

Within `ECHO-5`, the implementation is `src/echo5/curriculum_lazy.py`, tests
are `tests/test_curriculum_lazy.py`, and this document is `docs/CURRICULUM-LAZY.md`.
The reference semantics and limitations are documented in
[the old closure](CURRICULUM-CLOSURE.md) and
[the remediation review](REMEDIATION-AND-TRANSFER-20261011.md).

## API and parent integration

```python
from echo5.curriculum_lazy import run_benchmark, audit_report

report = run_benchmark(
    seed=4400000, runs=4, acquisition_steps=4, budget=2000000,
    # journal=existing_echo5_recorder,
)
# After persisting the JSON and freezing sources, replay in a fresh process:
audit = audit_report(report)
```

These are also the function defaults and match the parent's
`ECHO-5/docs/REMEDIATION-PILOT.json` curriculum configuration. The module never
loads that file itself. `journal` is an optional keyword accepting the existing
`echo5.trace.Recorder.write(kind=..., **facts)` interface; no new thought bus or
viewer feedback is introduced. Neither function performs file I/O, launches a
campaign, imports an LLM, installs dependencies, or measures time. The parent
owns source freezing, persistence, the mini terminal, and CPU/wall-time records.

Accepted integer ranges are seed 0 through 2**63-1, runs 1 through 256,
acquisition steps 1 through 8, and budget 1 through 10**10. Booleans, floats,
invalid ranges and unknown keyword arguments are rejected. The pool has six
inputs per acquisition step; the heldout set has eight inputs per run. These
dimensions and 512 bootstrap draws are explicit in the returned configuration.

`budget` is the same **standalone-equivalent logical ceiling per arm**, covering
preparation, selection, acquisition, update and heldout evaluation. Shared work
is reserved before arm execution. Producer validation has a separate ceiling
of `budget` per paired run; it never consumes or replenishes a learner's
allowance. Budget exhaustion or an invalid generated witness raises an
exception. There is no partial successful report, retry with easier tasks,
dropped pair, shortened acquisition schedule, or substitution of unused
budget for consumed work. Preserve exceptions and the trace in the parent.

`BudgetExceeded` is caught separately, emits
`curriculum_lazy_budget_exhausted` with `scientific_result: "budget_exhausted"`,
`instrument_error: false`, the configured ceiling and completed-pair count,
then is re-raised. Invalid witnesses and other `ValueError` defects still emit
`curriculum_lazy_instrument_error`. The caller must distinguish `BudgetExceeded`
from an instrument bug; a generic exception handler in the parent runner would
otherwise lose that distinction. No completed report or superiority claim is
returned on exhaustion, and the module never increases the budget itself.

The parent launches the four-run study only after all integration files are
stable. This implementation was verified using small tests and fresh
development seeds, not by running that pilot or reopening a sealed campaign.

### Development budget check

Three fixed development smoke seeds, 14012, 14013 and 14014, each completed one
paired run of four acquisition steps at 2,000,000 units. Each invocation passed
a journal and emitted 122 factual events. These are budget checks, not the
preregistered pilot outcomes; seed 4400000 was not run for this check.

| Development seed | Sequential total | Random total | Adaptive total | Separate audit |
|---|---:|---:|---:|---:|
| 14012 | 193,113 | 248,946 | 341,169 | 72,208 |
| 14013 | 206,608 | 274,135 | 335,230 | 90,832 |
| 14014 | 206,562 | 206,550 | 335,201 | 90,810 |

The largest observed arm total leaves 1,658,831 units of the 2M allowance.
Adaptive learning cost was higher than either control in all three smoke
fixtures; these checks do not establish an accuracy or cost advantage.

A conservative bound from the current source counters also fits 2M without
assuming any hypothesis elimination. Acquisition scenes have 225 cells, five
objects and nine nonbackground cells; heldout scenes have 483 cells, seven
objects and 18 nonbackground cells. Taking the most expensive suffix and all
non-source cells as targets gives the following rounded-up logical limits:

- Shared acquisition preparation: 12,000 units for four pools of six inputs.
- One acquisition prediction, including fingerprint and cache work: 1,500.
- One heldout prediction with the same accounting: 3,100.
- One acquired label, including oracle, witness and returned copy: 2,600.
- One heldout input's shared generation and validated label: 6,000.
- Adaptive selection bookkeeping: 256 per step; evidence update bookkeeping,
  including all 16 full-grid comparisons and cache reads: 4,000 per step.

For S live hypotheses, at most `6*S + (16-S) <= 96` predictions execute in
an acquisition step. Heldout inference executes at most `8*16` predictions
once, then reads its cache across the four saved prefixes. A deliberately
conservative full-arm bound, including some duplicate cache-read charges, is:

```text
12,000                                  shared acquisition preparation
+ 4 * (96*1,500 + 256 + 4,000 + 2,600)   all acquisition/selection/update work
+ 8 * 6,000                             shared heldout preparation
+ 8 * 16 * 3,100                        all possible heldout predictions
+ 4 * 8 * (2*16 + 484 + 2)              consensus/cache/output/adjudication
= 1,076,800 logical units per arm
```

The separate all-input producer audit is bounded by 100,000 units at four
steps: 24 acquisition witnesses at at most 2,300 units each, eight heldout
witnesses at at most 4,800 each, and 204 label/adjudication checks. These
bounds concern the current generator, grammar and counters, not measured CPU
time; recompute them if those definitions change. No protocol budget increase
is indicated for the planned four-step run.

## Matched opportunities and preserved answers

Each paired run uses the existing 16-program grammar and scene generator:
largest-object recoloring in four directions, optionally composed with
`rot90`, `fliplr` or `flipud`. The true rule belongs to this finite grammar.
All arms receive identical public pools, hypotheses, acquisition opportunities
and heldout inputs. A new `echo5-curriculum-lazy-v1` seed namespace separates
these generated tasks from the old confirmation stream. Pools remain IID,
unordered draws. Repeated inputs are retained and counted without resampling.

Only input generation, grammar construction and evaluator-owned heldout labels
are shared. There is **no shared prediction table**, exhaustive or otherwise.
Every arm gets a fresh cache for each acquisition pool and a separate heldout
cache. The cache key is pool position and hypothesis index. Repeated grid IDs
at different positions and grids in different arms do not share predictions.

The lazy adapter implements the table reads used by the existing
`curriculum.choose_challenge`, `_learn` and `_predict`; these functions and the
program executor remain unchanged. A table view itself executes nothing.

- Sequential takes the first candidate without inspecting predictions.
- Random takes one uniformly sampled candidate using an independent public
  RNG, also without inspecting predictions.
- Adaptive scores all candidates using disagreement among the current
  surviving hypotheses. Every consulted prediction is executed on demand and
  charged to selection, including candidates it ultimately leaves unused.
  Existing tie breaking and exhaustive scoring remain in force even when
  only one hypothesis survives.
- After selection, the private teacher renders and verifies just that arm's
  selected label. All 16 hypotheses are compared against it, preserving the
  old full compatibility vector, including hypotheses eliminated earlier.
  Previously paid predictions are reused; any missing selected-input
  predictions are charged to update. Survivors are intersected with the full
  compatibility vector exactly as before.

For H hypotheses, P candidates and S surviving hypotheses entering one round:

| Arm | Selection hypothesis executions | Update hypothesis executions |
|---|---:|---:|
| Sequential or random | 0 | H |
| Adaptive | P * S | H - S |

Here H=16 and P=6. First-round adaptive execution is exhaustive (96 executions)
and is entirely charged to that arm's selection. Controls execute 16
predictions each. All arms still perform H full-grid evidence comparisons,
one teacher query and one witness validation for their selected input.
Failed programs retain their attempted execution costs and a fingerprint
token. Budget failure is propagated, never cached as an ordinary failure.

Every acquisition prefix saves its surviving hypotheses and commitment. Once
that arm's acquisition is complete, the evaluator predicts on the eight
heldout inputs using each saved state. Reordering these read-only evaluations
after acquisition prevents verdicts, labels or evaluation caches from steering
later choices. Predictions retain `test_verified: false`; only the external
comparator supplies success. Heldout predictions are cached within the arm
across prefixes; a later subset of survivors does not re-execute its programs.

At K steps every arm has K teacher queries, 16*K evidence-hypothesis
comparisons, 225*16*K acquisition-cell comparisons and 8*K heldout prediction
and external adjudication calls. Prediction executions deliberately differ
between arms; the available hypotheses and information opportunities do not.

## Cost ledger

Every ledger is `{"used": integer, "counts": {operation: integer, ...}}`.
`used` always equals the sum of its counts. The existing executor's work
reservations and oracle counters are preserved; cache lookups and stores are
additional actual operation counts. A cached read pays for its lookup without
paying for another execution. There is no counter padding.

Each item in `results` has these `cost` ledgers:

| Field | Charged work |
|---|---|
| `preparation` | Shared acquisition input generation, grammar nodes, hypothesis identities and private target draw; zero hypothesis executions |
| `selection` | Actual index/RNG choice or full adaptive ranking, including all consulted predictions and their executor/fingerprint/cache work |
| `acquisition` | Selected teacher query, independent oracle rendering, witness execution/comparison and returned-label copy |
| `update` | Missing selected-input predictions, all 16 compatibility comparisons, survivor intersection and cache accesses |
| `heldout_evaluation` | Shared heldout generation/labels plus the arm's actual heldout predictions, cache use, consensus, returned grids and external adjudications at every prefix |
| `learning` | Sum of preparation, selection, acquisition and update |
| `total` | Learning plus heldout evaluation; the per-arm budget denominator |
| `exclusive` | Work actually executed privately by this arm; excludes both shared preparation components |

These totals overlap by definition: do not sum `learning`, `total` and their
component phases. A prefix's `learning_cost` is cumulative learning only,
including the public acquisition pools generated up front. Evaluation rows
contain incremental private evaluation `work`; their sum plus shared heldout
preparation equals the arm's heldout ledger.

The main paired cost comparison uses **learning**, with heldout costs exposed
separately. It also reports phase deltas and the full `total` difference.
Expensive heldout preparation or all-input auditing cannot dilute the learning
cost difference. This is a new descriptive comparison, not a replacement for
the historical closure's full-protocol 5% acceptance gate.

Top-level `cost.arms` aggregates each arm's ledgers across runs.
`shared_preparation` and `shared_heldout_evaluation` count actual shared work
once per paired run. Thus:

```text
physical_protocol = shared_preparation + shared_heldout_evaluation
                    + sum(all arm exclusive ledgers)
physical_with_audit = physical_protocol + audit_overhead
```

Standalone-equivalent arm totals include their share of the same common
computation. Their sum is not physical work. The implementation does not
re-execute preparation just to inflate the controls' ledgers.

After learning, producer validation checks the private witness on **all**
acquisition candidates, including unused choices, and all heldout inputs.
It compares acquired labels and heldout receipts to freshly rendered truth.
These actual witness executions and checks appear only in `audit_overhead`.
They are not learner hypothesis predictions and cannot populate learner caches.
Invalid unselected challenges still invalidate the instrument.

These are declared logical work units, not Python instruction counts, FLOPs,
CPU seconds or joules. Metadata commitments, report construction, statistics
and Recorder I/O are outside the experiment ledger. Separate replay reports
its own logical work, including serialized receipt bytes and a comparator
invocation. Parent timing must include and distinguish these instrumentation
costs; no real-time measurement is treated as deterministic.

## Results, interpretation and replay

`run_benchmark` returns JSON-serializable data with:

- `results`: one receipt per paired run and condition, with common task IDs,
  hypothesis IDs, every selection, acquired label, compatibility vector,
  survivor state, prefix evaluation, opportunities and phase ledgers.
- `tasks`: private target and run-seed receipts plus repeat counts, revealed
  for reporting after acquisition. These never enter the selector interface.
- `pairs`: adaptive versus random and sequential. Each contains signed
  per-run utility, final-accuracy, phase and total cost deltas; prefix/final
  case regressions; and whole-run paired uncertainty for learning utility and
  learning cost. Positive cost delta means adaptive costs more.
- `perfamily`: all 16 rule families, with run/case counts, successes, incorrect
  answers, abstentions, utility, costs and raw paired differences. Unrepresented
  families have zero cases and null accuracies; they are never counted as
  passing families.
- `cost` and `audit`: actual phase accounting and the scope of producer checks.

Learning utility is mean exact heldout accuracy over all K acquisition
prefixes; final accuracy remains separately visible. The statistical unit is
the independent acquisition run, not a prefix, query or selected input. The
512 deterministic bootstrap samples resample whole paired runs jointly for
utility and learning cost. Intervals and the inherited sign-test statistic
are descriptive; one-run intervals are degenerate and sparse families do not
establish generalization. There is no seed search or success requirement.

`instrument_valid: true` means the producer completed its bounded protocol
and witness/label checks. `independent_replay_required: true` remains explicit.
The pilot always reports `scientific_superiority: false` and
`scientific_result: "inconclusive"`: no confirmation contract for superiority
is being introduced here. Signed deltas, losses and
`observed_mean_cost_saving` preserve negative empirical results. Instrument
validity does not assert a benefit, and `promotion` always stays false.

`audit_report(report)` regenerates the entire study from the supplied public
configuration, reruns every arm, revalidates labels, recomputes statistics and
compares the complete canonical JSON receipt. It rejects changes to states,
predictions, truth, coverage, ledgers, metadata, summaries and verdict types,
including a boolean replaced with integer 1. Unknown fields also fail replay.
A valid negative or inconclusive report passes. The audit returns `valid`,
`instrument_valid`, `replayed`, scientific fields, `replay_work`,
`receipt_comparison_work` and their `total_work`; it does not add replay cost to
the original learning cost or grant promotion.

Full replay reuses the same implementation. The independent coordinate
renderer checks witness semantics, but replay is not an independent proof of
the whole algorithm or a hostile-process security boundary. The parent must
retain frozen sources and use a fresh process for custody. The library performs
no artifact or source-receipt reads and cannot attest to an external source
archive. Report serialization and wall-clock timing belong to that runner.

## Bounded verification

From `<LAB_ECHO5>`, using system Python:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover \
    -s tests -p test_curriculum_lazy.py -v
```

Tests were written and observed failing before implementation. They exercise
real programs on small generated inputs: lazy controls skip unused choices;
adaptive pays exhaustive consulted predictions; paid work is reused;
exhaustive lazy output and the complete execution ledger match the eager
reference plus explicit cache operations; learned states and answers preserve
old semantics across conditions and composed rules; budgets and phase totals
are enforced; heldout results and journals cannot drive learning; replay
rejects corrupt receipts; and a one-run four-step fixture fits the parent's
2,000,000-unit ceiling. They do not require an adaptive win.

The finite known grammar, synthetic layouts, full compatibility-vector update
and exhaustive adaptive selector remain limitations. This tests cost within
that declared learner, not optimal random learning, unseen semantic primitives,
ARC ability, S6, or a broader cost-superiority claim.
