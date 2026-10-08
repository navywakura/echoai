"""Regression tests for the B23-R3 format failure and its isolated recovery."""
import copy
import json
import tempfile
import unittest
import os
import subprocess
import random
from pathlib import Path
from unittest.mock import patch

from tests.test_s6b23 import fixture
from echo_arc import s6b23_search as prior
from echo_arc import s6b23r4_search as search
from seed import s6b23r4 as runner, s6b23r4_model as model
from seed import s6b23r4_preflight as preflight


class RecoveryTests(unittest.TestCase):
    def test_prompt_separates_allowed_values_from_executable_example(self):
        policy, base, event = fixture()
        before = prior.model_request('N7', 1, 9, policy, base, [event])
        req = search.model_request('N7', 1, 9, policy, base, [event])
        payload, original = json.loads(req['prompt']), json.loads(before['prompt'])
        self.assertNotIn('response_schema', payload)
        self.assertEqual(search.validate_proposal(payload['format_example']), payload['format_example'])
        self.assertIs(type(payload['format_example']['patches'][0]['set']['HOLD']), int)
        for key in ('policy', 'history', 'contexts', 'base', 'allowed_atoms', 'latest_details'):
            self.assertEqual(payload[key], original[key])
        req14 = search.model_request('N14', 1, 9, policy, base, [event])
        self.assertEqual(req['prompt'], req14['prompt'])

    def test_untrusted_input_cannot_add_winners_or_protected_data(self):
        policy, base, event = fixture()
        obj = dict(policy=policy, base=base, own_history=[event], kind='N7', index=1, seed=9)
        with self.assertRaises(ValueError):
            search.from_bytes(json.dumps(dict(obj, winner={})))
        obj['own_history'][0]['development']['origin'] = 'PROTECTED_B'
        with self.assertRaises(ValueError):
            search.from_bytes(json.dumps(obj))

    def test_model_command_uses_frozen_grammar(self):
        spec = dict(cli='llama-cli', model='weights.gguf', backend='cuda', gpu_layers=99, tensor_split='1,1')
        cmd = model.command(spec, Path('prompt.txt'), 7)
        self.assertEqual(cmd[cmd.index('--grammar') + 1], model.grammar())
        self.assertIn('--no-context-shift', cmd)
        self.assertTrue(model.config()['grammar_constraint'])

    def test_parser_rejects_actual_failure_shapes_without_repair(self):
        good = preflight.cases()[0]['expected']
        self.assertEqual(model.strict_answer(json.dumps(good)), good)
        bad = copy.deepcopy(good)
        bad['patches'][0]['set']['HOLD'] = [0, 1, 2, 4]
        cases = [json.dumps(bad), '```json\n' + json.dumps(good) + '\n```',
                 '{"patches":[],"patches":[]}', '{"patches":[{"when":"world_events >= 8","set":{"HOLD":4}}]}']
        for value in cases:
            with self.subTest(value=value), self.assertRaises((ValueError, KeyError, TypeError)):
                model.strict_answer(value)

    def test_preflight_has_no_game_observations(self):
        self.assertEqual(len(preflight.cases()), 4)
        for case in preflight.cases():
            search.validate_proposal(case['expected'])
            self.assertNotIn('base', case['request'])
            self.assertNotIn('own_history', case['request'])
            self.assertIsNone(case['request'].get('predicted_gain'))

    def test_bad_preflight_stops_before_science(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((RuntimeError, FileNotFoundError)):
                preflight.verify(Path(tmp), {}, 'profile')
        with patch.object(runner, 'integrity', return_value={}), \
             patch.object(runner, 'read', return_value={}), \
             patch.object(runner.model, 'verify_pair'), \
             patch.object(runner.preflight, 'run', side_effect=RuntimeError('format gate')), \
             patch.object(runner, 'micro') as micro, tempfile.TemporaryDirectory() as tmp, \
             patch.object(runner, 'ROOT', Path(tmp)):
            with self.assertRaisesRegex(RuntimeError, 'format gate'):
                runner.follow()
            micro.assert_not_called()

    def test_transport_failure_cannot_be_scientific_negative(self):
        with patch.object(model, '_raw_propose', return_value={'transport_ok': False, 'proposal': None, 'error': 'timeout'}):
            with self.assertRaisesRegex(RuntimeError, 'instrument'):
                model.propose(Path('/tmp'), {}, 'N7', 0, {}, 1, 'p')

    def test_invalid_grammar_output_stops_immediately(self):
        with patch.object(model, '_raw_propose', return_value={'transport_ok': True, 'proposal': None, 'error': 'invalid'}):
            with self.assertRaisesRegex(RuntimeError, 'instrument'):
                model.propose(Path('/tmp'), {}, 'N7', 0, {}, 1, 'p')

    def test_budget_and_acceptance_not_relaxed(self):
        self.assertEqual(runner.CELLS, ('N14', 'N7'))
        self.assertEqual(runner.MAX_GAMES, 3756)
        self.assertEqual(sum(runner.CAPS.values()), runner.MAX_GAMES)
        self.assertFalse(runner.passes(dict(gain=1, loss_indices=[])))
        self.assertFalse(runner.passes(dict(gain=9, loss_indices=[0])))
        self.assertTrue(runner.passes(dict(gain=2, loss_indices=[])))

    def test_independent_audit_runs_recovery_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = {'program': []}
            result = {'levels': 61}
            def fake_run(cmd, **kwargs):
                self.assertIn('seed.s6b23r4', cmd)
                task = runner.read(Path(cmd[-1]))
                runner.atomic(root / 's-N7/audits/baseline.json', dict(valid=True,
                    measurement_sha256=runner.sha(result), task_sha256=runner.sha(task)))
                runner.atomic(root / 's-N7-audit/measurements/baseline.json', result)
            with patch.object(runner, 'ROOT', root), patch.object(runner, 'INPUT', root / 'input'), \
                 patch.object(runner, 'measure', return_value=result), \
                 patch.object(runner.subprocess, 'run', side_effect=fake_run):
                self.assertEqual(runner.triple('s-N7', 'baseline', policy, runner.A), result)


@unittest.skipUnless(os.environ.get('B23_GBNF_VALIDATOR'), 'native llama.cpp validator configured separately')
class NativeGrammarTests(unittest.TestCase):
    def test_native_parser_accepts_language_and_rejects_failure_shapes(self):
        from echo_arc.s6b20_search import atoms, VALUES
        cases = []
        for key, op, value in atoms():
            cases.append(({'patches': [{'when': {key: [op, value]}, 'set': {'HOLD': 4}}]}, True))
        generator = random.Random(823004)
        choices = {}
        for key, op, value in atoms():
            choices.setdefault(key, []).append([op, value])
        for size in (1, 2, 3):
            for hold in VALUES:
                for _ in range(4):
                    guard = {k: generator.choice(choices[k]) for k in sorted(generator.sample(sorted(choices), size))}
                    cases.append(({'patches': [{'when': guard, 'set': {'HOLD': hold}}]}, True))
        good = preflight.cases()[0]['expected']
        for hold in (3, 5, 40, -1, 4.5, True, [4], '4'):
            p = copy.deepcopy(good); p['patches'][0]['set']['HOLD'] = hold
            cases.append((p, False))
        for guard in ({}, {'seed': ['eq', 1]}, {'body_known': ['le', 1]},
                      {'body_known': ['eq', 2]}, {k: ['eq', 0] for k in ('body_known', 'click_only', 'count_known', 'goal_evidence')}):
            p = copy.deepcopy(good); p['patches'][0]['when'] = guard
            cases.append((p, False))
        cases.extend([({'patches': good['patches'] * 2}, False), ({'patches': []}, False),
                      ('```json\n' + json.dumps(good) + '\n```', False),
                      ('{"patches":[{"when":{"body_known":["eq",0],"body_known":["eq",1]},"set":{"HOLD":4}}]}', False)])
        with tempfile.TemporaryDirectory() as tmp:
            grammar, source = Path(tmp) / 'grammar.gbnf', Path(tmp) / 'case.json'
            grammar.write_text(model.grammar())
            for obj, valid in cases:
                for sorted_keys in (False, True):
                    source.write_text(obj if isinstance(obj, str) else json.dumps(obj, sort_keys=sorted_keys))
                    result = subprocess.run([os.environ['B23_GBNF_VALIDATOR'], str(grammar), str(source)], capture_output=True, text=True)
                    with self.subTest(obj=obj, sorted_keys=sorted_keys):
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual('Input string is valid according to the grammar.' in result.stdout, valid, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
