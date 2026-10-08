"""Campaign witnesses: counterfactual credit, regression, resumability, journal tampering."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from seed import game_selfimprove as s


class CampaignTests(unittest.TestCase):
    def test_chain_tampering_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'journal.jsonl'
            s.journal(p, {'kind': 'test', 'value': 3})
            s.journal(p, {'kind': 'test', 'value': 4})
            self.assertEqual(len(s.events(p)), 2)
            p.write_text(p.read_text().replace('"value":3', '"value":9'))
            with self.assertRaises(ValueError):
                s.events(p)

    def run_witness(self, regresses=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s.atomic(root / 'profile.json', {'sources': s.hashes()})
            answer = json.dumps({'defaults': {'HOLD': 60}, 'rules': []})
            calls = []
            def proposer(prompts, seed):
                calls.append(seed)
                return [answer], [{'cost_usd': 0}]
            def measure(root, policy, specs, workers):
                changed = bool(policy['defaults'])
                b = specs == s.B
                levels = 10 + (2 if changed and not b else -1 if changed and b and regresses else 0)
                row = {'levels_completed': 1, 'actions': [], 'actions_per_level': [], 'resets': 0}
                return {'levels': levels, 'score': 1, 'rows': [row], 'trace_digest': s.sha([policy, levels])}
            with patch.object(s, 'CALLS', 2), patch.object(s, 'ROUND_SIZE', 1), patch.object(s, 'measure', measure):
                s.run(root, proposer, 1)
                self.assertEqual(len(calls), 4)
                first = s.events(root / 'echo' / 'journal.jsonl')
                verdicts = [e['verdict'] for e in first if e['kind'] == 'verdict']
                self.assertEqual(verdicts, ['V4', 'V4'] if regresses else ['accepted', 'V3'])
                # A proposal matching the current agent earns zero counterfactual credit.
                s.run(root, lambda *_: self.fail('resume requested model again'), 1)
                self.assertEqual(first, s.events(root / 'echo' / 'journal.jsonl'))
                strategies = json.loads((root / 'strategies.json').read_text())
                self.assertEqual(bool(strategies['echo']['defaults']), not regresses)
                self.assertTrue(strategies['sinfiltro']['defaults'])

    def test_no_credit_for_an_already_accepted_change_and_completed_resume(self):
        self.run_witness()

    def test_regression_is_rejected_but_unfiltered_keeps_it(self):
        self.run_witness(regresses=True)

    def test_answers_survive_verifier_interruption(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            s.atomic(root / 'profile.json', {'sources': s.hashes()})
            answer = json.dumps({'defaults': {'HOLD': 60}, 'rules': []})
            requests = [{'id': 0, 'type': 'P1', 'prompt': 'saved input'}]
            s.journal(root / 'fijo' / 'journal.jsonl', {'kind': 'answers', 'round': 0,
                      'requests': requests, 'answers': [answer], 'usages': [{'cost_usd': 0}]})
            def fail(*args):
                raise RuntimeError('interrupted before verification')
            with patch.object(s, 'CALLS', 1), patch.object(s, 'ROUND_SIZE', 1), patch.object(s, 'measure', fail):
                with self.assertRaises(RuntimeError):
                    s.run(root, lambda *_: self.fail('lost saved model response'), 1)
            self.assertEqual(s.events(root / 'fijo' / 'journal.jsonl')[0]['answers'], [answer])


if __name__ == '__main__':
    unittest.main()
