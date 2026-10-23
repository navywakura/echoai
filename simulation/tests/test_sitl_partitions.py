"""A revised confirmation must never silently reuse exposed flight seeds."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echo5 import sitl


class SitlPartitionTests(unittest.TestCase):
    def contract(self, root):
        contract = deepcopy(json.loads(sitl.CONTRACT.read_text()))
        contract['sitl'].update(confirmation_seed=971809,
            reserved_confirmation_interval=[971809, 971814],
            retired_confirmation_intervals=[[861703, 861708]])
        path = root / 'contract.json'
        path.write_text(json.dumps(contract))
        return path

    def test_fresh_confirmation_uses_registered_interval(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.contract(Path(name))
            with patch.object(sitl, 'CONTRACT', path):
                config = sitl._config(dict(output=str(sitl.ROOT/'artifacts/partition-test'),
                                          phase='confirmation', seed=971809))
                self.assertEqual(config['seed'], 971809)
                with self.assertRaises(ValueError):
                    sitl._config(dict(output=str(sitl.ROOT/'artifacts/partition-test'),
                                      phase='confirmation', seed=861703))

    def test_development_rejects_current_and_retired_holdouts(self):
        with tempfile.TemporaryDirectory() as name:
            path = self.contract(Path(name))
            with patch.object(sitl, 'CONTRACT', path):
                for seed, cases in [(861703, 1), (861702, 2), (971809, 1), (971808, 2), (971814, 1)]:
                    with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, 'reserved_confirmation_seed_interval'):
                        sitl._config(dict(output=str(sitl.ROOT/'artifacts/partition-test'),
                                          seed=seed, cases=cases))
                self.assertEqual(sitl._config(dict(output=str(sitl.ROOT/'artifacts/partition-test'),
                                                  seed=751701))['seed'], 751701)


if __name__ == '__main__':
    unittest.main()
