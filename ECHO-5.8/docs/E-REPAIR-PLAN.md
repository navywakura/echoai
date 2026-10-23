# E repairs · implementation plan

Spec: SHIELD2-DESIGN.md then E-BUSQUEDA-REPAIR-DESIGN.md (22 October 2026).
Execution: inline in existing isolated worktree 001f; one fresh whole-code review
before freezing each measurement. No commits, merges, APIs, publication or exams.

## Task 1: SHIELD-2 integer decisions and boundary
Interfaces: immutable learned table -> Controller; observable lidar/motion/speed ->
decision; decision -> original or regulated Car actuator. Write tests first:
legacy exact actions over headings/speeds; margin boundaries; brake precedence;
learned channel selection; no floats in core. Expected RED absent module, GREEN
all targeted tests. Reuse original Gate/functions without modifications.

## Task 2: SHIELD-2 evidence and execution
Interfaces: phase agenda + frozen source manifest -> runner; per-step gzip JSONL
and exclusive episode receipts -> auditor/report. Tests first with fake env:
training observes after-step; validation cannot mutate table; real termination;
technical exceptions durable and inconclusive; tamper/missing evidence fails.
Record sources, package versions, phase boundaries and learned table before
validation. Reviewer check; integrate only new files; run targeted tests again.
Freeze then execute 40 training, 10 diagnostic, 200 validation episodes, <=4CPU.
Audit every trace, aggregate gate, report honestly. No tuning after freeze.

## Task 3: Search repair using existing public solver
Interfaces: frozen independent cases -> public-only tasks -> existing solver ->
external evaluator. Tests first: actor has no expected/witness; configuration
fixed; budget/consensus abstention; score/audit tampering. No engine edits.
Reviewer check before freeze; 32 tasks x4 beam widths, same2M work each.
Archive cases before solving. Audit actual programs/predictions and accounting
without replaying search. Report whichever result, no retrospective arm change.

## Task 4: Closure
Update result docs, roadmap and handoff. Verify frozen hashes and targeted tests.
Show updated roadmap in final response and recommend next concrete work.
