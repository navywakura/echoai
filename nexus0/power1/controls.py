"""Source mutants and altered records must fail independent checks."""
import copy
import io
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from . import core
from .world import audit_episode


def mutants():
    from echoai.tests import test_power1
    source = Path(core.__file__).read_text()
    changes = {
        'no_return_cost': ('else out+home_goal+landing+RESERVE', 'else out+landing+RESERVE'),
        'no_landing_cost': ("landing = landed_cost['upper']", 'landing = 0'),
        'no_uncertainty': ("def route(self, path, field='upper'):", "def route(self, path, field='nominal'):"),
        'no_reserve': ('RESERVE = 40', 'RESERVE = 0'),
        'no_expiry': ("frame['now_ns']-battery['capture_ns'] <= TTL", "frame['now_ns']-battery['capture_ns'] <= 10**15"),
        'no_latch': ('        if self.stopped:\n', '        self.returning = False\n        if self.stopped:\n'),
    }
    results = {}
    for name, (old, new) in changes.items():
        if source.count(old) != 1:
            raise ValueError('mutant anchor '+name)
        module = types.ModuleType('power1_mutant')
        exec(compile(source.replace(old, new), name, 'exec'), module.__dict__)
        with patch.object(test_power1, 'Guard', module.Guard):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(test_power1.PowerTests))
        results[name] = dict(detected=not result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors))
    return results


def trace_mutations(record, model):
    results = {}
    for name in ('sensor', 'wsp', 'private_cost', 'outcome'):
        changed = copy.deepcopy(record)
        first = changed['trace'][0]
        if name == 'sensor':
            first['frame']['battery']['remaining'] += 1
        elif name == 'wsp':
            first['decision']['wsp'] = '00'*16
        elif name == 'private_cost':
            first['transition']['cost'] += 1
        else:
            changed['result']['remaining'] += 1
        results[name] = not audit_episode(changed, model)
    return results
