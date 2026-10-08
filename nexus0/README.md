# NEXUS-0 code

Implements `../docs/05-NEXUS-0-SPEC.md`. Import navi10 primitives from
the repo root. Do not clone LIF.

| Module | Role |
|---|---|
| `constants.py` | frozen integers |
| `types.py` | State, Metrics, clip |
| `qtable.py` | Q[4096][3] int8 |
| `world.py` | T(s,a) → ŝ' |
| `encoder.py` | bank → lex → DESCONOCIDO; FNV is baseline only |
| `lex.py` | host port of `kernel/navi/wsp_lex.c`, 235 n-grams |
| `gate.py` | OK / MODIFY / BLOCK |
| `env.py` | 32-cell ring |
| `loop.py` | one cognitive step, cortex absent |
| `bench.py` | 256 turns + JSON report |
| `bank/canonical.json` | vendor phrases |

`wsp_lex.c` is ported and FNV is out of the production path (2026-09-03).
A text with no n-gram is DESCONOCIDO, not a hash.

Known limits, measured not guessed:

- 11 of the 235 rows are unreachable, shadowed by an earlier substring key.
  Same in the C: first-match-wins is the contract, not a bug of the port.
- A miss collapses every unknown text onto one 16 B packet
  (`YO → DESCONOCIDO → UNK`). Not yet distinguished.
- Multi-thought input emits the first packet only: "estoy solo pero quiero
  conectar" → `SER → SOLEDAD`. Second packet is NEXUS-1 (spec §3).

Cells ride the same cable since 2026-09-03: `encode_cell` sets
`rel`/`dst` per kind (THREAT → `TEMER → PELIGRO`, GOAL → `DESEAR → AQUI`,
NOVEL → `DESCONOCIDO → UNK`, EMPTY → `OBSERVAR → AQUI`) and keeps
`seq=index`, without which two same-kind cells collide onto one Q row.
`bench.py` reports `sample_wsp`: 8 compact packets, atoms not hex.

## T vs the arithmetic baselines

`prediction_accuracy` on its own is theatre, so the bench prints what T
has to beat, all three scored on the same turns
(`prediction_known_turns`, the shared denominator):

| predictor | accuracy | what it is |
|---|---|---|
| `persist` (ŝ' = s) | 0.0142 | nothing moves |
| `ring` (i±1 mod 32) | 0.9715 | closed-form arithmetic |
| T(s,a) | **0.9964** | learned table |

T beats ring because two cells jump +2; the arithmetic baseline does not
know that. That is the first world-model number that is not the env's own
formula.

Before the JUMP cells the ring scored 1.0000 and T 0.9964 — the ring
*was* the world, so T could only copy it and lose a turn to the phase F
threat move. `t_beats_ring` did not exist as a key then; it does now, and
`test_t_beats_ring` is the lock that replaced
`test_t_does_not_beat_ring_arithmetic`. If it ever goes red the answer is
more turns or more exploration, stated as a number — not a lower bar.

Raw counts behind those rates, 320 turns, `prediction_known_turns` = 281:
T 280 hits, ring 273, persist 4. `jump_hits` = 10 approaches taken from
cells 5 and 21; the ring misses 8 predictions and T misses 1 (one stale
transition after the phase F threat move, `conflicts` = 1). The margin of
7 is the jump geometry the arithmetic cannot see.

## Keeping lex.py honest

`lex.py` is generated, not hand-maintained:

```
python3 -m echoai.nexus0.tools.gen_lex --check   # 0 in sync, 1 drift
python3 -m echoai.nexus0.tools.gen_lex           # rewrite the table
```

It rewrites only the region between the BEGIN/END markers, reads
`kernel/navi/wsp_lex.c` and never writes it, and is idempotent. Row order
stays C order; the 11 shadowed rows stay shadowed.

## plan.py — NEXUS-2

NEXUS-2 is a planner over T, not a bigger table. The 320-turn bench still
uses `Q.best`; the planner is gated by unit tests until it is wired as a
`select()` option.

`plan.scores(world, q, slot, depth)` returns one int8 per action:

```
score[a] = clip_i8(max( Q[slot][a], lookahead[a] ))
lookahead[a] = Q[slot][a]                    if T misses
             = max_b Q[ŝ'][b]                at depth 1
             = (7 * value(ŝ')) // 8          at depth 2
```

Depth 2 costs 3×3 leaf evaluations. No reward is invented. The root term
is what keeps the planner from sitting down when successors are still
flat; it is optimistic, so a bad successor cannot pull an action below
its own root Q.

The test that matters is distance 2: with `T(13,approach)=14`,
`T(14,approach)=15` and `Q[15,approach]=80`, the myopic row 13 is all
zeros so `Q.best(13)` returns wait, while `plan.best(13, depth=2)` scores
`[70, 0, 0]` and returns approach. Depth 1 scores `[0, 0, 0]` and also
says wait — the second step is doing the work, not a tie-break.

Where the planner does *not* yet see: `score = max_b Q[s'][b]` hides a bad
action behind a good sibling. A successor with `approach = -40` but
`avoid = 0` scores 0, so approach is only rejected by the tie-break. It
loses on score only when the whole successor row is negative. Both cases
are pinned in `test_planner_avoids_jump_into_threat`.

### Opt-in, and what it costs

`Agent(plan_depth=2)` swaps the exploit step for `plan.best`; ε-greedy and
full-tie exploration still come from `Q.select`, or the ring is never
walked. Default stays `plan_depth=0`.

```
python3 -m echoai.nexus0.bench                   # lab/nexus0_report.json
python3 -m echoai.nexus0.bench --plan-depth 2    # lab/nexus0_plan2_report.json
```

320 turns, same seed, separate files:

| | default | plan-2 (max_b root) | plan-2 (root max) |
|---|---|---|---|
| `policy_after` (threat row) | [-12, +5, 0] | [-4, +5, 0] | [-7, +5, 0] |
| `phase_e_action` | 1 avoid | 1 avoid | 1 avoid |
| `phase_g_action` | 1 avoid | 2 wait | 2 wait |
| `jump_hits` | 10 | 11 | 3 |
| `action_success` | 0.2938 | 0.0813 | 0.0969 |
| `prediction_accuracy` | 0.9964 | 1.0000 | 1.0000 |
| `t_beats_ring` | True | True | True |
| `false_facts` / `destroyed` / `cortex_calls` | 0/0/0 | 0/0/0 | 0/0/0 |

Action mix over 256 training turns:

| | approach | avoid | wait |
|---|---|---|---|
| default | 73 % | 24 % | 2 % |
| plan-2, before the root max | 19 % | 8 % | 71 % |
| plan-2, with the root max | 30 % | 11 % | **58 %** |

The root max helped — 71 % → 58 % wait, `jump_hits` 11 → 3, and
`action_success` up — but wait still dominates, and the reason is not the
root. It is `T(s, wait) = s`: waiting is a self-loop, so its lookahead is
`max_b Q[s][b]`, the maximum of the row it is already standing in. Wait
therefore ties with the best root term available and takes the tie-break.
`test_planner_avoids_jump_into_threat` pins the shape: a row `[0, 5, 0]`
scores `[0, 5, 5]`, and avoid loses to wait despite being the only action
that earned anything.

Discounting the depth-1 lookahead (`(7 * max_b Q[ŝ'][b]) // 8`) would make
a self-loop strictly worse than acting. Measured in a scratch run, it
takes plan-2 to 73/24/2, `action_success` 0.2938, `policy_after`
[-12, +5, 0], `jump_hits` 10 — i.e. exactly the default: the planner then
agrees with `Q.best` on every exploit turn of this ring. Not applied, and
worth knowing before wiring anything: in a 32-cell ring TD already fills
the neighbouring rows, so a depth-2 lookahead has nothing left to add.
That decision belongs to the next slice.

Next slices (do not skip KPI tests): measure the DESCONOCIDO rate on a
held-out ES corpus; decide whether `select()` gets a planner option, and
what it costs the 320-turn KPI.
