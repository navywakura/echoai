# Catálogo completo de módulos Python

Generado mediante `scripts/inventory.py`.
Cada fila describe un archivo, no una capacidad independiente. Los roles son orientativos.
Imports y menciones documentales no equivalen a pruebas ejecutadas ni cobertura.

Archivos: 981. Errores de parseo: 0.

Detalle de símbolos, hashes, imports, consumidores, tests y documentos: [modules.json](modules.json).

## .. — 6 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [../navi10_cam.py](../../../../navi10_cam.py) | NAVI 10 — CAM / memoria asociativa Heap-0. | 1 | 13 |
| [../navi10_dag.py](../../../../navi10_dag.py) | NAVI 10 — Dynamic Attractor Generator. | 2 | 1 |
| [../navi10_qn.py](../../../../navi10_qn.py) | NAVI 10 — Q_N mesh (Q8 × Q8). | 0 | 5 |
| [../navi10_spoke.py](../../../../navi10_spoke.py) | NAVI 10 — Stream-to-Spoke. | 1 | 1 |
| [../navi10_stdp.py](../../../../navi10_stdp.py) | NAVI 10 — STDP entero + neuromodulación E[6]. | 1 | 0 |
| [../navi10_wsp.py](../../../../navi10_wsp.py) | NAVI 10 — evento → postal WSP de 16 B. | 1 | 11 |

## __init__.py — 1 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [__init__.py](../../../__init__.py) | echoAI MONAD workspace. See echoai/CLAUDE.md. | 0 | 2 |

## echo4 — 109 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [echo4/__init__.py](../../../echo4/__init__.py) | ECHO-4 functional-self experiments; no hardware or parallel cognition. | 0 | 36 |
| [echo4/__main__.py](../../../echo4/__main__.py) | python -m echoai.echo4 {audit,demo,sensation-audit}; JSON stdout only. | 4 | 2 |
| [echo4/adapter.py](../../../echo4/adapter.py) | Adapt the new physics to the existing Agent, without a new policy or bus. | 3 | 1 |
| [echo4/arc2_bench.py](../../../echo4/arc2_bench.py) | E4-BENCH-ARC2 · ARC-AGI-2 with a model alone, with ECHO verifying its programs, and ECHO alone. | 1 | 0 |
| [echo4/arc3_agent.py](../../../echo4/arc3_agent.py) | E4-BENCH-ARC3 · ECHO-ARC3: ECHO's pieces playing ARC-AGI-3 without a language model. | 4 | 0 |
| [echo4/arc3_llm.py](../../../echo4/arc3_llm.py) | E4-BENCH-ARC3-LLM · a language model plays ARC-AGI-3, alone and with ECHO. | 2 | 0 |
| [echo4/arc3_llm2.py](../../../echo4/arc3_llm2.py) | E4-BENCH-ARC3-LLM2 · the model solves ARC-AGI-3 using ECHO as its laboratory. | 3 | 0 |
| [echo4/arc3_view.py](../../../echo4/arc3_view.py) | See what ECHO saw and did in an ARC-AGI-3 game: replay a recorded game and draw every frame. | 1 | 0 |
| [echo4/audit.py](../../../echo4/audit.py) | Read-only world/observation audit. Full-state truth stays here, not in Q. | 4 | 2 |
| [echo4/bench1.py](../../../echo4/bench1.py) | E4-BENCH-1 A · the same model with and without ECHO on public benchmarks. | 4 | 1 |
| [echo4/boundary.py](../../../echo4/boundary.py) | Bounded interventional influence map. Public observations/receipts only. | 4 | 2 |
| [echo4/boundary_agent.py](../../../echo4/boundary_agent.py) | Opt-in attachment; no replacement of Agent Q, gate, CAM, T or SENSATION. | 2 | 0 |
| [echo4/boundary_bench.py](../../../echo4/boundary_bench.py) | Reproducible BOUNDARY-1 campaign and full replay auditor (separate CLI). | 7 | 1 |
| [echo4/boundary_world.py](../../../echo4/boundary_world.py) | Private experiment executor/judge. Never imported by the consumer. | 6 | 6 |
| [echo4/code_exam.py](../../../echo4/code_exam.py) | Independent E4-CODE-1 A exam against the frozen corpus. | 0 | 0 |
| [echo4/code_gate.py](../../../echo4/code_gate.py) | E4-CODE-1 A · gate for a coding agent's shell commands: OK \| MODIFY \| BLOCK. | 0 | 1 |
| [echo4/code_mcp.py](../../../echo4/code_mcp.py) | E4-CODE-1 A · MCP server "echoai-verify" (stdio, JSON-RPC 2.0, no dependencies). | 3 | 1 |
| [echo4/code_memory.py](../../../echo4/code_memory.py) | E4-CODE-1 A · verified memory for a coding agent. | 4 | 1 |
| [echo4/continuity.py](../../../echo4/continuity.py) | CONT-A executor checkpoint, not a cognitive bus or a general deserializer. | 12 | 10 |
| [echo4/continuity_active.py](../../../echo4/continuity_active.py) | CONT-B executor custody for the existing SELF session and active agents. | 11 | 1 |
| [echo4/continuity_active_bench.py](../../../echo4/continuity_active_bench.py) | CONT-B development campaign: full state, fresh process, read-only replay. | 11 | 2 |
| [echo4/continuity_bench.py](../../../echo4/continuity_bench.py) | CONT-A development evidence, with fresh-process resume; not full closure. | 4 | 1 |
| [echo4/continuity_final_audit.py](../../../echo4/continuity_final_audit.py) | CONT-D source-locked A/B/C exam and independently reconstructive closure. | 2 | 4 |
| [echo4/continuity_final_cases.py](../../../echo4/continuity_final_cases.py) | CONT-D fixed recipes and negative controls; imports sealed A/B/C runtimes. | 13 | 1 |
| [echo4/continuity_graph.py](../../../echo4/continuity_graph.py) | CONT-B closed graph codec. CONT-A's source-pinned codec stays untouched. | 2 | 0 |
| [echo4/continuity_lineage.py](../../../echo4/continuity_lineage.py) | CONT-C: executor-owned lineage, not a policy or subjective identity. | 8 | 1 |
| [echo4/continuity_lineage_bench.py](../../../echo4/continuity_lineage_bench.py) | CONT-C development recipes, full-state continuations and independent replay. | 10 | 1 |
| [echo4/demo.py](../../../echo4/demo.py) | Bounded single-life integration smoke; learning stays on, never a certificate. | 3 | 3 |
| [echo4/dream_bench.py](../../../echo4/dream_bench.py) | DREAM-B/C/D closed-loop campaign and reconstruction, local LLM opt-in. | 10 | 4 |
| [echo4/dream_history.py](../../../echo4/dream_history.py) | DREAM-A private archive and public partial replay; no environment execution. | 1 | 4 |
| [echo4/dream_history_bench.py](../../../echo4/dream_history_bench.py) | DREAM-A native discovery-history increment, not a DREAM-1 closure. | 5 | 1 |
| [echo4/dream_policy.py](../../../echo4/dream_policy.py) | DREAM bounded strategy interpreter. No model, physics executor or file access. | 3 | 2 |
| [echo4/dream_probe.py](../../../echo4/dream_probe.py) | DREAM restored-probe histories. Execution is confined to collect/native. | 8 | 2 |
| [echo4/dream_qwen.py](../../../echo4/dream_qwen.py) | Opt-in local Qwen proposer with fixed weights and recorded HTTP receipts. | 5 | 2 |
| [echo4/dream_v2.py](../../../echo4/dream_v2.py) | DREAM-D v2: replay feedback, robust selection and anchored promotion. | 9 | 1 |
| [echo4/dream_v2_bench.py](../../../echo4/dream_v2_bench.py) | DREAM-D v2 campaign; prospective exams, real local Qwen and full audit. | 7 | 1 |
| [echo4/dream_v3.py](../../../echo4/dream_v3.py) | DREAM-v3 evaluation and history-only policy development, fixed weights. | 11 | 1 |
| [echo4/dream_v3_bench.py](../../../echo4/dream_v3_bench.py) | Prospective DREAM-D v3 campaign and independent full reconstruction. | 10 | 1 |
| [echo4/dream_v3_development.py](../../../echo4/dream_v3_development.py) | Development on already-open bodies; never grants prospective DREAM green. | 6 | 0 |
| [echo4/dream_v3_profile.py](../../../echo4/dream_v3_profile.py) | Versioned DREAM-v3 probes and conditional replay; original SELF is sealed. | 7 | 1 |
| [echo4/dream_v3_screen.py](../../../echo4/dream_v3_screen.py) | Reproducible prior screening on opened v2 cycle2, NOT execution evidence. | 8 | 0 |
| [echo4/integrate.py](../../../echo4/integrate.py) | E4-INTEGRATE-1 «una sola vida»: ECHO's body and tribe share one CAM/T/Q. | 12 | 2 |
| [echo4/integrate_bench.py](../../../echo4/integrate_bench.py) | E4-INTEGRATE-1 development bench: one life, seven arms, adversarial cases, profile. | 8 | 0 |
| [echo4/integrate_exam.py](../../../echo4/integrate_exam.py) | E4-INTEGRATE-1 exam: the approved D contract on 16 new seeds. | 6 | 0 |
| [echo4/interaction_bench.py](../../../echo4/interaction_bench.py) | INTERACTION-A mechanics and native wiring, not an INTERACTION closure. | 8 | 1 |
| [echo4/interaction_cases.py](../../../echo4/interaction_cases.py) | Development and adverse witnesses. No held-out cohort execution on import. | 4 | 1 |
| [echo4/interaction_final.py](../../../echo4/interaction_final.py) | Source-locked INTERACTION B/C/D campaign and fresh-process reconstruction. | 7 | 1 |
| [echo4/interaction_learning.py](../../../echo4/interaction_learning.py) | Derived, non-factual OTHER beliefs index the existing native Q, not a new Q. | 6 | 1 |
| [echo4/interaction_session.py](../../../echo4/interaction_session.py) | Two original Agent.turn calls, one atomic joint consequence, private memory. | 5 | 1 |
| [echo4/interaction_social.py](../../../echo4/interaction_social.py) | Three private native learners, two atomic turns per scheduled encounter. | 9 | 2 |
| [echo4/interaction_world.py](../../../echo4/interaction_world.py) | Costed joint-action physics; no policy, peer-memory reads or implicit gifts. | 2 | 1 |
| [echo4/maintain_agent.py](../../../echo4/maintain_agent.py) | Opt-in MAINT-A wiring. One original CAM/T/Q/gate, no new action policy. | 2 | 1 |
| [echo4/maintain_bench.py](../../../echo4/maintain_bench.py) | MAINT-A mechanism preflight: native execution, source lock, reconstruction. | 10 | 1 |
| [echo4/maintain_continuity.py](../../../echo4/maintain_continuity.py) | MAINT-C private custody using the existing CONT graph codec and validator. | 10 | 1 |
| [echo4/maintain_control.py](../../../echo4/maintain_control.py) | Explicit MAINT-B model-assisted proposal; original Q/T/CAM/gate still run. | 2 | 1 |
| [echo4/maintain_final.py](../../../echo4/maintain_final.py) | MAINT B/C/D source-locked development, prospective exam and native audit. | 10 | 1 |
| [echo4/maintain_model.py](../../../echo4/maintain_model.py) | Bounded, observation-only MAINT belief; known mechanics are an explicit prior. | 6 | 1 |
| [echo4/maintain_world.py](../../../echo4/maintain_world.py) | MAINT-A private physical fixture; original WORLD-1 transition is reused. | 3 | 2 |
| [echo4/other_bench.py](../../../echo4/other_bench.py) | OTHER development, source-locked exams, observation replay and native audit. | 10 | 1 |
| [echo4/other_model.py](../../../echo4/other_model.py) | OTHER: bounded observer on the agent's existing CAM/T, no private peer API. | 5 | 4 |
| [echo4/other_replay.py](../../../echo4/other_replay.py) | Reconstruct observation-only OTHER memory; never execute a peer or world. | 5 | 2 |
| [echo4/other_world.py](../../../echo4/other_world.py) | Private independent choice worlds. Native Agent/Q/gate choose every action. | 5 | 1 |
| [echo4/relation_b_bench.py](../../../echo4/relation_b_bench.py) | RELATION-B development bench. Development seeds only; never an exam. | 7 | 1 |
| [echo4/relation_bench.py](../../../echo4/relation_bench.py) | RELATION-A history/provenance benchmark; never grants relational transfer. | 9 | 1 |
| [echo4/relation_c.py](../../../echo4/relation_c.py) | RELATION-C: rupture, reunion, same identity with another body, and limits. | 8 | 1 |
| [echo4/relation_c_bench.py](../../../echo4/relation_c_bench.py) | RELATION-C witnesses on development seeds. Limits are published, not hidden. | 9 | 0 |
| [echo4/relation_d.py](../../../echo4/relation_d.py) | RELATION-D preregistered exam. Opening D requires the freeze approval. | 7 | 0 |
| [echo4/relation_help.py](../../../echo4/relation_help.py) | RELATION-B help task: A history, recorded in each agent's own CAM, indexes B. | 9 | 2 |
| [echo4/relation_memory.py](../../../echo4/relation_memory.py) | Bounded observed encounter history in the agent's existing CAM. | 8 | 2 |
| [echo4/relation_session.py](../../../echo4/relation_session.py) | Passive relation history on original native social executions, not transfer. | 2 | 1 |
| [echo4/roles.py](../../../echo4/roles.py) | E4-ROLES-1 A/B: who executes each task type, from observed recent competence. | 12 | 2 |
| [echo4/roles_bench.py](../../../echo4/roles_bench.py) | ROLES-1 A/B development bench. Development seeds only; never an exam. | 6 | 1 |
| [echo4/roles_c.py](../../../echo4/roles_c.py) | ROLES-C: refusal, intermediary relay, new member, absence, and a veto fix. | 8 | 2 |
| [echo4/roles_c_bench.py](../../../echo4/roles_c_bench.py) | ROLES-C witnesses on development seeds. Limits are published, not hidden. | 7 | 0 |
| [echo4/roles_d.py](../../../echo4/roles_d.py) | ROLES-D preregistered exam. Opening D requires the freeze approval. | 8 | 0 |
| [echo4/roles_v2.py](../../../echo4/roles_v2.py) | ROLES-1 v2: the only change is native periodic exploration for the learner. | 9 | 1 |
| [echo4/self_agent.py](../../../echo4/self_agent.py) | SELF-A opt-in observation hook; no change to policy or historical loops. | 3 | 4 |
| [echo4/self_attribution.py](../../../echo4/self_attribution.py) | SELF-B: finite, model-conditional diagnosis from public observations. | 6 | 4 |
| [echo4/self_audit.py](../../../echo4/self_audit.py) | SELF-A identifiability census. Private truth never enters SelfChangeMonitor. | 7 | 2 |
| [echo4/self_final.py](../../../echo4/self_final.py) | Bounded confirmation session; no executor, body readings or private labels. | 2 | 2 |
| [echo4/self_final_audit.py](../../../echo4/self_final_audit.py) | Joint SELF-1 exams: native reuse/lives, abstention, source lock and full replay. | 14 | 1 |
| [echo4/self_final_world.py](../../../echo4/self_final_world.py) | Private falsification mechanisms. Never imported by SelfSession/readout. | 6 | 1 |
| [echo4/self_model.py](../../../echo4/self_model.py) | SELF-A: observed change is not yet self/world attribution. | 1 | 1 |
| [echo4/self_probe_agent.py](../../../echo4/self_probe_agent.py) | Opt-in diagnostic factory; ordinary SelfAgent behavior remains unchanged. | 2 | 2 |
| [echo4/self_probe_audit.py](../../../echo4/self_probe_audit.py) | SELF-B development census and fresh replay; never a full SELF green. | 8 | 3 |
| [echo4/self_probe_world.py](../../../echo4/self_probe_world.py) | Private supervised executor for longer probes; never imported by inference. | 5 | 5 |
| [echo4/self_recovery.py](../../../echo4/self_recovery.py) | SELF-C: bounded public-observation belief and selective learning permission. | 2 | 3 |
| [echo4/self_recovery_agent.py](../../../echo4/self_recovery_agent.py) | SELF-C on the existing loop's self_model hook, with one CAM/T/Q. | 3 | 4 |
| [echo4/self_recovery_audit.py](../../../echo4/self_recovery_audit.py) | SELF-C development experiment: actual Agent turns and private replay judge. | 9 | 3 |
| [echo4/self_recovery_world.py](../../../echo4/self_recovery_world.py) | Private SELF-C executor: original physics, continuous life, no rescues. | 2 | 2 |
| [echo4/self_reuse.py](../../../echo4/self_reuse.py) | Bounded T readout. No physics, body registers or diagnostic labels. | 5 | 1 |
| [echo4/self_reuse_agent.py](../../../echo4/self_reuse_agent.py) | Native one-step laboratory trials and read-only reuse of the same T. | 4 | 1 |
| [echo4/self_reuse_audit.py](../../../echo4/self_reuse_audit.py) | SELF-C v2: matched exposure, native T-based task execution, full replay. | 9 | 3 |
| [echo4/sensation.py](../../../echo4/sensation.py) | Bounded local history of existing WSP observations, not a new bus. | 2 | 1 |
| [echo4/sensation_agent.py](../../../echo4/sensation_agent.py) | Opt-in native Agent prediction hook; Q, gate and world remain original. | 4 | 2 |
| [echo4/sensation_audit.py](../../../echo4/sensation_audit.py) | External exhaustive temporal audit. Never imported by the agent. | 4 | 1 |
| [echo4/sensation_campaign.py](../../../echo4/sensation_campaign.py) | Prospective learned-prediction campaign; physics stays outside learner API. | 7 | 1 |
| [echo4/sensation_predictor.py](../../../echo4/sensation_predictor.py) | Integer sensory prediction using the existing CAM, T and PATTERN-0. | 7 | 2 |
| [echo4/situate.py](../../../echo4/situate.py) | E4-SITUATE-1 «sé qué soy»: substrate facts ECHO verifies itself. | 8 | 1 |
| [echo4/situate2.py](../../../echo4/situate2.py) | E4-SITUATE-2 «qué creo que soy»: the neocortex interprets, the core decides. | 7 | 1 |
| [echo4/situate2_bench.py](../../../echo4/situate2_bench.py) | SITUATE-2 bench: real local Qwen (fixed weights) proposes; ECHO's core decides. | 9 | 1 |
| [echo4/situate_bench.py](../../../echo4/situate_bench.py) | SITUATE-1 bench: every condition runs in fresh child processes. | 7 | 0 |
| [echo4/tribe.py](../../../echo4/tribe.py) | E4-ROLES-1 v3 «la tribu»: elimination, derived rank, role reversal. | 10 | 5 |
| [echo4/tribe_exam.py](../../../echo4/tribe_exam.py) | ROLES-1 v5 «razonar la tribu»: C witnesses, development and preregistered D. | 6 | 3 |
| [echo4/tribe_liar.py](../../../echo4/tribe_liar.py) | ROLES-1 annex L: B lies affirmatively ("I know") in a random share of cases. | 8 | 2 |
| [echo4/tribe_liar2.py](../../../echo4/tribe_liar2.py) | ROLES-1 annex L v2: metaknowledge, "and what if I have it?". | 10 | 1 |
| [echo4/tribe_v4.py](../../../echo4/tribe_v4.py) | ROLES-1 v4: the deduction proposes an ordered candidate list; Q decides. | 5 | 1 |
| [echo4/viability.py](../../../echo4/viability.py) | Full-state feasibility oracle. Never imported by the ECHO decision path. | 2 | 2 |
| [echo4/world.py](../../../echo4/world.py) | WORLD-1: bounded integer physics, independent of the agent and auditor. | 1 | 15 |

## echo_arc — 51 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [echo_arc/__init__.py](../../../echo_arc/__init__.py) | echo-arc: ECHO for ARC Prize 2026 (self-contained; CC-BY 4.0 if it wins). | 0 | 34 |
| [echo_arc/agent.py](../../../echo_arc/agent.py) | echo-arc · ECHO's ARC-AGI-3 agent, self-contained (ARC Prize 2026 submission package). | 0 | 10 |
| [echo_arc/consumer_observe.py](../../../echo_arc/consumer_observe.py) | Development-only observations of actual wait-control consumption. | 6 | 1 |
| [echo_arc/consumer_requests.py](../../../echo_arc/consumer_requests.py) | Draft next-condition prompt evidence; not used by frozen B8/CPU inference. | 3 | 1 |
| [echo_arc/consumption_evidence.py](../../../echo_arc/consumption_evidence.py) | Exact observed native HOLD assignments; separate from frozen B8 heuristics. | 2 | 1 |
| [echo_arc/consumption_timeline.py](../../../echo_arc/consumption_timeline.py) | Passive development control reads with explicit decision/outcome alignment. | 3 | 2 |
| [echo_arc/context_requests.py](../../../echo_arc/context_requests.py) | B12: deterministic context budgeting after B11's development-only selection. | 4 | 1 |
| [echo_arc/context_tokenizer.py](../../../echo_arc/context_tokenizer.py) | Offline token counting only, in the separate S6 tokenizer environment. | 0 | 0 |
| [echo_arc/contrastive_evidence.py](../../../echo_arc/contrastive_evidence.py) | B11: passive development trajectories and paired, allowlisted feedback. | 5 | 4 |
| [echo_arc/contrastive_grammar.py](../../../echo_arc/contrastive_grammar.py) | Shared B11 applicability grammar: observations constrain syntax, not utility. | 5 | 5 |
| [echo_arc/contrastive_requests.py](../../../echo_arc/contrastive_requests.py) | Adaptive evidence selection versus a fixed generic request, equal interfaces. | 5 | 1 |
| [echo_arc/cost_guard_search.py](../../../echo_arc/cost_guard_search.py) | B19: acceptance-aware development search; no protected data or known guard. | 9 | 1 |
| [echo_arc/feasible_grammar.py](../../../echo_arc/feasible_grammar.py) | Mechanical witness compatibility, shared by both arms; no outcome ranking. | 4 | 4 |
| [echo_arc/feasible_requests.py](../../../echo_arc/feasible_requests.py) | A smaller, witnessed repair question; protected feedback stays a boolean. | 4 | 1 |
| [echo_arc/guard_search.py](../../../echo_arc/guard_search.py) | B18: bounded search over own candidate consumption evidence. | 10 | 1 |
| [echo_arc/guard_synthesis.py](../../../echo_arc/guard_synthesis.py) | Bounded guard search and lineage selection from own development evidence. | 8 | 1 |
| [echo_arc/local_patch.py](../../../echo_arc/local_patch.py) | B4: guarded one-parameter repairs, leaving native controls in place elsewhere. | 5 | 2 |
| [echo_arc/local_patch_grammar.py](../../../echo_arc/local_patch_grammar.py) | Token-constrained single guarded repair, reusing the existing NFA. | 2 | 1 |
| [echo_arc/observe.py](../../../echo_arc/observe.py) | Passive ARC decision recorder. Original agent and runner sources stay frozen. | 6 | 14 |
| [echo_arc/parameter_first_grammar.py](../../../echo_arc/parameter_first_grammar.py) | Same bounded B5 language, but choose the control before its guard. | 3 | 1 |
| [echo_arc/precise_observe.py](../../../echo_arc/precise_observe.py) | Passive snapshots in the existing journal; no tracing or second bus. | 3 | 2 |
| [echo_arc/precise_patch.py](../../../echo_arc/precise_patch.py) | B5: up to three observable guards, plus a bounded remaining-wait operation. | 3 | 7 |
| [echo_arc/precise_patch_grammar.py](../../../echo_arc/precise_patch_grammar.py) | Finite B5 guard library; model selects conditions and bounded values. | 2 | 2 |
| [echo_arc/repair_diagnostics.py](../../../echo_arc/repair_diagnostics.py) | Passive, bounded B8 evidence; hypotheses about applicability are not gates. | 3 | 1 |
| [echo_arc/repair_evidence.py](../../../echo_arc/repair_evidence.py) | Bounded summaries consumed from the existing passive ARC decision journal. | 1 | 1 |
| [echo_arc/repair_experiments.py](../../../echo_arc/repair_experiments.py) | B15 experiment selection from measured development operations, not labels. | 5 | 1 |
| [echo_arc/repair_loop_grammar.py](../../../echo_arc/repair_loop_grammar.py) | Same parameter-first grammar, extending the API with bounded transition revision. | 2 | 1 |
| [echo_arc/repair_loop_observe.py](../../../echo_arc/repair_loop_observe.py) | Combine existing consumer and transition witnesses without a second journal. | 5 | 2 |
| [echo_arc/repair_loop_requests.py](../../../echo_arc/repair_loop_requests.py) | ECHO selects observed failure mechanisms; FIJO retains generic selection. | 4 | 1 |
| [echo_arc/repair_memory.py](../../../echo_arc/repair_memory.py) | Development-only experiment memory and evidence selection for ECHO. | 7 | 1 |
| [echo_arc/repair_outcomes.py](../../../echo_arc/repair_outcomes.py) | B16: preserve local level gains in feedback without weakening acceptance. | 5 | 1 |
| [echo_arc/runner.py](../../../echo_arc/runner.py) | echo-arc · play ARC-AGI-3 games with the ECHO agent, locally or inside the Kaggle submission. | 1 | 8 |
| [echo_arc/s6b20_search.py](../../../echo_arc/s6b20_search.py) | B20 development-only bounded HOLD search; never imports experiment results. | 10 | 2 |
| [echo_arc/s6b21_archive.py](../../../echo_arc/s6b21_archive.py) | Bounded investigator archive. Rejected hypotheses never become stable policy. | 4 | 1 |
| [echo_arc/s6b21_search.py](../../../echo_arc/s6b21_search.py) | B21-A: seeded joint duration/guard search, with no experiment artifact reads. | 6 | 1 |
| [echo_arc/s6b22_search.py](../../../echo_arc/s6b22_search.py) | B22-S: paired global exploration and two-child, fixed-duration repair. | 7 | 3 |
| [echo_arc/s6b23_search.py](../../../echo_arc/s6b23_search.py) | B23 investigator: bounded, development-only search; the judge stays external. | 4 | 2 |
| [echo_arc/s6b23r4_search.py](../../../echo_arc/s6b23r4_search.py) | R4 changes only the model wire format; R3 evidence selection is preserved. | 3 | 2 |
| [echo_arc/s6b24_search.py](../../../echo_arc/s6b24_search.py) | Pure B24 researcher. Inputs and returned receipts completely determine a slot. | 8 | 1 |
| [echo_arc/stale_transition.py](../../../echo_arc/stale_transition.py) | Candidate bounded repair: revise a predicted move after observed no-ops. | 2 | 7 |
| [echo_arc/strategy.py](../../../echo_arc/strategy.py) | S6-B bounded, observable control strategies; model output is data, never code. | 1 | 3 |
| [echo_arc/strategy_grammar.py](../../../echo_arc/strategy_grammar.py) | Finite token grammar for model-authored bounded control strategies (S6-B2). | 1 | 1 |
| [echo_arc/temporal_agent.py](../../../echo_arc/temporal_agent.py) | v5.8: order/count memories over observed object entries, extending frozen v5.7. | 2 | 2 |
| [echo_arc/temporal_audit.py](../../../echo_arc/temporal_audit.py) | Recompute development receipts from records and chained observations. | 7 | 0 |
| [echo_arc/temporal_bench.py](../../../echo_arc/temporal_bench.py) | Development-only comparison of v5.8 and ablations, with visible decision logs. | 7 | 6 |
| [echo_arc/temporal_memory.py](../../../echo_arc/temporal_memory.py) | Bounded integer memories of observed entries, without simulator access. | 0 | 1 |
| [echo_arc/temporal_policy.py](../../../echo_arc/temporal_policy.py) | S6-B3 bounded policies over v5.8's observed order/count mechanisms. | 5 | 2 |
| [echo_arc/temporal_policy_grammar.py](../../../echo_arc/temporal_policy_grammar.py) | B3 token grammar, using the previous grammar automaton unchanged. | 2 | 1 |
| [echo_arc/temporal_runner.py](../../../echo_arc/temporal_runner.py) | Private v5.8 factory, preserving the frozen runner and its global registry. | 4 | 4 |
| [echo_arc/transition_evidence.py](../../../echo_arc/transition_evidence.py) | Count actual contradiction features in the existing development recorder. | 2 | 1 |
| [echo_arc/transition_observe.py](../../../echo_arc/transition_observe.py) | Passive transition-prediction witnesses in the existing development journal. | 1 | 0 |

## gui4 — 8 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [gui4/__init__.py](../../../gui4/__init__.py) | GUI-4 — presentation and demonstration layer for echoAI. | 0 | 1 |
| [gui4/__main__.py](../../../gui4/__main__.py) | ``python3 -m echoai.gui4`` — open the GUI-4 window. | 1 | 0 |
| [gui4/app.py](../../../gui4/app.py) | GUI-4 main window. | 7 | 1 |
| [gui4/benchmark.py](../../../gui4/benchmark.py) | The in-GUI benchmark: run reduced benches off the Tk thread and export. | 2 | 1 |
| [gui4/capture.py](../../../gui4/capture.py) | Screenshots and deterministic frame recording for GUI-4. | 1 | 1 |
| [gui4/catalog.py](../../../gui4/catalog.py) | The GUI-4 case catalogue: every demonstration echoAI can show. | 14 | 1 |
| [gui4/evidence.py](../../../gui4/evidence.py) | Read sealed ECHO-3 reports without recomputing anything. | 0 | 1 |
| [gui4/neural.py](../../../gui4/neural.py) | The GUI-4 neural view: spike history, not just instantaneous brightness. | 0 | 1 |

## harness — 28 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [harness/dev_bridge.py](../../../harness/dev_bridge.py) | Private developer adapter. Uses installed ECHO code; never ship in harness wheels. | 9 | 0 |
| [harness/echo-nexus/src/echo_nexus/__init__.py](../../../harness/echo-nexus/src/echo_nexus/__init__.py) | RxLabs' open harness. No ECHO implementation is distributed here. | 0 | 0 |
| [harness/echo-nexus/src/echo_nexus/__main__.py](../../../harness/echo-nexus/src/echo_nexus/__main__.py) | Public CLI; headless capture uses the same TUI widgets as interactive use. | 3 | 0 |
| [harness/echo-nexus/src/echo_nexus/app.py](../../../harness/echo-nexus/src/echo_nexus/app.py) | The echo-nexus terminal. Views consume evidence; they cannot change ECHO. | 10 | 4 |
| [harness/echo-nexus/src/echo_nexus/backend.py](../../../harness/echo-nexus/src/echo_nexus/backend.py) | Public process boundary: read operator manifests, never import ECHO source. | 0 | 2 |
| [harness/echo-nexus/src/echo_nexus/commands.py](../../../harness/echo-nexus/src/echo_nexus/commands.py) | One source for command help, completion, and the documentation. | 0 | 0 |
| [harness/echo-nexus/src/echo_nexus/config.py](../../../harness/echo-nexus/src/echo_nexus/config.py) | Operator configuration and private, redacted harness logs. | 0 | 3 |
| [harness/echo-nexus/src/echo_nexus/connections.py](../../../harness/echo-nexus/src/echo_nexus/connections.py) | Named connection references. Never persist or inspect a credential's contents. | 1 | 2 |
| [harness/echo-nexus/src/echo_nexus/decisions.py](../../../harness/echo-nexus/src/echo_nexus/decisions.py) | Readable summaries of received evidence, never a model's hidden reasoning. | 0 | 1 |
| [harness/echo-nexus/src/echo_nexus/demo.py](../../../harness/echo-nexus/src/echo_nexus/demo.py) | Synthetic viewer fixture. This is deliberately NOT an ECHO agent or ARC score. | 0 | 0 |
| [harness/echo-nexus/src/echo_nexus/editor.py](../../../harness/echo-nexus/src/echo_nexus/editor.py) | Explicit clipboard operations and a multiline message editor. | 0 | 1 |
| [harness/echo-nexus/src/echo_nexus/transport.py](../../../harness/echo-nexus/src/echo_nexus/transport.py) | Optional neocortex and MCP transports. Never invoke tools from model text. | 1 | 4 |
| [harness/echo-nexus/src/echo_nexus/visual.py](../../../harness/echo-nexus/src/echo_nexus/visual.py) | Terminal image rendering and actual telemetry, with honest missing values. | 0 | 0 |
| [harness/echo-nexus/src/echo_nexus/world.py](../../../harness/echo-nexus/src/echo_nexus/world.py) | Operator-only coordinates and orientation; never sent to an agent. | 1 | 1 |
| [harness/echo-nexus/tests/test_activity.py](../../../harness/echo-nexus/tests/test_activity.py) | test | 5 | 0 |
| [harness/echo-nexus/tests/test_connections.py](../../../harness/echo-nexus/tests/test_connections.py) | test | 4 | 0 |
| [harness/echo-nexus/tests/test_harness.py](../../../harness/echo-nexus/tests/test_harness.py) | test | 4 | 0 |
| [harness/echo-nexus/tests/test_nexus15.py](../../../harness/echo-nexus/tests/test_nexus15.py) | test | 5 | 0 |
| [harness/local_bridge.py](../../../harness/local_bridge.py) | Private ECHO integration for echo-nexus. NEVER export this file to its public repo. | 12 | 0 |
| [harness/localdev/__init__.py](../../../harness/localdev/__init__.py) | Local development tools; never an ECHO capability or a scientific examiner. | 0 | 0 |
| [harness/localdev/__main__.py](../../../harness/localdev/__main__.py) | CLI: python3 -m harness.localdev --help. | 4 | 0 |
| [harness/localdev/common.py](../../../harness/localdev/common.py) | implementation-or-support (review required) | 0 | 1 |
| [harness/localdev/cpu_contracts.py](../../../harness/localdev/cpu_contracts.py) | Seeded metamorphic checks on existing DSL operations, not ARC benchmark tasks. | 2 | 0 |
| [harness/localdev/engine.py](../../../harness/localdev/engine.py) | Candidate-only repair loop with fixed tests, custody and an explicit budget. | 2 | 1 |
| [harness/localdev/inventory.py](../../../harness/localdev/inventory.py) | Static Python AST and import graph; other languages are explicitly inventoried. | 1 | 1 |
| [harness/localdev/runner.py](../../../harness/localdev/runner.py) | Bubblewrap execution with bounded output, wall time and recorded child resource use. | 1 | 1 |
| [harness/localdev/worker.py](../../../harness/localdev/worker.py) | Trusted worker, mounted read-only outside the candidate source tree. | 0 | 0 |
| [harness/s6_publication.py](../../../harness/s6_publication.py) | Private publication of terminal B11 receipts, never exam instrumentation. | 0 | 1 |

## metaverse1 — 9 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [metaverse1/__init__.py](../../../metaverse1/__init__.py) | package | 0 | 1 |
| [metaverse1/assets/build_room.py](../../../metaverse1/assets/build_room.py) | Generate a METAVERSE-1 room mesh with Blender, headless and reproducibly. | 0 | 0 |
| [metaverse1/assets/build_world.py](../../../metaverse1/assets/build_world.py) | Build a META-WORLD-2 mesh from a world declaration.  Blender only. | 0 | 0 |
| [metaverse1/assets/custody.py](../../../metaverse1/assets/custody.py) | Chain of custody for a built asset: declaration -> mesh -> receipt. | 0 | 1 |
| [metaverse1/assets/render_room.py](../../../metaverse1/assets/render_room.py) | Render a preview PNG of a generated room.  Blender only, headless. | 0 | 0 |
| [metaverse1/bench.py](../../../metaverse1/bench.py) | META-WORLD-2 bench: does enlarging the world change anything it must not? | 4 | 1 |
| [metaverse1/declare.py](../../../metaverse1/declare.py) | Write a world declaration that a modeller can rebuild from, and nothing else. | 1 | 1 |
| [metaverse1/sdf.py](../../../metaverse1/sdf.py) | SDF emission for META-WORLD-2, with visual detail separated from collision. | 0 | 1 |
| [metaverse1/world.py](../../../metaverse1/world.py) | META-WORLD-2: a block map that scales without touching the frozen physics. | 2 | 1 |

## nexus0 — 385 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [nexus0/__init__.py](../../../nexus0/__init__.py) | NEXUS-0: fast loop with cortex off. Spec: echoai/docs/05-NEXUS-0-SPEC.md. | 5 | 12 |
| [nexus0/attend.py](../../../nexus0/attend.py) | NEXUS-4a ATTEND — decide whether the fast loop is enough. | 1 | 1 |
| [nexus0/bench.py](../../../nexus0/bench.py) | NEXUS-0 bench: 256 turns, policy flip, mild env change. Cortex off. | 4 | 1 |
| [nexus0/board.py](../../../nexus0/board.py) | GUI-1 — the board. A replay of `thought.jsonl`, as one HTML file. | 0 | 1 |
| [nexus0/body.py](../../../nexus0/body.py) | CUERPO-1 — a body, not another graph. | 4 | 1 |
| [nexus0/body3d.py](../../../nexus0/body3d.py) | PULPO — a body in three dimensions, and a strategy that changes. | 4 | 3 |
| [nexus0/capacity1.py](../../../nexus0/capacity1.py) | CAPACITY-1: audited 256/512 LIF and conditional Adaptive-LIF experiment. | 3 | 1 |
| [nexus0/cause1/__init__.py](../../../nexus0/cause1/__init__.py) | CAUSE-1: bounded attribution from paired physical interventions. | 0 | 0 |
| [nexus0/cause1/assets/runner.py](../../../nexus0/cause1/assets/runner.py) | Private paired intervention. Frozen PX4 driver; never writes body pose. | 0 | 0 |
| [nexus0/cause1/bench.py](../../../nexus0/cause1/bench.py) | Prospective factorial campaign and reconstructing acceptance certificate. | 9 | 1 |
| [nexus0/cause1/consumer.py](../../../nexus0/cause1/consumer.py) | Public-only consumer. Mounted code contains no world, labels or seeds. | 2 | 0 |
| [nexus0/cause1/controls.py](../../../nexus0/cause1/controls.py) | Attack saved physical evidence in throwaway copies; preserve originals. | 1 | 0 |
| [nexus0/cause1/core.py](../../../nexus0/cause1/core.py) | Integer attribution. Input is public evidence; output remains a hypothesis. | 0 | 3 |
| [nexus0/cause1/evaluate.py](../../../nexus0/cause1/evaluate.py) | Reconstruct public attribution and independently judge physical effects. | 4 | 0 |
| [nexus0/cause1/perception.py](../../../nexus0/cause1/perception.py) | Sensor adapter: SI geometry outside the integer decision step. | 0 | 1 |
| [nexus0/cause1/session.py](../../../nexus0/cause1/session.py) | One new flight, isolated public consumer, private randomized intervention. | 7 | 1 |
| [nexus0/cause1/transport.py](../../../nexus0/cause1/transport.py) | Reuse SIM-3 namespaces and COMPOSE's synchronous public transport. | 2 | 0 |
| [nexus0/compose1/__init__.py](../../../nexus0/compose1/__init__.py) | Opt-in composition experiments; full SITL closure is a separate gate. | 0 | 0 |
| [nexus0/compose1/bench.py](../../../nexus0/compose1/bench.py) | Audited functional composition; never relabels a kinematic run as PX4. | 7 | 1 |
| [nexus0/compose1/consumer.py](../../../nexus0/compose1/consumer.py) | Interactive WSP/control experiment in the SIM-3 cage. | 1 | 0 |
| [nexus0/compose1/controller.py](../../../nexus0/compose1/controller.py) | Receding-horizon composition over observed cells and learned effects. | 4 | 2 |
| [nexus0/compose1/model.py](../../../nexus0/compose1/model.py) | T and Q are the existing tables indexed by actual CAM slots. | 5 | 7 |
| [nexus0/compose1/space.py](../../../nexus0/compose1/space.py) | Private, explicitly kinematic 3D benchmark. Never mounted in the agent cage. | 1 | 4 |
| [nexus0/compose1/training.py](../../../nexus0/compose1/training.py) | Training only in A, with measured kinematic consequences, never B/C. | 2 | 1 |
| [nexus0/compose1_v2/__init__.py](../../../nexus0/compose1_v2/__init__.py) | Versioned COMPOSE-1 continuation; original evidence stays frozen. | 0 | 0 |
| [nexus0/compose1_v2/assets/live_runner.py](../../../nexus0/compose1_v2/assets/live_runner.py) | Private Gazebo/PX4 process. Public sensor snapshots out; one WSP in. | 0 | 0 |
| [nexus0/compose1_v2/bench.py](../../../nexus0/compose1_v2/bench.py) | Frozen two-gate acceptance; evidence validity is separate from advantage. | 12 | 0 |
| [nexus0/compose1_v2/campaign.py](../../../nexus0/compose1_v2/campaign.py) | Serial SITL development and frozen evaluation. All attempts are retained. | 5 | 0 |
| [nexus0/compose1_v2/consumer.py](../../../nexus0/compose1_v2/consumer.py) | Isolated consumer: observations in, one causal WSP plus diagnostics out. | 3 | 0 |
| [nexus0/compose1_v2/controller.py](../../../nexus0/compose1_v2/controller.py) | Composition compares terminal consequences rather than cheap prefixes. | 2 | 1 |
| [nexus0/compose1_v2/controls.py](../../../nexus0/compose1_v2/controls.py) | Executable negative controls and retained tampering of a valid A flight. | 9 | 1 |
| [nexus0/compose1_v2/development.py](../../../nexus0/compose1_v2/development.py) | Kept A-only diagnostics; these results never constitute acceptance. | 8 | 1 |
| [nexus0/compose1_v2/evaluate.py](../../../nexus0/compose1_v2/evaluate.py) | Private adjudication; geometry never enters the decision process. | 4 | 0 |
| [nexus0/compose1_v2/functional.py](../../../nexus0/compose1_v2/functional.py) | Kinematic bench with an independent consequence/geometry adjudicator. | 3 | 1 |
| [nexus0/compose1_v2/inspect_dev.py](../../../nexus0/compose1_v2/inspect_dev.py) | Read-only ULog/sensor diagnostics, with an optional decoded camera artifact. | 0 | 0 |
| [nexus0/compose1_v2/perception.py](../../../nexus0/compose1_v2/perception.py) | Sensor boundary: floating-point projection -> bounded integer WSP. | 1 | 1 |
| [nexus0/compose1_v2/rig.py](../../../nexus0/compose1_v2/rig.py) | Four depth views of one camera family; stock flight body is unchanged. | 1 | 0 |
| [nexus0/compose1_v2/school.py](../../../nexus0/compose1_v2/school.py) | Learn/refine T from actual A flight consequences, not target commands. | 5 | 0 |
| [nexus0/compose1_v2/session.py](../../../nexus0/compose1_v2/session.py) | Live bidirectional session; no harness route reaches PX4. | 7 | 0 |
| [nexus0/compose1_v2/space.py](../../../nexus0/compose1_v2/space.py) | Private extruded rooms; the same geometry can be rendered by Gazebo. | 2 | 0 |
| [nexus0/compose1_v2/transport.py](../../../nexus0/compose1_v2/transport.py) | Explicit read-only dependency mount, with no simulator or world files. | 2 | 0 |
| [nexus0/compose1_v3/__init__.py](../../../nexus0/compose1_v3/__init__.py) | Versioned COMPOSE-1 continuation; original evidence stays frozen. | 0 | 1 |
| [nexus0/compose1_v3/assets/live_runner.py](../../../nexus0/compose1_v3/assets/live_runner.py) | Private Gazebo/PX4 process. Public sensor snapshots out; one WSP in. | 0 | 0 |
| [nexus0/compose1_v3/bench.py](../../../nexus0/compose1_v3/bench.py) | Frozen two-gate acceptance; evidence validity is separate from advantage. | 12 | 1 |
| [nexus0/compose1_v3/campaign.py](../../../nexus0/compose1_v3/campaign.py) | Serial SITL development and frozen evaluation. All attempts are retained. | 5 | 0 |
| [nexus0/compose1_v3/candidates.py](../../../nexus0/compose1_v3/candidates.py) | Cost-aware bounded search; the V2 sensor and execution contract is reused. | 2 | 0 |
| [nexus0/compose1_v3/consumer.py](../../../nexus0/compose1_v3/consumer.py) | Isolated consumer: observations in, one causal WSP plus diagnostics out. | 3 | 0 |
| [nexus0/compose1_v3/controller.py](../../../nexus0/compose1_v3/controller.py) | Cost-aware bounded search; the V2 sensor and execution contract is reused. | 2 | 4 |
| [nexus0/compose1_v3/controls.py](../../../nexus0/compose1_v3/controls.py) | Executable negative controls and retained tampering of a valid A flight. | 9 | 1 |
| [nexus0/compose1_v3/development.py](../../../nexus0/compose1_v3/development.py) | All candidates and A results are retained; V2 B is not selection data. | 6 | 1 |
| [nexus0/compose1_v3/evaluate.py](../../../nexus0/compose1_v3/evaluate.py) | Private adjudication; geometry never enters the decision process. | 4 | 0 |
| [nexus0/compose1_v3/functional.py](../../../nexus0/compose1_v3/functional.py) | Kinematic bench with an independent consequence/geometry adjudicator. | 3 | 1 |
| [nexus0/compose1_v3/perception.py](../../../nexus0/compose1_v3/perception.py) | Sensor boundary: floating-point projection -> bounded integer WSP. | 1 | 1 |
| [nexus0/compose1_v3/rig.py](../../../nexus0/compose1_v3/rig.py) | Four depth views of one camera family; stock flight body is unchanged. | 1 | 0 |
| [nexus0/compose1_v3/school.py](../../../nexus0/compose1_v3/school.py) | Learn/refine T from actual A flight consequences, not target commands. | 5 | 0 |
| [nexus0/compose1_v3/session.py](../../../nexus0/compose1_v3/session.py) | Live bidirectional session; no harness route reaches PX4. | 7 | 0 |
| [nexus0/compose1_v3/space.py](../../../nexus0/compose1_v3/space.py) | Private extruded rooms; the same geometry can be rendered by Gazebo. | 2 | 4 |
| [nexus0/compose1_v3/transport.py](../../../nexus0/compose1_v3/transport.py) | Explicit read-only dependency mount, with no simulator or world files. | 2 | 0 |
| [nexus0/compose1_v4/bench.py](../../../nexus0/compose1_v4/bench.py) | Frozen two-gate acceptance; evidence validity is separate from advantage. | 14 | 1 |
| [nexus0/compose1_v4/power.py](../../../nexus0/compose1_v4/power.py) | Prospective sample planning from the consumed V3 validation, never new B/C. | 0 | 1 |
| [nexus0/constants.py](../../../nexus0/constants.py) | NEXUS-0 frozen integers. Do not invent floats. | 1 | 11 |
| [nexus0/corridor.py](../../../nexus0/corridor.py) | NEXUS-4i — another corridor. The experiment the ring could not be. | 4 | 1 |
| [nexus0/cortex.py](../../../nexus0/cortex.py) | NEXUS-4a cortex stub — emits WSP, never facts. | 4 | 1 |
| [nexus0/cortex_turn.py](../../../nexus0/cortex_turn.py) | NEXUS-4b — the contract a slow clock is allowed to see. | 2 | 0 |
| [nexus0/demo.py](../../../nexus0/demo.py) | Watch echoAI think in the terminal. | 4 | 1 |
| [nexus0/drone3/__init__.py](../../../nexus0/drone3/__init__.py) | DRONE-3: the integrated mission in one continuous PX4/Gazebo SITL session. | 0 | 1 |
| [nexus0/drone3/agent.py](../../../nexus0/drone3/agent.py) | The caged DRONE-3 agent: public observations in, one WSP plus a published | 10 | 0 |
| [nexus0/drone3/assets/runner.py](../../../nexus0/drone3/assets/runner.py) | Private DRONE-3 SITL adapter: one continuous PX4/Gazebo session. | 8 | 0 |
| [nexus0/drone3/bench.py](../../../nexus0/drone3/bench.py) | DRONE-3 bench: A develops and calibrates, the lock freezes, B validates once, | 12 | 0 |
| [nexus0/drone3/calibration.py](../../../nexus0/drone3/calibration.py) | TRANSFER-3 C1 camera calibration applied to physical frames. | 2 | 1 |
| [nexus0/drone3/consumer.py](../../../nexus0/drone3/consumer.py) | Isolated DRONE-3 consumer: one JSON observation in, one WSP decision out. | 1 | 0 |
| [nexus0/drone3/contract.py](../../../nexus0/drone3/contract.py) | Public constants and the canonical 16-byte intentions DRONE-3 may execute. | 1 | 1 |
| [nexus0/drone3/controls.py](../../../nexus0/drone3/controls.py) | Controls on the same recorded observations and budgets. None is ever flown. | 15 | 0 |
| [nexus0/drone3/dev.py](../../../nexus0/drone3/dev.py) | Development flights (partition A). Pilots are kept and never counted. | 3 | 0 |
| [nexus0/drone3/energy.py](../../../nexus0/drone3/energy.py) | POWER-1 over PX4 SITL's simulated battery. | 3 | 1 |
| [nexus0/drone3/evaluate.py](../../../nexus0/drone3/evaluate.py) | Read-only audit and private judge of one DRONE-3 flight. | 16 | 0 |
| [nexus0/drone3/gates.py](../../../nexus0/drone3/gates.py) | Supervisor-side gates. Pure integer functions of public, recorded inputs. | 6 | 1 |
| [nexus0/drone3/gateway.py](../../../nexus0/drone3/gateway.py) | Bounded cell goals over PX4-1's transport gate. | 3 | 1 |
| [nexus0/drone3/probes.py](../../../nexus0/drone3/probes.py) | In-flight refusal probes: illegal inputs built on live telemetry, never sent. | 7 | 1 |
| [nexus0/drone3/protocol.py](../../../nexus0/drone3/protocol.py) | The DRONE-3 matrix: rooms, conditions, private manipulations and seeds. | 2 | 1 |
| [nexus0/drone3/session.py](../../../nexus0/drone3/session.py) | Host side of one DRONE-3 flight: world build, cage, container, relay. | 5 | 1 |
| [nexus0/drone3/supervisor.py](../../../nexus0/drone3/supervisor.py) | SAFE-1's supervisor over the cell gateway, with the two DRONE-3 gates. | 5 | 1 |
| [nexus0/drone3/transport.py](../../../nexus0/drone3/transport.py) | The DRONE-3 agent's cage: an explicit read-only module mount, nothing else. | 1 | 0 |
| [nexus0/dynamic1/__init__.py](../../../nexus0/dynamic1/__init__.py) | DYNAMIC-1: external motion and short prediction, from a hovering body. | 0 | 2 |
| [nexus0/dynamic1/assets/consumer.py](../../../nexus0/dynamic1/assets/consumer.py) | DYNAMIC-1 consumer: the consumer of PATTERN-1R, copied, with one thing | 0 | 0 |
| [nexus0/dynamic1/assets/flightrunner_mover.py](../../../nexus0/dynamic1/assets/flightrunner_mover.py) | DYNAMIC-1 runner: PATTERN-1R's runner, copied, with the survey replaced by | 0 | 0 |
| [nexus0/dynamic1/assets/sensor_runner.py](../../../nexus0/dynamic1/assets/sensor_runner.py) | DYNAMIC-1: the channel of PATTERN-1R, copied; it starts the mover runner. | 0 | 0 |
| [nexus0/dynamic1/campaign.py](../../../nexus0/dynamic1/campaign.py) | DYNAMIC-1: the coordinator of PATTERN-1R, copied. The worlds are the same | 25 | 2 |
| [nexus0/dynamic1/contract.py](../../../nexus0/dynamic1/contract.py) | DYNAMIC-1: what moves, and where it will be in half a second. | 4 | 2 |
| [nexus0/dynamic1/dev.py](../../../nexus0/dynamic1/dev.py) | DYNAMIC-1 development flights: kept, never counted. | 16 | 0 |
| [nexus0/dynamic1/evaluate.py](../../../nexus0/dynamic1/evaluate.py) | DYNAMIC-1 evaluator: GROUND-1 groups, plus what the motion records claim. | 8 | 2 |
| [nexus0/dynamic1/session.py](../../../nexus0/dynamic1/session.py) | DYNAMIC-1 episode: the session of PATTERN-1R, copied. The runner moves a | 11 | 2 |
| [nexus0/dynamic1_v2/__init__.py](../../../nexus0/dynamic1_v2/__init__.py) | DYNAMIC-1 v2: the same question, tracking faces instead of a point. | 0 | 2 |
| [nexus0/dynamic1_v2/assets/consumer.py](../../../nexus0/dynamic1_v2/assets/consumer.py) | DYNAMIC-1 v2 consumer: v1, copied, tracking faces instead of a point. | 0 | 0 |
| [nexus0/dynamic1_v2/campaign.py](../../../nexus0/dynamic1_v2/campaign.py) | DYNAMIC-1 v2: v1 coordinator, copied. Only the consumer and the way the | 26 | 2 |
| [nexus0/dynamic1_v2/dev.py](../../../nexus0/dynamic1_v2/dev.py) | DYNAMIC-1 v2 development flights: kept, never counted. | 18 | 0 |
| [nexus0/dynamic1_v2/evaluate.py](../../../nexus0/dynamic1_v2/evaluate.py) | DYNAMIC-1 v2 evaluator: v1, copied, judging the prediction on what a flat | 8 | 1 |
| [nexus0/dynamic1_v2/session.py](../../../nexus0/dynamic1_v2/session.py) | DYNAMIC-1 v2 episode: v1 session, copied; only the consumer changes. | 11 | 1 |
| [nexus0/echo2.py](../../../nexus0/echo2.py) | Reproducible VITA-1 / FOOD-1 / SURV-1 probes. No hardware or LLM. | 8 | 2 |
| [nexus0/encoder.py](../../../nexus0/encoder.py) | Semantic WSP encoder for NEXUS-0. | 6 | 4 |
| [nexus0/env.py](../../../nexus0/env.py) | Synthetic 32-cell ring. No robot. No EEG. No Wikipedia. | 1 | 5 |
| [nexus0/escalate.py](../../../nexus0/escalate.py) | NEXUS-4f — how much to think, not another map. | 1 | 1 |
| [nexus0/flight1s/__init__.py](../../../nexus0/flight1s/__init__.py) | FLIGHT-1S — software-in-the-loop flight with PX4 SITL and Gazebo. | 0 | 3 |
| [nexus0/flight1s/__main__.py](../../../nexus0/flight1s/__main__.py) | ``python3 -m echoai.nexus0.flight1s`` — validate, preflight, bench, audit. | 11 | 0 |
| [nexus0/flight1s/assets/flightrunner.py](../../../nexus0/flight1s/assets/flightrunner.py) | Private side of FLIGHT-1S: the only process that talks to Gazebo and PX4. | 0 | 0 |
| [nexus0/flight1s/assets/flightrunner_frozen_clock.py](../../../nexus0/flight1s/assets/flightrunner_frozen_clock.py) | Mutant backend: a real flight whose reported clock never advances. | 0 | 0 |
| [nexus0/flight1s/assets/flightrunner_noforce.py](../../../nexus0/flight1s/assets/flightrunner_noforce.py) | Mutant backend: declares the disturbance and never publishes the wrench. | 0 | 0 |
| [nexus0/flight1s/assets/flightrunner_teleport.py](../../../nexus0/flight1s/assets/flightrunner_teleport.py) | Mutant backend: a harness that moves the body instead of flying it. | 0 | 0 |
| [nexus0/flight1s/audit.py](../../../nexus0/flight1s/audit.py) | An auditor that does not read ``flight1s_green``. | 9 | 1 |
| [nexus0/flight1s/bench.py](../../../nexus0/flight1s/bench.py) | The preregistered FLIGHT-1S bench: 48 episodes and the groups around them. | 11 | 3 |
| [nexus0/flight1s/evaluate.py](../../../nexus0/flight1s/evaluate.py) | The evaluator: integers in, verdicts out, nothing back to the vehicle. | 1 | 2 |
| [nexus0/flight1s/mutants.py](../../../nexus0/flight1s/mutants.py) | Controls and mutants, each provoked from something that worked. | 8 | 2 |
| [nexus0/flight1s/protocol.py](../../../nexus0/flight1s/protocol.py) | The frozen protocol, and the only door the sweep uses before it exists. | 3 | 3 |
| [nexus0/flight1s/runner.py](../../../nexus0/flight1s/runner.py) | One host runner for ``preflight → bench → audit``. | 5 | 0 |
| [nexus0/flight1s/runtime.py](../../../nexus0/flight1s/runtime.py) | Preflight for FLIGHT-1S: PX4 and Gazebo, or an explicit not_run. | 1 | 2 |
| [nexus0/flight1s/session.py](../../../nexus0/flight1s/session.py) | One flight episode, supervised from the host. | 4 | 5 |
| [nexus0/flight1s/sweep.py](../../../nexus0/flight1s/sweep.py) | The split-A calibration sweep, published in full. | 6 | 0 |
| [nexus0/flight1s/v2/__init__.py](../../../nexus0/flight1s/v2/__init__.py) | FLIGHT-1S v2 — the repaired protocol, beside v1 and never on top of it. | 0 | 2 |
| [nexus0/flight1s/v2/__main__.py](../../../nexus0/flight1s/v2/__main__.py) | ``python3 -m echoai.nexus0.flight1s.v2`` — the v2 CLI. | 13 | 0 |
| [nexus0/flight1s/v2/assets/flightrunner_accumulate.py](../../../nexus0/flight1s/v2/assets/flightrunner_accumulate.py) | Mutant backend: republishes the wrench on every sample of the window. | 0 | 0 |
| [nexus0/flight1s/v2/audit.py](../../../nexus0/flight1s/v2/audit.py) | The v2 auditor: rebuild the three verdicts, do not read the green. | 9 | 0 |
| [nexus0/flight1s/v2/bench.py](../../../nexus0/flight1s/v2/bench.py) | The v2 bench: the same 48 episodes, three separated verdicts. | 13 | 0 |
| [nexus0/flight1s/v2/calibrate.py](../../../nexus0/flight1s/v2/calibrate.py) | The A-v2 calibration: 64 flights plus negative controls, all published. | 9 | 1 |
| [nexus0/flight1s/v2/evaluate.py](../../../nexus0/flight1s/v2/evaluate.py) | Three questions, three verdicts, three denominators. | 3 | 1 |
| [nexus0/flight1s/v2/mutants.py](../../../nexus0/flight1s/v2/mutants.py) | v2 controls and mutants: one per boundary the three groups draw. | 9 | 1 |
| [nexus0/flight1s/v2/protocol.py](../../../nexus0/flight1s/v2/protocol.py) | The v2 protocol: load, calibrate, freeze. | 4 | 1 |
| [nexus0/flight1s/v2/runner.py](../../../nexus0/flight1s/v2/runner.py) | One host runner for the v2 chain: preflight → bench → audit. | 7 | 0 |
| [nexus0/flight1s/v2/runtime.py](../../../nexus0/flight1s/v2/runtime.py) | The v2 runtime lock, beside v1's and never on top of it. | 4 | 2 |
| [nexus0/flight1s/v3/__init__.py](../../../nexus0/flight1s/v3/__init__.py) | A configuration repair with the frozen v2 acceptance bands. | 0 | 13 |
| [nexus0/flight1s/v3/assets/flightrunner_configured.py](../../../nexus0/flight1s/v3/assets/flightrunner_configured.py) | Configure PX4 through its parameter interface, then run the frozen driver. | 0 | 0 |
| [nexus0/flight1s/v3/campaign.py](../../../nexus0/flight1s/v3/campaign.py) | Fresh flight campaigns with immutable outputs and fixed v2 bands. | 12 | 13 |
| [nexus0/flight1s/v3/certificate.py](../../../nexus0/flight1s/v3/certificate.py) | Frozen v3 validation, full bank and reconstructible evidence. | 13 | 8 |
| [nexus0/flight1s/worldbuild.py](../../../nexus0/flight1s/worldbuild.py) | The effective world for a flight episode, and the envelope gate. | 2 | 1 |
| [nexus0/flight1s_v4/__init__.py](../../../nexus0/flight1s_v4/__init__.py) | Prospective FLIGHT-1S v4; historical flight implementations stay intact. | 0 | 3 |
| [nexus0/flight1s_v4/campaign.py](../../../nexus0/flight1s_v4/campaign.py) | One prospective chain, raw evidence, and an audit that rebuilds its verdict. | 11 | 3 |
| [nexus0/flight1s_v4/contract.py](../../../nexus0/flight1s_v4/contract.py) | Immutable acceptance and grouped contrast; floats are lab measurements only. | 3 | 3 |
| [nexus0/flight1s_v4_close.py](../../../nexus0/flight1s_v4_close.py) | FLIGHT-1S v4: red closure of the interrupted validation chain. | 6 | 0 |
| [nexus0/flight1s_v5/__init__.py](../../../nexus0/flight1s_v5/__init__.py) | FLIGHT-1S v5: prospective sensor accuracy correction, unchanged v4 criteria. | 0 | 2 |
| [nexus0/flight1s_v5/assets/flightrunner_configured.py](../../../nexus0/flight1s_v5/assets/flightrunner_configured.py) | Configure PX4 through its parameter interface, then run the frozen driver. | 0 | 0 |
| [nexus0/flight1s_v5/campaign.py](../../../nexus0/flight1s_v5/campaign.py) | One prospective chain, raw evidence, and an audit that rebuilds its verdict. | 11 | 2 |
| [nexus0/flight1s_v5/container/patch_source.py](../../../nexus0/flight1s_v5/container/patch_source.py) | Two accuracy labels; assert all other source bytes remain identical. | 0 | 0 |
| [nexus0/flight1s_v5/contract.py](../../../nexus0/flight1s_v5/contract.py) | Reuse v4 acceptance exactly; change only the fixed physical configuration. | 4 | 2 |
| [nexus0/flight1s_v5_close.py](../../../nexus0/flight1s_v5_close.py) | FLIGHT-1S v5: red closure of the validation chain that stopped before its report. | 9 | 0 |
| [nexus0/flight1s_v6/__init__.py](../../../nexus0/flight1s_v6/__init__.py) | FLIGHT-1S v6: v4/v5 acceptance; a chain that no single row can stop. | 0 | 2 |
| [nexus0/flight1s_v6/assets/flightrunner_configured.py](../../../nexus0/flight1s_v6/assets/flightrunner_configured.py) | Configure PX4 through its parameter interface, then run the frozen driver. | 0 | 0 |
| [nexus0/flight1s_v6/campaign.py](../../../nexus0/flight1s_v6/campaign.py) | One prospective chain, raw evidence, and an audit that rebuilds its verdict. | 12 | 2 |
| [nexus0/flight1s_v6/contract.py](../../../nexus0/flight1s_v6/contract.py) | v4 acceptance, unchanged; a chain that no single row can stop. | 6 | 2 |
| [nexus0/food1.py](../../../nexus0/food1.py) | FOOD-1: OBJ-1's carried object can be consumed once per life. | 5 | 1 |
| [nexus0/fusion1/__init__.py](../../../nexus0/fusion1/__init__.py) | Opt-in, bounded provenance and sensor agreement over the existing WSP. | 0 | 1 |
| [nexus0/fusion1/bench.py](../../../nexus0/fusion1/bench.py) | Frozen functional fusion certificate, with isolated sensor replay. | 9 | 1 |
| [nexus0/fusion1/core.py](../../../nexus0/fusion1/core.py) | Integer evidence reducer. This file also runs alone in the SIM-3 cage. | 0 | 7 |
| [nexus0/fusion1/integration.py](../../../nexus0/fusion1/integration.py) | Use the historical gate; the fusion reducer never controls an actuator. | 3 | 1 |
| [nexus0/fusion1/judge.py](../../../nexus0/fusion1/judge.py) | Independent reference adjudicator. Does not import or call the reducer. | 0 | 1 |
| [nexus0/fusion1/replay.py](../../../nexus0/fusion1/replay.py) | Sensor boundary: reduced physical samples from immutable SITL evidence. | 2 | 1 |
| [nexus0/fusion1/scenarios.py](../../../nexus0/fusion1/scenarios.py) | Public development/test stimuli; condition names never reach the consumer. | 1 | 1 |
| [nexus0/gate.py](../../../nexus0/gate.py) | Pure action gate. OK / MODIFY / BLOCK. | 1 | 1 |
| [nexus0/gen1.py](../../../nexus0/gen1.py) | GEN-1: one inherited exploration integer, with fresh child memory. | 4 | 1 |
| [nexus0/gen1b.py](../../../nexus0/gen1b.py) | GEN-1b: inherit a local evidence budget; examine frozen learned policy. | 10 | 0 |
| [nexus0/gen1c.py](../../../nexus0/gen1c.py) | GEN-1c: inherit evidence needed to calibrate a noisy edge actuator. | 5 | 0 |
| [nexus0/gen1d.py](../../../nexus0/gen1d.py) | GEN-1d: confirm inherited local caution on paired actuator noise. | 5 | 0 |
| [nexus0/gen1e.py](../../../nexus0/gen1e.py) | GEN-1e: confirm inherited local caution on paired actuator noise. | 5 | 0 |
| [nexus0/gen1f.py](../../../nexus0/gen1f.py) | GEN-1f: confirm inherited local caution on paired actuator noise. | 5 | 1 |
| [nexus0/graph.py](../../../nexus0/graph.py) | WORLD-3 — a graph of 256 nodes, and the first body-map: position *is* node. | 4 | 1 |
| [nexus0/ground1/__init__.py](../../../nexus0/ground1/__init__.py) | GROUND-1: physical observation to WSP inside the cage, without oracle or a second bus. | 0 | 3 |
| [nexus0/ground1/assets/consumer.py](../../../nexus0/ground1/assets/consumer.py) | GROUND-1 consumer: runs in the SIM-3 cage, checks what SENSOR-1S sends and | 0 | 0 |
| [nexus0/ground1/campaign.py](../../../nexus0/ground1/campaign.py) | GROUND-1: SENSOR-1S v3's coordinator, copied. The flights, channel and | 19 | 2 |
| [nexus0/ground1/dev.py](../../../nexus0/ground1/dev.py) | GROUND-1 development flights in A: kept, never counted. | 13 | 0 |
| [nexus0/ground1/evaluate.py](../../../nexus0/ground1/evaluate.py) | GROUND-1 evaluator: SENSOR-1S v3's groups, plus what the translation claims. | 9 | 3 |
| [nexus0/ground1/session.py](../../../nexus0/ground1/session.py) | GROUND-1 episode: SENSOR-1S v2's session, copied; the consumer is GROUND-1's | 9 | 3 |
| [nexus0/ground1_v2/__init__.py](../../../nexus0/ground1_v2/__init__.py) | GROUND-1 v2: GROUND-1 with the channel's delivery stamp fixed at its source. | 0 | 3 |
| [nexus0/ground1_v2/assets/sensor_runner.py](../../../nexus0/ground1_v2/assets/sensor_runner.py) | GROUND-1 v2: SENSOR-1S v2's channel, copied; the sender reads its clock | 0 | 0 |
| [nexus0/ground1_v2/campaign.py](../../../nexus0/ground1_v2/campaign.py) | GROUND-1 v2: v1's coordinator, copied. Only the channel changes (its sender | 20 | 3 |
| [nexus0/ground1_v2/dev.py](../../../nexus0/ground1_v2/dev.py) | GROUND-1 v2 development flights in A: kept, never counted. | 14 | 0 |
| [nexus0/ground1_v2/session.py](../../../nexus0/ground1_v2/session.py) | GROUND-1 v2 episode: v1's session, copied; only the channel (TAP) is v2's, | 9 | 2 |
| [nexus0/heat1.py](../../../nexus0/heat1.py) | HEAT-1: two integer homeostatic variables with a causal trade-off. | 6 | 1 |
| [nexus0/heat1b.py](../../../nexus0/heat1b.py) | HEAT-1b: two integer homeostatic variables with a causal trade-off. | 7 | 2 |
| [nexus0/host1/__init__.py](../../../nexus0/host1/__init__.py) | Consequence-conditioned source authority and bounded WSP communication. | 0 | 0 |
| [nexus0/host1/bench.py](../../../nexus0/host1/bench.py) | Frozen machine-source bank, caged consumer, reconstructive audit. | 12 | 0 |
| [nexus0/host1/consumer.py](../../../nexus0/host1/consumer.py) | Only public claims and already observed receipts cross the existing cage wire. | 1 | 0 |
| [nexus0/host1/controls.py](../../../nexus0/host1/controls.py) | Negative controls never receive an actuator handle. | 2 | 1 |
| [nexus0/host1/core.py](../../../nexus0/host1/core.py) | Integer source/sign/context authority. No reward, CAM fact or actuator API. | 2 | 1 |
| [nexus0/host1/probes.py](../../../nexus0/host1/probes.py) | Fixed communication/absence probes, also replayed against the isolated consumer. | 3 | 1 |
| [nexus0/host1/replay.py](../../../nexus0/host1/replay.py) | Three existing nominal flights: new source hypotheses, no new physical flights. | 4 | 1 |
| [nexus0/host1/transport.py](../../../nexus0/host1/transport.py) | Reuse the SIM-3 cage/transport; no world, seed or future outcome mounted. | 3 | 0 |
| [nexus0/host1/world.py](../../../nexus0/host1/world.py) | Private, precomputed machine tape and integer kinematic receipts; no Gazebo claim. | 2 | 1 |
| [nexus0/lex.py](../../../nexus0/lex.py) | NEXUS-0 lexical WSP layer — host port of `kernel/navi/wsp_lex.c`. | 3 | 1 |
| [nexus0/loop.py](../../../nexus0/loop.py) | One-step cognitive loop. Cortex is not a module here; cortex_calls stays 0. | 21 | 11 |
| [nexus0/neural_viz.py](../../../nexus0/neural_viz.py) | NEURAL-VIZ-1 — live, read-only terminal cockpit for the real ECHO-2 loop. | 8 | 1 |
| [nexus0/neural_viz_gui.py](../../../nexus0/neural_viz_gui.py) | NEURAL-VIZ-1 native GUI for the real ECHO-2 agent. | 7 | 1 |
| [nexus0/obj1.py](../../../nexus0/obj1.py) | OBJ-1 — the world has things in it, not only a me. | 7 | 3 |
| [nexus0/open1.py](../../../nexus0/open1.py) | OPEN-1 — a fourth gear, because there is a fourth physics. | 8 | 1 |
| [nexus0/oracle.py](../../../nexus0/oracle.py) | NEXUS-4h — the world does not answer questions. | 1 | 1 |
| [nexus0/pattern.py](../../../nexus0/pattern.py) | PATTERN-0 — a temporal regularity that one-step T cannot see. | 1 | 2 |
| [nexus0/pattern0.py](../../../nexus0/pattern0.py) | PATTERN-0 — a riff one-step T cannot hear. | 10 | 1 |
| [nexus0/pattern1.py](../../../nexus0/pattern1.py) | PATTERN-1: invariant families from binary perception and consequences. | 0 | 4 |
| [nexus0/pattern1r/__init__.py](../../../nexus0/pattern1r/__init__.py) | PATTERN-1R: object identity across views, from a scripted survey flight. | 0 | 3 |
| [nexus0/pattern1r/assets/consumer.py](../../../nexus0/pattern1r/assets/consumer.py) | PATTERN-1R consumer: GROUND-1's consumer, copied, plus one thing. Every | 0 | 0 |
| [nexus0/pattern1r/assets/flightrunner_survey.py](../../../nexus0/pattern1r/assets/flightrunner_survey.py) | PATTERN-1R survey runner: the frozen FLIGHT-1S stage script, copied, | 0 | 0 |
| [nexus0/pattern1r/assets/sensor_runner.py](../../../nexus0/pattern1r/assets/sensor_runner.py) | PATTERN-1R: GROUND-1 v2's channel, copied. It starts the survey runner | 0 | 0 |
| [nexus0/pattern1r/campaign.py](../../../nexus0/pattern1r/campaign.py) | PATTERN-1R: GROUND-1 v2's coordinator, copied. The worlds come from this | 23 | 1 |
| [nexus0/pattern1r/contract.py](../../../nexus0/pattern1r/contract.py) | PATTERN-1R: the survey script and what is fixed before flying. | 4 | 2 |
| [nexus0/pattern1r/dev.py](../../../nexus0/pattern1r/dev.py) | PATTERN-1R development flights: kept, never counted. | 16 | 0 |
| [nexus0/pattern1r/evaluate.py](../../../nexus0/pattern1r/evaluate.py) | PATTERN-1R evaluator: GROUND-1's groups, plus what identity claims. | 9 | 1 |
| [nexus0/pattern1r/session.py](../../../nexus0/pattern1r/session.py) | PATTERN-1R episode: GROUND-1 v2's session, copied. The flight runner is | 11 | 2 |
| [nexus0/pattern1r_v2/__init__.py](../../../nexus0/pattern1r_v2/__init__.py) | PATTERN-1R: object identity across views, from a scripted survey flight. | 0 | 2 |
| [nexus0/pattern1r_v2/assets/consumer.py](../../../nexus0/pattern1r_v2/assets/consumer.py) | PATTERN-1R v2 isolated consumer. Same sensor framing and WSP translation; | 0 | 0 |
| [nexus0/pattern1r_v2/assets/flightrunner_survey.py](../../../nexus0/pattern1r_v2/assets/flightrunner_survey.py) | PATTERN-1R survey runner: the frozen FLIGHT-1S stage script, copied, | 0 | 0 |
| [nexus0/pattern1r_v2/campaign.py](../../../nexus0/pattern1r_v2/campaign.py) | PATTERN-1R: GROUND-1 v2's coordinator, copied. The worlds come from this | 25 | 2 |
| [nexus0/pattern1r_v2/contract.py](../../../nexus0/pattern1r_v2/contract.py) | A physically admissible, harness-only survey; no route reaches the learner. | 4 | 2 |
| [nexus0/pattern1r_v2/dev.py](../../../nexus0/pattern1r_v2/dev.py) | PATTERN-1R development flights: kept, never counted. | 16 | 0 |
| [nexus0/pattern1r_v2/development.py](../../../nexus0/pattern1r_v2/development.py) | Complete the six declared development worlds; never replace a flight. | 3 | 0 |
| [nexus0/pattern1r_v2/evaluate.py](../../../nexus0/pattern1r_v2/evaluate.py) | PATTERN-1R evaluator: GROUND-1's groups, plus what identity claims. | 9 | 1 |
| [nexus0/pattern1r_v2/inspect_dev.py](../../../nexus0/pattern1r_v2/inspect_dev.py) | Rejudge one development flight, preserving the verdict with its code hash. | 8 | 0 |
| [nexus0/pattern1r_v2/session.py](../../../nexus0/pattern1r_v2/session.py) | PATTERN-1R episode: GROUND-1 v2's session, copied. The flight runner is | 11 | 2 |
| [nexus0/pattern1r_v3/__init__.py](../../../nexus0/pattern1r_v3/__init__.py) | PATTERN-1R: object identity across views, from a scripted survey flight. | 0 | 2 |
| [nexus0/pattern1r_v3/assets/consumer.py](../../../nexus0/pattern1r_v3/assets/consumer.py) | PATTERN-1R v2 isolated consumer. Same sensor framing and WSP translation; | 0 | 0 |
| [nexus0/pattern1r_v3/assets/flightrunner_survey.py](../../../nexus0/pattern1r_v3/assets/flightrunner_survey.py) | PATTERN-1R survey runner: the frozen FLIGHT-1S stage script, copied, | 0 | 0 |
| [nexus0/pattern1r_v3/campaign.py](../../../nexus0/pattern1r_v3/campaign.py) | PATTERN-1R: GROUND-1 v2's coordinator, copied. The worlds come from this | 25 | 1 |
| [nexus0/pattern1r_v3/contract.py](../../../nexus0/pattern1r_v3/contract.py) | Only estimator barometer uncertainty changes; perception stays frozen. | 4 | 1 |
| [nexus0/pattern1r_v3/dev.py](../../../nexus0/pattern1r_v3/dev.py) | PATTERN-1R development flights: kept, never counted. | 16 | 0 |
| [nexus0/pattern1r_v3/development.py](../../../nexus0/pattern1r_v3/development.py) | Complete the six declared development worlds; never replace a flight. | 3 | 0 |
| [nexus0/pattern1r_v3/evaluate.py](../../../nexus0/pattern1r_v3/evaluate.py) | PATTERN-1R evaluator: GROUND-1's groups, plus what identity claims. | 9 | 1 |
| [nexus0/pattern1r_v3/inspect_dev.py](../../../nexus0/pattern1r_v3/inspect_dev.py) | Rejudge one development flight, preserving the verdict with its code hash. | 8 | 0 |
| [nexus0/pattern1r_v3/memory.py](../../../nexus0/pattern1r_v3/memory.py) | An ambiguous match is not evidence of a new family. | 1 | 1 |
| [nexus0/pattern1r_v3/regression_v2.py](../../../nexus0/pattern1r_v3/regression_v2.py) | Run every immutable v2 test with an absent, isolated test report. | 4 | 0 |
| [nexus0/pattern1r_v3/session.py](../../../nexus0/pattern1r_v3/session.py) | PATTERN-1R episode: GROUND-1 v2's session, copied. The flight runner is | 11 | 1 |
| [nexus0/pattern1r_v4/__init__.py](../../../nexus0/pattern1r_v4/__init__.py) | PATTERN-1R: object identity across views, from a scripted survey flight. | 0 | 1 |
| [nexus0/pattern1r_v4/assets/consumer.py](../../../nexus0/pattern1r_v4/assets/consumer.py) | PATTERN-1R v2 isolated consumer. Same sensor framing and WSP translation; | 0 | 0 |
| [nexus0/pattern1r_v4/assets/flightrunner_survey.py](../../../nexus0/pattern1r_v4/assets/flightrunner_survey.py) | PATTERN-1R survey runner: the frozen FLIGHT-1S stage script, copied, | 0 | 0 |
| [nexus0/pattern1r_v4/campaign.py](../../../nexus0/pattern1r_v4/campaign.py) | PATTERN-1R: GROUND-1 v2's coordinator, copied. The worlds come from this | 25 | 1 |
| [nexus0/pattern1r_v4/contract.py](../../../nexus0/pattern1r_v4/contract.py) | Only estimator barometer uncertainty changes; perception stays frozen. | 4 | 1 |
| [nexus0/pattern1r_v4/dev.py](../../../nexus0/pattern1r_v4/dev.py) | PATTERN-1R development flights: kept, never counted. | 16 | 0 |
| [nexus0/pattern1r_v4/development.py](../../../nexus0/pattern1r_v4/development.py) | Complete the six declared development worlds; never replace a flight. | 3 | 0 |
| [nexus0/pattern1r_v4/evaluate.py](../../../nexus0/pattern1r_v4/evaluate.py) | PATTERN-1R evaluator: GROUND-1's groups, plus what identity claims. | 9 | 1 |
| [nexus0/pattern1r_v4/inspect_dev.py](../../../nexus0/pattern1r_v4/inspect_dev.py) | Rejudge one development flight, preserving the verdict with its code hash. | 8 | 0 |
| [nexus0/pattern1r_v4/memory.py](../../../nexus0/pattern1r_v4/memory.py) | An ambiguous match is not evidence of a new family. | 1 | 0 |
| [nexus0/pattern1r_v4/regression_v2.py](../../../nexus0/pattern1r_v4/regression_v2.py) | Run every immutable v2 test with an absent, isolated test report. | 4 | 0 |
| [nexus0/pattern1r_v4/session.py](../../../nexus0/pattern1r_v4/session.py) | PATTERN-1R episode: GROUND-1 v2's session, copied. The flight runner is | 11 | 1 |
| [nexus0/plan.py](../../../nexus0/plan.py) | NEXUS-2: one- and two-step counterfactuals over T. | 4 | 1 |
| [nexus0/power1/__init__.py](../../../nexus0/power1/__init__.py) | POWER-1: integer energy viability; no authority over PX4 failsafes. | 0 | 1 |
| [nexus0/power1/bench.py](../../../nexus0/power1/bench.py) | Prospective functional bank, isolated consumer, reconstructing certificate. | 10 | 1 |
| [nexus0/power1/consumer.py](../../../nexus0/power1/consumer.py) | Isolated public battery/routes consumer; no world, seed or oracle access. | 1 | 0 |
| [nexus0/power1/controls.py](../../../nexus0/power1/controls.py) | Source mutants and altered records must fail independent checks. | 5 | 0 |
| [nexus0/power1/core.py](../../../nexus0/power1/core.py) | Cost gate, not a planner. Every movement output is the existing 16-byte WSP. | 1 | 2 |
| [nexus0/power1/telemetry.py](../../../nexus0/power1/telemetry.py) | External-unit adapter. Never invent current, capacity or measured joules. | 1 | 1 |
| [nexus0/power1/transport.py](../../../nexus0/power1/transport.py) | SIM-3 namespaces and existing synchronous transport, explicit dependencies. | 2 | 0 |
| [nexus0/power1/world.py](../../../nexus0/power1/world.py) | Private deterministic energy plant. Not mounted in the public consumer. | 2 | 1 |
| [nexus0/px41/__init__.py](../../../nexus0/px41/__init__.py) | PX4-1: bounded WSP execution; PX4 retains physical authority. | 0 | 0 |
| [nexus0/px41/assets/runner.py](../../../nexus0/px41/assets/runner.py) | Private SITL adapter. Only the gateway's bounded goal reaches MAVLink. | 2 | 0 |
| [nexus0/px41/audit.py](../../../nexus0/px41/audit.py) | Repeatable read-only entry point; delegates to the frozen verifier. | 1 | 0 |
| [nexus0/px41/bench.py](../../../nexus0/px41/bench.py) | Prospective PX4-1 campaign. No retuning after freeze; red B seals C. | 4 | 0 |
| [nexus0/px41/controls.py](../../../nexus0/px41/controls.py) | Actual source mutants and corrupted flight records, not self-reported flags. | 5 | 0 |
| [nexus0/px41/core.py](../../../nexus0/px41/core.py) | Integer-only transport gate. No arming, parameters, motor or mode commands. | 1 | 1 |
| [nexus0/px41/evaluate.py](../../../nexus0/px41/evaluate.py) | Reconstruct the gate and check independent PX4 ULog/physical evidence. | 7 | 0 |
| [nexus0/px41/session.py](../../../nexus0/px41/session.py) | Pinned simulator session; fixture intentions never depend on true pose. | 5 | 0 |
| [nexus0/qtable.py](../../../nexus0/qtable.py) | Integer Q-table for NEXUS-0. | 2 | 3 |
| [nexus0/qwen_sign.py](../../../nexus0/qwen_sign.py) | Qwen-0 operator report — SIGN, canonical + paraphrases, never CI-required. | 9 | 1 |
| [nexus0/qwen_signc.py](../../../nexus0/qwen_signc.py) | Qwen-0 operator report — SIGN-C, canonical + paraphrases, never CI-required. | 6 | 1 |
| [nexus0/room1.py](../../../nexus0/room1.py) | ROOM-1 — two rooms, one map. | 7 | 1 |
| [nexus0/safe1/__init__.py](../../../nexus0/safe1/__init__.py) | SAFE-1: bounded fault containment above frozen PX4/POWER gates. | 0 | 0 |
| [nexus0/safe1/assets/runner.py](../../../nexus0/safe1/assets/runner.py) | SITL-only safety adapter. Private pose is audit-only, never an action input. | 4 | 0 |
| [nexus0/safe1/assets/worker.py](../../../nexus0/safe1/assets/worker.py) | Experimental intention fixture, with explicit process/IPC fault variants. | 0 | 0 |
| [nexus0/safe1/bench.py](../../../nexus0/safe1/bench.py) | A -> freeze -> B -> C. Every scheduled fault flight is mandatory. | 8 | 0 |
| [nexus0/safe1/controls.py](../../../nexus0/safe1/controls.py) | Executable negative controls, never connected to an actuator. | 2 | 1 |
| [nexus0/safe1/core.py](../../../nexus0/safe1/core.py) | Integer supervisor; no recovery path and no direct actuator authority. | 2 | 2 |
| [nexus0/safe1/evaluate.py](../../../nexus0/safe1/evaluate.py) | Read-only replay, source binding and independent PX4 evidence. | 6 | 0 |
| [nexus0/safe1/functional.py](../../../nexus0/safe1/functional.py) | Deterministic fault fixtures; no simulator or actuator authority. | 2 | 2 |
| [nexus0/safe1/ipc.py](../../../nexus0/safe1/ipc.py) | A single bounded request/reply, including partial lines and blocked writes. | 0 | 1 |
| [nexus0/safe1/service.py](../../../nexus0/safe1/service.py) | Bounded operator setup/landing calls; never renew a mission's health permit here. | 0 | 1 |
| [nexus0/safe1/session.py](../../../nexus0/safe1/session.py) | Pinned, isolated SITL fault session. Previous milestone sources stay intact. | 5 | 0 |
| [nexus0/safe1_v2/__init__.py](../../../nexus0/safe1_v2/__init__.py) | SAFE-1 v2: unchanged safety runtime, corrected normal-arming audit. | 0 | 0 |
| [nexus0/safe1_v2/bench.py](../../../nexus0/safe1_v2/bench.py) | Fresh reserved bank after a narrow auditor correction; runtime remains v1. | 10 | 0 |
| [nexus0/safe1_v2/evaluate.py](../../../nexus0/safe1_v2/evaluate.py) | Narrow correction: distinguish normal rejected arm retries from forcing. | 1 | 1 |
| [nexus0/self1.py](../../../nexus0/self1.py) | SELF-1 — "was that me, or was that the floor?" | 6 | 1 |
| [nexus0/sensor1s/__init__.py](../../../nexus0/sensor1s/__init__.py) | SENSOR-1S: simulated sensors with explicit time, noise, latency, loss and source. | 0 | 6 |
| [nexus0/sensor1s/assets/consumer.py](../../../nexus0/sensor1s/assets/consumer.py) | SENSOR-1S consumer: runs in the SIM-3 cage and trusts nothing it reads. | 0 | 0 |
| [nexus0/sensor1s/assets/sensor_runner.py](../../../nexus0/sensor1s/assets/sensor_runner.py) | SENSOR-1S private side: the frozen v6 flight plus a sensor tap. | 0 | 0 |
| [nexus0/sensor1s/campaign.py](../../../nexus0/sensor1s/campaign.py) | SENSOR-1S: one prospective chain, raw evidence, an audit that rebuilds it. | 17 | 4 |
| [nexus0/sensor1s/contract.py](../../../nexus0/sensor1s/contract.py) | SENSOR-1S contract pieces: configuration, sources, declared noise, faults. | 3 | 6 |
| [nexus0/sensor1s/dev.py](../../../nexus0/sensor1s/dev.py) | Development flights in A: allowed by the contract, kept, never counted. | 11 | 0 |
| [nexus0/sensor1s/evaluate.py](../../../nexus0/sensor1s/evaluate.py) | SENSOR-1S evaluator: private truth against what the consumer received. | 2 | 3 |
| [nexus0/sensor1s/model.py](../../../nexus0/sensor1s/model.py) | The SENSOR-1S body: PX4's X500 with sensor elements and nothing else. | 1 | 1 |
| [nexus0/sensor1s/session.py](../../../nexus0/sensor1s/session.py) | One SENSOR-1S episode: the v6 flight with a sensor tap on the private | 9 | 2 |
| [nexus0/sensor1s_v2/__init__.py](../../../nexus0/sensor1s_v2/__init__.py) | SENSOR-1S v2: the sensor channel in its own process; v1 criteria unchanged. | 0 | 3 |
| [nexus0/sensor1s_v2/assets/sensor_runner.py](../../../nexus0/sensor1s_v2/assets/sensor_runner.py) | SENSOR-1S v2 private side: the v6 flight in one process, the sensor | 0 | 0 |
| [nexus0/sensor1s_v2/campaign.py](../../../nexus0/sensor1s_v2/campaign.py) | SENSOR-1S v2: v1's coordinator, copied; only namespace, seeds, channel | 19 | 3 |
| [nexus0/sensor1s_v2/dev.py](../../../nexus0/sensor1s_v2/dev.py) | SENSOR-1S v2 development flights in A: kept, never counted. | 12 | 0 |
| [nexus0/sensor1s_v2/session.py](../../../nexus0/sensor1s_v2/session.py) | SENSOR-1S v2 episode: v1's session, copied with three references changed | 9 | 2 |
| [nexus0/sensor1s_v3/__init__.py](../../../nexus0/sensor1s_v3/__init__.py) | SENSOR-1S v3: v2's channel; LiDAR bias judged only where truth can judge it. | 0 | 5 |
| [nexus0/sensor1s_v3/campaign.py](../../../nexus0/sensor1s_v3/campaign.py) | SENSOR-1S v3: v2's coordinator, copied; namespace, seeds, history and the | 20 | 4 |
| [nexus0/sensor1s_v3/evaluate.py](../../../nexus0/sensor1s_v3/evaluate.py) | SENSOR-1S v3 evaluator: v1's, copied, with one change. LiDAR bias is | 2 | 3 |
| [nexus0/shifts.py](../../../nexus0/shifts.py) | SHIFT-S: an acquired food becomes poisonous, without resetting memory. | 2 | 1 |
| [nexus0/sign.py](../../../nexus0/sign.py) | CORTEX-1 — the turn where the slow clock changes a decision. | 7 | 1 |
| [nexus0/signc.py](../../../nexus0/signc.py) | SIGN-C — the turn where being wrong is what makes the slow clock speak. | 11 | 1 |
| [nexus0/sim3/__init__.py](../../../nexus0/sim3/__init__.py) | SIM-3 — declarative worlds, real physics, and an information boundary. | 0 | 4 |
| [nexus0/sim3/__main__.py](../../../nexus0/sim3/__main__.py) | ``python3 -m echoai.nexus0.sim3`` — validate, preflight, bench, audit. | 9 | 0 |
| [nexus0/sim3/assets/gzrunner.py](../../../nexus0/sim3/assets/gzrunner.py) | Private side of SIM-3: the only process that talks to Gazebo. | 0 | 0 |
| [nexus0/sim3/assets/gzrunner_frozen.py](../../../nexus0/sim3/assets/gzrunner_frozen.py) | Mutant backend: a Gazebo that runs but reports a clock that never moves. | 0 | 0 |
| [nexus0/sim3/assets/probe.py](../../../nexus0/sim3/assets/probe.py) | The SIM-3 consumer: an instrumental probe, deliberately adversarial. | 0 | 0 |
| [nexus0/sim3/assets/probe_abusive.py](../../../nexus0/sim3/assets/probe_abusive.py) | A consumer that misbehaves on purpose. Never part of the 24 bench runs. | 0 | 0 |
| [nexus0/sim3/audit.py](../../../nexus0/sim3/audit.py) | An auditor that does not read ``sim3_green``. | 6 | 1 |
| [nexus0/sim3/bench.py](../../../nexus0/sim3/bench.py) | The preregistered SIM-3 bench. | 12 | 0 |
| [nexus0/sim3/canon.py](../../../nexus0/sim3/canon.py) | Bytes first, structure second. | 0 | 15 |
| [nexus0/sim3/ci.py](../../../nexus0/sim3/ci.py) | Fast, honest SIM-3 CI entry point. | 4 | 0 |
| [nexus0/sim3/declarations.py](../../../nexus0/sim3/declarations.py) | Validation of frozen campaign, world-family and slice declarations. | 2 | 2 |
| [nexus0/sim3/evaluate.py](../../../nexus0/sim3/evaluate.py) | The evaluator. It sees the truth; it never answers back. | 4 | 1 |
| [nexus0/sim3/generate.py](../../../nexus0/sim3/generate.py) | A declarative world generator with a PRNG you can reimplement. | 3 | 8 |
| [nexus0/sim3/geom.py](../../../nexus0/sim3/geom.py) | Millimetre integers, and the exact-decimal gate that produces them. | 1 | 1 |
| [nexus0/sim3/metamorph.py](../../../nexus0/sim3/metamorph.py) | Metamorphic pairs: two questions with known answers. | 4 | 1 |
| [nexus0/sim3/mutants.py](../../../nexus0/sim3/mutants.py) | Mutants: every refusal must be provoked from a control that passed. | 8 | 2 |
| [nexus0/sim3/pkg.py](../../../nexus0/sim3/pkg.py) | Packages: hash first, structure second, geometry last. | 3 | 9 |
| [nexus0/sim3/rig.py](../../../nexus0/sim3/rig.py) | The trusted rig, and the systems the supervisor is allowed to add. | 2 | 1 |
| [nexus0/sim3/runner.py](../../../nexus0/sim3/runner.py) | One host runner for ``preflight → bench → audit``. | 5 | 0 |
| [nexus0/sim3/runtime.py](../../../nexus0/sim3/runtime.py) | Preflight: find the real tools, or say plainly that they are missing. | 1 | 3 |
| [nexus0/sim3/sandbox.py](../../../nexus0/sim3/sandbox.py) | The consumer's cage, and the one wire that leaves it. | 2 | 2 |
| [nexus0/sim3/sdfprof.py](../../../nexus0/sim3/sdfprof.py) | The ``sim3-boxes-v1`` SDF profile: a closed grammar, not a filter. | 2 | 2 |
| [nexus0/sim3/seal.py](../../../nexus0/sim3/seal.py) | Commitments, derived seeds, and an exam you can only open once. | 1 | 11 |
| [nexus0/sim3/session.py](../../../nexus0/sim3/session.py) | One episode: Gazebo on the private side, a probe on the public side. | 6 | 1 |
| [nexus0/sleep2.py](../../../nexus0/sleep2.py) | SLEEP-2: consolidate repeated CAM/T transitions into compact rules. | 5 | 1 |
| [nexus0/stream1.py](../../../nexus0/stream1.py) | STREAM-1: long external WSP streams with DynamicAlias measured. | 7 | 1 |
| [nexus0/talk.py](../../../nexus0/talk.py) | TALK-1 — posthumous subtitles. Never a thought, never a cause. | 0 | 2 |
| [nexus0/talk1.py](../../../nexus0/talk1.py) | TALK-1 bench — does the subtitle say what the record says, and nothing else? | 10 | 1 |
| [nexus0/thought.py](../../../nexus0/thought.py) | NEXUS-4c — one line per turn, every turn. | 4 | 2 |
| [nexus0/tools/__init__.py](../../../nexus0/tools/__init__.py) | Dev tools for nexus0. Not imported by the fast loop. | 0 | 1 |
| [nexus0/tools/gen_lex.py](../../../nexus0/tools/gen_lex.py) | Regenerate the LEX table of `echoai/nexus0/lex.py` from | 0 | 1 |
| [nexus0/tools/qwen_cortex.py](../../../nexus0/tools/qwen_cortex.py) | Qwen-0 — the same cable as sign_cortex.py, with a local 4B behind it. | 0 | 1 |
| [nexus0/tools/sign_cortex.py](../../../nexus0/tools/sign_cortex.py) | CORTEX-1 — the slow clock, with no weights in it. | 0 | 1 |
| [nexus0/tools/signc_cortex.py](../../../nexus0/tools/signc_cortex.py) | SIGN-C — the slow clock for CI, with no weights in it. | 0 | 1 |
| [nexus0/transfer3/__init__.py](../../../nexus0/transfer3/__init__.py) | TRANSFER-3 preparation. No campaign or behavioural certificate yet. | 0 | 16 |
| [nexus0/transfer3/bench_b2.py](../../../nexus0/transfer3/bench_b2.py) | Bounded public Plan B2; exact replay, dependency closure, no real B/C. | 12 | 2 |
| [nexus0/transfer3/bench_b3.py](../../../nexus0/transfer3/bench_b3.py) | Explicit B3 adapters over the frozen B2 harness; public only. | 6 | 1 |
| [nexus0/transfer3/bench_c1.py](../../../nexus0/transfer3/bench_c1.py) | Plan C1 bench: camera extrinsic calibration. Pilot, confirmation, audit. | 12 | 1 |
| [nexus0/transfer3/body_a1.py](../../../nexus0/transfer3/body_a1.py) | Plan A1 body: integer movement costs with a non-conservative turn term. | 2 | 2 |
| [nexus0/transfer3/budget_school.py](../../../nexus0/transfer3/budget_school.py) | Exactly budgeted public school; no unseen tail transitions are executed. | 5 | 1 |
| [nexus0/transfer3/calib_a1.py](../../../nexus0/transfer3/calib_a1.py) | Movement-cost calibration learned from observed energy. No map, no geometry. | 1 | 2 |
| [nexus0/transfer3/calib_b2.py](../../../nexus0/transfer3/calib_b2.py) | Agent-safe bounded gain transfer, learned in the existing CAM/T model. | 2 | 2 |
| [nexus0/transfer3/calib_c1.py](../../../nexus0/transfer3/calib_c1.py) | Agent-safe camera extrinsic calibration. Knows sensors, never the world. | 1 | 1 |
| [nexus0/transfer3/camera_c1.py](../../../nexus0/transfer3/camera_c1.py) | Plan C1 world: a camera mounted with an extrinsic offset. Evaluator side only. | 2 | 1 |
| [nexus0/transfer3/campaign_c1.py](../../../nexus0/transfer3/campaign_c1.py) | Plan C1 sealed campaign A -> B -> C. The examiner side. Holds no secret. | 11 | 1 |
| [nexus0/transfer3/confirm_a2.py](../../../nexus0/transfer3/confirm_a2.py) | Plan A2: prospective public confirmation of the frozen turn-only candidate. | 9 | 2 |
| [nexus0/transfer3/confirm_a3.py](../../../nexus0/transfer3/confirm_a3.py) | Plan A3: does a learned cost parameter complete more missions in new rooms? | 9 | 1 |
| [nexus0/transfer3/consumer_a2.py](../../../nexus0/transfer3/consumer_a2.py) | Isolated Plan A2 consumer: frames in, one causal WSP plus diagnostics out. | 1 | 0 |
| [nexus0/transfer3/consumer_b2.py](../../../nexus0/transfer3/consumer_b2.py) | Isolated B2: only gain payload, goal, safe-mode and sensor frames. | 3 | 0 |
| [nexus0/transfer3/consumer_b3.py](../../../nexus0/transfer3/consumer_b3.py) | B3 isolated entrypoint. Same transport schema, conditional-motion planner. | 3 | 0 |
| [nexus0/transfer3/consumer_c1.py](../../../nexus0/transfer3/consumer_c1.py) | Isolated Plan C1 consumer. Frames in; one causal WSP, admitted cells out. | 1 | 0 |
| [nexus0/transfer3/costs_a2.py](../../../nexus0/transfer3/costs_a2.py) | Agent-safe movement-cost vocabulary. Contains nothing the evaluator knows. | 0 | 7 |
| [nexus0/transfer3/curve_v7.py](../../../nexus0/transfer3/curve_v7.py) | Coverage and representation conflict as a function of school budget. | 9 | 2 |
| [nexus0/transfer3/custodian_c1.py](../../../nexus0/transfer3/custodian_c1.py) | Plan C1 custodian. RUN THIS ONLY WHERE NEITHER AGENT CAN READ YOUR FILES. | 6 | 1 |
| [nexus0/transfer3/custody.py](../../../nexus0/transfer3/custody.py) | Public-commitment checks and an explicitly public custody rehearsal. | 2 | 2 |
| [nexus0/transfer3/custody_v2.py](../../../nexus0/transfer3/custody_v2.py) | Bound, ordered PUBLIC custody fixture. Real campaigns fail closed. | 3 | 1 |
| [nexus0/transfer3/diagnostic_v5.py](../../../nexus0/transfer3/diagnostic_v5.py) | Same-history Q interventions on existing PUBLIC v3/v4 traces only. | 7 | 1 |
| [nexus0/transfer3/filter_arch1.py](../../../nexus0/transfer3/filter_arch1.py) | ARCH-1 filter: does plan commitment make model precision pay? | 8 | 1 |
| [nexus0/transfer3/filter_b1.py](../../../nexus0/transfer3/filter_b1.py) | Plan B1 pre-campaign filter: can the planner profit from a calibrated body? | 7 | 1 |
| [nexus0/transfer3/gain_b1.py](../../../nexus0/transfer3/gain_b1.py) | Plan B1 body: per-action actuation gain. Evaluator side, never caged. | 5 | 4 |
| [nexus0/transfer3/model.py](../../../nexus0/transfer3/model.py) | Allowlisted, coordinate-free action-effect transfer; no episodic snapshot. | 1 | 1 |
| [nexus0/transfer3/planner_a1.py](../../../nexus0/transfer3/planner_a1.py) | Plan A1 planner: believed movement cost values the plan directly. | 5 | 1 |
| [nexus0/transfer3/planner_a2.py](../../../nexus0/transfer3/planner_a2.py) | Plan A2 planner: identical logic to A1, with an isolation-safe import graph. | 4 | 2 |
| [nexus0/transfer3/planner_arch1.py](../../../nexus0/transfer3/planner_arch1.py) | ARCH-1: bounded plan commitment. A versioned planner extension, not a new core. | 1 | 1 |
| [nexus0/transfer3/planner_b1.py](../../../nexus0/transfer3/planner_b1.py) | Plan B1 planner: burst-aware admissibility and a reserve consistent with belief. | 4 | 2 |
| [nexus0/transfer3/planner_b2.py](../../../nexus0/transfer3/planner_b2.py) | B2 reuses B1; safe reserve never discounts all directions by one gain. | 3 | 2 |
| [nexus0/transfer3/planner_b3.py](../../../nexus0/transfer3/planner_b3.py) | Gain plus observed braking, with one transition used by search and gates. | 5 | 1 |
| [nexus0/transfer3/planner_c1.py](../../../nexus0/transfer3/planner_c1.py) | Plan C1 planner: re-register the camera, then run the unchanged pipeline. | 4 | 1 |
| [nexus0/transfer3/policy.py](../../../nexus0/transfer3/policy.py) | V2 transfers relative-feature Q, with identical locomotion in both arms. | 3 | 7 |
| [nexus0/transfer3/rehearsal.py](../../../nexus0/transfer3/rehearsal.py) | Public functional development only. Never opens or generates campaign B/C. | 6 | 7 |
| [nexus0/transfer3/rehearsal_v2.py](../../../nexus0/transfer3/rehearsal_v2.py) | Public V2: geometry-disjoint rooms, common kinetics, frozen relative Q. | 8 | 6 |
| [nexus0/transfer3/rehearsal_v3.py](../../../nexus0/transfer3/rehearsal_v3.py) | Public one-factor-at-a-time trials after the single-ingestion correction. | 6 | 1 |
| [nexus0/transfer3/rehearsal_v4.py](../../../nexus0/transfer3/rehearsal_v4.py) | Equal-budget, prospectively specified public screening; not sealed B/C. | 8 | 4 |
| [nexus0/transfer3/repair_v5.py](../../../nexus0/transfer3/repair_v5.py) | Public development repairs. No new planner, campaign or exam claims. | 6 | 1 |
| [nexus0/transfer3/rooms_v8.py](../../../nexus0/transfer3/rooms_v8.py) | Room diversity at fixed school budget. One factor: how many distinct rooms. | 9 | 1 |
| [nexus0/transfer3/school_b2.py](../../../nexus0/transfer3/school_b2.py) | Evaluator-side gym. Learner receives frames only, never this world. | 3 | 2 |
| [nexus0/transfer3/school_c1.py](../../../nexus0/transfer3/school_c1.py) | Plan C1 school, evaluator side. The estimate is a pure function of frames. | 6 | 1 |
| [nexus0/transfer3/school_v3.py](../../../nexus0/transfer3/school_v3.py) | Single-ingestion school; reward and exploration are independent factors. | 6 | 2 |
| [nexus0/transfer3/school_v6.py](../../../nexus0/transfer3/school_v6.py) | Pessimistic transfer of unsampled actions. The factor lives in the export. | 5 | 3 |
| [nexus0/transfer3/screen_a1.py](../../../nexus0/transfer3/screen_a1.py) | Plan A1 development screen: does a learned cost calibration transfer? | 8 | 2 |
| [nexus0/transfer3/screen_a1_v2.py](../../../nexus0/transfer3/screen_a1_v2.py) | Plan A1 v2: the two degenerate controls of A1, replaced. | 6 | 2 |
| [nexus0/transfer3/screen_v6.py](../../../nexus0/transfer3/screen_v6.py) | Public v6 screening: one budgeted school, two exports, frozen v4 criterion. | 8 | 1 |
| [nexus0/transfer3/space_a2.py](../../../nexus0/transfer3/space_a2.py) | Plan A2 generator: two-wall extruded rooms. Evaluator side, never caged. | 4 | 3 |
| [nexus0/transfer3/transport_a2.py](../../../nexus0/transfer3/transport_a2.py) | Read-only dependency mount for the Plan A2 consumer. | 2 | 1 |
| [nexus0/transfer3/transport_b2.py](../../../nexus0/transfer3/transport_b2.py) | B2 explicit read-only mount, reusing A2 transport protocol and cleanup. | 2 | 1 |
| [nexus0/transfer3/transport_c1.py](../../../nexus0/transfer3/transport_c1.py) | Read-only dependency mount for the Plan C1 consumer. | 2 | 1 |
| [nexus0/types.py](../../../nexus0/types.py) | NEXUS-0 frozen types. Integers only. | 1 | 1 |
| [nexus0/view.py](../../../nexus0/view.py) | NEXUS-4c — replay the thought log in a terminal. | 3 | 1 |
| [nexus0/vita1.py](../../../nexus0/vita1.py) | VITA-1: environment clock; H itself belongs to the existing Agent. | 1 | 1 |
| [nexus0/world.py](../../../nexus0/world.py) | Discrete one-step world model T(s, a) → ŝ'. | 2 | 4 |
| [nexus0/xfer1.py](../../../nexus0/xfer1.py) | XFER-1 — the same animal, three worlds. | 11 | 1 |

## observe.py — 1 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [observe.py](../../../observe.py) | Mini terminal for real ECHO records, with no model or second thought bus. | 2 | 7 |

## observe_b5.py — 1 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [observe_b5.py](../../../observe_b5.py) | Display actual new S6/refinement records through the existing mini terminal. | 1 | 1 |

## release1 — 11 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [release1/build.py](../../../release1/build.py) | E4-RELEASE-1 · REL-A build: compiled core + open layer as one wheel. | 0 | 0 |
| [release1/cleanroom.py](../../../release1/cleanroom.py) | E4-RELEASE-1 · clean room: install the wheel in a new venv outside the repo and verify REL-A/REL-B. | 0 | 0 |
| [release1/echoai_release/__init__.py](../../../release1/echoai_release/__init__.py) | echoAI-4 release tooling (open layer): CLI, BYOK cortex, identity, reproduction. | 0 | 1 |
| [release1/echoai_release/__main__.py](../../../release1/echoai_release/__main__.py) | implementation-or-support (review required) | 1 | 0 |
| [release1/echoai_release/_hook.py](../../../release1/echoai_release/_hook.py) | Loaded from echoai_release.pth at interpreter start (release venv only). | 2 | 0 |
| [release1/echoai_release/cli.py](../../../release1/echoai_release/cli.py) | echoai — command line for the ECHO-4 release. | 11 | 0 |
| [release1/echoai_release/cortex.py](../../../release1/echoai_release/cortex.py) | BYOK cortex: any language model can be ECHO's slow, interchangeable cortex. | 3 | 1 |
| [release1/echoai_release/evidence.py](../../../release1/echoai_release/evidence.py) | Index of the sealed receipts shipped with the release (open evidence). | 0 | 0 |
| [release1/echoai_release/identity.py](../../../release1/echoai_release/identity.py) | Release identity: the compiled core has no source files to hash. | 11 | 0 |
| [release1/echoai_release/reproduce.py](../../../release1/echoai_release/reproduce.py) | Reproduce sealed evidence with the installed (compiled) agent. | 6 | 0 |
| [release1/review.py](../../../release1/review.py) | E4-RELEASE-1 · REL-C: export allowlist and secret/private-data scan of the wheel. | 0 | 0 |

## seed — 167 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [seed/__init__.py](../../../seed/__init__.py) | ECHO-SEED: an un-trained ECHO that learns concepts in clonable sandboxes (towards ECHO-4.5). | 0 | 68 |
| [seed/arc3gym.py](../../../seed/arc3gym.py) | ARC3-GYM · ECHO-4.5 S5 (docs/ECHO45-S5-DESIGN.md): generated turn-based games with the ARC-AGI-3 interface. | 3 | 4 |
| [seed/arc_b24_closure.py](../../../seed/arc_b24_closure.py) | Validate collected B24 closure custody using metadata only, without replay. | 0 | 1 |
| [seed/arc_capabilities.py](../../../seed/arc_capabilities.py) | Synthetic development diagnostics, separate from every reserved ARC exam. | 6 | 1 |
| [seed/arc_comparison.py](../../../seed/arc_comparison.py) | Prepare an auditable, budget-matched follow-up without reopening old exams. | 10 | 2 |
| [seed/arc_delayed_policy.py](../../../seed/arc_delayed_policy.py) | ARC-3E-POLICY-1: the existing delayed credit mechanism with new actions. | 1 | 1 |
| [seed/arc_memory.py](../../../seed/arc_memory.py) | ARC adapter for the existing 3E diary, evidence retrieval and suppression. | 5 | 4 |
| [seed/arc_v3_batch.py](../../../seed/arc_v3_batch.py) | Offline, resumable V3 batch evaluation. No LLM, learning or automatic submission. | 7 | 1 |
| [seed/associative_stress.py](../../../seed/associative_stress.py) | Controlled stress of the unchanged guide backend; no ARC solver or LLM. | 4 | 0 |
| [seed/associative_stress_report.py](../../../seed/associative_stress_report.py) | Read completed CAP-STRESS-1 outputs and render measured capacity curves. | 0 | 0 |
| [seed/capacity_forensics.py](../../../seed/capacity_forensics.py) | Read-only diagnosis of the frozen V2 guide, receipts and existing results. | 7 | 0 |
| [seed/capacity_media.py](../../../seed/capacity_media.py) | Publishable charts and 3D tree GIFs derived from verified capacity evidence. | 4 | 1 |
| [seed/capacity_study.py](../../../seed/capacity_study.py) | Capacity sweep, audited historical controls and a queue behind S6-PROBE1. | 8 | 1 |
| [seed/dreams.py](../../../seed/dreams.py) | ECHO-SEED · S2 dreams: invented tasks for training an intuition (recognition) network. | 3 | 0 |
| [seed/dsl.py](../../../seed/dsl.py) | ECHO-SEED · the starting primitives: small, typed Grid -> Grid operations. | 0 | 3 |
| [seed/echo45_completion.py](../../../seed/echo45_completion.py) | Local durable supervisor for the requested capacity comparison and S6 notice. | 2 | 1 |
| [seed/echo45_grid.py](../../../seed/echo45_grid.py) | Installable development entry point for the additive ECHO-4.5 grid solver. | 8 | 1 |
| [seed/echo45_grid_v2.py](../../../seed/echo45_grid_v2.py) | V2 entry point for the ECHO-4.5 grid development candidate. | 9 | 0 |
| [seed/echo45_v3.py](../../../seed/echo45_v3.py) | Private ECHO-4.5 V3 candidate: relational memory, delayed policy and guide. | 10 | 0 |
| [seed/final_arc.py](../../../seed/final_arc.py) | ARC final receipts with explicit reset provenance and complete action counts. | 5 | 2 |
| [seed/final_audit_recovery.py](../../../seed/final_audit_recovery.py) | Full R4 replay with a frozen, explicit correction of JSON representation comparison. | 4 | 1 |
| [seed/final_campaign.py](../../../seed/final_campaign.py) | Prepare and resume the frozen R1-R4 final examination, with a full replay audit. | 4 | 0 |
| [seed/final_eval.py](../../../seed/final_eval.py) | Final grid judge: test labels are never part of the solver input. | 5 | 1 |
| [seed/game_selfimprove.py](../../../seed/game_selfimprove.py) | S6-B0 training-only controller. Run with the separate ARC environment. | 6 | 10 |
| [seed/game_selfimprove_b1.py](../../../seed/game_selfimprove_b1.py) | S6-B1: format repair in a separate, source-pinned controller instance. | 0 | 0 |
| [seed/game_selfimprove_b2.py](../../../seed/game_selfimprove_b2.py) | S6-B2: format repair in a separate, source-pinned controller instance. | 1 | 0 |
| [seed/game_selfimprove_b3.py](../../../seed/game_selfimprove_b3.py) | B3: local observed verification, with short free GPU proposal jobs. | 7 | 1 |
| [seed/game_selfimprove_b4.py](../../../seed/game_selfimprove_b4.py) | Guarded-repair pilot and conditional continuation; all evidence is training-only. | 11 | 1 |
| [seed/game_selfimprove_b5.py](../../../seed/game_selfimprove_b5.py) | B5: precise repair pilot, adaptive campaign and one sealed examination. | 6 | 1 |
| [seed/grid_memory_update.py](../../../seed/grid_memory_update.py) | Acquire verified demonstration programs into a new development candidate. | 8 | 1 |
| [seed/gym.py](../../../seed/gym.py) | ECHO-SEED · the gym: training tasks only. Evaluation sets are sealed and cannot be read here. | 0 | 1 |
| [seed/integrated_grid.py](../../../seed/integrated_grid.py) | Additive ARC grid candidate: 3E receipts, cached synthesis and bounded views. | 4 | 1 |
| [seed/integrated_grid_v2.py](../../../seed/integrated_grid_v2.py) | V2 development candidate: relation-first residual synthesis and depth allocation. | 4 | 1 |
| [seed/integration_campaign.py](../../../seed/integration_campaign.py) | Recorded public-development ablations for the additive ECHO-4.5 candidate. | 11 | 1 |
| [seed/integration_followup.py](../../../seed/integration_followup.py) | Fixed V2 follow-up on disjoint public training tasks, without further tuning. | 5 | 0 |
| [seed/integration_report.py](../../../seed/integration_report.py) | Rebuild figures and a closure receipt from measured integration artifacts. | 2 | 0 |
| [seed/integration_revision.py](../../../seed/integration_revision.py) | V2 search-order hypothesis on the same public development cohort. | 8 | 0 |
| [seed/integration_transfer.py](../../../seed/integration_transfer.py) | Causal, synthetic transfer of verified ARC programs through the 3E diary. | 8 | 0 |
| [seed/intuition.py](../../../seed/intuition.py) | ECHO-SEED · S2 intuition network: look at a task's (input -> output) pairs, say which primitives to try. | 1 | 0 |
| [seed/kenyon_arc1.py](../../../seed/kenyon_arc1.py) | Frozen, training-only ARC-1 comparison of base / 640 / 500k guide units. | 9 | 1 |
| [seed/kenyon_bench.py](../../../seed/kenyon_bench.py) | Small synthetic development check of 640 versus 500k sparse guide units. | 3 | 1 |
| [seed/kenyon_capacity.py](../../../seed/kenyon_capacity.py) | Experimental sparse 500k-unit guide for ECHO-SEED's existing DSL search. | 3 | 4 |
| [seed/learn.py](../../../seed/learn.py) | ECHO-SEED · wake (search with the library) and sleep (compress solved programs into concepts). | 2 | 3 |
| [seed/program_guide_campaign.py](../../../seed/program_guide_campaign.py) | Executable associative capacity test; no ARC labels or model calls. | 5 | 1 |
| [seed/refinement.py](../../../seed/refinement.py) | Bounded multi-view program synthesis; only demonstrations establish facts. | 3 | 6 |
| [seed/refinement_bench.py](../../../seed/refinement_bench.py) | Preregistered ARC-2 training-only ablations; never read evaluation tasks. | 5 | 0 |
| [seed/refinement_s2v_bench.py](../../../seed/refinement_s2v_bench.py) | Additive development check using ECHO's learned S2v library; preserves S0 run. | 6 | 0 |
| [seed/relational_campaign.py](../../../seed/relational_campaign.py) | Preregistered private V3 module comparison. Commands: develop, prepare, run, audit. | 7 | 0 |
| [seed/relational_dsl.py](../../../seed/relational_dsl.py) | REL-DSL-1: bounded typed object programs; no task identifiers or test labels. | 3 | 1 |
| [seed/relational_report.py](../../../seed/relational_report.py) | Independent result arithmetic and private V3 closure/figures; no new solver runs. | 3 | 0 |
| [seed/relational_solver.py](../../../seed/relational_solver.py) | Integrated relational grid actor with exact verification and delayed cost policy. | 4 | 1 |
| [seed/relational_tasks.py](../../../seed/relational_tasks.py) | Private synthetic judges independent of REL-DSL executor. Never passed to actor. | 0 | 1 |
| [seed/rsi1.py](../../../seed/rsi1.py) | Private bounded library self-improvement, independent of all S6 cohorts. | 3 | 1 |
| [seed/rsi1_queue.py](../../../seed/rsi1_queue.py) | Wait for a valid PROBE2 completion, then execute the private free RSI assay. | 3 | 1 |
| [seed/rsi1_recovery1.py](../../../seed/rsi1_recovery1.py) | Declared CPU transport recovery of RSI1; original run remains immutable. | 3 | 1 |
| [seed/s6_capacity.py](../../../seed/s6_capacity.py) | Preregistered manual capacity controls; development only, no LLM or exam. | 11 | 1 |
| [seed/s6_followup_report.py](../../../seed/s6_followup_report.py) | Publish bounded B6/B7 closures only after their independent audits finish. | 1 | 0 |
| [seed/s6_precise_capacity.py](../../../seed/s6_precise_capacity.py) | B5 instrument control, frozen before measurement; no LLM or reserved exam. | 12 | 2 |
| [seed/s6_precise_exam.py](../../../seed/s6_precise_exam.py) | B5 examination: policies frozen first, no observer, independent replay/audit. | 8 | 2 |
| [seed/s6_prompt_pilot.py](../../../seed/s6_prompt_pilot.py) | Small paired-seed LLM pilot, gated by a completed human capacity control. | 4 | 1 |
| [seed/s6_transition_capacity.py](../../../seed/s6_transition_capacity.py) | Preregistered human instrument controls; no model and no examination. | 11 | 0 |
| [seed/s6b10.py](../../../seed/s6b10.py) | B10: witnessed guard decoding, paired model choices and unchanged exam gates. | 9 | 1 |
| [seed/s6b10_background.py](../../../seed/s6b10_background.py) | Resume the frozen B10 pipeline in a user service, independent of this chat. | 3 | 1 |
| [seed/s6b10_diagnose.py](../../../seed/s6b10_diagnose.py) | Post-mortem of existing B10 artifacts; no inference, games or exam access. | 3 | 0 |
| [seed/s6b10_exam.py](../../../seed/s6b10_exam.py) | New untouched cohort, four arms and the existing B1--B5 criteria. | 4 | 1 |
| [seed/s6b10_report.py](../../../seed/s6b10_report.py) | Use the same terminal proof checks for the B10 report, without exam reads. | 2 | 0 |
| [seed/s6b11.py](../../../seed/s6b11.py) | Frozen B11: contrasting development evidence and autonomous repair selection. | 14 | 1 |
| [seed/s6b11_background.py](../../../seed/s6b11_background.py) | B11 user-service supervisor. No repeated submissions or experimental changes. | 2 | 0 |
| [seed/s6b11_background2.py](../../../seed/s6b11_background2.py) | B11 user-service supervisor. No repeated submissions or experimental changes. | 2 | 0 |
| [seed/s6b11_exam.py](../../../seed/s6b11_exam.py) | B11 four-arm reserved evaluation; unchanged B1--B5, no instrumentation. | 4 | 1 |
| [seed/s6b11_recovery.py](../../../seed/s6b11_recovery.py) | Lossless transport extension for the unchanged, frozen B11 experiment. | 3 | 1 |
| [seed/s6b11_recovery2.py](../../../seed/s6b11_recovery2.py) | Lossless transport extension for the unchanged, frozen B11 experiment. | 4 | 1 |
| [seed/s6b12.py](../../../seed/s6b12.py) | B12: inherited, byte-identical audited pilot; fresh bounded-context campaign. | 7 | 1 |
| [seed/s6b12_background.py](../../../seed/s6b12_background.py) | Durable user service, bounded transport recovery and truthful desktop notice. | 2 | 0 |
| [seed/s6b12_exam.py](../../../seed/s6b12_exam.py) | B12 reserved exam, using the unchanged B11 evaluation and B1--B5 checks. | 3 | 1 |
| [seed/s6b12_recovery1.py](../../../seed/s6b12_recovery1.py) | Declared execution-time extension. Frozen B12 inference and gates are preserved. | 5 | 1 |
| [seed/s6b12_report.py](../../../seed/s6b12_report.py) | Read-only progress publisher. No solver, model, protected traces or submissions. | 0 | 0 |
| [seed/s6b13.py](../../../seed/s6b13.py) | Private S6-B13, sequential local proposals and unchanged scientific gates. | 12 | 4 |
| [seed/s6b13_audit_recovery1.py](../../../seed/s6b13_audit_recovery1.py) | Transport-only recovery of the completed, non-promoting B13-R1 pilot. | 2 | 1 |
| [seed/s6b13_exam.py](../../../seed/s6b13_exam.py) | B13's sealed four-arm exam. No observer, feedback or post-exam adaptation. | 4 | 1 |
| [seed/s6b13_model.py](../../../seed/s6b13_model.py) | Local, bounded Qwen proposals with exact tokenizer and immutable receipts. | 3 | 1 |
| [seed/s6b13_prompt.py](../../../seed/s6b13_prompt.py) | B13: own-evidence target memory, current-aware grammar, bounded prompts. | 7 | 2 |
| [seed/s6b13_runtime1.py](../../../seed/s6b13_runtime1.py) | Declared B13 restart with a private native CPU runtime; scientific code reused. | 4 | 1 |
| [seed/s6b14.py](../../../seed/s6b14.py) | B14: repaired experiment controller; frozen B13 executor and gates reused. | 7 | 1 |
| [seed/s6b14_prompt.py](../../../seed/s6b14_prompt.py) | B14 bounded prompts: mandatory latest receipt, relevant cases and replay memory. | 7 | 1 |
| [seed/s6b14_qualification.py](../../../seed/s6b14_qualification.py) | Real-history context regression and conservative replay exclusion checks. | 5 | 0 |
| [seed/s6b15.py](../../../seed/s6b15.py) | Private B15 condition; frozen B13 execution and scientific gates reused. | 9 | 1 |
| [seed/s6b15_micro.py](../../../seed/s6b15_micro.py) | Preregistered 2x2 transport/evidence ablation. DEVELOPMENT_A only. | 4 | 1 |
| [seed/s6b15_micro_audit.py](../../../seed/s6b15_micro_audit.py) | Read-only reconstruction of B15's closed micro; no new games or inference. | 5 | 0 |
| [seed/s6b15_prompt.py](../../../seed/s6b15_prompt.py) | B15: operator-bound proposals, selected-case applicability and numeric evidence. | 8 | 1 |
| [seed/s6b15_qualification.py](../../../seed/s6b15_qualification.py) | Instrument qualification using existing B14 A records and real token counts. | 5 | 0 |
| [seed/s6b16.py](../../../seed/s6b16.py) | B16: sequential repair using local level gains and faithful counterexamples. | 7 | 1 |
| [seed/s6b16_micro.py](../../../seed/s6b16_micro.py) | Paired sequential calibration: B15 controller versus B16, A only. | 7 | 1 |
| [seed/s6b16_prompt.py](../../../seed/s6b16_prompt.py) | B16 prompts retain B15 bounds and grammar, adding faithful local outcomes. | 4 | 1 |
| [seed/s6b16_qualification.py](../../../seed/s6b16_qualification.py) | Existing-record qualification of B16; no new games or generated proposals. | 6 | 0 |
| [seed/s6b16_recovery1.py](../../../seed/s6b16_recovery1.py) | Declared B16 recovery: canonicalize calibration parity, never outcomes. | 4 | 1 |
| [seed/s6b17.py](../../../seed/s6b17.py) | Private B17 micro: B16 / synthesis / hybrid, then independent A audit. | 10 | 2 |
| [seed/s6b17_prompt.py](../../../seed/s6b17_prompt.py) | B17: same legal language, mechanical scope search and bounded LLM choice. | 9 | 2 |
| [seed/s6b17_qualification.py](../../../seed/s6b17_qualification.py) | Qualify B17 orchestration and context using fixtures, never generate or play. | 5 | 0 |
| [seed/s6b18.py](../../../seed/s6b18.py) | Portable private B18 micro, independent audit and conditional retention judge. | 11 | 1 |
| [seed/s6b18_model.py](../../../seed/s6b18_model.py) | B18 CUDA transport, reusing the frozen bounded GGUF receipt machinery. | 2 | 0 |
| [seed/s6b19.py](../../../seed/s6b19.py) | B19 private qualification: targeted screen, broad development, fresh conservation. | 8 | 1 |
| [seed/s6b19_diagnostic.py](../../../seed/s6b19_diagnostic.py) | Declared post-B18 development; consumed B is never a new confirmation. | 5 | 0 |
| [seed/s6b20.py](../../../seed/s6b20.py) | Private B20 runner. Isolated caches, unchanged judge, explicit phase gates. | 10 | 1 |
| [seed/s6b20_capacity.py](../../../seed/s6b20_capacity.py) | Directed capability control, isolated from B20 discovery and model inputs. | 2 | 0 |
| [seed/s6b20_review.py](../../../seed/s6b20_review.py) | Independent arithmetic review: no solver, controller or game imports. | 0 | 0 |
| [seed/s6b21.py](../../../seed/s6b21.py) | B21-A CPU experiment: reuse the frozen evaluator with an explicit adapter. | 10 | 1 |
| [seed/s6b21_build.py](../../../seed/s6b21_build.py) | Stage a private, minimal B21-A runtime and wait for the audited B20 gate. | 2 | 1 |
| [seed/s6b21_report.py](../../../seed/s6b21_report.py) | Read-only experiment reporting; writes only the private results document. | 0 | 0 |
| [seed/s6b21_review.py](../../../seed/s6b21_review.py) | B21-A arithmetic review uses the frozen independent B20 arithmetic checker. | 1 | 0 |
| [seed/s6b22.py](../../../seed/s6b22.py) | Private B22 V/S experiment, using the frozen actor and individual-loss judge. | 10 | 1 |
| [seed/s6b22_build.py](../../../seed/s6b22_build.py) | Recover exact B21 receipts, review exposure, and freeze the private B22 runtime. | 3 | 1 |
| [seed/s6b22_forensics.py](../../../seed/s6b22_forensics.py) | Read-only B22 postmortem. No simulator, model, or experiment runner imports. | 0 | 1 |
| [seed/s6b22_forensics_neighbors.py](../../../seed/s6b22_forensics_neighbors.py) | Retrospective reconstruction of B22 repair rankings; never plays a game. | 3 | 0 |
| [seed/s6b22_report.py](../../../seed/s6b22_report.py) | Private progress report; reads receipts and never sends feedback to search. | 0 | 0 |
| [seed/s6b22_review.py](../../../seed/s6b22_review.py) | Independent stdlib arithmetic review. Does not import researcher or simulator. | 1 | 1 |
| [seed/s6b23.py](../../../seed/s6b23.py) | B23 five-arm micro, broad validation and sealed retention. Never opens S6. | 8 | 1 |
| [seed/s6b23_build.py](../../../seed/s6b23_build.py) | Private B23 packaging, source custody, model readiness and frozen launch. | 3 | 1 |
| [seed/s6b23_cloud.py](../../../seed/s6b23_cloud.py) | Freeze and run the private B23 bundle on Kaggle/Colab, using local assets. | 3 | 0 |
| [seed/s6b23_model.py](../../../seed/s6b23_model.py) | Pinned local GGUF transport. No API, downloads, or implicit model fallback. | 4 | 1 |
| [seed/s6b23_report.py](../../../seed/s6b23_report.py) | Read-only status summary; an old status file is never proof of a live process. | 0 | 1 |
| [seed/s6b23_review.py](../../../seed/s6b23_review.py) | Independent B23 arithmetic/accounting review; no simulator or researcher. | 1 | 0 |
| [seed/s6b23_smoke.py](../../../seed/s6b23_smoke.py) | Real baseline/replay/audit instrument check, isolated from the B23 experiment. | 3 | 0 |
| [seed/s6b23r4.py](../../../seed/s6b23r4.py) | B23-R4 two-model interface recovery, broad validation and sealed retention. Never opens S6. | 9 | 1 |
| [seed/s6b23r4_build.py](../../../seed/s6b23r4_build.py) | Freeze R4 from exact R3 source bytes and explicit, separately named changes. | 2 | 0 |
| [seed/s6b23r4_cloud.py](../../../seed/s6b23r4_cloud.py) | Freeze and run the private B23-R4 bundle on Kaggle/Colab, using local assets. | 3 | 0 |
| [seed/s6b23r4_model.py](../../../seed/s6b23r4_model.py) | R4 protocol recovery, reusing R3 transport/accounting without changing it. | 3 | 1 |
| [seed/s6b23r4_preflight.py](../../../seed/s6b23r4_preflight.py) | Real, zero-game, neutral format gate. Separate ledger; no training or feedback. | 6 | 1 |
| [seed/s6b23r4_review.py](../../../seed/s6b23r4_review.py) | Independent B23-R4 arithmetic/accounting review; no simulator or researcher. | 2 | 0 |
| [seed/s6b24.py](../../../seed/s6b24.py) | B24 repaired and cooperative researcher diagnostic. Never opens the S6 exam. | 9 | 3 |
| [seed/s6b24_build.py](../../../seed/s6b24_build.py) | Private B24 package. Frozen R4 remains byte-identical; no historical controls. | 2 | 0 |
| [seed/s6b24_cloud.py](../../../seed/s6b24_cloud.py) | Freeze and run the private B24 bundle on Kaggle/Colab, using local assets. | 3 | 0 |
| [seed/s6b24_model.py](../../../seed/s6b24_model.py) | B24 single pinned 7B transport, exact menu reconstruction and bounded accounting. | 7 | 4 |
| [seed/s6b24_preflight.py](../../../seed/s6b24_preflight.py) | Real, zero-game, neutral format gate. Separate ledger; no training or feedback. | 6 | 4 |
| [seed/s6b24_review.py](../../../seed/s6b24_review.py) | B24 arithmetic, physical custody and deterministic feedback review; no simulation. | 8 | 1 |
| [seed/s6b6.py](../../../seed/s6b6.py) | B6 pilot: explain parameter consumption and retrieve real decision sites. | 10 | 1 |
| [seed/s6b7.py](../../../seed/s6b7.py) | One bounded adaptive follow-up to B6, preserving every earlier result. | 4 | 1 |
| [seed/s6b8.py](../../../seed/s6b8.py) | B8: frozen adaptive repair experiment; no gate or reserved answer changes. | 13 | 2 |
| [seed/s6b8_cpu.py](../../../seed/s6b8_cpu.py) | Separate paired CPU continuation of B8; all original scientific gates kept. | 6 | 1 |
| [seed/s6b8_cpuq8.py](../../../seed/s6b8_cpuq8.py) | Separate paired CPU continuation of B8; all original scientific gates kept. | 6 | 1 |
| [seed/s6b8_exam.py](../../../seed/s6b8_exam.py) | B8 examination: distinct unopened cohort and unchanged scientific gates. | 5 | 1 |
| [seed/s6b8_recovery.py](../../../seed/s6b8_recovery.py) | One manual infrastructure recovery; original B8 sources and receipts intact. | 4 | 1 |
| [seed/s6b9.py](../../../seed/s6b9.py) | B9: observed contradictions, bounded transition revision, paired CPU proposals. | 11 | 1 |
| [seed/s6b9_exam.py](../../../seed/s6b9_exam.py) | B9 uses the unchanged four-arm exam logic on a distinct unopened cohort. | 4 | 1 |
| [seed/s6b9_report.py](../../../seed/s6b9_report.py) | Publish terminal artifacts only; never attach to or instrument an examination. | 1 | 1 |
| [seed/s6probe1.py](../../../seed/s6probe1.py) | S6-PROBE1: capacity control from the audited B12 program (378 A levels). | 10 | 2 |
| [seed/s6probe1_audit.py](../../../seed/s6probe1_audit.py) | Independent PROBE1 re-execution, using frozen actors in a separate cache. | 7 | 0 |
| [seed/s6probe1_audit_recovery1.py](../../../seed/s6probe1_audit_recovery1.py) | Audit instrument recovery: compare canonical JSON, preserve frozen execution. | 2 | 0 |
| [seed/s6probe2.py](../../../seed/s6probe2.py) | S6-PROBE2: directed capacity control for HOLD 0/1, selected after PROBE1. | 9 | 1 |
| [seed/s6probe2_calibrate.py](../../../seed/s6probe2_calibrate.py) | Wait for the independent audit, then freeze and calibrate PROBE2 only. | 2 | 0 |
| [seed/s6probe2_independent.py](../../../seed/s6probe2_independent.py) | Independent replay of PROBE2's base and both V3 survivors, A only. | 7 | 0 |
| [seed/sandbox.py](../../../seed/sandbox.py) | ECHO-SEED · clonable sandboxes where an un-trained ECHO learns concepts (towards ECHO-4.5). | 5 | 2 |
| [seed/selfimprove.py](../../../seed/selfimprove.py) | ECHO-4.5 S6 · self-improvement: ECHO asks, a language model proposes, ECHO verifies (docs/ECHO45-S6-AUTOMEJORA-DESIGN.md). | 5 | 1 |
| [seed/verified_program_guide.py](../../../seed/verified_program_guide.py) | Sparse guide for verified executable schemas over color/translation invariant motifs. | 5 | 1 |
| [seed/village.py](../../../seed/village.py) | EGO-MEMORIA-1 · the village: agents that help or lie, forgetting, a costly diary, and future claims. | 0 | 0 |
| [seed/village2.py](../../../seed/village2.py) | A second village condition: costly verified receipts and observed-return learning. | 1 | 1 |
| [seed/village2_campaign.py](../../../seed/village2_campaign.py) | Development, one frozen village examination and a fresh-process full audit. | 3 | 1 |
| [seed/village3.py](../../../seed/village3.py) | Age-matched observed returns; the village2 world and diary stay unchanged. | 3 | 1 |
| [seed/village3_campaign.py](../../../seed/village3_campaign.py) | Versioned memory experiment; no writes to closed village2 artifacts. | 5 | 0 |
| [seed/village3_efficient.py](../../../seed/village3_efficient.py) | Completed, factorized returns with exploration reduced by acquired evidence. | 3 | 1 |
| [seed/village3_efficient_campaign.py](../../../seed/village3_efficient_campaign.py) | Second development hypothesis, with its own freeze, receipts and exam. | 4 | 0 |
| [seed/village3_factorized.py](../../../seed/village3_factorized.py) | Separate observed immediate costs from age-matched downstream costs. | 3 | 1 |
| [seed/village3_factorized_campaign.py](../../../seed/village3_factorized_campaign.py) | Second development hypothesis, with its own freeze, receipts and exam. | 4 | 0 |
| [seed/village3_receipts.py](../../../seed/village3_receipts.py) | Learn delayed costs by retained-proof affordance, from executed outcomes. | 4 | 1 |
| [seed/village3_receipts_campaign.py](../../../seed/village3_receipts_campaign.py) | Second development hypothesis, with its own freeze, receipts and exam. | 4 | 0 |
| [seed/village3_settled.py](../../../seed/village3_settled.py) | Factorized returns mature after the world's declared maximum delay + 1. | 3 | 1 |
| [seed/village3_settled_campaign.py](../../../seed/village3_settled_campaign.py) | Second development hypothesis, with its own freeze, receipts and exam. | 4 | 0 |

## tests — 204 archivos

| Archivo | Descripción declarada / rol orientativo | Dependencias locales | Tests importadores |
|---|---|---:|---:|
| [tests/__init__.py](../../../tests/__init__.py) | test | 0 | 0 |
| [tests/test_arc_b24_closure.py](../../../tests/test_arc_b24_closure.py) | Synthetic local B24 custody only: no runner, models, datasets or games. | 1 | 0 |
| [tests/test_arc_capabilities.py](../../../tests/test_arc_capabilities.py) | test | 7 | 0 |
| [tests/test_arc_comparison.py](../../../tests/test_arc_comparison.py) | test | 3 | 0 |
| [tests/test_arc_integration.py](../../../tests/test_arc_integration.py) | test | 6 | 2 |
| [tests/test_arc_v3_batch.py](../../../tests/test_arc_v3_batch.py) | Batch evaluation must not leak labels, hide failures or rescore guesses as proofs. | 4 | 0 |
| [tests/test_b4_inference_audit.py](../../../tests/test_b4_inference_audit.py) | test | 0 | 0 |
| [tests/test_b4_recovery.py](../../../tests/test_b4_recovery.py) | test | 0 | 0 |
| [tests/test_b4_recovery2.py](../../../tests/test_b4_recovery2.py) | test | 0 | 0 |
| [tests/test_capacity1.py](../../../tests/test_capacity1.py) | CAPACITY-1: fixed sensory interface, causal controls and certificate. | 2 | 0 |
| [tests/test_capacity_study.py](../../../tests/test_capacity_study.py) | Scientific-integrity checks; no ARC solve, holdout or S6 game is executed. | 5 | 0 |
| [tests/test_cause1.py](../../../tests/test_cause1.py) | Counterexamples to attribution, timing and public input boundaries. | 4 | 0 |
| [tests/test_compose1.py](../../../tests/test_compose1.py) | test | 5 | 0 |
| [tests/test_compose1_v2.py](../../../tests/test_compose1_v2.py) | Behavioral regressions for composition, evidence and the physical boundary. | 8 | 0 |
| [tests/test_compose1_v3.py](../../../tests/test_compose1_v3.py) | Behavioral regressions for composition, evidence and the physical boundary. | 8 | 0 |
| [tests/test_compose1_v4.py](../../../tests/test_compose1_v4.py) | Sample-design regressions, including the discrete red that motivated V4. | 4 | 0 |
| [tests/test_consumer_observe.py](../../../tests/test_consumer_observe.py) | test | 7 | 0 |
| [tests/test_consumer_requests.py](../../../tests/test_consumer_requests.py) | test | 5 | 0 |
| [tests/test_consumption_evidence.py](../../../tests/test_consumption_evidence.py) | test | 3 | 0 |
| [tests/test_cpu_quantization.py](../../../tests/test_cpu_quantization.py) | test | 0 | 0 |
| [tests/test_drone3.py](../../../tests/test_drone3.py) | DRONE-3: gates, gateway, supervisor, calibration, energy and agent contracts. | 14 | 0 |
| [tests/test_dynamic1.py](../../../tests/test_dynamic1.py) | DYNAMIC-1: what moves, and where it will be in half a second. | 16 | 0 |
| [tests/test_dynamic1_v2.py](../../../tests/test_dynamic1_v2.py) | DYNAMIC-1 v2: the face, not a point. | 14 | 0 |
| [tests/test_echo2.py](../../../tests/test_echo2.py) | ECHO-2's first slices: real terminal turns and object consequences. | 10 | 0 |
| [tests/test_echo45_completion.py](../../../tests/test_echo45_completion.py) | test | 1 | 0 |
| [tests/test_echo4_bench1.py](../../../tests/test_echo4_bench1.py) | E4-BENCH-1 A · grader, ECHO verifier, structural property and a mock end-to-end run. | 2 | 0 |
| [tests/test_echo4_boundary1.py](../../../tests/test_echo4_boundary1.py) | Prospective BOUNDARY tests: causal controls, provenance and bounded state. | 10 | 0 |
| [tests/test_echo4_code1.py](../../../tests/test_echo4_code1.py) | E4-CODE-1 A · the command gate against the frozen exam corpus (allowlist, deny-by-default). | 2 | 0 |
| [tests/test_echo4_code1_memory.py](../../../tests/test_echo4_code1_memory.py) | E4-CODE-1 A · verified memory and MCP protocol (unit tests, development). | 2 | 0 |
| [tests/test_echo4_continuity1.py](../../../tests/test_echo4_continuity1.py) | CONT-A persistence tests; these do not close full E4-CONTINUITY-1. | 7 | 0 |
| [tests/test_echo4_continuity1b.py](../../../tests/test_echo4_continuity1b.py) | CONT-B tests. A passing component does not close CONTINUITY-1. | 9 | 0 |
| [tests/test_echo4_continuity1c.py](../../../tests/test_echo4_continuity1c.py) | CONT-C lineage, quarantine and custody tests; no full-phase green. | 5 | 0 |
| [tests/test_echo4_continuity1d.py](../../../tests/test_echo4_continuity1d.py) | CONT-D: A-only preparation, source-lock protocol, independent audit negatives. | 3 | 0 |
| [tests/test_echo4_dream1.py](../../../tests/test_echo4_dream1.py) | DREAM B/C/D infrastructure; never opens the frozen campaign partitions. | 10 | 0 |
| [tests/test_echo4_dream1_v2.py](../../../tests/test_echo4_dream1_v2.py) | DREAM-D v2 tests use synthetic scores or bodies outside the exam domain. | 11 | 0 |
| [tests/test_echo4_dream1_v3.py](../../../tests/test_echo4_dream1_v3.py) | DREAM-v3 fixtures stay outside prospective H65..96; no real LLM here. | 10 | 0 |
| [tests/test_echo4_dream1a.py](../../../tests/test_echo4_dream1a.py) | DREAM-A: strict custody, partial information, budgets and native evidence. | 3 | 0 |
| [tests/test_echo4_integrate1.py](../../../tests/test_echo4_integrate1.py) | INTEGRATE-1: one memory, energy receipts, firewall ablation, resume, SITUATE, cortex off. | 3 | 0 |
| [tests/test_echo4_interaction1a.py](../../../tests/test_echo4_interaction1a.py) | INTERACTION-A physics, real native execution and fail-closed scope. | 7 | 0 |
| [tests/test_echo4_interaction1bcd.py](../../../tests/test_echo4_interaction1bcd.py) | INTERACTION B/C/D native learning, adverse observations and custody checks. | 12 | 0 |
| [tests/test_echo4_maintain1.py](../../../tests/test_echo4_maintain1.py) | MAINT-B/C/D: observation-only control, physical predictions and custody. | 10 | 0 |
| [tests/test_echo4_maintain1a.py](../../../tests/test_echo4_maintain1a.py) | MAINT-A: mechanism integrity, not a learned-maintenance acceptance exam. | 8 | 0 |
| [tests/test_echo4_other1.py](../../../tests/test_echo4_other1.py) | OTHER-1: public interfaces and real native agents, only development seeds. | 8 | 0 |
| [tests/test_echo4_relation1a.py](../../../tests/test_echo4_relation1a.py) | RELATION-A observed history, isolation, limits and reconstructive custody. | 10 | 1 |
| [tests/test_echo4_relation1b.py](../../../tests/test_echo4_relation1b.py) | RELATION-B help task: physics, derived rows, isolation, veto, limits, parity. | 8 | 0 |
| [tests/test_echo4_relation1c.py](../../../tests/test_echo4_relation1c.py) | RELATION-C: body relief, fail-stop on corrupt history, limits, invariant. | 3 | 0 |
| [tests/test_echo4_roles1.py](../../../tests/test_echo4_roles1.py) | ROLES-1 A/B: physics, receipts, rank claims as hypotheses, rows, veto, limits. | 5 | 0 |
| [tests/test_echo4_roles1_v2.py](../../../tests/test_echo4_roles1_v2.py) | ROLES-1 v2: native periodic exploration breaks the v1 tie trap. | 2 | 0 |
| [tests/test_echo4_roles1c.py](../../../tests/test_echo4_roles1c.py) | ROLES-C: veto fix, refusal window, relay hypotheses, absence, new member. | 4 | 0 |
| [tests/test_echo4_self1.py](../../../tests/test_echo4_self1.py) | SELF-A tests, not a substitute for attribution and behavioral recovery. | 10 | 0 |
| [tests/test_echo4_self1_final.py](../../../tests/test_echo4_self1_final.py) | Final SELF-1 confirmation, model limits, native controls and evidence custody. | 11 | 0 |
| [tests/test_echo4_self1b.py](../../../tests/test_echo4_self1b.py) | SELF-B conditional attribution, prequential probes and honest unknowns. | 9 | 0 |
| [tests/test_echo4_self1c.py](../../../tests/test_echo4_self1c.py) | SELF-C actual-loop recovery, selective T/PATTERN gating and replay. | 12 | 0 |
| [tests/test_echo4_self1c_v2.py](../../../tests/test_echo4_self1c_v2.py) | SELF-C v2: causal memory ablations, native trials and artifact integrity. | 10 | 0 |
| [tests/test_echo4_sensation1.py](../../../tests/test_echo4_sensation1.py) | SENSATION first deliverable: bounded history and independent audit checks. | 8 | 0 |
| [tests/test_echo4_sensation_predictor.py](../../../tests/test_echo4_sensation_predictor.py) | Prediction chronology, bounded learning, frozen exams and native wiring. | 10 | 0 |
| [tests/test_echo4_situate1.py](../../../tests/test_echo4_situate1.py) | SITUATE-1: substrate facts, own world proof, unknowns, claims, change detection. | 3 | 0 |
| [tests/test_echo4_situate2.py](../../../tests/test_echo4_situate2.py) | SITUATE-2: claim classification, belief firewall, profile, dream selection. | 3 | 0 |
| [tests/test_echo4_tribe.py](../../../tests/test_echo4_tribe.py) | ROLES-1 v3/v4/v5 «la tribu»: world, facts vs testimony, elimination, derived rank. | 5 | 0 |
| [tests/test_echo4_tribe_liar.py](../../../tests/test_echo4_tribe_liar.py) | ROLES-1 annex L: affirmative lies, prior detection, the key, derived reliability. | 5 | 0 |
| [tests/test_echo4_tribe_liar2.py](../../../tests/test_echo4_tribe_liar2.py) | ROLES-1 annex L v2: metaknowledge is a hypothesis; deduction considers itself. | 6 | 0 |
| [tests/test_echo4_world1.py](../../../tests/test_echo4_world1.py) | WORLD-1 physics, feasibility, observation limits and unchanged-agent wiring. | 10 | 0 |
| [tests/test_final_audit_recovery.py](../../../tests/test_final_audit_recovery.py) | test | 1 | 0 |
| [tests/test_final_exam.py](../../../tests/test_final_exam.py) | test | 2 | 0 |
| [tests/test_flight1s.py](../../../tests/test_flight1s.py) | FLIGHT-1S unit bank: worlds, envelope, protocol, ordering, boundary. | 14 | 0 |
| [tests/test_flight1s_backend.py](../../../tests/test_flight1s_backend.py) | FLIGHT-1S backend bank: real PX4 and Gazebo, or an explicit skip. | 12 | 0 |
| [tests/test_flight1s_v2.py](../../../tests/test_flight1s_v2.py) | FLIGHT-1S v2 unit bank: the repair, the rules, and v1 left alone. | 15 | 0 |
| [tests/test_flight1s_v3.py](../../../tests/test_flight1s_v3.py) | v3 tests: same acceptance bands, history intact, fail-closed certificate. | 7 | 0 |
| [tests/test_flight1s_v4.py](../../../tests/test_flight1s_v4.py) | Acceptance boundaries and reconstruction from real historical evidence. | 6 | 0 |
| [tests/test_flight1s_v5.py](../../../tests/test_flight1s_v5.py) | v5 changes only the fixed physical configuration; v4 acceptance is inherited. | 8 | 0 |
| [tests/test_flight1s_v6.py](../../../tests/test_flight1s_v6.py) | v6: aggregation identical to v4 when every flight is measured and never | 13 | 0 |
| [tests/test_fusion1.py](../../../tests/test_fusion1.py) | test | 9 | 0 |
| [tests/test_game_selfimprove.py](../../../tests/test_game_selfimprove.py) | Campaign witnesses: counterfactual credit, regression, resumability, journal tampering. | 2 | 0 |
| [tests/test_game_strategy.py](../../../tests/test_game_strategy.py) | Meaningful negative cases for the model/data boundary, without game dependencies. | 2 | 0 |
| [tests/test_gen1.py](../../../tests/test_gen1.py) | GEN-1: one inherited integer, fresh memories, causal controls. | 4 | 0 |
| [tests/test_gen1f.py](../../../tests/test_gen1f.py) | GEN-1f: inherited local evidence and its final certificate. | 5 | 0 |
| [tests/test_grid_memory_update.py](../../../tests/test_grid_memory_update.py) | test | 7 | 0 |
| [tests/test_ground1.py](../../../tests/test_ground1.py) | GROUND-1: the translation, its evaluator and its chain, before any lock. | 20 | 0 |
| [tests/test_ground1_v2.py](../../../tests/test_ground1_v2.py) | GROUND-1 v2: only the channel's sender changes. | 14 | 0 |
| [tests/test_gui4.py](../../../tests/test_gui4.py) | GUI-4 tests. | 7 | 0 |
| [tests/test_h1h3_exam.py](../../../tests/test_h1h3_exam.py) | Adverse checks for S5-F verdicts and reset accounting, without exam worlds. | 0 | 0 |
| [tests/test_heat1.py](../../../tests/test_heat1.py) | HEAT-1b: two-variable homeostasis and causal certificate. | 7 | 0 |
| [tests/test_host1.py](../../../tests/test_host1.py) | test | 8 | 0 |
| [tests/test_integration_deployment.py](../../../tests/test_integration_deployment.py) | test | 8 | 0 |
| [tests/test_kenyon_arc1.py](../../../tests/test_kenyon_arc1.py) | Outcome isolation and regression accounting for the development runner. | 1 | 0 |
| [tests/test_kenyon_capacity.py](../../../tests/test_kenyon_capacity.py) | Development-only checks for the optional sparse guide. | 2 | 0 |
| [tests/test_local_patch.py](../../../tests/test_local_patch.py) | test | 9 | 0 |
| [tests/test_localdev.py](../../../tests/test_localdev.py) | Engineering contracts; these tests neither open sealed exams nor call a model. | 4 | 0 |
| [tests/test_metaverse1.py](../../../tests/test_metaverse1.py) | META-WORLD-2 tests. | 7 | 0 |
| [tests/test_neural_viz.py](../../../tests/test_neural_viz.py) | NEURAL-VIZ-1 observes the live loop without becoming a decision path. | 5 | 0 |
| [tests/test_nexus0.py](../../../tests/test_nexus0.py) | NEXUS-0 KPI tests. Spec: echoai/docs/05-NEXUS-0-SPEC.md §12. | 46 | 0 |
| [tests/test_observe.py](../../../tests/test_observe.py) | Log boundary checks: split writes, replacement, tampering, no actor input. | 6 | 0 |
| [tests/test_observe_arc.py](../../../tests/test_observe_arc.py) | Real training-game parity. Run in the separately managed ARC environment. | 6 | 0 |
| [tests/test_observe_b5.py](../../../tests/test_observe_b5.py) | test | 1 | 0 |
| [tests/test_observe_s6.py](../../../tests/test_observe_s6.py) | Read-only display of paired requests, model receipts and measured outcomes. | 3 | 0 |
| [tests/test_pattern1.py](../../../tests/test_pattern1.py) | PATTERN-1: learned invariance without id/pose/context leakage. | 2 | 0 |
| [tests/test_pattern1r.py](../../../tests/test_pattern1r.py) | PATTERN-1R: the survey, the signature, and what identity claims. | 21 | 0 |
| [tests/test_pattern1r_v2.py](../../../tests/test_pattern1r_v2.py) | Real correspondence defects, identity controls and X500 route geometry. | 15 | 0 |
| [tests/test_pattern1r_v3.py](../../../tests/test_pattern1r_v3.py) | One new estimator covariance; the frozen perception contract stays intact. | 10 | 0 |
| [tests/test_pattern1r_v4.py](../../../tests/test_pattern1r_v4.py) | The final classifier is named from school, never from the exam. | 7 | 0 |
| [tests/test_power1.py](../../../tests/test_power1.py) | Counterexamples to percentage-only budgets and unjustified viability. | 5 | 0 |
| [tests/test_precise_patch.py](../../../tests/test_precise_patch.py) | test | 9 | 0 |
| [tests/test_px41.py](../../../tests/test_px41.py) | PX4-1 transport boundary, acknowledgement and completion regressions. | 2 | 0 |
| [tests/test_qtable.py](../../../tests/test_qtable.py) | Q-table: negative δ flips policy. No env required. | 2 | 0 |
| [tests/test_refinement.py](../../../tests/test_refinement.py) | test | 3 | 0 |
| [tests/test_relational_v3.py](../../../tests/test_relational_v3.py) | test | 10 | 0 |
| [tests/test_release1.py](../../../tests/test_release1.py) | E4-RELEASE-1: BYOK cortex protocol (mock servers), key hygiene, firewall, failures. | 4 | 0 |
| [tests/test_repair_campaign.py](../../../tests/test_repair_campaign.py) | test | 4 | 0 |
| [tests/test_repair_evidence.py](../../../tests/test_repair_evidence.py) | test | 1 | 0 |
| [tests/test_rsi1.py](../../../tests/test_rsi1.py) | test | 3 | 0 |
| [tests/test_rsi1_recovery1.py](../../../tests/test_rsi1_recovery1.py) | test | 2 | 0 |
| [tests/test_s6.py](../../../tests/test_s6.py) | test | 3 | 0 |
| [tests/test_s6_capacity.py](../../../tests/test_s6_capacity.py) | test | 2 | 0 |
| [tests/test_s6_precise_capacity.py](../../../tests/test_s6_precise_capacity.py) | test | 3 | 0 |
| [tests/test_s6_probe_cleanup.py](../../../tests/test_s6_probe_cleanup.py) | test | 0 | 0 |
| [tests/test_s6_prompt_pilot.py](../../../tests/test_s6_prompt_pilot.py) | test | 2 | 0 |
| [tests/test_s6_prompt_reporting.py](../../../tests/test_s6_prompt_reporting.py) | test | 0 | 0 |
| [tests/test_s6_publication.py](../../../tests/test_s6_publication.py) | test | 1 | 0 |
| [tests/test_s6b10.py](../../../tests/test_s6b10.py) | test | 12 | 0 |
| [tests/test_s6b10_background.py](../../../tests/test_s6b10_background.py) | test | 2 | 0 |
| [tests/test_s6b11.py](../../../tests/test_s6b11.py) | test | 11 | 0 |
| [tests/test_s6b11_recovery.py](../../../tests/test_s6b11_recovery.py) | test | 2 | 0 |
| [tests/test_s6b11_recovery2.py](../../../tests/test_s6b11_recovery2.py) | test | 2 | 0 |
| [tests/test_s6b12.py](../../../tests/test_s6b12.py) | test | 5 | 0 |
| [tests/test_s6b12_recovery1.py](../../../tests/test_s6b12_recovery1.py) | R1 rejects changed results and duplicate submissions; never relaxes B12 gates. | 2 | 0 |
| [tests/test_s6b13.py](../../../tests/test_s6b13.py) | B13 custody, autonomous targeting, verifier and exam gates; no games. | 10 | 1 |
| [tests/test_s6b13_audit_recovery1.py](../../../tests/test_s6b13_audit_recovery1.py) | test | 2 | 0 |
| [tests/test_s6b13_runtime1.py](../../../tests/test_s6b13_runtime1.py) | Native restart wiring. No games and no model generations. | 3 | 0 |
| [tests/test_s6b14_policy.py](../../../tests/test_s6b14_policy.py) | test | 7 | 6 |
| [tests/test_s6b14_runner.py](../../../tests/test_s6b14_runner.py) | test | 3 | 0 |
| [tests/test_s6b15_policy.py](../../../tests/test_s6b15_policy.py) | test | 8 | 0 |
| [tests/test_s6b15_runner.py](../../../tests/test_s6b15_runner.py) | test | 4 | 0 |
| [tests/test_s6b16_policy.py](../../../tests/test_s6b16_policy.py) | test | 6 | 1 |
| [tests/test_s6b16_recovery1.py](../../../tests/test_s6b16_recovery1.py) | test | 2 | 0 |
| [tests/test_s6b16_runner.py](../../../tests/test_s6b16_runner.py) | test | 5 | 0 |
| [tests/test_s6b17_runner.py](../../../tests/test_s6b17_runner.py) | test | 6 | 0 |
| [tests/test_s6b17_synthesis.py](../../../tests/test_s6b17_synthesis.py) | test | 6 | 0 |
| [tests/test_s6b17_timeline.py](../../../tests/test_s6b17_timeline.py) | test | 7 | 1 |
| [tests/test_s6b18.py](../../../tests/test_s6b18.py) | test | 5 | 4 |
| [tests/test_s6b19.py](../../../tests/test_s6b19.py) | test | 5 | 0 |
| [tests/test_s6b20.py](../../../tests/test_s6b20.py) | test | 6 | 0 |
| [tests/test_s6b21.py](../../../tests/test_s6b21.py) | test | 7 | 0 |
| [tests/test_s6b22.py](../../../tests/test_s6b22.py) | test | 7 | 0 |
| [tests/test_s6b22_forensics.py](../../../tests/test_s6b22_forensics.py) | Checks of the postmortem instrument, without game execution. | 1 | 0 |
| [tests/test_s6b23.py](../../../tests/test_s6b23.py) | test | 9 | 1 |
| [tests/test_s6b23r4.py](../../../tests/test_s6b23r4.py) | Regression tests for the B23-R3 format failure and its isolated recovery. | 9 | 0 |
| [tests/test_s6b24_model.py](../../../tests/test_s6b24_model.py) | Protocol and custody regression tests; no model or game runs. | 3 | 0 |
| [tests/test_s6b24_r1_package.py](../../../tests/test_s6b24_r1_package.py) | R1 package checks, run by the owned validate.py in an isolated ZIP extraction. | 4 | 0 |
| [tests/test_s6b24_r1_transport.py](../../../tests/test_s6b24_r1_transport.py) | Read-only B24 v1 transport regression; no inference, tokenizer or games. | 4 | 0 |
| [tests/test_s6b24_review.py](../../../tests/test_s6b24_review.py) | Synthetic B24 review regressions: no games, models, network or saved results. | 8 | 0 |
| [tests/test_s6b24_runner.py](../../../tests/test_s6b24_runner.py) | B24 custody and budget checks; simulation functions remain mocked here. | 2 | 0 |
| [tests/test_s6b24_search.py](../../../tests/test_s6b24_search.py) | Synthetic researcher contracts: no games, historical controls, or inference. | 6 | 0 |
| [tests/test_s6b5.py](../../../tests/test_s6b5.py) | test | 3 | 0 |
| [tests/test_s6b6.py](../../../tests/test_s6b6.py) | test | 2 | 0 |
| [tests/test_s6b7.py](../../../tests/test_s6b7.py) | test | 2 | 0 |
| [tests/test_s6b8.py](../../../tests/test_s6b8.py) | test | 10 | 0 |
| [tests/test_s6b8_cpu.py](../../../tests/test_s6b8_cpu.py) | test | 2 | 0 |
| [tests/test_s6b8_cpuq8.py](../../../tests/test_s6b8_cpuq8.py) | test | 2 | 0 |
| [tests/test_s6b8_recovery.py](../../../tests/test_s6b8_recovery.py) | test | 3 | 0 |
| [tests/test_s6b9.py](../../../tests/test_s6b9.py) | test | 11 | 0 |
| [tests/test_s6b9_report.py](../../../tests/test_s6b9_report.py) | test | 1 | 0 |
| [tests/test_s6probe1.py](../../../tests/test_s6probe1.py) | test | 4 | 0 |
| [tests/test_s6probe2.py](../../../tests/test_s6probe2.py) | test | 6 | 0 |
| [tests/test_safe1.py](../../../tests/test_safe1.py) | test | 5 | 0 |
| [tests/test_safe1_v2.py](../../../tests/test_safe1_v2.py) | test | 1 | 0 |
| [tests/test_sensor1s.py](../../../tests/test_sensor1s.py) | SENSOR-1S: the rig, the consumer, the geometry, the evaluator, and the | 12 | 0 |
| [tests/test_sensor1s_v2.py](../../../tests/test_sensor1s_v2.py) | SENSOR-1S v2: only the process boundary and the pipe change. | 11 | 0 |
| [tests/test_sensor1s_v3.py](../../../tests/test_sensor1s_v3.py) | SENSOR-1S v3: only the LiDAR bias judgement changes. | 12 | 0 |
| [tests/test_shifts.py](../../../tests/test_shifts.py) | SHIFT-S: preserved memory, changed physics, measurable adaptation. | 5 | 0 |
| [tests/test_sim3.py](../../../tests/test_sim3.py) | SIM-3 unit bank: profile, packages, geometry, generator, seal, transport. | 12 | 0 |
| [tests/test_sim3_backend.py](../../../tests/test_sim3_backend.py) | SIM-3 backend bank: real Gazebo, real namespaces, or an explicit skip. | 9 | 0 |
| [tests/test_sleep2.py](../../../tests/test_sleep2.py) | SLEEP-2: bounded consolidation with immutable CAM/T sources. | 2 | 0 |
| [tests/test_stale_transition.py](../../../tests/test_stale_transition.py) | test | 2 | 0 |
| [tests/test_strategy_grammar.py](../../../tests/test_strategy_grammar.py) | test | 2 | 0 |
| [tests/test_stream1.py](../../../tests/test_stream1.py) | STREAM-1: external chunks stay outside WSP while alias stays visible. | 2 | 0 |
| [tests/test_temporal_arc.py](../../../tests/test_temporal_arc.py) | ARC integration, hidden-state controls and passive observer parity. | 8 | 0 |
| [tests/test_temporal_campaign.py](../../../tests/test_temporal_campaign.py) | Scientific boundaries for B3; stdlib-only checks before launch. | 4 | 0 |
| [tests/test_temporal_memory.py](../../../tests/test_temporal_memory.py) | Semantic properties of order/count memory, runnable with system Python. | 1 | 0 |
| [tests/test_temporal_policy.py](../../../tests/test_temporal_policy.py) | B3 data boundary and private native policy integration. | 11 | 0 |
| [tests/test_transfer3.py](../../../tests/test_transfer3.py) | Public functional development; not a reserved confirmation bank. | 5 | 0 |
| [tests/test_transfer3_a1.py](../../../tests/test_transfer3_a1.py) | Plan A1: movement-cost calibration. Public development, not a campaign. | 8 | 0 |
| [tests/test_transfer3_a1_v2.py](../../../tests/test_transfer3_a1_v2.py) | Plan A1 v2: the amended controls must not be degenerate. | 7 | 0 |
| [tests/test_transfer3_a2.py](../../../tests/test_transfer3_a2.py) | Plan A2: extended generator, isolation-safe planner, prospective confirmation. | 11 | 0 |
| [tests/test_transfer3_a3.py](../../../tests/test_transfer3_a3.py) | Plan A3: mission-completion endpoint, McNemar, hand-set prior controls. | 5 | 0 |
| [tests/test_transfer3_arch1.py](../../../tests/test_transfer3_arch1.py) | ARCH-1: bounded plan commitment. Gates must survive the commitment. | 6 | 0 |
| [tests/test_transfer3_b1.py](../../../tests/test_transfer3_b1.py) | Plan B1: actuation gain, burst-aware gate, pre-campaign filter. | 6 | 0 |
| [tests/test_transfer3_b2.py](../../../tests/test_transfer3_b2.py) | test | 10 | 0 |
| [tests/test_transfer3_b3.py](../../../tests/test_transfer3_b3.py) | test | 10 | 0 |
| [tests/test_transfer3_c1.py](../../../tests/test_transfer3_c1.py) | Plan C1: camera extrinsic calibration under two-family fusion. | 12 | 0 |
| [tests/test_transfer3_campaign_c1.py](../../../tests/test_transfer3_campaign_c1.py) | Plan C1 sealed campaign: ordering, binding and tamper detection. | 6 | 0 |
| [tests/test_transfer3_custody.py](../../../tests/test_transfer3_custody.py) | Preparation tests, not TRANSFER-3 acceptance. | 3 | 0 |
| [tests/test_transfer3_v2.py](../../../tests/test_transfer3_v2.py) | test | 4 | 0 |
| [tests/test_transfer3_v3.py](../../../tests/test_transfer3_v3.py) | Regression for single ingestion and independently varied school factors. | 7 | 0 |
| [tests/test_transfer3_v4.py](../../../tests/test_transfer3_v4.py) | test | 4 | 0 |
| [tests/test_transfer3_v5.py](../../../tests/test_transfer3_v5.py) | Repair regressions, not sealed transfer acceptance. | 12 | 0 |
| [tests/test_transfer3_v6.py](../../../tests/test_transfer3_v6.py) | V6: pessimistic transfer of unsampled planar actions. Public development. | 8 | 0 |
| [tests/test_transfer3_v7.py](../../../tests/test_transfer3_v7.py) | V7: coverage/conflict curve over school budget. Diagnostic, not selection. | 6 | 0 |
| [tests/test_transfer3_v8.py](../../../tests/test_transfer3_v8.py) | V8: room diversity at fixed budget. Public diagnostic, not selection. | 8 | 0 |
| [tests/test_village2.py](../../../tests/test_village2.py) | test | 5 | 0 |
| [tests/test_village3.py](../../../tests/test_village3.py) | test | 3 | 0 |
| [tests/test_village3_efficient.py](../../../tests/test_village3_efficient.py) | test | 3 | 0 |
| [tests/test_village3_factorized.py](../../../tests/test_village3_factorized.py) | test | 3 | 0 |
| [tests/test_village3_receipts.py](../../../tests/test_village3_receipts.py) | test | 3 | 0 |
| [tests/test_village3_settled.py](../../../tests/test_village3_settled.py) | test | 2 | 0 |

