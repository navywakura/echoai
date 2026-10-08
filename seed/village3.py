"""Age-matched observed returns; the village2 world and diary stay unchanged.

Pending costs cannot be compared as though they were completed outcomes.
Credit stores only action/context/return, never a claim's evidence or answer.
"""
from types import FunctionType

from seed import village2 as base
from seed.game_selfimprove import sha

HORIZON = 64


class Echo(base.Echo):
    def __init__(self, seed, diary=True, verification=True):
        super().__init__(seed, diary, verification)
        self.pending_returns = {}
        self.matured = 0

    def begin(self, key, context, action, cost, age):
        self.credit[key] = (context, action)
        self.pending_returns[key] = [age, -cost]

    def charge(self, key, cost):
        if key in self.pending_returns:
            self.pending_returns[key][1] -= cost
        else:
            # Late observed consequences still belong to their original action.
            context, action = self.credit[key]
            self.update(context, action, -cost)

    def mature(self, age):
        for key, (started, reward) in list(self.pending_returns.items()):
            if age - started >= HORIZON:
                context, action = self.credit[key]
                self.update(context, action, reward, new=True)
                del self.pending_returns[key]
                self.matured += 1

    def state(self):
        return dict(super().state(), pending_returns={k: list(v) for k, v in self.pending_returns.items()},
                    matured=self.matured, return_horizon=HORIZON)


def run(seed, liars="BD", debts=True, diary=True, verification=True,
        episodes=base.EPISODES, actor=None, learn=True, observer=None):
    world = base.World(seed, liars, debts)
    actor = actor or Echo(seed, diary, verification)
    initial = sha(actor.state())
    rows = []
    for episode in range(episodes):
        if learn:
            actor.mature(episode)
        offer = world.offer(episode)
        context = actor.context(offer["agent"])
        action = actor.choose(context, learn)
        verify, write = base.ACTIONS[action]
        values = actor.scores(context)
        result = world.execute(episode, verify)
        cost = result["cost"] + int(write) * base.WRITE
        note = actor.remember(offer, result, verify) if write else None
        if learn:
            actor.begin(world.session + ":" + str(episode), context, action, cost, episode)
        claims = []
        for claim in world.claims(episode):
            evidence = actor.evidence(claim)
            settled = world.settle(claim, evidence)
            cost += settled["cost"]
            if learn:
                actor.charge(claim["session"] + ":" + str(claim["episode"]), settled["cost"])
            claims.append(dict(claim, **settled, evidence=evidence["hash"] if evidence else None))
        row = {"episode": episode, "offer": offer, "context": context, "action": action,
               "q_values": values, "verified": verify, "wrote": write, "result": result,
               "entry_hash": note["hash"] if note else None, "claims": claims, "cost": cost}
        rows.append(row)
        if observer:
            observer(row)
    return {"initial_sha256": initial, "rows": rows, "final": actor.state(),
            "description": actor.description()}, actor


# Preserve all five controls, memory interventions and stability probes verbatim.
experiment = FunctionType(base.experiment.__code__, dict(base.experiment.__globals__, run=run))
