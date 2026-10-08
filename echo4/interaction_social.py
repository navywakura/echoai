"""Three private native learners, two atomic turns per scheduled encounter.

Private partner incentives create heterogeneous objectives. They are NOT counted
as interaction gain. The focal learner receives only the unmodified A net.
"""
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.loop import Agent
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.other_model import OtherModel
from echoai.echo4.other_world import ChoiceEnv, PRIVATE_STEPS
from echoai.echo4.interaction_world import InteractionWorld, pair
from echoai.echo4.interaction_session import InteractionSession, Port
from echoai.echo4.interaction_learning import BeliefAgent, RoutedObserver, ARMS, BELIEF_SOURCE


def settled():
    return Cell(3, KIND_OBJECT, extract_text="own action settled")


class PrivateTraining(ChoiceEnv):
    kind = (KIND_OBJECT,) * 4

    def step(self, action):
        reward, _ = super().step(action)
        return reward, settled()


class SocialPort(Port):
    kind = (KIND_OBJECT,) * 4

    def step(self, action):
        reward = self._session._commit(self._actor, action)
        if self._actor == 1:
            reward += self._session.private_credit(action)
        return reward, settled()


class SocialSession(InteractionSession):
    def __init__(self, cues, schedule, *, arm="identity", resources=(4096, 4096, 4096), swapped=False):
        if arm not in ARMS or type(swapped) is not bool:
            raise ValueError("arm/swapped")
        if type(resources) is not tuple or len(resources) != 3:
            raise ValueError("three resource ledgers required")
        for v in resources:
            integer(v, 0, 8192, "resource")
        self.world = InteractionWorld(cues, resources[:2])
        if type(schedule) is not tuple or len(schedule) != len(cues):
            raise ValueError("one scheduled encounter per cue")
        for handle in schedule:
            integer(handle, 1, 2, "scheduled peer")
        self._schedule, self.ledger = schedule, list(resources)
        self._preferences = ((0, 1, 2), (1, 2, 0))[:: -1 if swapped else 1]
        self.focal = BeliefAgent(SocialPort(self, 0), arm)
        partners = []
        for preferences in self._preferences:
            private = PrivateTraining(preferences, (0, 1, 2) * (PRIVATE_STEPS // 3))
            partner = Agent(env=private, ask=False, cortex=False, plan_depth=0,
                            remainder=True, explore_flat=True, evidence_budget=4)
            partner.thought_log = None
            for tick in range(PRIVATE_STEPS):
                partner.turn(tick)
            partner.env = SocialPort(self, 1)
            partners.append(partner)
        self.partners = tuple(partners)
        self.all_agents = (self.focal, *self.partners)
        mode = arm if arm in ("identity", "pooled", "no_history") else "identity"
        self.observer = RoutedObserver(OtherModel(self.focal.cam, self.focal.t, mode=mode), self.focal)
        self.peer_models = tuple(OtherModel(a.cam, a.t) for a in self.partners)
        self.active_handle = schedule[0]
        self.agents = (self.focal, self.partners[self.active_handle-1])
        self.models = (self.observer, self.peer_models[self.active_handle-1])
        self.failed = self.stopped = False
        self._active = False
        self._pending, self._running, self._native_returns = [None, None], [False, False], [None, None]
        self._event, self._greedy, self._turn = None, False, 0

    def private_credit(self, action):
        return 16 if action == self._preferences[self.active_handle-1][self._event["cue"]] else -16

    def _execute(self, actor):
        # Counterpart prior is greedy, but original Q still updates every time.
        prior = self._greedy
        self._greedy = True if actor == 1 else self._decision_greedy
        try:
            return super()._execute(actor)
        finally:
            self._greedy = prior

    def step(self, *, order=(0, 1), greedy=False, visible=(True, True), outcomes=(True, True),
             tracked=True, veto=(False, False)):
        if self.failed or self.stopped or self.world.done or self._active:
            raise RuntimeError("joint session stopped/exhausted/in flight")
        pair(order, "order", 0, 1)
        if order[0] == order[1] or type(greedy) is not bool or type(tracked) is not bool:
            raise ValueError("order/greedy/tracked")
        for mask in (visible, outcomes, veto):
            if type(mask) is not tuple or len(mask) != 2 or any(type(v) is not bool for v in mask):
                raise ValueError("visibility/outcome/veto mask")
        handle = self._schedule[self.world.tick]
        self.active_handle = handle
        self.agents = (self.focal, self.partners[handle-1])
        self.models = (self.observer, self.peer_models[handle-1])
        self.world.resources = (self.ledger[0], self.ledger[handle])
        self.observer.handle = handle if tracked else None
        self.observer.resource = self.ledger[0]
        self._decision_greedy = greedy
        self.focal.operator_inhibit = self.focal.operator_inhibit or veto[0]
        if veto[1]:
            super().inhibit(1)  # Native observed context from private training.
        try:
            frame = super().step(order=order, greedy=greedy, visible=visible, outcomes=outcomes)
        finally:
            # If a receipt fails after physical settlement, costs still exist.
            self.ledger[0], self.ledger[handle] = self.world.resources
        frame["contexts"][0] = [p.hex() if p else None for p in self.observer.contexts]
        frame["outcomes"][0] = [p.hex() if p else None for p in self.observer.outcomes]
        frame.update(handle=handle, belief=self.focal.belief_packet.hex(),
                     ledger=tuple(self.ledger), private_credit=self.private_credit(frame["actions"][1]))
        return frame

    def stop(self):
        super().stop()
        for model in self.peer_models:
            model.stop()

    def invariant(self):
        isolated = all(len({id(getattr(a, k)) for a in self.all_agents}) == 3
                       for k in ("cam", "t", "q", "env"))
        models = (self.observer.model, *self.peer_models)
        ticks = self.world.tick
        return bool(isolated and not self._active
                    and self.observer.count == ticks and sum(m.count for m in self.peer_models) == ticks
                    and all(m.cam is a.cam and m.world is a.t and m.pending is None
                            and a.metrics.turns == m.count + (0 if i == 0 else PRIVATE_STEPS)
                            and a.metrics.false_facts == 0 and a.cam.destroyed == 0
                            and a.metrics.cortex_calls == 0 and not a.cortex_enabled
                            and m.capacity_drops == 0
                            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                                    and (s.source != BELIEF_SOURCE or not s.has_fact and not s.extract)
                                    for s in a.cam.slot if s.occupied)
                            for i, (a, m) in enumerate(zip(self.all_agents, models)))
                    and all(v >= 0 for v in self.ledger))
