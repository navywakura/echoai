# Native MiniGrid/BabyAI interaction sandbox

Implementation for the 2026-10-10 closure. **No tests, episodes, benchmarks or
confirmation cases were run during programming.** Dependency installation,
imports and compilation are separate from capability validation. The numerical
contract is [SANDBOX-CONTRACT.json](SANDBOX-CONTRACT.json); negative outcomes
remain negative. This is a local adaptation, not an official BabyAI score.

## Parent dashboard interface

```python
from echo5.sandbox import Session, catalogue
from echo5.trace import Recorder

choices = catalogue()  # static; no environment or episode starts
spec = {
    "scenario": "door_key",
    "seed": 101,
    "mode": "informative",
    "budget": {"actions": 192, "work": 200000},
    "environment_options": {},
}
# Starting a Session starts a native episode. Execute after programming is complete.
with Recorder("artifacts/new-session/thought.jsonl") as journal:
    with Session(spec, journal=journal) as session:
        initial = session.snapshot()
        next_state = session.step()       # one policy decision + one native action
        same_state = session.snapshot()   # detached JSON; no action or budget charge
        # session.step("left") also permits a public manual action.
        # session.reset() starts a new episode with the same validated specification.
        # After done, save the evaluator result outside the policy/UI actor inputs:
        # result = session.result()
        # verdict = result["receipt"]["payload"]["adjudication"]
```

`Session(spec, journal=None)`, `snapshot()`, `step(action=None)`, `reset()`,
`result()` and `close()` are synchronous. `close()` is idempotent. Stepping a
closed or finished session raises; reset a finished session or construct a new
one. The caller serializes operations and owns play/pause, reset controls,
SSE/polling, persistence and any server. There is no background thread here.
`SandboxSession` is an alias of `Session`.

`catalogue()` returns a list of `{id, name, environment, defaults}` objects,
beginning with `door_key`. Names are descriptive English strings; the UI can
translate them. Each `defaults` is a valid session spec. Scenario IDs:

| Scenario | Native registered environment |
| --- | --- |
| `door_key` | `MiniGrid-DoorKey-8x8-v0` |
| `objects` | `BabyAI-GoToLocal-v0` |
| `unlock_pickup` | `BabyAI-UnlockPickupDist-v0` |
| `blocked_door` | `MiniGrid-BlockedUnlockPickup-v0` |
| `dynamic` | `MiniGrid-Dynamic-Obstacles-8x8-v0` |
| `ambiguous_objects` | `BabyAI-PickupLoc-v0` |
| `ordered_doors` | `BabyAI-OpenTwoDoors-v0` |
| `put_next` | `BabyAI-PutNextLocal-v0` |

`environment` can explicitly select an allowlisted native environment. The
allowlist also includes `MiniGrid-DoorKey-6x6-v0` and `BabyAI-UnlockPickup-v0`.
It does not allow arbitrary registered environments, Python entry points,
wrappers, rendering modes or secret grid input. `seed` is an evaluator setting;
it is never passed to the actor. Mode must be one of the five contract modes.
An integer `budget` is shorthand for work units with 192 actions. Explicit
budgets require both `actions` (1–1024) and `work` (1–100,000,000).

`environment_options` replaces the scenario defaults. All profiles accept an
odd `agent_view_size` in 3–9. `objects` also accepts `room_size` (5–10) and
`num_dists` (1–12); `ambiguous_objects` accepts `room_size`; `put_next` accepts
`room_size` and `num_objs` (2–10); `dynamic` accepts `n_obstacles` (1–5).
`ordered_doors` accepts distinct `first_color`, `second_color` and boolean
`strict`. Native rejection sampling still belongs to the external package;
these size limits do not claim a hard wall-clock deadline. The parent can use
a worker-process timeout when running user problems.

## Snapshot and observation contract

Snapshots use `schema: echo5.sandbox.snapshot.v1` and portable JSON:

| Field | Meaning |
| --- | --- |
| `done`, `status`, `closed`, `step` | Lifecycle and number of actual native actions |
| `observation` | Exactly `schema`, `image`, `direction`, `mission` |
| `visible_grid` | The actual encoded native partial image, copied from `observation.image` |
| `visible_grid_order` | `x_y_type_color_state`; indexing is **column, row**, not row, column |
| `agent_position.view` | `[view_size // 2, view_size - 1]`, the actual agent marker in the view |
| `agent_position.relative` | Estimated `[x,y]` relative to episode origin, never hidden absolute coordinates |
| `objects` | Decoded visible objects with `view_position`, color, state and carrying flag |
| `mission` | Parsed bounded mission and ordered atomic subgoals |
| `hypotheses` | Candidate target positions, unresolved alternatives and pose uncertainty |
| `evidence` | Most recent observation update, including changed cells and its observation tick |
| `prediction` | The prediction made **before** the most recent action; explicitly a hypothesis |
| `action` | Most recent selected action `{id,name,reason}`, initially null |
| `consequence` | Actual observation change, direction change and resulting learning update |
| `memory.cells` | Only observed cells, with estimated relative position, encoded cell, decoded attributes, view coordinate and `seen_at` |
| `budget.actions` | `{limit,used,remaining}` native action ledger |
| `budget.work` | Existing `Budget.snapshot()` with `{limit,used,remaining,counts}` |

For rendering, type IDs 0–10 mean unseen, empty, wall, floor, door, key, ball,
box, goal, lava, agent. Color IDs 0–5 are red, green, blue, purple, yellow,
grey. Door state IDs 0/1/2 mean open/closed/locked. The native observation
places the carried object at the agent's view coordinate: it does **not**
reveal the tile underneath. The memory does not invent an empty underfoot tile.
Use unseen tiles as unknown and the `agent_position` marker as an overlay.

No full-grid renderer, `env.grid`, `env.agent_pos`, object identity, evaluator
seed, native reward, hidden verifier or success label enters the actor snapshot.
The relative map is assembled using visible static landmark registration and
the known motor action model. Ambiguous odometry remains labelled as an
estimate; spatial coordinates are not independently verified absolute facts.
The UI may show that map, but cannot turn it into a privileged full-map view.

`snapshot()` is passive and deep-copies its data. Mutating UI JSON cannot alter
memory or the simulator. Snapshot polling never chooses a new action. A
stale memory after budget exhaustion is distinguishable from the newest raw
observation through observation ticks and the consequence status.

## Real external implementation and reuse

The environment is created with Farama `gymnasium.make`, reset with an
evaluator-owned seed and stepped through its native `step` method. MiniGrid
provides occlusion, pickup/drop, keys, locked doors, moving obstacles and
termination. BabyAI supplies its own instruction verifiers. No hand-written
grid pretends to be the external package. Missing or mismatched dependencies
raise `DependencyUnavailable`; there is no synthetic fallback.

The observation boundary matches the documented native partial view and action
encoding. Primary references: [MiniGrid usage](https://minigrid.farama.org/content/basic_usage/),
[BabyAI UnlockPickup](https://minigrid.farama.org/environments/babyai/UnlockPickup/),
and [pinned MiniGrid source](https://github.com/Farama-Foundation/Minigrid/tree/v3.0.0).
The installed 3.0.0 source was reviewed for view orientation, carrying encoding,
dynamic-step order, mission grammar, object matching and native success rules.

The existing `interaction.py` was reviewed. Its `HypothesisAgent` requires
public full geometry and therefore cannot consume this partial view without
leaking or inventing unseen cells. This adapter reuses its canonical receipt
helpers and the shared `Budget` ledger instead of copying the full-grid world.
The existing `Recorder` remains the sole diary adapter to the existing ARC
journal. It writes passive facts; JSON is not a new thought-bus, no simulator
or journal narration feeds the actor, and WSP/NEXUS/legacy engines are unchanged.

The new actor is a finite symbolic mission policy. It acquires a memory map
from observations, records transition counts and contradictions, and replans
through observed traversable cells. It can seek a matching key, toggle doors,
clear carried objects and relocate blockers. Unseen destinations trigger
bounded information-seeking views. Native mechanics and the grammar are
provided knowledge: this does not claim learned neural weights, autonomous
rule discovery, LIF action selection, physical robotics or unrestricted language.

## Missions and user problems

`mission` may be text, `{"text": "..."}`, or a structured specification:

```json
{
  "order": "single",
  "steps": [{
    "verb": "pickup",
    "target": {"type": "ball", "color": "red", "location": "left"}
  }]
}
```

Supported structured verbs are `goto`, `pickup`, `open`, `putnext`. `putnext`
also requires `reference` with the same three descriptor fields. Locations
are null, left, right, front or behind; colors may be null. `order` is single
for one step and sequence/all for two. Text equivalents include:

- `go to the red ball`, `pick up a blue box`, `open the yellow door`.
- `pick up the ball on your left`, `go to a green object behind you`.
- `put the red ball next to the blue box`.
- `open the red door, then open the blue door`.
- `open the blue door after you open the red door`.
- Two atomic instructions joined by `and`.
- The three native reach-goal phrases in the JSON contract, including DoorKey.

At most two atomic instructions and 512 characters are accepted. No freeform
assistant, Python evaluation, shell, URL retrieval or LLM is invoked. Articles
do not create privileged identity: multiple matching objects remain alternatives,
and only the external verifier can say that the chosen object satisfies the task.
Locations refer to the initial agent frame. The built-in location task is
single-room; operator location overrides in multiple rooms are rejected.

A BabyAI override binds a native BabyAI instruction verifier to existing
matching objects after reset. A request with no matching objects is rejected;
the adapter does not create a conveniently matching target. This deliberately
defines a **user task**, not an official unchanged benchmark task. MiniGrid
overrides must preserve the native goal semantics; arbitrary relabelling is
rejected. Environment options and seed specify the world independently of
the actor. Fixed profiles never filter seeds after seeing outcomes.

## Comparison, adjudication and replay

Both `echo5.sandbox_eval` and the convenience export in `echo5.sandbox` provide
`run_benchmark(config, journal=None)`. The return has `schema`, `config`, `rows`,
`summary`, `gates`, plus the captured numerical contract and source manifest.
Rows are one case/condition each, preserving case ID, split, family, environment,
seed, external verdict, costs, transcript receipt and replay audit.

```python
from echo5.sandbox_eval import run_benchmark, audit_benchmark

# Execute only after all closure programming and approved checks are complete.
config = {"split": "development", "cases_per_family": 2}
# report = run_benchmark(config, journal=journal)
# separate_process_audit = audit_benchmark(saved_report)
```

Config keys are `split`, `seed`, `cases_per_family`, `budget`, `families`, `modes`.
Omitted settings come from the JSON contract. A subset or altered budget is
an exploratory run and cannot meet the confirmation gate. Confirmation needs
all seven families, all five modes, exactly 192 actions/200,000 work units per
condition, and at least eight cases per family. Native failures, exhausted
budgets and action limits stay in the denominator. Instrument failures raise
and leave factual error events for the parent to retain.

| Policy | Control being measured |
| --- | --- |
| `informative` | Acquired map, goal planning, information-seeking views and replanning |
| `fixed` | Observation-independent eight-action sequence |
| `passive` | Deterministic seed-0 random turns/forward, no goal planning |
| `no_memory` | Same planner using only current visible cells; retains odometry/task progress |
| `no_planning` | Observed memory retained, but only local reactive actions, no graph search |

All start with empty memory and identical native worlds and limits. In dynamic
obstacles, only actions 0–2 exist; unsupported fixed-policy proposals are
explicitly recorded and mapped to left, matching the native implementation's
documented fallback. Native reset/step calls and wall seconds are reported
separately from logical actor work. Replay costs are separately reported under
the same per-condition execution cap. Polling/serialization is observer overhead;
logical work is not external-library instruction counts, FLOPs or joules.

Development and confirmation seeds occupy disjoint ranges. Confirmation adds
larger layouts, unlock-plus-object and blocker-plus-key combinations, ordered
doors, relational placement, changed obstacle density and larger ambiguous
object rooms. The grammar/mechanics intentionally know these bounded rule types
beforehand; the holdout measures application to new cases, not invention of rules.
The entire policy implementation and contract must be frozen before measurement.

`Session.result()` returns `{receipt: {payload, sha256}, timing}`. Its evaluator
payload contains config, source/dependency identities, native observations,
decisions, actions, consequences, memory, cost ledgers and `adjudication`.
Success requires the native environment to terminate with positive reward;
the actor's supported-subgoal flags never adjudicate. A success on the final
permitted step counts even when native timeout is also true. A hash is only
integrity metadata, never success evidence.

`replay_episode(result, journal=None)` recreates the native world and reexecutes
policy/manual decisions, comparing the whole deterministic payload. It checks
versions, sources, every observation, memory changes, costs, actions and native
outcome. Wall timings and the diary's envelope timestamps are excluded from
identity. `audit_benchmark(report)` independently replays every row and recomputes
costs, summaries and gates; it rejects incomplete case sets and relabelled seeds,
conditions, verdicts or work. Run it in a new process for independent custody.

Correctness, measured task performance and superiority are distinct gates.
The preregistered informative success threshold is 50%, with at least one
informative success in every family; superiority additionally
requires positive paired net success wins against **each** control. Equal-success
cost comparisons are reported separately. Development alone never closes the
confirmation gate. These finite numerical criteria are not a statistical proof
of general superiority.

## Diary events

The optional journal implements only `write(kind=..., **facts)`, compatible with
`echo5.trace.Recorder`; envelope fields remain owned by that recorder. Events:
`sandbox_reset`, `sandbox_step`, `sandbox_stop`, `sandbox_error`,
`sandbox_case_start`, `sandbox_adjudication`, `sandbox_instrument_error`.
Step events include the consumed observation, visible objects, hypotheses,
pre-action prediction, selected action, actual next observation, consequence,
memory and remaining budgets. Adjudication events are labelled evaluator output
and never become actor input. No generated inner monologue is recorded.

## Isolated setup and deferred reproduction

Only `.venv-sandbox` is used. The base ECHO-5 `.venv`, global packages, older
environments and frozen sources are not modified. The setup pins every runtime
dependency and verifies wheel hashes from PyPI release metadata. No training
extras, Torch, models, credits or cloud services are required.

```sh
cd /home/user/REALRXOS/RXos/echoai/ECHO-5
python3.12 -I scripts/setup_sandbox.py
python3.12 -I scripts/setup_sandbox.py --check
```

Setup uses the system CPython 3.12.13 `venv`, with global site packages disabled,
then invokes pip only through `.venv-sandbox/bin/python`. It never calls make,
reset, step, a unit test or an experiment. `--check` checks imports/versions only.
Runtime has no actor network client or LLM. This is a data-flow boundary, not an
OS network sandbox or isolation from hostile in-process Python introspection.

After **all** closure code is programmed and the owner releases CPU execution:

```sh
.venv-sandbox/bin/python -I tests/test_sandbox.py
.venv-sandbox/bin/python -I scripts/control.py
```

The unit file is stdlib-discoverable in the base environment; dependency-backed
tests explicitly skip if pins are missing. That skip is not a native capability
pass. The separate sandbox interpreter must run the native suite before claiming
correctness. No test or benchmark result is asserted by this implementation note.

To run and persist a development benchmark later without changing the shared CLI:

```sh
.venv-sandbox/bin/python -I - <<'PY'
import json, pathlib, sys
root = pathlib.Path.cwd()
sys.path.insert(0, str(root / 'src'))
from echo5.sandbox_eval import run_benchmark
from echo5.trace import Recorder
folder = root / 'artifacts' / 'sandbox-development-new'
folder.mkdir(parents=True, exist_ok=False)
with Recorder(folder / 'thought.jsonl') as journal:
    report = run_benchmark({'split': 'development', 'cases_per_family': 2}, journal)
(folder / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
PY
```

Preserve new output directories, manifests and the numerical contract. Never
overwrite a previous run, reuse old closed campaigns, or adjust the confirmation
denominator after seeing results. Compilation/import evidence and deferred
functional checks must remain distinguished in the handoff.
