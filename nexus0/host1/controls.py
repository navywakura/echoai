"""Negative controls never receive an actuator handle."""
import copy
from pathlib import Path
from .world import Local, episode, audit_episode
from .probes import communication


def mutants():
    source = (Path(__file__).parent/'core.py').read_text()
    variants = {
        'no_source': ('source*64+', '0*64+'),
        'no_sign': ('(symbol-1)*16+', '(1-1)*16+'),
        'no_context': ('+context\n', '+0\n'),
        'button_learning': ("if self.policy == 'button':", "if self.policy == 'consequence':"),
        'ignore_consequence': ('success = sum((a-b)**2 for a, b in zip(p[\'target_mm\'], receipt[\'position_mm\'])) <= 350**2', 'success = True'),
        'communication_gate': ("if not request['safe']:", 'if False:'),
    }
    values = {}
    for name, (old, new) in variants.items():
        if source.count(old) != 1:
            raise ValueError('anchor '+name)
        namespace = {}
        exec(compile(source.replace(old, new), '<host1-mutant-'+name+'>', 'exec'), namespace)

        class Adapter(Local):
            def call(self, request):
                if request['op'] == 'init':
                    self.agent = namespace['Host'](request['policy'])
                    return dict(ready=True)
                return super().call(request)

        if name == 'communication_gate':
            values[name] = not all(row['ok'] for row in communication(Adapter()))
        else:
            r = episode(20263901, 'consequence', Adapter())
            values[name] = not (r['useful'] == 24 and r['dropped'] == r['recovered'] == 16 and r['no_button_updates'])
    return values


def corruptions():
    original = episode(20263901, 'consequence')
    values = {}
    for name in ('publication', 'receipt', 'source', 'choice', 'count'):
        bad = copy.deepcopy(original)
        if name == 'publication':
            bad['trace'][0]['claim']['published_ns'] += 1
        elif name == 'receipt':
            bad['trace'][0]['receipt']['position_mm'][1] *= -1
        elif name == 'source':
            bad['trace'][0]['claim']['source'] ^= 1
        elif name == 'choice':
            bad['evaluations'][0]['chosen'] ^= 1
        else:
            bad['useful'] += 1
        values[name] = not audit_episode(bad)
    return values
