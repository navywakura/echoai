import copy
import json
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import patch

from echo_arc import context_requests as context
from seed import s6b12 as s, s6b12_exam as exam


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = s.parent.BASE / 'c1/payload.json'
        cls.payload = json.loads(path.read_text())
        cls.over = cls.payload['requests']['local-echo-685001'][0]
        cls.short = cls.payload['requests']['local-fijo-685001'][0]
        cls.original_count, cls.short_count, cls.compacted_count = context.count_many([
            cls.over['prompt'], cls.short['prompt'], context.variant(cls.over['prompt'], 1)])

    def test_real_failed_request_fits_losslessly(self):
        self.assertEqual(self.original_count['tokens'], 6372)
        counts = {self.over['prompt']: self.original_count,
                  context.variant(self.over['prompt'], 1): self.compacted_count}
        result = context.bounded(self.over, counts.__getitem__)
        self.assertLessEqual(result['context']['tokens'], 6000)
        self.assertEqual(result['context']['tier'], 1)
        self.assertTrue(result['context']['lossless_evidence'])
        before = context.sections(self.over['prompt'])
        after = context.sections(result['prompt'])
        self.assertEqual(context.expand(after[-2]), before[-2])
        self.assertEqual(context.expand(after[-1]), before[-1])
        self.assertEqual(result['guard_schema'], self.over['guard_schema'])
        self.assertEqual(result['type'], self.over['type'])

    def test_fitting_request_keeps_all_original_bytes(self):
        result = context.bounded(self.short, lambda _: self.short_count)
        self.assertEqual({k: v for k, v in result.items() if k != 'context'}, self.short)
        self.assertEqual(result['context']['tier'], 0)

    def test_compaction_preserves_both_signs_and_protected_verdict(self):
        features = {k: i for i, k in enumerate(context.FEATURE_ORDER)}
        value = [{'verdict': 'V4', 'protected_rejection': True,
                  'contrasts': [{'effect': sign, 'sequence': [{'before': {'features': features}}]}
                                for sign in ('gain', 'loss')]}]
        self.assertEqual(context.expand(context.compact(value)), value)
        self.assertNotIn('SECRET_PROTECTED_STATE', json.dumps(context.compact(value)))

    def test_fallback_never_truncates_mandatory_instructions_or_verdicts(self):
        previous = context.sections(self.over['prompt'])
        for tier in range(2, 6):
            text = context.variant(self.over['prompt'], tier)
            changed = context.sections(text)
            self.assertEqual(len(changed[-2]), len(previous[-2]))
            self.assertEqual([r['verdict'] for r in changed[-2]], [r['verdict'] for r in previous[-2]])
            self.assertEqual([r['proposal'] for r in changed[-2]], [r['proposal'] for r in previous[-2]])
            self.assertEqual(len(changed[-1]), 3)
            self.assertIn('Current accepted program ', text)
            self.assertTrue(text.endswith('. Return JSON only.'))

    def test_oversize_is_refused_before_any_model_call(self):
        with self.assertRaisesRegex(ValueError, 'before submission'):
            context.bounded(self.over, lambda _: {'tokens': 6001, 'token_ids_sha256': 'test'})

    def test_maximum_program_and_six_contrasts_fit_before_submission(self):
        request = copy.deepcopy(self.over)
        marker = 'Current accepted program '
        start = request['prompt'].index(marker) + len(marker)
        program, size = json.JSONDecoder().raw_decode(request['prompt'][start:])
        program['patches'] = [{'set': {'REVALIDATE_NOOP': 1 + i % 8},
            'when': {'body_known': ['eq', 1], 'reset_known': ['eq', 1], 'stagnation': ['ge', 80]}}
            for i in range(32)]
        request['prompt'] = request['prompt'][:start] + context.canonical(program) + request['prompt'][start + size:]
        hs, he, _, _, history, _ = context.sections(request['prompt'])
        detail = next(r for r in history if r.get('contrasts'))
        history = [copy.deepcopy(detail) for _ in range(6)]
        request['prompt'] = request['prompt'][:hs] + context.canonical(history) + request['prompt'][he:]
        result = context.bounded(request)
        self.assertLessEqual(result['context']['tokens'], 6000)
        start = result['prompt'].index(marker) + len(marker)
        parsed, _ = json.JSONDecoder().raw_decode(result['prompt'][start:])
        self.assertEqual(parsed, program)


class ProtocolTests(unittest.TestCase):
    def test_worker_can_run_in_independent_process(self):
        self.assertIs(pickle.loads(pickle.dumps(s.play_one)), s.play_one)

    def test_remote_context_preflight_precedes_model_loading(self):
        generator = s.generator()
        code = generator.template().replace('PAYLOAD', repr('e30='))
        compile(code, 'B12-wrapper', 'exec')
        self.assertLess(code.index('S6_B12_CONTEXT_PREFLIGHT_OK'), code.index('model=AutoModelForCausalLM'))
        self.assertIn("enc['input_ids'].shape[1]<=6000", code)
        self.assertIn("_context['token_ids_sha256']", code)
        for i in range(6):
            meta = generator.metadata('c' + str(i))
            self.assertTrue(meta['is_private'])
            self.assertFalse(meta['enable_gpu'])
            self.assertFalse(meta['enable_tpu'])

    def test_remote_count_mismatch_rejected_before_model_load(self):
        generator = s.generator()
        class Tokenizer:
            def apply_chat_template(self, *args, **kwargs): return 'text'
            def encode(self, *args, **kwargs): return [1, 2]
        with tempfile.TemporaryDirectory() as directory:
            namespace = {'payload': {'requests': {'local-echo': [{'prompt': 'text', 'context': {
                'limit': 6000, 'tokens': 1}}]}}, 'tok': Tokenizer(), 'work': Path(directory)}
            with self.assertRaisesRegex(AssertionError, 'tokenizer count differs'):
                exec(generator.PREFLIGHT, namespace)
            self.assertFalse((Path(directory) / 'context-preflight.json').exists())

    def test_unqualified_campaign_cannot_open_exam(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pilot.json').write_text(json.dumps({'promote': False}))
            with patch.object(s, 'ROOT', root), patch.object(s, 'integrity', return_value={}):
                with self.assertRaises(AssertionError):
                    exam.run()
            self.assertFalse((root / 'exam/opened.json').exists())

    def test_audit_directory_created_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def replay(phase, audit):
                self.assertEqual(phase, 'campaign')
                self.assertTrue(audit)
                self.assertTrue((root / 'campaign-audit').is_dir())
            with patch.object(s, 'ROOT', root), patch.object(s, 'run_phase', side_effect=replay):
                s.main(['audit', 'campaign'])


if __name__ == '__main__':
    unittest.main()
