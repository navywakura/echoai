"""Factorized returns mature after the world's declared maximum delay + 1."""
from types import FunctionType
from seed import village2 as base, village3_factorized as previous

HORIZON = 49


class Echo(previous.Echo):
    def mature(self, age):
        # Claims of age 48 settle after choose(); they enter Q on the next turn.
        super().mature(age + previous.HORIZON - HORIZON)

    def state(self):
        return dict(super().state(), return_horizon=HORIZON)


run = FunctionType(previous.run.__code__, dict(previous.run.__globals__, Echo=Echo),
                   "run", previous.run.__defaults__)
experiment = FunctionType(base.experiment.__code__, dict(base.experiment.__globals__, run=run))
