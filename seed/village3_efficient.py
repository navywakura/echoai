"""Completed, factorized returns with exploration reduced by acquired evidence."""
from types import FunctionType
from seed import village2 as base, village3_factorized as previous

HORIZON = previous.HORIZON


class Echo(previous.Echo):
    def exploration_pm(self):
        return max(20, 100 // (1 + self.matured // 400))

    def choose(self, context, learn=True):
        allowed = self.allowed()
        if learn and self.rng.randrange(1000) < self.exploration_pm():
            return self.rng.choice(allowed)
        scores = self.scores(context)
        best = max(scores[i] for i in allowed)
        return min(i for i in allowed if scores[i] == best)

    def state(self):
        return dict(super().state(), exploration_pm=self.exploration_pm())


run = FunctionType(previous.run.__code__, dict(previous.run.__globals__, Echo=Echo),
                   "run", previous.run.__defaults__)
experiment = FunctionType(base.experiment.__code__, dict(base.experiment.__globals__, run=run))
