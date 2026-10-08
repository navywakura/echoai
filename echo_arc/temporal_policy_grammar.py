"""B3 token grammar, using the previous grammar automaton unchanged."""
import json
from echo_arc.strategy_grammar import Grammar as OriginalGrammar
from echo_arc.temporal_policy import LIMITS, FEATURES


def segments():
    result = [['{"defaults":{']]
    for i, (name, (lo, hi)) in enumerate(LIMITS.items()):
        result.append([(',' if i else '') + json.dumps(name) + ':'])
        result.append([str(n) for n in range(lo, hi + 1)])
    result.append(['},"rules":[{"when":'])
    conditions = []
    for feature in FEATURES:
        if FEATURES[feature] == (0, 1):
            conditions.extend({feature: ['eq', n]} for n in (0, 1))
        elif feature == 'level':
            conditions.extend({feature: ['ge', n]} for n in range(6))
        else:
            conditions.extend({feature: ['ge', n]} for n in (0, 2, 4, 8, 16, 32, 64, 128))
    result.append([json.dumps(c, separators=(',', ':')) for c in conditions])
    result.append([',"set":'])
    result.append([json.dumps({k: n}, separators=(',', ':'))
                   for k, (lo, hi) in LIMITS.items() for n in range(lo, hi + 1)])
    result.append(['}]}'])
    return result


class Grammar(OriginalGrammar):
    def __init__(self, encode, eos):
        self.options = [tuple(tuple(encode(t)) for t in opts) for opts in segments()]
        if any(not option for alternatives in self.options for option in alternatives):
            raise ValueError('empty encoded grammar segment')
        self.eos, self.cache = eos, {}
