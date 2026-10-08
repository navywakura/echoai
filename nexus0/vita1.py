"""VITA-1: environment clock; H itself belongs to the existing Agent.

No living reward, automatic respawn or alternative transition memory.
The wrapped world's step still supplies the observed physical successor.
"""
from __future__ import annotations

from echoai.nexus0.constants import R_THREAT


class VitalEnv:
    def __init__(self, world, drain: int = 1) -> None:
        if type(drain) is not int or not 1 <= drain <= 127:
            raise ValueError("drain must be an integer in 1..127")
        self.world = world
        self.drain = drain

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "world"), name)

    def reset(self) -> None:
        self.world.reset()

    def step_vital(self, action: int, h: int):
        if type(h) is not int or not 1 <= h <= 127:
            raise ValueError("only a living integer H can take a step")
        reward, cell = self.world.step(action)
        nutrition = getattr(self.world, "last_nutrition", 0)
        if type(nutrition) is not int:
            raise ValueError("nutrition must be an integer")
        h_next = max(0, min(127, h - self.drain + nutrition))
        return (R_THREAT if h_next == 0 else reward), cell, h_next
