import importlib
from dataclasses import asdict
from pathlib import Path
import unittest
from echoai.tests.test_echo58_crece_f0 import RuntimeTests


class MechanicalTests(unittest.TestCase):
    def test_worker_validates_responses_and_rejects_bad_destination(self):
        path = Path(__file__).resolve().parents[1] / 'echo58/crece/mechanical.py'
        self.assertTrue(path.exists(), 'mechanical worker missing')
        module = importlib.import_module('echoai.echo58.crece.mechanical')
        fixture = RuntimeTests()
        fixture.setUp()
        a, p = fixture.agent(lambda m, v, c: ())
        states = [{'moment': fixture.rt.DROP, 'view': asdict(a._view(fixture.obs, fixture.world, p)),
                   'context': asdict(fixture.rt.Context())}] * 200
        good = module.check('def piece(moment, v, c):\n    return (NOTE(0, HAND),)\n', states)
        self.assertTrue(good['green'], good)
        bad = module.check('def piece(moment, v, c):\n    return (GOTO((0, 0)),)\n', states)
        self.assertFalse(bad['green'])
        self.assertEqual(bad['stage'], 'effects')


if __name__ == '__main__':
    unittest.main()
