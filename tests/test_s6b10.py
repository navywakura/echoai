import importlib.util
import json
from pathlib import Path
import pickle
import tempfile
import unittest

from echo_arc import feasible_grammar as g, feasible_requests as prompts, stale_transition as patch
from seed import s6b10 as s


def features(**updates):
    return dict({key: lo for key, (lo, _) in patch.FEATURES.items()}, **updates)


def row(*observations, levels=0, origin='DEVELOPMENT_A'):
    return {'origin': origin, 'levels_completed': levels, 'game': 'private-id', 'diagnostics': {
        'counts': {'contradictory_noop': len(observations)},
        'contradiction_features': [{'features': f, 'count': 1} for f in observations]}}


def proposal(value=3, guard=None):
    return {'patches': [{'set': {'REVALIDATE_NOOP': value},
                         'when': {'motor_ready': ['eq', 0]} if guard is None else guard}]}


class Grammar(unittest.TestCase):
    def test_filter_requires_joint_observation_not_independent_feature_ranges(self):
        schema = g.build_schema([row(features(count_known=0, motor_ready=1),
                                    features(count_known=1, motor_ready=0))], [])
        impossible = proposal(3, {'count_known': ['eq', 1], 'motor_ready': ['eq', 1]})
        with self.assertRaisesRegex(ValueError, 'witness grammar'):
            g.validate_answer(json.dumps(impossible), schema)
        g.validate_answer(json.dumps(proposal()), schema)
        for bad in (proposal(0), {'patches': [{'set': {'HOLD': 30}, 'when': {'motor_ready': ['eq', 0]}}]}):
            with self.assertRaises(ValueError):
                g.validate_answer(json.dumps(bad), schema)

    def test_token_language_enforces_history_without_selecting_one_winning_value(self):
        schema = g.build_schema([row(features(stagnation=64))], [{'proposal': proposal(3), 'B': {'secret': 42}}])
        grammar = g.Grammar(lambda text: tuple(text.encode()), 256, schema)
        for value in (1, 2, 4, 8):
            text = json.dumps(proposal(value), separators=(',', ':'))
            tokens = list(text.encode())
            for index, token in enumerate(tokens):
                self.assertIn(token, grammar.allowed(tokens[:index]))
            self.assertIn(256, grammar.allowed(tokens))
            self.assertEqual(grammar.allowed(tokens + [256, 0, 0]), [256])
            g.validate_answer(text, schema)
        with self.assertRaises(ValueError):
            g.validate_answer(json.dumps(proposal(3)), schema)
        self.assertNotIn('secret', json.dumps(schema))

    def test_absence_of_evidence_is_abstention_and_protected_data_is_rejected(self):
        schema = g.build_schema([row()], [])
        grammar = g.Grammar(lambda text: tuple(text.encode()), 256, schema)
        tokens = list(b'{"patches":[]}')
        for index, token in enumerate(tokens):
            self.assertIn(token, grammar.allowed(tokens[:index]))
        self.assertEqual(grammar.allowed(tokens), [256])
        g.validate_answer('{"patches":[]}', schema)
        with self.assertRaises(ValueError):
            g.build_schema([row(features(), origin='PROTECTED_B')], [])

    def test_requests_sanitize_feedback_and_share_mask_rule(self):
        observations = [row(features(stagnation=64), levels=2), row(), row(features())]
        prior = [{'verdict': 'V4', 'B': {'private_map': 17}, 'reason': 'SECRET', 'A': {'gain': 2}}]
        for arm in ('echo', 'fijo'):
            request = prompts.requests(arm, 1, 1, s.strategy(), {'rows': observations}, prior)[0]
            self.assertEqual(request['id'], 1)
            text = json.dumps(request)
            for forbidden in ('private_map', 'private-id', 'SECRET'):
                self.assertNotIn(forbidden, text)
            self.assertEqual(request['guard_schema'], g.build_schema(prompts.select(observations, arm), prior))
        self.assertEqual(prompts.select(observations, 'echo')[0]['levels_completed'], 2)
        self.assertEqual(prompts.select(observations, 'fijo')[0]['levels_completed'], 0)

    def test_pipeline_namespace_model_wrapper_and_unopened_cohort(self):
        from seed import s6b10_exam as exam
        self.assertEqual(s.run_phase.__defaults__, (False,))
        self.assertIs(s.measure.__globals__['play_one'], s.play_one)
        self.assertIs(s.run_phase.__globals__['requests'], s.requests)
        self.assertIs(exam.run.__globals__['s'], s)
        self.assertIs(exam.development.__globals__['development_one'], exam.development_one)
        pickle.dumps(s.play_one)
        pickle.dumps(exam.development_one)
        self.assertNotEqual(s.EXAM_SEEDS, s.parent.EXAM_SEEDS)
        generator = s.generator()
        code = generator.template().replace('PAYLOAD', repr('e30='))
        compile(code, 'B10-wrapper', 'exec')
        self.assertIn('row_grammars[batch_id].allowed', code)
        self.assertIn("r['guard_schema']", code)
        self.assertFalse(generator.metadata('p0')['enable_gpu'])
        self.assertEqual(generator.metadata('c5')['id'], 'navywakura/echo45-s6b10-c5-20260929')


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('arcengine'), 'managed ARC runtime')
class Native(unittest.TestCase):
    def test_counting_actual_joint_contradictions_preserves_behavior(self):
        from echo_arc import agent, runner
        from echo_arc.observe import Journal
        from echo_arc.temporal_bench import _gym_env
        from echo_arc.transition_evidence import Recorder
        for program in (patch.EMPTY, proposal(3, {'stagnation': ['ge', 32]})):
            value = s.strategy(program)
            seed = runner.seed_for(_gym_env(3, 19).game_id, 0)
            agent._COMP_CACHE.clear()
            native = s.Execution.play(_gym_env(3, 19), 500, seed, value)
            with tempfile.TemporaryDirectory() as directory:
                recorder = Recorder(Journal(Path(directory) / 'arc-decisions.jsonl'), origin='DEVELOPMENT_A', program=program)
                agent._COMP_CACHE.clear()
                try:
                    observed = s.Execution.play(_gym_env(3, 19), 500, seed, value, recorder)
                finally:
                    recorder.close()
                self.assertEqual(native, observed)
                summary = recorder.summary()
                count = sum(w['count'] for w in summary['contradiction_features'])
                self.assertEqual(count, summary['counts'].get('contradictory_noop', 0))
                if program == patch.EMPTY:
                    self.assertGreater(count, 0)


if __name__ == '__main__':
    unittest.main()
