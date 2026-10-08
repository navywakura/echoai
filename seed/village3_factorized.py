"""Separate observed immediate costs from age-matched downstream costs."""
from types import FunctionType

from seed import village2 as base, village3 as mature

HORIZON = mature.HORIZON


class Echo(mature.Echo):
    def __init__(self, seed, diary=True, verification=True):
        super().__init__(seed, diary, verification)
        self.navigation = {c: [[0, 0], [0, 0]] for c in self.q}
        self.writing = [0, 0]
        self.downstream = {c: [[0, 0] for _ in base.ACTIONS] for c in self.q}

    def begin(self, key, context, action, cost, age):
        super().begin(key, context, action, cost, age)
        verify, write = base.ACTIONS[action]
        # run() supplies the separately observed navigation charge, not a
        # counterfactual outcome or a private future-claim label.
        cell = self.navigation[context][int(verify)]
        cell[0] -= self.observed_navigation_cost
        cell[1] += 1
        if write:
            self.writing[0] -= cost - self.observed_navigation_cost
            self.writing[1] += 1
        self.pending_returns[key].append(0)

    def charge(self, key, cost):
        if key in self.pending_returns:
            self.pending_returns[key][1] -= cost
            self.pending_returns[key][2] -= cost
        else:
            context, action = self.credit[key]
            self.update(context, action, -cost)
            self.downstream[context][action][0] -= cost

    def mature(self, age):
        for key, (started, reward, downstream) in list(self.pending_returns.items()):
            if age - started >= mature.HORIZON:
                context, action = self.credit[key]
                self.update(context, action, reward, new=True)
                cell = self.downstream[context][action]
                cell[0] += downstream
                cell[1] += 1
                del self.pending_returns[key]
                self.matured += 1

    @staticmethod
    def estimates(cells):
        count = sum(c[1] for c in cells)
        fallback = sum(c[0] for c in cells) * 1000 // count if count else 0
        return [base.Echo.value(c) if c[1] else fallback for c in cells]

    def scores(self, context):
        navigation = self.estimates(self.navigation[context])
        downstream = self.estimates(self.downstream[context])
        write_cost = self.value(self.writing)
        return [navigation[int(verify)] + int(write) * write_cost + downstream[i]
                for i, (verify, write) in enumerate(base.ACTIONS)]

    def state(self):
        import copy
        return dict(super().state(), navigation=copy.deepcopy(self.navigation), writing=list(self.writing),
                    downstream=copy.deepcopy(self.downstream))


def run(seed, liars="BD", debts=True, diary=True, verification=True,
        episodes=base.EPISODES, actor=None, learn=True, observer=None):
    actor = actor or Echo(seed, diary, verification)

    class ObservedWorld(base.World):
        def execute(self, episode, verified):
            result = super().execute(episode, verified)
            actor.observed_navigation_cost = result["cost"]
            return result

    from types import SimpleNamespace
    visible_base = SimpleNamespace(**vars(base))
    visible_base.World = ObservedWorld
    execute = FunctionType(mature.run.__code__, dict(mature.run.__globals__, base=visible_base),
                           "run", mature.run.__defaults__)
    return execute(seed, liars, debts, diary, verification, episodes, actor, learn, observer)


experiment = FunctionType(base.experiment.__code__, dict(base.experiment.__globals__, run=run))
