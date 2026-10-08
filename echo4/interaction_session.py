"""Two original Agent.turn calls, one atomic joint consequence, private memory.

Bounded nested env.step calls let the original loops receive their own rewards
after BOTH gated actions, without predicting/forging the peer's execution.
The OTHER observer is passive in this A increment.
"""
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.loop import Agent
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.other_model import OtherModel, context, outcome
from echoai.echo4.interaction_world import InteractionWorld, pair


class Port:
    kind = (KIND_OBJECT,) * 3

    def __init__(self, session, actor):
        self._session, self._actor = session, actor

    @property
    def i(self):
        return self._session.world.cue

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"joint task cue={self.i}")

    def step(self, action):
        reward = self._session._commit(self._actor, action)
        return reward, self.cell()


class InteractionSession:
    def __init__(self, cues, resources=(256, 256), *, observer_mode="identity"):
        self.world = InteractionWorld(cues, resources)
        self.agents = tuple(Agent(env=Port(self, i), ask=False, cortex=False,
                                  remainder=True, explore_flat=True, plan_depth=0) for i in range(2))
        for agent in self.agents:
            agent.thought_log = None
        self.models = tuple(OtherModel(a.cam, a.t, mode=observer_mode) for a in self.agents)
        self.failed = self.stopped = False
        self._active = False
        self._pending = [None, None]
        self._running = [False, False]
        self._event = None
        self._greedy = False
        self._turn = 0
        self._native_returns = [None, None]

    def _execute(self, actor):
        if self._running[actor]:
            raise RuntimeError("recursive actor execution")
        self._running[actor] = True
        action = self.agents[actor].turn(self._turn, greedy=self._greedy)
        self._native_returns[actor] = action
        return action

    def _commit(self, actor, action):
        pair((actor, actor), "actor", 0, 1)
        pair((action, action), "executed action", 0, 2)
        if (not self._active or self.failed or self.stopped or self.world.done
                or not self._running[actor] or self._pending[actor] is not None):
            raise RuntimeError("missing/duplicate/closed joint transaction")
        self._pending[actor] = action
        other = 1 - actor
        if self._pending[other] is None:
            self._execute(other)
        else:
            self._event = self.world.advance(tuple(self._pending))
        if self._event is None:
            raise RuntimeError("both real executions are required")
        return self._event["net"][actor]

    def step(self, *, order=(0, 1), greedy=False, visible=(True, True), outcomes=(True, True)):
        if self.failed or self.stopped or self.world.done or self._active:
            raise RuntimeError("joint session stopped/exhausted/in flight")
        pair(order, "order", 0, 1)
        if order[0] == order[1] or type(greedy) is not bool:
            raise ValueError("execution order/greedy")
        for mask in (visible, outcomes):
            if type(mask) is not tuple or len(mask) != 2 or any(type(v) is not bool for v in mask):
                raise ValueError("visibility/outcome mask")
        tick, cue = self.world.tick, self.world.cue
        views = tuple((context(0, cue), context(1, cue if visible[i] else None)) for i in range(2))
        self._active = True
        self._pending, self._running, self._native_returns = [None, None], [False, False], [None, None]
        self._event, self._greedy, self._turn = None, greedy, tick
        try:
            forecasts = tuple(m.begin(tick, v) for m, v in zip(self.models, views))
            self._execute(order[0])
            actions = tuple(self._pending)
            if actions != tuple(self._native_returns):
                raise RuntimeError("native execution receipt mismatch")
            receipts = tuple((outcome(0, cue, actions[i]),
                              outcome(1, cue if visible[i] else None, actions[1-i]) if outcomes[i] else None)
                             for i in range(2))
            predictions = tuple(m.finish(tick, actions[i], receipts[i]) for i, m in enumerate(self.models))
            return {**self._event, "contexts": [[p.hex() for p in v] for v in views],
                    "outcomes": [[p.hex() if p is not None else None for p in v] for v in receipts],
                    "forecasts": forecasts, "predictions": predictions,
                    "proposals": tuple(a.last_proposed_action for a in self.agents),
                    "gates": tuple(a.last_gate_decision for a in self.agents)}
        except Exception:
            self.failed = True
            self.stop()  # No retry after partial learning/execution; no implicit rollback.
            raise
        finally:
            self._active = False

    def inhibit(self, actor):
        pair((actor, actor), "actor", 0, 1)
        if self._active or self.failed or self.stopped or self.world.done:
            raise RuntimeError("cannot inhibit a closed or in-flight session")
        a = self.agents[actor]
        slot = a.cam.get(a.observation(a.env.cell()))
        if slot < 0:
            raise ValueError("native veto requires an observed context")
        a.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT

    def stop(self):
        self.stopped = True
        self.world.stop()
        for model in self.models:
            model.stop()

    def invariant(self):
        a, b = self.agents
        return bool(not self._active and all(getattr(a, k) is not getattr(b, k) for k in ("cam", "t", "q", "env"))
                    and all(m.cam is a.cam and m.world is a.t and m.count == self.world.tick
                            and m.pending is None and a.metrics.turns == self.world.tick
                            and a.metrics.cortex_calls == 0 and not a.cortex_enabled
                            and a.metrics.false_facts == 0 and a.cam.destroyed == 0
                            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                                    for s in a.cam.slot if s.occupied)
                            for a, m in zip(self.agents, self.models)))
