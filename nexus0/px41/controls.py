"""Actual source mutants and corrupted flight records, not self-reported flags."""
import io
import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from . import core
from .evaluate import audit


def mutants():
    from echoai.tests import test_px41
    source = Path(core.__file__).read_text()
    edits = {
        'no_ttl': ('now-request[\'published_ns\'] > TTL', 'False'),
        'no_envelope': ("return deny('envelope')", 'pass'),
        'no_authority': ("return deny('authority')", 'pass'),
        'ack_is_arrival': ("self.state = 'executing'", "self.state = 'complete'"),
        'no_ack_identity': ("ack['system'] != self.system", 'False'),
        'no_exclusion': ("if self.state != 'ready':", 'if False:'),
    }
    results = {}
    for name, (old, new) in edits.items():
        if source.count(old) != 1:
            raise ValueError('mutant anchor '+name)
        module = types.ModuleType('px41_mutant')
        exec(compile(source.replace(old, new), name, 'exec'), module.__dict__)
        with patch.object(test_px41, 'Gateway', module.Gateway):
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_px41.GatewayTests)
            result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        results[name] = dict(detected=not result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors))
    return results


def corruptions(root):
    root = Path(root)
    results = {}
    for kind in ('wsp', 'target', 'ack', 'ulog'):
        with tempfile.TemporaryDirectory(prefix='px41-negative-') as directory:
            dest = Path(directory)/'flight'
            shutil.copytree(root, dest, symlinks=True)
            if kind == 'ulog':
                path = next(dest.rglob('*.ulg'))
                content = path.read_bytes()
                path.write_bytes(content[:-1]+bytes([content[-1] ^ 1]))
            else:
                path = dest/'out/trace.jsonl'
                rows = [json.loads(x) for x in path.read_text().splitlines()]
                if kind == 'wsp':
                    next(r for r in rows if r['kind'] == 'send')['wsp'] = '00'*16
                elif kind == 'target':
                    next(r for r in rows if r['kind'] == 'send')['target_mm'][1] += 6000
                else:
                    next(r for r in rows if r['kind'] == 'ack')['ack']['result'] = 2
                path.write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows))
            result = audit(dest)
            results[kind] = dict(detected=not result['valid'], findings=result['findings'])
    return results
