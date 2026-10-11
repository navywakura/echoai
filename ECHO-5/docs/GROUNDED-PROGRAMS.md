# Grounded programs: API and bounds

This is a stdlib development implementation, not an ARC score or a claim of
general reasoning. It imports `seed.relational_dsl` and `seed.dsl` only through
`echo5.legacy.module`. The original `Object`, `Scene`, connected components,
binding/edit types, painting, erasure, stamping, rendering, and geometric
functions are reused. It does not invoke the old solver, mutate the old DSL,
start a model, or access a campaign. The separate evaluator owns query labels.

## Grounding

```python
from echo5.budget import Budget
from echo5.grounding import ground, select, targets, apply_relation

work = Budget(100_000)
scene = ground(rows, work)             # canonical seed.relational_dsl.Scene
source = select(scene, 'unique_shape', work)
objects_to_right = targets(scene, source, 'right', work)
result = apply_relation(rows, role='unique_shape', relation='right',
                        effect='recolor', budget=work)
```

Grid inputs are rectangular lists/tuples, 1–30 cells on each axis, with exact
integer colors 0–9 (booleans and coercible strings are rejected). Segmentation
uses the unique majority color on the border and four-connected same-color
components. A tied background, zero objects, or more than 32 objects rejects
the operation. Background need not be zero.

| Role | Binding rule |
| --- | --- |
| `largest`, `smallest` | Unique maximum/minimum cell count |
| `topmost`, `leftmost` | Unique minimum bounding-box top/left |
| `bottommost`, `rightmost` | Unique maximum bounding-box bottom/right |
| `unique_shape` | Exactly one object has a translation-normalized shape occurring once |
| `unique_color` | Exactly one object has a color occurring on only one object |

Every tie abstains. In particular, several different singleton shapes do not
constitute a unique shape role. Shape equality is exact, not rotation-invariant.
Contextual roles can select an object that is neither largest nor smallest.
They compare objects in the current scene and never memorize a color value or
absolute coordinate.

Relations are `all`, `same_shape`, `same_color`, `same_row`, `same_col`, `left`,
`right`, `above`, `below`. Targets exclude the source. The inherited row/column
relations compare top-left anchors. Directions are strict bounding-box
relations **from source to target**: `right` requires target.min_x > source.max_x;
`above` requires target.max_y < source.min_y. Perpendicular alignment is not
required; partially overlapping bounds do not count as strict separation.

Effects are `recolor` (paint targets with the source's observed color), `erase`
(paint targets with the observed background), `stamp` (replace targets at their
anchors with the source shape/color), and `extract` (source bounding-box image).
Stamp overlap/out-of-bounds and a missing target reject execution. Extraction
uses relation `all`, needs no target, and renders background around source cells.

## Closed program interpreter

```python
from echo5.programs import execute, parse_program, expand, candidate_atoms

program = {'steps': [
    {'op': 'relate', 'role': 'unique_shape',
     'relation': 'all', 'effect': 'extract'},
    {'op': 'rot90'},
]}
output = execute(program, rows, budget=Budget(100_000), library=None)
parsed = parse_program(program, budget=Budget(1000))
assert parsed.to_dict() == program
steps = expand(program, budget=Budget(1000))  # immutable tuple of typed Step
```

The root must have exactly the key `steps`, whose value is a nonempty list.
Each step is one of:

```json
{"op": "rot90"}
{"op": "relate", "role": "largest", "relation": "right", "effect": "recolor"}
{"op": "call", "name": "turn_extracted_shape"}
```

Geometry names accepted by the interpreter: `identity`, `rot90`, `rot180`,
`rot270`, `fliplr`, `flipud`, `transpose`, `crop`, `up2`, `down2`, `tile1x2`,
`tile2x1`. Geometry takes no extra arguments. Calls take only a name matching
`[a-z][a-z0-9_]{0,63}`; relations take exactly the three fields shown. No color
constants, coordinate literals, callbacks, source code, loops, imports, or
user-defined operators are accepted. Unknown keys are rejected at every level,
including `test_verified`, `authority`, or `confidence`. There are no model calls.

Programs have at most 16 surface steps, 16 expanded primitive steps, eight nested
calls, and 128 visited expansion nodes. Missing/quarantined names, dependency
changes, cycles, and expansion overflow raise `ValueError`; budgets raise the
distinct `BudgetExceeded`. Invalid attempts consume actual work before failure.
`execute` returns an immutable tuple-of-tuples. Supplied `Program` values are
revalidated; external proposals should be JSON data, not Python objects.

## Concepts and persistence

```python
from echo5.concepts import Library   # ConceptLibrary is an alias

library = Library()
demos = [
    {'input': [[1, 2, 3], [4, 5, 6]],
     'output': [[4, 1], [5, 2], [6, 3]]},
    {'input': [[7, 8], [0, 9], [1, 2]],
     'output': [[1, 0, 7], [2, 9, 8]]},
]
receipt = library.acquire(
    'turn', {'steps': [{'op': 'rot90'}]}, demos,
    budget=Budget(100_000), provenance={'source': 'separate demonstrations'})
output = execute({'steps': [{'op': 'call', 'name': 'turn'}]},
                 [[1, 2]], budget=Budget(100_000), library=library)
assert output == ((1,), (2,))

state = library.state()                         # detached portable JSON value
restored = Library.restore(state, budget=Budget(1_000_000))
library.save('artifacts/concepts.json')
loaded = Library.load('artifacts/concepts.json', budget=Budget(1_000_000))
```

`acquire(name, program, demonstrations, *, budget, provenance)` requires 2–10
demonstrations with at least two distinct input grids. It independently executes
the program against every supplied output; a solver/model's success claim is
insufficient. The outputs must come from the demonstration provider, not the
query evaluator. Provenance permits `source` (required), `task_id`, and `note`
strings of at most 512 characters. Task identifiers are metadata only.

The receipt contains the program, its expanded definition, direct dependency
checksums, the demonstration inputs/outputs and their checksums, provenance,
status, and any measured counterexamples. At most 64 immutable names are stored.
Reacquiring the same active name/definition verifies the new demonstrations but
returns the original receipt; it does not overwrite evidence. A different
definition or a quarantined name requires a new name. No query input, prediction,
label, or success flag is saved by `solve`.

`active_names()` returns a sorted tuple. `resolve(name, *, budget)` validates
checksum, status, and dependency checksums and returns detached program JSON.
`reverify_all(*, budget)` replays the original support of every active concept
and returns the number checked. `solve` invokes it on every task, then tests
every recalled candidate against that task's training demonstrations. Failing
on an unrelated task means *inapplicable*, not that the concept is false.

An explicit scope correction is different:

```python
receipt = library.challenge(
    'turn', [{'input': [[1, 2]], 'output': [[1, 2]]}],
    budget=Budget(100_000), provenance={'source': 'external scope correction'})
assert receipt['status'] == 'quarantined'
```

`challenge` accepts 1–10 demonstrations, executes the named concept, and records
only measured disagreements/undefined executions. A disagreement quarantines
the concept and its dependents atomically after all required budget reservations.
An agreeing challenge leaves state unchanged. Quarantine survives save/load.
There is no automatic repair, deletion, or reactivation; a replacement must be
acquired under a new name from independently supplied demonstrations.

State schema version 1 has `schema_version`, `concepts`, and an outer SHA-256
`checksum`; receipts also carry SHA-256 checksums. `restore`/`load` reject unknown
schemas, corruption, duplicate names, stale dependencies, forged evidence, or
active counterexamples. They reexecute active support even when all checksums
are valid: hashes detect alteration and do not grant authority. Files are bounded
to 8 MB; default restore/load budget is 10 million logical units. Persistence
requires a caller-owned path with an existing parent directory. `save` is a
direct JSON write, not a transactional database or concurrent-writer protocol.

## Solving and proposal verification

```python
from echo5.solver import solve, verify_proposal, candidate_compositions

task = {'train': demos, 'test': [{'input': [[2, 7, 3], [5, 0, 8]]}]}
answer = solve(task, budget=Budget(2_000_000), library=library,
               relational=True, hierarchical=True, learn=False, journal=None)
assert answer['test_verified'] is False
# answer['predictions'] == [[[5, 2], [0, 7], [8, 3]]]

check = verify_proposal({'steps': [{'op': 'rot90'}]}, task,
                        budget=Budget(100_000), library=None)
assert check['status'] == 'consistent'  # demonstration consistency only
```

`solve(task, *, budget=2_000_000, library=None, relational=True,
hierarchical=True, learn=False, journal=None)` accepts a nonnegative integer or
shared `Budget`. Train/test lists each contain 1–10 examples. Only `input` is read
from test mappings: tests poison indexing, `get`, iteration, copying, and
serialization of test labels. Contradictory training labels return `invalid_task`.
An optional `task['proposals']` list has at most 64 JSON programs; proposals face
the same verifier. Invalid proposals are counted and cannot override the judge.

The result contains `status`, `predictions`, `program`, `metrics`,
`test_verified=False`, and `alternatives`. Status values:

| Status | Meaning |
| --- | --- |
| `solved` | Every consistent program in the completed search tier agrees on all queries |
| `ambiguous` | Consistent candidates disagree, or one is undefined on a query (including role ties) |
| `unsolved` | Both finite tiers completed without a consistent candidate |
| `budget_exhausted` | Search incomplete; predictions withheld even if a candidate was found |
| `invalid_task` | Invalid grids, counts, contradictory labels, or malformed proposal collection |
| `invalid_library` | Stored evidence/integrity failed revalidation |

Only `solved` returns predictions, as lists of lists; `program` is the expanded
JSON witness. Up to 16 ambiguous program witnesses are included in `alternatives`;
this display cap never limits disagreement detection. The private evaluator must
judge predictions independently of all returned statuses.

`verify_proposal(proposal, task, *, budget=2_000_000, library=None, journal=None)`
checks one supplied JSON program, returning `consistent`, `rejected`, `ambiguous`,
or `budget_exhausted` in the same envelope. A `consistent` proposal returns its
predictions; it has not competed with alternative programs and is not a test
certification. This is the optional LLM proposal boundary without any model API.

With `learn=True`, a solved expanded program can be acquired under a deterministic
program-hash name using only training demonstrations. Insufficient independent
evidence leaves the library unchanged. Acquisition uses the same remaining
budget; learning exhaustion is reported in `metrics.learning`, without changing
an already completed prediction decision. Library absence disables acquisition.

## Search and fair cost controls

Tier 1 evaluates **all** 232 atoms, every active named concept, and all supplied
proposals. The atom iterator is `programs.candidate_atoms(*, relational=True)`.
It emits eight geometry programs (`identity` through `crop`) plus grounded
programs. If no hypothesis is consistent, tier 2 enumerates
`solver.candidate_compositions(*, relational=True, names=())`: every atom followed
by nonidentity geometry and geometry followed by a relational atom or concept.
There are 3,192 tier-2 candidates without concepts. Submitted/acquired programs
can be longer; endogenous search does not enumerate arbitrary 16-step sequences.
Tier-2 generation does not inspect task IDs, colors, labels, or generator names.

This is an explicit simplicity prior: success in tier 1 prevents tier-2 search.
Agreement applies to the completed tier plus recalled/supplied hypotheses, not
to all possible programs in the interpreter. More complex unsearched hypotheses
can disagree. The result never establishes query truth or unrestricted uniqueness.

`relational=False` restricts roles/relations to V3's vocabulary while keeping the
same geometry, execution, verification, and budget rules. Recalled/proposed
programs outside that vocabulary are inapplicable. It is an expressiveness
control, not a claim to reproduce the historical V3 solver's entire policy.

`hierarchical=False` executes the **same ordered candidates and expansions**
without memoizing common execution prefixes. The normal mode shares computed
prefixes and deterministic failures within one solve. It charges cache key cell
work, lookups, and insertions, and caps the cache at 20,000 entries. A cached
invalid candidate still incurs parsing, expansion, candidate, and lookup work.
No cache survives across tasks. Named calls expand and pay for their primitive
execution; a macro is not a free operation. Memory can cost more than empty
search because replaying stored support and hashing dependencies cost work.

Budget categories include validation cells, segmentation cells, object features
and comparisons, mapping/rendering, geometry cells, program/expansion nodes,
candidate attempts, comparisons, cache work, evidence replay, JSON traversal,
and hashing bytes. Reservations precede the corresponding operations. These are
declared logical work units, not exact CPU instructions, RAM bytes, time, or
energy. Inherited primitive counters describe their logical units; interpreter
and Python allocation overhead are not cycle-accounted. `metrics.used` is the
whole shared ledger; `metrics.task_used` is this call's delta. `counts`, `limit`,
`remaining`, candidate/error counts, cache hits, consistent-program counts,
`unique_predictions`, `query_undefined`, tier/completion, and reverified-concept
counts are included. `cortex_calls` remains zero because no model is invoked.

The journal accepts the parent's `trace.Recorder` (`write(**event)`). It receives
actual observation counts, verified demonstration hypotheses, and final measured
status/costs. The solver never reads it. Existing recorder envelope fields are
not supplied. Use the existing observer with this recorder for development runs;
do not instrument sealed campaigns.

## Verification and remaining limits

From `ECHO-5/`, use the pinned isolated interpreter:

```sh
.venv/bin/python -I scripts/dev.py test
make check
```

Owned tests cover geometry and extraction composition, new palette/layout
spatial transfer, a contextual role distinct from size selection, all ties,
invalid backgrounds, poisoned query labels, ambiguity, budget exhaustion,
authority-key rejection, cyclic/oversized programs, independently checked
acquisition, corrupt/forged receipts, dependent quarantine, persistence,
per-task revalidation, prefix-cost controls, and passive journal integrity.
The parent owns separate generators, curriculum, and held-out scoring.

Limits include border-based segmentation, a closed color palette and grammar,
no object tracking across steps (each step regrounds its current image), no
arbitrary relational pair search, no concept parameters, no automatic concept
repair, and no unbounded hierarchy. Stamp collision behavior is inherited. More
data does not ensure unique inference. Unit transfer fixtures are evidence of
those fixtures only; transfer outside independently measured generators and
any net advantage including acquisition costs remain separate questions.
