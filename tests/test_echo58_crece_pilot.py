import importlib
from pathlib import Path
import unittest
import tempfile


class GateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).resolve().parents[1] / 'echo58/crece/pilot.py').exists(), 'pilot missing')
        self.pilot = importlib.import_module('echoai.echo58.crece.pilot')

    def test_global_gain_cannot_hide_family_regression_or_damage(self):
        base = {'a': {'success': 9, 'harm': 0}, 'b': {'success': 0, 'harm': 0}}
        regression = {'a': {'success': 8, 'harm': 0}, 'b': {'success': 3, 'harm': 0}}
        damage = {'a': {'success': 10, 'harm': 1}, 'b': {'success': 0, 'harm': 0}}
        good = {'a': {'success': 10, 'harm': 0}, 'b': {'success': 0, 'harm': 0}}
        self.assertFalse(self.pilot.gate(base, regression))
        self.assertFalse(self.pilot.gate(base, damage))
        self.assertFalse(self.pilot.gate(base, base))
        self.assertTrue(self.pilot.gate(base, good))

    def test_source_extraction_only_removes_markdown_wrapper(self):
        body = 'def piece(moment, v, c):\n    return ()\n'
        self.assertEqual(self.pilot.extract_code('```python\n' + body + '```'), body)
        self.assertEqual(self.pilot.extract_code(body), body)

    def test_partial_pilot_is_rejected_before_another_api_attempt(self):
        self.assertTrue(hasattr(self.pilot, 'ensure_fresh'), 'partial-run guard missing')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'f1-pilot.json'
            (Path(d) / 'f1-trial-0.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'partial'):
                self.pilot.ensure_fresh(path)


if __name__ == '__main__':
    unittest.main()
