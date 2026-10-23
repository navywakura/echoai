import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from echoai.echo58.acumula.config import Config, ConfMemory


class PersistenceTests(unittest.TestCase):
    def test_fresh_process_reproduces_decisions_without_network_or_key(self):
        from echoai.echo58.crece import persistence as p
        from echoai.echo58.crece.equiv import observed, digest
        from echoai.echo58.crece.runtime import HAgent
        from echoai.echo58.acumula3 import bench as B3
        memory = ConfMemory(Config())
        source = ('def piece(moment, v, c):\n'
                  '    if moment == OUTCOME and c.intent and c.intent[0] == PICK and c.out == PICKED and c.dropped_here == (c.intent[2], v.progress):\n'
                  '        return (BAN_UNTIL_PROGRESS(c.intent[2], PICK),)\n'
                  '    return ()\n')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = p.store_piece(root, source)
            p.save_snapshot(root, root/'g.json', memory, [spec], {'generation':1})
            agent = observed(HAgent)(source=memory.probe_copy(), plugs=p.plugs_from_specs(root,[spec]))
            family = B3.MIX[0]
            world = B3.W.make_world(family, 7_000_010, 'A2')
            try:
                row = agent.run(world)
            finally:
                world.close()
            expected = {'trace':digest(agent.trace), 'result':row}
            script = '''
import json, sys, urllib.request
from pathlib import Path
def forbidden(*a, **kw):
    raise AssertionError('network forbidden during reload')
urllib.request.urlopen = forbidden
original_read = Path.read_text
def guarded(path, *a, **kw):
    if path.name.startswith('.api'):
        raise AssertionError('key access forbidden during reload')
    return original_read(path, *a, **kw)
Path.read_text = guarded
from echoai.echo58.crece.persistence import load_snapshot
from echoai.echo58.crece.equiv import observed, digest
from echoai.echo58.crece.runtime import HAgent
from echoai.echo58.acumula3 import bench as B3
root = Path(sys.argv[1])
memory, plugs, _ = load_snapshot(root, root/'g.json')
agent = observed(HAgent)(source=memory.probe_copy(), plugs=plugs)
world = B3.W.make_world(sys.argv[2], 7_000_010, 'A2')
try:
    result = agent.run(world)
finally:
    world.close()
print(json.dumps({'trace':digest(agent.trace), 'result':result}))
'''
            result = subprocess.run([sys.executable,'-c',script,d,family], capture_output=True, text=True,
                                    timeout=60, env={'PYTHONPATH':str(Path(__file__).resolve().parents[2]),
                                                     'PYTHONDONTWRITEBYTECODE':'1','PATH':os.defpath})
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(expected)))

    def test_snapshot_restores_policy_memory_and_rejects_tampered_piece(self):
        path = Path(__file__).resolve().parents[1] / 'echo58/crece/persistence.py'
        self.assertTrue(path.exists(), 'snapshot persistence missing')
        p = importlib.import_module('echoai.echo58.crece.persistence')
        memory = ConfMemory(Config())
        memory.observe(2, 4, 'ENTER', 0, 'HURT')
        source = 'def piece(moment, v, c):\n    return ()\n'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = p.store_piece(root, source)
            snapshot = p.save_snapshot(root, root/'g1.json', memory, [spec], {'generation':1})
            restored, plugs, doc = p.load_snapshot(root, root/'g1.json')
            self.assertEqual(restored.raw, memory.raw)
            self.assertEqual(doc['snapshot_sha256'], snapshot['snapshot_sha256'])
            self.assertEqual(len(plugs), 1)
            (root/'objects'/f"{spec['sha256']}.py").write_text(source + '# changed\n')
            with self.assertRaisesRegex(ValueError, 'piece hash'):
                p.load_snapshot(root, root/'g1.json')


if __name__ == '__main__':
    unittest.main()
