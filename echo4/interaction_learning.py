"""Derived, non-factual OTHER beliefs index the existing native Q, not a new Q."""
from echoai.core.dag import allocate
from echoai.core.wsp import pack
from echoai.nexus0.loop import Agent
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.other_model import context, outcome, decode

ARMS = ("identity", "pooled", "no_history", "solo", "always_join")
BELIEF_SOURCE = "interaction1-belief"


def belief(cue, resource, forecasts):
    integer(cue, 0, 2, "own cue")
    integer(resource, 0, 8192, "own resource")
    if type(forecasts) is not tuple or len(forecasts) != 3:
        raise ValueError("three forecast columns required")
    for value in forecasts:
        if value is not None:
            integer(value, 0, 2, "forecast")
    known = set(forecasts) - {None}
    category = 1 + next(iter(known)) if len(known) == 1 else 0
    return pack(src=2, rel=29, dst=3, domain=9, generator=8, style=8,
                slot=min(5, resource), seq=cue + 3 * category)


class BeliefAgent(Agent):
    def __init__(self, env, arm):
        if arm not in ARMS:
            raise ValueError("unsupported interaction arm")
        super().__init__(env=env, ask=False, cortex=False, plan_depth=0,
                         remainder=True, explore_flat=True, evidence_budget=4)
        self.thought_log = None
        self.arm, self.belief_packet = arm, None
        self.operator_inhibit = False

    def observation(self, cell):
        if cell.index == 3:
            return super().observation(cell)
        if self.belief_packet is None:
            raise RuntimeError("belief must precede the decision")
        return self.belief_packet

    def _slot_for(self, wsp, vertex, extract, e6, source="nexus0-env"):
        if wsp[10:14] != bytes((0, 9, 8, 8)):
            return super()._slot_for(wsp, vertex, extract, e6, source)
        slot = self.cam.get(wsp)
        if slot < 0:
            slot, _ = allocate(self.cam, wsp, vertex, 0, e6, has_fact=0,
                               extract="", source=BELIEF_SOURCE, key=wsp)
        if slot < 0:
            raise RuntimeError("no capacity for a non-factual decision context")
        if self.operator_inhibit:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return slot

    def _propose(self, slot, turn_i, greedy=False):
        if self.arm == "solo":
            return 1
        if self.arm == "always_join":
            return 0
        return super()._propose(slot, turn_i, greedy=greedy)


class RoutedObserver:
    """Route relative public peer 1 to a stable handle; no second memory."""
    def __init__(self, model, agent):
        self.model, self.agent = model, agent
        self.handle, self.resource = 1, 0
        self.contexts = self.outcomes = None

    def __getattr__(self, name):
        return getattr(self.model, name)

    def _route(self, packets, *, action=False):
        own, peer = packets
        if peer is None or self.handle is None:
            return own, None
        _, cue, executed = decode(peer, action=action)
        return own, (outcome(self.handle, cue, executed) if action else context(self.handle, cue))

    def begin(self, tick, packets):
        self.contexts = self._route(packets)
        forecasts = self.model.begin(tick, self.contexts)
        # A conflict in ANY observed conditional column makes the summary
        # uncertain too; do not hide it by using a different known column.
        remote = self.contexts[1]
        slot = -1 if remote is None else self.model.cam.get(self.model._key(remote))
        conflict = slot >= 0 and any(self.model.world.alt_n[slot])
        columns = (None,) * 3 if conflict else forecasts[1]
        self.agent.belief_packet = belief(decode(self.contexts[0])[1], self.resource, columns)
        return forecasts

    def finish(self, tick, action, packets):
        self.outcomes = self._route(packets, action=True)
        return self.model.finish(tick, action, self.outcomes)
