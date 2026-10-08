"""RELATION-B help task: A history, recorded in each agent's own CAM, indexes B.

The help physics and the counterpart reciprocity profile are designed and
published. The reciprocity incentive is private and never counted as gain.
B outcomes are NOT written to RelationMemory; A remains its only physics.
"""
import random

from echoai.core.dag import allocate
from echoai.core.wsp import pack
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.other_model import context, decode, LIMIT
from echoai.echo4.interaction_learning import BeliefAgent
from echoai.echo4.interaction_social import SocialSession, settled
from echoai.echo4.relation_session import RelationSession

B_ARMS = ("history", "other_only", "shuffled", "pooled", "no_history", "solo", "always_ask")
ASK, SOLO, WAIT = 0, 1, 2
HELP = 0  # Partner actions 1 and 2 both mean "no help".
ASK_HELPED = (1, 8)
ASK_REFUSED = (3, 0)
SOLO_RESULT = (1, 2)
HELP_COST = 3
RECIPROCITY = 16
WINDOW = 3
B_CELLS = (4, 5, 6)  # Partner private B contexts: no history / 0 / >=1 recent.
B_PRIVATE_STEPS = 240
B_STYLE = 9
B_SOURCE = "relation1-b-derived-row"
PRIVATE_STEPS_OFFSET = 1024


def success(entry):
    """Confirmed joint success in one observed A episode (own view only)."""
    r = entry["observation"]
    own = decode(bytes.fromhex(r["outcomes"][0]), action=True)[2]
    other = None if r["outcomes"][1] is None else decode(bytes.fromhex(r["outcomes"][1]), action=True)[2]
    return int(own == other == 0 and r["output"] > 0)


def bucket(entries):
    """0 = fewer than WINDOW prior episodes, 1 = none recent, 2 = >=1 recent."""
    if type(entries) is not list:
        raise ValueError("episode list required")
    if len(entries) < WINDOW:
        return 0
    return 2 if any(success(e) for e in entries[-WINDOW:]) else 1


def shuffled(entries, seed, tick):
    integer(seed, 0, (1 << 31) - 1, "seed")
    integer(tick, 0, LIMIT - 1, "tick")
    rows = list(entries)
    random.Random(seed * LIMIT + tick).shuffle(rows)
    return rows


def row(arm, resource, *, level=0, handle=0, cue=0, category=0):
    """Derived, non-factual WSP16 decision row for B. Never a fact."""
    if arm not in B_ARMS:
        raise ValueError("unsupported B arm")
    integer(resource, 0, 8192, "own resource")
    integer(level, 0, 2, "history bucket")
    integer(handle, 0, 2, "handle")
    integer(cue, 0, 2, "public cue")
    integer(category, 0, 3, "forecast category")
    if arm in ("history", "shuffled", "pooled"):
        seq = level
    elif arm == "other_only":
        seq = 16 + 12 * max(0, handle - 1) + 4 * cue + category
    else:  # no_history and fixed-proposal controls share context-only rows.
        seq = 64 + cue
    return pack(src=2, rel=29, dst=3, domain=9, generator=8, style=B_STYLE,
                slot=min(5, resource), seq=seq)


def settle(action, help_action, resources):
    """Pure B physics. Returns event with costs/outputs for (learner, partner)."""
    integer(action, 0, 2, "learner B action")
    if help_action is not None:
        integer(help_action, 0, 2, "partner B action")
    if type(resources) is not tuple or len(resources) != 2:
        raise ValueError("two ledgers required")
    for v in resources:
        integer(v, 0, 8192, "resource")
    asked = helped = False
    paid, output = [0, 0], [0, 0]
    capable = [True, True]
    if action == ASK:
        capable[0] = resources[0] >= ASK_REFUSED[0]
        asked = capable[0]
        if asked:
            if help_action is None:
                raise ValueError("asked partner must execute")
            capable[1] = resources[1] >= HELP_COST
            helped = help_action == HELP and capable[1]
            paid[0], output[0] = ASK_HELPED if helped else ASK_REFUSED
            paid[1] = HELP_COST if helped else 0
    elif action == SOLO:
        capable[0] = resources[0] >= SOLO_RESULT[0]
        if capable[0]:
            paid[0], output[0] = SOLO_RESULT
    if help_action is not None and not asked:
        raise ValueError("partner cannot act unless asked")
    return {"action": action, "help_action": help_action, "asked": asked, "helped": helped,
            "paid": tuple(paid), "output": tuple(output),
            "net": tuple(output[i] - paid[i] for i in range(2)),
            "incapable": tuple(not c for c in capable)}


class HelpAgent(BeliefAgent):
    """Same native Agent; B rows are derived keys, B arm only fixes controls."""
    def __init__(self, env, b_arm):
        if b_arm not in B_ARMS:
            raise ValueError("unsupported B arm")
        super().__init__(env, "identity")  # A phase identical for every B arm.
        self.b_arm, self.in_b = b_arm, False

    def _slot_for(self, wsp, vertex, extract, e6, source="nexus0-env"):
        if wsp[10:14] != bytes((0, 9, 8, B_STYLE)):
            return super()._slot_for(wsp, vertex, extract, e6, source)
        slot = self.cam.get(wsp)
        if slot < 0:
            slot, _ = allocate(self.cam, wsp, vertex, 0, e6, has_fact=0,
                               extract="", source=B_SOURCE, key=wsp)
        if slot < 0:
            raise RuntimeError("no capacity for a non-factual B row")
        if self.operator_inhibit:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return slot

    def _propose(self, slot, turn_i, greedy=False):
        if self.in_b and self.b_arm == "solo":
            return SOLO
        if self.in_b and self.b_arm == "always_ask":
            return ASK
        return super()._propose(slot, turn_i, greedy=greedy)


class HelpPort:
    kind = (KIND_OBJECT,) * 7

    def __init__(self, session, actor, index=0):
        self._session, self._actor, self.i = session, actor, index

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"help task context={self.i}")

    def step(self, action):
        return self._session._help_commit(self._actor, action), settled()


class PrivateHelp:
    """Partner private B training: reciprocity incentive + own help cost."""
    kind = (KIND_OBJECT,) * 7

    def __init__(self, cells):
        for v in cells:
            if v not in B_CELLS:
                raise ValueError("private B context")
        self._cells, self.steps = cells, 0

    @property
    def i(self):
        return self._cells[min(self.steps, len(self._cells) - 1)]

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"private help context={self.i}")

    def step(self, action):
        integer(action, 0, 2, "native action")
        if self.steps >= len(self._cells):
            raise RuntimeError("private help budget exhausted")
        reward = incentive(self.i - B_CELLS[0], action) - (HELP_COST if action == HELP else 0)
        self.steps += 1
        return reward, settled()


def incentive(level, help_action):
    """Designed private reciprocity; published separately, never a gain."""
    integer(level, 0, 2, "partner history bucket")
    integer(help_action, 0, 2, "partner action")
    return RECIPROCITY if (help_action == HELP) == (level == 2) else -RECIPROCITY


class HelpSession(RelationSession):
    def __init__(self, cues, schedule, *, b_arm="history", seed=0, **kwargs):
        if b_arm not in B_ARMS or kwargs.get("arm", "identity") != "identity":
            raise ValueError("B arm; A arm is always identity")
        integer(seed, 0, (1 << 31) - 1, "seed")
        self._b_arm, self._seed = b_arm, seed
        self._help_agent = True
        super().__init__(cues, schedule, **kwargs)
        rng = random.Random(seed ^ 0x5EB)
        for partner in self.partners:
            port = partner.env
            partner.env = PrivateHelp(tuple(rng.choice(B_CELLS) for _ in range(B_PRIVATE_STEPS)))
            for step in range(B_PRIVATE_STEPS):
                partner.turn(PRIVATE_STEPS_OFFSET + step)
            partner.env = port
        self.b_frames = 0
        self.b_turns = [0, 0, 0]
        self._b_active = False
        self._b_state = None
        self._last_b_tick = -1

    # The focal learner is built by SocialSession; swap in HelpAgent without
    # altering its constructor arguments or the A arm.
    @property
    def focal(self):
        return self.__dict__["focal"]

    @focal.setter
    def focal(self, agent):
        if self.__dict__.get("_help_agent") and not isinstance(agent, HelpAgent):
            agent = HelpAgent(agent.env, self._b_arm)
        self.__dict__["focal"] = agent

    def levels(self, handle, *, tracked=True):
        """Focal B context from its own RelationMemory; prior episodes only."""
        memory = self.relations[0]
        if not tracked:
            return 0
        if self._b_arm == "history":
            return bucket(memory.history(handle))
        if self._b_arm == "shuffled":
            return bucket(shuffled(memory.history(handle), self._seed, self.world.tick))
        if self._b_arm == "pooled":
            return bucket(memory.history())
        return 0

    def partner_level(self, handle):
        # Counterpart's OWN memory; the learner appears there as subject 1.
        return bucket(self.relations[handle].history(1))

    def _other_category(self, handle, cue):
        model = self.observer.model
        forecasts = tuple(model._predict(context(handle, cue), a) for a in range(3))
        known = set(forecasts) - {None}
        return 1 + next(iter(known)) if len(known) == 1 else 0

    def help_step(self, *, greedy=False, tracked=True, veto=(False, False)):
        if self.failed or self.stopped or self.world.done or self._active or self._b_active:
            raise RuntimeError("help step on stopped/exhausted/in-flight session")
        if type(greedy) is not bool or type(tracked) is not bool:
            raise ValueError("greedy/tracked")
        if type(veto) is not tuple or len(veto) != 2 or any(type(v) is not bool for v in veto):
            raise ValueError("veto mask")
        tick, cue = self.world.tick, self.world.cue
        if tick == self._last_b_tick:
            raise RuntimeError("one B step per encounter")
        handle = self._schedule[tick]
        partner = self.partners[handle-1]
        level = self.levels(handle, tracked=tracked)
        category = self._other_category(handle, cue) if self._b_arm == "other_only" and tracked else 0
        packet = row(self._b_arm, self.ledger[0], level=level,
                     handle=handle if tracked else 0, cue=cue, category=category)
        partner_level = self.partner_level(handle)
        self._b_state = {"tick": tick, "handle": handle, "partner_level": partner_level,
                         "veto": veto, "greedy": greedy, "event": None, "pending": [None, None]}
        focal_port, partner_port = self.focal.env, partner.env
        prior_belief = self.focal.belief_packet
        self._b_active = True
        try:
            self.focal.env = HelpPort(self, 0)
            partner.env = HelpPort(self, 1, B_CELLS[partner_level])
            self.focal.belief_packet = packet
            self.focal.in_b = True
            if veto[0]:
                self.focal.operator_inhibit = True
            action = self.focal.turn(LIMIT + tick, greedy=greedy)
            event = self._b_state["event"]
            if event is None or event["action"] != action:
                raise RuntimeError("B execution receipt mismatch")
            self.b_turns[0] += 1
            self.b_frames += 1
            self._last_b_tick = tick
            return {"tick": tick, "handle": handle, "cue": cue, "row": packet.hex(),
                    "level": level, "partner_level": partner_level,
                    "proposal": self.focal.last_proposed_action, "gate": self.focal.last_gate_decision,
                    "private_credit": (incentive(partner_level, event["help_action"])
                                       if event["help_action"] is not None else 0),
                    **event, "ledger": tuple(self.ledger)}
        except Exception:
            self.failed = True
            self.stop()  # Keep executed costs; no retry or rollback.
            raise
        finally:
            self.focal.in_b = False
            self.focal.env, partner.env = focal_port, partner_port
            self.focal.belief_packet = prior_belief
            self._b_active = False

    def _help_commit(self, actor, action):
        state = self._b_state
        if not self._b_active or state is None or state["pending"][actor] is not None:
            raise RuntimeError("missing/duplicate B transaction")
        integer(action, 0, 2, "B action")
        state["pending"][actor] = action
        handle = state["handle"]
        partner = self.partners[handle-1]
        if actor == 1:
            # Partner reward: own physical cost plus designed private incentive.
            cost = HELP_COST if action == HELP and self.ledger[handle] >= HELP_COST else 0
            return incentive(state["partner_level"], action) - cost
        help_action = None
        if action == ASK and self.ledger[0] >= ASK_REFUSED[0]:
            if state["veto"][1]:
                # Real gate: INHIBIT on the partner's own observed B row.
                slot = partner.cam.get(partner.observation(partner.env.cell()))
                if slot < 0:
                    raise ValueError("partner veto requires an observed B context")
                partner.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
            help_action = partner.turn(LIMIT + state["tick"], greedy=True)
            if state["pending"][1] != help_action:
                raise RuntimeError("partner B receipt mismatch")
            self.b_turns[handle] += 1
        event = settle(action, help_action, (self.ledger[0], self.ledger[handle]))
        self.ledger[0] -= event["paid"][0]
        self.ledger[handle] -= event["paid"][1]
        state["event"] = event
        return event["net"][0]

    def invariant(self):
        # Parent accounting counts A turns only; remove B turns before the
        # inherited check, then restore. B rows must stay non-factual.
        agents = self.all_agents
        extra = (self.b_turns[0], *(B_PRIVATE_STEPS + self.b_turns[i] for i in (1, 2)))
        for a, n in zip(agents, extra):
            a.metrics.turns -= n
        try:
            inherited = super().invariant()
        finally:
            for a, n in zip(agents, extra):
                a.metrics.turns += n
        rows = all(not s.has_fact and not s.extract
                   for s in self.focal.cam.slot if s.occupied and s.source == B_SOURCE)
        return bool(inherited and rows and not self._b_active)

