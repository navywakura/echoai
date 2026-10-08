"""Finite token grammar for model-authored bounded control strategies (S6-B2).

Values and conditions are selected by model probabilities. Syntax is fixed;
no candidate is selected, repaired, or ranked using game results here.
"""
import json
from echo_arc.strategy import LIMITS

PARAMETERS = ('HOLD', 'MIN_EVIDENCE', 'BABBLE', 'WALL_MIN')


def segments():
    out = [['{"defaults":{']]
    for i, name in enumerate(PARAMETERS):
        out.append([(',' if i else '') + json.dumps(name) + ':'])
        lo, hi = LIMITS[name]
        out.append([str(n) for n in range(lo, hi + 1)])
    out.append(['},"rules":[{"when":'])
    conditions = []
    for feature in ('click_only', 'body_known', 'reset_known'):
        conditions.extend({feature: ['eq', value]} for value in (0, 1))
    for feature, values in [('level', range(6)), ('world_events', (0, 1, 2, 3, 5, 10, 20, 40, 80)),
                            ('stagnation', (0, 5, 10, 20, 40, 80, 160, 320, 640, 1000, 2000))]:
        conditions.extend({feature: ['ge', value]} for value in values)
    out.append([json.dumps(c, separators=(',', ':')) for c in conditions])
    out.append([',"set":'])
    settings = []
    for name in PARAMETERS:
        lo, hi = LIMITS[name]
        settings.extend(json.dumps({name: n}, separators=(',', ':')) for n in range(lo, hi + 1))
    out.append(settings)
    out.append(['}]}'])
    return out


class Grammar:
    """An epsilon-NFA over tokenized segments; works for batched prefix callbacks."""
    def __init__(self, encode, eos):
        self.options = [tuple(tuple(encode(text)) for text in alternatives) for alternatives in segments()]
        if any(not option for alternatives in self.options for option in alternatives):
            raise ValueError('empty encoded grammar segment')
        self.eos = eos
        self.cache = {}

    def closure(self, states):
        out = set(states)
        queue = list(states)
        while queue:
            segment, option, offset = queue.pop()
            if segment == len(self.options):
                continue
            if offset == len(self.options[segment][option]):
                nxt = segment + 1
                additions = {(nxt, i, 0) for i in range(len(self.options[nxt]))} \
                    if nxt < len(self.options) else {(nxt, 0, 0)}
                for state in additions - out:
                    out.add(state)
                    queue.append(state)
        return frozenset(out)

    def states(self, prefix):
        key = tuple(prefix)
        if key in self.cache:
            return self.cache[key]
        if not key:
            found = self.closure({(0, i, 0) for i in range(len(self.options[0]))})
        elif key[-1] == self.eos:
            previous = self.states(key[:-1])
            if not any(s[0] == len(self.options) for s in previous):
                raise ValueError('premature EOS')
            found = frozenset({(len(self.options), 0, 0)})
        else:
            previous = self.states(key[:-1])
            found = self.closure({(s, o, k + 1) for s, o, k in previous
                                  if s < len(self.options) and k < len(self.options[s][o])
                                  and self.options[s][o][k] == key[-1]})
        if not found:
            raise ValueError('generated prefix escaped grammar')
        self.cache[key] = found
        return found

    def allowed(self, prefix):
        if self.eos in prefix:
            # A finished row in a batch may accumulate padding while its neighbour continues.
            self.states(prefix[:prefix.index(self.eos) + 1])
            return [self.eos]
        states = self.states(prefix)
        tokens = {self.eos for s, _, _ in states if s == len(self.options)}
        tokens.update(self.options[s][o][k] for s, o, k in states
                      if s < len(self.options) and k < len(self.options[s][o]))
        if not tokens:
            raise ValueError('empty token mask')
        return sorted(tokens)
