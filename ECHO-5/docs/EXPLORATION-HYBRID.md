# Bounded opt-in hybrid exploration

Development change, 2026-10-11. `frontier_hybrid` is a fixed symbolic policy;
it has no learned gate, additional skills, LLM, environment handle, world seed,
hidden grid, reward input or success oracle. Native adjudication remains outside
the actor. Small contract tests are development evidence, not a scientific result.

## API and compatibility

```python
ObservationActor(mode='frontier_hybrid')
Session({'mode': 'frontier_hybrid', ...}, journal=journal)
report = exploration_study.run_benchmark(config, journal=journal)
audit = exploration_study.audit_benchmark(report)  # fresh process, same frozen sources
```

`normalize_spec` accepts the new opt-in mode. Its default remains `informative`.
`MODES` and the original three-member `EXPLORATION_MODES` remain unchanged;
`EXPLORATION_OPTIONS` includes hybrid. Historical modes retain their selection,
work accounting and traces. No dependencies were added.

`exploration_study.normalize_config` accepts exactly the original ordered three
arms or all four distinct arms. Partial, duplicate and unknown cohorts fail.
All four can be reordered explicitly; the registered main plan below retains the
original order with hybrid last. Omitting `modes` retains the original three arms,
seed 1400000, seven profiles and four cases per profile: 28 worlds / 84 episodes.
Profile offsets and IDs remain `base_seed + profile_index * 1000 + case_index`.

The existing runner and auditor use the configured arms throughout case creation,
complete-pair validation, aggregation and native replay. Comparisons are first arm
minus each subsequent arm, including work differences. Thus the registered fourth
contrast entry `frontier_hybrid` compares **information minus hybrid**. There are
three contrasts in the four-arm report; Hoeffding intervals use `.05 / 3` per
contrast, versus the unchanged `.025` in the historical three-arm report. Exact
discordance p-values remain descriptive, unadjusted values. No confirmation,
promotion, equivalence or success advantage is granted by this pilot API.

## Observable gate and bounds

The existing mission, prerequisite and path planners run first, with the same
skills, observation-acquired map, inventory rules and logical-work budget. If
they return a plan, hybrid uses it and records phase `goal`, without information
scoring. Exploration uses nearest by default, with these two possible triggers:

- `observed_mission_blockage`: an active mission requirement has an observed
  match, but the shared bounded planner found no supported goal/prerequisite
  plan. Ordered missions inspect only the first incomplete step. When carrying
  the correct `putnext` target, the requirement is its reference object. An
  unseen target/reference or an unrelated closed/locked door is insufficient.
  This is blockage **relative to observed memory and the bounded planner**,
  not proof that no route exists in the actual world.
- `observation_stagnation`: eight consecutive action observations add no new
  mapped cell or visited pose, change no remembered cell or inventory, and add
  no supported subgoal. The counter saturates at eight and resets on any such
  progress. Choosing again or polling snapshots cannot advance it.

Each triggered information phase permits at most **two new scored selections**
within **four subsequent observation steps**. A new phase cannot start until
**eight more observation steps after that four-step window**: earliest restart
is trigger tick + 12. Losing the trigger or obtaining a mission plan ends the
phase early without shortening this cooldown. Persistent blockage during the
cooldown is still reported, with phase `nearest`. The normal action and work
limits remain authoritative; no hidden reserve or separate scoring budget exists.

All arms retain their destination until its pose is visited, its route disappears,
or it no longer meets frontier eligibility. A gate change alone never discards a
valid destination. Even phase `information` avoids scoring while a destination is
still valid. When no eligible candidates exist, shared relocation/scan fallback
behavior applies.

## Eligibility, cost and limits of attribution

Hybrid's unscored enumeration applies the **same eligibility predicate** as the
historical selectors: a reachable, unvisited pose with a nonempty route and at
least one predicted unknown cell along the existing three bounded view rays,
stopping at remembered walls or non-open doors. It stops at the first unknown
cell instead of counting every predicted unknown cell. Such candidates carry
`None` for information gain; zero is not invented as an estimate.

Ordinary selection does not call `_frontier_candidates` or consume
`information_candidate` / `information_ray` work. It does consume
`frontier_candidate`, `frontier_visibility_probe`, commitment lookup and ranking
work. This is a lazy eligibility test, not free visibility. In the worst case it
still probes three view-length rays per candidate. The existing heap-based path
search, route matching, sorting and enumeration all scale with their inputs;
there is **no O(1) pathfinding claim**. Planner guards and the common work budget
bound execution.

On a triggered new selection, hybrid calls the existing full information scorer
and information selector. Both the eligibility work and the subsequent full
scoring work are charged. `hybrid_progress`, `hybrid_gate` and
`hybrid_mission_match` charge its extra observation/gate bookkeeping. All arms
have identical available observations, skills, memory semantics, path planner,
frontier eligibility, commitment rule, policy seed 0 and episode budget limits.

**Both historical nearest and information controls pay the full ray estimate.**
They are intentionally preserved. A hybrid cost benefit could therefore come
from lazy scoring/eligibility optimization, from the fixed switching rule, or
both. These four arms do not isolate a causal benefit of switching, and cannot
establish learned blockage detection. A separate, preregistered lazy-nearest
ablation would be needed to isolate that attribution; it is not added here.
Logical work is not FLOPs, elapsed time or energy.

## Actual decision events

The existing `Recorder` / `thought.jsonl` channel receives the decision through
`sandbox_step.hypotheses.exploration`; receipts also contain
`transcript[].decision.exploration`. No new bus or viewer-to-policy input exists.
Exploration decisions report:

- `phase`: `nearest` or `information`; `trigger` and its `trigger_evidence`.
- Observation tick, phase start, information deadline, cooldown deadline and
  remaining selection quota.
- `information_scoring_attempted` and `information_scored`, distinguishing a
  started but budget-exhausted computation from a completed one.
- Candidate count, continued-target flag, relative target pose, and the predicted
  unknown count only when it was actually computed for this decision.

Goal and manual decisions explicitly use phases `goal` and `manual` with no
trigger/scoring claim. Manual actions cannot inherit a previous automatic trigger.
When scoring exhausts the budget, `sandbox_stop` can export the gate already
computed. If work ends before the gate executes, no trigger is fabricated.
The trace is detached reporting data; the actor never reads it back as instructions.
Read new development diaries with the existing mini-terminal viewer, for example
`python3 ../observe.py --technical /absolute/path/to/thought.jsonl`, while the
runner writes them. Do not attach instrumentation to sealed historical campaigns.

## Registered main study — pending freeze and execution

**Update, 2026-10-12:** the combined runner has now completed this registered
study and its independent-process audit. See the
[measured results](SEARCH-EFFICIENCY-RESULTS-20261012.md): hybrid 28/28, the same
332 actions as nearest, and 4.45% less logical work. No information phase was
triggered in these worlds, so switching utility remains unmeasured. The text
below preserves the original preregistration; r2 and r3 replay the same worlds
and are not additional independent samples.

The owner froze sources before the scientific campaign. This configuration
registers **28 worlds and 112 episodes**, with original-order arms and hybrid last.
At the time of implementation it had not been run as a campaign. Tiny native smoke tests use a
separate seed (1480000); they do not execute the registered 1440000-series worlds.

```json
{
  "seed": 1440000,
  "cases_per_profile": 4,
  "actions": 256,
  "work": 750000,
  "profiles": [
    "objects_small", "objects_medium", "objects_large",
    "key_small", "key_medium", "ordered_doors", "put_next"
  ],
  "modes": [
    "frontier_information", "frontier_nearest", "frontier_random", "frontier_hybrid"
  ],
  "policy_seed": 0,
  "practical_success_difference": 0.1,
  "confirmation": false
}
```

The first ID is `objects_small:1440000`; the last is `put_next:1446003`.
Every arm receives the same generated task/options, native mission and budget
for each ID. Store new reports and thought journals in a fresh output directory;
audit in another process against the same frozen source manifest.

The [historical report](REMEDIATION-RESULTS-20261011.md) is immutable: all original
arms succeeded on 28/28; information used 300 actions / 232985 work, nearest
309 actions / 231435 work. These results are not hybrid results and are not
recomputed or relabelled by the new study.

## Small verification only

From ECHO-5, run the new contract tests and existing exploration regressions in
the pinned native environment (the base `.venv` skips optional native tests):

```sh
make check
.venv-sandbox/bin/python -B -I - <<'PY'
import sys, unittest
sys.path[:0] = ['src', 'tests']
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_exploration_hybrid', 'test_exploration_controls', 'test_exploration_study'])
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
PY
```

Tests cover no-scoring ordinary choices, active blockage versus unrelated doors,
ordered/relational requirements, stagnation, bounded phases/cooldown, commitment,
budget exhaustion, public-input boundaries, original defaults and world IDs,
complete four-arm validation, real thought events, and small native run/replay.
The native hybrid smoke tests cap activity at nine actions in one session and
one action per arm in one separate world, plus their replays. Full suites and
scientific campaigns remain the responsibility of the subsequent freeze/run.
