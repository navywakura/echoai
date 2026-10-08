import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from seed import s6b8 as s, s6b8_recovery as r


class Recovery(unittest.TestCase):
    def test_private_binding_preserves_the_optional_audit_argument(self):
        self.assertEqual(r.run_phase.__defaults__, (False,))
        self.assertEqual(r.run_phase.__code__, s.run_phase.__code__)

    def test_only_the_missing_round_uses_recovery(self):
        calls = []
        class Original:
            def propose(self, *args):
                calls.append(args)
                return 'original'
        with patch.object(r, 'integrity'), patch.object(s, 'generator', return_value=Original()):
            self.assertEqual(r.recovered_propose('p1', {}, {}), 'original')
            self.assertEqual(r.recovered_propose('c0', {}, {}), 'original')
        self.assertEqual([x[0] for x in calls], ['p1', 'c0'])

    def test_recovery_cannot_change_prompts_or_seeds(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base/'p2').mkdir()
            (base/'p2/payload.json').write_text(json.dumps({'requests': {'expected': []}, 'model': {'seeds': {'expected': 2}}}))
            with patch.object(r, 'integrity'), patch.object(s, 'BASE', base):
                with self.assertRaises(AssertionError):
                    r.recovered_propose('p2', {'changed': []}, {'expected': 2})
                with self.assertRaises(AssertionError):
                    r.recovered_propose('p2', {'expected': []}, {'expected': 3})

    def test_cached_incomplete_recovery_is_never_a_success(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base/'p2').mkdir()
            (base/'p2/terminal.json').write_text(json.dumps({'status': 'ERROR'}))
            with patch.object(r, 'integrity'), patch.object(r, 'BASE', base):
                with self.assertRaises(AssertionError):
                    r.audit_model('p2', {})


if __name__ == '__main__':
    unittest.main()
