# Bounded curriculum optimization

**Update, 2026-10-12:** the combined runner completed eight paired runs and
their fresh-process audit. The efficient adaptive arm preserves 64/64 final
answers and 240/256 prefix answers while reducing total work by 49.23% relative
to the old adaptive arm. It still costs 21.16% more than optimized random, which
scores 56/64. See [results and limits](SEARCH-EFFICIENCY-RESULTS-20261012.md).
The original implementation notes below retain the before-campaign context;
replaying this sample in r2 and r3 does not double its independent run count.

Implementation revision, 11 October 2026. Changes are confined to
`src/echo5/curriculum_lazy.py`, `tests/test_curriculum_efficient.py`, and this
document. The [lazy benchmark](CURRICULUM-LAZY.md) remains the default. Search
implementation, historical campaigns, contracts, and source archives are
outside this change.

The owner supplied a four-run baseline: random and adaptive both ended at
32/32, with 484,264 random versus 995,301 adaptive learning-work units.
Those results motivate the optimization; they were not rerun here and are
not evidence of the optimized policy's performance. Verification uses small
unit fixtures only. Freeze all runner dependencies before any experiment.

## Stable runner API

```python
from echo5.curriculum_lazy import run_efficient_benchmark, audit_report

# Experiment invocation: only after sources and the combined runner freeze.
report = run_efficient_benchmark(
    seed=4_400_000,
    runs=8,
    acquisition_steps=4,
    budget=2_000_000,
    journal=None,  # Or the existing Recorder.write(kind=..., **facts).
)
# Persist the report, then replay under frozen sources in a fresh process:
audit = audit_report(report)
```

All arguments are keyword-only; the values shown are the entry point's
defaults. Integer validation and bounds match the lazy API: seed
0..2**63-1, runs 1..256, acquisition steps 1..8, budget 1..10**10. Invalid
types, including booleans in integer fields, fail. No file I/O, source-freeze
claim, source-receipt reads, model calls, or process launch occurs in either
function. The runner owns custody and persistence.

The combined `efficiency_runner` pilot plans an explicit override to
`seed=4_700_000`, with eight runs, four acquisitions and a 2,000,000-unit
ceiling. That configuration has not been executed in this work; it awaits
the shared freeze of all three workstreams. The API default remains as above.

The report schema is `echo5-curriculum-efficient-v1`, with
`config.efficient: true`. Audit returns `echo5-curriculum-efficient-audit-v1`.
The equivalent general call is `run_benchmark(..., efficient=True)`; its
existing default `runs=4` still applies unless specified. The flag accepts
only Boolean values. Omission or `efficient=False` retains the three-arm
`echo5-curriculum-lazy-v1` receipt, original RNG stream, costs, and audit
schema. A pre-change canonical receipt hash is pinned in the new tests.

The four result conditions, in order for each run, are:

| Condition | Selection | Evidence update |
|---|---|---|
| `sequential` | First input, no predictions | Entering survivors only |
| `random` | One independent public RNG draw, no predictions | Entering survivors only |
| `adaptive` | Original exhaustive disagreement scoring | Original full grammar |
| `adaptive_efficient` | Singleton shortcut or bounded disagreement scoring | Entering survivors only |

Controls receive the same survivor update optimization as the efficient arm.
This makes the controls less wasteful too. Their **costs** in this new schema
are therefore different from legacy lazy controls, while their selections,
learned states and answers retain the same semantics. The `adaptive` reference
retains its old costs and behavior. Equal seeds use the existing lazy task
namespace, so all four arms and the old benchmark have matched generated
pools, hypothesis identities, teacher rules and heldout inputs. Changing the
report schema does not silently select a new sample.

## Exact selection and evidence semantics

For S entering survivors, the old score is the number of disagreeing pairs:

```text
D(input) = S*(S-1)//2 - sum(n*(n-1)//2 for each prediction fingerprint bin)
0 <= D(input) <= S*(S-1)//2
```

`choose_challenge_efficient(table, survivors, budget)` accepts only a public
prediction table, live indices and a logical budget. It returns
`(selected_index, disagreement_scores)`.

- At **exactly one** survivor, every possible score is zero. Select index
  zero, preserving the old tie break, without executing any hypothesis for
  selection. The selected teacher label and the surviving hypothesis's
  evidence check are still acquired and paid for.
- At two or more survivors, score candidates in original order. Each visited
  candidate is fully scored over all S hypotheses. Stop scanning the pool
  only after an actual score reaches `S*(S-1)//2`. No later candidate can
  improve it; an equal score loses the original first-index tie break.
- If the bound is never reached, score the entire pool. There is no partial
  hypothesis tally, optimistic estimate, 90% threshold, or majority shortcut.
  This conservative bound may miss other possible optimizations.

`disagreement_scores` always has one entry per pool position. Measured scores
are integers; unmeasured entries are JSON `null`, including every entry in a
singleton round. A `null` score is never an asserted zero or maximum.

Evidence filtering evaluates only hypotheses present in `before`. Elimination
is monotone: a previous counterexample already excludes a hypothesis from the
version space. Its agreement with a later label cannot revive it. Live
hypotheses still receive the original shape checks and every cell comparison;
an invalid live prediction or elimination of all survivors raises an error.

Efficient/control archive rows add `compatibility_scope: "entering_survivors"`
and a grammar-indexed `compatibility` vector:

- `true`: evaluated against this acquired label and compatible;
- `false`: evaluated against this acquired label and contradicted;
- `null`: previously eliminated and not evaluated against this label.

`compatible` lists only known compatible entering survivors in those rows.
For the legacy `adaptive` reference it retains its original whole-grammar
meaning. `rejected` continues to list only new eliminations. An eliminated
hypothesis might agree with a later input; its `null` must not be interpreted
as either compatibility or incompatibility. The all-input producer audit
validates teacher witnesses, not these skipped learner hypotheses.

Heldout inference remains the original unanimous consensus function. Multiple
survivors that disagree produce `ambiguous`, even with 90% agreement. A solved
prediction always retains `test_verified: false`. Selection and learning
receive neither heldout labels nor verdicts; saved states are evaluated only
after that arm finishes acquisition. Journal payloads are detached copies
sent through the existing Recorder interface and cannot modify the learner.

## Work, budgets and matched opportunities

Let H be grammar size (16), P pool size (6), and C the number of fully scored
candidates in a round. Each arm owns its caches; no prediction or oracle
result paid for by another learner enters those caches.

| Arm | Selection hypothesis executions | Update hypothesis executions | Evidence comparisons |
|---|---:|---:|---:|
| Old adaptive | P*S | H-S | H |
| Efficient adaptive, S > 1 | C*S | 0 (selected predictions already paid) | S |
| Efficient adaptive, S = 1 | 0 | 1 | 1 |
| Efficient random/sequential | 0 | S | S |

The counters charge executor attempts, prediction fingerprints, cache reads
and stores, histogram bins, scored candidates, actual rank comparisons, full
evidence cell comparisons and survivor filtering. New counters also charge
the singleton test (`selection_survivor_checks`), score-vector slots
(`selection_score_slots`), bound calculation (`selection_discrimination_bounds`),
actual bound tests (`selection_bound_checks`), and nullable evidence-vector
slots (`evidence_compatibility_slots`). Skipped execution is never charged or
represented as completed work; cached reads still incur lookups. A failed
execution retains attempted work, while `BudgetExceeded` propagates.

Every arm still makes K selected teacher queries, with oracle rendering,
witness execution, comparison and label copying charged to acquisition. Each
arm has 8*K heldout prediction and external-adjudication calls. The report's
`opportunities` lists **actual** evidence comparisons; optimized counts may
be lower. Matched samples mean the same public pools and information access,
not artificially equal prediction executions or compatibility comparisons.

The equal per-run **total** ceiling includes preparation, selection,
acquisition, update and heldout evaluation. Shared preparation is reserved
before the arm starts; it neither supplies a free prediction table nor hides
evaluation costs. No arm gets more queries, an increased ceiling or a smaller
denominator on budget exhaustion. The whole invocation raises, retaining the
existing `curriculum_lazy_budget_exhausted` journal event and distinct resource
exhaustion classification.

Phase accounting follows the lazy schema:

```text
learning = preparation + selection + acquisition + update
total = learning + heldout_evaluation
physical_protocol = shared_preparation + shared_heldout_evaluation
                    + sum(arm exclusive work)
physical_with_audit = physical_protocol + audit_overhead
```

Audit overhead has a separate ceiling per paired run and cannot fund a
learner. Shared computation appears once in physical work and in each arm's
standalone-equivalent total. These overlapping ledgers must not be added
together indiscriminately. Costs remain declared logical operations, not
Python instruction counts, CPU time, FLOPs or energy. Report assembly,
statistics, metadata hashing and journal I/O remain outside the learning
ledger, as in lazy-v1.

## Comparison, canonical serialization and replay

`pairs` includes `adaptive_vs_random`, `adaptive_vs_sequential` and
`adaptive_efficient_vs_adaptive`, `adaptive_efficient_vs_random`,
`adaptive_efficient_vs_sequential`. Per-run rows retain utility, final
accuracy, learning cost, total cost, individual phase deltas and case
regressions. Positive cost differences mean the first named arm costs more.
Whole-run bootstrap intervals remain descriptive; all 16 families, including
unobserved families, stay visible in `perfamily`. No cost or accuracy win is
required for a valid instrument; promotion and scientific superiority remain
false, and the scientific result remains `inconclusive`.

For deterministic receipts and digests, the runner should use the same
canonical encoding as the auditor:

```python
canonical = json.dumps(
    report, sort_keys=True, separators=(",", ":"), allow_nan=False,
).encode("utf-8")
digest = hashlib.sha256(canonical).hexdigest()
```

Reports contain no timestamps, PID, CPU seconds or elapsed wall times.
`timing_measured: false` is a fixed declaration. Actual CPU and elapsed time
belong in separate process receipts, outside the canonical report. Given
the same frozen sources, configuration and pinned Python runtime, the report
is deterministic across fresh processes. The unit test checks that property
and performs real replay in the second process.

`audit_report(report)` dispatches from the schema, validates the opt-in,
regenerates all four arms, revalidates labels and compares the entire canonical
receipt. Partial scores, unknown compatibility, costs and summaries are
covered. Changed types or unknown fields fail. Replay work and serialized
comparison work remain separate from the original learning ledger. This
reuses the implementation; it is not an independent proof of the algorithm
or verification of an external source archive.

## Bounded verification

From `<LAB_ECHO5>`, use system Python for tests:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover -s tests -p test_curriculum_efficient.py -v
PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover -s tests -p test_curriculum_lazy.py -v
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3.12 -B -m unittest discover -s tests -p 'test_curriculum*.py' -v
make check
```

Observed results: 16 new tests passed, 17 lazy tests passed, and the combined
curriculum-only selection passed all 57 tests. `make check` passed environment
and syntax validation (88 Python files at the time of that check). No search
tests or full project test suite were run during this workstream.

The tests were written and observed failing before production changes. They
cover exact selections, survivor states and query answers against the old
algorithm; maximum-score and below-maximum ties; 90% disagreement; unknown
eliminated compatibility; real execution/cache/cell costs; exact and exhausted
budgets; matched four-arm receipts; legacy receipt stability; fresh-process
determinism; replay corruption; and heldout/observer isolation. They use
tiny geometry inputs and one-run development fixtures, with no artifact writes
or campaign invocation. No full experiment or performance claim accompanies
this implementation.
