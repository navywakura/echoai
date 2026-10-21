# STATUS — what is closed, and the number that closes it

<!-- S6B12-R1-BEGIN -->
**S6-B12-R1 — CAMPAIGN_NO_PROMOTION.** Recuperación declarada del límite remoto; mismas propuestas y criterios, reproducción exacta obligatoria de las siete respuestas guardadas. [Adenda](ECHO45-S6-B12-RECOVERY1.md) · [Seguimiento](ECHO45-S6-B12-LIVE.md).
<!-- S6B12-R1-END -->

<!-- S6B12-RESULT-BEGIN -->
**S6-B12 — CAMPAIGN_NO_PROMOTION. S6 todavía no verde.** Contexto verificado antes de inferencia, piloto previo auditado y campaña nueva. [Contrato](ECHO45-S6-B12-DESIGN.md) · [Resultados](ECHO45-S6-B12-RESULTS.md).
<!-- S6B12-RESULT-END -->

<!-- S6B11-RESULT-BEGIN -->
**S6-B11 — PENDING_ERROR. S6 todavía no verde.** Desarrollo ampliado, contrastes antes/después y selección adaptativa; conservación estricta. [Contrato](ECHO45-S6-B11-DESIGN.md) · [Resultado](ECHO45-S6-B11-RESULTS.md) · [Estado](../lab/seed/s6b11-20260929/status.json).
<!-- S6B11-RESULT-END -->

<!-- S6B10-RESULT-BEGIN -->
**S6-B10 — PILOTO SIN PROMOCIÓN. S6 todavía no verde.** ECHO 534, FIJO 534; aceptaciones ECHO 0. Piloto auditado, reserva sin abrir. [Resultado](ECHO45-S6-B10-RESULTS.md) · [Estado](../lab/seed/s6b10-20260929/status.json).
<!-- S6B10-RESULT-END -->

<!-- S6-DIAGNOSIS-20260929-BEGIN -->
**Diagnóstico S6, 29 sep:** B10 mejora niveles A y B, sin pérdida individual de niveles, pero todas sus propuestas hacen más lenta una misma partida protegida. V4 exige conservar también cada puntuación individual. Trece programas dan seis conductas medidas; evidencia de tareas repetida y feedback protegido limitado. B7 ya tuvo una mejora ECHO aceptada, pero empató con FIJO. No se cambian umbrales ni se abre reserva. [Criterios, historia y causa investigada](ECHO45-S6-DIAGNOSIS-20260929.md).
<!-- S6-DIAGNOSIS-20260929-END -->

<!-- S6B9-RESULT-BEGIN -->
**S6-B9 — PILOTO SIN PROMOCIÓN. S6 todavía no verde.** ECHO 534, FIJO 534; aceptaciones ECHO 0. Piloto auditado, reserva sin abrir. [Resultado](ECHO45-S6-B9-RESULTS.md) · [Estado](../lab/seed/s6b9-20260929/status.json).
<!-- S6B9-RESULT-END -->

**Histórico del 29 sep, 05:15–07:07 Madrid — S6-B9:** seis pruebas y paridad de la base completas; piloto cerrado sin promoción y auditoría válida. ECHO/FIJO 534–534, cero aceptaciones; reserva sin abrir. El control humano positivo (+8 A sin pérdidas A/B) no se atribuye al modelo. [Resultado B9](ECHO45-S6-B9-RESULTS.md) · [Control](ECHO45-S6-TRANSITION-RESULTS.md).

**Histórico del 29 sep — continuaciones CPU de S6-B8:** float16 terminó parcial (2/6 respuestas); la condición Q8 cerró el piloto y su auditoría, sin mejora ni promoción (534–534). Los cambios de backend están declarados y las reservas permanecen sin abrir. [Float16](ECHO45-S6-B8-CPU-DESIGN.md) · [Q8](ECHO45-S6-B8-CPUQ8-RESULTS.md).

**29 sep — S6-B8 pendiente:** implementación y 14 pruebas completas; doce propuestas auditadas, cero aceptaciones, suma A ECHO/FIJO 534–534. Faltan seis propuestas: dos trabajos fallaron durante la descarga de pesos y quedan 13 segundos de GPU gratis. Reserva sin abrir. [Informe](ECHO45-S6-B8-RESULTS.md) · [Después de S6](ECHO45-POST-S6-PLAN-20260929.md).

**29 sep 2026 — cierre de esta iteración:** EGO-MEMORIA-3E VERDE: M1–M5 16/16 y M6 exacto 16/16; revisiones 3A–3D conservadas. S6-B6/B7 cerrados y auditados; B7 ECHO 537 frente a FIJO 537, aceptaciones ECHO 1; sin promoción; examen final sin abrir. B5 y los exámenes anteriores permanecen cerrados; S6 todavía no se declara VERDE. [Memoria](ECHO45-EGO-MEMORIA3-RESULTS.md) · [Registro actual](ECHO45-RECOVERY-20260929.md).

<!-- S6B5-AUTO-BEGIN -->
**Estado automático S6-B5 — 2026-09-28 17:36 Madrid: CLOSED.**

Control preciso cerrado: 6/12 positivos, ganador preregistrado `hold20_after_level`. Es una reparación humana, no automejora.

Piloto: ECHO acepta 0; suma A ECHO 534, FIJO 534; promoción no.

S6 todavía no acredita B1–B5. Examen nuevo sin abrir.

[Contrato](ECHO45-S6-B5-DESIGN.md) · [Informe](ECHO45-S6-B5-RESULTS.md) · [Estado](../lab/seed/s6b5-20260928/status.json).
<!-- S6B5-AUTO-END -->

**ECHO-4.5, 2026-09-28 17:05 Madrid:** parches precisos probados y congelados;
doce controles con B nueva en curso. Tres primeros positivos (178→181 A,
sin pérdidas individuales A/B). B5 congelado y activo esperando cierre,
con piloto, cuatro brazos y reserva nuevos condicionados a promociones.
Refinamiento/varias vistas/relaciones implementados: tests pasan, cuatro
ablaciones ARC-2 0/12 con S0; condición nueva con biblioteca aprendida S2v
2/12 en los cuatro brazos, sin ventaja adicional. No se acredita transferencia.
[Roadmap temporal](ECHO4-ECHO5-TIMELINE.md).

**ECHO-4.5, 2026-09-28 16:03 Madrid:** ejecuciones terminadas. Control manual
S6: 20 reparaciones, ninguna supera V1–V4; cierre 15:31. `hold20` gana tres
niveles A sin pérdidas A, pero pierde puntuación en una partida B. Piloto
omitido, cero llamadas LLM/GPU. R4 cerrado 15:32: replay completo 1040
soluciones/32 partidas, procedencia y contabilidad válidas; R1/R4 pasan,
R2/R3 fallan. S6 y ECHO-4.5 siguen ROJOS. Nueva hipótesis/capacidad necesita
otro contrato y ensayos de desarrollo; no bajar umbrales ni reutilizar como
ciego el examen abierto. [Control](ECHO45-S6-CAPACITY-RESULTS.md) ·
[Examen](ECHO45-FINAL-EXAM-RESULTS.md) · [Roadmap](ECHO45-ECHO5-ROADMAP.md).

**ECHO-4.5, 2026-09-28 14:45 Madrid:** control positivo manual S6 implementado,
probado y congelado; 20 reparaciones legales en desarrollo bajo V1–V4 originales.
En segundo plano, cuatro procesos CPU, sin LLM ni examen. Activación histórica
FIJO 35/40, acciones distintas 1/40; ECHO 36/40, acciones distintas 0/40;
ambos 178 niveles. Resultado del control pendiente; S6 permanece ROJO.
R4: 32/32 partidas ARC reproducidas con contabilidad SDK válida; rejillas
todavía en replay. [Contrato del control](ECHO45-S6-CAPACITY-CONTROL.md) ·
[Estado vivo](NOW.md).

**ECHO-4.5, 2026-09-28 tarde:** medición final terminada: R1 31/400 frente a
20/400 (criterio pasa); R2 0/120 (falla); R3 11/112 frente a 13/112 (falla,
objetivo 23). Auditoría original interrumpida a las 04:07 por representación
tupla/lista del registro; recuperación explícita congelada y en ejecución.
No se modifican agente, criterios ni medidas. Cierre R4 todavía pendiente.
[Resultados](ECHO45-FINAL-EXAM-RESULTS.md) · [Estado vivo](NOW.md).

**ECHO-4.5, 2026-09-28 02:04 Madrid:** evaluación final R1–R4 implementada,
validada en desarrollo, congelada y ejecutándose en segundo plano. Resultados
pendientes; estimación de medición más auditoría 2–4 h. S6-B4 cerró su piloto
sin promoción: cero aceptaciones entre 24, seis rondas auditadas, examen sin
abrir; S6 continúa ROJO. EGO-MEMORIA-2 cerrado ROJO: M1–M4 16/16, M5 15/16,
M6 replay exacto 16/16. Borrador Kaggle CPU v5.8 local, sin envío externo.
[Roadmap](ECHO45-ECHO5-ROADMAP.md) · [Estado vivo](NOW.md).

**ECHO-4 RELATION-1 started — 2026-09-22:** RELATION-A implemented and verified.
Observed encounter histories on each agent's original CAM; no shared private
memory, policy change or transfer claim. 912 primary episodes reconstruct;
native behavior/cost parity with no-recording control and reversed execution.
36 new tests; 181 including selected INTERACTION/OTHER/core/Q regressions pass.
Fresh-process audit valid, no findings, `phase_a_valid=true`, `relation1_green=false`:
`ce24ccaa61f9d8b9b781274857b6ce15a9e75817bbf8d0b5fd2649a403369539`.
115 pinned sources; all 110 INTERACTION sources and artifacts intact.
Next RELATION-B: learned use and transfer, then C/D. History replay does not
resume the complete agent or prove consciousness. Remains 9/13 software
milestones (~69%, not effort). No Discord, hardware, web, commit/push or HF.
METAVERSE-1 last. [Results](ECHO4-RELATION1-A-RESULTS.md),
[contract](ECHO4-RELATION1-A-DESIGN.md).

**Historical ECHO-4 INTERACTION-1 closure — 2026-09-22:** B/C/D and fresh-process native
reconstruction pass. `valid=true`, no findings, `interaction1_green=true`:
`d1c5b073e7ac406ddd855184cc6f4bd1176d354eed57438eb51af1383f040735`.
110 pinned sources; all 104 A sources and sealed artifacts unchanged.
37 new tests and 11 adverse witnesses pass. Each new cohort: scored focal net
6912 vs solo/ablations 6144 (+12.5%); joint physical net 9984 vs 6656.
Formation costs remain: full-life focal net 14059/14136 vs solo 15360.
No full-life individual advantage, subjective consciousness or general social
planning claim. One-step asymmetric profile, pretrained native counterparts
with declared private incentives excluded from gain; original CAM/T/Q/gate,
WSP16, no basal LLM, no copied Agent loop. Integration remains pending.
Final regression: all 723 ECHO-4 tests and 33 selected core/Q tests pass;
756 distinct tests, no failures or skips.
Next RELATION, then ROLES, INTEGRATE, RELEASE. 9/13 software milestones (~69%,
including WORLD foundation), not effort/time estimate. HF not published;
hardware after software, METAVERSE-1 last. No Discord/web/commit/push.
[Results and limits](ECHO4-INTERACTION1-BCD-RESULTS.md),
[frozen contract](ECHO4-INTERACTION1-BCD-DESIGN.md).

**Historical ECHO-4 INTERACTION-1 start — 2026-09-22:** increment A verified.
Costed shared physics, two original Agent loops with private CAM/T/Q, one
own reward/update only after both gated actions. 243/243 transitions and nine
scripted mechanical witnesses; three native 144-round development sequences.
Per-agent net 485/690/668 versus solo 576 each: first sequence loses. OTHER
remains passive; matching symmetric policies is not learned negotiation.
35 new tests, 108 including selected regressions, all pass.
Fresh-process reconstruction valid, no findings, `phase_a_valid=true`,
**`interaction1_green=false`**. Digest:
`da8cc00befb52ac1abc9942bae1aa8eacf3fbe2049501dfebd26c2a1ed57c1c3`.
104 pinned sources; all 99 ancestral sources unchanged. Next INTERACTION-B,
then C/D. Software milestone count remains 8/13 (~62%, including WORLD as
implemented foundation), not estimated effort/time or integrated readiness.
Four scientific phases remain including INTERACTION, then RELEASE.
No Discord, hardware, web, commit, push or HF publication; METAVERSE-1 last.
[Results](ECHO4-INTERACTION1-A-RESULTS.md), [contract](ECHO4-INTERACTION1-A-DESIGN.md).

**Historical ECHO-4 OTHER-1 closure — 2026-09-22:** observational counterpart model on
the observer's original CAM/T, two native agents with private Q/memory/worlds.
40 new tests pass. Two new cohorts: identity 1536/1536 each versus pooled
1008/1536, self-copy 0/1536 and no-history 0/1536. On equal preferences,
self-copy also scores 1536/1536; no universal gain. First-half abstentions,
negative control errors and private learning costs remain in the evidence.

Fresh-process native reconstruction valid, no findings, `other1_green=true`:
`1263f11ab291a1ff350313a93a70d9f4b3b9259099482bb8425e9f414c2aa024`.
99 pinned sources, 93 parental sources unchanged. Scope: discrete observable
behavior prediction, NOT consciousness, useful coordination or thermal-body
integration. WSP16 and original CAM/T/Q/gate retained, no basal LLM.
Selected regression (OTHER/MAINTAIN/core/Q): 619 pass and one historical
expected failure, 620 distinct tests. Eight sandbox socket denials resolved
by rerunning the 29 affected GUI-class tests with localhost permission.
Next **E4-INTERACTION-1**. Four scientific phases remain: INTERACTION,
RELATION, ROLES, INTEGRATE; then RELEASE for planned `rxlabs/echoai-4`.
No publication, Discord, hardware, web, commit or push. METAVERSE-1 last.
[Results and limits](ECHO4-OTHER1-RESULTS.md), [contract](ECHO4-OTHER1-DESIGN.md).

**Historical ECHO-4 MAINTAIN-1 closure — 2026-09-22:** B/C/D and independent native
reconstruction pass. `valid=true`, no findings, `maintain1_green=true`, digest
`7e1c0e821ba2ddf79834fef6a66a16bfd2773a456d29ac5bbf535c11e6024fbe`.
93 pinned sources; original MAINT-A and earlier evidence unchanged.
Scope: autonomous virtual maintenance conditional on a declared mechanical
model, NOT physics/repair policy learned from scratch or general self-repair.

Two new cohorts, 960 lives: 144/144 recoverable lives completed and 192/192
repairs confirmed by subsequent executed cooling. Work 9450 vs fixed 7501,
no-repair 4815 and no-body-history 4672; all thresholds pass in each cohort.
Zero D deaths in all arms; 96/240 adaptive lives stop in the four limit scenarios.
24 paid services fail to repair; pairwise losses and all resource costs retained.
C: 12 fresh-process continuation cases, 257 identical future events and 11/11
rejected mutants. 85/85 MAINTAIN tests pass, 42 new. No cortex calls, resets, replenishment,
private causal truth in controller inputs, or hidden restoration.
Final regression: 611/611 ECHO-4 tests pass; including core/Q, 1105 pass and
one historical expected failure (1106 total). Eight sandbox socket denials
resolved by rerunning the GUI classes with localhost permission; no new failures.

Next **E4-OTHER-1**. Five scientific phases remain (OTHER, INTERACTION, RELATION,
ROLES, INTEGRATE), then RELEASE for planned `rxlabs/echoai-4`; not published.
Hardware later; METAVERSE-1 last. Legacy Discord remains out of scope.
[Results and limits](ECHO4-MAINTAIN1-FINAL-RESULTS.md),
[frozen contract](ECHO4-MAINTAIN1-BCD-DESIGN.md).

**Historical ECHO-4 MAINT-A increment — 2026-09-22:** costed service fixture and native
SelfAgent wiring implemented without changing the original loop/policy/gate.
Repairable and nonrepairable faults, finite spares, persistent external heat,
useful work and operator stop; no reset, respawn or hidden-truth policy input.
216 scripted episodes plus four witnesses, 1,090 native ticks; all invariants
hold. Blind service: 18 repairs, 45 work, six deaths versus control 120 work,
zero deaths. Original Q baseline dies after four ticks, with no work/repair.
These are mechanism results, not autonomous maintenance or behavioral gain.
235 tests pass (43 new); fresh-process reconstruction valid, no findings,
87-source lock (`ec4a6d1e…`), all 82 prior sources intact.
**`maintain1_green=false`; next MAINT-B**, evidence-based intervention choice.
Six scientific phases remain including MAINTAIN, then RELEASE. Planned HF
target `rxlabs/echoai-4`: installable agent and demonstration, not fused/new
Qwen weights. No repo creation/upload; permissions/licenses/install still
require validation. No Discord, hardware, web, commit or push changes.
[Results](ECHO4-MAINTAIN1-A-RESULTS.md), [contract](ECHO4-MAINTAIN1-A-DESIGN.md),
[release plan](../echo4/README.md).

**ECHO-4 DREAM-D v3 closure — 2026-09-22:** E4-DREAM-1 is green within its
restored WORLD-1 diagnostic-exploration profile. Two additional probes and
evidence-conditioned safe branches preserve original SELF/physics/gate and
the 12-step cap. Fifteen real fixed-weight Qwen calls, 60 valid proposals.
New exams: DREAM 300/298/302 of 320; fixed 190/230/220; random 238/246/237.
All per-cycle +32/+16 margins pass. Zero wrong diagnoses/terminalities in all
ten arms, invariants intact and exact replay parity for all nine v3 arms.
One initial promotion, two retentions; no-Qwen and no-feedback tie DREAM.
No exclusive model or feedback benefit demonstrated. Full fresh-process
reconstruction is valid without findings; receipt grants `dream1_green=true`
(`965ce6cb…`). All 82 sealed sources and bound v1/v2 artifacts remain intact;
both old red results are preserved. 926 tests: 925 pass, one historical
expected failure. Owned model server closed; no basal LLM or weight updates.
No consciousness, self-repair, general improvement or product integration
claim. Next: MAINTAIN, not started; ECHO-4 as a whole remains open.
No Discord, hardware, web deployment, commit, push or HF publication.
[Results](ECHO4-DREAM1-D-V3-RESULTS.md), [contract](ECHO4-DREAM1-D-V3-DESIGN.md),
[roadmap](ROADMAP.md).

**ECHO-4 DREAM-D v2 — 2026-09-22:** replay feedback, worst-batch selection
and promotion against both incumbent and original fixed control implemented.
Nine real Qwen calls, 36 valid proposals; three stratified cycles of 320 cases
per arm. DREAM 245/245/240, fixed 180/210/200, random 206/230/238. Fixed-margin
checks pass throughout; random +16 fails in cycles 2/3 (+15/+2).
**V2 remains red, `dream1_green=false`.** No-Qwen matches DREAM exactly;
no exclusive LLM benefit demonstrated. All nine arms preserve invariants,
with zero wrong diagnoses/terminalities and exact online/replay parity.
Full reconstruction is valid without findings (`f5d36371…`); all 76 frozen
sources and every bound v1 artifact remain unchanged after documentation edits.
891 tests: 890 pass, one historical expected failure. V1 evidence untouched.
Post-hoc cycle-2 catalog enumeration gives maximum and oracle union245,
below required246. Next v3 PLAN: more informative probes, then fresh
preregistration/exam, not threshold/seed changes to turn v2 green.
No basal LLM, weight modification, Discord use, hardware, web, commit or push.
[Results](ECHO4-DREAM1-D-V2-RESULTS.md), [contract](ECHO4-DREAM1-D-V2-DESIGN.md),
[roadmap](ROADMAP.md).

**ECHO-4 DREAM-B/C/D implementation — 2026-09-22:** fixed-weight local Qwen
ran six real calls, producing 24 valid bounded declarative candidates.
Three complete cycles include historical replay, incumbent selection,
new WORLD-1 trials, versioning/rollback and history expansion after evaluation.
DREAM scores 40/40/50 out of 80 per cycle; fixed 40/40/70, random 41/42/72,
no-Qwen 40/50/75. Zero wrong diagnoses/terminalities across all seven arms,
invariants intact and exact online/replay parity. Full reconstruction valid
without findings (`5feb033f…`), but **DREAM-D v1 is red: `dream1_green=false`**.
The first historical selection improves 60→80/80 with fewer steps, but that
does not meet the preregistered new-case advantage. Implementation is complete;
scientific closure remains pending. Next: DREAM-D v2 development and a fresh
preregistered exam, preserving v1.
871 distinct tests: 870 pass and one historical expected failure; eight
sandbox GUI socket errors resolved by an authorized rerun without code changes.
All 72 sealed sources and the CONT-D binding remain intact after doc updates.
No basal LLM, weight changes, Discord use, hardware, web publication, commit
or push. MAINTAIN remains pending;
METAVERSE-1 stays last. [Results](ECHO4-DREAM1-BCD-RESULTS.md),
[contract](ECHO4-DREAM1-BCD-DESIGN.md), [roadmap](ROADMAP.md).

**ECHO-4 DREAM-A increment — 2026-09-22:** private native-attempt archives and
budgeted partial replay implemented. Three WORLD-1 trees contain 31 nodes and
28 executed attempts; 62 replay queries return 28 observations, 32 unknowns
and two terminal responses. Replay does not execute the world or call an LLM.
Full checkpoint/archive/report reconstruction is valid without findings
(`011cc0d9…`); all 66 sources and the existing CONT-D artifact binding remain
intact. 31 new tests plus 717 regressions: 748 distinct tests, 747 pass and
one historical expected failure. Eight sandbox socket errors resolved after
an authorized rerun of the 29 GUI tests, without code changes. Ruff passes.
This is infrastructure evidence, not better exploration or a DREAM-1 closure.
Qwen, strategy generation/selection and new-task improvement remain pending.
README now specifies subjective-consciousness limits, MAINTAIN repair goals,
and runtime packaging of the fast/slow agent rather than fusion into weights.
New RELEASE-1 PLAN follows INTEGRATE: package, runtime verification, license/
privacy review, then authorized Hugging Face publication and clean install.
Stable software release precedes future lab hardware; METAVERSE-1 stays last.
No upload, model activation, commit or push. [Results](ECHO4-DREAM1-A-RESULTS.md),
[product README](../echo4/README.md), [roadmap](ROADMAP.md).

**ECHO-4 CONT-D closure — 2026-09-22:** E4-CONTINUITY-1 is green within its
declared synchronous WORLD-1 software profile. New A/B/C exams each pass
23/23 scenarios: 300/300 subsequent events and 186/186 native turns match
fresh-process continuations; 30/30 mutants rejected. The 62-source lock is
written before B. Full reconstructive verification and independent replays
of CONT-A/B/C are valid with no findings. Only the audit receipt grants
`continuity1_green=true` (`69d57a0b…`); the campaign grants eligibility only.
33 new tests plus 872 regressions: 905 run, 904 pass, one historical expected
failure. Real-artifact checkpoint/journal corruption injected in memory is
rejected without changing originals. History loss changes PATTERN learning
counts but not actions/predictions here; Q remainders additionally have a
separate synthetic arithmetic witness, not a claimed WORLD-1 behavioral gain.
Existing SELF and CONT-A/B/C sources/artifacts remain intact. No subjective
identity, autonomous repair, distributed exclusivity or hardware claim.
Next: DREAM-A contract/history; DREAM-1 remains PLAN, cortex OFF. MAINTAIN
remains pending in the basal branch. Hardware later, METAVERSE-1 last.
No commit/push/web deployment. [Closure and limits](ECHO4-CONTINUITY1-D-RESULTS.md),
[roadmap](ROADMAP.md).

**ECHO-4 CONT-C update — 2026-09-22:** explicit virtual lineage distinguishes
resume, replacement body, descendant and fork. New bodies inherit learned
memory but revoke body-bound diagnostics/permissions, require quarantine and
new supervised calibration/confirmation. Terminal individuals cannot rebody.
30 new tests pass; 805 general regressions and 37 CONT-B tests complete, with
one historical expected failure and no unexpected failures. A/B audits remain
valid; all sealed SELF/A/B sources retain their hashes. CONT-C completes its
virtual profile: 21/21 cases, 125/125 subsequent events and 43/43 native turns
match in fresh processes. Full reconstructive verification is valid, with no
findings; a corrupted checkpoint is rejected. Full CONTINUITY remains open;
next CONT-D final exam. `continuity1_green=false`.
No LLM, second bus, subjective identity claim or distributed exclusivity.
DREAM remains PLAN; hardware after software, METAVERSE-1 last. No commit/push/web.
[CONT-C evidence](ECHO4-CONTINUITY1-C-RESULTS.md), [roadmap](ROADMAP.md).

**ECHO-4 CONT-B update — 2026-09-22:** SELF diagnostic sessions and active
recovery/reuse now checkpoint at complete operation boundaries, including
pending plans, the receipt inbox, confirmation and original learning hooks.
37 new tests pass. All 18 development cases resume identically in fresh
processes: 142/142 subsequent events and 67/67 physical turns match, including
full state hashes. Independent reconstructive verification is valid with no
findings; a tampered report is rejected. CONT-A verification also remains
valid. Broad regressions: 805 tests, 804 pass and one historical expected
failure. Together with the 37 new tests: 842, no unexpected failures.
Global and life-local clocks remain distinct; vetoed, stopped and terminal
runs do not restart.
All 50 sealed SELF final sources and 37 CONT-A sources retain their hashes.
**Full CONTINUITY remains open:** CONT-C lineage and CONT-D final exam remain.
`continuity1_green=false`. Next: CONT-C. DREAM remains PLAN, cortex OFF,
hardware after software and METAVERSE-1 last. No commit/push/deployment.
[CONT-B evidence](ECHO4-CONTINUITY1-B-RESULTS.md), [roadmap](ROADMAP.md).

**ECHO-4 update — 2026-09-22:** CONT-A implements nominal SelfAgent/WORLD-1
checkpoint/resume at complete turn boundaries, with a closed JSON schema,
external custody digest, source fingerprints and shared original CAM/T/Q.
29 new tests pass. Five development scenarios resume in fresh processes;
52/52 subsequent steps and all state hashes match. Terminal state does not
resurrect. Broad regression run: 805 tests, 804 pass and one historical
expected failure after the 29 GUI tests passed on an authorized retry
(eight localhost socket errors in the sandbox). Fresh verification is valid
with no findings. All 50 sealed SELF-1
final sources retain their hashes. **Full CONTINUITY remains open:** active
recovery, body/individual lineage and the final exam are not implemented.
`continuity1_green=false`. Next: CONT-B. E4-DREAM-1 is now an official PLAN
branch after CONTINUITY, inspired by Dream-RSI: fixed-weight local Qwen proposes
bounded offline exploration strategies, with fixed evaluation and new holdouts.
No model calls/training or kernel changes here; baseline cortex stays OFF.
Hardware follows software; METAVERSE-1 remains last. No commit/push/deployment.
[CONT-A evidence](ECHO4-CONTINUITY1-A-RESULTS.md),
[DREAM plan](ECHO4-DREAM1-PLAN.md), [roadmap](ROADMAP.md).

**ECHO-4 final closure — 2026-09-22:** E4-SELF-1 is green within the declared
software WORLD-1 domain. `SelfSession` challenges the first consensus with
remaining safe probes before authorizing recovery or learning. New A/B/C
exams, source lock before B, 80/80 correct diagnoses per stage. Reuse scores
B 189/240 vs 152/240 unprotected; C 193/240 vs 143/240. It also beats
freeze-all and no-T, with zero paired losses. B/C each complete all 40 viable
24-step lives and stop in 40 infeasible ones, with no selective death in scope.
A completes 40/44 viable lives; four conservative stops remain visible.
48/48 abstention cases per stage, plus native veto and insufficiency/alias
witnesses. **Limits:** 3/4/4 terminalities in intentionally out-of-prior
mechanisms; rejection after the trace is not general preventive safety.
Trusted restoration is not self-repair; mixed-cause failures remain published.
27 new tests plus 302 selected regressions pass. Full fresh-process replay
of A/B/C and all six ancestors is valid with no findings (`98ffc1ca…`).
The audit receipt grants `self1_green=true`; the campaign report only grants
eligibility. Historical red SELF-C v1 and all sealed sources are preserved.
Next: **E4-CONTINUITY-1**, not implemented here. Hardware follows software;
METAVERSE-1 stays last. No commit, push or web deployment.
[Final contract](ECHO4-SELF1-FINAL-DESIGN.md), [closure and limits](ECHO4-SELF1-FINAL-RESULTS.md),
[roadmap](ROADMAP.md).

**ECHO-4 update — 2026-09-22:** SELF-C v2 is green for controlled memory reuse,
not full E4-SELF-1. Native one-step trials teach the same T, selectively retain
body-affected evidence during matched exposure, then select an action by
matching learned T predictions to a requested WSP. Development scores 114/144
versus 99/144 unprotected; confirmation scores 108/144 versus 90/144. It also
beats freeze-all (76/144, 56/144) and the no-T decision ablation (60/144, 48/144),
with zero paired losses. All 13 prospective criteria pass in both stages.
Held updates preserve T/PATTERN in 540/540 and 648/648 instances; legitimate
external learning remains enabled. Q stays unchanged; zero terminalities,
false facts, destroyed slots or cortex calls. **Trusted executor restoration
is required; this is not autonomous repair.** Mixed-cause success is only
42/72 and 36/72, tied with unprotected learning; every failure is published.
30 new tests plus 272 selected regressions pass. Fresh-process full replay
is valid with no findings (`74bbdfdd…`). Previous audits remain valid,
including the preserved red SELF-C v1. `self_c_v2_green=true`, `self1_green=false`.
Next: final joint SELF-1 contract and new B/C exams, including unsupported
mechanisms/unknowns, contradictions and vetoes. No CONTINUITY yet. Hardware
follows software; METAVERSE-1 stays last. No commit, push or deployment here.
[Design](ECHO4-SELF1-C-V2-DESIGN.md), [results](ECHO4-SELF1-C-V2-RESULTS.md),
[roadmap](ROADMAP.md).

**ECHO-4 update — 2026-09-21:** SELF-C v1 is implemented, but its behavioral-gain
criterion is red. Actual Agent turns use diagnosis-conditioned proposals and
the existing T-learning hook, shared with SENSATION/PATTERN. All 119 held
body-effect updates preserve the learned models; 4,801 legitimate updates
pass, including 171 external ones. On 240 conditions, selective recovery and
the no-attribution control both complete all 126 feasible 24-step lives.
The selective agent stops in the 114 infeasible cases instead of dying;
this is a safety benefit, not the required strict gain in task completion.
36 new tests plus 236 selected regressions pass; previous certificates remain
valid. Fresh-process full SELF-C replay is valid with no findings (`15d8bfba…`),
including the red outcome. `development_checks_passed=false`,
`self1_green=false`; v1 is preserved without changing its threshold.
Next: SELF-C v2, a prospective task measuring downstream utility of retained T,
then new B/C closure exams. No CONTINUITY yet; hardware later, METAVERSE-1 last.
[Design](ECHO4-SELF1-C-DESIGN.md), [results](ECHO4-SELF1-C-RESULTS.md).

**ECHO-4 update — 2026-09-21:** SELF-B implements model-conditional attribution
and discriminating probes. Active selection scores 7,920/7,920 on the public
development census, with zero wrong attributions and terminalities. Fixed
order ties accuracy but requires 133,320 diagnostic actions versus 66,660;
removing the long nominal reference leaves 1,632 unknowns. This relies on
known nominal physics, a declared perturbation family and trusted restoration,
not general causal identification or autonomous discovery of physical laws.
28 new tests and 236 selected tests pass; fresh-process full replay valid
with no findings (`06fae2d4…`). SELF-A/BOUNDARY/SENSATION reverified unchanged.
**self1_green=false. Next: SELF-C**, selective knowledge protection and
behavioral recovery, then new B/C closure exams. Read-only preservation of
the nominal reference does not establish selective protection during learning.
Hardware follows software; METAVERSE-1 stays last.
[Design](ECHO4-SELF1-B-DESIGN.md), [results](ECHO4-SELF1-B-RESULTS.md),
[roadmap](ROADMAP.md).

**ECHO-4 update — 2026-09-21:** E4-SELF-1 has started; SELF-A implements a
bounded change monitor sharing BOUNDARY/CAM, not positive causal attribution.
The 7,920-condition census finds 119 ambiguous public-evidence classes even
with both action/wait probes: 3,256 conditions have incompatible latent causes.
All 15,840 observed-change comparisons check out, with nominal reference/CAM
preserved in 396/396 instances. 29 new tests and 208 selected tests pass;
fresh-process replay valid (`eeb52994…`). Previous SENSATION/BOUNDARY certificates
remain valid. **self1_green=false**: discriminating interventions, self/world
attribution, selective model protection and behavioral recovery remain pending.
No consciousness claim; hardware follows software and METAVERSE-1 stays last.
[Design](ECHO4-SELF1-DESIGN.md), [first deliverable](ECHO4-SELF1-A-RESULTS.md).

**ECHO-4 update — 2026-09-21:** BOUNDARY-1 is green for observable causal
influence under matched, restored virtual interventions. B/C each score
1,408/1,408 versus 778/765 for temporal coincidence; zero false influence,
512/512 correct invalid-trial abstentions per stage. Frozen CAM/T/PATTERN/map,
34 new tests and 179 selected tests pass. Fresh-process full replay is valid
with no findings, certificate `48789bd5…`; SENSATION certificate reverified.
This relies on trusted experimental restoration, not WSP equality alone.
No body-ownership, autonomous experiment, recovery or consciousness claim.
The next milestone at that checkpoint, **E4-SELF-1**, is now in development above.
Physical validation follows software; METAVERSE-1 remains last.
[Results](ECHO4-BOUNDARY1-RESULTS.md), [contract](ECHO4-BOUNDARY1-DESIGN.md).

**ECHO-4 update — 2026-09-21:** SENSATION-1 is green for nominal WORLD-1
next-WSP prediction. Two-step history scores 22,052/25,781 in B versus
21,834 for T, and 22,418/26,030 in C versus 22,215. Gains exceed the
prospective 0.5 percentage-point threshold in both stages, with zero paired
losses. Frozen model, bounded memory, shared native CAM/T integration,
145 passing tests, fresh-process audit valid with no findings. Certificate
`96f2deae…`. No claim of survival, causal attribution or consciousness.
The next milestone at that checkpoint, BOUNDARY-1, is now closed above.
ECHO-4 as a whole remains open;
physical validation follows software and METAVERSE-1 remains last.
[Closure](ECHO4-SENSATION1-CLOSURE.md), [contract](ECHO4-SENSATION1-PREDICTOR-V1.md),
[programme](ECHO4-EGO-PROGRAMA.md).

**Active software direction — 2026-09-21:** ECHO-4 targets echoAI's functional
self (ego): self/world attribution, continuity and regulation of its own
needs. WORLD-1 is implemented as a feasibility foundation, not an ego or
learned-maintenance result. 45 new tests and 48 selected regressions pass;
the untrained single-life agent dies after 37 actions. Hardware comes after
software; neither hardware nor METAVERSE-1 gates this program. ECHO-3's
physical acceptance remains unchanged. [Program](ECHO4-EGO-PROGRAMA.md),
[results](ECHO4-WORLD1-RESULTS.md), [roadmap](ROADMAP.md).

**Current checkpoint — 2026-09-20:** ECHO-1 and ECHO-2 are closed. ECHO-3
has fourteen software milestones with green certificates: SIM-3, FLIGHT-1S v6, SENSOR-1S v3,
GROUND-1 v2, DYNAMIC-1 v2, PATTERN-1R v4, FUSION-1, COMPOSE-1 v4, CAUSE-1, PX4-1, POWER-1, SAFE-1 v2, HOST-1 and TRANSFER-3. One milestone remains. DYNAMIC-1 v2 completed
29 flights with valid evidence, 250 audit checks, no findings, seven caught
mutants and seven rejected report mutations ([results](DYNAMIC1-V2-RESULTS.md)).
PATTERN-1R v4 completed 28 flights, 242 valid audit checks, no findings, six
caught mutants and seven rejected report mutations. Bank identity: 4,591/4,866
correct, 45 confused, 230 unknown. Anonymous LiDAR families for two walls;
learning/exam run by replay, not autonomous echoAI flight. V1/v2/v3 reds are
preserved ([results](PATTERN1R-V4-RESULTS.md)). FUSION-1 passed 864 functional
episodes and 240 reduced replay windows from twelve existing flights, with
valid audit, 15 tests, eight mutants and seven report mutations
([results](FUSION1-RESULTS.md)). **COMPOSE-1 v4 has a green certificate:**
`b5974a9e…`, valid evidence, no findings. 6,144 functional missions confirm
movement savings against horizon one in both B and C. 32 new Gazebo/PX4
flights: full agent reaches 6/6 feasible goals versus Q's 0/6 and correctly
abandons both low-energy missions. Zero observed execution violations.
The full and conventional planners tie at 70 physical movements; horizon one
uses 78. The full agent's WSP drives PX4 using public sensor evidence.
V4 reuses unchanged v3 code with prospectively larger fresh functional
samples; v1/v2/v3 remain red. Scope is planar navigation in extruded rooms,
fixed altitude, abstract energy, no hardware or sealed TRANSFER-3 exam.
The second audit in a fresh process reproduces the certificate; chain and
audit both exit 0.
([results and reproduction](COMPOSE1-V4-RESULTS.md)). **CAUSE-1 is green in SITL:**
16 development flights and 32 reserved flights; B and C each score 16/16 versus
8/16 for temporal coincidence, with zero false self-attributions. Valid evidence,
60 tests, four mutants, seven trace mutations and seven report mutations rejected.
Fresh-process audit reproduces certificate `a469abab…`, exit 0. Scope: normal
motion relative to a planar wall, experimental intentions, nominal skill prediction,
no unmeasured external body forces or CAM/T/Q writes ([results](CAUSE1-RESULTS.md)).
**PX4-1 is green in SITL:** development 4/4, B 4/4 and C 4/4 flights;
48/48 invalid requests blocked in B/C, eight confirmed goals, four autonomous
PX4 failsafe landings without external NAV_LAND. Maximum physical arrival
error B/C: 172/354 mm. 48 closure tests; wider regression 521 tests with one
expected failure. Six source mutants, four trace mutations and one report
mutation detected. Fresh-process audit reproduces `342ca3aa…`, exit 0.
Scope: bounded north/south one-metre goals, fixed altitude, one transaction
per supervised session; no integrated navigation or hardware ([results](PX41-RESULTS.md)).
**POWER-1 is functionally green:** in each of B/C, 320/320 full-policy episodes
finish at home with reserve, completing 128/128 feasible goals versus 64/128
for the fixed-percentage control, matching the oracle in the declared domain.
2,160 total episodes, 78 tests, six mutants, four episode mutations and three
report mutations detected; fresh-process audit reproduces `6a05ad4c…`, exit 0.
Scope is simulated energy units, not measured joules or new flights. Replay
of twelve PX4-1 flights correctly abstains on 2,197 unusable battery samples.
Instrumented battery and continuous-flight integration remain outstanding
([results](POWER1-RESULTS.md)).
**SAFE-1 v2 is green in SITL:** B/C each pass 6/6 flights and 512/512 functional
episodes. Ten fault flights land through PX4's native failsafe, without new
goals or external NAV_LAND. Maximum veto delay 288 ms; disarm within 27,723 ms
of veto. 108 tests, six mutants, four corruptions and three report mutations
detected. Fresh-process audit reproduces `eecb77b8…`, exit 0. V1 remains red
due to an auditor false positive on a normal rejected arming retry; its C stayed
sealed. V2 corrects only that audit and uses fresh B/C seeds with unchanged
runtime. Scope: faults before a bounded goal from hover, simulated energy,
not general safety or hardware ([results](SAFE1-V2-RESULTS.md)).
**HOST-1 is functionally green:** B/C each score 1,536/1,536 useful source
choices versus 768/1,536 for button reward. Each passes 1,024 authority-loss
and 1,024 recovery checks, plus 14 communication/arbitration cases. 127 tests,
six mutants, five episode corruptions and three report mutations detected;
fresh-process audit reproduces `18d4a4fa…`, exit 0. Scope: supervised calibration
and read-only choices evaluated on prerecorded machine kinematics, not new
flown goals or general human trust. Separate replay of three existing flights
confirms/contradicts source hypotheses without duplicating evidence; n=3 stays
below the trust threshold ([results](HOST1-RESULTS.md)).
**TRANSFER-3 is green in software:** the independent C1 v2 sealed campaign
passed B (38/0 blocks) and C (48/1), with zero calibration-attributable losses,
and both exams reproduced with identical hashes. Certificate `8c77aead…` has
`transfer3_green=true`. Scope: static two-wall simulation, noiseless sensors,
no hardware, HIL, real flight or DRONE-3 ([results](TRANSFER3-PLAN-C1-RESULTS.md)).
**DRONE-3 closed its SITL leg on 2026-09-20, and only that leg.** One
continuous PX4 v1.15.4 + Gazebo session per flight runs the whole blocked-station
mission: perception, evidence with the transferred C1 calibration, composition,
the epistemic gate, POWER's energy gate, the SAFE supervisor, a bounded cell
gateway and PX4 keeping its failsafes. B and C each score 12/12 in fresh rooms
whose geometries were never flown before: 6/6 feasible missions reached, 3/3
correct low-reserve aborts, 3/3 contained faults landed by PX4's own data-link
failsafe, zero collisions (minimum clearance 1,247 mm), zero hard-constraint
violations and 228/228 in-flight refusal probes blocked per stage. Eleven
mutants detected, eight trace manipulations rejected by the audit. Certificate
`c44402df…` carries `drone3_sitl_green=true`; a fresh-process audit reproduces
it. **`drone3_hil_green`, `drone3_cage_green` and `drone3_green` stay false:
there is no flight controller, drone, real sensor or cage in the laboratory**
([results](DRONE3-RESULTS.md), [handoff](DRONE3-HARDWARE-GUIDE.md)).
Hardware HIL/cage validation remains outstanding, so ECHO-3 stays at 14/15. See the [versioned status review](ECHO3-STATUS-20260917.md)
and [roadmap](ROADMAP.md). The sections below preserve the historical results;
their old “next” instructions do not override this checkpoint.

Reproduce with, from `/home/roger/REALRXOS/RXos`:

```
PYTHONPATH=. python3 -m echoai.tests.test_nexus0
PYTHONPATH=. python3 -m echoai.nexus0.bench
PYTHONPATH=. python3 -m echoai.nexus0.bench --plan-depth 2
```

| Rung | State | The number that closes it |
|---|---|---|
| **NEXUS-0** — memory, policy, learning, gate | **closed** | `policy_after` = [-12, +5, 0]: approach on the threat row is negative and loses to avoid. `false_facts` = 0, `destroyed` = 0, `cortex_calls` = 0, `encoder_beats_fnv` True (vendor bank 6/6 rel vs FNV 0/6). |
| **NEXUS-1** — a world model that is not the env's formula | **closed** | `t_beats_ring` True: with two JUMP cells at +2, T scores 0.9964 against the (i±1) arithmetic baseline's 0.9715, same 281 scored turns. |
| **NEXUS-2** — planner, as a module | **closed** | Distance 2: `T(13,approach)=14`, `T(14,approach)=15`, `Q[15,approach]=80` → `plan.scores(13, depth=2)` = [70, 0, 0] → approach, while depth 1 scores [0, 0, 0] → wait. Does not mutate Q or T. Opt-in; default `plan_depth=0`. |
| **NEXUS-2 — in the 320-turn ring** | **refuted** | plan-2 waits 58 % of turns, because `T(s,wait) = s` makes wait's lookahead the max of its own row. Discounting that self-loop (scratch, not applied) makes plan-2 *identical* to `Q.best`: 73/24/2, `policy_after` [-12, +5, 0], `jump_hits` 10. In 32 cells TD already fills the neighbouring rows, so two-step lookahead adds nothing. |

| **NEXUS-3** — asking is a skill, not a gesture | **closed** | `novel_approach_return` = **+80 asking, −80 blind** over the same 320 turns and seed. Approach on the NOVEL cell pays −16 while the hidden bit is set and +16 once the oracle has cleared it, so one question is worth a 160-point swing. |
| **NEXUS-4i** — topology transfer (corridor) | **closed** | Same agent, not the 32-cell ring. HOME A→B→C→D, SHIFT A→B→X→D. On entry: transferred T(B,approach)=C conf 3, unseen {A,B,D}=0; control knows nothing, unseen=3. First visits in the window: 1 vs 4. KPI 4 not as predicted (approach at B still wins; agent learns “enter X, then avoid”). This is not AGI. |

Not published as improvements: plan-2's `action_success` (0.0969 vs the
default 0.2938 — a waiting agent does not reach a GOAL), its
`prediction_accuracy` of 1.0 (self-loops are trivially predictable), and
its `policy_after[0]` of -7 vs -12 (less approach at the threat means
less punishment, not better policy). Nor NEXUS-3's `novel_visits`: the
blind agent stands on the NOVEL cell 66 times to the seer's 5, and that
is paralysis, not curiosity — it learned wait, and wait does not move.

## NEXUS-3 — the ladder gate

An epistemic act, not a fourth move. `env.hidden_bit` is a fact about the
NOVEL cell that observation cannot reach. *(Superseded by NEXUS-4h: this
rung originally read `env.ask()`, which returned the extract and cleared
the bit in one call. There is no `env.ask()` any more — an oracle outside
the world replies, `oracle.accept` verifies, and only then does
`env.reveal(NOVEL_CLEAR)` clear the bit.)* The agent emits
`YO → PREGUNTAR → DESCONOCIDO @AHORA` on the same 16 B cable, at most
once per cell, **before** the gate, and it does not move `i`. That order
is the point: the turn that asks is already the turn that gets paid.

```
python3 -m echoai.nexus0.bench            # lab/nexus0_report.json
python3 -m echoai.nexus0.bench --no-ask   # lab/nexus0_noask_report.json
```

320 turns, same seed, the only difference is whether asking is allowed:

| | asking | blind |
|---|---|---|
| `novel_approach_return` | **+80** | **−80** |
| `questions` | 1 | 0 |
| `Q` on the NOVEL cell | [+10, 0, 0] → greedy **approach** | [-12, 0, 0] → greedy **wait** |
| `action_success` | 0.3094 | 0.2094 |
| `policy_after` (threat row) | [-12, +5, 0] | [-12, +5, 0] |
| `phase_e_action` | 1 avoid | 1 avoid |
| `false_facts` / `destroyed` / `cortex_calls` | 0/0/0 | 0/0/0 |

Oracle beats blind: `novel_approach_return` +80 > −80. The two agents
learn opposite policies about the same cell — one walks into it on
purpose, the other treats it as a threat — and the only difference
between them is a single question. `ask` stays on by default; the threat
at cell 7 is untouched by the bait, and `policy_after` is identical in
both arms.

### Value, not map: the seeking probe

Does the trained agent *go* to the NOVEL cell, or just get paid when it
trips over it? Probe: after training, `teleport(0)` and walk 32 greedy
steps (`novel_hits_greedy`, `PROBE_STEPS`).

**`novel_hits_greedy` = 0 asking, 0 blind.** Also 0 at 64 steps. The
listed bar was not lowered and no bonus for visiting cell 11 was added.

The reason is not reluctance — the walk never starts. `Q[c0]` is
[0, 0, 0], `best()` breaks a full tie to wait, and wait does not move, so
a greedy agent from cell 0 sits there forever. In 256 turns TD carried
value exactly **one cell** back from each rewarded cell:

| cell | 0 | 1 | 2 | 3 GOAL | … | 10 | 11 NOVEL |
|---|---|---|---|---|---|---|---|
| asking | [0,0,0] wait | [0,0,0] wait | [3,0,0] appr | [11,0,0] appr | | **[2,0,0] appr** | [10,0,0] appr |
| blind | [0,0,0] wait | [0,0,0] wait | [3,0,0] appr | [11,0,0] appr | | **[0,0,0] wait** | [-12,0,0] wait |

So the honest close: **asking changed the value of the cell, not the map
to it.** The one place the difference does show as movement is one cell
wide — from c10, the seer's approach is +2 and it walks in; the blind
agent's row is flat and it waits. That is a neighbour, not a search.

### NEXUS-4a ATTEND + stub

LLM still off. `cortex_calls` default **0**; with the flag, the switch
wakes on miss / no-extract / novel / low-C only. Firewall: the stub
cannot VERIFY — `cortex.py` has no CAM handle, no `allocate`, no
`has_fact`, and a test greps for all three.

```
python3 -m echoai.nexus0.bench            # cortex off, cortex_calls 0
python3 -m echoai.nexus0.bench --cortex   # lab/nexus0_cortex_report.json
```

`attend(slot_hit, extract_ok, E, kind_novel, ham) -> (bool, reason)` is
an integer predicate: MISS (1), NO_EXTRACT (2), NOVEL (4), LOW_C (3).
The conditions are an OR, so check order changes only the label; LOW_C
is checked last because it would otherwise mask everything (below).
`cortex.propose(wsp, reason)` returns 16 B: on NOVEL it proposes the
same PREGUNTAR packet the fast loop already knows, and the loop routes
it through `_ask()` so there is exactly one path to the oracle. On any
other reason it hands the observation back unchanged. It has no
hypothesis of its own; that is the next rung, not this one.

On the NOVEL cell the switch fires with reason `novel`, the stub
proposes asking, `questions` = 1 and `false_facts` = 0.

**ATTEND uses Q preference + T known, not `default_e()`'s C.**
`cortex_calls` with `--cortex`: **36 / 256** (was 187). Default still 0.

The first cut read `E[C]`, and `default_e()` carries C = 15 — below
`C_PLASTIC` on every EMPTY and GOAL cell — so the switch woke on 73 % of
turns and was a router with extra steps. `C_PLASTIC` was not lowered and
`default_e()` was not touched; ATTEND stopped believing the poster:

- `q_confident`: the Q row is not a full tie — there is a preference.
- `t_known`: T has seen the action that preference names. wait mapping
  to itself counts, and should: a known standstill is a turn the fast
  path handles alone.
- settled gate (`ATTEND_SETTLED_HITS` = 2, in the loop): a slot seen
  twice that *still* has a flat row is a boring cell, not an open
  question. Most of this ring pays nothing and stays flat forever.

That last gate is what actually bites. Without it the count sits at 112,
because "no preference" and "no map for the wait that no preference
implies" are the same fact counted twice — relabelling moved wakes from
`low_C` to `no_map` and changed no totals. Measured before choosing:
settle at 2 → 36 wakes, at 3 → 61, at 4 → 86, at 8 → 112.

Reason histogram over 256 turns, `--cortex`:

| off | low_C | novel | no_map | miss |
|---|---|---|---|---|
| 220 | 30 | 4 | 2 | 0 |

`off` is now the champion, `novel` still wakes on all 4 visits to cell
11, and the poster alone no longer wakes anything —
`test_attend_poster_C_does_not_wake` pins that.

With `--cortex` the locks hold: `policy_after` [-12, +5, 0],
`novel_approach_return` +80, `false_facts` 0, `destroyed` 0.

### NEXUS-4b hook

JSONL contract, `parse_reply` rejects prose. No LLM in-process.
`cortex_calls` 36/256 (40 over the full 352-turn report, which includes
phase G and the seeking probe).

`python3 -m echoai.nexus0.bench --cortex` writes one line per wake to
`lab/cortex.jsonl`; the default bench creates no file at all.
`NAVI_CORTEX_LOG` overrides the path. A woken turn is exactly:

```json
{"turn": 10, "reason": 4, "reason_name": "novel",
 "wsp_in": "YO → DESCONOCIDO → UNK @AHORA | E[V+0 A+20 D+0 C+40 U+10 B+0]",
 "wsp_in_hex": "021f2908001400280a0000000500000b",
 "slot": 3901, "ham": 0, "q_row": [0, 0, 0], "t_pred": null,
 "extract": "cell=11 kind=NOVEL",
 "wsp_out": "YO → PREGUNTAR → DESCONOCIDO @AHORA | E[V+0 A+40 D+0 C+10 U+60 B+0]",
 "wsp_out_hex": "020f1f080028000a3c00000005000000"}
```

There is no free-text field, and a test asserts the key set exactly.

`cortex.parse_reply(text)` accepts **only** 32 hex characters or a
compact line of known atoms (`YO → TEMER → PELIGRO @AHORA`, optional
`| E[...]` tail). A sentence, a JSON answer, a VERIFY claim, an unknown
atom name, a 33-character hex string — all return None, and the loop
keeps the observation. Refusals count in `cortex_rejected`.

`cortex.complete(turn)` runs the argv in `NAVI_CORTEX_CMD` as a local
subprocess, JSON in on stdin, text out on stdout, 10 s timeout, no
shell. Unset — the default — it returns None and the stub answers. No
HTTP client exists in this tree.

Reasons in the 40 logged wakes: low_C 32, novel 5, no_map 3. The novel
lines are the ones where the stub actually proposes something: the
PREGUNTAR packet, routed through `_ask()`.

### NEXUS-4c thought log + ANSI viewer

Not a brain render. Replay of 320 turns. LLM still off.

`cortex.jsonl` only holds the ~40 woken turns, so the viewer needs the
other log: one line per turn, quiet ones included.

```
python3 -m echoai.nexus0.bench --thought              # lab/thought.jsonl
python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --fps 20
python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --follow
```

352 lines for the 352-turn report (256 training + 64 phase G + 32
probe). `NAVI_THOUGHT_LOG` overrides the path; the default bench writes
nothing, and `--cortex` does not imply `--thought` — two logs, two
flags. Fixed keys, asserted as a set: `turn, cell, kind, action, reward,
wsp, attend_on, reason_name, q_row, t_pred, questions, cortex_calls`.

`view.py` is stdlib only — no pygame, no web, no matplotlib. The ring
backdrop starts from the env's initial layout and is corrected from the
log as the agent visits cells, which is how the phase F threat move
(7 → 8) appears. A turn on the NOVEL cell:

```
  0123456789012345
  ···G···T···N···G
             @
  6789012345678901
  ···T·······G····

  approach    +4              |####         <
  avoid       +0              |
  wait        +0              |

  YO → DESCONOCIDO → UNK @AHORA | E[V+0 A+20 D+0 C+40 U+10 B+0]
  turn  10  cell 11 NOVEL   r +16  ATTEND OFF
  t_pred None  questions 1  cortex_calls 0
```

The agent sits on its own row so standing on the NOVEL cell does not
erase the `N`. Legend: `G` goal, `T` threat, `N` novel, `·` empty,
`@` agent, `<` the action taken.

Note: `bench.run()` used to write a hardcoded `"cortex_calls": 0` into
every report, which would have made this invariant unfalsifiable the
moment a cortex existed. The report now carries the real counter from
`Metrics`.

### NEXUS-3b traces

The corridor fills **3 cells back** (c8, c9, c10 all positive, where the
one-step update left c8 and c9 flat); myopic from c8 hits c11: **yes**,
`8 → 9 → 10 → 11` with no planner at all. Wall from home still holds.

Integer eligibility traces, opt-in, `Agent(trace=True)` /
`python3 -m echoai.nexus0.bench --trace` → `lab/nexus0_trace_report.json`.
`z[4096][3]` int, credited `+16` on the chosen (s,a), paid out as
`Q += (δ * z) >> 6` and decayed `z ← (7 * z) >> 3`; only the ~12 live
entries are touched per turn. `TRACE_CREDIT >> TRACE_SHIFT` equals
`1 >> ALPHA_SHIFT`, so the current step keeps α = 1/4 exactly and the
tail of the path gets the remainder. Traces are cleared at `run()`.

`Q[·][approach]` along the corridor after 256 turns, asking in both:

| | c8 | c9 | c10 | c11 |
|---|---|---|---|---|
| one-step (default) | 0 | 0 | +2 | +10 |
| traces | **+2** | **+3** | +3 | +5 |

Read-only myopic walk (depth 0, no planner) from c8:

```
seer + traces    8 → 9 → 10 → 11 → 12 …    hits 11: 1
seer, no traces  8   8    8    8    8 …    hits 11: 0
blind + traces   8   8    8    8    8 …    hits 11: 0
```

**The price, stated:** spreading δ along the path dilutes the threat.
`policy_after` goes [-12, +5, 0] → **[-1, 0, 0]**: approach still loses,
by 1 instead of by 17. In the trace side-report `phase_e_action` becomes
wait rather than avoid and `t_beats_ring` goes False. That is why traces
are opt-in and the default bench keeps the one-step update. The default
is unchanged and verified: `policy_after` [-12, +5, 0], `false_facts` 0.

From home nothing changed: cell 7 still costs −16, the seer with traces
still never reaches c11 from c0. Longer spinal cord, same wall.

### The value wall, and c11 behind it

6↔7 is a value wall: the planner from c0 never crosses cell 7. From c8
(past the wall): **1 hit vs 0**, seer vs blind, `T(8→9)` observed yes
(n=4, as are 9→10 and 10→11). Still no bonus for standing on 11.

The wall is one cell further along than it looks. c6 is [1, 0, 0], so the
agent does step *onto* the threat; what it never does is continue
through it — at c7 approach is −12 against avoid +5, so it turns back and
cycles. From home, c8 is unreachable at any depth.

Past the wall the picture inverts. Read-only walk from c8, depth 2:

```
seer   8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 …   hits 11: 1
blind  8   8    8    8    8    8    8    8    8 …   hits 11: 0
```

Same T, same corridor, both arms; the only difference is the value one
question put on the cell. So **c11 was unreachable from home, not
non-existent** — and reaching it still needs the planner: at depth 0 both
arms sit at c8, because the corridor's own rows are flat and TD only ever
carried value one cell back.

### Planner as +1 hop

From c9 the seer plans approach (T → c10, `Q[c10]` > 0); `Q.best(c9)` is
wait. Blind: both wait. Still not a map from c0.

`T(9, approach) → c10` was observed 4 times in the 256-turn run, in both
arms — nothing was fabricated for the test. The planner buys exactly its
own depth of reach and no route: from c0 the myopic policy and depth 1
both wait (c1 is flat too), depth 2 reaches c2's +3 and the agent finally
walks — 0→1→2→3→4→5→7 — then falls into a 6↔7 limit cycle at the threat.
A planner-driven greedy walk still reaches the NOVEL cell **zero** times.
Reach is not a route. `plan_depth` stays 0 in the default bench.

Still open, deliberately: `encode_ask()` emits one packet per question,
so all questions share a CAM slot — fine with one NOVEL cell, broken with
two. And nothing yet makes the agent travel to information: that needs
value propagated along the ring (more turns, eligibility traces), not a
reward for standing on cell 11. `walk_greedy()` also still learns through
`turn()`; it runs last so no lock can see it, but a probe used for more
than this should not update.

---

## NEXUS-4d — T_CONF 0–3 from n; ATTEND reads it

`world.conf(s, a) -> int`, an integer 0..3 read off the counters
`observe()` already keeps. No float, nothing new in the fast path.

```
n == 0                 → 0   never seen
n == 1                 → 1   one observation
n >= 2,  alt_n == 0    → 2   consistent
n >= 8,  alt_n == 0    → 3   very consistent
alt_n > 0              → 2 at most, whatever n is
```

The cap is the point: a row that was ever contradicted must not read
like a row nothing ever argued with, however often the winner won.
`known()` stays yes/no, `pair()` stays.

### The ring's own table, 256 turns

36 rows of T are non-empty: **32 read 2, 4 read 3**, none read 0 or 1.
The 3s are not the interesting cells — they are the two limit cycles the
agent grinds on:

| cell | action | → cell | n | alt_n | conf |
|---|---|---|---|---|---|
| 6 | approach | 7 | 12 | 0 | **3** |
| 7 | avoid | 6 | 12 | 0 | **3** |
| 18 | approach | 19 | 53 | 0 | **3** |
| 19 | avoid | 18 | 49 | 0 | **3** |
| **5** | approach | **7** (JUMP) | 4 | 0 | 2 |
| **21** | approach | **23** (JUMP) | 4 | 0 | 2 |
| 0…4, 8…17, 20, 23…31 | approach | i+1 | 4–6 | 0 | 2 |

So `conf` measures evidence, not geometry: the JUMP rows are the ones
that carry structure `i±1` does not know, and at 256 turns they have
only been walked four times each, so they read 2. Given more turns they
do climb — at 1024 turns cell 5 → 7 is n=15 → **3**, cell 21 → 23 is
n=14 → **3**. Nothing was extended in the bench to make that happen.

### The stale transition

Phase F moves the threat 7 → 8, so cell 7's kind changes, its WSP
changes, and its CAM slot changes. The row that gets contradicted is the
JUMP itself:

```
cell 5 approach   pred=slot 2905 (old cell 7)  n=4
                  alt =slot  711 (new cell 7)  alt_n=2   conf 2, not 3
```

`conflicts` goes 0 → 2. KCC keeps the winner (alt_n=2 is not > n=4), so
`predict()` is unchanged and no fact was destroyed — but the row is now
disputed and `conf` says so. That is the whole difference between "T
knows" and "T knows well", and it is the first row in this lab where the
two answers differ.

### ATTEND reads it — and stays exactly as quiet

`attend(..., t_conf: int = 0)`. `t_known` is still the bool (`conf >= 1`);
`t_conf` is the quality behind it. One guard: if the map is decent
(`>= 2`) on a turn that is hit + extract + not novel + q_confident, do
not wake for `no_map`. It can only ever silence `NO_MAP` — it cannot turn
an `off` into a wake, and every other reason keeps its wake.

**`--cortex` wakes: 36/256 — was 36/256.** Unchanged, measured on both
sides of the commit. Over the full 352-turn bench, `cortex_calls` is 40
before and 40 after. Reasons: `off` 220, `low_C` 30, `novel` 4,
`no_map` 2.

**The guard never fired, and that is reported, not hidden.** In this
wiring `t_known = settled ∨ (predict ≠ None)` on the same (slot, action)
`t_conf` is computed from, so `t_conf >= 2` implies `t_known` and the
new branch is never the deciding vote. A test counts it: 0 turns of 256
had `conf >= 2` with an unknown row. The guard becomes load-bearing when
a row can be *known and bad* — a known row whose `conf` is 1, or one in
dispute — which is the inverse model's slice, not this one. `T_CONF` is
correct and measured now; the switch is not yet paid by it.

`SETTLED_HITS` 2 and `C_PLASTIC` 20 untouched. `E` is still in the
`attend` signature and still unread. Default bench intact:
`policy_after [-12, +5, 0]`, `false_facts 0`, `destroyed 0`,
`cortex_calls 0`, `encoder_beats_fnv`, `t_beats_ring`,
`novel_approach_return +80`.

Tests 100 → 111.

---

## NEXUS-4e — I(s, s') → a on observed neighbours

`world.inverse(s, s_next) -> Optional[int]`. Per slot, a short list of
`[s_next, action, count]`, written by `observe()` before T's KCC decides
anything: what was taken to reach s' is a fact about the step, not about
which s' currently wins the row.

Same KCC discipline as T — highest count wins, a second action for one
landing does not displace the first until it strictly beats it, a tie
keeps the incumbent. One fallback, and only one: if s' is s and `wait`
has been observed from s at all, the answer is `wait`. With no evidence
the answer is **None**. A standstill is never guessed to be `approach`.

### KPI: I(s, T(s,a)) == a where conf >= 2

After 256 turns, **36 of 36 rows recover their action.** Not a subset —
every row of T with evidence.

| action | rows with conf ≥ 2 | recovered |
|---|---|---|
| approach | 31 | 31 |
| avoid | 3 | 3 |
| wait | 2 | 2 |
| **total** | **36** | **36** |

After the full bench (phase F + the 32-step probe) it is **39 of 39**.

### JUMP does not come back as wait

The row the whole thing is for: cell 5 `approach` lands on cell **7**,
skipping 6. `i+1` arithmetic would call that landing something else; the
inverse says `approach`, from evidence.

```
slot(cell 5) entries:  [(cell 7, approach, 4)]
inverse(slot 5, T.predict(slot 5, approach)) = approach
```

Same for cell 21 → 23. Both asserted, both against `wait` explicitly.

### Size: not 4096²

```
inv_size          36 entries after 256 turns, 41 after the full bench
non-empty slots   31
max per slot      3        (cap INV_MAX_ENTRIES = 8)
inv_dropped       0
4096 x 4096       16 777 216       — the table that was not built
```

Three distinct successors is the most any slot in this ring has, so 8 is
slack rather than a budget. An observation that would not fit is counted
in `inv_dropped`, not silently forgotten; a topology that needs more
shows up as a number instead of as a wrong answer.

### Phase F: the conflict is forward-only

Phase F moves the threat, cell 7's kind changes, and it gets a second
CAM slot — so cell 5's jump acquires a second landing and T's row goes
into dispute (`conflicts` 2, `alt_n` 2 against `n` 4, `conf` capped at 2,
see NEXUS-4d).

```
cell 5 approach   winner  slot 2905 (cell 7, THREAT)   n=4    inverse → approach
                  alt     slot  711 (cell 7, EMPTY)  alt_n=2  inverse → approach
```

The action was `approach` both times. **The disagreement lives in T
(which s'), not in I (which a)** — the inverse is right about both
landings and had nothing to unlearn. That is a property of this
particular change, not a general claim: nothing here says the agent
understood the new world from one observation, and the test asserts only
that the losing landing answers `a` or `None`, never a fabricated third
action.

### Untouched

`conf()`, ATTEND, `SETTLED_HITS`, `C_PLASTIC`, `parse_reply`, the viewer,
`plan.py`. Bench length still 256. Default intact: `policy_after
[-12, +5, 0]`, `false_facts 0`, `destroyed 0`, `cortex_calls 0`,
`encoder_beats_fnv`, `t_beats_ring`, `novel_approach_return +80`.
`--cortex` wakes 36/256, unchanged.

Tests 111 → 119.

---

## NEXUS-4f — Escalation 0 vs 2 via ΔQ. Default still Q.

`qtable.margin(s)` = best − runner-up, integer, 0 on a tie, never
negative. `escalate.level(margin, …)` returns a rung:

```
0  Q         the policy's argmax                      margin >  ESC_MARGIN
1  T         reserved, NOT wired — T already runs every turn in the loop,
             so a rung that only consults it would label work already done
2  SEARCH    plan.best over T, depth 2                margin <= ESC_MARGIN
3  ASK       reserved — PREGUNTAR stays Agent._ask(), the one path to the
             oracle, fired before the action is chosen. Not a fourth gear.
4  CORTEX    reserved — that decision is ATTEND's. escalate does not
             duplicate attend() and must not be read as replacing it.
```

`ESC_MARGIN = 4`, in Q units. `Agent(escalate=False)` by default;
`bench --escalate` writes `lab/nexus0_escalate_report.json`. Exploration
(full tie or ε) never reaches the planner — asserted turn by turn.

### search_differs is not 0. It is also not worth anything.

`--escalate`, 352 turns:

```
esc_margin              4
level_q                18      level_search          231
search_copies_q         48     search_differs       183
search_strictly_better   0
```

183 disagreements, **0 of them the planner scoring its own action
higher**. So `differs` alone flatters rung 2, and a third counter was
added rather than reporting two. Every disagreement is one shape:

```
q_row = (1, 0, 0)     plan.scores = (4, 0, 4)
q.best = approach     plan.best = wait
```

`plan.scores` ties approach with wait, and `plan.best`'s documented
tie-break picks wait. That is a tie-break, not a route.

### The sweep, on the default trajectory

Counterfactual — what rung 2 *would* say at each exploit turn of the
unmodified bench, computed without acting on it, so the trajectory is
identical in all three rows:

| ESC_MARGIN | level 0 | level 2 | copies | differs | strictly better |
|---|---|---|---|---|---|
| 2 | 66 | 62 | 22 | 40 | **0** |
| 4 | 59 | 69 | 29 | 40 | **0** |
| 8 | 4 | 124 | 84 | 40 | **0** |

The same 40 turns, at every threshold. Moving ESC_MARGIN buys more
searching and not one different-on-the-merits decision. 4 is reported
because it splits the exploit turns roughly in half; nothing rests on
the choice.

**So: in this ring, thinking more copies Q.** ChatGPT's point 3 closes
with a number. It is not "the planner is useless" in general — it is
"this corridor has nothing at depth 2 that Q has not already backed up
one cell at a time", which is the same wall NEXUS-2 hit and the same
reason `plan_depth` stays 0.

### The cost of acting on a tie-break

The `--escalate` arm waits where the default approaches, so it walks a
different ring and learns a weaker policy: `policy_after` [-12, +5, 0] →
**[-7, +5, 0]**, `novel_approach_return` +80 → **+48**. Approach still
loses at the threat and `negative_delta_causes_policy_change` still
holds — the escalate run is checked against the same policy lock as the
default, not exempted from it. But the deeper look paid for itself in
neither direction.

### Untouched

`plan.py` (module stays — it is still what reaches c10 from c9 and c11
from c8), `inverse`, `conf`, ATTEND, `SETTLED_HITS`, `parse_reply`, the
viewer. Default intact: `policy_after [-12, +5, 0]`, `false_facts 0`,
`destroyed 0`, `cortex_calls 0`, `level_search 0`,
`novel_approach_return +80`, `t_beats_ring`, `encoder_beats_fnv`.
`--cortex` wakes 36/256.

Tests 119 → 130.

---

## NEXUS-4g — N ≠ S ≠ δ

Three different facts about one turn, counted apart. They were one word
before: `novelty` in `loop.py` was `cam_miss OR cell.kind == NOVEL`, so
the NOVEL cell read novel on every visit forever, and `q.update()`'s
return value was thrown away at the call site.

```
N  first turn ever STARTED on this origin.
   Not the cell's kind: after the first hit, standing on cell 11 again
   is not a miss.
S  T had a prediction and it was wrong: pred_next is not None and
   pred_next != slot_n. A T_MISS is ignorance, not surprise, and is not
   counted. Slot inequality; the Hamming distance stays where it was,
   in prediction_hamming_error.
δ  the integer q.update() returns, counted when non-zero.
```

### Default bench, 352 turns

```
cam_misses         33      surprises            1      deltas       217
novel_no_surprise  33      surprise_known       1      delta_only   208
```

Three different numbers, as they must be. 33 places seen for the first
time, exactly one turn where the map was wrong, 217 turns where the
policy moved. `novel_no_surprise == cam_misses`: on a first visit T has
no prediction, so a new place is never also a surprise — that is the
definition working, not a coincidence.

**S without N is phase F at cell 5, not an extra slot.** The threat
moves 7 → 8; cell 5 is still EMPTY, same 16 B packet, same CAM slot
1517. Its JUMP now lands on a different packet, so T is wrong there:
`conflicts` rises, `alt_n` goes 0 → 1, and KCC keeps the incumbent
(n=4 against alt_n=1) — the learning is `observe()`, not an allocation.
`destroyed` stays 0.

The landing *does* get a new slot: empty-7 is a new packet, so it is a
new CAM entry. That is the destination's N, at a different cell, and the
test says which is which rather than papering over it.

### One definition had to be measured, not assumed

`s.hits == 0` never fires: `navi10_cam.Cam.put()` seeds `hits = 1` on a
fresh slot, and that module is import-only. `cam.get(wsp) < 0` before
allocation does not work either — the loop allocates the *landing* slot
every turn, so a cell is in CAM before the agent has ever stood on it,
and by that reading only **2 of 352** turns are misses. That measures
the allocator, not the agent. N is `s.hits <= 1` after `_slot_for`:
put() seeds 1, this loop adds 1 per turn started here, so ≤ 1 is exactly
"allocated, never stood on". 33, and the first two readings are recorded
here so the choice is auditable.

`store_priority` keeps its rule (curiosity = N ∧ S ≥ 4) and now reads
the clean N instead of the conflated one. It is not in the report JSON
and was not added to it.

### Untouched

`attend()`, `escalate.level()` — this is reporting, not control.
`plan.py`, `escalate.py`, `inverse`, `conf()`, `parse_reply`, `view.py`,
`thought.KEYS`, `SETTLED_HITS`, `C_PLASTIC`, `ESC_MARGIN`. Bench length
still 256 + 64 + 32. Default intact: `policy_after [-12, +5, 0]`,
`false_facts 0`, `destroyed 0`, `cortex_calls 0`, `level_search 0`,
`novel_approach_return +80`, `t_beats_ring`, `encoder_beats_fnv`.
`--cortex` wakes 36/256.

Tests 130 → 136.

---

## NEXUS-4h — the oracle is outside. The env no longer answers.

`RingEnv.ask()` **is gone**. It used to return the extract *and* clear
`hidden_bit` in one call, so physics and testimony were the same object
and `source="oracle"` was a label rather than a provenance. The order is
now three separate things, in this order and no other:

```
oracle.reply()      raw text from outside. Does not touch the env,
                    Q, T or CAM.
oracle.accept(text) VERIFY. NOVEL_CLEAR, or None. Prose, empty, JSON,
                    multi-line and a hex WSP are all None.
RingEnv.reveal(x)   physics, and only physics — reached only after
                    accept passed. An extract it does not recognise
                    changes nothing.
```

`oracle.accept` is deliberately **not** `cortex.parse_reply`. The cortex
emits hypothesis packets; a sensor emits an extract. A reply that passes
one must not pass the other, and a test asserts exactly that on
`"YO → PREGUNTAR → DESCONOCIDO @AHORA"`: `parse_reply` takes it,
`accept` refuses it.

### Provenance, not a label

| packet | source |
|---|---|
| cell 11 | `nexus0-env` — the ring perceived the cell |
| PREGUNTAR | `sensor` (default) or `file` (`--oracle PATH`) |

Never `nexus0-env` on the question, never `sensor` on the cell. Asserted
both ways.

### Default bench, unmoved

```
oracle_source  sensor    oracle_path  None    oracle_rejected  0
questions      1         novel_approach_return  +80
cam_misses    33   surprises   1   deltas  217   surprise_known  1
policy_after [-12, +5, 0]   false_facts 0   destroyed 0   cortex_calls 0
```

The question fires on the same turn as before — only who answers
changed — so the N/S/δ numbers of NEXUS-4g are identical, and the test
asserts the four of them by value rather than by inequality.

The default answerer is an in-process callable that knows one thing
(`oracle.Sensor`). It is a stub and is named one: a file the bench
writes for itself and then reads back would be theatre. `--no-ask` is
silence, not a mute oracle — `Agent.oracle is None`, `questions 0`,
`oracle_rejected 0`, `novel_approach_return −80`.

### An outside answerer, opt-in

`bench --oracle PATH` reads one line. Writes
`lab/nexus0_oracle_report.json`, never the NEXUS-0/1 report.

| answer file | rejected | novel return | false_facts |
|---|---|---|---|
| `NOVEL_CLEAR` | 0 | **+80** | 0 |
| prose | 66 | **−80** | 0 |
| missing | 66 | **−80** | 0 |

A chatty or absent oracle leaves the trap armed, writes no `has_fact`
from that reply, and takes no CAM slot for it. **66, not 1**: the
"asked at most once" guard is keyed on the cell's cleared extract, so a
refused answer means the question is still open and gets asked again on
the next visit. That is the behaviour, stated rather than smoothed —
`questions` in a refused arm counts attempts, not answers.

`+80` is no longer the environment congratulating itself. It is what
happens when something outside the world says one checkable word, VERIFY
accepts it, and only then the trap disarms.

### Untouched

`T_CONF`, `inverse`, `escalate.py`, `plan.py`, N/S/δ (still report, not
control), `attend()`, `parse_reply`, `view.py`, `SETTLED_HITS`,
`C_PLASTIC`, `ESC_MARGIN`. No HTTP, no LLM, no `NAVI_CORTEX_CMD`, no
stdin. Bench length unchanged. `--cortex` wakes 36/256.

Tests 136 → 145.

---

## NEXUS-4i — another corridor

The experiment the ring could not be: the same agent, the same 16 B WSP,
the same three actions, a world that is **not 32 cells**, and a T/Q
carried in from a world that no longer holds.

```
HOME    A → B → C → D        D = GOAL, C = EMPTY
SHIFT   A → B → X → D        X = THREAT, C is off the path
```

Successor by **table**, never `(i+1) % n`. A, B and D keep their index
*and* their kind, so they keep their packet, their CAM slot, their T rows
and their Q rows. C and X are two different cells, not one cell wearing
two kinds — **no cell is repainted**, and a test asserts
`home.kind == shift.kind`. That is the whole difference from phase F,
which *was* a repaint. `approach` at D collects the goal and returns the
agent to A; without it a goal you can stand on is a reward pump.

No NOVEL, no JUMP, no oracle bait. `_ask()` stays wired and never fires:
there is no KIND_NOVEL here, and `questions` is 0.

`Agent(env=…)`; the default is still `RingEnv()`. The 352-turn ring bench
is untouched, and `nexus0/corridor.py` writes
`lab/nexus0_corridor_report.json` — a test greps the module to be sure
the string `nexus0_report.json` does not appear in it.

### The two numbers

**Knows vs does not know, on entry to SHIFT:**

| | T(B, approach) | conf | unseen of {A,B,D} |
|---|---|---|---|
| transferred | **C** (known) | 3 | **0** |
| control (Q=T=0) | **None** | 0 | **3** |

**First visits paid inside the shift window:** transferred **1** (only X,
the genuinely new cell), control **4**. `surprise_known` over the window:
transferred **14**, control **0** — the control cannot be surprised
because it never predicted anything.

### The first wrong step, in another world

Turn 97, the first `approach` out of B in SHIFT. Origin slot unchanged,
origin not counted as a CAM miss, `surprise_known` rose, `conflicts` rose,
KCC kept the incumbent on one observation, and X is a new packet (the
destination's N). Phase F's shape, in a world that is not the ring.

### KPI 4 did not come out as predicted — and was not tuned

The prompt expected `approach` at B to stop winning after the hit on X.
It does not, and it converges there (checked out to 512 shift turns):

```
Q[B]  home [4, 0, 0]  →  shift [1, 0, 0]   best: approach, still
Q[X]  shift [-3, +5, 0]                    approach negative, avoid pays
```

The policy *does* bend where the world moved — `Q[B, approach]` falls by
75 % and `Q[X, approach]` goes negative. It does not turn into refusal,
because in SHIFT **the only route to D runs through X**, and `avoid` at a
threat pays `R_AVOID_OK`, so `max Q[X]` stays positive and B's backup
with it. The agent learns "enter X, then avoid", not "never enter X".
The corridor reuses the ring's own `_reward` unchanged; nothing was
retuned to make an assertion pass, and the test asserts what was measured.

### What this is not

This is not AGI. It is a corridor: five cells, one topology change, one
transferred table. What it shows is narrow and stated narrowly — a T
learned in one world is still right about the part of the next world that
did not change, wrong about the part that did, and it finds out by being
wrong rather than by being told.

### Ring default, untouched

```
policy_after [-12, +5, 0] · novel_approach_return +80 · surprise_known 1
cam_misses 33 · surprises 1 · deltas 217 · oracle_source sensor
false_facts 0 · destroyed 0 · cortex_calls 0 · level_search 0
RingEnv has no ask() · --cortex wakes 36/256
```

Tests 145 → 153. MVP watch: `python3 -m echoai.nexus0.demo`. The
situated program ChatGPT signed is closed. What follows (sleep, a real
LLM behind the firewall, a body, Akida) is another project.


---

## CORTEX-1 — the slow clock changes a decision (2026-09-03)

The first slice outside the situated program. Not a slice of the ring:
the ring never needed a cortex, and the planner proved it
(`search_strictly_better = 0`).

Until now, if `cortex.parse_reply` returned UNIR / TEMER / OBSERVAR, the
loop **threw it away**; only `PREGUNTAR` did anything, through `_ask()`.
That missing wire was the whole slice. There is no LLM in it, and that is
the point: the claim is the cable, not the brand of the model.

### The world (`nexus0/sign.py`)

Two cells. Cell 0 is `KIND_EMPTY` in both layouts and carries a **sign**
in Spanish; cell 1 is GOAL in one layout and THREAT in the other.

| layout | the sign on cell 0 | `approach` from cell 0 |
|---|---|---|
| prize | `AMBAR: entra. El siguiente sitio es el premio.` | **+16** |
| trap | `AMBAR: no entres. El siguiente sitio es una trampa.` | **−16** |

`encode_cell(0, EMPTY)` is `020e0408001400280a00000005000000` in **both**.
The fast loop's entire view of that cell — packet, flat Q row, empty T —
is byte-identical in the world that pays +16 and the world that pays −16.
It does not read Spanish, so greedy it waits. That is not a limitation
being worked around; it is the experiment.

### The numbers (`lab/nexus0_cortex1_report.json`, turn 0, greedy)

| | fast | cortex |
|---|---|---|
| prize | `wait`, **0** | `approach`, **+16** |
| trap | `wait`, **0** | `avoid`, **0** (not −16) |

```
CortexROI +16     decision_change true     questions 0
cortex_calls 2    cortex_rejected 0    cortex_actions 2
false_facts 0     destroyed 0
ATTEND woke by REASON_LOW_C — no new reason code, no new wake in the ring
ring --cortex 36/256, unchanged
```

The trap arm is the half that cannot be faked. A cortex that always said
UNIR would collect the +16 in prize and walk into the −16 in trap; the
report and `test_stub_trap_avoids` both catch that, and a mutation run
confirmed it (5 tests red when the rule is made constant).

### What the cortex is allowed to do

It **proposes**. `_propose` consumes `last_cortex_action`, hands it to
`gate()` exactly like Q's answer, and the gate can still veto it — an
inhibited slot turns the proposal into `wait` and the +16 is not
collected. The cortex writes no CAM slot, no T row and no Q cell: after
the prize turn, CAM holds the two cells that were stood on and nothing
else, and the slot's extract is the world's sign verbatim, with no atom
of the reply in it. `has_fact` means *a sign was there*, never *the sign
told the truth*.

One guard is worth naming. `cortex.propose()` hands the observation back
unchanged when it has no hypothesis, and an EMPTY cell's own packet
already reads `OBSERVAR` while a THREAT's reads `TEMER` — both in
`ACTION_REL`. Treating that echo as advice would let the ring take orders
from its own perception. Only a reply that came from **outside** and
survived `parse_reply` sets a proposal, which is why the ring with
`--cortex` still has `cortex_actions = 0`.

### The cortex of CI (`nexus0/tools/sign_cortex.py`)

Twenty lines, no imports from echoai, no network, no weights. Reads the
turn JSON on stdin, matches the sign, prints one line of atoms — or
prints **nothing** when there is no sign, which is a real answer: away
from cell 0 the reply is silence, `parse_reply` rejects it, and Q decides
(`cortex_rejected_8 = 1` in the 8-turn probe). A cortex that always
speaks is a cortex that cannot be wrong.

`nexus0/cortex.gbnf` is the grammar a future llama.cpp would be
constrained to. Nothing in CI runs it.

### What is still unmeasured

The 4B was **not** run. Latency on this host, tok/s, the reject rate under
GBNF and the CortexROI of a real model are four numbers this slice does
not have, and they are the whole content of the follow-up report, with
host and quant labelled.

Second honest limit: ATTEND stops waking after the sign cell settles
(flat row, `hits >= ATTEND_SETTLED_HITS`), so the cortex steers turn 0 and
then falls silent. That is ATTEND doing its job — not thinking always —
not the cable failing, and the KPI is turn 0 by design.

Tests 155 → 173. `lab/nexus0_report.json` untouched; CORTEX-1 writes
`lab/nexus0_cortex1_report.json` only.

---

## GUI-1 — the board (2026-09-03)

A circuit board, not a 3D brain. `nexus0/board.py` turns a
`thought.jsonl` into **one self-contained HTML file**: CSS and JS inline,
the turns embedded as a JSON array, zero CDN, zero network, no WebSocket,
no tail. It opens over `file://` with no server.

```
python3 -m echoai.nexus0.bench --thought
python3 -m echoai.nexus0.board echoai/lab/thought.jsonl
→ lab/board.html   112 321 bytes · 352 turns · 32 cells
```

The ANSI demo stays. CI does not need a browser, and nothing here
replaces `view.py` or `demo.py`.

### The log grew from 12 keys to 17

The board cannot paint what the log does not carry, and `loop.turn` was
computing five numbers and dropping them on the floor. `thought.KEYS` now
adds exactly:

```
n              0|1        CAM miss on the origin this turn  (n_fact)
s              0|1        T predicted and was wrong          (s_fact)
delta          0|1        Q.update returned non-zero         (d_fact)
cortex_action  null|0|1|2 the proposal _propose consumed
gate_decision  0|1|2      OK / MODIFY / BLOCK
```

Integers and null. No prose, no nested `events[]` — a viewer can derive a
timeline from these and cannot derive these from a timeline. The twelve
older keys keep their name, their order and their meaning; a test pins
`KEYS[:12]`. `cortex_action` is read in `turn()` *before* `_propose`
consumes it, so it is the proposal that actually got a vote, and it is
`null` on every turn of the ring.

The flags are not a second, looser accounting: over the 352-turn bench
`sum(n) = cam_misses = 33`, `sum(s) = surprises = 1`,
`sum(delta) = deltas = 217`, asserted.

### What the board shows, and what it cannot

Eight blocks, each showing this turn and not a metaphor for it: CAM
(hit / MISS), WSP (the packet as atoms), T (`ŝ'` or —, red when S fired),
Q (three integer bars, blue when δ ≠ 0), GATE (ok / modify / block),
ATTEND (on/off + reason), CORTEX (the proposal, dashed grey — a
hypothesis, never solid), ORACLE (whether `questions` rose).

The ring is drawn from the log alone, rebuilt from turn 0 on every frame:
a cell nobody has stood on yet is `?`, not a guess, and scrubbing
backwards **un-reveals**. That is why the phase F threat move shows up
exactly when it happened — turn 120 has `T` at cell 7, turn 300 has it at
cell 8 — rather than being seeded from `RingEnv`.

The world's size comes from the log (`max(cell) + 1`), never from
`N_CELLS`: a `sign.py` log draws two cells, not thirty empty boxes.

`board.py` imports `argparse`, `json`, `pathlib`, `sys` and nothing else.
It does not import `loop`, `qtable`, `world`, `attend` or navi10, and
`loop.py` gained **zero** imports — no Qt, no second bus. Both directions
are pinned by tests that read the source as text.

**One honest gap.** The five permitted keys contain no per-turn reject
flag, so a cortex that woke and said nothing looks the same on the board
as one whose reply `parse_reply` refused. Both read "woke and proposed
nothing", and the legend on the page says so. Inventing a sixth key was
not in the contract; if that distinction is wanted it is a key, not a
guess in the viewer.

### Locks

```
policy_after [-12, +5, 0] · novel_approach_return +80 · surprise_known 1
cam_misses 33 · surprises 1 · deltas 217
false_facts 0 · destroyed 0 · cortex_calls 0 · cortex_actions 0
ring --cortex 36/256 · CORTEX-1 sign green · thought.KEYS = 17
```

Tests 173 → 185.

---

## WORLD-3 — 256 addresses, one edge moves (2026-09-04)

`nexus0/graph.py`. Not the ring, not the corridor of five, not SIGN. The
first body-map: the animal's position **is** the node. Same `Agent`, same
16 B WSP, same three actions, same `encode_cell(index, kind)`. What is new
is the address space.

```
256 nodes · successor by table, never (i+1) % n, never a 2D grid
spine  16 shared nodes, index and kind identical in both layouts
HOME   ... -> B(174) -> C(187) -> GOAL(200) -> back to START(5)
SHIFT  ... -> B(174) -> X(251) -> GOAL(200) -> back to START(5)
```

**Exactly one edge differs**: `approach` out of the fork B. Counted, not
asserted — `test_only_one_edge_differs` walks all 3 × 256 rows of both
tables and the diff is `[(approach, 174)]`. C is EMPTY and X is THREAT:
two nodes with two kinds, not one node repainted. Nothing changes its
label, so every packet, CAM slot, T row and Q row survives the move. In
HOME nothing points at X; in SHIFT nothing points at C. `approach` at
GOAL collects and returns to START — a goal you can stand on and
re-collect is a reward pump, not a world.

### The transfer, without money in it

On entry to SHIFT, with CAM/T/Q carried and nothing reset but the world:

```
T rows known on the 16 spine nodes      16
still true of HOME                      16 / 16
still true of SHIFT                     15 / 16
the one that is not                     spine position 13 = the fork
control (Q/T/CAM empty), rows known      0
spine nodes unseen on entry   transfer 0   control 16
```

That is the whole claim, and it costs no reward to state: fifteen of the
sixteen rows learned in HOME describe the new world exactly, and the agent
is wrong **only** where the world changed. The first greedy turn in SHIFT
proves it from the other side — T commits to C, the world hands back X,
`surprise_known` rises, the origin slot is unchanged and is not a CAM
miss, and X is a new packet. Same shape as the corridor's first wrong
step, in a world of 256 addresses.

### `transfer_gain` = +256, and what it is made of

```
transfer_reward_sum_shift   256   (64 greedy turns from the fork)
control_reward_sum_shift      0
transfer_gain              +256
transfer_goal_hits_in_shift   0
transfer_avoid_pays_in_shift 32  x R_AVOID_OK(8) = 256
```

Read it exactly as it is. The carried agent walks into X, its Q row for a
node it has never seen is flat, greedy answers `wait`, and the **gate**
turns that into `avoid` at a threat — which pays `R_AVOID_OK`. It bounces
B ↔ X for the whole window and **never reaches GOAL in SHIFT**. The
control has a flat row everywhere, so greedy answers `wait` and it does
not move at all. So the gain is real reward on the same seat, the same
seed and the same number of turns, and it is *not* a goal: it is the
difference between an agent with a policy and an agent with none. Both
halves are asserted in `test_transfer_gain_positive` so the number cannot
be read as more than it is. No reward was retuned; `R_SUCCESS` /
`R_THREAT` / `R_AVOID_OK` are the ring's own.

### The credit horizon — why the fork is at spine position 13

Measured on this spine, not assumed. Q is integer with α = 1/4, so a
positive δ below 4 shifts to zero and value stops travelling. Counting
back from GOAL, `Q[approach]` along the 16-node spine reads:

```
0 0 0 0 0 0 0 0 0 0 0 0 0 4 8 13     (512 turns; identical at 2048)
```

Three nodes deep and no further. Eligibility traces (`trace=True`) do not
extend it — they spread the debt and leave the far spine negative
(`-27 -5 -6 …`), with greedy answering `avoid` at the start. So the fork
sits inside the horizon at position 13. Put it at position 1, as first
sketched, and both arms stand still in a flat row: `transfer_gain` would
be 0 − 0, a KPI that cannot be failed. The mutant was run; it goes red.

### CAM, and what 256 does and does not prove

```
nodes 256 · reachable 17 (16 spine + X) · cam_occupied 17 / 4096
```

The 239 off-path nodes are their own successor, so the table is total
without inventing an edge — and nobody ever stands on them. **WORLD-3
does not press CAM.** ANTI-ALIAS has nothing to bite on here yet, and this
report says so rather than implying otherwise.

What 256 *does* prove is the packet ceiling. `encode_cell` writes the node
index into `ext.seq` as `index & 0xFF`, so node 256 hands back byte for
byte the packet of node 0. 256 is exactly this encoder's ceiling before
two places become one place — the number ANTI-ALIAS has to move.
`test_256_is_the_packet_ceiling` pins both halves: the collision at 256,
and 256 distinct packets below it.

### Locks

```
ring default untouched: policy_after [-12, +5, 0] · +80 · surprise_known 1
cam_misses 33 · surprises 1 · deltas 217 · oracle_source sensor
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0
WORLD-3 cortex OFF · 3 actions · green true
report lab/nexus0_world3_report.json, never nexus0_report.json
```

Tests 192 → 208. This is not AGI. It is the corridor of five grown to 256
addresses.

---

## GUI-2 — the board, live (2026-09-04)

`nexus0/board.py --follow`. The same board as GUI-1, watching the log as
it is written.

### Why there is a server at all

A page opened with `file://` cannot watch a file grow. It has no way to
re-read the disk on a timer, and GUI-1's turns are baked into the
document at write time. So `--follow` starts a stdlib server on the
loopback and the page asks it, once every 200 ms, for the turns it does
not already hold. **That is a design consequence, not a workaround** —
the alternative would have been a second protocol, which is exactly what
the contract forbids.

```
python3 -m echoai.nexus0.board echoai/lab/thought.jsonl --follow
http://127.0.0.1:8765/  poll 200 ms  route /turns.json
```

Two routes and no files: `/` renders the page, `/turns.json?from=N`
answers with the turns after N. Nothing on disk is reachable by URL, so
there is no path to traverse — `/etc/passwd` and `/../../board.py` are
404, asserted. `127.0.0.1` is not a flag; a board reachable from another
machine would be a service. `?from=N` is parsed by hand rather than by
importing a URL library to read one integer, and junk reads as 0 instead
of a stack trace.

### The KPI, as a test and not a screenshot

`test_the_poll_sees_a_line_that_was_not_there`: write a two-turn jsonl,
start the server on a real socket in a thread, `GET ?from=0` → 2 turns,
**append a third line**, `GET ?from=2` → exactly that turn, `total` 3,
`cells` 8 (the world grew with it), all 17 keys present. Freeze the
reader's cache so the poll only ever answers what was on disk at startup
and four tests go red, that one included.

Run for real, board up before the log existed, against the ANSI demo
writing 48 turns:

```
before loop: waiting = true
27 polls saw new turns: from=0 [0] · from=1 [1,2] · … · from=47 [47]
final total 48 · Ctrl-C exit 0
```

The loop was never told anybody was watching: the board is a second
reader of the same jsonl a human could `tail`.

### One protocol, and it is the one already in use

```
new WebSocket  0      EventSource 0      CDN 0      npm 0      Qt 0
<script> tags  1      fetch(      1      http:// in the page  0
loop.py imports gained  0      thought.KEYS  17, unchanged
```

`board.py` still imports no part of the fast path — not `loop`, `qtable`,
`world`, `attend`, `cam` or navi10 — and `loop.py` contains none of
`board`, `http`, `socket`, `Qt` or `WebSocket`. Both directions are
pinned by tests that read the source as text.

### `file://` is untouched

`test_the_file_board_is_untouched_by_gui2`: `render_html(recs)` and
`render_html(recs, live=False)` are the same string, and it carries no
`fetch(`, no `/turns.json`, no poll loop, no badge. The live page is the
same board and not a second one — same CSS, same JS, with the poll
appended. Verified beyond the test as well: regenerating
`lab/board.html` after this slice gives a file byte for byte identical
to the one GUI-1 wrote (112 321 bytes, md5 unchanged).

### Two things the writer forced

The log is being appended to while it is read, so:

- **A torn final line is dropped, not raised** — it will be whole on the
  next poll. A bad line anywhere *earlier* is a corrupt log and raises.
- **The parse is cached on (mtime, size)** so a 200 ms poll does not
  re-read a growing file for nothing, and a test asserts the cache does
  not hide the next line.

And a log that does not exist yet is `waiting`, not an error: the board
can be started before the loop. Without `--follow` a missing log is still
`no such log`, exit 1.

### Locks

```
policy_after [-12, +5, 0] · +80 · surprise_known 1 · false_facts 0
destroyed 0 · cortex_calls 0 · thought.KEYS 17 · WORLD-3 green
```

Tests 208 → 221.

---

## CUERPO-1 — a body, not another graph (2026-09-04)

`nexus0/body.py`. The animal stops being an index in a table: it has a
**pose**, and orientation is state of the body, not a fourth action. Same
`Agent`, same three actions, same 16 B packet via `encode_cell`.

```
grid     5 x 5, six walls          heading  0,1,2,3 = E,N,W,S  (y grows north)
pose     index = (x + 5*y)*4 + h   100 bins, max index 99 < 256

approach   one step the way it faces; into a wall or off the grid it does
           not move and the collision pays R_THREAT
avoid      turn 90 deg counter-clockwise (E->N->W->S). No translation.
wait       nothing moves

y=4  .  .  .  .  G        start (0,0) facing E
y=3  .  #  #  #  .        goal  (4,4), collect and go home
y=2  .  .  .  .  .        row y=2 is the corridor
y=1  .  #  #  #  .        block layout: (2,2) becomes a wall
y=0  S  .  .  .  .
```

`cell().index` **is** the pose: there is no second position ledger, which
was the way this slice could have been a costume. `kind` belongs to the
floor tile, never to the heading — the four poses on the goal tile are
all GOAL and the index separates them. **No floor tile is painted
THREAT.** The threat here is the collision itself, so `cell.threat` is
false everywhere and the gate never modifies an action in this room: the
bump's −16 goes into Q unhelped. Nothing is retuned; `R_SUCCESS` /
`R_THREAT` are the ring's own.

### `t_beats_stepper` — two arms, and they carry different halves

The baseline is "always one step east", blind to heading and to walls.
Both arms score T and the stepper on exactly the same poses.

```
free-running (run(), nobody helping)   T 10/10   stepper  4/10
   poses stood on 10 of 76 · stepper answered and missed 0
swept (carried to every pose in turn)  T 76/76   stepper 12/76
   stepper answered and missed 44
```

Read honestly: **free-running, the win is the cheap half.** The animal's
own loop hugs the east wall and the top-right column, where "x+1" cannot
even state a guess, and an unanswerable guess is scored as a miss. The
**strong** half is the swept arm, where the stepper answers 44 times and
is wrong every one of them:

```
(0,0,N)  heading  truth (0,1,N)   stepper said (1,0,N)
(0,0,W)  wall     truth (0,0,W)   stepper said (1,0,W)
(1,0,N)  wall     truth (1,0,N)   stepper said (2,0,N)
```

Not a 0.99 world model. It is the JUMP comparison again: arithmetic loses
to a table that has felt the exceptions, and here the exceptions are
heading and walls.

### One tile becomes a wall

```
approach successors that change, open -> block   4
   (1,2,E) (2,2,E) (2,2,W) (3,2,W)
avoid successors that change                     0
```

Turning is body physics and never consults the room, so closing the
corridor changed no `avoid` row at all. Of the 76 T rows carried into the
new floor plan, 72 are unaffected and **all 72 are still true** there;
the 4 that are not are exactly the ones the diff names. The room is
harder, not impossible — the left and right columns still join start to
goal, asserted by flood fill.

### What the free-running animal actually did

It found a **ten-pose loop** on its own: east along y=0 to (4,0), one
turn north, up the x=4 column to the goal, collect, home. 42 goal
collections during training — every positive reward in this room is a
collection, since no tile is THREAT and `R_AVOID_OK` can never be paid.

### Greedy stands still, and here is the number

```
greedy from start, 128 turns:  reward 0 · goal hits 0 · poses visited 1
Q[approach] along the free loop:  0 0 0 0 -4 0 0 4 8 13
```

The same integer credit horizon WORLD-3 measured: α = 1/4 drops a
positive δ below 4, value stops about three steps back from the goal, and
the start of a ten-pose loop is nine steps away. So the greedy probe
waits. The −4 is (4,0,E), the pose facing the east wall — it learned the
bump. **This is reported beside the KPI and is not the KPI**: walking to
the goal on purpose is WALK-1, and this is the number that slice has to
move.

### Locks

```
poses 100 · reachable 76 (72 in block) · cam_occupied 76 / 4096
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0 · 3 actions
ring default untouched: policy_after [-12, +5, 0] · +80 · surprise_known 1
report lab/nexus0_cuerpo1_report.json, never nexus0_report.json
```

Tests 221 → 238. Not MiniGrid, not eight actions, not lidar, not a
camera, not Akida. A turtle in a small room.

---

## WALK-1 — reverse curriculum. **RED**, and here is the number (2026-09-04)

`nexus0/body.py --walk`, report `lab/nexus0_walk1_report.json`. The runner
**exits 1**. The KPI was `exam_goal_hits > 0` from the canonical start and
it scored **0**. Nothing was retuned and the start was not moved.

### What was built, exactly as specified

Reverse curriculum in *training only*: distance to a collection is flooded
backwards over the successor table itself (a turn costs a step, so this is
not Manhattan — Manhattan is blind to heading, and heading is half of this
body's state), and one agent is trained from distance 1 outward to 12,
keeping Q/T/CAM throughout. 14 544 training turns. Then the exam: the same
agent, teleported to **(0,0,E)**, greedy, cortex off, 128 turns.

```
phase  d=1   d=2   d=3   d=4   d=5   d=6 …
goals   48    32    42    48    16     0
Q[app]   8     4     0     0     0     0
```

**The curriculum worked.** The animal collected goals in every near phase,
including from distance 4. It is not an exploration failure.

```
exam start (0,0,E)  · distance to a collection 9
exam goal_hits 0 · reward 0 · bumps 0 · poses visited 1   (it stood still)
Q[approach] along the shortest path from the start:
    0  0  0  0  -16  0  0  4  8  13
```

### Why, as arithmetic rather than as an excuse

`qtable.update` ends in `q += delta >> 2`. A positive delta below 4 shifts
to **zero**, so on a chain paying only at the end the value converges to

```
q_k  =  (7 * q_(k+1)) // 8  -  3     ->   13, 8, 4, 0, 0, 0, …
```

`credit_chain()` in `body.py` replays that integer expression to its fixed
point — nothing is monkeypatched, `qtable.py` is untouched — and predicts
`[13, 8, 4, 0, 0, …]`. The measured best `Q[approach]` by distance is
`{0:13, 1:8, 2:4, 3:0, 4:0, …}`. **The prediction and the measurement are
identical.** Value stops three states from the goal; the start is nine.

A fixed point is not a shortage of turns, and that is asserted rather than
argued: `test_more_training_at_the_wall_changes_nothing` soaks distances
1–3 for over 10 000 turns and gets 8, 4, **0**.

So a reverse curriculum reaches the wall faster. It cannot move it: the
wall does not depend on the order states are visited in.

### What would move it, and why it was not done

The same chain with no truncation is positive the whole way —
`credit_chain(0, 12)` = `[16, 14, 12, 10, 8, 7, 6, 5, 4, 3, 2, 1, 0]`. A
throwaway probe that monkeypatched `ALPHA_SHIFT` to 0 (never shipped, not
in the repo) ran the identical curriculum and identical exam and scored
**goal_hits 12, reward 192** from (0,0,E).

That isolates the blocker exactly: it is the α = 1/4 integer step, not
exploration, not the room, not the curriculum. Every fix for it —
`ALPHA_SHIFT`, eligibility traces, n-step returns, a residual accumulator
for the truncated remainder — is on this slice's forbidden list, and
rightly: each is an architecture change to the fast path and deserves its
own KPI. **This slice does not get to make it quietly.**

Traces were tried anyway, as a mutant: the exam moves and still collects
nothing, which agrees with what WORLD-3 measured about them.

### The tests are honest about it

`test_goal_hits_positive` asserts the KPI as written and is marked
`@unittest.expectedFailure`. It is not deleted and not weakened — the suite
reports `expected failures=1`, and the day somebody moves the wall it
becomes an *unexpected success* and must be promoted to a plain assertion.

Both ways of faking green are caught twice over. Examining from a pose one
step from the goal turns `test_exam_is_canonical_start` red **and** makes
the KPI test an unexpected success; choosing actions from the stored route
turns `test_no_hardcoded_path` red and does the same. `shortest_path()`
exists only for the report — `test_no_hardcoded_path` reads the source of
`_exam` and asserts it contains no route, no successor table, no pose
constant and no action constant.

### Locks

```
alpha_shift 2 · gamma 7/8 · R_SUCCESS 16 · R_THREAT -16 · R_AVOID_OK 8
traces false · plan_depth 0 · cortex_calls 0 · questions 0
false_facts 0 · destroyed 0
ring default untouched: policy_after [-12, +5, 0] · +80 · surprise_known 1
CUERPO-1 still green · report never touches nexus0_report.json
```

Tests 238 → 249, `OK (expected failures=1)`.

---

## CREDIT-1 — keep the crumbs. **GREEN** (2026-09-04)

`QTable(remainder=True)` / `Agent(remainder=True)` /
`python3 -m echoai.nexus0.body --walk-remainder`, report
`lab/nexus0_credit1_report.json`. α is still 1/4, γ is still 7/8, every
`R_*` is untouched and the default is **off**.

### The change, in four lines

```python
owed = rem[s][a] + delta
step = trunc_div(owed)          # toward zero:  5->1  3->0  -3->0  -5->-1
rem[s][a] = owed - (step << 2)
q[s][a] = clip_i8(q + step)
```

`delta >> 2` threw away three quarters of every small update. Now they
are **owed** and paid the moment the debt reaches a whole unit: four
deltas of 3 pay 3 units instead of 0.

`trunc_div` is not `>>`. Python's shift **floors**, so `(-5) >> 2` is -2
where `+5 >> 2` is +1 — a negative delta would pay more than it owed and
the remainder would go on owing credit already spent. Truncation toward
zero keeps the two signs symmetric. Integers throughout.

The debt is bounded by construction: `|rem| < 4` always, because a whole
unit is paid the instant it exists. Measured peak during the whole
curriculum: **3**. At the fixed point delta is 0 and nothing is owed, so
the end-state remainder is 0 along the path and non-zero in 26 of
4096×3 cells.

At the int8 rail the credit is dropped rather than accumulated — a debt
against a value that cannot move would grow without bound.

### The KPI

Same curriculum, same exam, same canonical start, same rewards, same α.
The only difference is the flag.

```
                     WALK-1 (off)      CREDIT-1 (on)
exam_start              (0,0,E)           (0,0,E)
exam_goal_hits                0                12
exam_reward_sum               0               192   = 12 x R_SUCCESS
exam_bumps                    0                 0
exam_poses_visited            1                10   the ten-pose loop
green                     False              True
```

Q along the shortest path from the start, where WALK-1 had seven zeros:

```
off  [ 0,  0,  0,  0, -16,  0,  0,  4,  8, 13]
on   [ 3,  4,  5,  6, -10,  9, 11, 13, 15, 18]
```

Positive the whole way, so greedy walks. The −10 at index 4 is (4,0,E),
the pose facing the east wall: it still knows the bump, and the exam
records **0 bumps** because the policy turns there instead.

Predicted before it was run, from the integers alone:
`credit_chain_with_remainder(12)` = `[16, 14, 12, 10, 8, 7, 6, 5, 4, 3, …]`
— the chain loses the `− 3` and stays positive past nine steps.
`credit_chain(2)` is untouched and still predicts the wall
`[13, 8, 4, 0, …]` for anyone who does not pull the lever.

### WALK-1 stays red

It is not rewritten, not quietly fixed, and its report on disk still says
`green: false, exam_goal_hits: 0`. `body --walk` still exits 1, and
`test_goal_hits_positive` is still `@unittest.expectedFailure`
(`OK (expected failures=1)`). `test_walk1_without_remainder_still_red` is
the control and asserts it.

### The ring, asked and answered

**Yes — the remainder moves the ring's locks. It is measured here and it
is not enabled.** Probed by patching `Agent` in a throwaway script;
`bench.py` has no remainder flag and is not getting one:

```
remainder=False   policy_after [-12, +5, 0]   deltas 217
remainder=True    policy_after [-11, +12, 0]  deltas 218
both              +80 · surprise_known 1 · false_facts 0 · cortex_calls 0
                  t_beats_ring True
```

The firewall and the epistemics do not move; the *policy numbers* do.
That is exactly why this is opt-in and why the default bench never sees
it. Off means no array at all — `rem` is `[]`, and `update` takes the
branch it always took.

Traces and the remainder raise `ValueError` together: two answers to the
same question, pick one.

### Locks

```
default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
         false_facts 0 · destroyed 0 · cortex_calls 0 · remainder False
alpha_shift 2 · gamma 7/8 · R 16/-16/8 · traces false · plan_depth 0
CREDIT-1 report never touches nexus0_report.json or the WALK-1 red one
```

Tests 249 → 260, `OK (expected failures=1)`.

---

## PULPO — a 3D body. Three legs green, one **RED** (2026-09-04)

`nexus0/body3d.py`, report `lab/nexus0_pulpo_report.json`. The runner
**exits 1**. Three of the four things asked for are measured green; the
fourth, the change of strategy, is red for two reasons that are both
numbers.

```
3 x 3 x 3 voxels, 6 headings      index = (x + 3y + 9z)*6 + h   0..161
approach  one voxel the way it faces; into stone or off the cube it does
          not move and pays R_THREAT
avoid     h -> (h+1) % 6 over +X, +Y, +Z, -X, -Y, -Z. No translation.
wait      nothing moves
```

161 < 256, so all 162 poses are distinct packets; 4³·6 = 384 would alias,
which is why the cube is 3. `encode_cell(0)` still equals
`encode_cell(256)` and that is left alone.

The room is two corridors that share only the corner they start and end
at, with no voxel of one touching the other:

```
short   (0,0,0) (1,0,0) (2,0,0) (2,1,0) (2,2,0) (2,2,1) (2,2,2)    8 actions
long    (0,0,0) (0,0,1) (0,0,2) (0,1,2) (0,2,2) (1,2,2) (2,2,2)   18 actions
block   (2,1,0) becomes stone. The long way is untouched.
```

### Green: a 3D body that walks

```
exam from (0,0,0,+X), greedy, cortex off, remainder on, 512 turns
open   56 collections · reward 896 · 9 poses · reached (2,2,2)
       moved on all three axes
T      70/70 correct · stepper 4/70 · stepper answered and missed 38
       (heading and stone, with examples)
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0 · CAM 70/4096
```

CREDIT-1 is what makes this possible; with the plain `>> 2` it stands
still, exactly as WALK-1 measured in 2D.

### Red: it does not take the detour

```
block  0 collections · reward -32 · visits (1,0,0) and (2,0,0), bumps
       into the plug, and stops
```

**Reason one, arithmetic.** The detour is 18 actions from the start and
the value horizon is **11** — computed from the shipped integers, cycle
feedback included, and the geometry search below could not beat it.

**Reason two, exploration, and this is the more interesting one.**
`qtable.select` answers `approach` on a flat row, always; `avoid` is only
tried once a row is *not* flat. The only thing that unflattens a row at a
pose the route must **turn** at is the −16 of walking into stone. So a
turn in open air is a turn the fast loop can never discover.

```
open route   2 turns, both against stone          learnable
block route 12 turns, 3 of them in open air       not learnable
```

That is also why the 2D body worked: its one turn was at (4,0,E), facing
the east wall. It was never a general ability — it was a corner.

### What was searched before calling it red

The heading ring is a free choice of labels, and the first one
(+X, −X, +Y, −Y, +Z, −Z) learns **nothing at all**, from any geometry: it
costs two turns per corner and the intermediate heading points back down
the corridor just walked, so that pose's row stays flat. Regrouping it to
(+X, +Y, +Z, −X, −Y, −Z) makes a corner one turn and is what made the
open arm work.

Then, exhaustively over the cube: every start, goal, pair of
middle-disjoint corridors, and plug.

```
pairs with both routes under the horizon                      1462
of those, with every turn against stone in both layouts          0
with a learnable open route and the goal still connected       695
of those, with a learnable blocked route                         0
```

25 of the best candidates were trained with the real agent rather than
judged on paper: every one gave `open > 0, block = 0`. A 3×3×3 cube with
a 6-cycle turn has no geometry that satisfies both legs. The cube was not
raised to 4×4×4 (384 > 256) and no geometry was faked.

### What was not done

No `if block: avoid`. No waypoint list — `test_no_hardcoded_path` reads
the source of `_exam` and asserts it holds no route, no successor table,
no pose constant and no action constant. No retuned reward, no `α` change,
no traces, no planner, no cortex. `green()` still demands
`exam_block_goal_hits > 0`, so the runner reports the failure, and
`test_exam_block_goal_hits_positive` is `@unittest.expectedFailure` —
when either blocker moves it becomes an unexpected success and has to be
promoted.

### What would move it

Not more turns and not a bigger reward. Either the exploration rule has
to be able to try a turn from a flat row, or the value horizon has to
reach past 11. Both are changes to the fast path, both would move the
ring's `[-12, +5, 0]`, and both deserve their own KPI and their own
opt-in flag — the way CREDIT-1 got one.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
false_facts 0 · destroyed 0 · cortex_calls 0 · remainder False
alpha_shift 2 · gamma 7/8 · R 16/-16/8 · traces false
report never touches nexus0_report.json, cuerpo1, credit1 or the walk1 red
```

Tests 260 → 274, `OK (expected failures=2)`.

---

## PULPO-C — reorientación (verde)

`nexus0/body3d.py`, `nexus0/qtable.py` (`select`), `nexus0/loop.py`.
Runner: `PYTHONPATH=. python3 -m echoai.nexus0.body3d` → **rc 0**.

El tapón cobra. Mismo cuerpo, mismo Q, misma T, misma CAM, tres acciones,
córtex apagado, examen greedy desde `(0,0,0,+X)`.

```
open    64 cobros · reward 1024 · 8 poses · ejes [0,1,2] · llegó a (2,2,1)
block   42 cobros · reward  672 · 12 poses · usó el desvío · 0 choques
control 64 / 0     ← el mismo horario con la palanca apagada
T       56/56 · stepper 4/56 · el stepper contestó y falló 30 veces
```

### El cuerpo (geometría nueva, dentro de 3×3×3)

```
corto   (0,0,0) +X +X  +Y +Y  +Z      (2,2,1)    5 movs + 2 giros =  7
largo   (0,0,0) +Y +Y  +Z     +X +X   (2,2,1)    5 movs + 6 giros = 11
tapón   (2,1,0), en medio del corto. El largo intacto.
```

Los dos corredores comparten solo START y GOAL, y ningún voxel de uno
toca un voxel del otro: no hay tercera ruta escondida. 162 poses, 161 <
256, el techo del paquete sigue medido y no subido — 4³·6 = 384 aliasea.

El desvío mide **11** y `value_horizon()` mide **11**. No es coincidencia:
es la restricción. Con la palanca encendida la cadena entera de Q sale
exactamente como la predice la aritmética entera, y el START se lleva la
última unidad que el descuento puede cargar.

```
dist  11 10  9  8  7  6  5  4  3  2  1  0
Q      1  2  3  4  5  6  7  8 10 12 14 16     margen 1 en el START
```

### Las dos palancas

**1. `explore_flat` en `qtable.select`.** Opt-in, default `False`, memoria
extra **cero**, `update()` sin tocar. Con la palanca apagada una fila
plana contesta `approach` siempre, así que un giro solo se descubre donde
avanzar duele: contra piedra. Con ella encendida la fila plana entra en el
mismo ciclo `turn % 3` que ya tenía una fila no plana. `best()` decide
igual todos los turnos greedy y todos los de explotación.

**2. Curriculum inverso también en `block`.** `_curriculum(ag, layout,
turn)` está parametrizado por layout y usa `poses_by_distance(layout)`;
no nombra ninguna ruta. Tras el tapón se vuelve a pasar sobre el cubo que
el cuerpo tiene ahora. El teleport es ayuda de **entrenamiento**: el
examen siempre sale del START canónico.

### El presupuesto de turnos por teleport — medido, no elegido

`episode_turns(d) = N_ACTIONS * (d + 2) + 1`. Dos propiedades, las dos
descubiertas rompiéndose:

- **Largo.** `d + 2` es el presupuesto greedy y basta para un cuerpo que
  no explora. Uno que explora gasta turnos en las otras dos acciones:
  `d + 2` cobra **0** en el examen open donde `3·(d+2)` cobra 47.
- **Coprimo con `N_ACTIONS`.** El contador de turnos corre a través de los
  teleports, así que un episodio de un número entero de ciclos ofrece a
  cada pose la misma acción cada repetición. Medido en la pose donde el
  desvío tiene que girar: con `3·(d+2)` recibió `wait` veinte veces,
  `approach` veinte veces y `avoid` **ninguna**. El `+ 1` hace precesar la
  fase.

### Giros al aire, que era el bloqueo real

```
ruta open  2 poses de giro, las dos contra piedra → aprendible sin palanca
ruta block 6 poses de giro, 2 al aire libre      → NO aprendible sin ella
           (0,0,0,+X) y (0,2,1,-Z): avanzar sigue funcionando ahí
```

Por eso el brazo abierto ya andaba y el desvío no. El informe lleva las
dos preguntas con la palanca y sin ella, y el control corre entero cada
vez en vez de estar escrito en prosa.

### Mutantes

```
palanca ignorada en select            6 rojos · body3d rc=1
palanca ON por defecto                1 rojo  · body3d rc=0 · bench rc=0
episodio = d+2 (presupuesto greedy)   6 rojos · body3d rc=1
episodio = múltiplo de N_ACTIONS      5 rojos · body3d rc=1
sin readaptación tras el tapón        5 rojos · body3d rc=1
tapón en el corredor largo            6 rojos · body3d rc=1
desvío 12 (START mirando -Z)          6 rojos · body3d rc=1
```

El último es la prueba del horizonte por medición, no por argumento: todo
igual, la palanca encendida, el desvío una acción más largo, y
`exam_block_goal_hits` cae de 42 a **0**.

### Dos cosas que hay que decir claras

**La palanca encendida por defecto no mueve el anillo.** Medido:
`policy_after [-12, +5, 0]`, +80, 33/1/217, `surprise_known 1`,
`false_facts 0`. Sigue apagada por defecto porque el contrato del anillo
está medido sobre el `select` que siempre tuvo, no porque lo rompa.

**El brazo abierto se paga.** Tras el curriculum en `block`, el examen en
el cubo abierto cobra 42 por el desvío, no 64 por el atajo: el cuerpo se
queda con la última ruta que le enseñaron. Está en el informe como
`exam_open_goal_hits_after_readapt`. No es KPI y no baja ninguno; es un
número que hay que ver, y es el olvido que le toca a ECHO-1, no a este
tajo.

### Lo que no se hizo

Ni `if block: avoid`, ni waypoints, ni lista de poses —
`test_no_hardcoded_path` sigue leyendo `_exam`, y
`test_the_curriculum_names_no_route` lee además `_curriculum`. Ni R, ni
α, ni γ, ni trazas, ni n-step, ni planner, ni córtex, ni 4ª acción, ni
4×4×4. `green()` no se debilitó: se le **añadieron** condiciones
(`detour_cost_block <= value_horizon`, `> short_cost_open`,
`explore_flat`).

`test_exam_block_goal_hits_positive` deja de ser `@expectedFailure` y
pasa a aserción normal. WALK-1 sin resto sigue rojo a propósito y es el
único `expectedFailure` que queda.

### Corrección de contabilidad

`t_before` metía filas que T nunca aprendió (`predict` → `None`) y luego
las contaba como rotas por el tapón. Ahora solo lleva lo que T sabía:
`t_rows_carried` 56, `unaffected` 52, `still_true` 52.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0
remainder False · explore_flat False · traces false
alpha_shift 2 · gamma 7/8 · R 16/-16/8 · CAM 59/4096
bench rc=0 · body rc=0 · body --walk rc=1 (rojo a propósito)
body --walk-remainder rc=0 · graph rc=0 · sign rc=0 · demo rc=0
```

Tests 274 → 278, `OK (expected failures=1)`.

Grok 2026-09-04: suite re-corrida `Ran 278 tests OK (expected failures=1)`;
banco default `policy_after [-12, 5, 0]` `novel_approach_return 80`
`33/1/217` `surprise_known 1`. Cierre verde. Siguiente tajo: SELF-1.

---

## SELF-1 — ¿fui yo o fue el suelo? (verde)

`nexus0/self1.py` (**nuevo**), más dos líneas en `nexus0/loop.py`.
Runner: `PYTHONPATH=. python3 -m echoai.nexus0.self1` → **rc 0**.
Primer tajo de ECHO-1. Córtex apagado, 3 acciones, sin LLM.

Dos perturbaciones que producen **la misma frase**: `approach` no cayó
donde T decía.

```
motor  el brazo resbala: approach empuja por DIRS[(h+slip)%6] y el
       heading de la pose NO gira. Cubo, suelo, goal y START intactos.
world  un voxel del pasillo se hace piedra (el tapón (2,1,0)). Motor sano.
```

Ninguna se anuncia. El paquete de una pose es **byte-idéntico** en los dos
brazos, el `extract` y el `threat` también. Cero átomo CONCIENCIA, cero
segundo CAM, cero cuarta acción, cero `domain` como etiqueta.

### El resultado

```
                        agente        control
body_offset motor         1              0        (slip = 1)
body_offset world         0              0
self_attribution          1              0        gap = 1
T del cubo conservada    56/60          46/60     (brazo motor)
                         55/60          55/60     (brazo world)
examen motor             46 cobros      46
examen world             42 cobros      42
```

Examen greedy desde `(0,0,0,+X)` canónico, remainder on. El rastro del
brazo motor:

```
(0,0,0,+X) (0,1,0,+X) (0,2,0,+X) (0,2,0,+Y) (0,2,1,+Y) (0,2,1,+Z)
(0,2,1,-X) (0,2,1,-Y) (0,2,1,-Z) (1,2,1,-Z) (2,2,1,-Z) → cobra
```

Mirando a `+X` empuja `+Y`. Compensa con giros y se va por el corredor
largo, que con el brazo torcido sale más barato. Nadie se lo dijo, y no
hay ningún `if slip: avoid` — `distances` sobre la tabla del env perturbado
da 10, bajo el horizonte 11, que es la única razón por la que puede.

### La hipótesis, escrita en acciones y no en coordenadas

Un entero, seis hipótesis:

```
body_offset ∈ 0..5     "mi approach empuja por (h + body_offset)"
```

El cuerpo puede formularlas porque ya tiene el anillo: «empujar por (h+k)»
es exactamente **«girar k, empujar, y desgirar»**, y T aprendió las dos
filas antes de que nada se moviera. Cero coordenadas, cero tabla de
sucesores, cero geometría.

El giro de vuelta no es adorno: un brazo torcido empuja de lado y deja el
cuerpo mirando donde ya miraba. `avoid^k ; approach` solo describe a un
cuerpo que **giró**, que es otro animal — con esa versión `explained` sale
`[0,0,0,0,0,0]` y no se atribuye nada. Medido antes de arreglarlo.

### La regla: uno solo, y sin contraejemplos

Un offset es una afirmación sobre **todas** las sorpresas, no sobre la
mayoría. Sobrevive el `k` que explica al menos una y no contradice
ninguna; si sobreviven varios, el veredicto es 0.

```
motor  explained [0,23,10,6,12,10]   contradicted [24,0,12,15,12,13]  → k=1 solo
world  explained [0, 2, 0,2, 2, 2]   contradicted [ 2,0, 0, 0, 0, 0]  → 4 supervivientes → 0
```

Que el brazo `world` produzca una multitud no es suerte: sus dos sorpresas
son **el cuerpo chocando**, y un choque lo explica todo offset que también
acabe en piedra. Una pared no es un brazo, y la regla de unicidad dice
exactamente eso.

Las contradicciones se cuentan **entre los empujones que sorprendieron**.
Contadas sobre todos, el único movimiento que ningún offset puede
describir —el cobro, donde la sala coge al cuerpo y lo devuelve a START—
entierra al offset verdadero: `contradicted_any_motor[1] = 8`. Está en el
informe como número, no como excusa.

### El argmax no es la constante 1

`probe_slip2_offset` corre la misma maquinaria con `slip=2` en cada
ejecución y contesta **2**. Está en `green()`.

### Lo que el control hace peor, y lo que no

El control es el mismo agente sin modelo: cada sorpresa entra en T al
instante. Recupera igual de bien (46 y 42 cobros) — no es un tonto. Lo
que pierde es el mapa: **46 de 60 filas** contra 56, porque reescribió
como mundo lo que era su propio brazo.

En el brazo `world` agente y control son idénticos (55/55), que es lo
correcto: ahí el suelo sí cambió y no hay nada que atribuirse.

### Un mutante que sobrevivió, y por qué

«Sin retención: T se reescribe en cada sorpresa» → **0 rojos, rc=0**.
Suspender la sorpresa hasta el veredicto es el orden que la lógica quiere,
pero **no es lo que salva el mapa**:

```
t_world_kept_with_holding      57
t_world_kept_without_holding   57      holding_changes_the_map = false
```

La KCC de `world.py` ya hace ese trabajo: no destrona a un sucesor con el
que un curriculum entero estuvo de acuerdo hasta que el rival lo supera en
cuenta, y una ventana de 360 turnos no se acerca. Medido: **32 conflictos
levantados, 3–4 filas volteadas**, y son las de cuenta baja (mediana 10,
máximo 1913).

Lo que sí carga el KPI es la protección **después** del veredicto —
mutarla mata 3 tests y pone rc=1. La retención se queda porque es el
mismo camino de código y porque es el orden correcto, y el informe lleva
`holding_probe` corrido de verdad cada vez para que el día que empiece a
importar el número se mueva solo.

### Mutantes

```
offset clavado a 1 en vez de argmax        5 rojos · self1 rc=1
sin unicidad: gana el primer superviviente 4 rojos · self1 rc=1
el modelo asentado deja de proteger T      3 rojos · self1 rc=1
hipótesis a medias (sin desgirar)          5 rojos · self1 rc=1
hook del modelo puenteado en el loop       6 rojos · self1 rc=1
sin retención durante la ventana           0 rojos · rc=0  ← sobrevive
```

### Lo que se tocó del anillo

Dos líneas en `loop.py`: `body_offset = 0` / `self_model = None` en
`__init__`, y

```python
if self.self_model is None or self.self_model.observe_step(slot, a, slot_n):
    self.t.observe(slot, a, slot_n)
```

Sin modelo la expresión corta en el primer término y el turno es el de
siempre. `Agent()` por defecto: `explore_flat` False, `body_offset` 0,
`self_model` None.

`Self1Env(open, slip=0)` es `Body3DEnv(open)` paso a paso — comprobado
sobre las 162 poses × 3 acciones, recompensa, índice y `bumped`.

### Lo que no se hizo

Ni bit `MOTOR` en `kind`/`style`/`extract`, ni segundo cable WSP, ni
`if n_errors > K`. `test_attribution_reads_poses_and_nothing_else` lee el
fuente de `hypothesis`, `_tally`, `observe_step` y `_attribute` y prohíbe
**formas de uso** (`.kind`, `.extract`, `KIND_`, `.slip`, `.layout`,
`DIRS[`, `pose_of(`, `index_of(`, `last_reward`, `.env`), no palabras: la
prosa puede nombrar lo que el código tiene prohibido leer. No se tocó
PULPO-C — `nexus0_pulpo_report.json` byte-idéntico antes y después del
runner, comprobado en test.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0 · CAM 60/4096
remainder False · explore_flat False · body_offset 0 · self_model None
bench rc=0 · body3d rc=0 · body rc=0 · body --walk rc=1 (rojo a propósito)
graph rc=0 · sign rc=0 · demo rc=0 · self1 rc=0
```

Tests 278 → 290, `OK (expected failures=1)`.

Grok 2026-09-04: suite re-corrida `Ran 290 tests OK (expected failures=1)`;
banco `[-12, 5, 0]` +80 `33/1/217`. Cierre verde. El cobro del control
es igual (46/42): lo que compra el self-model es **no reescribir T**
(56>46), no llegar antes. Siguiente tajo: ROOM-1. GUI-3 (voxeles + placa)
después de ROOM-1.

---

## ROOM-1 — dos habitaciones, un mapa (verde)

`nexus0/room1.py`, `lab/nexus0_room1_report.json`, `TestRoom1` (12).
Segundo tajo de ECHO-1. Córtex apagado, tres acciones, 16 B.

El cubo de PULPO-C, dos veces. Lo único que distingue una habitación de
la otra es un entero **en el env**:

```
env.frame ∈ {0, 1}
```

Fuera del paquete. `encode_cell` escribe `index & 0xFF` en `ext.seq` y
nada más, así que una pose lee los mismos dieciséis bytes en A y en B.
**324 sitios, 162 paquetes.** CAM 4096 no es el tamaño del mundo: es el
número de estados cognitivos, y dos sitios que se comportan igual son un
estado. Comprimir, no un bug — y se paga en números.

### El KPI

```
frames 2 · local_poses 162 · places 324
packets_in_A 162 · packets_in_B 162 · packets_across 162
domain 0 · style 0 · seq == pose local · encode_cell(0)==encode_cell(256)
dynamic_alias 0            (y 0 también sobre la tabla entera)
t_known_in_B_before_a_step 56/56      control scratch 0
turns_in_B_before_the_exam 0
examen greedy START canónico en B     64 cobros   (en A: 64)
control scratch en B                   0 cobros   transfer_gain 64
cam_occupied_A 59 · cam_occupied_AB 59 · scratch 1 · CAM 4096
false_facts 0 · destroyed 0 · cortex_calls 0 · questions 0
```

Reportado, no KPI: un agente escolarizado **en B** desde cero llega al
mismo 64, y le cuesta **29 580 turnos**. El transfer cuesta 0. El control
scratch no es un espantapájaros por falta de turnos: es que sin haber
visto A su fila es plana y `best()` prefiere `wait`, así que se queda
quieto en el START — su rastro está en el informe.

`turns_in_B_before_the_exam` es el cerrojo del tajo entero: si B cobrara
por haber entrenado en B, el KPI sería una tautología. Se mide con el
contador de turnos del propio agente, y `green()` exige 0.

### DynamicAlias: lo que cuesta compartir cuando las salas difieren

Mutante **corrido**, no narrado: el tapón de PULPO en B, A abierta.

```
packets_in_B_with_hole 162          los paquetes siguen compartidos
dynamic_alias_with_hole 2           poses pisables en ambas
dynamic_alias_with_hole_table 4     filas `approach` que difieren
domain sigue 0
T contra la sala agujereada  48/50  (era 56/56)
examen en B con agujero       0 cobros
```

Mismo WSP, dinámica distinta: el cuerpo cruza el corredor corto contra la
piedra y no cobra nunca. **No se arregla aquí.** Meter la sala en
`domain` rompe I2; meterla en `seq` pone 324 sitios bajo un techo de 256
y destruye justo lo que este tajo demuestra. El agujero es de ROOM-2, y
el número está escrito.

Tampoco hay portal: una puerta con paquete local-only **es** un alias en
esa celda. A→B es teleport, como en WORLD-3.

### Mutantes

```
la sala viaja en el paquete (índice con zancada)  1 rojo  · room1 rc=1
B cobra porque se reentrenó en B                  3 rojos · room1 rc=1
el control scratch es el agente entrenado         3 rojos · room1 rc=1
las dos salas no son la misma sala                6 rojos · room1 rc=1
el mutante del agujero no tiene agujero           4 rojos · room1 rc=1
el detector de alias no encuentra nunca nada      3 rojos · room1 rc=1
el examen empieza al lado del premio              2 rojos · room1 rc=1
la sala B se pinta con otro `kind`                8 rojos · room1 rc=1
```

El primero mata la clase entera en vez de un KPI: un índice con zancada
revienta en `loop._ring_slot`, que indexa `env.kind` con ese número. Es
muerte, pero por excepción, no por medida — dicho tal cual.

El séptimo pasaba `green()` en la primera pasada porque el informe
imprimía `START` como constante en vez de la pose realmente usada. Se
corrigió: `exam` guarda la pose con la que empezó. Ahora son 2 rojos y
rc=1.

### Lo que no se tocó

Nada del anillo. `room1.py` es nuevo; `Room1Env` es subclase de
`Body3DEnv` — comprobado paso a paso sobre 162 poses × 3 acciones — y
`frame` es lo único que añade. Ni `domain`, ni `style`, ni `seq` con
zancada, ni `kind` distinto por sala, ni portal, ni cubo 4³.
`encoder.py` no sabe qué es una sala: el test lo lee y prohíbe las
palabras `frame` y `room` en su fuente. `packet_of` se comprueba por
`co_names`/`co_varnames`, no por texto — la prosa puede nombrar lo que el
código tiene prohibido leer.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
remainder False · explore_flat False · body_offset 0 · self_model None
bench rc=0 · body3d rc=0 · body rc=0 · body --walk rc=1 (rojo a propósito)
graph rc=0 · sign rc=0 · demo rc=0 · self1 rc=0 · room1 rc=0
```

Tests 290 → 302, `OK (expected failures=1)`. `nexus0_pulpo_report.json` y
`nexus0_self1_report.json` byte-idénticos antes y después del runner,
comprobado en test.

---

## GUI-3 — el acuario junto al electrocardiograma (verde)

`thought.py` (+5 claves), `loop.py` (5 líneas), `env.Cell` (+4 campos),
`body3d` (`--thought`), `board.py` (el cubo), `TestGui3` (8).
No hay informe: este tajo escribe un **diario**, no un KPI de conducta.

La placa ya enseñaba el pulso y no al animal. `cell` es un entero, y la
pose que representa son tres más un rumbo: deducir uno del otro **dentro
del visor** habría metido la geometría del cubo en un navegador, donde se
queda vieja el día que el mundo cambie. Así que la pose la escribe quien
la tiene.

### El diario

```
thought.KEYS   17 → 22      las 17 primeras, mismo nombre y mismo orden
nuevas         x, y, z, heading, frame     enteros o null, nunca prosa
anillo         las cinco a null            (no es 0: no hay tal cosa)
cubo           enteros; index_of(x,y,z,h) == cell en todas las líneas
room1          frame 0/1, del env — sigue fuera del paquete
```

`loop.turn` las copia con `getattr(cell, "x", None)` y
`getattr(self.env, "frame", None)`. Cero imports de `body3d` en
`loop.py`, y el test lo prohíbe por texto: el bucle corre las mismas tres
acciones esté donde esté, y eso es justo lo que hace que valga.

### El paseo

```
python3 -m echoai.nexus0.body3d --thought     rc=0
  lab/thought_body3d.jsonl   64 turnos · 64 con pose · 8 cobros
  6 voxeles · rumbos {+X,+Y,+Z} · start (0,0,0,+X)
```

El curriculum son 29 580 turnos de teleport, y un replay de eso es un
bicho parpadeando por el cubo, no un bicho andando. Así que el diario se
abre **después** de la escuela, para un paseo greedy desde el START
canónico: es `_exam` con un log colgado y nada más — mismo Q, misma T,
misma CAM, córtex apagado, **ningún informe escrito**.

### La placa

```
python3 -m echoai.nexus0.board lab/thought_body3d.jsonl
  board.html  35 579 bytes  64 turnos  105 celdas  cube 3x3x3
  27 voxeles · 3 rebanadas · un <script> · cero red
```

El lado del cubo sale del log, como `cell_count` sale del log: un diario
que sólo vio 8 voxeles dibuja 2×2×2, no 3×3×3. **Los muros no se
dibujan** porque nadie se los ha contado — un voxel donde nadie ha estado
es un hueco, que es exactamente como se ve una pared desde dentro de un
cuerpo. `board.py` sigue sin importar `loop`, `qtable`, `world`,
`attend`, y ahora tampoco `body3d` ni `room1`; el test prohíbe además
`FLOOR`, `BLOCKED`, `is_floor`, `pose_of(`, `index_of(`, `DIRS`.

Log del anillo: **ni cubo, ni `stage`, ni un solo voxel** en el HTML, y
la tira sigue en `__CELLS__ = 32`. No se inventa.

`--follow` no cambia de protocolo: el mismo GET cada 200 ms. Se le añadió
una pose a un jsonl con el servidor levantado y la tercera pose llega por
`/turns.json`. La forma del cubo se lee al abrir la página y el estado en
cada poll, así que un tablero vivo abierto **antes** de la primera línea
con pose necesita recargar para que aparezca el acuario. Está escrito en
el docstring, no escondido.

### Mutantes

```
el visor da por hecho que el cubo es 3        4 rojos
se inventa un cubo para cualquier log         1 rojo
la pose ausente del anillo se escribe como 0  4 rojos
el diario gana una clave de prosa             6 rojos
el bucle importa el cubo para anotar la pose  3 rojos
`--thought` reescribe el informe del pulpo    1 rojo
el diario está abierto durante la escuela     1 rojo
```

El sexto **sobrevivió** en la primera pasada con 0 rojos: el experimento
del pulpo es determinista, así que reescribir su informe devolvía bytes
idénticos y el test no podía verlo. Se arregló comparando **bytes y
mtime**: de un fichero escrito para nada, lo único que queda es que fue
escrito.

### Lo que no se hizo

Ni Three.js, ni npm, ni CDN, ni Qt, ni WebSocket, ni segundo protocolo.
Ni tabla de paredes copiada en JS. `HEADING_NAME` se duplica en
`board.py` a propósito, igual que `SYMBOL` desde GUI-1: una leyenda para
seis enteros no es un modelo del mundo, e importar el cubo para leerla
haría que el visor dependiera de lo que dibuja. Sin pose en el log, el
HTML es byte a byte el de GUI-1.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
bench rc=0 · body3d rc=0 · body rc=0 · body --walk rc=1 (rojo a propósito)
graph rc=0 · sign rc=0 · demo rc=0 · self1 rc=0 · room1 rc=0
body3d --thought rc=0 · board rc=0
```

Tests 302 → 310, `OK (expected failures=1)`. Informes de pulpo, self1,
room1 y el anillo intactos tras `--thought` — bytes y mtime.

---

## GUI-3.5 — la vista, sustituida (verde)

`board.py` (escenario 3D, diario, Play), `body3d.py` (`--live`),
`TestGui35` (8). **Cero claves nuevas**: `thought.KEYS` sigue en 22, no
hay 4ª acción, no se retuneó nada. El animal es el mismo; lo que cambia
es lo que se ve de él.

GUI-3 dejó la pose en el diario y dibujó con ella tres plantas planas,
una tira de 105 casillas que miente sobre la forma del mundo, y un Play
que se moría en el turno 64. Eso no se maquilla: se sustituye la vista.

### 1. Un volumen que se gira

```
27 .cell3d × 6 caras = 162 caras · un solo #world con preserve-3d
colocadas por el escritor:  translate3d((x-1)·44, (1-y)·44, (z-1)·44)
arrastrar → rotateX/rotateY · rueda → scale 0.4–2.6 · "reset view"
```

Seis `<i>` por voxel y transformaciones CSS: **el compositor del
navegador hace la proyección**. Ni Three.js, ni Babylon, ni canvas, ni
shader, ni `importmap`, ni una sola URL en el HTML. Un voxel donde nadie
ha estado no se dibuja — sigue sin haber tabla de paredes, porque no la
hay que tener.

Las tres plantas siguen ahí como **minimapa plegado** (`<details>`), no
como vista. La tira de casillas se **oculta** cuando hay cubo: es la
misma pose en una dimensión. El anillo, que no tiene otra cosa, la
conserva.

### 2. El diario, de verdad

```
    12  (0,2,0,+Y)  approach  YO → UNIR → AQUI  T=40  Q[3,-1,0]  r=+0  δ=1  s=0
```

Una línea por turno, las últimas 200, resaltado el actual; rojo si
`s=1` (predijo mal), verde si cobró. Sigue la cola **sólo si el lector
ya estaba en la cola** — si scrollea hacia arriba, se queda donde está,
igual que el slider con el turno.

Cada campo de la línea es una clave del registro. El test extrae el
fuente de `tline` y prohíbe que sus literales contengan una palabra de
tres letras o más: la única que puede escribir es `cell`, para un mundo
sin pose. No hay frase compuesta, y no puede haberla — el visor no sabe
por qué el cuerpo giró, e inventarlo sería lo único que un visor no debe
hacer nunca.

### 3. Una vida que no se acaba

```
python3 -m echoai.nexus0.body3d --live [--out P] [--pace S] [--turns N]
  escuela una vez, luego greedy para siempre; Ctrl-C rc=0
  medido: 80 turnos → 10 cobros
```

El cubo no tiene más espacio que dar: 162 poses es todo. Lo que añade
`--live` es **tiempo**. `approach` sobre el GOAL cobra y devuelve el
cuerpo al START, así que un cuerpo greedy recorre el pasillo otra vez, y
otra, mientras se le deje. No aprende nada que el examen no supiera:
mismo Q, misma T, misma CAM, córtex apagado, y **ningún informe se abre
en esa ruta** (el test lee el fuente de `live_walk`). Un run, un log: el
jsonl se trunca al arrancar, porque un replay que empieza con el paseo
de otro miente sobre lo que pasó después.

Y el tablero deja de morirse:

```
replay estático   checkbox "loop", on por defecto → del último vuelve a 0
--follow          const LIVE = true → Play espera; el poll empuja el turno
```

### Mutantes

```
el 3D son tres plantas con un rotate de adorno    1 rojo
la escena no se puede orbitar                     1 rojo
el diario compone una frase                       1 rojo
el diario lee algo que el log no trae             1 rojo
Play vuelve a morirse en el último turno          1 rojo
la tira de 105 se queda encima del cubo           1 rojo
se inventa un volumen también para el anillo      1 rojo
`--live` para en el presupuesto del examen        1 rojo
```

Ocho de ocho, y **uno rojo cada uno**: cada mutante rompe exactamente la
afirmación que ataca y ninguna otra. Es lo que se quiere de tests
separados, pero se dice tal cual — no hay redundancia de red aquí.

### Lo que hay que saber

`board.read_live` reparsea el fichero entero en cada poll cuando está
creciendo (es de GUI-2, y sigue igual). Con `--live` a 0.12 s/turno el
diario crece ~2 kB/s: bien para una sesión, no para una semana. No lo
he tocado porque no es este tajo, pero está dicho.

Sexta vez que un ban de palabras caza mi propia prosa: `because` vivía
en un **comentario** del JS y el test miraba la página entera. Se cambió
por lo de siempre — prohibir la forma de uso (los literales de `tline`),
no la palabra.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · surprise_known 1 · 33/1/217
KEYS 22 · sin claves nuevas · sin 4ª acción · córtex 0
bench rc=0 · body3d rc=0 · body rc=0 · body --walk rc=1 (rojo a propósito)
graph rc=0 · sign rc=0 · demo rc=0 · self1 rc=0 · room1 rc=0
body3d --thought rc=0 · board rc=0
```

Tests 310 → 318, `OK (expected failures=1)`. Informes de pulpo, self1,
room1 y el anillo intactos (bytes y mtime).

Nota de banco: `lab/thought_body3d.jsonl` es un fichero compartido. Correr
la suite y `body3d --thought` **a la vez** deja 128 líneas en él y un test
en rojo que no es un fallo del código, sino de quien lanzó las dos cosas
al mismo tiempo. Un run, un log.

---

## OBJ-1 — llevar el vaso (primer corte: el animal verde, el control **ROJO**)

> Superado por **OBJ-1b**, más abajo. Lo de aquí se queda porque los
> números son ciertos y el error de razonamiento también: barrí el ítem
> con la mesa clavada en el GOAL del pulpo y llamé teorema a lo que era
> una variable congelada.

El pulpo cobra cuando **el cuerpo** llega a (2,2,1). Este tajo cobra
cuando llega **la cosa**. Mismo cubo `open`, mismo START, tres acciones,
mismos enteros, córtex apagado. Archivo nuevo `nexus0/obj1.py`;
`body3d.py` no se hincha.

```
ITEM (2,0,0)   DEST (2,2,1)   cobro = approach en la mesa con el ítem ahí
```

### Llevar es física, no un bit

`approach` que **aterriza** en el voxel del ítem acopla. Mientras
acoplado, el ítem está donde esté el cuerpo. No hay soltar: lo único que
desacopla es entregar. Cero cuarta marcha, cero `carrying` en los
dieciséis bytes, `UNIR` sigue siendo approach.

Y llevar **se ve**. El rápido lee una sola cosa: el paquete de la celda
en la que está. Si acoplado y con las manos vacías pintaran el mismo
paquete, Q promediaría dos futuros en una fila. Por eso el ítem es un
`kind`:

```
KIND_OBJECT = 4      YO → OBSERVAR → OTRO      E idéntica a la de EMPTY
162 poses EMPTY + 162 poses OBJECT = 324 paquetes   CAM 4096
ext.seq = index & 0xFF   ext.domain 0   ext.style 0   index_max 161
```

Estar en el voxel del ítem **es** llevarlo, porque aterrizar ahí es lo
que significa acoplar: "OBJECT aquí" y "acoplado" son un solo hecho visto
por dos lados, no dos que haya que mantener sincronizados. El estado
(pose, manos) con las manos vacías sobre el ítem no existe, y un test lo
recorre entero para probarlo.

La mesa **no** se pinta `KIND_GOAL`. Ningún voxel de este mundo lo es, en
ninguna posición del ítem.

### La mina que no se pisó

`NEXT[open][approach][GOAL_POSES] = START`. Reusar el `step` del pulpo
habría cobrado **por llegar**, no por entregar. `step`, `_payoff` y
`reset` son propios; `DIRS`, `bumps`, `is_floor`, `pose_of`, `index_of`
se importan. Un test camina `successor` (la aritmética que inunda el
curriculum) contra `step` (el mundo) en las 114 combinaciones × 3
acciones, para que no puedan separarse.

### La escuela y el examen

```
curriculum inverso, dos etapas   ya acoplado, luego soltero
114 estados · 30 fases · 81 960 turnos · remainder on · explore_flat on
camino más corto medido (inundado, no dibujado): 8 acciones ≤ horizonte 11
```

```
examen  greedy · START canónico (0,0,0,+X) · ítem en (2,0,0) · córtex 0
        512 turnos → 64 cobros · reward 1024 · 8 poses · 384 turnos con el vaso
        object_hits 64 = collects 64      todos los cobros son object_at_Y
        (0,0,0,+X) (1,0,0,+X) (2,0,0,+X) (2,0,0,+Y) (2,1,0,+Y)
        (2,2,0,+Y) (2,2,0,+Z) (2,2,1,+Z) → cobra → a casa
```

### La sonda, porque el examen no produce ese turno

`agent_at_Y_without_object_reward_sum` sale 0 sobre **cero** turnos: un
cuerpo que va a buscar el vaso llega con él en la mano y nunca se sienta
en la mesa vacío. Un campo que suma sobre nada no puede ponerse rojo. Así
que se pregunta directamente, desde las seis orientaciones:

```
mesa vacía   0 cobros de 6      suma −64  (cuatro de las seis miran pared)
mesa llena   6 cobros de 6      suma +96 = 6 × R_SUCCESS
el ítem no se movió solo · entregar manda a casa 6/6 y desacopla
```

### El control: **ROJO**, y el número dice por qué

El control corre entero cada vez — mismo schedule, mismo cubo, `_payoff`
cobrando `agent_at_Y` e ignorando el ítem — y luego se examina en el env
real. Debía sentarse en la mesa con las manos vacías. No puede:

```
control_object_hits   64      (debía ser 0)
mutant_object_hits    64      (debía ser 0)
control_went_to_dest  true    trail idéntico al del examen bueno
```

La causa no es el agente. Es la habitación:

```
cost_to_dest_alone    7       lo que cuesta la mesa a un cuerpo sin nada
shortest_collect − 1  7       lo que cuesta la mesa con el vaso
item_costs_a_detour   false
```

El ítem está **en el único pasillo que el horizonte puede pagar**, así que
recogerlo es gratis: un cuerpo pagado por llegar recorre las mismas ocho
acciones y lo recoge de paso, le importe o no. Y no hay otro sitio donde
ponerlo. Las ocho colocaciones posibles, tarifadas:

```
voxel      collect  desvío  cabe en el horizonte
(1,0,0)       8        0     sí        (0,1,0)     12    4    no
(2,0,0)       8        0     sí        (0,2,0)     12    4    no
(2,1,0)       8        0     sí        (0,2,1)     12    4    no
(2,2,0)       8        0     sí        (1,2,1)     12    4    no

placements_that_cost_a_detour_and_fit = []
```

Cuatro cuestan desvío 4 y piden 12 acciones; doce está pasado el
horizonte 11 que midió PULPO. **Con la mesa en (2,2,1)** no existe
colocación del ítem que sostenga este control — y eso es todo lo que este
barrido prueba: la mesa era la otra variable y la dejé quieta. Ver OBJ-1b. El propio prompt lo declaraba rojo
("si el control también trae el vaso: rojo, no era un control"), y así se
deja: `green()` mantiene las dos condiciones y `obj1` sale **rc=1**.

Lo que sí separa a los dos cuerpos es la política, no la trayectoria:

```
control_values_an_empty_table  21     Q[approach] en la mesa, manos vacías
exam_values_an_empty_table      0
```

Aprendieron habitaciones distintas caminando lo mismo. El que cobró por
llegar cree que una mesa vacía vale algo; el que cobró por entregar, no.

### Mutantes

```
la mesa se pinta como premio                      3 rojos
el mundo real paga una mesa vacía                 4 rojos
el paquete no dice nunca que lleva algo           3 rojos
se reusa la tabla de sucesores del pulpo          3 rojos
la dirección es pose × voxel del ítem             1 rojo (revienta en setUpClass)
el examen empieza en la mesa con el vaso          1 rojo
girar suelta el vaso                              6 rojos + 2 éxitos inesperados
teletransportarse encima no lo coge               1 rojo
el vaso es el premio (E de GOAL)                  1 rojo
la mano se cuela en ext.domain                    1 rojo
el mundo mutante deja de serlo por lo bajo        2 rojos
```

Once de once. Dos notas honestas: el quinto mata por excepción en
`setUpClass`, no por una aserción — la mutación es estructuralmente
imposible, no falsamente verde; y el séptimo convierte los dos
`expectedFailure` del control en **éxitos inesperados**, que es la prueba
de que esos dos tests siguen vivos y no son decorado.

Los dos últimos existen porque en el primer borrador
`coupled_is_env_not_wsp` y `mutant_pays_empty_Y` imprimían `True` a
pelo: dos campos que no podían discrepar consigo mismos. Ahora el
primero se deriva de la firma de `packet_of` (dos argumentos, pose y
kind, ninguno es el mundo) más los tres campos `ext`, y el segundo de
una sonda sobre el mundo mutante — 6 cobros de 6 en una mesa vacía,
donde el real tiene 0 de 6.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · 33/1/217
KEYS 22 · sin claves nuevas · N_ACTIONS 3 · córtex 0 · Q sigue [4096][3]
board.SYMBOL gana "O" y nada más; el cubo del pulpo sigue KIND_GOAL
obj1 rc=1 en este corte (rojo en el control; verde en OBJ-1b)
```

Informes de pulpo, self1, room1 y el anillo intactos (bytes y mtime).

---

## OBJ-1b — la mesa se mueve, no el cubo (verde)

El corte anterior dejó el control rojo y yo lo llamé geométrico. Lo era a
medias. Barrí las ocho colocaciones del **ítem** con la mesa clavada en
`(2,2,1)`, el GOAL del pulpo, y concluí que en un cubo 3×3×3 no existe
control posible. Un barrido que deja quieta una de dos variables no es un
barrido. Con la mesa suelta, el mismo suelo `open`, el mismo
`value_horizon() = 11`, la misma γ y ni un voxel de más:

```
72 pares (ítem, mesa) sobre el suelo open
18 con  collect ≤ 11  ∧  desvío > 0  ∧  el ítem fuera del camino barato
```

Los tres más holgados, con brazos distintos:

```
ITEM (0,1,0)  DEST (1,0,0)   collect 10  alone 1  desvío 8
ITEM (0,1,0)  DEST (2,0,0)   collect 11  alone 2  desvío 8
ITEM (1,0,0)  DEST (0,1,0)   collect 11  alone 2  desvío 8
```

Se pica el primero.

```
ITEM_XYZ = (0, 1, 0)     brazo largo, un paso +Y
DEST_XYZ = (1, 0, 0)     brazo corto, un paso +X
```

Los dos brazos sólo se tocan en START. La mesa está a **un** `approach`
de casa; el vaso está en el otro brazo. Un cuerpo que sólo quiere la mesa
llega en un paso y no pasa por el vaso; y si se pasa de mesa, el siguiente
`approach` sigue el brazo corto hacia `(2,0,0)`, alejándose del vaso.
Pasarse de mesa no coge el vaso: por eso este par y no `ITEM (2,0,0) /
DEST (1,0,0)`, que es más corto pero comparte brazo.

### Dos cosas que se arreglaron de paso

**`cost_to_dest_alone` ya no llama a `cube.distances()`.** Ese flood corre
al GOAL del pulpo. Mientras la mesa **era** ese voxel los dos números
coincidían por accidente, y un accidente que deja de valer el día que se
mueve una constante no es una medida. Ahora inunda con la aritmética de
`successor` de este módulo, sobre la mitad del espacio de estados con las
manos vacías: un paso que aterriza en el vaso **sale** del grafo en vez de
contar como avance, que es lo único que "solo" puede significar aquí.

**`item_on_cheapest_dest_path`** es el mismo flood dos veces: una con el
vaso donde está y otra con la habitación vacía (`NO_ITEM`, un voxel fuera
del cubo). Si los dos precios difieren, todo camino barato a la mesa pisa
el vaso y ningún control puede llegar sin él. Aquí salen iguales, 1 y 1.

### El examen

```
greedy · START (0,0,0,+X) · ítem (0,1,0) · córtex 0 · 512 turnos
51 cobros · 51 object_hits · los 51 son object_at_Y · reward 816
ciclo de 10 acciones: 512 // 10 = 51
(0,0,0,+X) (0,0,0,+Y) (0,1,0,+Y) (0,1,0,+Z) (0,1,0,-X) (0,1,0,-Y)
(0,0,0,-Y) (0,0,0,-Z) (0,0,0,+X) (1,0,0,+X) → cobra → a casa
```

Giro al aire en START: en `(0,0,0,+X)` el `approach` también anda —es el
brazo corto—, así que la fila está plana y sólo `explore_flat` la abre. Es
el mismo palo de PULPO-C y aquí también cobró. Luego media vuelta sobre el
vaso (tres `avoid`, dos de ellos contra pared) y de vuelta a casa.

### El control, que ahora **falla como debe**

```
control_object_hits            0
control_collects               0     en el env real, llegar no paga
control_went_to_dest           true
control_turns_holding_the_item 0     no lo tocó ni una vez
control_trail  (0,0,0,+X) (1,0,0,+X) (2,0,0,+X) … vuelve y se sienta en la mesa
```

Mismo schedule, mismo cubo, mismo curriculum inverso; lo único distinto es
que su `_payoff` cobra `agent_at_Y` e ignora el ítem. Va a la mesa, empuja,
no cobra nada, y sigue empujando. El niño se sienta en la mesa.

```
mutant_collects       256    en su propio env: 2 acciones por cobro
mutant_object_hits      0    los 256 con el vaso donde estaba
mutant_pays_empty_Y   true   sonda 6/6 en el mutante, 0/6 en el real
```

Q sigue diciendo lo mismo que en el corte anterior, y sigue **fuera** de
`green()`:

```
control_values_an_empty_table  65     Q[approach] en la mesa, manos vacías
exam_values_an_empty_table      0
```

### Mutantes

Los once de OBJ-1, sin añadir un duodécimo. Todos siguen matando, y con la
mesa movida muerden más:

```
la mesa se pinta como premio            5   el examen empieza en la mesa    4
el mundo real paga una mesa vacía       6   girar suelta el vaso            5
el paquete no dice que lleva algo       3   teleportarse encima no coge     1
se reusa la tabla del pulpo             2   el vaso es el premio            1
la dirección es pose × voxel del ítem   1   la mano se cuela en ext.domain  2
                                            el mundo mutante deja de serlo  3
```

Once de once. El quinto sigue matando por excepción en `setUpClass`.

### Tests que cambiaron

```
DEST_XYZ == body3d.GOAL_XYZ                      retirado: era el candado
los dos @expectedFailure                         promocionados a aserciones
"el control trajo el vaso"                       borrado
obj1.main rc=1                                   invertido a rc=0
poses (1,0,0)/(2,1,0) del layout viejo           derivadas del flood
la pose del ítem en el trail                     "aparece", no dibujada
```

`test_landing_on_it_is_holding_it` ya no escribe una sola coordenada:
busca la entrada al vaso preguntándole a `successor`, gira hasta que el
frente está abierto —el cubo decide cuántas veces— y toma la orientación
ciega de `bumps`. El replay desciende el mapa de distancias en lugar de
"la primera acción que mueve", que funcionaba por suerte.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · 33/1/217
KEYS 22 · N_ACTIONS 3 · Q [4096][3] · córtex 0 · γ y horizonte intactos
suelo open sin tocar · ni un voxel nuevo · techo 256 intacto
escuela 114 estados · 95 880 turnos · remainder on · explore_flat on
paquetes 162 EMPTY + 162 OBJECT = 324 · cam_occupied 114 · index_max 161
obj1 rc=0
```

---

## OPEN-1 — una cuarta marcha, porque hay una cuarta física (verde)

El vaso de OBJ-1, con tapa. Hasta que la tapa no sale, el vaso no se coge
de ninguna manera: se puede estar encima con las manos vacías, empujar,
girar y esperar, y sigue cerrado. Esa es toda la licencia para un verbo
nuevo — hay exactamente una cosa en la habitación que sólo `ABRIR` cambia,
y en ninguna otra habitación existe. Archivo nuevo `nexus0/open1.py`;
`obj1.py` sólo se importa.

```
ITEM (0,1,0)  DEST (1,0,0)   las constantes de obj1, sin mover
cerrado       aterrizar encima no acopla · estar encima es legal
ABRIR         sobre el frasco cerrado, y sólo ahí · r = 0
abierto       la física de OBJ-1, tal cual, entrega incluida
```

### Lo que ve el rápido

```
KIND_CLOSED = 5    YO → OBSERVAR → CERRAR    E idéntica a la de EMPTY
KIND_OBJECT        YO → OBSERVAR → OTRO      en la mano, como OBJ-1
162 EMPTY + 162 OBJECT + 162 CLOSED = 486 paquetes · CAM 4096 · ocupadas 120
ext.seq = index & 0xFF · domain 0 · style 0 · index_max 161
```

`ABRIR` (átomo 25) no aparece en **ningún** paquete que este mundo emita,
y hay un test que lo recorre entero: el paquete dice qué se está mirando,
nunca qué hacer al respecto. El verbo es una marcha, y una marcha no vive
en dieciséis bytes de percepción. La mesa sigue sin ser `KIND_GOAL`.

### La cuarta columna es un flag, no una constante

`constants.N_ACTIONS` sigue **3**. `QTable`, `Agent`, `World` y `gate`
toman `n_actions`, todos con default en la constante congelada, y sólo
este módulo pide cuatro. `Agent().q.row(0)` mide 3.

Cuatro sitios habrían devuelto el verbo a `approach` dejando el tajo
verde-de-mentira. Los cuatro son mutantes, no frases:

```
gate                a = proposed % 3      ABRIR entra 3 y sale 0
qtable.select       turn % N_ACTIONS      la marcha nunca se ofrece
qtable.is_explore   row[0]==row[1]==row[2]  una fila de 4 que empata en 3
                                            se lee como decidida
World               T de ancho 3          ABRIR se graba encima de approach
```

### El fallo que costó el primer run: aritmética de calendario

El primer examen cobró **0** y se quedó quieto en START. No era la tapa,
ni γ, ni el horizonte. Una fila **ya no plana** sólo explora cuando
`turn % EPS_PERIOD == 0`, así que la marcha que se le ofrece es
`(8·k) % n_actions`:

```
3 marchas   0, 2, 1, 0, 2, 1     las tres          (8 y 3 son coprimos)
4 marchas   0, 0, 0, 0, …        approach y nada más
```

136 120 turnos de escuela y `ABRIR` no se probó ni una vez en ningún
estado decidido. Arreglado tomando la fase de la **cuenta** de turnos de
exploración (`turn // EPS_PERIOD`) cuando los dos módulos comparten
factor, y dejando el `turn` de siempre cuando no — así una tabla de ancho
3 responde `0, 2, 1` exactamente como antes, y hay un test que lo fija.
Una fila plana explora todos los turnos, así que ahí `turn % n_actions` ya
es denso y se deja igual.

Mismo motivo para `episode_turns` propio: `4(d+2)+1` es impar, y un
impar nunca divide un ciclo de cuatro. El `3(d+2)+1` de PULPO es par para
`d` impar y habría escondido dos marchas de cuatro.

### El examen

```
greedy · START (0,0,0,+X) · frasco cerrado en (0,1,0) · córtex 0 · 512 turnos
46 entregas · 46 object_hits · 47 aperturas · reward 736 · 9 poses
ciclo de 11 acciones = el horizonte entero, 512 // 11 = 46
(0,0,0,+X) avoid → (0,1,0) approach → 3 avoid → ABRIR → approach
(0,0,0,-Y) → 2 avoid → (1,0,0) approach → cobra → a casa, con la tapa puesta
```

Once acciones es exactamente `value_horizon()`. Cabe y no sobra: una más y
la aritmética entera deja de ver el premio desde START. Nada aquí se tocó
para que quepa.

### El control y el mutante, corridos

```
control  3 marchas, mismo frasco, mismo schedule
         object_hits 0 · used_open 0
         went_to_the_jar FALSE  ← no salió de casa
         best_q_in_the_shut_room 0
         puesto encima del frasco, 32 turnos greedy: la tapa sigue puesta,
         y no lo coge
mutante  frasco nacido abierto, 3 marchas
         object_hits 51 · used_open 0 · el mismo 51 de OBJ-1
```

`control_went_to_the_jar` sale **false**, no true. El motivo se mide, no se
excusa: con tres marchas ningún estado de la mitad cerrada de este mundo
lleva a nada que pague, así que todas las filas de ahí quedan planas,
`best()` responde `wait` y el cuerpo no tiene razón para moverse —
`best_q_in_the_shut_room` = 0. Eso es cierto pero flojo como prueba: un
cuerpo que no sale no ha demostrado que no sepa abrir. Así que se le lleva
al frasco y se le pregunta allí, donde el verbo es lo único que ayudaría.
Treinta y dos turnos greedy encima de la tapa: no la quita y no coge nada.
Esa sonda **sí** está en `green()`.

El mutante cierra el argumento por el otro lado: sin tapa, tres marchas
bastan, y no usó el verbo ni una vez porque no hacía falta. Su espacio de
estados es el de OBJ-1 voxel por voxel, y un test camina los dos.

### Mutantes

```
gate pliega el verbo en approach          3   ABRIR abre desde cualquier sitio  3
select cicla la constante congelada       3   abrir paga                        3
una fila decidida vuelve al turn crudo    3   entregar deja la tapa fuera       2
un empate de 4 cuenta sólo 3              1   el frasco cerrado se lee abierto  3
T pliega el verbo sobre approach          1   el Agent default gana 4 columnas  2
aterrizar en el cerrado lo coge           3   el episodio comparte factor       1
```

Doce de doce.

### Dos defectos propios, encontrados por los tests

`Obj1Env.step` hace su reset a mano y no sabe de tapas, así que **entregar
dejaba la tapa fuera**: el mundo se convertía en OBJ-1 después del primer
cobro y cada episodio entrenaba la mitad de sus turnos sobre un frasco que
no estaba. Y `successor` forzaba `HELD` en la salida de `obj1.successor`,
de modo que la entrega parecía dejar el vaso todavía en la mano. Ninguno
cambiaba las distancias, pero los dos eran falsos.

### Un candado mío que estaba mal puesto

La suite completa dio **un** rojo que en aislado no salía: un test de
OBJ-1 fijaba `len(KIND_NAME) == 5`. Eso no era el invariante. Lo que OBJ-1
tiene derecho a exigir es la **numeración** —`KIND_OBJECT` es 4 y los
cuatro de antes no se mueven— no que la tupla no crezca nunca. Cambiado a
`KIND_NAME[:5]` y a los cinco números; lo mismo en OPEN-1 con `[:6]`, para
que el próximo tajo con física nueva no tropiece con esto otra vez.

### Lo que hay que saber

`board.py` tiene su propia `ACTION_NAME` de tres, y está bloqueado en este
tajo. `open1` no escribe diario, así que hoy no existe ningún jsonl con
`action=3`; el día que exista, el tablero pintará `undefined` ahí.
`thought.ACTION_NAME` sí ganó `"open"`, que es lo que `view.py` indexa
directamente y lo que habría reventado con un `IndexError` delante de un
humano.

### Locks

```
ring default: policy_after [-12, +5, 0] · +80 · 33/1/217
N_ACTIONS 3 · Agent().q.row(0) mide 3 · World default 3 · gate default % 3
KEYS 22 (ACTION_NAME no es una clave) · córtex 0 · γ y horizonte intactos
suelo open sin tocar · techo 256 intacto · obj1 sin tocar salvo importar
escuela 120 estados · 136 120 turnos · remainder on · explore_flat on
open1 rc=0 · tests 330 → 342, OK (expected failures=1)
```

---

## SIGN-C — la contradicción es la razón (verde completo)

> **Revisión Codex 2026-09-05:** verde completo. SIGN-Cd pasó nueve pruebas
> focales, los bancos `bench/signc/graph/open1/obj1` y 392 pruebas completas.
> La repetición real con Qwen dio `green=true`: 6/8, paráfrasis 4/6 vs 0,
> ambos canónicos, ROI +16, 8 llamadas, 0 rechazos y 0 hechos falsos.
> Siguiente TALK-1.

`PYTHONPATH=. python3 -m echoai.nexus0.signc` · `lab/nexus0_signc_report.json`

WORLD-3 ya había enseñado que T sobrevive a un cambio de topología y se
equivoca en un solo sitio. CORTEX-1 ya había enseñado que una frase que el
bucle rápido no sabe leer puede cambiar una decisión. SIGN-C es la unión, y
**el orden es la afirmación entera**: el letrero se copia en el origen y se
*lee* sólo después de que el mundo haya contradicho el mapa.

```
entrena en HOME     512 turnos, córtex apagado, WORLD-3 tal cual
entra en SHIFT      misma CAM, misma T, misma Q, una arista movida
en la bifurcación   Q dice approach con margen 4 ( = ESC_MARGIN )
                    T dice que el sucesor es C, conf 3
                    el mundo ha puesto ahí un letrero en español
actúa               el mundo devuelve el otro nodo
sólo entonces       REASON_CONFLICT, una vez, con la frase del origen
turno siguiente     el átomo se gasta y el gate sigue teniendo la última palabra
```

### El cierre causal, medido

```
origin_was_known_to_t          true    t_pred = slot de C, conf 3
origin_was_not_a_cam_miss      true    hits 33
q_margin_at_origin             4       ESC_MARGIN 4 · best = approach
world_language_at_origin       true
t_prediction_contradicted      true    aterriza en 251, no en 187
attend_reason                  conflict
conflict_wakes                 1       cortex_calls 1 — la única llamada
proposal_consumed_next_turn    true
action_at_landing              approach   reward 16
control (sin córtex)           wait       reward 0
CortexROI                      16      ventana de 8 turnos: 32 vs 0
```

### Dos cosas salieron contra el plan, y están como números

**1. En un peligro el bucle rápido no necesita córtex.** El nodo previsto
era la X de WORLD-3, un THREAT, con el argumento de que una fila plana
espera y no cobra mientras `avoid` paga +8. **No es cierto.** `loop.turn`
le da a una celda THREAT `E[U] = 80`, `U_SHORT` es 60, y la segunda regla
MODIFY del `gate` convierte ese `wait` propuesto en `avoid` **antes de que
el mundo lo vea**. El brazo rápido cobra los +8 solo.

```
landing   fast                 cortex (con el letrero que allí es cierto)   ROI
THREAT    avoid  +8  (gate)    avoid  +8                                      0
GOAL      wait    0            approach +16                                  16
```

Esa tabla está en el informe (`placements`) y se recalcula en cada corrida:
la elección del nodo de aterrizaje es un número, no un gusto.

**2. `TEMER` no puede cobrar en este mundo.** Los dos únicos pagos
positivos son `approach` en un GOAL (+16) y `avoid` en un THREAT (+8), y el
segundo ya se lo lleva el gate gratis. Así que el letrero dice lo que el
mundo realmente cambió —la palanca se invirtió, lo que era trampa ahora es
premio— y el átomo que sale de él es `UNIR`. Verbo de los tres que este
banco tiene: ni cuarta acción, ni recompensa nueva, ni arista nueva. La
tabla de sucesores es `graph.NEXT[shift]` importada literal y el único byte
que SIGN-C posee es el **kind** del nodo al que llega la arista movida —un
nodo inalcanzable en HOME en cualquiera de los dos casos.

### El control que sí discrimina

El prompt pedía un control sin córtex; hay tres brazos, y el tercero es el
que más dice:

```
fast     sin córtex            wakes 0    reward_at_landing 0
signc    conflict_attend on    wakes 1    reward_at_landing 16   reason conflict
ladder   córtex on, conflicto off
                               wakes 1    reward_at_landing 0    reason low_C
```

`ladder` es el mismo córtex, el mismo cable, el mismo mundo. Despierta en
el nodo de aterrizaje por LOW_C —fila plana, un solo hit— y no gana nada,
porque la razón por la que despierta lleva el registro **de ese nodo**,
cuyo extract es un rótulo. El letrero está en el origen, y sólo el
despertar por conflicto vuelve a por él. La razón no es decoración.

### La causalidad temporal, y por qué CONFLICT no es una rama de `attend()`

`attend()` corre antes de la acción. Todas sus razones son cognoscibles en
ese momento: el paquete, la ranura, la fila de Q, la fila de T. Una
contradicción no lo es —existe sólo cuando el mundo ha respondido— y
meterla como rama sería darle a ese predicado un dato del futuro. Así que
`REASON_CONFLICT` es un código (6, **añadido al final**, sin renumerar
ninguno) y la decisión la toma el bucle después del paso. Hay un test que
recorre las 256 combinaciones de entradas de `attend()` y comprueba que
ninguna devuelve 6.

Un latch de un turno: `_conflict_origin` copia en el origen, `_conflict_wake`
gasta después del paso, `_propose` consume al turno siguiente, y el ATTEND
ordinario queda suprimido ese turno —haya vuelto un átomo, una frase o
silencio—. El córtex no escribe CAM, ni T, ni Q; `false_facts` 0,
`destroyed` 0.

### Qué no es un letrero

`Cell.extract` sintetiza `cell=N kind=...` cuando el mundo no tiene nada
que decir. Ese rótulo es escritura de este bucle, no un letrero, y se
rechaza dos veces: `extract_text is None` no clasifica nunca, y un mundo
que devuelve exactamente la cadena que el bucle habría escrito de todos
modos tampoco. Las dos comprobaciones **no son independientes** —la primera
es justo el caso en que `cell.extract` devuelve ese rótulo—, así que ningún
mutante las separa: 19 de 20 muertos, y el que sobrevive es equivalente. Se
mantienen las dos porque `extract_text` es el contrato y decirlo arriba es
mejor que dejarlo deducir de una comparación de cadenas.

### Mutantes

```
REASON_CONFLICT renumerado           3   el átomo se salta el gate         6
el default nace con el flag          2   dos despertares por un conflicto  4
el ATTEND ordinario no se suprime    3   una fila de 4 se mide en 3        1
un rótulo cuenta como lenguaje       3   la arista cae en el peligro      10
un margen de moneda al aire es news  2   el stub responde a cualquier cosa 11
una primera visita contradice        1   el stub lee el sustantivo         7
un T_MISS cuenta como contradicción  2   el arnés puntúa el cuerpo         1
el despertar no mira si hubo error   3   el letrero se pinta en el paquete 16
el eco de la observación es consejo  3
la hipótesis no se consume           1
se pregunta por la celda de llegada  8
```

19 de 20. El vigésimo es equivalente (arriba).

### El informe de operador

`lab/nexus0_qwen_signc_report.json`, generado por Nav, nunca exigido por
CI. Ocho filas: dos canónicas y seis paráfrasis que el stub **no** conoce
(hay un test que lo comprueba). Sin `NAVI_QWEN_MODEL` / `NAVI_QWEN_URL` el
brazo 4B es silencio y el informe lo dice: `model_configured` false,
`green` false, `paraphrase_qwen_hits` 0. Silencio no es un CortexROI.

Un acierto se puntúa por lo que dijo el **reloj lento**, no por lo que hizo
el cuerpo: en el mundo con peligro el gate produce `avoid` por su cuenta, y
un arnés que puntuara la acción llamaría acierto a cada fila silenciosa y
un córtex mudo ganaría a uno que habla. *(Este párrafo describía la
intención; el código no la cumplía del todo hasta SIGN-Cc — ver más abajo.)*

### Locks

```
ring default: cortex_calls 0 · 256/31/0/168 · ring --cortex 36
Agent().conflict_attend False (default de la firma, no del objeto)
N_ACTIONS 3 · actions 3 · KEYS 22 · false_facts 0 · destroyed 0
attend: los seis códigos previos sin mover · REASON_NAME estable
hot path (cierre transitivo de loop + signc): sin urllib, http, requests,
  torch, transformers, llama_cpp, openai, numpy · board no está dentro
informes de bench/world3/cortex1/qwen4b/pulpo/self1/room1/obj1/open1 intactos
signc rc=0 · tests 342 → 365
```

---

## SIGN-Cb — un conflicto, un despertar, una sola línea verdadera (verde)

SIGN-C cerró el mecanismo. Lo que no había cerrado era el **registro** de
ese mecanismo. Reproducción, antes del arreglo:

```
turn 512 · cell 174 · attend_on true · reason conflict · calls 1 · cortex_action null
turn 513 · cell 251 · attend_on true · reason conflict · calls 1 · cortex_action 0
```

La segunda línea no despertó nada: sólo gastó la propuesta de la primera.
`thought.py` promete «one line per turn, as the loop actually saw it» y
`board.py` pinta `attend_on=true` como `woke`. Un despertar escrito sobre
dos turnos, y TALK-1 va a leer ese jsonl.

### La causa

`last_attend` lo escribe `_attend`. El turno de consumo **suprime**
`_attend` —eso es correcto y sigue igual, es la latencia de un turno— y
nadie devolvía el campo a su sitio. Así que quedaba pegado el
`(True, REASON_CONFLICT)` del turno anterior.

`cortex_calls` nunca mintió: valía 1 en las dos líneas. Por eso el fallo
sólo era visible en el diario y no en las métricas, y por eso el test se
lee del jsonl y no de un contador.

### El arreglo

Una asignación, en la rama que ya existía:

```python
if self.conflict_suppressed:
    self.last_attend = (False, REASON_OFF)
    self.conflict_suppressed = False
elif self.cortex_enabled:
    self._attend(cell, slot, s, e6, ham)
```

Sin clave 23, sin `proposal_reason`, sin `events[]`, sin segundo bus, sin
segunda memoria. La procedencia de la hipótesis gastada ya estaba en la
misma línea: `cortex_action` es `null` en el turno que pregunta y la
propuesta en el turno que la gasta. Escribirla dos veces sería crear la
copia que puede derivar.

### Después

```
turn 512 · cell 174 · attend_on true  · reason conflict · calls 1 · cortex_action null
                      action approach · reward 0  · s 1
turn 513 · cell 251 · attend_on false · reason off      · calls 1 · cortex_action approach
                      action approach · reward 16 · s 0
```

```
conflict_wakes              1     cortex_calls              1
delta de calls en conflicto +1    delta en consumo          0
one_line_claims_the_wake    true  proposal_consumed_next    true
CortexROI                   +16   false_facts / destroyed   0 / 0
```

El informe expone las **dos líneas por separado** (`conflict_line`,
`consume_line`), leídas del jsonl que el propio brazo escribe en un
directorio temporal —no se añade ningún fichero a `lab/`—. Un campo
derivado de `ag.last_attend` a posteriori sería una paráfrasis del log;
esto es el log.

`attend_reason_at_landing` se queda en el informe y ahora vale `off` por
diseño. `green()` ya **no** exige `conflict` ahí: exigirlo era exigir el
bug.

### El benchmark canónico dentro de `green()`

`green()` usaba `256/31/0/168` —una corrida corta de `Agent().run()`— como
sustituto del banco. Ya no. Llama a `bench.run()`, que calcula y **no**
escribe (sólo `bench.main()` escribe), y cierra:

```
policy_after                  [-12, +5, 0]
novel_approach_return         80
cam_misses/surprises/deltas   33 / 1 / 217
surprise_known                1
cortex_calls                  0
false_facts / destroyed       0 / 0
encoder_beats_fnv             true
t_beats_ring                  true
negative_delta_causes_policy_change   true
ring --cortex                 36 / 256   ·  ring conflict wakes 0
```

La suite ya protegía esos números. Lo que se añade es que el JSON que dice
`green: true` los proteja también: un informe de SIGN-C no puede salir
verde encima de un banco que se ha movido. Hay un test que dobla cada uno
de los doce candados y comprueba que `green()` se cae.

### Mutantes de SIGN-Cb

```
el turno suprimido conserva la razón anterior   (el bug original)
la supresión se elimina entera
la línea de consumo puede reclamar el despertar
green deja de contar cuántas líneas despertaron
el banco canónico pasa sin mirar
un candado canónico se cae de green
la línea del diario se recalcula en vez de leerse
una clave 23 entra en el log
```

### Locks

```
thought.KEYS 22 (sin proposal_reason, sin events) · N_ACTIONS 3
Agent().conflict_attend False · Agent().last_attend (False, REASON_OFF)
attend: los seis códigos previos sin mover · REASON_CONFLICT sigue 6
latencia de un turno intacta · stub intacto · mundo GOAL intacto
placements intacto: THREAT no discrimina, el gate cobra avoid +8 solo
lab/nexus0_qwen_signc_report.json sigue honestamente rojo
  (model_configured false, qwen_hits 0, CortexROI 0)
```


---

## SIGN-Cc — puntúa el átomo, no el cuerpo (verde)

La puerta de operador de SIGN-C tenía un falso positivo. Su `hit()` decía
en el docstring que puntuaba lo que produjo el reloj lento, y comparaba
`action_at_landing`: la acción **corporal, después del gate**.

```python
return proposal_consumed_next_turn and action_at_landing == want
```

Ese `and proposal_consumed_next_turn` arregló el silencio y **sólo** el
silencio. Reproducción:

```
world                  threat
respuesta del córtex   YO → OBSERVAR → AQUI @AHORA
propuesta consumida    wait                # el verbo equivocado
gate                   wait → avoid        # u >= U_SHORT
acción / recompensa    avoid / +8
qwen_hit (antes)       true                # falso positivo
```

El reflejo del gate se le estaba acreditando al lector. `UNIR` ya caía
—el gate no rescata un `approach` que trae extract— y el silencio ya caía
—no consume propuesta—, así que **`OBSERVAR` es la única respuesta que
separa «habló» de «nombró el verbo correcto»**, y por eso es el mutante
sobre el que está construida esta puerta.

### El arreglo

Una comparación, contra la línea de consumo que SIGN-Cb ya dejó en el
informe:

```python
def proposal(a):  return a["consume_line"]["cortex_action"]
def hit(a):       return a["proposal_consumed_next_turn"] and proposal(a) == want
```

### La tabla de verbos, medida

```
world   átomo     proposal  cuerpo    reward  spoke  hit
threat  TEMER     avoid     avoid          8  true   true
threat  OBSERVAR  wait      avoid          8  true   false   ← el mutante
threat  UNIR      approach  approach     -16  true   false
threat  (silencio) None     avoid          8  false  false
goal    UNIR      approach  approach      16  true   true
goal    TEMER     avoid     avoid          0  true   false
goal    OBSERVAR  wait      wait           0  true   false
goal    (silencio) None     wait           0  false  false
```

Las dos filas donde `proposal` y `cuerpo` **difieren** son exactamente las
dos que el gate rescata, y las dos que antes mentían.

### Nombres separados

Dos hechos distintos ya no comparten clave:

```
qwen_proposal / stub_proposal   el verbo que nombró el reloj lento
qwen_action   / stub_action     lo que hizo el cuerpo tras el gate
qwen_proposal_at_X              approach, exigido por green()
canonical_threat_qwen_proposal  avoid,    exigido por green()
qwen_action_at_X / CortexROI    siguen describiendo el cuerpo, que es
                                lo que el mundo pagó
```

`green()` exige el **proposal** en las dos direcciones. Ni la acción final
ni una recompensa positiva bastan: con el gate produciendo `avoid` a
partir de un átomo equivocado y a partir de ningún átomo, una puerta
keyed en la acción aprobaría a un modelo que nunca leyó la frase.

### Estado de la puerta, sin modelo

```
model_configured   false     green              false     rc 1
qwen_calls 8 · qwen_rejected 8 · qwen_hits 0 · qwen_proposal_at_X null
stub_hits 2 (las dos canónicas) · paraphrase_stub_hits 0 de 6
CortexROI 0 · false_facts 0 · attend_reason conflict
```

Honestamente rojo, sin pesos y sin falsificarla. Primer intento de operador:
el informe llevaba `NAVI_QWEN_URL=http://127.0.0.1:8080`, pero no había
servidor escuchando; las ocho respuestas llegaron vacías en ~0,13 s. Es un
resultado **inconcluso de infraestructura**, no una medida del 4B. El GGUF y
`~/src/llama.cpp/build/bin/llama-server` existen; arrancar `qwen_up.sh` y
repetir la puerta.

### Locks de SIGN-Cb, sin mover

```
una sola línea dice conflict · el turno de consumo queda off
Δcalls +1 en conflicto, 0 en consumo · one_line_claims_the_wake true
latencia de un turno intacta · thought.KEYS 22 · N_ACTIONS 3
loop.py, signc.py, qwen_cortex.py, el prompt, gate, recompensas, stub,
CAM/T/Q y WSP: sin tocar
```

---

## SIGN-Cd — el átomo de acción ocupa el campo de relación (verde)

> **Auditoría Codex 2026-09-05:** implementación aceptada. La selección de
> gramática se observa dentro del brazo Qwen, se restaura incluso ante una
> excepción, `green()` exige ambos verbos canónicos y el hash recalculado,
> y la gramática general conserva sus 42 átomos en los cuatro campos.
> Resultado independiente: 9/9 pruebas SIGN-Cd y 392/392 en la suite.
> La repetición con el GGUF cerró después la puerta de operador.

La primera puerta válida con el 4B salió **roja**, y el rojo era correcto:
el modelo estuvo cargado, hubo ocho inferencias reales, `qwen_rejected=0`,
ROI +16 y dos paráfrasis ganadas, pero el letrero canónico de peligro no
produjo propuesta.

```
goal   canónico   YO   → UNIR    → AQUI  @AHORA
threat canónico   AMOR → CAMBIAR → TEMER @AHORA
```

La segunda línea **no es un rechazo y no es un error del modelo**. Es un
WSP bien formado y una lectura razonable del letrero: lo que cambió ahora
es de temer. `parse_reply` la acepta. Pero `loop` construye la propuesta a
partir del **rel**, y aquí `TEMER` está en DST. Así que no hubo rechazo y
no hubo decisión: el 4B había leído el letrero y lo dijo en una forma que
el cuerpo no puede tomar.

### Lo que no se hace

No se le enseña esa frase al parser. No se amplía lo que cuenta como
acción. No se baja `green()`. Y no se recorta `cortex.gbnf`: la gramática
general sigue siendo el vocabulario del reloj lento —los 42 átomos en los
cuatro campos— porque un córtex que sólo sabe nombrar acciones no puede
pensar ninguna otra cosa. Sigue byte-idéntica, con su sha fijado en un
test:

```
cortex.gbnf         2be563fcb54456b81d5b2fb11faed584079d7f2456ed2beebb66f5a6578184d0
cortex_action.gbnf  915018489cd8915d39ec9e518a0eb4ce58e607457030945402f0d6e69f60283e
```

### Lo que sí

Una gramática nueva, del **operador**, para las llamadas de este informe y
ninguna otra. No es un vocabulario más pequeño: es otra pregunta.

```
YO → { UNIR | TEMER | OBSERVAR | NONE } → AQUI @AHORA
```

SRC, DST y TIME quedan fijos porque este informe puntúa **una propuesta
local**, no composición libre de pensamientos. `NONE` está a propósito:
atraviesa `parse_reply`, es un átomo válido y no mapea a ninguna acción,
así que abstenerse se puede decir. Una gramática de tres obligaría a
producir un verbo en cada turno, y un córtex que no puede declinar no
puede equivocarse.

Medido, con la línea que llega al parser:

```
YO → UNIR     → AQUI @AHORA   rel 11  →  approach
YO → TEMER    → AQUI @AHORA   rel 18  →  avoid
YO → OBSERVAR → AQUI @AHORA   rel 14  →  wait
YO → NONE     → AQUI @AHORA   rel 40  →  ninguna acción, y no es rechazo
AMOR → CAMBIAR → TEMER @AHORA rel 13  →  ninguna acción  (la línea real)
```

La forma es byte por byte la que produce `cortex.gbnf`, así que el mismo
`parse_reply` lee las dos y nada río abajo sabe cuál se usó.

### Aislamiento

`qwen_signc` pone `NAVI_QWEN_GBNF` **sólo alrededor del brazo 4B** y lo
restaura en `finally` — una fila que reviente no puede dejar la shell del
operador, ni el tajo siguiente, apuntando a la gramática de SIGN-C. Una
variable que no existía vuelve a no existir, no a cadena vacía: el wrapper
trata el blanco como «usa la de por defecto» y las dos cosas no son la
misma. Los brazos `fast` y `stub` no se re-apuntan, y hay un test que mira
el valor de la variable **dentro** de cada brazo.

Qwen-0 y cualquier otro consumidor de `qwen_cortex.py` siguen con
`cortex.gbnf`: ni `qwen_sign.py`, ni `qwen_cortex.py`, ni `loop.py`
mencionan el fichero nuevo, y hay un test que lo comprueba por nombre de
fichero —no por el prefijo, que habría chocado con `cortex_actions`, la
métrica que todos esos módulos ya llevan.

### Lo que registra el informe

```
action_grammar            true
action_grammar_name       cortex_action.gbnf
action_grammar_sha256     915018489cd8…
general_grammar_sha256    2be563fcb544…   (distinto, y exigido distinto)
qwen_proposals            los cuatro verbos por mundo, tal cual salieron
```

`green()` **recomputa** el sha del fichero. Una corrida hecha por accidente
con la gramática general lleva el otro hash y se rechaza; una que dijera
`action_grammar: true` con un hash viejo, también. Hay un test que dobla
las nueve formas de mentir sobre esto y comprueba que `green()` se cae.

### Puerta real de operador — verde

Nav repitió el banco con el servidor local y el GGUF Q4_K_M. El informe
escrito en `lab/nexus0_qwen_signc_report.json` vuelve a pasar `green()` al
recomputarlo desde código y conserva los dos hashes anteriores:

```
goal    0 UNIR   1 UNIR   2 UNIR   3 UNIR
threat  0 TEMER  1 UNIR   2 UNIR   3 TEMER
```

6/8, cuatro de seis paráfrasis frente a cero del stub, los dos canónicos
correctos, ROI +16, ocho llamadas, cero rechazos, latencia media 1,8484 s y
cero hechos falsos. **Los dos fallos de amenaza quedan a la vista**: en
ambos el modelo propuso approach y recibió −16. No se retoca el dataset ni
se rebaja la clave para esconderlos. `green()` no exige ocho de ocho —
exige los dos canónicos y que el 4B gane al stub en paráfrasis. Es verde
para SIGN-C y deuda explícita de seguridad antes de cualquier ECHO-2 físico.
CI no arranca pesos y no exige ninguno de esos números.

### Locks

```
cortex.gbnf byte-idéntica (sha fijado) · 42 átomos en los cuatro campos
la matriz de SIGN-Cc intacta: OBSERVAR en THREAT sigue hit false
SIGN-Cb: una sola línea dice conflict, el consumo queda off
loop.py, signc.py, cortex.py, parse_reply, gate, recompensas, CAM/T/Q/WSP,
  frases del banco y umbrales de green(): sin tocar
prompt del modelo sin tocar — la variable aislada aquí es el esquema
sin servidor: rc=1, green=false, y action_grammar se registra igual
```

---

## TALK-1 — entrega declarada verde (revisión posterior roja)

`PYTHONPATH=. python3 -m echoai.nexus0.talk1` · `lab/nexus0_talk1_report.json`
`PYTHONPATH=. python3 -m echoai.nexus0.talk RUTA.jsonl`

El turno ya ocurrió. El animal ya decidió, el mundo ya pagó, y el
pensamiento que existió está en el jsonl. `talk.py` lo lee y escribe
español; **el orden de esas dos cosas es la afirmación entera**.

```
entrada        thought.jsonl, esquema exacto de 22 claves
salida         un subtítulo por registro, en el mismo orden
consistencia   496 / 496 cláusulas · TranslationConsistency 100
mutantes       24 / 24 en fuente · 21 / 21 dentro del informe
escrituras     0 · sha256 del fuente idéntico antes y después
```

### El subtítulo

Español controlado, gramática cerrada de dieciséis cláusulas etiquetadas,
una línea por registro:

```
turno: 512 · celda: 174 (EMPTY) · pose: sin pose · cuerpo: se acercó ·
gate: aceptó · recompensa: 0 · atención: despertó por conflicto ·
córtex: no propuso · T: predijo 3539 · nuevo: no · sorpresa: sí · δ: sí ·
preguntas: 0 · llamadas: 1 · Q: [3, 0, 0] · WSP: YO → OBSERVAR → AQUI @AHORA…

turno: 513 · celda: 251 (GOAL) · pose: sin pose · cuerpo: se acercó ·
gate: aceptó · recompensa: +16 · atención: apagada ·
córtex: propuso acercarse · T: no predijo · nuevo: sí · sorpresa: no · δ: sí ·
preguntas: 0 · llamadas: 1 · Q: [6, 0, 0] · WSP: YO → DESEAR → AQUI @AHORA…
```

Esas dos líneas son las de SIGN-Cb, tomadas de una corrida real. **Sin
«porque».** La primera dice que ATTEND despertó por conflicto y que el
cuerpo se acercó: dos hechos, dos cláusulas, ninguna conjunción. La
segunda dice que el córtex propuso acercarse y que el cuerpo se acercó,
también por separado, porque `gate` conserva la última palabra — la misma
separación que hubo que arreglar en SIGN-Cc.

Diez conjunciones están prohibidas y auditadas en cada línea: *porque, por
lo que, así que, debido a, ya que, puesto que, de modo que, por eso,
gracias a, a causa de*.

`Q` y `WSP` se reproducen **literales**. No se reinterpretan.

### Aislamiento causal, medido y no declarado

`causal_writes` no es una bandera: es el número de hallazgos de un escáner
AST sobre `talk.py`. Importa exactamente cinco módulos —`__future__`,
`json`, `sys`, `pathlib`, `typing`— y ninguno más. Ni `echoai`, ni
`subprocess`, ni `socket`, ni red, ni `os`, ni `shutil`. Abre el fichero en
lectura y su sha256 es el mismo antes y después. Ningún módulo del animal
lo importa, y hay un test que lo comprueba por AST sobre `loop`, `thought`,
`signc`, `open1` y `obj1`.

El escáner tiene sus propios mutantes: se le inyecta a `talk.py` un
`import echoai...`, un `from echoai... import`, un `import subprocess`, un
`write_text` y un `open(p, 'a')`, y debe verlos los cinco. Las dos formas
de import son ramas distintas del AST y al principio sólo una estaba
cubierta.

`talk.py` **duplica** `KEYS` y `ACTION_NAME` en vez de importarlos —
importar `thought` sería un paso hacia importar el animal — y los tests las
fijan contra las de verdad, porque una copia que puede derivar en silencio
es peor que ninguna.

### El auditor no le pregunta al redactor

`TranslationConsistency` no puede ser «el redactor coincide consigo mismo».
`audit()` **parsea el subtítulo de vuelta** a sus dieciséis cláusulas y las
compara con el registro usando tablas propias, escritas aparte. Hay un test
que lee el código fuente de `audit` y comprueba que no menciona
`talk.render`, `talk.BODY` ni `talk.PROPOSAL`.

Una regla mía murió por el camino, y lo digo: escribí primero una lista de
palabras prohibidas para la cláusula `cuerpo` —«jamás “giró”, “avanzó”,
“retrocedió”…» — y **ningún mutante podía matarla**, porque la igualdad
exacta de esa misma cláusula ya rechaza cualquier cosa que la lista
rechazaría. Era código muerto disfrazado de invariante. La quité. Lo que sí
añade valor es el barrido final: ninguna cláusula **salvo** `cuerpo` y
`córtex` puede contener un verbo, y eso sí es matable, porque `pose` es la
única cláusula comprobada por contenido y no por igualdad — el único sitio
donde un redactor podría colar un verbo o un «porque» pasando todo lo
demás. Hay dos mutantes que hacen exactamente eso.

### La matriz

31 registros. Nada se reconoce por turno ni por celda: el significado sale
de los campos.

```
acciones          0, 1, 2, 3          gate              OK, MODIFY, BLOCK
recompensa        +, 0, −             propuesta         null, 0, 1, 2
razones           las siete, conflict incluida
pose              completa, sin marco, y los cinco null del anillo
T                 conocida y null     n/s/delta         0 y 1 en los tres
propuesta wait + cuerpo avoid + gate MODIFY
```

Tres filas **no son sintéticas**: el par real `conflict`/`consume` de
SIGN-Cb, y un turno real de OPEN-1 —celda 18 (CLOSED), pose (0,1,0), fila Q
de cuatro, el cuerpo abrió y la tapa salió—. Un banco que sólo narra
registros que él mismo escribió no se ha encontrado con el animal.

La primera versión de esa fila de OPEN-1 aterrizó en una celda EMPTY: el
turno de asignación de ranura movía el cuerpo fuera del frasco. Corregido
para que esté de pie sobre el frasco cerrado, con un `assert` de que el
kind es `CLOSED`, de que la acción fue 3 y de que la tapa salió.

### Validación: error explícito, nunca un defecto

Se valida el fichero **entero** antes de emitir un solo subtítulo: media
narración que parece completa es peor que un error. JSON ilegible, clave
que falta, clave que sobra, acción fuera de rango, `q_row` de dos, flag que
no es 0 ni 1, kind desconocido, razón desconocida, media pose, rumbo sin
pose, `attend_on` en desacuerdo con la razón — todos son `BadRecord`,
stderr y rc=2, con stdout **vacío**. Hay un test con dieciocho formas rotas.

### Mutantes

```
esperar narrado como movimiento          la narración se emite sin validar
esperar narrado como apertura            el auditor le pregunta al redactor
approach y avoid intercambiados          el auditor deja de comparar el cuerpo
open narrado como approach               el auditor deja de barrer las cláusulas
signo de recompensa invertido            el auditor deja de mirar la causalidad
cero narrado como ganancia               un verbo colado en la pose
atención apagada narrada como conflicto  una causa colada en la pose
conflicto omitido                        un registro omitido / duplicado / reordenado
propuesta inventada                      el traductor importa el animal (from / import)
el reflejo del gate acreditado al córtex  el traductor escribe el jsonl
predicción inventada                     el traductor abre en escritura
WSP reinterpretado                       el traductor arranca un proceso
una cláusula desaparece                  green deja de exigir cada candado
validate deja de mirar claves / forma / rango
una línea rota se salta en silencio
```

24 de 24 en fuente. Dentro del informe, 21 de 21 subtítulos corrompidos a
mano que el auditor debe rechazar. `green()` recomputa cada condición desde
los campos del informe, y hay un test que dobla los 23 candados uno a uno.

### Un embellecedor Qwen queda apuntado, no implementado

Si algún día se quiere prosa más suelta, sería **otro operador opcional**
que consuma subtítulos ya auditados. No está aquí y nunca formará parte de
`green()`.

*(La puerta de TALK-1 salió roja en revisión: aceptaba subtítulos falsos.
Ver TALK-1b más abajo.)*

### Locks

```
thought.KEYS 22 · sin story, events, text, narration, subtitle, why
thought.ACTION_NAME approach, avoid, wait, open · N_ACTIONS 3 · WSP 16 B
anillo default cortex_calls 0 · false_facts 0 · destroyed 0
anillo --cortex 36 / 256
loop.py, thought.py, gate.py, cortex.py, las gramáticas, SIGN-C y los
  mundos: sin tocar. El consumidor se adapta al contrato.
informes y diarios anteriores: byte y mtime intactos
```

### Revisión Codex posterior — un falso verde residual

Los ocho contraejemplos de TALK-1 están cerrados y los 24 tests focales
TALK-1/TALK-1b pasan. Queda un caso no cubierto: si se añade a
`report["mutants"]` un mutante futuro con `killed=false` y se falsean los
dos contadores resumen, `green()` devuelve true. `battery_state.alive`
sólo intersecta con `REQUIRED_MUTANTS` y la cláusula posterior confía en
los contadores, pese a prometer proteger mutantes requeridos o no.

Veredicto: semántica e aislamiento cerrados; puerta del informe aún roja.
Siguiente TALK-1c. PATTERN-0 espera.

### Revisión Codex posterior — rojo de verificación

La entrega genera 256/256 subtítulos, conserva el diario, separa cuerpo,
gate y propuesta, y los 14 tests focales pasan. El `talk.py` real sólo lee
el jsonl y su salida observada es correcta. Sin embargo, la puerta
`TranslationConsistency=100` acepta estos subtítulos falsos sin fallos:

```text
pose real: (1, 2, 0) rumbo 3 marco 1
acepta:    (100, 200, 0) rumbo 3 marco 1
acepta:    (2, 1, 0) rumbo 3 marco 1
acepta:    (1, 2, 0) rumbo 3 marco 1 con obstáculo
sin frame: (0, 0, 2) rumbo 5 marco 99
```

Además, redactor y auditor comparten `talk.REASON_ES`: si ambos llaman
«celda nueva» a `miss`, pasa. El escáner AST tampoco detecta
`Path(p).open('w').write('x')` ni `open(p, mode).write('x')`.

Veredicto vigente: narrador correcto, aislamiento actual correcto,
**auditor con falsos verdes**. Siguiente TALK-1b; PATTERN-0 no
empieza.


---

## TALK-1b — que el auditor no pueda equivocarse con el narrador (verde)

El narrador de TALK-1 estaba bien y el aislamiento del código era real. La
**puerta** no: aceptaba subtítulos falsos. Tres agujeros, todos de la misma
forma —una comprobación incapaz de estar en desacuerdo con lo que
comprueba— y los catorce tests pasaban. Eso era el defecto.

### Los contraejemplos, antes y después

Fila `pose_full`, valor real `(1, 2, 0) rumbo 3 marco 1`:

```
                                        antes      después
(100, 200, 0) rumbo 3 marco 1           audit []   pose != real
(2, 1, 0) rumbo 3 marco 1               audit []   pose != real
(1, 2, 0) rumbo 3 marco 1 con obstáculo audit []   pose != real
(0, 0, 2) rumbo 5 marco 99  (sin frame) audit []   pose != real
```

La pose se auditaba buscando **cada número como subcadena**: `1` está en
`100`, el orden no importaba y se podía añadir lo que fuera.

```
razón `miss` renombrada en el redactor  antes: audit []
                                        después: dos hallazgos
```

`audit()` leía `talk.REASON_ES`, la tabla **del redactor**. Un narrador que
llamara `miss` «despertó por celda nueva» se comprobaba contra su propio
error y pasaba.

```
Path(p).open('w').write('x')     antes: ningún hallazgo
Path(p).open(mode).write('x')    antes: ningún hallazgo
open(p, mode).write('x')         antes: ningún hallazgo
fh.write('x')                    antes: ningún hallazgo
__import__('echoai.nexus0.loop') antes: ningún hallazgo
```

El escáner leía el modo de `open` **por posición**, como si toda llamada
fuese el builtin —en `Path(p).open('w')` el modo es `args[0]`, no
`args[1]`— y nunca miraba `write`.

### Arreglo 1 — pose por igualdad exacta

`talk1.want_pose()` construye la única cadena válida y se compara por
igualdad. Cierra los cuatro contraejemplos y además coordenadas
reordenadas, prefijos, sufijos, rumbo/marco inventados u omitidos, y una
pose donde el registro dice `sin pose`.

`talk.validate()` se endurece **sólo** donde expresa el contrato que ya
existía, y comprobado antes contra los 384 registros reales del laboratorio
—ninguno lo viola—:

```
sin pose  ⇒  heading Y frame deben ser null
q_row     ⇒  3 ó 4 enteros, nada más
action    ⇒  debe caber en la fila Q que produjo la decisión
cortex_action ⇒ lo mismo
```

`lab/thought_sign.jsonl` sigue dando rc=2, como ya daba: es un diario de 17
claves anterior a GUI-3, y rechazarlo es la regla de «ni defectos ni saltos
silenciosos» funcionando.

### Arreglo 2 — un auditor de verdad independiente

`parse()` y `audit()` no referencian `talk.LABELS`, `talk.SEP`,
`talk.REASON_NAME`, `talk.REASON_ES`, `talk.BODY`, `talk.PROPOSAL`,
`talk.GATE`, `talk._pose` ni `talk.render`. Hay un test que lee el fuente
de las tres funciones y lo comprueba. `talk1` tiene sus propias dieciséis
etiquetas —con su orden—, su separador y sus siete traducciones de ATTEND,
y otro test las fija contra las del redactor: la deriva es un test rojo, no
un acuerdo silencioso.

Cuarenta y nueve comprobaciones nuevas de razones: las siete torcidas una a
una en el redactor, y las 42 combinaciones de una razón vistiendo las
palabras de otra.

### Arreglo 3 — escáner conservador

```
cualquier open(...)              hallazgo   (talk.py no necesita ninguno)
write / writelines / truncate    hallazgo, salvo sys.stdout y sys.stderr
write_text, unlink, touch, …     hallazgo
eval, exec, __import__, compile  hallazgo
importlib, tempfile, pickle      hallazgo
```

No se afirma que un escáner AST sea un sandbox. Sí cubre todas las formas
equivalentes que el banco dice prohibir, incluidas dos que se me
escaparon: un descriptor que **parece** un stream (`evil.stdout.write`) no
está exento.

### Arreglo 4 — la batería no se puede vaciar

`mutants_total >= 12` permitía borrar categorías enteras y seguir verde.
Ahora hay un `REQUIRED_MUTANTS` explícito de **42 nombres** —seis de pose,
siete de razones, cinco de escritura/escape, y el resto— y `green()`
recomputa desde `report["mutants"]`, no desde los campos que el informe
escribe sobre sí mismo. Tres rechazos por separado, para que cada uno se
pueda demostrar necesario:

```
falta alguno de los requeridos      → rojo
hay un nombre duplicado             → rojo
alguno de los requeridos sobrevive  → rojo
```

Un test borra cada uno de los 42, uno por uno, dejando los campos resumen
del informe diciendo que todo va bien: sólo la recomputación puede
pillarlo. Otro duplica un nombre. Otro hace sobrevivir a uno **y miente en
el contador**, que es donde se ve que `green()` no se cree al informe.

### Dos reglas mías más que murieron

Con las dieciséis cláusulas en igualdad exacta, el barrido de verbos y el
bucle de conjunciones dentro de `audit()` quedaron subsumidos: nada se
puede añadir en ningún sitio sin romper la igualdad de la cláusula donde se
añadió. Ningún mutante podía matarlos. Los quité y dejé escrito dónde vive
de verdad cada regla: la prohibición de «porque» se aplica en
`uses_a_conjunction`, que cuenta conjunciones sobre **toda** la matriz y
sobre un diario real de 256 turnos, y que `green()` exige a cero — el
mutante que mete una conjunción pone 37 tests en rojo.

Es la tercera vez en estos tajos que escribo un guardián que nada puede
violar por su cuenta. Está anotado en memoria.

### Cierre

```
TranslationConsistency        100 %   (496 / 496 cláusulas)
pose false subtitles          0 aceptados de 15 probados
shared-table mutants          0 supervivientes de 49
write/escape mutants          0 supervivientes de 12
required mutants present      42 / 42, sin duplicados, todos muertos
causal_writes                 0 en el talk.py real
mutantes en fuente            39 / 39
```

### Revisión Codex posterior — un falso verde residual

Los ocho contraejemplos originales están cerrados y los 24 tests focales
TALK pasan. Queda uno nuevo: un elemento futuro de `report["mutants"]` con
`killed=false` pasa si los contadores resumen dicen que murió.
`battery_state.alive` sólo mira `REQUIRED_MUTANTS`; después `green()` se
fía de los contadores para los demás. Reproducido localmente:

```text
base_green                         true
extra_future_mutant_killed=false  green=true   # falso verde
```

Semántica e aislamiento quedan aceptados. La puerta del informe espera la
corrección mínima de TALK-1c; PATTERN-0 no empieza todavía.

### Revisión Codex final — TALK-1 verde

TALK-1c cerró el contraejemplo literal: un mutante futuro vivo queda en
`battery_state.alive` y `green()` da false aunque ambos resúmenes mientan.
Entradas malformadas producen rojo sin excepción y un mutante futuro muerto
puede ampliar limpiamente la batería.

Auditoría independiente:

```text
TALK focales                 31 OK
suite                        423 OK (expected failures=1)
talk1 / bench / signc        rc=0 / rc=0 / rc=0
TranslationConsistency      496 / 496 = 100
source / narrated            256 / 256, orden y sha idénticos
required / alive / malformed 42 / 0 / 0
causal_writes                0
```

TALK-1 queda cerrado. Siguiente PATTERN-0.

---

## TALK-1c — ningún mutante vivo, tampoco uno futuro (verde)

Quedaba un falso verde, y era mío: el comentario de `green()` prometía
proteger «every mutant in the battery, required or not» y no lo hacía.

```python
r = talk1.experiment()
r["mutants"].append({"mutant": "extra futuro vivo",
                     "killed": False, "failures": []})
r["mutants_total"] = len(r["mutants"])
r["mutants_killed"] = r["mutants_total"]     # contador mentiroso
talk1.green(r)      # antes: True     después: False
```

### Causa

Dos cosas a la vez. `battery_state()["alive"]` intersecaba con
`REQUIRED_MUTANTS`, así que un mutante que no estuviera en la lista podía
sobrevivir sin que ningún campo lo dijera. Y `green()` comparaba los dos
contadores del informe **entre sí**, sin volver a contar: un informe que
mentía en los dos se daba la razón a sí mismo.

```
alive (antes)   set(REQUIRED) & set(names) - dead     ← el extra no cabe
alive (después) todo el que no murió, requerido o no
```

### Lo que `green()` exige ahora, todo recomputado desde la lista

```
entradas malformadas          []
requeridos ausentes           []
nombres duplicados            []
mutantes vivos                []   requeridos o futuros
mutants_total                 == len(mutants)          recontado
mutants_killed                == count(killed is True) recontado
```

Un mutante extra **muerto** sigue siendo verde: la batería tiene que poder
crecer, o el candado es una jaula. Uno extra **vivo** es rojo aunque los
campos resumen digan que murió.

### Malformados: rojo limpio, no una excepción

Una puerta que revienta ante un informe malo no lo ha juzgado. Una entrada
sin nombre, sin `killed`, con `killed: 1` —`isinstance(True, int)` es
cierto, así que el booleano se comprueba primero—, con `killed` como texto
o `None`, una entrada que no es un objeto, o un `mutants` que no es una
lista o que no está: todo eso es un hallazgo y un `False`, sin traza.

### Otra regla mía que murió

`mutants_killed == mutants_total` desapareció del bloque final. Una vez que
los dos totales se recuentan y `alive` tiene que estar vacío, esa cláusula
no puede fallar sin que falle antes alguna de ésas — y mientras estuvo ahí
era **la única** que atrapaba a tres de ellas, así que ninguna de las tres
podía demostrarse necesaria. Quitándola, las tres pasaron a tener su propio
mutante. Cada rechazo se sostiene solo.

Van cuatro. Está en memoria.

### Cierre

```
falso verde reproducido       sí, literal · ahora False
extra muerto                  sigue verde
miente sólo en total          rojo      miente sólo en killed   rojo
9 formas de entrada malformada rojo, sin excepción
4 formas de `mutants` inválido rojo, sin excepción
requeridos                    42 / 42 presentes, únicos, muertos
mutantes en fuente            45 / 45
```

---

## PATTERN-0 — un riff que la T de un paso no oye (verde)

`PYTHONPATH=. python3 -m echoai.nexus0.pattern0` · `lab/nexus0_pattern0_report.json`

```
... B → A → C → A → B → A → C → A ...
```

En `A`, con la **misma** acción, el mundo devuelve unas veces `C` y otras
`B`. `World.predict(A, approach)` tiene una fila y una respuesta, así que
acierta la mitad — no porque esté rota, sino porque el dato que decide el
sucesor no está en su lista de argumentos. **De dónde venía el cuerpo** sí
lo está.

```
(B, A, approach) → C
(C, A, approach) → B
```

### La ambigüedad, medida y no afirmada

Leída del inverso de la propia T después de entrenar, no del ciclo:

```
slot 3195 · acción 0   →   {37: 50, 1649: 50}
```

Cincuenta y cincuenta. Un solo `(s,a)` ambiguo, y el informe imprime los
conteos para que nadie tenga que fiarse del ciclo.

### El resultado

```
transiciones de entrenamiento   212      contextos maduros   7
examen                          4 rotaciones × 40 pasos
puntos de decisión              80
T                               40   (la moneda al aire que le toca)
patrón                          80
prediction_gain_hits            +40
pattern_unknown                 0
por rotación                    20/10/20 en las cuatro
```

### Los cinco controles, cada uno un brazo

```
sin contexto (prev descartado)  gain 0   colapsa exactamente sobre T
sin regularidad (mundo con dos sucesores alternos por contexto)
                                0 reglas maduras · gain 0 · 98 conflictos
reloj absoluto turn % k         mejor de {2,3,4,5,6,8}: 20 / 80   < T
memoria llena (capacidad 4)     size 4 · dropped 16 · nada sobrescrito
predictor que no sabe nada      80 puntos, 0 aciertos, 80 unknown
```

El último cierra dos reglas que de otro modo nadie podía violar: **`None`
no es acierto y no sale del denominador**. Se puntúa sobre exactamente los
mismos puntos ambiguos con una T vacía y una memoria vacía; si `None`
contara, saldrían 80 aciertos, y si los no cubiertos salieran del
denominador, saldrían 0 puntos.

El control del reloj no funciona por suerte: cada rotación arranca su
contador local **en cero** desde una fase distinta del ciclo, y el informe
publica `exam_local_turn_starts = [0, 0, 0, 0]`. La API de la memoria no
recibe turno — hay un test que inspecciona las firmas.

El control sin regularidad no lleva las pausas de `avoid` que sí lleva el
mundo honesto: estar quieto **es** una regularidad, y un control que no
debe contener ninguna no puede recibirla.

### La memoria

```
orden 2      (slot_anterior, slot_actual, acción) → slot_siguiente
capacidad    512, declarada y constante
clave        12 + 12 + 4 bits: es el contexto, no un hash de él
tabla        direccionamiento abierto, sondeo lineal, cinco listas fijas
lleno        dropped++, y nada de lo ya aprendido se toca
KCC          el alternativo desplaza sólo si gana estrictamente
madurez      n >= min_hits (2) **y** alt_n == 0
```

Una regla que alguna vez fue contradicha se **guarda y no se ofrece**:
`predict()` devuelve `None`. Es una extensión explícita del predictor —
donde el contexto no tiene regla, la respuesta cae a `World.predict` sin
tocarla. No guarda WSP, ni kind, ni recompensa, ni hechos que CAM ya tiene;
no escribe en `World.pred/n/alt`; importa exactamente cuatro módulos
(`__future__`, `hashlib`, `typing`, `constants`) y ninguno del animal. Hay
un escáner AST con sus propios mutantes.

### Congelación

```
observes_during_exam    0
t_hash antes/después    iguales
pattern_hash            iguales
```

Ambas memorias van envueltas en un contador de `observe()` durante el
examen, y se hashean antes y después. Un mutante que aprende durante el
examen mueve las dos cosas.

### Mutantes

```
la clave olvida el slot anterior / la acción     el examen aprende
madura con una sola observación                  usa una sola rotación
una regla contradicha se sigue ofreciendo        el contador no se reinicia
mature ignora la contradicción                   None cuenta como acierto
la tabla llena sobrescribe                       los no cubiertos salen del denominador
dropped no se cuenta                             la ambigüedad se afirma
la memoria crece con la corrida                  el control recibe regularidad
KCC desplaza sin ganar                           el control conserva el contexto
el compositor ignora la memoria                  green: 9 candados sueltos
el compositor escribe en T                       el escáner deja de mirar
```

**33 / 33** en fuente (39 / 39 tras PATTERN-0b). La batería del informe
tiene 29 requeridos, todos muertos, con la disciplina de TALK-1c: nombres
requeridos, sin duplicados, entradas válidas, y `green()` recontando desde
la lista en vez de creerse los resúmenes.

### Nada se enchufa al bucle

`loop.py` no importa `pattern`, `Agent()` no tiene ningún atributo nuevo y
no hay coste observable en el banco por defecto. XFER-1 decidirá qué
memoria merece cruzar mundos después de verla medida.

### Locks

```
WSP 16 B · CAM 4096 · destroyed 0 · false_facts 0
World T con su semántica y sus tablas intactas
N_ACTIONS 3 · thought.KEYS 22 · sin clave `pattern`
anillo default cortex_calls 0 · anillo --cortex 36 / 256
TALK-1 y SIGN-C: informes y comportamiento intactos
sin LLM, sin Qwen, sin prosa, sin etiquetas humanas, sin A/B/C dentro del
  detector, sin segunda CAM, sin diario nuevo
```


---

## PATTERN-0b — cerrar la auditoría de aislamiento (verde)

El resultado predictivo de PATTERN-0 no se toca y sigue igual: **80 / 40 /
+40**. Lo que estaba roto era el escáner que dice que la memoria no toca
nada.

### Los contraejemplos, antes y después

```
                                antes           después
self.world.pred[0][0] = 9       []  aceptado    escribe en `world.pred`
self.world.n[0][0] += 1         []  aceptado    escribe en `world.n`
self.world.alt[0][0] = 9        []  aceptado    escribe en `world.alt`
self.world.alt_n[0][0] = 1      []  aceptado    escribe en `world.alt_n`
self.world.pred = []            []  aceptado    escribe en `world.pred`
```

Cinco escrituras directas en las tablas de `World`, las cinco limpias.

### Causa

El escáner miraba **nombres de atributo** y **llamadas**. `pred` no estaba
en la lista de campos prohibidos —y no puede estarlo: `PatternMemory` tiene
tablas llamadas `pred`, `n`, `alt` y `alt_n` **propias**, y las escribe en
cada observación—. Lo que separa unas de otras no es el nombre del campo
sino **el receptor**. Y `self.world.pred[0][0] = 9` es un `Subscript` de un
`Subscript` de un `Attribute`, así que mirar el nodo del objetivo tal cual
no ve nada.

### El arreglo

```
Assign · AnnAssign · AugAssign     los tres, y objetivos en tupla
pelar los subíndices               hasta el Attribute que dice de quién es
receptor ajeno                     self.world / self.t / self.cam / self.q
                                   y también los nombres sueltos world, t
tablas ajenas                      pred, n, alt, alt_n, inv, conflicts
tablas propias                     self.pred, self.n, self.alt, self.alt_n
                                   siguen siendo legales, por el receptor
```

Hay un test con las siete formas que sí debe marcar —incluida
`self.world.pred[0], other = 9, 8` y `self.world.inv[0][0][0] = 1`— y otro
con las siete que **no** debe marcar, que son las escrituras que la memoria
hace sobre sí misma en cada `observe()`.

### Inyecciones independientes

El mutante compuesto se ha ido. Inyectaba un import, una llamada y un
paquete guardado **en un solo blob**, y se contaba muerto si se encontraba
*algo*: por eso cinco escrituras en `World` podían viajar escondidas detrás
de un import prohibido.

Ahora hay **doce inyecciones separadas**, cada una un mutante requerido con
su propio nombre, y cada una detectada por sí sola:

```
importa World · importa la CAM · importa el encoder
llama a world.observe
escribe world.pred · world.n · world.alt · world.alt_n
reemplaza world.pred entera · escribe t.alt_n
guarda un WSP · toca la CAM
```

Más `el patrón real no toca nada`, que exige `isolation_findings(pattern.py)
== []`. Un test comprueba además que **la evidencia de cada entrada es la de
su propia inyección**: comprobar sólo `killed` dejaría pasar una batería que
volviera al blob.

### La cabecera, corregida

Decía que el examen se corre «en rotaciones que el entrenamiento nunca
caminó». **Eso no era cierto**: la marcha de entrenamiento es una sola
corrida desde la fase 0 y pasa por las cuatro fases por el camino. Lo que
hace held-out al examen es que sus transiciones se toman **después** de
congelar y hashear ambas memorias, desde entornos nuevos, con el contador
local otra vez en cero. Hay un test que mide que el entrenamiento sí recorre
varias fases y que busca la frase vieja en el fuente para que no vuelva.

### Cierre

```
cifras predictivas            80 / 40 / +40, intactas
contraejemplos                5 / 5 detectados
inyecciones independientes    12, cada una por sí sola
isolation_findings(pattern.py) []
mutantes requeridos           29, presentes, únicos, todos muertos
mutantes en fuente            39 / 39
```

---

## XFER-1 — el mismo animal en tres mundos (entregado; review pendiente)

No la misma clase corrida tres veces, ni tres agentes con copias de las
tablas del otro. **Un solo objeto `Agent`**, nacido una vez, cuyas CAM, Q,
T y memoria de contexto son los mismos cuatro objetos a ambos lados de las
dos fronteras — comprobado por `id()`, porque parecerse no es ser.

En una frontera se sustituye `ag.env` y se suelta un latch: `prev_slot`, la
afirmación de que el cuerpo estaba en algún sitio hace un instante, que
deja de ser cierta en el momento en que le cambian el mundo debajo. Soltar
eso no es olvidar nada, y hay un test que compara CAM, Q, la fila del
peligro y el tamaño de la memoria antes y después de cruzar.

### El parque

```
S0 → S1 → H1 → S3 → H2 → S5 → H3 → S7 → GOAL → S0
```

Tres peligros y un premio. `avoid` en un peligro es un **esquive**: paga +8
y sigue la vuelta, así que un cuerpo que los conoce da vueltas en vez de
bombear recompensa contra uno solo. Aparte, entrando por teletransporte,
el riff de PATTERN-0: en R0 el sucesor depende de la celda de la que se
viene. La regla se lee del ciclo con `pattern0.successors_of`, la misma
función que la generó allí — una tabla, no tres ramas.

Los tres layouts comparten encoder, identidades WSP, kinds y tres acciones.
Lo único que cambia es **física, por tabla de sucesores**:

```
A → B   1 arista movida   (S0 → D1)
B → C   2 aristas         (S0 vuelve a S1, S7 → D2)
```

### Las dos filas

```
                         B                    C
T en la entrada          9 filas conocidas    10 filas conocidas
  todavía correctas      8                    9
  contradichas           1  (celda 5)         1  (celda 96)
transfer                 208                  224
scratch                  152                  152
gain                     +56                  +72
agregado                 +128 = 56 + 72
control de edad          152  → gain 0        152  → gain 0
```

Cada frontera paga por su cuenta. Un total positivo con una frontera muerta
no pasa: hay un test que pone `gain_B = 0` **dejando el agregado cuadrado y
positivo** y comprueba que `green()` se cae, y otro que hace lo mismo con C.

### El protocolo, emparejado y registrado

Misma clase y layout, misma semilla, mismo asiento y estado físico de
entrada, mismos flags, mismas acciones, mismos turnos — y **los mismos
valores de `turn`** entregados a la política.

Eso último hubo que registrarlo, no suponerlo: en este parque la fase de
exploración **no mueve la recompensa**, así que un control corrido con
otros turnos habría sacado lo mismo y ningún número se habría enterado. El
mutante «transfer y scratch en turnos distintos» sobrevivió hasta que la
comprobación pasó a ser la huella del protocolo —primer turno, último
turno, suma— en vez del resultado. Emparejado es una propiedad del
protocolo, no del desenlace.

### El control de edad

Un agente que ha consumido **los mismos turnos previos** en un parque sin
peligros, sin premio y con un riff cuyos sucesores se alternan. Uno nuevo
por frontera, con el kilometraje exacto que lleva el animal enseñado en ese
punto: 608 antes de B, 672 antes de C.

Ese fue el segundo fallo propio del tajo. La primera versión reutilizaba el
**mismo** control de edad en las dos fronteras, así que llegaba a C
habiendo caminado B — y sacaba `age_control_gain_C = +72`, exactamente el
conocimiento que existe para descartar. Un control que ha hecho el examen
anterior no es un control.

Su reclamación tampoco es que un cuerpo con kilómetros no aprenda nada: su
propio corredor es determinista y sí madura contextos. Es que no tiene nada
de la estructura **transferible** — nunca pisa el riff, y ni el peligro ni
el premio están en su parque.

### La sonda de patrón

Con las cuatro memorias congeladas, antes de que ninguno de los dos brazos
dé un turno en el mundo nuevo:

```
                   puntos   aciertos   desconocidos   observes
transfer B / C        96       96            0            0
scratch  B / C        96        0           96            0
edad     B / C        96        0           96            0
```

`None` es fallo y no sale del denominador. La sonda no paga, no escribe y
no aprende — hay un test que compara identidades, hash de la memoria,
contador de observaciones y ranuras de CAM antes y después.

### El enganche, opt-in

```python
Agent(pattern_memory=True)      # y por defecto, False
```

`Agent()` no construye ninguna memoria, `prev_slot` es `None`, y el anillo
sigue en `[-12, +5, 0]`, `+80`, `256/31/0/168`, `36/256` con `--cortex`. El
banco canónico también: `33/1/217`.

Encendido, es **el mismo canal de predicción**, no una segunda T:

```
pred_next = self._predict(slot, a)
    contexto maduro  -> pattern.predict(prev_slot, slot, a)
    si no            -> t.predict(slot, a)
tras el paso, en la misma rama y bajo la misma condición que t.observe:
    pattern.observe(prev_slot, slot, a, slot_n)
```

Medido en el riff, donde T tiene una fila y una sola respuesta: `_predict`
devuelve **dos** sucesores distintos según de dónde venga el cuerpo, y uno
de los dos es justo donde T sola se equivocaba. Sin contexto, cae a T sin
cambiar nada.

### Ningún mundo se llama a sí mismo delante del animal

`loop.py`, `pattern.py`, `qtable.py`, `world.py`, `gate.py` y `encoder.py`:
cero menciones de un layout y cero lecturas de `layout` / `park` /
`world_name` / `world_id` del entorno. Dos reglas, y sólo dos: el barrido de
texto subsume cualquier comprobación AST de *nombres* —una constante, un
identificador y un atributo son todos texto— así que la única regla AST que
queda es otra pregunta: si el módulo le pregunta al mundo cómo se llama, lo
cual puede hacer sin nombrar ningún parque. `escalate.level` no está en esa
lista a propósito.

### Mutantes

```
nace un Agent nuevo en B / en C          None cuenta como acierto
copia las tablas y lo llama el mismo     los no cubiertos salen del denom.
borra CAM / Q / T / PatternMemory        transfer y scratch en otros turnos
no limpia prev_slot y cose dos mundos    scratch desde otro asiento / fase
la memoria no recibe lo que T recibe     el total esconde gain_B / gain_C
la sonda aprende                         PARK_C repite la física de PARK_B
una rama por nombre en el core           la edad recibe la regla verdadera
el informe borra un requerido            un futuro vivo con contadores falsos
```

22 requeridos en el informe, todos muertos, con la disciplina de TALK-1c y
PATTERN-0b: sin duplicados, entradas válidas, **todos** los vivos contados
aunque sean futuros, y `green()` recontando total y muertos desde la lista.
**31 / 31** en fuente.

### Locks

```
WSP 16 B · CAM 4096 · destroyed 0 · false_facts 0 · cortex_calls 0
N_ACTIONS 3 · thought.KEYS 22 · Agent().pattern_memory None
anillo default [-12,+5,0] · +80 · 256/31/0/168 · --cortex 36/256
banco canónico 33/1/217 · PATTERN-0 sigue en 80 / 40 / +40
sin red, sin Qwen, sin subprocess, sin numpy, sin torch, sin floats en el
  parque, sin etiquetas humanas
```

### Revisión Codex — XFER-1b requerido

Los resultados +56/+72 y la continuidad de las cuatro memorias son reales,
pero la puerta todavía admite falsos verdes: otro objeto `Agent` con las
cuatro memorias antiguas injertadas pasa como el mismo animal; gains positivos
desligados de las restas de reward pasan; `matched_flags` no compara los
brazos que corren; y el 96–0 de Pattern usa un scratch sin slots CAM del riff,
por lo que no aísla la utilidad propia de PatternMemory. Los 15 tests focales
pasan, pero esos contraejemplos se reprodujeron directamente.

Siguiente tajo: XFER-1b. Hasta ese cierre, **ECHO-1 sigue abierto**.


---

## XFER-1b — identidad y controles corregidos; puerta aún en revisión

El resultado causal de XFER-1 no se toca y sigue igual: **B 208 vs 152
(+56), C 224 vs 152 (+72), agregado +128, patrón 96/96, PATTERN-0 en
80/40/+40**. Lo que estaba flojo era la auditoría: tres afirmaciones podían
satisfacerlas algo que no era lo que la afirmación decía.

### 1. El cuerpo, no el equipaje

```python
reborn = new_agent()
reborn.cam, reborn.q, reborn.t, reborn.pattern_memory = (old.cam, old.q,
                                                         old.t, old.pattern_memory)
identities(reborn) == identities(old)   # True — y es cierto
is_same_body(reborn, old)               # antes: no existía · ahora: False
```

`same_agent_across_worlds` se derivaba **sólo** de los cuatro objetos
internos, así que un `Agent` reconstruido con las memorias injertadas pasaba
como el mismo animal. Ahora se conserva una referencia real al cuerpo nacido
y se compara con `is`. Las cuatro comprobaciones de memoria **siguen**: son
afirmaciones distintas.

La decisión vive en **un solo sitio**, la frontera, y `experiment` sólo
conjunta las filas — dos sitios calculándolo eran dos maneras de decir lo
mismo y ninguna se podía demostrar necesaria. Hay un test que cruza una
frontera con un cuerpo distinto del esperado y comprueba que dice `false`.

### 2. Los gains, atados a las restas

```python
r["gain_B"] = 1; r["gain_C"] = 1; r["aggregate_transfer_gain"] = 2
green(r)      # antes: True     ahora: False
```

Las recompensas seguían implicando +56/+72 y los campos ya decían otra cosa.
`green()` exige ahora `gain == transfer − scratch` en las dos fronteras,
además del agregado. Dos mutantes independientes con gains **positivos** y
desligados de las restas, y un test que además hace mentir al campo resumen.

`gain_B > 0` y `gain_C > 0` desaparecieron del bloque: con las recompensas
obligadas a diferir y cada gain obligado a ser esa diferencia, un gain no
positivo no puede ocurrir sin que falle antes otra cláusula. Estaban
subsumidas y ningún mutante podía matarlas.

### 3. Los flags de los brazos que corren

`matched_flags` comparaba el animal transferido con un `Agent()` **ajeno al
experimento**. Un scratch nacido con `ask=True`, `cortex=True` y sin
PatternMemory habría pasado desapercibido.

Ahora hay una firma de protocolo por brazo, tomada antes de la ventana:

```
n_actions · ask_enabled · cortex_enabled · pattern_memory · plan_depth
escalate_enabled · conflict_attend · q_trace · q_remainder · q_explore_flat
q_width · env_seed · window_turns
```

Determinista, sin ids, y **sin el layout**: eso es justo lo que el brazo de
edad debe variar. `transfer == scratch == age` en B y en C. La comparación
es una función propia (`signatures_match`) que se prueba diciendo que no.

`false_facts`, `destroyed`, `cortex_calls` y los rechazos se suman sobre
**todos** los brazos ejecutados. `llm_calls` se reporta como lo que es —el
mismo número que `all_arms_cortex_calls`, porque el hook del córtex es la
única puerta a un modelo— y la puerta cierra sobre la suma, no sobre un cero
escrito.

Siete mutantes independientes: scratch sin PatternMemory, con córtex, con
ask, con `explore_flat`, con `remainder`, con `plan_depth`, con otra semilla;
más el control de edad con otros flags. La semilla se mata **por protocolo**,
no por desenlace: esta física es determinista y no cambia el reward.

### 4. La ablación, perceptualmente emparejada

El 96–0 anterior no aislaba nada:

```
PatternMemory entrenada + CAM vacía  ->  0 hits, 96 unknown
scratch real                          ->  0 hits, 96 unknown
```

Ese cero se explica entero por no poder mapear los puntos a slots, antes de
preguntarle nada a la memoria. Ahora los mismos tuples enteros ya resueltos
por una CAM que conoce el riff se le dan a **las dos**:

```
puntos 96 · known_slots 96 · mapping_matched true
entrenada 96 · vacía 0 · writes 0
```

`None` sigue siendo fallo y sigue en el denominador. El mutante inverso
—memoria entrenada con una CAM que no resuelve— da `mapping_matched false`
y `green()` rechaza que se cite esa fila como ablación emparejada. La fila
scratch original se conserva, pero ya no es la prueba.

### 5. El canal

El mutante llamado «PatternMemory no recibe las mismas transiciones que T»
construía `half = PatternMemory()` y recorría un bucle **cuyo cuerpo no
insertaba nada**: comparaba memoria entrenada contra memoria vacía y no
auditaba el canal.

Ahora se instrumenta una corrida real con dos cortes, registrando cada
llamada de verdad:

```
t_observations 64 · pattern_observations 62 · cuts 2
skipped_after_cuts [0, 32]        una por corte, ni una más
counts_match true · projection_matches true
refused_step_silences_both true   (un self_model que rechaza calla a los dos)
```

La proyección `(slot, action, next_slot)` coincide elemento por elemento. El
audit **puede** salir falso: `channel_audit(skip_at=10)` deja caer una
transición camino de la memoria y `projection_matches` pasa a `false`. Y hay
un mutante que le quita una transición a Pattern sin apagar la memoria.

Se quitó el campo `matches`: era una conjunción al lado de sus propios
conjuntos y ponerlo a `True` a mano no rompía nada. El veredicto se deriva
una vez, en `experiment`.

### 6. Una afirmación muerta del control de edad

`PARK_VOID` se describía con «un riff cuyos sucesores se alternan». Nunca se
ejecutó: `aged_agent` no entra en R0/R1/R2 y la rama devolvía `options[0]`
siempre, así que no alternaba nada. **La afirmación y el código no usado se
han eliminado.** Lo que se declara es lo que se mide: el cuerpo envejecido no
toca el riff, y los tests lo comprueban celda por celda. Un mutante devuelve
el riff alternante muerto y muere.

### Cierre

```
same_agent_object                     true
gains_equal_reward_differences        true en B y C
protocol_signatures_match             true en B y C, tres brazos
all_arms_false_facts / destroyed      0 / 0
all_arms_cortex_calls                 0
pattern_probe_mapping_matched_B/C     true · known_slots 96 == puntos 96
trained 96 vs empty 0 · pattern_probe_writes 0
pattern_channel_matches_t             true
gain_B +56 · gain_C +72 · agregado +128    (sin tocar)
```

32 mutantes requeridos en el informe, todos muertos, sin duplicados, con
`green()` recontando desde la lista. **50 / 50** en fuente. El informe es
byte-idéntico entre dos corridas.

### Revisión Codex — XFER-1c requerido

La ejecución nominal y las cifras anteriores son válidas; los 24 tests
focales y la suite completa de 467 pruebas pasan. Sin embargo, `green()` no
lee varias evidencias que el propio informe conserva. Codex reprodujo seis
falsos verdes: borrar `rows`; poner `same_agent_object=false` en una frontera;
cambiar la firma real del scratch a `ask=true`; registrar una llamada de
córtex en sus métricas; poner `channel.projection_matches=false`; o marcar la
ablación B como no emparejada. Todos siguen dando `green=True` si los
resúmenes superiores permanecen sin cambiar.

Además, el silencio de T ante rechazo se comprueba sólo mirando
`quiet.t.pred[0]`, que no detecta aprendizaje en otra fila. XFER-1c debe
recomputar la puerta desde `rows`, firmas, métricas, ablación y canal, e
instrumentar las llamadas reales del brazo rechazado. No se toca el animal,
la física ni los números.

Siguiente tajo: XFER-1c. Hasta cerrarlo, **ECHO-1 sigue abierto**.


---

## XFER-1c — la puerta lee la evidencia; cierre aún pendiente

XFER-1b arregló la implementación y sus cifras no se mueven: **B 208 vs 152
(+56), C 224 vs 152 (+72), agregado +128, entrenada 96 / vacía 0 / writes 0,
canal 64 / 62 / cuts 2, PATTERN-0 en 80 / 40 / +40**.

Lo que quedaba era una puerta que se creía los resúmenes que el propio
informe escribe sobre su evidencia.

### Los seis falsos verdes, antes y después

```
                                          antes    después
rows = {}                                 True     False
rows[B]["same_agent_object"] = False      True     False
rows[B] firma del scratch difiere         True     False
arm_metrics[B]["scratch"]["cortex_calls"] = 1
                                          True     False
channel["projection_matches"] = False     True     False
rows[B]["ablation"]["mapping_matched"] = False
                                          True     False
```

Una sola causa: los datos crudos viven en `rows`, `arm_metrics`, `channel` y
`ablation`, y la puerta sólo consultaba copias resumen de nivel superior. La
corrida nominal era buena; el certificado podía contradecirse y seguir verde.

### Una autoridad por afirmación

`evidence(report)` recomputa desde las filas y devuelve `None` si la forma no
es la de un informe. Valida que existan exactamente B y C, que cada fila diga
`same_agent_object`, que sus `protocol_signatures` traigan los tres brazos y
que `signatures_match` sea cierto **sobre esas firmas reales**, que
`arm_metrics` traiga los tres brazos por frontera, y recalcula desde ahí
`false_facts`, `destroyed`, `cortex_calls` y `cortex_rejected`.

`green()` deriva de eso y **ata cada resumen por igualdad** al dato que
resume: recompensas, gains, agregado, gain del control de edad, puntos de
entrada, aciertos de la sonda, las cuatro claves de ablación, las escrituras,
`llm_calls`, `matched_flags` y `protocol_signatures_match`. Un resumen que se
mueva solo cae; un dato crudo que se mueva solo cae; los dos movidos a la vez
caen contra la cláusula directa. Hay un test que hace exactamente eso último
para cada comprobación, porque si no la atadura haría todo el trabajo y la
cláusula podría borrarse sin que nadie lo notara.

El veredicto del canal se deriva **dentro** de `green()` desde
`report["channel"]`: `counts_match`, `projection_matches`, el silencio ante
rechazo y `pattern_observations == t_observations − cuts`.

Un informe ausente o malformado devuelve `False` y no lanza. La red cubre
**todo** el veredicto, no sólo la comprobación de forma: `evidence` valida el
esqueleto y una fila puede seguir sin una hoja que nunca prometió — hay un
test con cinco de esas.

### El rechazo del `self_model`, auditado de verdad

`channel_audit` probaba el silencio de T comparando `quiet.t.pred[0]` antes y
después. Esa fila arbitraria puede quedarse igual mientras T aprende en
cualquiera de las otras 4095 ranuras.

Ahora se instrumentan las llamadas reales a los dos métodos:

```
                          honesto   con fuga en el slot 1234
refused_t_observations       0                1
refused_pattern_observations 0                0
refused_step_silences_both  true            false
t_observations / pattern     64 / 62         64 / 62   (igual)
counts_match / projection   true / true    true / true (igual)
```

`leak_at_slot` hace que T reciba una observación tras el rechazo **fuera de
la fila cero**: la auditoría cae, y todo lo demás de esa corrida queda
idéntico, así que es ese contador el que hace el trabajo. El hook de
`loop.py` no se ha tocado: T y Pattern están en la misma rama y eso estaba
bien; el defecto estaba en cómo se probaba.

### Mutantes

Ocho nuevos requeridos, todos con los resúmenes superiores **deliberadamente
dejados en verde**:

```
las filas crudas desaparecen           un brazo registra un rechazo
una fila dice que el cuerpo no es él   la ablación cruda no está emparejada
la firma cruda del scratch difiere     el canal crudo no cuadra
un scratch llama al córtex             tras el rechazo T observa fuera de la fila 0
```

**40 requeridos** en el informe, todos muertos, sin duplicados, con `green()`
recontando desde la lista.

### Cierre

```
B 208 / 152 / +56        C 224 / 152 / +72        agregado +128
trained 96 / empty 0 / writes 0
channel 64 / 62 / cuts 2
PATTERN-0 80 / 40 / +40
```

### Revisión Codex — XFER-1d requerido

XFER-1c mata los seis falsos verdes que recibió y la suite completa queda en
477 pruebas verdes. El resultado causal no se mueve. Sin embargo, Codex
reprodujo contradicciones residuales que aún dan `green=True`:

```text
channel.refused_t_observations = 1 con silence=true
las tres firmas omiten ask_enabled
las tres firmas llevan ask_enabled=true
ablation.empty.unknown = 0 de 96
ablación de 95 puntos citada junto a entrada de 96
turn_first crudo cambia con matched_turn_values=true
```

Son relaciones exigidas por el propio XFER-1c: el silencio debe derivarse de
los dos contadores, una firma igual también debe ser completa y canónica,
`None` permanece en el denominador, los puntos de ablación deben ser los de
la sonda y el protocolo debe derivarse de las caminatas reales. El tajo
XFER-1d cierra el grafo completo sin tocar el núcleo ni las cifras.

Hasta ese cierre, **ECHO-1 sigue abierto**.

---

## XFER-1d — cerrar el grafo completo de evidencia (verde) · ECHO-1 cerrado

XFER-1c impidió que el certificado contradijera sus filas. Lo que quedaba
era que las filas se contradijeran **entre sí**. Las cifras no se mueven:
**B 208 vs 152 (+56), C 224 vs 152 (+72), agregado +128, entrenada 96 /
vacía 0 / writes 0, canal 64 / 62 / cuts 2 · rechazos 0 / 0, PATTERN-0 en
80 / 40 / +40**.

### Los seis contraejemplos, antes y después

```
                                                       antes   después
channel["refused_t_observations"] = 1                  True    False
los tres brazos pierden `ask_enabled`                  True    False
ablation["empty"]["unknown"] = 0                       True    False
ablación de 95 puntos junto a sonda de 96              True    False
rows[B]["transfer"]["turn_first"] += 1                 True    False
los tres brazos con ask=true, iguales entre sí         True    False
```

Y los seis de XFER-1c siguen dando `False`.

### Igualdad no es corrección

`signatures_match()` demuestra que los tres brazos coinciden. Tres brazos
que **todos** tienen `ask_enabled=True` coinciden perfectamente y los tres
incumplen el protocolo; tres brazos a los que les falta **la misma** clave
también coinciden. Así que hay un `XFER1_PROTOCOL` literal —fijado en un
test contra `protocol_signature(new_agent())`, para que un cambio en
`new_agent` salga rojo en vez de mover la expectativa consigo— y cada firma
se compara con él, campo a campo y con los tipos comprobados: `0 == False`
en Python, así que `ask_enabled: 0` compararía igual sin la comprobación de
tipo.

### Un validador por estructura

```
signature_evidence   claves, tipos, igualdad entre brazos, igualdad al protocolo
walk_evidence        entry_cell, turns, turn_first, turn_last, fingerprint
                     recomputado como suma del rango, iguales en los tres brazos,
                     turns == WINDOW_TURNS, entry_cell == SEAT
pattern_evidence     tipos, rangos, hits+unknown <= points, observes == 0,
                     mismos puntos en las tres sondas, la ablación atada a
                     esos puntos, y la tabla publicada
channel_evidence     turns 64, t_observations == turns, cuts == len(saltos) == 2,
                     saltos [0, 32], pattern == t − cuts, y el silencio
                     recomputado de sus dos contadores
```

Cada uno devuelve `None` en vez de un booleano que alguien pueda poner a
`True`. Ninguno cree un booleano de la fila: `matched_turn_values` movido a
uno y `turn_first` movido en uno pasaba, y ahora no.

El fingerprint es la suma de los valores de turno, así que se **recomputa**
desde el primer turno y la cuenta: no se puede mover sin mover uno de ésos.

### Denominadores completos

```
sondas de entrada    transfer 96 / 96 / 0 unknown
                     scratch y age 0 / 96 unknown
                     observes 0 en las tres
ablación             points 96 · known_slots 96 · mapping_matched
                     entrenada 96 / 0 unknown · vacía 0 / 96 unknown
                     writes == entrenada.observes + vacía.observes == 0
```

`None` sigue dentro del denominador, y ahora el predictor vacío tiene que
**declarar** sus unknowns: `unknown = 0` junto a `points = 96` es una
memoria diciendo que contestó.

Algunas de esas comprobaciones no se pueden alcanzar a través de un informe
entero —la tabla publicada fija `hits` y `unknown` exactamente, así que una
violación de rango la caza la tabla primero— así que se prueban donde
viven: hay un test que llama a `_probe_ok`, `walk_evidence`,
`signature_evidence` y `channel_evidence` directamente con valores fuera de
rango, de tipo equivocado y con claves ausentes.

### Bends coherentes

Un test dobla **los tres brazos a la vez** —fingerprint, ventana, asiento,
turno final— para que la comparación entre brazos quede satisfecha y sólo
la recomputación pueda rechazar. Y dos bends de ablación en direcciones
opuestas: las sondas a 48 con la ablación en 96, y la cabecera de la
ablación a 48 con sus dos brazos y la sonda en 96. Sin ese segundo, la
atadura entre los puntos de la ablación y los de la sonda era un agujero
real y no una redundancia.

### Cláusulas duplicadas, retiradas

Ocho cláusulas de `green()` que otra cláusula ya cubría se han ido, porque
ningún mutante podía matarlas: la comprobación del juego de claves de la
firma (subsumida por los tipos y por la desigualdad), las identidades y el
protocolo emparejado repetidos en el bucle de booleanos, la atadura de las
recompensas escrita dos veces, y la atadura de la ablación duplicada entre
`green` y `pattern_evidence` — ahora vive sólo donde vive esa estructura.

### Locks

```
mismas cifras · informe determinista · loop.py, mundos, física, rewards,
turnos, posiciones, riff y CAM/Q/T/PatternMemory sin tocar
```
