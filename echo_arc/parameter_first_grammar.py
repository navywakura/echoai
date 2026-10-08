"""Same bounded B5 language, but choose the control before its guard.

No value, guard, score or known repair is injected. Both experimental arms
must use this order if a future condition adopts it.
"""
import json
from echo_arc.precise_patch import LIMITS
from echo_arc.precise_patch_grammar import conditions
from echo_arc.strategy_grammar import Grammar as NFA


class Grammar(NFA):
    def __init__(self, encode, eos):
        segments = [['{"patches":[{"set":'],
                    [json.dumps({key:value},separators=(',',':')) for key,(lo,hi) in LIMITS.items()
                     for value in range(lo,hi+1)], [',"when":'],
                    [json.dumps(row,sort_keys=True,separators=(',',':')) for row in conditions()], ['}]}']]
        self.options = [tuple(tuple(encode(text)) for text in options) for options in segments]
        if any(not tokens for options in self.options for tokens in options):
            raise ValueError('empty grammar segment')
        self.eos, self.cache = eos, {}
