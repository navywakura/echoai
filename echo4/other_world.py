"""Private independent choice worlds. Native Agent/Q/gate choose every action.

Only this executor knows preferences and future cues. No shared memory,
joint reward, communication policy or physiological-maintenance claim.
"""
import random

from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.loop import Agent
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.other_model import OtherModel, context, outcome, LIMIT

PRIVATE_STEPS = 240
ENCOUNTERS = 192


class ChoiceEnv:
    kind = (KIND_OBJECT,) * 3

    def __init__(self, preferences, cues):
        if type(preferences) is not tuple or sorted(preferences) != [0, 1, 2]:
            raise ValueError("requires a preference permutation")
        for v in preferences:
            integer(v, 0, 2, "preference")
        if type(cues) is not tuple or not 1 <= len(cues) <= 1024:
            raise ValueError("bounded private cue sequence required")
        for v in cues:
            integer(v, 0, 2, "cue")
        self._preferences, self._cues = preferences, cues
        self.steps = self.successes = self.reward_sum = 0
        self.last_action = self.last_reward = None
        self._stopped = False

    @property
    def i(self):
        return self._cues[min(self.steps, len(self._cues) - 1)]

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"local cue={self.i}")

    def step(self, action):
        integer(action, 0, 2, "native action")
        if self._stopped or self.steps >= len(self._cues):
            raise RuntimeError("choice world stopped/budget exhausted")
        reward = 16 if action == self._preferences[self.i] else -16
        self.successes += int(reward == 16)
        self.reward_sum += reward
        self.last_action, self.last_reward = action, reward
        self.steps += 1
        return reward, self.cell()

    def stop(self):
        self._stopped = True


def new_agent(preferences, cues):
    agent = Agent(env=ChoiceEnv(preferences, cues), ask=False, cortex=False,
                  remainder=True, explore_flat=True, plan_depth=0)
    agent.thought_log = None
    return agent


class Encounter:
    def __init__(self, preferences, *, seed, mode="identity"):
        integer(seed, 0, (1 << 31)-1, "seed")
        if type(preferences) is not tuple or len(preferences) != 2:
            raise ValueError("two private tasks required")
        rng = random.Random(seed)
        cues = tuple(tuple(rng.randrange(3) for _ in range(PRIVATE_STEPS + LIMIT + 1)) for _ in range(2))
        self.agents = tuple(new_agent(p, stream) for p, stream in zip(preferences, cues))
        # Separate prior lives before first contact; no public-model reset.
        for tick in range(PRIVATE_STEPS):
            for agent in self.agents:
                agent.turn(tick)
        self.models = tuple(OtherModel(a.cam, a.t, mode=mode) for a in self.agents)
        self.tick = 0
        self.stopped = self.failed = False
        self.mode = mode

    def step(self, *, order=(0, 1), visible=(True, True), outcomes=(True, True),
             handles=(1, 1), veto=(False, False)):
        if self.stopped or self.failed or self.tick >= LIMIT:
            raise RuntimeError("encounter stopped/budget exhausted")
        if order not in ((0, 1), (1, 0)) or type(order) is not tuple or any(type(v) is not int for v in order):
            raise ValueError("execution order")
        for mask in (visible, outcomes, veto):
            if type(mask) is not tuple or len(mask) != 2 or any(type(v) is not bool for v in mask):
                raise ValueError("visibility/veto mask")
        if type(handles) is not tuple or len(handles) != 2:
            raise ValueError("tracking handles")
        for handle in handles:
            if handle is not None:
                integer(handle, 1, 2, "peer handle")
        cues = tuple(a.env.cell().index for a in self.agents)
        views = tuple((context(0, cues[i]),
                       None if handles[i] is None else context(handles[i], cues[1-i] if visible[i] else None))
                      for i in range(2))
        try:
            forecasts = tuple(model.begin(self.tick, view) for model, view in zip(self.models, views))
            actions = [None, None]
            for i in order:
                agent = self.agents[i]
                if veto[i]:
                    slot = agent.cam.get(agent.observation(agent.env.cell()))
                    if slot < 0:
                        raise ValueError("private veto origin unseen")
                    agent.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
                actions[i] = agent.turn(PRIVATE_STEPS + self.tick, greedy=True)
            receipts = tuple((outcome(0, cues[i], actions[i]),
                              outcome(handles[i], cues[1-i] if visible[i] else None, actions[1-i])
                              if handles[i] is not None and outcomes[i] else None) for i in range(2))
            predictions = tuple(model.finish(self.tick, actions[i], receipts[i]) for i, model in enumerate(self.models))
            event = {"tick": self.tick, "contexts": [[p.hex() if p else None for p in v] for v in views],
                     "outcomes": [[p.hex() if p else None for p in v] for v in receipts],
                     "forecasts": forecasts, "predictions": predictions, "actions": tuple(actions),
                     "proposals": tuple(a.last_proposed_action for a in self.agents),
                     "gates": tuple(a.last_gate_decision for a in self.agents),
                     "rewards": tuple(a.env.last_reward for a in self.agents)}
            self.tick += 1
            return event
        except Exception:
            self.failed = True  # No continuation after a partially executed joint observation.
            raise

    def stop(self):
        self.stopped = True
        for a, m in zip(self.agents, self.models):
            a.env.stop()
            m.stop()

    def invariant(self):
        a, b = self.agents
        isolated = all(getattr(a, name) is not getattr(b, name) for name in ("cam", "t", "q", "env"))
        return bool(isolated and all(
            model.cam is agent.cam and model.world is agent.t
            and agent.cam.destroyed == 0 and agent.metrics.false_facts == 0
            and agent.metrics.cortex_calls == 0 and not agent.cortex_enabled
            and agent.env.steps == PRIVATE_STEPS + self.tick
            and model.count == self.tick and model.pending is None
            and all(len(slot.wsp) == 16 and (not slot.has_fact or bool(slot.extract))
                    for slot in agent.cam.slot if slot.occupied)
            and all(not slot.has_fact for slot in agent.cam.slot
                    if slot.occupied and slot.source == "other1-derived-index")
            for agent, model in zip(self.agents, self.models)))
