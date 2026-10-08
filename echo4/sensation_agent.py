"""Opt-in native Agent prediction hook; Q, gate and world remain original."""
from __future__ import annotations

from echoai.echo4.adapter import DockEnv
from echoai.echo4.sensation_predictor import SensationPredictor
from echoai.echo4.world import Body
from echoai.nexus0.loop import Agent


class SensationAgent(Agent):
    def __init__(self, *, initial: Body = Body(), depth: int = 2):
        super().__init__(env=DockEnv(initial=initial), initial_h=initial.h,
                         initial_temperature=initial.temperature, temperature_bands=8,
                         ask=False, cortex=False, plan_depth=0,
                         remainder=True, explore_flat=True)
        self.thought_log = None
        self.sensation = SensationPredictor(self.cam, self.t, depth=depth, update_base=False)
        self.sensation.start(self.observation(self.env.cell()))
        self.last_sensation = None
        self.last_sensory_prediction = None

    def _predict(self, slot: int, a: int):
        if self.cam.get(self.sensation.history.snapshot()[-16:]) != slot:
            raise RuntimeError("sensory history disagrees with Agent observation")
        prediction = self.sensation.anticipate(a)
        self.last_sensory_prediction = prediction
        return prediction.slot

    def turn(self, turn_i: int, greedy: bool = False) -> int:
        # Historical full-CAM fallback must not alias an absent state to row 0.
        if self.cam.used > len(self.cam.slot) - 2:
            raise RuntimeError("CAM capacity guard")
        action = super().turn(turn_i, greedy=greedy)
        self.last_sensation = self.sensation.observe(self.observation(self.env.cell()))
        return action

    def respawn(self) -> None:
        super().respawn()
        self.sensation.start(self.observation(self.env.cell()))
        self.last_sensation = self.last_sensory_prediction = None
