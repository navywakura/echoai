# Independent transfer research instrument

Authorized development revision after closure r3, 2026-10-11. This module does
not change that closure, its contract, the solver, or sealed campaigns. It
implements the independent-generator intervention in
[REMEDIATION-AND-TRANSFER-20261011.md](REMEDIATION-AND-TRANSFER-20261011.md).

## API and integration

```python
from echo5.transfer_independent import run_benchmark

report = run_benchmark(
    seed=2400000, cases_per_family=3, budget=2000000,
    journal=None,  # optionally an existing echo5.trace.Recorder
)
```

These are the defaults. The result is a JSON-serializable dictionary. `budget`
is a fresh logical-work allowance **per solver call**, including the template
arm. Three demonstrations and two queries form each case. This configuration
has 24 independent cases and nine template cases, hence 33 solver calls. The
main runner owns execution, recording, serialization, custody and replay.
Importing the module or returning a report performs no artifact writes.

`seed` accepts integers 0..2**63-1, `cases_per_family` 1..64, and `budget`
0..100,000,000. Booleans are rejected. A zero budget is a valid exhaustion
check. A supplied journal receives the existing solver's factual observation,
hypothesis and result events, plus case identity and evaluator outcome events;
it never becomes actor input. There is no new thought bus or LLM invocation.

Other useful evaluator APIs:

- `make_case(seed, family, *, demonstrations=3, queries=2)` returns task,
  private expected outputs, construction scenes, witness declaration, hashes
  and logical costs. Demonstrations accept 2..10 and queries 1..10.
- `public_task(case, *, ledger=None)` returns detached, explicitly whitelisted
  demonstration input/output pairs and query inputs only.
- `oracle_output(scene, family, *, ledger=None)` builds expected pixels from
  evaluator construction records. It neither segments an actor grid nor
  executes the declared witness.
- `score_result(case, result, *, ledger=None)` performs strict whole-case
  equality against private expected outputs, rejecting boolean pixels.
- `witness_program(family)` documents supported expressibility for external
  development checks. Neither generation nor `run_benchmark` executes it.

## Independent generation and semantics

Shapes grow one four-connected cell at a time from a randomly selected frontier.
Frontiers are sorted before local RNG draws; global random state is untouched.
Rectangles are rejected. The outline family also rejects shapes whose boundary
disconnects or whose outline would be identity. These are geometric checks,
without solving or filtering for favorable search results.

Every family cycles through three to six objects; five examples cover all four
counts. Source shapes contain 17..22 cells in a 5x5 region. Smaller, irregular
distractors have 3..6 cells. Objects use rejection placement, an empty border,
and a one-cell gap; supported scenes ordinarily use distinct colors. Directional
families require both selected targets and unselected distractors. Packing
uses unequal areas, randomly chosen from 3..11, within 4x3 regions. Containers
have clipped corners, two-cell walls, and an optional opening. The control
demonstrations use mirrored grown shapes and, for odd counts, a central cross.
All generated objects are nonrectangular and four-connected.

The generator uses none of the old morphology, packing or containment helpers,
`curriculum._scene`, actor grounding, or the program interpreter. Oracle labels
are constructed directly from saved object coordinates and colors. Tests disable
those existing APIs while generating every family. Hand-computed fixtures check
the reference separately; further tests compare supported witnesses against
labels **after** independent construction.

| Family | Category | Reference behavior | Template comparator |
|---|---|---|---|
| `outline_extract_scale` | supported | Outline largest, extract, double both axes | yes |
| `fill_extract_tile` | supported | Fill largest box, extract, tile horizontally | yes |
| `inside_erase_crop` | supported | Erase strict-box interior targets, crop occupied extent, reflect horizontally | yes |
| `right_erase_crop_rotate` | supported | Erase objects strictly right of largest, crop, rotate clockwise | none |
| `below_recolor_reflect` | supported | Recolor objects strictly below largest, reflect horizontally | none |
| `pack_reflect` | supported | Pack descending area horizontally with one-cell gaps, reflect | none |
| `ambiguous_reflection` | ambiguous control | Identity and horizontal reflection both fit symmetric demonstrations; asymmetric queries distinguish them | none |
| `unsupported_new_color` | unsupported control | Recolor largest to 9, a color absent from every input | none |

“Inside” is the existing strict bounding-box relation, including when the
container is open; it does not mean topological enclosure. An open/closed
container varies topology without changing the supported semantics. The absent
color control relies on the current closed DSL preserving the input palette
apart from background. If the parent extends that language to introduce new
colors, this control must be reviewed in a new instrument revision.

No input grid repeats within a case, including between demonstrations and
queries. Training outputs are permitted demonstration evidence. Query outputs,
family/category, seeds, scenes, witnesses, control evidence and evaluation
outcomes never enter `solve`. Each call receives `library=None`, `learn=False`,
relational and hierarchical execution enabled, interned caching, and the same
full synthesis grammar with depth 4, beam 24 and 12,000 candidates. Settings
are not selected using a family's witness or query labels.

## Report schema: `echo5.transfer_independent.v1`

| Path | Meaning |
|---|---|
| `instrument_valid` | True only on completed runs with stable source identities, matching public-task hashes, matching solver ledger receipts, and accepted result statuses; not a solver pass or external oracle certification |
| `config`, `runtime`, `sources` | Base seed, counts, budget, Python identity, and fixed relevant source paths/hashes |
| `independent.solver_settings`, `template.solver_settings` | Identical public solver settings, including budget |
| `<arm>.families.<family>` | Case counts, exact/abstention/wrong, exact rate, coverage, status counts, control counts and costs |
| `<arm>.by_category` | Separate `supported`, `ambiguous_control`, and `unsupported_control` summaries |
| `<arm>.receipts[]` | Full private case, solver result including predictions/metrics, scored outcome and stage costs |
| `comparison` | `independent_samples_not_paired`, matched semantic families and independent-minus-template exact-rate differences |
| `preparation_cost` | Source identity and deterministic schedule derivation work outside individual cases |

`exact + abstention + wrong == cases`. Exact requires `status == solved`,
`test_verified == false`, correct dimensions, strict integer colors, and equality
of **both** query outputs. `solved` alone is never a success. Any emitted answer
that fails exact comparison counts as wrong. Exhaustion, ambiguity and unsolved
statuses with no predictions count as abstentions, with statuses retained.
Invalid-task/search/library statuses, inconsistent work receipts, changed sources
or generation errors raise an exception; they do not become successful abstentions
or yield an `instrument_valid` report.

For controls, every `solved` status is also a `false_commitment`, even if the
chosen reference happens to match. `control_pass` requires `ambiguous` for the
ambiguity control and `unsolved` for the unsupported control. Budget or search
exhaustion does **not** demonstrate recognition of a limit. For supported cases,
the receipt's `control_pass` is null. Empty category summaries have zero cases,
null rates and null costs, as in the template arm's control categories.

The comparator calls only `transfer.make_case(..., split='development')`, with
independently derived seeds and the same demonstration/query counts. Its existing
labels are also directly constructed. It does not load old campaign configuration,
confirmation data or learned libraries. These are different random scenes from
different generators, **not paired observations**. Differences are descriptive
rates, without paired confidence intervals, significance tests or closure gates.

## Costs and reproducibility

Each receipt has these separate logical ledgers (`used`, `counts`, and individual
ledger limit/remaining). Family/category summaries sum their `used` and counts:

- `generation`: growth, geometric rejections, placement, input rendering,
  duplicate detection and random draws.
- `oracle`: coordinate reference construction and expected-output pixels.
- `receipt`: independent case serialization/hash work.
- `solve`: the actual supplied solver Budget, checked against returned metrics.
- `evaluation`: detached public copy, public hash check and exact comparison.
- `template_generation_and_oracle`: the old generator's combined ledger, which
  includes its hashing. Separate template generation/oracle/receipt entries are
  null because the old API does not distinguish them reliably.

Do not add case/receipt/family/category copies of the same ledger together.
Stage counter units differ; their sum is an accounting convention, not equal
CPU work. Python allocation, imports, report aggregation/serialization, optional
journal I/O, process startup and wall time are not fully metered. No claim of
all-in CPU, energy or computational savings follows from these counters.
Generator/oracle/receipt/evaluation ledgers have separate 20-million-unit caps;
exhausting a setup cap is an instrument error, not an actor abstention.

Reports deliberately contain no timestamps or wall durations. With identical
source files, runtime and options, canonical JSON can be compared byte for byte
in a fresh process. Per-case seeds are SHA-256-derived from the base seed, arm,
family and index, not shared between arms. Full scenes and expected grids remain
in evaluator receipts so reconstruction does not depend on a solver prediction.
The independent case hash covers its body before adding `sha256` and `costs`;
the public hash covers only `task`. Template cases keep their existing hashes.
The orchestrator should start a fresh process after freezing sources; filesystem
hashes alone cannot prove that previously imported Python code matches the files.

## Small checks and limits

From `echoai/`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=ECHO-5/src python3 -B -m unittest discover -s ECHO-5/tests -p test_transfer_independent.py -v
PYTHONDONTWRITEBYTECODE=1 make -C ECHO-5 check
```

The focused tests include whole-case replay in two fresh processes with different
hash seeds and **one unit** of solve budget, interpreter-disabled generation,
literal oracle outputs, all object counts, nonrectangular connectivity, no mutable
aliases, directional distractors, label isolation, witness compatibility,
strict scoring and cost arithmetic. A generator-only check of the requested
seed=2400000, three-case schedule covered 120 scenes and supported witness
comparisons with zero solver searches. None of these checks is the main research
benchmark or an accuracy result.

This remains a finite synthetic instrument with deliberate role/topology
constraints and empty-memory search. It measures generator shift and new
compositions within a known DSL, not acquisition of a new language, learned
library benefit, open-world reasoning or official ARC performance. Supported
families can still be ambiguous from their demonstrations or missed by bounded
search. Those failures remain visible. Main-run execution, source freeze and
independent replay belong to the parent runner.
