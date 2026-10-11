# Matched acquisition curriculum closure — V2 learning utility

V2 was authorized on 2026-10-10 **after development r1 and before confirmation**.
This is an outcome-informed development revision, not a claim that V1 was
successful or that the V2 endpoint was registered before all development.
The archived r1 report and valid audit remain unchanged. In r1, all arms
achieved 16/16 final successes over four independent runs. Eleven of twelve
arms identified the rule after one teacher query; the remaining arm needed
two. Final comparative gain was zero: r1 refutes final superiority for that
observed cohort and supplies no evidence of improved final precision.

V2 measures learning utility across the existing three query prefixes. The
grammar, generator, pools, selection algorithms, seed partition and reserved
uninspected confirmation seeds are unchanged. There is no search for winning
seeds or redesign of pools. Confirmation still uses 32 paired independent
runs and exactly three teacher queries per arm. V2 may fail. The old
`adversarial.py` result also remains historical evidence with its extra-work
confound; that frozen source is not changed or run by this instrument.

## Interface and implementation plan

`echo5.curriculum.run_benchmark(config, journal=None)` returns JSON with
`schema`, normalized `config`, flat evaluation `rows`, `summary`, `gates`,
and acquisition `runs`. `audit_report(report)` regenerates cases, checks
outputs against its external renderer, replays acquisition and cost ledgers,
and recomputes summaries/gates. Invalid receipts raise `ValueError`; a valid
report with negative scientific gates remains a valid audit. Schemas are
`echo5-curriculum-closure-v2`, `echo5-curriculum-contract-v2` and
`echo5-curriculum-audit-v2`; archived V1 reports use their archived V1 auditor.

`default_config(phase='confirmation')` returns the exact registered config;
`run_benchmark({})` selects those defaults. Confirmation overrides are
rejected. Development accepts bounded overrides of `paired_runs`, `rounds`,
`pool_per_round`, `confirmation_cases_per_run`, `work_per_run`, `seed` and
`bootstrap_samples`. The condition order is always
`['sequential', 'random', 'adaptive']`. Configuration is JSON data; neither
an arbitrary oracle nor executable configuration is accepted. Budget
exhaustion is an instrument exception, not a truncated successful report.
The parent must retain exceptions and the journal.

Each flat row includes `id`, `run_id`, `run_index`, one-based `prefix`, `query_index`, `condition`,
`family`, `result`, evaluator-owned `expected`, boolean `success`, `work`
and the frozen `hypotheses_sha256`. A result always keeps
`test_verified: false`; the external evaluator adjudicates exact grids.
Private labels become report/audit receipts after the experiment; the
report is never passed to the actor. Row identity is
`(run_index, condition, prefix, query_index)`. Confirmation has 2,304 rows:
32 runs × 3 arms × 3 prefixes × 8 evaluation inputs. This is still 32
independent replicates, with 256 evaluation cases per arm reused at each
prefix, not 768 independent cases per arm.

`summary.curves` reports accuracy, paired run accuracies, case regressions and
cumulative actual costs at each prefix. `summary.utility_totals` contains
per-run utilities and their means; `summary.utility_comparisons` contains
paired utility deltas, confidence intervals, sign tests and full protocol
cost comparisons. `summary.totals` and `summary.comparisons` retain their V1
meaning of **final** accuracy and final accuracy gain; the latter remains
descriptive and is explicitly marked `final_gain_descriptive_only: true`.

Each run contains generated inputs/labels, the private witness, grammar IDs,
prediction-table commitment, common phase ledgers, repetition counts and
three arm receipts. Arm receipts contain each selected index, disagreement
scores (adaptive only), acquired label, full compatibility vector, before/
after survivors, rejected indices, frozen-state hash, exclusive work and
standalone-equivalent total work. `arms[condition].prefixes` contains frozen
survivors, hashes and cumulative acquisition/evaluation/total ledgers for
every query prefix. Final arm ledgers split acquisition from all prefix
evaluation work, without double-counting their sum. Source hashes include the new module,
the old adversarial hash helper, the executor and its direct dependencies.
The parent must freeze sources before importing the module; these hashes
are not a substitute for a source archive or a hostile-process sandbox.

Configuration and numerical gates are in `CURRICULUM-CONTRACT.json`.
`default_config(phase='development')` chooses a separate development seed;
the confirmation defaults require 32 independent runs. Smaller development
runs are permitted but cannot pass the confirmation gate. Unknown options
are rejected. Each arm starts with a fresh finite hypothesis set. The
existing program executor and budget ledger are imported, not reimplemented;
the frozen adversarial module contributes its canonical program hash only.

V2 implementation order: document the endpoint revision before new execution;
record every prefix and charge its evaluation; independently adjudicate
outputs and replay all ledgers; write bounded regressions; hand off tests
for parent execution after all programming is complete. Freeze V2 sources
and contract separately from the archived V1 campaign.

## Matching and causal boundary

One shared prediction table executes every grammar hypothesis on each input
once, before any arm's selection. This is a common, reusable computation,
not repeated work charged to a control to inflate its cost. All arms consume
the same actual table and have zero private hypothesis-execution calls.
Only fingerprints enter disagreement ranking; full predicted grids are
used for learning and prefix outputs. Cryptographic fingerprint equality is
the declared finite-output comparison convention, checked by full replay.
Each round offers the same pool and one teacher query per arm. The actor
receives inputs, predictions and its evidence-derived surviving indices;
it receives no family, witness, hidden output, generator seed or teacher.
Prediction disagreement uses only those public predictions. The teacher
releases a label only after selection. Earlier acquisition labels affect
later choices. Immediately after each label, the evaluator predicts on the
same immutable evaluation table using only that prefix's frozen surviving
hypotheses. Neither evaluation labels nor correctness feed back to selection
or evidence filtering. The prefix state hash is checked and retained.

Sequential takes the first input in an IID, unordered pool, without the
historical first-easy-case bias. Random samples an input uniformly. Adaptive
maximizes live hypothesis pair disagreement. Evidence filters the same
finite grammar in every arm; no LLM or synthesis outside that grammar.

Matching is exact for actual prediction tables, label queries, label
comparison opportunities and prefix prediction/adjudication opportunities.
Every arm performs all three teacher queries even when already identified;
the protocol has no early stopping or extra adaptive experiments.
It is **not an assertion of equal total CPU or
logical work**: adaptive selection performs additional useful work that is
counted. No filler, sleeping, counter padding, or omitted selection cost is
allowed. A separate gate allows at most 5% relative total-work overhead per
run, in the mean, and at the upper paired 95% confidence bound versus either
control. A selection benefit may therefore remain red.
This distinguishes removal of the extra-learning confound from a stronger
claim that adaptive selection is cheaper. The report includes both physical
work (common once plus all arms) and standalone-equivalent arm costs (common
plus that arm); standalone totals must not be summed as physical work.

For `H=16`, `R=3`, `P=6`, `Q=8` under the registered configuration, per
independent run:

| Quantity | Actual work or opportunity |
|---|---:|
| Acquisition table executions, common to all arms | `H*R*P = 288` |
| Evaluation table executions, common to all arms | `H*Q = 128` |
| Total actual common hypothesis executions | `416` |
| Witness executions, including unselected candidates | `R*P+Q = 26` |
| Teacher queries per arm | `R = 3` |
| Evidence/hypothesis comparisons per arm | `H*R = 48` |
| Actual evidence cell comparisons per arm | `225*H*R = 10800` |
| Private hypothesis executions per arm | `0` |
| Evaluation prediction calls per arm, all prefixes | `R*Q = 24` |
| External adjudications per arm, all prefixes | `R*Q = 24` |

The evaluation table is computed once and reused; V2 does not charge three
table constructions. Consensus reads, returned grids, prediction invocations
and external verdicts are actually performed and charged at each prefix.
All common preparation remains charged up front, including later pools;
prefix cost curves do not pretend that preparation was lazy or free.

All 16 programs output 15x15 acquisition grids, so evidence comparisons
visit all 225 cells and do not stop at the first mismatch. The full
compatibility vector is retained as the counterexample receipt and
intersected with existing evidence. No eliminated program is re-executed.
Adaptive counts prediction reads, histogram bins, candidates and rank
comparisons; sequential counts one index choice; random counts one bounded
RNG draw. No unused adaptive scoring is performed by controls.

If `G_i` is common work and `A_ic` is exclusive arm work in run `i`, the
comparison cost is `T_ic = G_i + A_ic` and physical work is
`G_i + sum_c A_ic`. Overhead versus control `c` is
`(T_i,adaptive - T_ic) / T_ic`. This denominator includes generation, oracle
and witness verification, table construction, acquisition, selection,
consensus, returned-grid serialization and external adjudication at all
prefixes. The full three-query protocol cost supplies the <=5% gate; prefix
cost curves are descriptive, not separate budget grants. The
report exposes exclusive arm costs so the shared preparation cannot
conceal the selector's marginal expense.

This comparison is specifically conditional on a shared exhaustive finite
prediction bank. It does not establish cost superiority over an optimized
lazy random learner that skips unselected inputs. Common preparation can
dominate the 5% denominator, which is why its cost and the selectors'
exclusive costs are both reported. The teacher is external to the actor's
API but lives in the same trusted Python process; this is information-flow
separation, not an operating-system security boundary.

These are defined logical units. Inherited DSL reservations, hash-cell
visits and RNG-call units are not Python instructions or FLOPs. Metadata
hashing, journaling, source reads, report construction, statistical
resampling and the separate audit are instrumentation outside the
experiment ledger. The parent should report their wall time separately.
No budget remainder is added to consumed work. A 20,000,000-unit per-arm
standalone-equivalent ceiling is enforced in addition to the relative gate.
External adjudication is counted as one comparator invocation per result,
not a fictitious full-grid comparison for an abstention. Teacher returns
copy every label cell; their cell count is distinct from that call unit.

## Scope and preregistered gates

The 16-program grammar uses the existing `largest` role, four directions,
recoloring and optional `rot90`, `fliplr` or `flipud` composition. New input styles, dimensions,
colors and multi-cell distractors are withheld until evaluation. These are
new synthetic layouts within a declared finite grammar, not unseen semantic
primitives, transfer.py's experiment, official ARC, or sealed S6 data.
An independent object-coordinate renderer generates labels; the existing
DSL must execute the private witness successfully on **every** input,
including all unselected pool items. Invalid challenges are instrument
errors, never silently replaced or removed from the denominator.
Every input has a target in each direction: the existing DSL rejects empty
target bindings. Distractors may already share the source color, creating
ambiguity without making challenges unsolvable. Scene generation never
conditions on the secret rule. This constraint replaced the initial
largest/topmost proposal during source review, before any execution.
Acquisition pools are IID draws and can repeat a public input. Repetitions
are retained, charged and reported, never silently resampled or claimed as
new independent evidence. Evaluation repetitions are handled the same way;
dimensions and colors make acquisition/evaluation inputs disjoint. The
statistical unit is the acquisition run, not a unique-grid count.

For run `i`, arm `c` and query prefix `k`, let `a_ick` be exact accuracy on
that run's same eight evaluation inputs. Define
`U_ic = (a_ic1 + a_ic2 + a_ic3) / 3`: an equally weighted discrete AUC or
mean prefix accuracy. There is no zero-query baseline, trapezoidal weighting,
best-prefix selection or post-hoc choice of a favorable query budget.

The primary paired effect is `U_i,adaptive - U_i,random`. Acceptance requires:

- At least 32 independent paired acquisition runs and the frozen confirmation configuration.
- Mean paired utility gain versus random >=0.10, at least six winning runs,
  lower paired 95% bootstrap bound >0 and exact one-sided sign-test p<=0.05.
- No individual evaluation-case regression against random **at any prefix**.
- Nonnegative mean paired utility gain against sequential. Prefix-level
  sequential case/run losses are reported; the safeguard is mean utility,
  not an unstated requirement of domination at every sequential prefix.
- Final adaptive accuracy >=0.95, with no final individual-case or run
  regressions against either control. Positive final gain is not required
  and cannot be claimed from a positive utility result.
- <=5% relative total-work overhead against either control, both for every
  run and for the mean and upper paired confidence bound; the existing
  20,000,000-unit standalone-equivalent ceiling also remains binding.

Absolute cost deltas and intervals are reported as well. Utility and cost
uncertainty jointly resample 4096 deterministic sets of **whole paired runs**.
All prefixes, evaluation cases and arms of a run stay together; neither 24
prefix evaluations nor eight inputs become independent replicates. Final
accuracy comparisons retain descriptive paired intervals. All ties yield p=1.
Bootstrap intervals are descriptive for this generator mixture; no general
capability inference or guaranteed green result follows.

The initial zero-cost-increase proposal was revised before execution after
coordinator static review within authorized scope. The numeric 5% threshold
was the coordinator's decision, not an explicit numeric user instruction.
Reduced survivor lookup work is
too small to credibly pay for selection and serialization of additional
correct outputs. The 5% allowance tests smarter selection at exactly matched
information opportunities, without pretending that a selector is free; the
accuracy and gain gates were strengthened at the same time. That **V1** cost
revision preceded execution. The separately declared **V2** change of primary
endpoint followed development r1 and precedes confirmation; it must not be
presented as the original V1 preregistration or as improved final precision.

Selection, queried evidence, rejected hypotheses, survivor commitments,
predictions and externally adjudicated results have deterministic receipts.
Optional events use the existing Recorder's `write(kind=..., **facts)`.
The viewer never supplies feedback to the actor. Runtime timing is outside
the deterministic scientific report and must be measured by the parent.

Tests and CPU benchmarks are intentionally deferred until the parent has
finished all programming. Changing gates after observing confirmation
requires a new contract version and preservation of the original report.

## Parent execution after all programming is complete

The new tests use only development seeds and do not require any advantage
gate to pass. Run from `ECHO-5`, using system Python, in the parent's normal
background test process:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_curriculum.py -v
```

The reusable unit report fixture is bounded to one development pair, three
acquisition rounds, two candidates per round and two evaluation queries;
its bootstrap uses 128 draws. The main development campaign can use
`default_config('development')` with `paired_runs=4` and
`confirmation_cases_per_run=4`, retaining all three conditions. These
overrides cannot alter the fixed 32-by-8 confirmation protocol.
Pure arithmetic fixtures cover utility gains with equal final accuracy,
prefix regressions, the sequential mean safeguard and run-level replication;
they execute no actors and are not experimental evidence or cost audits.

For the closure runner, import the module after source freeze, create the
existing `echo5.trace.Recorder` for a new `thought.jsonl`, and call:

```python
from echo5.curriculum import default_config, run_benchmark, audit_report

config = default_config('confirmation')
report = run_benchmark(config, journal=recorder)
# Persist JSON and source/contract archive without overwriting a prior run.
# In a fresh process, reload that JSON and its frozen source environment:
audit = audit_report(report)
```

The report's `gates.scientific_success` is a numerical-gates result,
with `independent_audit_required: true`. Only a valid independent audit's
`closure_success` completes the instrument check. `promotion` stays false
and `s6_green` stays false in every outcome. Scientific failures do not make
an otherwise intact report unauditable, and an audit pass does not turn a
negative comparative result into success.
