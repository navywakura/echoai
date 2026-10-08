"""
One-step cognitive loop. Cortex is not a module here; cortex_calls stays 0.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.qn import SLOT_FLAG_INHIBIT, hamming16, simhash16
from echoai.core.spoke import encode_event
from echoai.core.wsp import E_NAMES

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_REL,
    ATTEND_SETTLED_HITS,
    BENCH_TURNS,
    ESC_MARGIN,
    GATE_BLOCK,
    HAM_MISS,
    JUMP_CELLS,
    N_ACTIONS,
    N_CELLS,
    N_SLOTS,
    SAMPLE_TURNS,
    T_MISS_ERROR,
)
from echoai.nexus0 import cortex, cortex_turn, escalate, oracle, plan, thought
from echoai.nexus0.escalate import LEVEL_Q, LEVEL_SEARCH
from echoai.nexus0.attend import REASON_CONFLICT, REASON_OFF, attend
# Imported by name: the Agent kwarg `cortex` shadows the module in __init__.
from echoai.nexus0.cortex import ENV_LOG

ENV_THOUGHT = "NAVI_THOUGHT_LOG"
from echoai.nexus0.encoder import ATOM_ID, E_ASK, compact, encode_ask, encode_cell, rel_of
from echoai.nexus0.env import Cell, KIND_NOVEL, KIND_THREAT, NOVEL_CLEAR, RingEnv
from echoai.nexus0.gate import gate
from echoai.nexus0.pattern import PatternMemory
from echoai.nexus0.qtable import QTable
from echoai.nexus0.types import Metrics, default_e
from echoai.nexus0.world import World


# CAM wants E as a V,A,D,C,U,B tuple; the encoder keeps it as a dict for
# pack(). One source, two shapes.
E_ASK_6 = tuple(E_ASK[k] for k in E_NAMES)


class Agent:
    def __init__(self, plan_depth: int = 0, ask: bool = True,
                 trace: bool = False, remainder: bool = False,
                 explore_flat: bool = False,
                 cortex: bool = False,
                 cortex_log: Optional[str] = None,
                 thought_log: Optional[str] = None,
                 escalate: bool = False,
                 conflict_attend: bool = False,
                 pattern_memory: bool = False,
                 oracle_path: Optional[str] = None,
                 n_actions: Optional[int] = None,
                 initial_h: Optional[int] = None,
                 initial_temperature: Optional[int] = None,
                 observe_temperature: bool = True,
                 temperature_bands: int = 4,
                 env=None,
                 inherited_b: int = 0,
                 evidence_budget: int = 0,
                 evidence_greedy: bool = True) -> None:
        self.cam = Cam()
        # OPEN-1: how many gears the world handed to this agent has. None
        # is the frozen three and every default bench takes exactly the
        # path it always took. A wider agent folds its proposal, its gate
        # and its Q row to *this* number, because folding to three would
        # hand the environment an approach every time the policy said
        # `open` — the verb would never reach the physics.
        self.n_actions = N_ACTIONS if n_actions is None else int(n_actions)
        # CREDIT-1: the remainder is opt-in and off by default, so the
        # ring's locks are measured on exactly the update they always had.
        # PULPO-C: `explore_flat` is opt-in the same way, and touches only
        # select() — the ring never asks for it.
        self.q = QTable(trace=trace, remainder=remainder,
                        explore_flat=explore_flat,
                        n_actions=self.n_actions,
                        inherited_b=inherited_b)
        self.t = World(n_actions=self.n_actions)
        self.metrics = Metrics()
        if (type(evidence_budget) is not int
                or evidence_budget not in (0, 1, 2, 4, 8, 16)):
            raise ValueError("evidence_budget must be one of 0, 1, 2, 4, 8, 16")
        # GEN-1b: one inherited integer. Zero keeps every older agent on
        # QTable's exact selection path; positive values reuse T.n as local
        # evidence and allocate no parallel memory.
        self.evidence_budget = evidence_budget
        if type(evidence_greedy) is not bool:
            raise ValueError("evidence_greedy must be bool")
        self.evidence_greedy = evidence_greedy
        self.last_evidence_explore = False
        # GEN-1 bench instrumentation. These expose the existing decision
        # path; they do not add a policy or feed anything back into it.
        self.last_proposed_action: Optional[int] = None
        self.last_gate_decision: Optional[int] = None
        self.last_explore = False
        # NEXUS-4i: the same agent can be handed a different world. Default
        # is the ring, so every lock above is measured on exactly what it
        # always was. A world only has to answer cell()/step()/reset()/
        # teleport()/reveal() and expose `kind`.
        self.env = RingEnv() if env is None else env
        self.survival_enabled = initial_h is not None
        self.thermal_enabled = initial_temperature is not None
        if type(observe_temperature) is not bool:
            raise ValueError("observe_temperature must be bool")
        if type(temperature_bands) is not int or temperature_bands not in (4, 8):
            raise ValueError("temperature_bands must be 4 or 8")
        self.temperature_bands = temperature_bands
        self.temperature_observed = self.thermal_enabled and observe_temperature
        if self.thermal_enabled and not self.survival_enabled:
            raise ValueError("temperature requires vitality")
        if self.survival_enabled:
            if type(initial_h) is not int or not 1 <= initial_h <= 127:
                raise ValueError("initial_h must be an integer in 1..127")
            step_name = "step_homeostatic" if self.thermal_enabled else "step_vital"
            if not callable(getattr(self.env, step_name, None)):
                raise ValueError(f"survival requires an environment with {step_name}")
            if cortex or plan_depth or escalate:
                raise ValueError("VITA-1 requires cortex and planning off")
            self.initial_h = initial_h
            self.H = initial_h
            if self.thermal_enabled:
                if (type(initial_temperature) is not int
                        or not 1 <= initial_temperature <= 126):
                    raise ValueError(
                        "initial_temperature must be an integer in 1..126")
                self.initial_temperature = initial_temperature
                self.temperature = initial_temperature
            self.episode_terminal = False
            self.life_turns = 0
            self.life_id = 0
            self.deaths = 0
            self.last_reward = 0
        self.sample_wsp: list = []  # first SAMPLE_TURNS packets, atoms not hex
        # 0 = NEXUS-0/1 default: Q.select decides, planner never runs.
        # 1 or 2 = opt-in NEXUS-2 lookahead on exploit turns only.
        self.plan_depth = int(plan_depth)
        # SELF-1: one integer, "my approach pushes along (h + body_offset)".
        # 0 is "the arm is the arm I learned with", which is what the ring
        # has always assumed without needing to say so. `self_model` is the
        # thing allowed to change it; None means every surprise goes
        # straight into T, exactly as before.
        self.body_offset = 0
        self.self_model = None
        # NEXUS-3 PREGUNTAR is on by default: it is epistemology, not
        # policy. No reward changes, so the NEXUS-0 locks must not move.
        self.ask_enabled = bool(ask)
        self.last_ask: Optional[bytes] = None
        # NEXUS-4h: who answers. Not the env — it has no ask() any more.
        # --no-ask is silence, not a mute oracle: there is nobody to ask.
        self.oracle = oracle.from_path(oracle_path) if self.ask_enabled else None
        # NEXUS-4a: the switch, off by default. The main bench must keep
        # cortex_calls == 0 (docs/02-INVARIANTS.md).
        self.cortex_enabled = bool(cortex)
        self.last_attend: tuple = (False, REASON_OFF)
        # CORTEX-1: the slow clock's proposal for *this* turn, or None.
        # A hypothesis with a lifetime of one turn: _propose consumes it,
        # the gate still has the last word, and it is never written to
        # CAM, T or Q as a fact.
        self.last_cortex_action: Optional[int] = None
        # Where woken turns are recorded. NAVI_CORTEX_LOG wins; otherwise
        # only an explicit path writes. No cortex, no file.
        env_log = os.environ.get(ENV_LOG, "").strip()
        self.cortex_log: Optional[str] = (
            (env_log or cortex_log) if self.cortex_enabled else None
        )
        # Every turn, not just the woken ones. Independent of --cortex.
        env_thought = os.environ.get(ENV_THOUGHT, "").strip()
        self.thought_log: Optional[str] = env_thought or thought_log
        # NEXUS-4f: let ΔQ decide whether the planner runs. Off by default,
        # so _propose stays the one that produced [-12, +5, 0]. Counters
        # answer the only question worth asking of rung 2 in this ring:
        # when it does run, does it say anything Q did not?
        self.escalate_enabled = bool(escalate)
        self.level_counts = {LEVEL_Q: 0, LEVEL_SEARCH: 0}
        self.search_copies_q = 0
        self.search_differs = 0
        # Of the disagreements, how many the planner actually scores
        # higher. `differs` alone would flatter rung 2: plan.best breaks a
        # tie to wait, so a disagreement is not by itself new information.
        self.search_strictly_better = 0
        # XFER-1: PATTERN-0's order-2 context memory, as an **extension of
        # the predictor this loop already has** and off by default. None
        # means every line below is skipped and the ring's numbers are the
        # ones it has always had — there is no second T, no second CAM, no
        # second log and no second bus.
        #
        # `prev_slot` is the whole of the extra state: where the body was
        # last turn. It is a latch, not a memory, and `clear_context()`
        # drops it at a world boundary so a transition cannot start in one
        # world and end in another.
        self.pattern_memory = PatternMemory() if pattern_memory else None
        self.prev_slot: Optional[int] = None
        # SIGN-C: the fifth reason, opt-in and off by default, so every
        # bench above is measured on the ATTEND that produced its numbers.
        # It needs the slow clock to be on at all — there is nothing to
        # wake otherwise — and it is the only path in this file that reads
        # a fact the world produced *after* the action was chosen.
        self.conflict_attend = bool(conflict_attend)
        self.conflict_wakes = 0
        # One turn of suppression after a conflict wake. A causal query is
        # already pending, so the ordinary ATTEND must not spend a second
        # call on the consuming turn — and it is cleared whatever came
        # back, silence and rejection included.
        self.conflict_suppressed = False

    def clear_context(self) -> None:
        """Drop the one-turn latch. Not a forgetting of anything.

        CAM, Q, T and the pattern memory are untouched: what goes is the
        claim that the body was somewhere a moment ago, which stops being
        true the instant the world underneath it is swapped.
        """
        self.prev_slot = None

    def observation(self, cell) -> bytes:
        """Same encoder, with physiological observation only when enabled."""
        if self.survival_enabled:
            return encode_cell(
                cell.index, cell.kind, vitality=self.H,
                temperature=self.temperature if self.temperature_observed else None,
                temperature_bands=self.temperature_bands)
        return encode_cell(cell.index, cell.kind)

    def respawn(self) -> None:
        """Start the next life after death, retaining learned memory."""
        if not self.survival_enabled or not self.episode_terminal:
            raise RuntimeError("respawn requires a terminal survival episode")
        self.env.reset()
        self.H = self.initial_h
        if self.thermal_enabled:
            self.temperature = self.initial_temperature
        self.episode_terminal = False
        self.life_turns = 0
        self.life_id += 1
        self.last_reward = 0
        self.body_offset = 0
        self.clear_context()
        self.q.reset_traces()
        self.last_cortex_action = None
        self.last_ask = None
        self.last_attend = (False, REASON_OFF)
        self.conflict_suppressed = False

    def _predict(self, slot: int, a: int) -> Optional[int]:
        """T, extended by context where the context has a rule.

        The same prediction the loop already made — `pred_next` below is
        what surprise, `s`, `pred_hits` and the conflict wake are all
        computed from. With the memory off this is `self.t.predict` and
        nothing else.
        """
        if self.pattern_memory is not None and self.prev_slot is not None:
            hit = self.pattern_memory.predict(self.prev_slot, slot, a)
            if hit is not None:
                return hit
        return self.t.predict(slot, a)

    def _ask(self, cell, cell_slot: int) -> bool:
        """PREGUNTAR: emit a question, take an answer from outside.

        Not a movement action and not in env.step: the ring still has three.
        At most once per cell — the cleared extract on the cell's slot is
        the record that stops a second ask. Epistemology, not policy.

        NEXUS-4h, the order that matters: something outside the world
        replies, VERIFY (`oracle.accept`) decides whether that is testimony
        a fact can be made of, and only then is the physics told. A reply
        that fails the gate is counted and changes nothing — the trap stays
        armed and no has_fact is written from it.
        """
        s = self.cam.slot[cell_slot]
        if cell.kind != KIND_NOVEL or NOVEL_CLEAR in s.extract:
            return False
        if self.oracle is None:
            return False

        wsp_ask = encode_ask()
        self.last_ask = wsp_ask
        self.metrics.questions += 1

        answer = oracle.accept(self.oracle.reply())
        if answer is None:
            self.metrics.oracle_rejected += 1
            return False

        v_ask, _, _ = encode_event(wsp_ask)
        # The question's own packet carries where the answer came from.
        # The cell's packet keeps source="nexus0-env": the ring perceived
        # the cell, a sensor answered about it, and the two must not blur.
        self._slot_for(wsp_ask, v_ask, answer, E_ASK_6, source=self.oracle.source)

        # The cell's own slot remembers that it has been asked.
        s.extract = f"{s.extract} {answer}".strip()
        s.has_fact = 1
        self.env.reveal(answer)  # physics last, and only after VERIFY
        return True

    def _attend(self, cell, cell_slot: int, s, e6, ham: int) -> bool:
        """Wake the slow clock only when the fast path is not enough.

        The count lives here, not in cortex.py, so cortex_calls records a
        decision the loop made. Whatever comes back is a packet: if it is
        a PREGUNTAR it goes through _ask(), the one path to the oracle,
        so a hypothesis can never become a fact by another door.
        """
        # Certainty from what the fast loop holds, not from the packet's E.
        # A slot seen ATTEND_SETTLED_HITS times that still has a flat Q row
        # is a settled boring cell, not an open question — most of this ring
        # pays nothing and stays flat forever. Without that gate the two
        # flat-row reasons (no preference, and no map for the wait that no
        # preference implies) are the same fact counted twice, and waking on
        # them costs 112 of 256 turns.
        row = self.q.row(cell_slot)
        # The table's own answer, not a literal triple. For a table of the
        # frozen width `flat()` *is* `row[0] == row[1] == row[2]`, so the
        # ring's 36 wakes are the same expression they always were; a
        # four-gear agent no longer reads a row that ties on its first
        # three as settled while its fourth gear still has a vote.
        tied = self.q.flat(row)
        settled = tied and s.hits >= ATTEND_SETTLED_HITS
        q_confident = (not tied) or settled
        best = self.q.best(cell_slot)
        t_known = settled or (self.t.predict(cell_slot, best) is not None)
        # How good the row is, not just whether it exists. In this wiring
        # t_known is the same fact at conf >= 1, so the quality only ever
        # confirms an OFF; it earns its place when a row can be known and
        # bad, which is where the inverse model goes next.
        t_conf = self.t.conf(cell_slot, best)
        on, reason = attend(
            slot_hit=s.occupied != 0,
            extract_ok=bool(cell.extract),
            E=e6,
            kind_novel=cell.kind == KIND_NOVEL,
            ham=ham,
            q_confident=q_confident,
            t_known=t_known,
            t_conf=t_conf,
        )
        self.last_attend = (on, reason)
        if not on:
            return False
        self.metrics.cortex_calls += 1

        wsp_in = encode_cell(cell.index, cell.kind)
        wsp_c = cortex.propose(wsp_in, reason)

        # A local binary may answer instead — but only in atoms. Prose,
        # JSON or a claim in words is rejected and the stub's packet stands.
        record = cortex_turn.build(
            turn=self.metrics.turns,
            reason=reason,
            wsp_in=wsp_in,
            wsp_out=wsp_c,
            slot=cell_slot,
            ham=ham,
            q_row=row,
            t_pred=self.t.predict(cell_slot, self.q.best(cell_slot)),
            extract=s.extract,
        )
        reply = cortex.complete(record)
        spoke = False
        if reply is not None:
            parsed = cortex.parse_reply(reply)
            if parsed is not None:
                wsp_c = parsed
                spoke = True
                record = cortex_turn.build(
                    turn=self.metrics.turns,
                    reason=reason,
                    wsp_in=wsp_in,
                    wsp_out=wsp_c,
                    slot=cell_slot,
                    ham=ham,
                    q_row=row,
                    t_pred=record["t_pred"],
                    extract=s.extract,
                )
            else:
                self.metrics.cortex_rejected += 1

        self._log_cortex(record)
        rel = rel_of(wsp_c)
        if rel == ATOM_ID["PREGUNTAR"]:
            # Unchanged since NEXUS-3, and deliberately not an action: the
            # stub already asks, so a question is not the slow clock
            # changing a decision.
            self._ask(cell, cell_slot)
        elif spoke and rel in ACTION_REL:
            # CORTEX-1. UNIR / TEMER / OBSERVAR are a *proposal*: _propose
            # hands it to the gate like any other, and nothing is written
            # to CAM, T or Q from it.
            #
            # `spoke` is load-bearing. cortex.propose() hands the
            # observation back unchanged when it has no hypothesis, and an
            # EMPTY cell's own packet already reads OBSERVAR (a THREAT's
            # reads TEMER). Treating that echo as advice would let the ring
            # take orders from its own perception. Only a reply that came
            # from outside and survived parse_reply proposes.
            self.last_cortex_action = ACTION_REL.index(rel)
        return True

    def _conflict_origin(self, cell, cell_slot: int, cam_miss: int):
        """What the origin held before the world answered, or None.

        Read at the top of the turn and used at the bottom: a
        contradiction is not knowable until `env.step()` has spoken, and
        by then the body is somewhere else. This is the record of where
        the commitment was made, not of where it was found out.

        Three things have to be true of the origin, and each is a way the
        turn could be uninteresting instead of contradictory:

        - **The world put language here.** `Cell.extract` synthesises
          `cell=N kind=...` when a world has nothing to say, and that
          label is this loop's own writing, not a sign. It is rejected
          twice over: `extract_text is None` never qualifies, and a world
          that hands back exactly the string the loop would have written
          anyway has still told the slow clock nothing. The two are not
          independent — `extract_text is None` *is* the case where
          `cell.extract` returns that label, so the second check already
          covers the first and no mutant can separate them. The first is
          kept because it is the contract (`extract_text`, not `extract`)
          and because it says so at the top of the function instead of
          leaving it to be inferred from a string comparison.
        - **Q was committed.** Below `ESC_MARGIN` the fast loop was nearly
          indifferent, and being wrong about a coin-flip is not news.
        - **The origin was not a CAM miss.** A place seen for the first
          time cannot contradict anything; that is `REASON_MISS`, and it
          already has a rung.

        T is the fourth condition and is checked at the other end, where
        the prediction lives: an unknown row predicts nothing, so nothing
        it said can be contradicted.
        """
        if cam_miss:
            return None
        text = getattr(cell, "extract_text", None)
        if text is None:
            return None
        text = str(text)
        if not text.strip():
            return None
        if text.strip() == Cell(index=cell.index, kind=cell.kind).extract:
            return None
        margin = self.q.margin(cell_slot)
        if margin < ESC_MARGIN:
            return None
        return {
            "slot": int(cell_slot),
            "index": int(cell.index),
            "kind": int(cell.kind),
            "text": text,
            "margin": int(margin),
            "q_row": self.q.row(cell_slot),
        }

    def _conflict_wake(self, origin: dict, ham: int, pred_next: int,
                       slot_n: int) -> bool:
        """The world contradicted a confident prediction. Ask, once.

        Same cable as `_attend`: one `cortex_turn` record out, at most 16 B
        back, `parse_reply` between them. What is new is only *when* — the
        query is made after the evidence exists, and what it carries is the
        origin's own record, so the sentence the world posted is read
        because a prediction failed and not before.

        Nothing here writes: no CAM, no T, no Q. The proposal is the same
        one-turn hypothesis CORTEX-1 defined, `_propose` consumes it next
        turn, and the gate still has the last word. A reply that is a
        PREGUNTAR is not an action and does nothing — `_ask` stays the one
        path to the oracle and a conflict is not a question about a novel
        cell.
        """
        self.conflict_wakes += 1
        self.metrics.cortex_calls += 1
        self.last_attend = (True, REASON_CONFLICT)
        # The origin's packet, not the landing cell's: the body is already
        # somewhere else and the slow clock is being asked about the place
        # where the commitment was made.
        wsp_in = encode_cell(origin["index"], origin["kind"])
        wsp_c = cortex.propose(wsp_in, REASON_CONFLICT)

        def _record(out: bytes) -> dict:
            return cortex_turn.build(
                turn=self.metrics.turns,
                reason=REASON_CONFLICT,
                wsp_in=wsp_in,
                wsp_out=out,
                slot=origin["slot"],
                ham=int(ham),
                q_row=origin["q_row"],
                t_pred=int(pred_next),
                extract=origin["text"],
            )

        record = _record(wsp_c)
        reply = cortex.complete(record)
        spoke = False
        if reply is not None:
            parsed = cortex.parse_reply(reply)
            if parsed is not None:
                wsp_c = parsed
                spoke = True
                record = _record(wsp_c)
            else:
                self.metrics.cortex_rejected += 1
        self._log_cortex(record)
        rel = rel_of(wsp_c)
        if spoke and rel in ACTION_REL:
            self.last_cortex_action = ACTION_REL.index(rel)
        # Whatever came back — an atom, a rejection, silence — the query
        # has been spent. The next turn belongs to it.
        self.conflict_suppressed = True
        return True

    @staticmethod
    def _append(path_str: str, line: str) -> None:
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def _log_cortex(self, record: dict) -> None:
        """Append one line per wake. No path, no file — the default bench
        must not create a jsonl at all."""
        if not self.cortex_log:
            return
        self._append(self.cortex_log, cortex_turn.to_line(record))

    def _propose(self, slot: int, turn_i: int, greedy: bool = False) -> int:
        """Action before the gate. Exploration is never taken from ε-greedy."""
        # CORTEX-1: a hypothesis lasts one turn and is consumed whether it
        # is used or not, so a stale proposal can never act twice. It is
        # still only a proposal — the gate runs on it exactly as it runs
        # on Q's answer.
        hypothesis, self.last_cortex_action = self.last_cortex_action, None
        if hypothesis is not None:
            self.metrics.cortex_actions += 1
            return int(hypothesis) % self.n_actions
        if self.evidence_budget and not greedy:
            action = self._evidence_action(slot, turn_i)
            if action is not None:
                self.last_evidence_explore = True
                return action
            # GEN-1e: the evidence policy replaces the historical clock.
            # Once every local action has met the inherited requirement,
            # the contract says to trust Q; returning through q.select()
            # would silently resume periodic exploration and make b only
            # a short prelude to the old policy.
            if self.evidence_greedy:
                return self.q.best(slot)
        if self.plan_depth <= 0 and self.escalate_enabled:
            return self._escalated(slot, turn_i, greedy=greedy)
        if self.plan_depth <= 0:
            return self.q.select(slot, turn_i, greedy=greedy)
        if self.q.is_explore(slot, turn_i, greedy=greedy):
            return self.q.select(slot, turn_i, greedy=greedy)
        return plan.best(self.t, self.q, slot, depth=self.plan_depth)

    def _evidence_action(self, slot: int, turn_i: int) -> Optional[int]:
        """Least-observed local action until inherited evidence is met."""
        state = int(slot) & (N_SLOTS - 1)
        counts = self.t.n[state]
        least = min(counts)
        start = int(turn_i) % self.n_actions
        if least < self.evidence_budget:
            for offset in range(self.n_actions):
                action = (start + offset) % self.n_actions
                if counts[action] == least:
                    return action
        return None

    def _escalated(self, slot: int, turn_i: int, greedy: bool = False) -> int:
        """Rung 0 or rung 2, chosen by ΔQ. Exploration keeps its turns.

        A full tie and every ε turn go through `q.select` untouched: if the
        planner ate those, the ring would never be walked and the flat rows
        it plans over would stay flat.
        """
        if self.q.is_explore(slot, turn_i, greedy=greedy):
            return self.q.select(slot, turn_i, greedy=greedy)
        lvl = escalate.level(
            margin=self.q.margin(slot),
            t_conf=self.t.conf(slot, self.q.best(slot)),
            kind_novel=False,
            extract_ok=True,
            cortex_enabled=self.cortex_enabled,
        )
        self.level_counts[lvl] = self.level_counts.get(lvl, 0) + 1
        if lvl != LEVEL_SEARCH:
            return self.q.best(slot)
        a_q = self.q.best(slot)
        a_plan = plan.best(self.t, self.q, slot, depth=2)
        if a_plan == a_q:
            self.search_copies_q += 1
        else:
            self.search_differs += 1
            sc = plan.scores(self.t, self.q, slot, depth=2)
            if sc[a_plan] > sc[a_q]:
                self.search_strictly_better += 1
        return a_plan

    def _slot_for(
        self, wsp: bytes, vertex: int, extract: str, e6, source: str = "nexus0-env"
    ) -> int:
        slot = self.cam.get(wsp)
        if slot >= 0:
            return slot
        slot, _ = allocate(
            self.cam,
            wsp,
            vertex,
            0,
            e6,
            has_fact=1 if extract else 0,
            extract=extract,
            source=source,
            label=extract[:40],
            key=wsp,
        )
        if slot < 0:
            self.metrics.unknown += 1
            return 0
        return slot

    def _ring_slot(self, i: int, a: int) -> int:
        """Baseline: the ring's own geometry. Not learned, just arithmetic.

        Uses the env cell index, then asks CAM for that cell's slot; a cell
        never seen has no slot and the baseline scores a miss.
        """
        aa = int(a) % self.n_actions
        n = len(self.env.kind)  # 32 for the ring; a corridor is shorter
        if aa == ACTION_APPROACH:
            j = (int(i) + 1) % n
        elif aa == ACTION_AVOID:
            j = (int(i) - 1) % n
        else:
            j = int(i)
        return self.cam.get(encode_cell(j, self.env.kind[j]))

    def turn(self, turn_i: int, greedy: bool = False) -> int:
        if self.survival_enabled and self.episode_terminal:
            raise RuntimeError("episode is terminal; call respawn before acting")
        cell = self.env.cell()
        wsp = self.observation(cell)
        if len(self.sample_wsp) < SAMPLE_TURNS:
            # c<i> is ext.seq: two EMPTY cells are different 16 B packets
            # even though their atoms read the same.
            self.sample_wsp.append(f"t{turn_i} c{cell.index} {compact(wsp)}")
        if cell.kind == KIND_NOVEL:
            self.metrics.novel_visits += 1
        vertex, lat, _ticks = encode_event(wsp)
        e6 = default_e()
        if cell.threat:
            e6 = (-80, 80, 0, 20, 80, 0)
        if self.survival_enabled:
            thermal_b = (wsp[9] - 256 if self.temperature_observed
                         and wsp[9] >= 128 else wsp[9])
            e6 = (*e6[:4], wsp[8],
                  thermal_b if self.temperature_observed else e6[5])
        slot = self._slot_for(wsp, vertex, cell.extract, e6)
        s = self.cam.slot[slot]
        ham = hamming16(vertex, s.vertex) if s.occupied else HAM_MISS
        # N: is this the first turn ever *started* on this origin?
        #
        # Not `cell.novelty`: that is 1 forever on the NOVEL cell, which
        # conflated "somewhere new" with "the cell labelled NOVEL". After
        # the first hit, standing on cell 11 again is not a miss.
        #
        # Not `cam.get(wsp) < 0` either. The loop allocates the *landing*
        # slot every turn, so a cell is in CAM before the agent has ever
        # stood on it; by that reading only 2 of 352 turns are misses,
        # which measures the allocator, not the agent. hits is seeded to 1
        # by echoai.core.cam.Cam.put() (import-only, not ours to change) and
        # this loop adds 1 per turn started here — so <= 1 is exactly
        # "allocated, never stood on".
        n_fact = 1 if s.hits <= 1 else 0

        # SIGN-C. Captured before the action, spent after the world has
        # answered. None on every turn of every other bench, because the
        # flag is off and worlds that post no sign never qualify anyway.
        origin = (
            self._conflict_origin(cell, slot, n_fact)
            if (self.cortex_enabled and self.conflict_attend)
            else None
        )

        # A conflict query from last turn is still in flight: its proposal
        # is about to be consumed, and a second call now would be the same
        # turn asked twice. The suppression lasts exactly one turn and is
        # released whether or not the slow clock actually said anything.
        if self.conflict_suppressed:
            # SIGN-Cb. `last_attend` is what the diary prints, and
            # `thought.py` promises one line per turn *as the loop saw it*.
            # No ATTEND decision is made on this turn, so the field has to
            # say so: left alone it still held the previous turn's
            # `(True, REASON_CONFLICT)`, and one wake was written onto two
            # lines. `cortex_calls` never moved, which is precisely why the
            # lie was only visible in the log.
            #
            # Where the consumed hypothesis came from is not lost by this:
            # the same line carries `cortex_action`, which is null on the
            # turn that asked and the proposal on the turn that spends it.
            self.last_attend = (False, REASON_OFF)
            self.conflict_suppressed = False
        elif self.cortex_enabled:
            self._attend(cell, slot, s, e6, ham)

        if self.ask_enabled:
            self._ask(cell, slot)

        # Read before _propose consumes it: this is the proposal that got
        # a vote this turn, null when the slow clock said nothing.
        cortex_action = self.last_cortex_action
        self.last_evidence_explore = False
        q_explore = self.q.is_explore(slot, turn_i, greedy=greedy)
        a_prop = self._propose(slot, turn_i, greedy=greedy)
        self.last_explore = q_explore or self.last_evidence_explore
        inhibit = bool(s.flags & SLOT_FLAG_INHIBIT)
        decision, a, _flags = gate(
            wsp,
            cam_hit=s.occupied != 0,
            extract_ok=bool(cell.extract),
            E=e6,
            proposed=a_prop,
            inhibit=inhibit,
            threat=cell.threat,
            n_actions=self.n_actions,
        )
        self.last_proposed_action = a_prop
        self.last_gate_decision = decision
        if decision == GATE_BLOCK:
            a = a  # wait

        pred_next = self._predict(slot, a)
        if cell.index in JUMP_CELLS and int(a) % self.n_actions == ACTION_APPROACH:
            self.metrics.jump_hits += 1
        terminal = False
        if self.survival_enabled:
            if self.thermal_enabled:
                r, nxt_cell, h_next, temperature_next = \
                    self.env.step_homeostatic(a, self.H, self.temperature)
                if (type(temperature_next) is not int
                        or not 0 <= temperature_next <= 127):
                    raise ValueError("environment returned invalid temperature")
                self.temperature = temperature_next
            else:
                r, nxt_cell, h_next = self.env.step_vital(a, self.H)
            if type(h_next) is not int or not 0 <= h_next <= 127:
                raise ValueError("environment returned invalid vitality")
            self.H = h_next
            self.last_reward = int(r)
            self.life_turns += 1
            terminal = h_next == 0 or (
                self.thermal_enabled and self.temperature in (0, 127))
            self.episode_terminal = terminal
            self.deaths += int(terminal)
        else:
            r, nxt_cell = self.env.step(a)
        if cell.kind == KIND_NOVEL and int(a) % self.n_actions == ACTION_APPROACH:
            # The bait, scored: -16 per blind approach, +16 once asked.
            self.metrics.novel_approach_return += int(r)
        wsp_n = self.observation(nxt_cell)
        v_n, _, _ = encode_event(wsp_n)
        e_next = default_e()
        if self.survival_enabled:
            thermal_b_next = (wsp_n[9] - 256 if self.temperature_observed
                              and wsp_n[9] >= 128 else wsp_n[9])
            e_next = (*e_next[:4], wsp_n[8],
                      thermal_b_next if self.temperature_observed else e_next[5])
        slot_n = self._slot_for(wsp_n, v_n, nxt_cell.extract, e_next)

        if self.self_model is None or self.self_model.observe_step(slot, a, slot_n):
            self.t.observe(slot, a, slot_n)
            # The same transition, at the same moment, under the same
            # condition. One channel: a memory fed anything T is not fed
            # would be a second world model wearing an extension's coat.
            if self.pattern_memory is not None and self.prev_slot is not None:
                self.pattern_memory.observe(self.prev_slot, slot, a, slot_n)
        if self.pattern_memory is not None:
            self.prev_slot = slot
        # S: T committed to a successor and the world disagreed. A T_MISS
        # is ignorance — nothing was predicted, so nothing was wrong.
        s_fact = 1 if (pred_next is not None and pred_next != slot_n) else 0
        if pred_next is None:
            surprise = T_MISS_ERROR
        else:
            surprise = hamming16(self.cam.slot[pred_next].vertex, v_n)
            self.metrics.pred_known += 1
            self.metrics.pred_ham_sum += surprise
            if pred_next == slot_n:
                self.metrics.pred_hits += 1
            # Same turns, same denominator: what T has to beat.
            if slot == slot_n:
                self.metrics.persist_hits += 1
            if self._ring_slot(cell.index, a) == slot_n:
                self.metrics.ring_hits += 1

        # δ: the number update() already returned and the loop threw away.
        delta = (self.q.update(slot, a, r, slot_n, terminal=True)
                 if terminal else self.q.update(slot, a, r, slot_n))
        if terminal:
            self.clear_context()
        d_fact = 1 if delta != 0 else 0
        self.metrics.cam_misses += n_fact
        self.metrics.surprises += s_fact
        self.metrics.deltas += d_fact
        if s_fact and not n_fact:
            self.metrics.surprise_known += 1
        if n_fact and not s_fact:
            self.metrics.novel_no_surprise += 1
        if d_fact and not n_fact and not s_fact:
            self.metrics.delta_only += 1

        # The contradiction, now that there is one to have. T has already
        # been told by its own path above and Q has already been updated:
        # the slow clock is being asked about a turn the fast loop has
        # finished, and its answer changes neither table.
        if origin is not None and s_fact:
            self._conflict_wake(origin, ham, pred_next, slot_n)
        if s.hits < 65535:
            s.hits += 1
        if cell.extract and s.has_fact:
            self.metrics.verify += 1
        if s.has_fact and not cell.extract:
            self.metrics.false_facts += 1

        self.metrics.turns += 1
        self.metrics.ham_sum += ham
        self.metrics.destroyed = self.cam.destroyed
        if r > 0:
            self.metrics.action_pos += 1
        # Curiosity is unchanged as a rule (new place AND a bad map) but
        # now reads the clean N instead of the conflated one.
        if n_fact and surprise >= 4:
            self.metrics.store_priority += 1

        if self.thought_log:
            self._append(
                self.thought_log,
                thought.to_line(
                    thought.build(
                        turn=turn_i,
                        cell=cell.index,
                        kind=cell.kind,
                        action=a,
                        reward=r,
                        wsp=wsp,
                        attend_on=bool(self.last_attend[0]),
                        reason=self.last_attend[1],
                        q_row=self.q.row(slot),
                        t_pred=pred_next,
                        questions=self.metrics.questions,
                        cortex_calls=self.metrics.cortex_calls,
                        n=n_fact,
                        s=s_fact,
                        delta=d_fact,
                        cortex_action=cortex_action,
                        gate_decision=decision,
                        # GUI-3. A world that has a pose says so on its
                        # own cell; the ring does not, and getattr writes
                        # null. No import of any world here — the loop
                        # runs the same three actions whatever it is
                        # standing in, and that is the whole point.
                        x=getattr(cell, "x", None),
                        y=getattr(cell, "y", None),
                        z=getattr(cell, "z", None),
                        heading=getattr(cell, "heading", None),
                        frame=getattr(self.env, "frame", None),
                    )
                ),
            )
        return a

    def run(self, n: int = BENCH_TURNS) -> Metrics:
        if self.survival_enabled:
            # A bounded run never silently revives or erases a living body.
            for t in range(n):
                if self.episode_terminal:
                    break
                self.turn(self.metrics.turns)
            return self.metrics
        self.env.reset()
        self.q.reset_traces()  # a new episode starts with no credit owed
        self.clear_context()  # a reset is a discontinuity, like a teleport
        for t in range(n):
            self.turn(t)
        return self.metrics

    def greedy_on(self, cell_index: int) -> int:
        self.env.teleport(cell_index)
        cell = self.env.cell()
        wsp = self.observation(cell)
        vertex, _, _ = encode_event(wsp)
        slot = self._slot_for(wsp, vertex, cell.extract, default_e())
        return self.q.best(slot)

    def walk_greedy(self, steps: int = 32, start: int = 0) -> int:
        """Seeking probe: from `start`, walk greedily and count NOVEL cells.

        Tropiezo vs búsqueda. Training visits happen by accident; this asks
        whether the learned policy goes there on purpose. greedy=True means
        no ε and no full-tie approach — only what Q says.
        """
        self.env.teleport(start)
        hits = 0
        for t in range(int(steps)):
            if self.env.cell().kind == KIND_NOVEL:
                hits += 1
            self.turn(t, greedy=True)
        return hits

    def threat_slots(self) -> list:
        out = []
        for i, k in enumerate(self.env.kind):
            if k == KIND_THREAT:
                wsp = encode_cell(i, k)
                sl = self.cam.get(wsp)
                if sl >= 0:
                    out.append(sl)
        return out
