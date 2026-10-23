# ECHO-5 representation, concepts and hierarchy closure

Execution update, 10 October 2026: the implementation below describes V1.
Its development result and independent audit are retained in
`artifacts/closure-development-20261010-r1/`. The active measurement contract
is V2 in [TRANSFER-CONTRACT.json](TRANSFER-CONTRACT.json), frozen before any
confirmation evaluation. V2 requires memory efficiency against empty and
size-matched irrelevant libraries, including acquisition and semantic work;
the manual fixed library is an oracle reference with accuracy and total-cost
noninferiority requirements. Strict superiority against that oracle remains
reported, including when false. This amendment does not change the solver,
cases or seeds and does not make the V1 negative result green.

The revised development run is in `artifacts/closure-development-20261010-r2/`.
The later 72-case development expansion and independent replay are retained in
`artifacts/development-scale-20261010-r1/`, with a concise Spanish report in
`DEVELOPMENT-SCALE-20261010.md`. It passes the numerical V2 development criteria;
confirmation and its independent audit remain necessary for closure.

Implementation target: `CLOSURE-IMPLEMENTATION-20261010.md`. The initial handoff
was limited to programming and static checks. Background tests, measurement
and independent development replay have since been completed. The exact32 bank
in `RESULTS-20261010.md` is now
development evidence only; its historical sources and receipts are untouched.

The interface is `echo5.transfer.run_benchmark(config, journal=None)`, returning
`schema`, `config`, `rows`, `summary`, `gates` plus acquisition, library,
contract and source receipts. `audit_benchmark(report, replay=False)` is the
public recomputation entry point. `audit_report(report)` always requests full
replay and is compatible with the parent's `closure.audit_worker` dispatch.
The existing Recorder remains the passive
journal; no new thought bus or model is introduced.

Implementation order (execution of every test remains deferred to the parent):

- [x] Extend canonical object grounding with containment, morphology and packing.
- [x] Add an opt-in bounded synthesis frontier and integer-key prefix reuse;
  preserve the original solver defaults and closed executable program format.
- [x] Freeze demonstration-backed library views per solve, without granting
  authority to checksums or dropping revalidation costs.
- [x] Build independent structural generators, four library controls and
  explicit ambiguity/unsupported controls; retain acquisition and all costs.
- [x] Add independent audit/replay, executable evidence, tests and invocation.
- [x] Full checks and CPU development evaluation, in the background after programming.
- [ ] Parent: archive sources, confirm, replay in a fresh process, publish outcomes.

`TRANSFER-CONTRACT.json` freezes seeds, grammar, limits and numerical gates
before any confirmation evaluation. Confirmation must reject overrides;
development may use smaller configurations and must remain labeled development.
The parent owns source archival, background execution and the final audit.

## Interface and invocation

The runner takes a JSON configuration, **not the whole contract**:

```python
from echo5.transfer import default_config, run_benchmark, audit_benchmark, audit_report

config = default_config('development')  # or 'confirmation'
report = run_benchmark(config, journal=recorder)
# Equivalent frozen confirmation config: {'phase': 'confirmation'}.
# Write report as JSON; invoke auditing later from a fresh frozen-source process.
audit = audit_benchmark(report, replay=True)
# audit_report(report) is exactly the full-replay orchestration hook.
```

`normalize_config` validates without executing the solver. Development permits
subsets of `families`, `conditions` and `seeds`, reduced work budgets and a
different bounded synthesis config. Confirmation must match every frozen value.
Training seeds and any derived confirmation seeds are unavailable to development.
Changes to the numerical contract after seeing confirmation require a new version,
new seeds, and preservation of the previous artifacts. This instrument cannot
prevent a caller from manually invoking a generator; run custody is the parent's
responsibility.

After all components are programmed, the parent can use the existing orchestrator
with a **new** output directory (these commands were not executed here):

```sh
cd /home/user/REALRXOS/RXos/echoai/ECHO-5
nohup .venv/bin/python -I scripts/closure.py worker transfer --phase development \
  --output artifacts/transfer-development-v1 > artifacts/transfer-development-v1.log 2>&1 &
```

After that process exits, run the audit separately, also in the background:

```sh
nohup .venv/bin/python -I scripts/closure.py audit-worker transfer \
  --output artifacts/transfer-development-v1 > artifacts/transfer-development-v1-audit.log 2>&1 &
```

For confirmation, use the parent campaign freeze/archive workflow before starting
the worker; a standalone worker does not archive sources. The runner starts no
process, viewer or model. A supplied `Recorder.write(kind=..., **facts)` receives
actual observations, verified training hypotheses, retained-frontier counts,
library freezes and externally scored outcomes. Its text never enters search.

Each row retains case and source identity, condition, public task, expected
queries (evaluator only), a Boolean external success, complete work ledgers,
wall/process durations and the actor result. `program` is the flattened executable
form; `hypothesis` preserves actual concept calls. `test_verified` is always false.
The top-level `cases` and `training` entries contain the frozen original inputs,
oracles, witness programs, seeds and generator receipts. `libraries` contain full
demonstrations, dependencies, checksums and provenance, not just names or hashes.

## What changed

The original `solve(task, ...)` path still uses its original two-tier grammar and
legacy prefix policy. No default candidate set, budget or historical benchmark
was changed. New use is explicit:

```python
result = solve(task, library=library, budget=16_000_000,
               synthesis=config['synthesis'], cache_policy='interned')
```

The opt-in search composes retained prefixes with primitives or verified named
chunks up to four search levels in this contract. Expanded programs still obey
the existing 16-primitive, eight-level named-expansion and 128-node limits.
The public synthesis API accepts depths 1–8, beam widths 1–128 and up to 100,000
candidate attempts; the contract fixes width 24 and 12,000 attempts. Ranking uses
only demonstration error. State reduction includes **all query executions**,
including undefined outcomes, so training-equivalent prefixes with different
query behavior are not collapsed. It does not use hidden query outputs.

Every hypothesis in the first matching retained tier must agree before a
prediction is emitted. Query-undefined consistent hypotheses force ambiguity.
Candidate/work exhaustion clears predictions; no partially checked tier can
solve. Beam pruning is reported explicitly. Agreement is over the retained
frontier and the library prior, not every possible program in the DSL.

Integer prefix/input keys replace repeated whole-grid hashing in the new policy.
Input references remain alive, preventing object-id reuse. The implementation
interns bounded prefix nodes, starts execution at the deepest available prefix,
and charges identity reads, key construction, lookups, writes, failed entries and
all residual execution. Both cached and uncached arms use the same candidates,
ranking and reduction. The compiled library view replays original support once
per solve, then shares immutable primitive tuples; a later solve revalidates
again. Source library changes cannot mutate an existing task-local view.

The new operations reuse canonical SEED `Object`, `Scene`, segmentation and
rendering. `inside` means strict bounding-box containment, not topological
enclosure. `same_size` compares area. `outline` removes four-neighbour interiors;
`fill_box` refuses to overwrite a foreign object. `pack` orders by descending
area with one-cell gaps and refuses equal-area ties. These are deliberate bounded
representation choices, not learned universal visual concepts.

## Families and controls

| Evaluation family | Independent expected transformation | Witness depth |
|---|---|---:|
| `outline_extract_scale` | Hollow a rectangle/clipped polyomino, isolate its boundary, double resolution | 3 |
| `fill_extract_tile` | Fill a U-shaped object's rectangle, isolate it, repeat horizontally | 3 |
| `pack_rotate_scale` | Order three distinct-area shapes, pack, turn, double resolution | 3 |
| `inside_erase_crop` | Remove an internal marker, crop surviving objects, reflect | 3 |
| `ambiguous_rotation` | Symmetric demonstrations with asymmetric queries; no witness claimed | — |
| `unsupported_color` | Introduce a color absent from every input; outside this palette-preserving language | — |

Witness depth is a declared construction, not a proof of minimal description.
The shallow comparison measures whether the search actually needs additional
levels on the sampled tasks. Oracles are rendered from generated shape data and
small independent geometric routines; they do not call the actor DSL. Witnesses
are then executed against those oracles; disagreement is an instrument error.
Witnesses, family/seed metadata and query labels are removed from solver inputs.
Controls are retained in costs and statuses; their safe behavior is abstention,
even if a guess would happen to equal an oracle.

Six acquisition tasks teach four base transformations and two parent concepts.
All acquisition attempts, including failures, are retained. The fixed library
uses six declared witness definitions and pays construction/verification costs.
The learned library must find its programs from demonstrations. The irrelevant
library performs identity and matches both the learned record count and expanded
primitive count, with acquisition-only support. It is not byte-size matched;
serialized sizes are reported. Its accounting also includes the acquisition
needed to determine the matched size. Empty, empty-uncached, empty-depth-two and
old-representation controls complete the seven conditions. The last is an
ablation in the new instrument, not a new historical ECHO-4.5 score.

There are 12 preregistered confirmation base seeds per family, offset by 100000
times the fixed family index: 72 cases / 504 condition rows. Development has two
base seeds. Six separate acquisition seeds precede all evaluation. The 16-million
work ceiling bounds each solve, but runtime has not been measured. Shared grammar,
hand-designed primitives and generators limit all conclusions; these are neither
504 independent capabilities nor an estimate of general intelligence.

## Costs, gates and audit

Per-arm totals include search, every failed attempt, acquisition, generation,
witness validation, library construction/freezing/revalidation and evidence/key
handling. Shared evaluation generation and source custody are charged in full to
each arm; `physical_run_work` counts shared work once. Logical units are explicit
instrumented operations, not a count of all CPython instructions or FLOPs.
Whole-run and per-row wall/process durations are measured independently, including
journaling when enabled. No logical saving implies a latency or energy benefit.

The contract requires 75% supported success for the learner, zero predictions on
controls, positive matched library size, positive hierarchy and representation
gains without paired losses, identical cached/uncached search results and at least
1% prefix work saving. Each learned-library comparison requires at least 5%
**total** work saving and no paired accuracy regression, including comparison
with the fixed library. Full closure requires every gate on the frozen
confirmation config. These strict criteria may produce negative findings.
Neither a verified replay nor a development success changes a false scientific
gate into a pass. Summary denominators include failed/budget-limited cases.

`recompute_summary(config, rows, training, libraries, preparation, cases,
custody_work)` exposes the accounting primitive to the parent. The safer complete
entry point is `audit_benchmark`: it checks the frozen contract and source closure,
regenerates and compares every original case/oracle, rejects missing/duplicate
rows, checks ledger sums, rebuilds libraries from acquisition evidence, executes
all claimed solved programs, and recalculates exact success and gates. Hashes
alone do not establish evidence. Without replay it returns `arithmetic_valid:
true` only after those checks, and `valid: false`.

With `replay=True`, acquisition is rerun from recorded inputs, all libraries and
preparation costs must match, and every scored row is rerun against its original
inputs with its original condition. Programs, predictions, statuses and logical
costs must match exactly. Timings are not compared for equality. Replay and
regeneration costs are reported separately as audit work. The parent must run
this in a fresh process from the archived source bytes. Mismatches raise
`ValueError` rather than silently rewriting a receipt. A valid audit can certify
an honestly negative experiment.

`tests/test_transfer.py` covers independent hand outputs, ties and overwrite
rejection, three-primitive discovery, parent/child acquisition, cache/control
equivalence, ambiguity, search/work exhaustion, poisoned query mappings,
contract separation, generator/witness agreement, full replay and forged
success/cost/oracle/source/gate receipts. These tests are written, **not run**.
