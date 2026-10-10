"""Shared B11 applicability grammar: observations constrain syntax, not utility."""
from functools import lru_cache
import hashlib
import json

from echo_arc import stale_transition as patch
from echo_arc.feasible_grammar import canonical, matches, public_features
from echo_arc.precise_patch_grammar import conditions
from echo_arc.strategy_grammar import Grammar as NFA

PARAMETERS = ('REVALIDATE_NOOP', 'HOLD', 'COOLDOWN_CAP')


def witnesses(rows):
    if any(r.get('origin') != 'DEVELOPMENT_A' for r in rows):
        raise ValueError('only development observations are allowed')
    found = {p: [] for p in PARAMETERS}
    for row in rows:
        d = row['diagnostics']
        found['REVALIDATE_NOOP'].extend({'features': public_features(w['features']), 'limit': 8}
                                      for w in d['contradiction_features'])
        found['HOLD'].extend({'features': public_features(w['features']), 'current': w['value']}
                            for w in d['consumers'] if w['parameter'] == 'HOLD')
        found['COOLDOWN_CAP'].extend({'features': public_features(w['features']),
                                     'limit': w['features']['hold_remaining']}
                                    for w in d['feature_counts'] if w['features']['hold_remaining'] > 0)
    return {p: [json.loads(t) for t in sorted({canonical(w) for w in ws})]
            for p, ws in found.items()}


def build_schema(rows, history):
    observations = witnesses(rows)
    groups = []
    library = conditions()
    for parameter, ws in observations.items():
        if not ws:
            continue
        lo, hi = patch.LIMITS[parameter]
        values = list(range(max(1, lo), hi + 1)) if parameter == 'REVALIDATE_NOOP' else list(range(lo, hi + 1))
        by_value = {value: [] for value in values}
        for guard in library:
            applicable = [w for w in ws if matches(guard, w['features'])]
            if not applicable:
                continue
            for value in values:
                if parameter == 'REVALIDATE_NOOP' or any(
                    (parameter == 'HOLD' and value != w['current']) or
                    (parameter == 'COOLDOWN_CAP' and value < w['limit']) for w in applicable):
                    by_value[value].append(guard)
        for value, guards in by_value.items():
            if guards:
                groups.append({'parameter': parameter, 'value': value, 'guards': guards})
    excluded = [item for e in history if e.get('proposal')
                for item in patch.validate(e['proposal'])['patches']]
    return {'version': 11, 'origin': 'DEVELOPMENT_A', 'groups': groups,
            'excluded': excluded, 'witness_sha256': hashlib.sha256(canonical(observations).encode()).hexdigest()}


def choices(schema):
    if schema['version'] != 11 or schema['origin'] != 'DEVELOPMENT_A':
        raise ValueError('unknown B11 schema')
    excluded = {canonical(p) for p in schema['excluded']}
    result = []
    for group in schema['groups']:
        parameter, value = group['parameter'], group['value']
        if parameter not in PARAMETERS or not patch.LIMITS[parameter][0] <= value <= patch.LIMITS[parameter][1]:
            raise ValueError('unknown B11 control')
        if parameter == 'REVALIDATE_NOOP' and value == 0:
            raise ValueError('disabled transition repair')
        guards = [g for g in group['guards']
                  if canonical({'set': {parameter: value}, 'when': g}) not in excluded]
        if guards:
            result.append((parameter, value, guards))
    return result


def validate_answer(answer, schema):
    program, allowed = patch.parse(answer), choices(schema)
    if not allowed:
        if program != patch.EMPTY:
            raise ValueError('no applicable repair; abstention required')
    elif len(program['patches']) != 1:
        raise ValueError('one repair required')
    else:
        item = program['patches'][0]
        if not any(item['set'] == {p: v} and item['when'] in guards for p, v, guards in allowed):
            raise ValueError('proposal escaped development witness grammar')
    return program


class Grammar:
    def __init__(self, encode, eos, schema):
        @lru_cache(maxsize=None)
        def tokens(text):
            result = tuple(encode(text))
            if not result:
                raise ValueError('empty token segment')
            return result
        allowed = choices(schema)
        segments = [[['{"patches":[{"set":'], [canonical({p: v})], [',"when":'],
                     [canonical(g) for g in guards], ['}]}']] for p, v, guards in allowed]
        if not allowed:
            segments = [[['{"patches":[]}']]]
        self.grammars = []
        for sequence in segments:
            g = NFA.__new__(NFA)
            g.options = [tuple(tokens(t) for t in options) for options in sequence]
            g.eos, g.cache = eos, {}
            self.grammars.append(g)

    def allowed(self, prefix):
        result = set()
        for g in self.grammars:
            try:
                result.update(g.allowed(prefix))
            except ValueError:
                continue
        if not result:
            raise ValueError('generated prefix escaped B11 grammar')
        return sorted(result)
