"""R4 protocol recovery, reusing R3 transport/accounting without changing it."""
import json
from functools import lru_cache
from types import FunctionType
from seed import s6b23_model as prior
from seed.s6b23_model import *
from echo_arc.s6b20_search import atoms, VALUES


@lru_cache(maxsize=1)
def grammar():
    """All legal guards, canonical key ordering, no duplicate features or repair."""
    def lit(text):
        return json.dumps(text)
    def key(text):
        return lit(json.dumps(text)) + ' ws ' + lit(':') + ' ws '
    by_feature = {}
    for feature, op, value in atoms():
        by_feature.setdefault(feature, []).append(
            lit('[') + ' ws ' + lit(json.dumps(op)) + ' ws ' + lit(',') + ' ws ' + lit(str(value)) + ' ws ' + lit(']'))
    features = sorted(by_feature)
    when = key('when') + lit('{') + ' ws g0n3 ws ' + lit('}')
    edit = key('set') + lit('{') + ' ws ' + key('HOLD') + 'hold ws ' + lit('}')
    lines = ['root ::= ws ' + lit('{') + ' ws ' + key('patches') + lit('[') + ' ws patch ws ' +
             lit(']') + ' ws ' + lit('}') + ' ws',
             'patch ::= ' + lit('{') + ' ws ( ' + when + ' ws ' + lit(',') + ' ws ' + edit +
             ' | ' + edit + ' ws ' + lit(',') + ' ws ' + when + ' ) ws ' + lit('}'),
             'ws ::= [ \\t\\n\\r]{0,4}',
             'hold ::= ' + ' | '.join(lit(str(v)) for v in VALUES)]
    for i, feature in enumerate(features):
        lines.append(f'f{i} ::= ' + key(feature) + '( ' + ' | '.join(by_feature[feature]) + ' )')
        for n in range(1, 4):
            rule = f'g{i}n{n} ::= f{i}'
            if i < len(features) - 1:
                if n > 1:
                    rule += f' ( ws {lit(",")} ws g{i+1}n{n-1} )?'
                rule += f' | g{i+1}n{n}'
            lines.append(rule)
    return '\n'.join(lines) + '\n'


def config():
    value = prior.config()
    value.update(grammar_constraint=True, grammar_sha256=sha(grammar()),
                 template_validation='ChatML plus eight real format inferences; R4',
                 invalid_output='instrument stop; no semantic repair or silent retry')
    return value


def command(spec, prompt, seed):
    cmd = prior.command(spec, prompt, seed)
    return cmd[:-2] + ['--grammar', grammar()] + cmd[-2:]


def _raw_propose(*args, **kwargs):
    scope = dict(prior.propose.__globals__, **globals())
    return FunctionType(prior.propose.__code__, scope, prior.propose.__name__, prior.propose.__defaults__)(*args, **kwargs)


def propose(*args, **kwargs):
    result = _raw_propose(*args, **kwargs)
    if not result['transport_ok'] or result['proposal'] is None:
        raise RuntimeError('B23-R4 instrument failure: ' + str(result.get('error')))
    return result
