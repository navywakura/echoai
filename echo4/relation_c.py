"""RELATION-C: rupture, reunion, same identity with another body, and limits.

Sealed B sources are untouched. This module adds a body relief hook and a
fail-stop wrapper; nominal behaviour is identical to HelpSession.
"""
import random

from echoai.nexus0.loop import Agent
from echoai.echo4.world import integer
from echoai.echo4.other_model import OtherModel
from echoai.echo4.other_world import PRIVATE_STEPS
from echoai.echo4.interaction_social import PrivateTraining, SocialPort, settled
from echoai.echo4.relation_memory import RelationMemory
from echoai.echo4.interaction_learning import BELIEF_SOURCE
from echoai.echo4.relation_help import (HelpSession, PrivateHelp, B_CELLS, B_PRIVATE_STEPS, B_SOURCE,
                                        HELP, HELP_COST, RECIPROCITY, PRIVATE_STEPS_OFFSET)

HELP_MODES = ("reciprocal", "never")


class NeverHelp(PrivateHelp):
    """Private B training of a body that is rewarded for never helping."""
    def step(self, action):
        integer(action, 0, 2, "native action")
        if self.steps >= len(self._cells):
            raise RuntimeError("private help budget exhausted")
        reward = (-RECIPROCITY - HELP_COST) if action == HELP else RECIPROCITY
        self.steps += 1
        return reward, settled()


class RelationCSession(HelpSession):
    """HelpSession plus explicit body relief; any failure after start stops it."""

    def help_step(self, **kwargs):
        # Precondition rejections raise before execution and do not fail.
        if (self.failed or self.stopped or self.world.done or self._active or self._b_active
                or self.world.tick == self._last_b_tick):
            return super().help_step(**kwargs)
        try:
            return super().help_step(**kwargs)
        except Exception:
            self.failed = True
            self.stop()  # e.g. corrupt history: no request, no help, costs kept.
            raise

    def relieve(self, handle, preferences, help_mode, *, seed=0):
        """Same public identity, new native body with no memory of the learner."""
        integer(handle, 1, 2, "handle")
        integer(seed, 0, (1 << 31) - 1, "seed")
        if help_mode not in HELP_MODES:
            raise ValueError("help mode")
        if type(preferences) is not tuple or sorted(preferences) != [0, 1, 2]:
            raise ValueError("preference permutation")
        if self.failed or self.stopped or self._active or self._b_active:
            raise RuntimeError("cannot relieve a closed or in-flight session")
        body = Agent(env=PrivateTraining(preferences, (0, 1, 2) * (PRIVATE_STEPS // 3)),
                     ask=False, cortex=False, plan_depth=0, remainder=True,
                     explore_flat=True, evidence_budget=4)
        body.thought_log = None
        for tick in range(PRIVATE_STEPS):
            body.turn(tick)
        rng = random.Random(seed ^ 0xC0DE)
        cells = tuple(rng.choice(B_CELLS) for _ in range(B_PRIVATE_STEPS))
        body.env = PrivateHelp(cells) if help_mode == "reciprocal" else NeverHelp(cells)
        for step in range(B_PRIVATE_STEPS):
            body.turn(PRIVATE_STEPS_OFFSET + step)
        body.env = SocialPort(self, 1)
        i = handle - 1
        self.retired[handle] += self.peer_models[i].count
        self.partners = tuple(body if j == i else p for j, p in enumerate(self.partners))
        self.all_agents = (self.focal, *self.partners)
        self.peer_models = tuple(OtherModel(body.cam, body.t) if j == i else m
                                 for j, m in enumerate(self.peer_models))
        self.relations = tuple(RelationMemory(body.cam) if j == handle else m
                               for j, m in enumerate(self.relations))
        self._preferences = tuple(preferences if j == i else p for j, p in enumerate(self._preferences))
        self.b_turns[handle] = 0
        return body

    @property
    def retired(self):
        return self.__dict__.setdefault("_retired", [0, 0, 0])

    def invariant(self):
        """Explicit restatement that survives a body relief (checked equal to
        the inherited invariant in nominal sessions by the tests)."""
        agents = self.all_agents
        models = (self.observer.model, *self.peer_models)
        ticks = self.world.tick
        isolated = all(len({id(getattr(a, k)) for a in agents}) == 3 for k in ("cam", "t", "q", "env"))
        extra = (self.b_turns[0], *(PRIVATE_STEPS + B_PRIVATE_STEPS + self.b_turns[i] for i in (1, 2)))
        counts = (self.observer.count == ticks
                  and sum(m.count for m in self.peer_models) + sum(self.retired) == ticks)
        per_agent = all(
            m.cam is a.cam and m.world is a.t and m.pending is None and m.capacity_drops == 0
            and a.metrics.turns == m.count + n and a.metrics.false_facts == 0
            and a.cam.destroyed == 0 and a.metrics.cortex_calls == 0 and not a.cortex_enabled
            and r.cam is a.cam and r.count == m.count and r.invariant()
            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                    and (s.source not in (BELIEF_SOURCE, B_SOURCE) or not s.has_fact and not s.extract)
                    for s in a.cam.slot if s.occupied)
            for a, m, r, n in zip(agents, models, self.relations, extra))
        return bool(isolated and counts and per_agent and not self._active and not self._b_active
                    and all(v >= 0 for v in self.ledger))
