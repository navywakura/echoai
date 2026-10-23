# SHIELD-2 slow confirmation · implementation plan

> **For agentic workers:** Use superpowers:executing-plans; implement inline,
> with one fresh whole-code reviewer before freezing. Track checkboxes here.

**Goal:** Confirm the unchanged slow controller against legacy in two new
learning lineages and100 paired development seeds, with an honest U/B verdict.
**Architecture:** Reuse Controller, play, audit_episode and summary from frozen
SHIELD-2. Add only protocol, orchestration and custody audit in shieldconfirm.
**Tech Stack:** Python3.10, existing safe1 virtualenv; stdlib orchestration.
**Spec:** ECHO-5.8/docs/SHIELD2-SLOW-CONFIRM-DESIGN.md.

## Global Constraints

- Only SafetyCarGoal2-v0, no exams, LLM, installation, publication or old-file edits.
- Fixed280 episodes;40 training per replica,50 paired validation seeds per replica.
- Training state separate; all80 complete and both tables committed before validation.
- At most4 simulation processes. No automatic retries, omission or early cost stop.
- Slow remains300mm/s and margin3; no candidate/policy changes after results.
- U and B separate; full development green requires both plus successful audit.
- No commits/merge/cleanup requested. Reuse managed isolated worktree001f.

## Review Focus

- Close/setup/worker failure after a completed receipt: durable failure and no green.
- Coincidentally equal table hashes: allowed; lineage/empty starts must be separate.
- One insensitive replica: U inconclusive, never promoted by pooled averages.
- Ties, zero pairs or exact p=0.05 boundary: integer sign test, no float rounding.
- Missing/swapped/extra episode or absent phase commitment: audit rejects.

## Task 1: fixed protocol and gates

Files: create echo58/shieldconfirm/{__init__,protocol}.py;
tests/test_echo58_shieldconfirm.py.
Interfaces: agenda()->list[dict(replica,phase,arm,seed)]; assess(validation_rows)
returns by-replica/pooled summary, exact sign fraction, U, B and full-green.
- [x] Write failing tests for280 exact jobs/disjoint seeds, pair matching,
  per-replica regressions, sensitivity, sign ties/bounds and residual tail.
- [x] Run targeted unittest: expected missing-module RED.
- [x] Implement exact agenda and integer criteria; no simulator imports.
- [x] Run targeted tests: expected GREEN; record evidence in ledger.

## Task 2: frozen runner and lifecycle

Files: create echo58/shieldconfirm/bench.py; extend same tests.
Consumes Task1 agenda, inherited core/boundary/custody. Produces source freeze,
exclusive280 receipts/traces, two table files, chained phase commits and run end.
- [x] Tests first for lifecycle order/membership and durable pre-episode failure.
  Expect RED absent functions.
- [x] Implement prepare/check_sources, train_replica, validation_job, run.
  Each wrapper catches outer failures; global training barrier enforced.
- [x] Verify with fake env/executor, never actual worlds before freeze.
- [x] Run new and original SHIELD targeted tests; expected GREEN.

## Task 3: audit, measurement and closure

Files: create echo58/shieldconfirm/audit.py; extend tests. Results doc and roadmap.
Consumes evidence from Task2, audit_episode from SHIELD-2, assess from Task1.
- [x] RED tests: wrong replica/context/table, missing phase or failed run cannot pass.
- [x] Implement verify_lifecycle and audit: exact set, chains, training continuity,
  frozen matching tables and gate math; preserve recorded-state replay limitation.
- [x] Fresh whole-code reviewer before measurement; fix Important issues with
  observed RED→GREEN regressions in one pass. No simulation by reviewer.
- [x] Integrate only new reviewed files byte-identically to stable paths; test again.
- [x] Freeze before worlds, then train80 and validate200, audit all280 traces.
- [x] Report U/B/full status even red/inconclusive; final hashes and source checks.
- [x] Update roadmap/handoff; include visible roadmap and concrete next step in final.
