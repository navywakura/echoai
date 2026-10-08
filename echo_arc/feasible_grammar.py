"""Mechanical witness compatibility, shared by both arms; no outcome ranking."""
from functools import lru_cache
import hashlib
import json

from echo_arc import stale_transition as patch
from echo_arc.precise_patch_grammar import conditions
from echo_arc.strategy_grammar import Grammar as NFA


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def matches(guard, features):
    return all(features[k] == v if op == 'eq' else
               features[k] >= v if op == 'ge' else features[k] <= v
               for k, (op, v) in guard.items())


def public_features(features):
    result = {key: features[key] for key in patch.FEATURES}
    if any(type(result[k]) is not int or not lo <= result[k] <= hi
           for k, (lo, hi) in patch.FEATURES.items()):
        raise ValueError('invalid observation')
    return result


def build_schema(rows, history):
    """Keep guards witnessed on A; exclude only exact previously tried repairs."""
    witnesses = []
    for row in rows:
        if row['origin'] != 'DEVELOPMENT_A':
            raise ValueError('only development A is allowed')
        for witness in row['diagnostics']['contradiction_features']:
            if type(witness['count']) is not int or witness['count'] < 1:
                raise ValueError('invalid observation count')
            witnesses.append({'features': public_features(witness['features']), 'count': witness['count']})
    features = [json.loads(text) for text in sorted({canonical(w['features']) for w in witnesses})]
    guards = [guard for guard in conditions() if any(matches(guard, f) for f in features)]
    excluded = []
    for event in history:
        if event.get('proposal'):
            for item in patch.validate(event['proposal'])['patches']:
                if set(item['set']) == {'REVALIDATE_NOOP'}:
                    excluded.append(item)
    return {'version': 1, 'origin': 'DEVELOPMENT_A', 'guards': guards,
            'excluded': [json.loads(text) for text in sorted({canonical(p) for p in excluded})],
            'witnesses': sum(w['count'] for w in witnesses),
            'witness_sha256': hashlib.sha256(canonical(witnesses).encode()).hexdigest()}


def choices(schema):
    if schema['version'] != 1 or schema['origin'] != 'DEVELOPMENT_A':
        raise ValueError('unknown witness schema')
    excluded = {canonical(item) for item in schema['excluded']}
    result = {}
    for value in range(1, 9):
        guards = []
        for guard in schema['guards']:
            item = {'set': {'REVALIDATE_NOOP': value}, 'when': guard}
            patch.validate({'patches': [item]})
            if canonical(item) not in excluded:
                guards.append(guard)
        if guards:
            result[value] = guards
    return result


def validate_answer(answer, schema):
    program, allowed = patch.parse(answer), choices(schema)
    if not allowed:
        if program != patch.EMPTY:
            raise ValueError('no witnessed repair available; only abstention allowed')
    elif len(program['patches']) != 1:
        raise ValueError('one witnessed repair required')
    else:
        item = program['patches'][0]
        if set(item['set']) != {'REVALIDATE_NOOP'} or item['when'] not in allowed.get(item['set']['REVALIDATE_NOOP'], []):
            raise ValueError('proposal escaped witness grammar')
    return program


class Grammar:
    """Union of eight segmented NFAs; the model selects value and guard."""
    def __init__(self, encode, eos, schema):
        @lru_cache(maxsize=None)
        def tokens(text):
            value = tuple(encode(text))
            if not value:
                raise ValueError('empty encoded segment')
            return value
        alternatives = choices(schema)
        segments = [[['{"patches":[{"set":'],
                     [json.dumps({'REVALIDATE_NOOP': value}, separators=(',', ':'))],
                     [',"when":'], [canonical(guard) for guard in guards], ['}]}']]
                    for value, guards in alternatives.items()]
        if not alternatives:
            segments = [[['{"patches":[]}']]]
        self.grammars = []
        for sequence in segments:
            grammar = NFA.__new__(NFA)
            grammar.options = [tuple(tokens(text) for text in options) for options in sequence]
            grammar.eos, grammar.cache = eos, {}
            self.grammars.append(grammar)

    def allowed(self, prefix):
        allowed = set()
        for grammar in self.grammars:
            try:
                allowed.update(grammar.allowed(prefix))
            except ValueError:
                continue
        if not allowed:
            raise ValueError('generated prefix escaped witness grammar')
        return sorted(allowed)
