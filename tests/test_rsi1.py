import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seed import rsi1 as r
from seed import rsi1_queue as q


class PrivateRSI(unittest.TestCase):
    def test_source_and_command_proposals_rejected(self):
        for program in ([['open', '/tmp/x'], ['crop']], [['__import__'], ['crop']],
                        [['crop']], [['crop'], ['eval']], [['up2']] * 4):
            with self.assertRaises(ValueError):
                r.checked_program(program)
        with self.assertRaises(ValueError):
            r.parse_reply('def op(g): return g')

    def test_structured_proposal_ignores_prose(self):
        self.assertEqual(r.parse_reply('I ran tests! {"steps":[["crop"],["rot90"]]}'),
                         [['crop'], ['rot90']])

    def test_private_output_not_in_solver_or_prompt(self):
        task = r.corpus(311, 'unit', 1)[0]
        task['test'][0]['output'] = [['PRIVATE_SENTINEL']]
        self.assertNotIn('PRIVATE_SENTINEL', r.canonical(r.public(task)))
        self.assertNotIn('PRIVATE_SENTINEL', r.prompt_for([task], [{'task':task['id'],'correct':False}], r.Library(), True))

    def test_partitions_deterministic_and_distinct(self):
        a = r.corpus(311, 'dev-1', 2)
        self.assertEqual(a, r.corpus(311, 'dev-1', 2))
        self.assertNotEqual(a[0]['train'], r.corpus(311, 'final-exam', 2)[0]['train'])

    def test_score_regression_veto(self):
        before = [{'task':str(i), 'correct':i == 0} for i in range(4)]
        after = [{'task':str(i), 'correct':i != 0} for i in range(4)]
        v = r.decision(before, after)
        self.assertEqual(len(v['gains']), 3)
        self.assertFalse(v['accepted'])
        self.assertEqual(v['losses'], ['0'])

    def test_replay_failure_stops_not_negative_result(self):
        before = [{'task':str(i), 'correct':False} for i in range(2)]
        after = [{'task':str(i), 'correct':True} for i in range(2)]
        bad = [{'task':str(i), 'correct':i == 0} for i in range(2)]
        with patch.object(r, 'measure', side_effect=[after, bad]):
            with self.assertRaisesRegex(RuntimeError, 'replay'):
                r.attempt(r.Library(), [], before, [['crop'], ['rot90']], 1)

    def test_accepted_program_uses_existing_library(self):
        lib = r.Library({'rsi001': {'steps': [['crop'], ['rot90']], 'tasks':[], 'round':1}})
        self.assertIsInstance(lib, r.learn.Library)
        task = r.corpus(311, 'unit', 1)[0]
        self.assertTrue(r.measure([task], lib, True)[0]['correct'])

    def test_model_call_failure_counts_budget_without_retry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(r, 'ROOT', Path(d)), \
             patch.object(r.subprocess, 'run', side_effect=RuntimeError('failed')) as run:
            with self.assertRaises(RuntimeError):
                r.propose('x', 'unit', {'llama_cli':'none', 'model_path':'none'})
            self.assertEqual(json.loads((Path(d)/'budget.json').read_text())['model_calls_reserved'], 1)
            self.assertEqual(run.call_count, 1)
            with self.assertRaisesRegex(RuntimeError, 'recovery'):
                r.propose('x', 'unit', {'llama_cli':'none', 'model_path':'none'})
            self.assertEqual(run.call_count, 1)

    def test_zero_spend_and_bounded_calls(self):
        self.assertEqual(r.CFG['spend_eur'], 0)
        self.assertEqual(r.CFG['max_model_calls'], 3 * 5 * 3 + 3 * 2 * 2)

    def test_queue_waits_and_rejects_invalid_completion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertFalse(q.gate(root))
            r.atomic(root/'status.json', {'stage':'BLOCKED'})
            with self.assertRaises(RuntimeError): q.gate(root)

    def test_complete_small_run_with_invalid_model_preserves_red_and_exam(self):
        # Real solver and five-generation orchestration; only transport is a double.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            model=root/'model';model.write_bytes(b'GGUF fixture')
            profile={'model_path':str(model),'model_sha256':r.file_sha(model)}
            cfg=dict(r.CFG, replicas=[999],anchors=2,dev_per_generation=2,exam_tasks=2,research_tasks=2)
            r.atomic(root/'profile.json', profile)
            with patch.object(r,'ROOT',root), patch.object(r,'CFG',cfg), \
                 patch.object(r,'integrity',return_value=profile), \
                 patch.object(r,'propose',return_value={'program':None,'seconds':0}) as model_call, \
                 patch.object(r,'write_report'):
                r.run()
                result=json.loads((root/'result.json').read_text())
                self.assertFalse(result['S6_green']);self.assertFalse(result['RSI1_green'])
                self.assertTrue((root/'exam-freeze.json').exists())
                self.assertEqual(len(result['exam']),5)
                self.assertTrue(all(row['replay_ok'] for row in result['exam']))
                self.assertEqual(model_call.call_count,19)
            r.atomic(root/'status.json', {'stage':'DONE'})
            r.atomic(root/'result.json', {'screened':873})
            with self.assertRaises(RuntimeError): q.gate(root)

    def test_queue_requires_replays_and_solidity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            value={'screened':874, 'model_calls':0,'B_measured':False,'exam_opened':False,
                   'screen_replays':88,'soundness_checks':[{'untouched_identical':True}]*5,
                   'verified':[], 'budget':{'scheduled_games':12000}}
            r.atomic(root/'status.json', {'stage':'DONE'}); r.atomic(root/'result.json', value)
            self.assertTrue(q.gate(root))
            value['soundness_checks'][0]={'untouched_identical':False}
            r.atomic(root/'result.json', value)
            with self.assertRaises(RuntimeError): q.gate(root)


if __name__ == '__main__':
    unittest.main()
