"""FOOD-1: OBJ-1's carried object can be consumed once per life.

An approach with the item in hand consumes it instead of moving. Empty
hands keep OBJ-1 movement; delivery is disabled because food is consumed,
not returned to a rewarding table. Nutrition is physical, not a kind:
the poison control has the same appearance and is learned separately.
"""
from __future__ import annotations

from echoai.nexus0 import body3d as cube
from echoai.nexus0.constants import ACTION_APPROACH, N_ACTIONS, R_SUCCESS, R_THREAT
from echoai.nexus0.env import KIND_EMPTY
from echoai.nexus0.obj1 import Obj1Env


class FoodEnv(Obj1Env):
    def __init__(self, nutrition: int = 24) -> None:
        if type(nutrition) is not int or not -127 <= nutrition <= 127:
            raise ValueError("nutrition must be an integer in -127..127")
        self.nutrition = nutrition
        super().__init__()

    def reset(self) -> None:
        self.last_nutrition = 0
        self.consumed = 0
        super().reset()

    def _paint(self) -> None:
        if self.obj is None:
            self.kind = [KIND_EMPTY] * cube.N_POSES
        else:
            super()._paint()

    def delivers(self, aa: int) -> bool:
        return False

    def step(self, a: int):
        self.last_nutrition = 0
        if int(a) % N_ACTIONS == ACTION_APPROACH and self.coupled:
            self.obj = None
            self.coupled = False
            self.consumed += 1
            self.last_nutrition = self.nutrition
            self.last_reward = (R_SUCCESS if self.nutrition > 0 else
                                R_THREAT if self.nutrition < 0 else 0)
            self.bumped = False
            self._paint()
            return self.last_reward, self.cell()
        return super().step(a)
