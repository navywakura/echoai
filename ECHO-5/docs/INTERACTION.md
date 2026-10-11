# ECHO-5 interactive learning: finite development contract

Preregistered before the benchmark on 2026-10-10. This is a CPU-only,
deterministic synthetic development experiment, not an ARC score, sealed
exam, physical trial, or unsimulated replay. No model calls or installation.

## Fixed comparison

- Confirmation: `run_benchmark(seed=30791, cases=24, budget=10000)`.
- Three independent arms: `passive`, `active`, `no_planning`.
- Every case/arm receives 10,000 logical work units and at most **64 actual
  actions**, including **16 acquisition actions** and up to 48 goal actions.
- Eight cases each: `novel_layout`, `novel_goal`, `changed_dynamics`.
  Generation is constructive; all four cardinal effects remain available.
  Walls leave a perimeter route. No infeasible samples are silently dropped.
- Acquisition uses a 5 by 5 public layout. Layout transfer changes geometry;
  goal transfer uses goals absent from acquisition; dynamics transfer changes
  the mapping from action handles to displacement after acquisition.
- Arms get identical initial observations, action handles, and limits. Their
  chosen interventions produce their own observations. They do **not** receive
  each other's observations or an identical prerecorded trajectory.
- Passive exploration chooses seeded random actions; active exploration
  scores disagreement between surviving finite effect hypotheses. Both use
  learned transition planning. The ablation uses active exploration without
  learned goal planning. Acquisition, hypotheses, graph construction, search,
  simulation, generation and replay validation count toward total cost.
- The policy seed is always 0, independent of the evaluator's seed and case
  index. Actor input contains neither seed, case ID, split nor result label.
- Report every case, including exhaustion and abstention: success, action
  count, work counts, acquisition/evaluation/audit costs, and actual transition
  transcript. Compare paired success and total work, publishing wins, losses,
  and ties. No tuning from confirmation results; no superiority threshold is
  added afterwards. A count difference on this finite set is not generality.

## Public boundary and API

`HypothesisAgent` receives validated public observations only: dimensions,
walls, position, visible goal, tick and generic action handles. It receives
neither a world object, a case/split label, nor the hidden action mapping.
Simulator checkpoints are evaluator-only. Strict schemas reject extra fields.

`choose(observation, *, budget, explore=False)`,
`observe(before, action, after, *, budget)`,
`plan(observation, *, budget, max_depth=64)`, `checkpoint()`, and
`HypothesisAgent.restore(checkpoint, *, budget, journal=None)` are the actor
boundary. `DiscreteWorld` exposes `observation()` and `step(action, *, budget)`;
its checkpoint/restore and `replay_episode` belong to the evaluator.
`run_benchmark(..., journal=None)` returns JSON-compatible dictionaries and
does not run anything during import.

Each action starts with five explicit hypotheses: four cardinal unit moves
and no motion. Walls clip moves to no motion. Filtering uses observed
transitions; blocked probes can remain ambiguous. Plans use bounded backward
BFS over unanimous predictions supported by at least two observations of
that action in the current dynamics epoch. Inferred edges are labeled as
such, separately from exact observed transitions. A contradictory observation
invalidates all cached skills and starts a new evidence epoch. Evidence is
retained. Effects outside the finite class cause abstention.

Legacy NEXUS `World` is reused as an observation cache through
`legacy.module`, with strict public-state indexing before its permissive
integer API. Its majority winner cannot override a contradictory observation.
The earlier two-step reward lookahead does not implement the goal/precondition
search required here. Budget and trace use the shared ECHO-5 modules; trace
events contain actual input, hypothesis counts, actions and observations, never
an invented monologue. The viewer's output is never fed back into the actor.

Checkpoint hashes detect corruption, not malicious authorship. Restore
replays validated evidence with charged work and recomputes derived state.
Python object privacy is an API boundary, not a hostile-process sandbox.

## Evidence and cost accounting

`cases[i].arms[mode]` contains `success`, `status`, `actions`,
`actions_by_phase`, `work` (the shared budget snapshot), `costs`, `transcript`,
`initial_worlds`, `audit`, `contradictions` and the finite learned `model`.
`initial_worlds` contains the **evaluator-only** acquisition/evaluation world
checkpoints, including the hidden mappings. These never cross the actor input
boundary. Each transcript row contains `phase`, `before`, `action`, `after`,
the actual `decision`, and a `learning` receipt when updating completed.
An action whose learning update exhausted its budget is still retained.

`replay_episode(initial_worlds[phase], phase_rows, budget=Budget(...))` executes
every recorded action again and compares the complete observations. Its
`audit.final.position == audit.final.goal` determines success. The report's
duplicate `final_position` and `goal` are convenience fields; auditors should
use the replay result. No success is credited if replay cannot complete within
the arm's budget. Audit work belongs to the original arm's total. A later
independent audit has its own ledger, rather than silently overwriting that
total. The parent evaluator also recomputes aggregate arithmetic and repeats
the complete benchmark in a fresh process.

The four `costs` entries (generation, acquisition, evaluation, audit) sum to
`work.used`. Logical units charge each hypothesis prediction/filter, graph
state, candidate edge, observed-cache lookup, BFS expansion/edge and extracted
plan step. Generation charges both grids' candidate cells and mapping setup.
Decision and simulator steps are single units. An evidence update charges two
units (cache observation and record update), plus one for allocating the fixed
legacy cache when necessary. These are **logical API operations**, not Python
instruction counts or allocation bytes. Legacy `World` allocates its existing
4096-slot tables. JSON formatting, validation, import/setup overhead and viewer
wall time are not CPU/energy measurements. `environment_action` in the work
ledger includes resimulation; `actions` counts only the actor's actual actions.

Graph costs are retained even for failed searches, and a complete graph is
rebuilt for every goal-plan request. The search uses at most 256 cells, four
actions and five candidate effects per action, with depth at most 256. The
benchmark uses depth 64. A failed plan allows another informative probe; an
out-of-class observation forces abstention. Earlier evidence remains in the
checkpoint after a contradiction, while old graph skills are invalidated.

Observations may start a fresh episode at tick 0. An identical transition
receipt within the current dynamics epoch is rejected, including tick 0;
replaying an episode cannot increase support. Distinct new-world receipts
remain accepted. Without an explicit authenticated episode identity, an
identical genuine repeat cannot be distinguished from replay and is rejected
conservatively. Within an episode every evidence record must continue the
previous observed transition; repeated or skipped ticks are rejected. Restore
rebuilds receipt deduplication, the hypotheses and observed cache from
at most 4096 records, charges replay, and checks the stored derived model with
type-sensitive canonical JSON. Plan artifacts are recomputed after restore.
The API trusts its observation source: hashing cannot prove that somebody
really performed a declared acquisition episode.

The report includes paired success wins/losses/ties and work comparisons for
equal-success pairs. This is descriptive finite-set accounting; no population
significance or physical generalization is inferred. Online evaluation actions
continue to update the transition model from observations. They do not use
reserved answer labels. This differs from the separate grid task's frozen
concept-library evaluation, whose contract is owned by the parent evaluator.

## Verification and scope

24 interaction tests cover informative probes, ambiguous blocked effects,
novel-layout detours, depth limits, the planning ablation, contradiction and
out-of-class behavior, strict public schemas, label/seed isolation, budget
exhaustion before mutation, observation/checkpoint aliasing, exact replay,
checkpoint corruption, continuity, and traced/untraced equality. Small fixture
benchmarks use seed 19 and three cases; they are not the confirmation set.

Run the focused tests from ECHO-5 with the frozen interpreter:

```sh
.venv/bin/python -I -B -c 'import sys,unittest; sys.path.insert(0,"src"); suite=unittest.defaultTestLoader.discover("tests",pattern="test_interaction.py"); result=unittest.TextTestRunner(verbosity=2).run(suite); sys.exit(not result.wasSuccessful())'
make check
make test
```

Root instructions were reviewed with the ECHO-5 scope: no historical campaign
or source edits, no second thought bus, no LLM, GPU, installation, physical
hardware claim, commit or publication. The legacy observation model is imported
through the shared adapter. There is no new neural engine. Traces use the
existing `Recorder` adapter and contain only recorded facts and explicit
conditional hypotheses. Confirmation seed 30791 remains reserved for the parent
run after source freeze; this implementation does not claim confirmation results.
