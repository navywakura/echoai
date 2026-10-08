"""Adapt the new physics to the existing Agent, without a new policy or bus."""
from __future__ import annotations

from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.loop import Agent
from echoai.echo4.world import Body, DockRules, DockWorld


class DockEnv(DockWorld):
    kind = (KIND_OBJECT,)
    i = 0

    def cell(self) -> Cell:
        return Cell(index=0, kind=KIND_OBJECT)

    def step_homeostatic(self, action: int, h: int, temperature: int):
        # Agent keeps the existing physiological registers. A mismatch must
        # not silently teleport the body or refill its resource reserve.
        if Body(h, temperature) != self.body:
            raise ValueError("agent physiology disagrees with the world")
        result = self.advance(action)
        return result.reward, self.cell(), self.body.h, self.body.temperature

    def step(self, _action: int):
        raise RuntimeError("WORLD-1 requires step_homeostatic")

    def teleport(self, _index: int) -> Cell:
        raise RuntimeError("teleport is not a WORLD-1 action")

    def reveal(self, _extract: str) -> bool:
        return False


def new_agent(rules: DockRules = DockRules(), initial: Body = Body()) -> Agent:
    env = DockEnv(rules, initial)
    agent = Agent(
        env=env, initial_h=initial.h, initial_temperature=initial.temperature,
        temperature_bands=8, ask=False, cortex=False, plan_depth=0,
        remainder=True, explore_flat=True,
    )
    # WORLD-1 is stdout-only; inherited NAVI_THOUGHT_LOG must not write an
    # unrelated user's diary. No global environment variables are changed.
    agent.thought_log = None
    return agent
