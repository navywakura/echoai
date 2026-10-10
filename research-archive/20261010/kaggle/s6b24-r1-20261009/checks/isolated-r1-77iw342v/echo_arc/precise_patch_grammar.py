"""Finite B5 guard library; model selects conditions and bounded values."""
import json
from echo_arc.precise_patch import FEATURES, LIMITS
from echo_arc.strategy_grammar import Grammar as NFA


def conditions():
    atoms = []
    thresholds = (0, 1, 2, 4, 8, 16, 20, 32, 40, 64, 80, 128)
    for key, (lo, hi) in FEATURES.items():
        if (lo, hi) == (0, 1):
            atoms.extend({key: ["eq", value]} for value in (0, 1))
        else:
            atoms.extend({key: [op, value]} for op in ("ge", "le") for value in thresholds if lo <= value <= hi)
    anchors = [{"reset_known": ["eq", 1]}, {"reset_pending": ["eq", 1]},
               {"body_known": ["eq", 0]}, {"motor_ready": ["eq", 1]}]
    rows = list(atoms)
    for anchor in anchors:
        rows.extend(dict(anchor, **atom) for atom in atoms if not set(anchor) & set(atom))
    pairs = [{"reset_known": ["eq", 1], "pending_effect": ["eq", 0]},
             {"reset_known": ["eq", 1], "reset_useful": ["eq", 1]},
             {"body_known": ["eq", 0], "pred_error": ["eq", 1]}]
    for pair in pairs:
        rows.extend(dict(pair, **atom) for atom in atoms if not set(pair) & set(atom))
    return [json.loads(value) for value in sorted({json.dumps(row, sort_keys=True, separators=(',', ':')) for row in rows})]


class Grammar(NFA):
    def __init__(self, encode, eos):
        segments = [['{"patches":[{"when":'],
                    [json.dumps(row, sort_keys=True, separators=(',', ':')) for row in conditions()],
                    [',"set":'],
                    [json.dumps({key: value}, separators=(',', ':')) for key, (lo, hi) in LIMITS.items()
                     for value in range(lo, hi + 1)], ['}]}']]
        self.options = [tuple(tuple(encode(text)) for text in options) for options in segments]
        if any(not tokens for options in self.options for tokens in options):
            raise ValueError("empty grammar segment")
        self.eos, self.cache = eos, {}
