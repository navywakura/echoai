"""Costed joint-action physics; no policy, peer-memory reads or implicit gifts."""
from echoai.echo4.world import integer
from echoai.echo4.other_model import LIMIT

JOIN_COST = (3, 5, 3)
JOIN_OUTPUT = (10, 6, 0)
SOLO_COST = 1
SOLO_OUTPUT = 5


def pair(values, name, lower, upper):
    if type(values) is not tuple or len(values) != 2:
        raise ValueError(name + " requires a pair")
    for value in values:
        integer(value, lower, upper, name)
    return values


class InteractionWorld:
    def __init__(self, cues, resources=(256, 256)):
        if type(cues) is not tuple or not 1 <= len(cues) <= LIMIT:
            raise ValueError("bounded cue sequence required")
        for cue in cues:
            integer(cue, 0, 2, "cue")
        self.resources = pair(resources, "resource", 0, 8192)
        self._cues = cues
        self.tick = 0
        self.stopped = False
        self.spent = self.output = self.net = (0, 0)
        self.last = None

    @property
    def cue(self):
        return self._cues[min(self.tick, len(self._cues) - 1)]

    @property
    def done(self):
        return self.stopped or self.tick >= len(self._cues)

    def advance(self, actions):
        if self.done:
            raise RuntimeError("joint world stopped or exhausted")
        pair(actions, "executed action", 0, 2)
        cue, before = self.cue, self.resources
        costs = tuple(JOIN_COST[cue] if a == 0 else SOLO_COST if a == 1 else 0 for a in actions)
        capable = tuple(before[i] >= costs[i] for i in range(2))
        paid = tuple(costs[i] if capable[i] else 0 for i in range(2))
        joint = actions == (0, 0) and all(capable)
        output = tuple(JOIN_OUTPUT[cue] if joint else
                       SOLO_OUTPUT if actions[i] == 1 and capable[i] else 0 for i in range(2))
        net = tuple(output[i] - paid[i] for i in range(2))
        after = tuple(before[i] - paid[i] for i in range(2))
        event = {"tick": self.tick, "cue": cue, "actions": actions,
                 "before": before, "after": after, "paid": paid, "output": output,
                 "net": net, "joint_executed": joint, "incapable": tuple(not v for v in capable)}
        self.resources = after
        self.spent = tuple(self.spent[i] + paid[i] for i in range(2))
        self.output = tuple(self.output[i] + output[i] for i in range(2))
        self.net = tuple(self.net[i] + net[i] for i in range(2))
        self.tick += 1
        self.last = event
        return event

    def stop(self):
        self.stopped = True
