"""Token-constrained single guarded repair, reusing the existing NFA."""
import json
from echo_arc.strategy_grammar import Grammar as NFA
from echo_arc.local_patch import LIMITS, FEATURES


def conditions():
    values = []
    for k, bounds in FEATURES.items():
        if bounds == (0, 1):
            values.extend({k: ["eq", n]} for n in (0, 1))
        else:
            thresholds = (1, 2, 3, 4, 8, 16, 32, 64, 128)
            values.extend({k: ["ge", n]} for n in thresholds if n <= bounds[1])
    for key in ("stagnation", "entry_count", "marker_count"):
        for n in (2, 4, 8, 16):
            if n <= FEATURES[key][1]:
                values.append({"motor_ready": ["eq", 1], key: ["ge", n]})
    return values


class Grammar(NFA):
    def __init__(self, encode, eos):
        segments = [['{"patches":[{"when":'],
                    [json.dumps(c, separators=(',', ':')) for c in conditions()],
                    [',"set":'],
                    [json.dumps({k: n}, separators=(',', ':')) for k, (lo, hi) in LIMITS.items()
                     for n in range(lo, hi + 1)], ['}]}']]
        self.options = [tuple(tuple(encode(t)) for t in opts) for opts in segments]
        if any(not t for opts in self.options for t in opts):
            raise ValueError("empty encoded grammar segment")
        self.eos, self.cache = eos, {}
