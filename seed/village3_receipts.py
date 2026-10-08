"""Learn delayed costs by retained-proof affordance, from executed outcomes."""
import copy
from types import FunctionType
from seed import village2 as base, village3_factorized as factor, village3_efficient as previous

HORIZON = previous.HORIZON


class Echo(previous.Echo):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proof_returns = {c: [[0, 0], [0, 0]] for c in self.q}
        self.receipt_credit = {}

    def begin(self, key, context, action, cost, age):
        super().begin(key, context, action, cost, age)
        entry = self.diary[-1] if self.diary else None
        retained = bool(entry and entry["session"] + ":" + str(entry["episode"]) == key and entry.get("proof"))
        self.receipt_credit[key] = int(retained)

    def charge(self, key, cost):
        pending = key in self.pending_returns
        super().charge(key, cost)
        if not pending:
            context, _ = self.credit[key]
            self.proof_returns[context][self.receipt_credit[key]][0] -= cost

    def mature(self, age):
        for key, (started, reward, downstream) in self.pending_returns.items():
            if age - started >= HORIZON:
                context, _ = self.credit[key]
                cell = self.proof_returns[context][self.receipt_credit[key]]
                cell[0] += downstream
                cell[1] += 1
        super().mature(age)

    def scores(self, context):
        nav = self.estimates(self.navigation[context])
        later = self.estimates(self.proof_returns[context])
        writing = self.value(self.writing)
        return [nav[int(verify)] + int(write) * writing + later[int(verify and write)]
                for verify, write in base.ACTIONS]

    def state(self):
        return dict(super().state(), proof_returns=copy.deepcopy(self.proof_returns),
                    receipt_credit=dict(self.receipt_credit))


run = FunctionType(factor.run.__code__, dict(factor.run.__globals__, Echo=Echo), "run", factor.run.__defaults__)
experiment = FunctionType(base.experiment.__code__, dict(base.experiment.__globals__, run=run))
