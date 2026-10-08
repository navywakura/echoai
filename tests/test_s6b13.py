"""B13 custody, autonomous targeting, verifier and exam gates; no games."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock

from seed import s6b13 as b, s6b13_prompt as p, s6b13_model as m, s6b13_exam as exam
from seed import s6_precise_exam
from echo_arc import stale_transition as patch
from echo_arc.contrastive_grammar import choices


def row():
    f = {k: lo for k, (lo, hi) in patch.FEATURES.items()}
    f.update(body_known=1, reset_known=1, hold_remaining=8)
    return dict(origin='DEVELOPMENT_A', levels_completed=3, score=1,
                diagnostics=dict(counts={}, contradiction_features=[{'features': f, 'count': 3}],
                    consumers=[{'parameter': 'HOLD', 'features': f, 'value': patch.DEFAULTS['HOLD'], 'count': 2}],
                    feature_counts=[{'features': f, 'count': 3}]))


def event(current, index=0):
    proposal = {'patches': [{'set': {'HOLD': 1}, 'when': {'reset_known': ['eq', 1]}}]}
    contrast = dict(case_index=0, effect='gain', levels=[1, 5], score=[1, 4],
                    actions_per_level=[[], []], first_different_action=2, sequence=[])
    return dict(id=index, base_sha256=b.sha(current), verdict='V3', A={'gain': 4}, proposal=proposal,
                B={'PRIVATE_SECRET': 'must-never-reach-prompt'},
                development=dict(origin='DEVELOPMENT_A', behavior_sha256='abc', losses=1,
                                 gains=1, changed_games=2, contrasts=[contrast]))


class GrammarAndTarget(unittest.TestCase):
    def test_compaction_preserves_every_feature(self):
        features = row()['diagnostics']['consumers'][0]['features']
        raw = {'sequence': [{'before': {'features': features, 'action': ['K', 1]}}]}
        compressed = p.compact_features(raw)
        reconstructed = dict(zip(p.FEATURE_ORDER, compressed['sequence'][0]['before']['features'], strict=True))
        self.assertEqual(features, reconstructed)
        self.assertEqual(raw['sequence'][0]['before']['action'], compressed['sequence'][0]['before']['action'])

    def test_current_aware_filter(self):
        current = b.strategy(program={'patches': [{'set': {'REVALIDATE_NOOP': 1},
                                                    'when': {'body_known': ['eq', 1]}}]})
        allowed = choices(p.schema_for([row()], current, []))
        self.assertFalse(any(param == 'REVALIDATE_NOOP' and value == 1 for param, value, _ in allowed))
        self.assertTrue(any(param == 'REVALIDATE_NOOP' and value == 2 for param, value, _ in allowed))

    def test_protected_observations_rejected(self):
        r = dict(row(), origin='PROTECTED_B')
        with self.assertRaises(ValueError):
            p.schema_for([r], b.strategy(), [])
        with self.assertRaises(ValueError):
            p.request('echo', 0, b.strategy(), {'rows': [r]}, [])

    def test_target_lives_then_expires(self):
        current = b.strategy()
        target = event(current)
        history = [target]
        self.assertEqual(p.target_for(current, history), target)
        for i in range(1, 4):
            history.append(dict(id=i, base_sha256=b.sha(current), target_id=0, verdict='V3', A={'gain': 0}))
        self.assertIsNone(p.target_for(current, history))
        self.assertIsNone(p.target_for(b.strategy(program=target['proposal']), [target]))

    def test_target_before_accepted_program_no_B_or_global_indices(self):
        current = b.strategy()
        req = p.request('echo', 1, current, {'rows': [row(), row(), row()]}, [event(current)])
        self.assertEqual(req['type'], 'REFINE')
        self.assertEqual(req['target_parameter'], 'HOLD')
        for text in req['prompt_variants']:
            self.assertLess(text.index('REFINEMENT TARGET'), text.index('Accepted policy:'))
            self.assertNotIn('PRIVATE_SECRET', text)
            self.assertNotIn('case_index', text)
        bad = b.canonical({'patches': [{'set': {'REVALIDATE_NOOP': 1}, 'when': {'body_known': ['eq', 1]}}]})
        with self.assertRaisesRegex(ValueError, 'different control'):
            p.check_answer(bad, req)

    def test_expired_target_does_not_reenter_old_selector(self):
        current = b.strategy()
        history = [event(current)] + [dict(id=i, base_sha256=b.sha(current), target_id=0,
                    verdict='V3', A={'gain': 0}, type='REFINE') for i in (1, 2, 3)]
        req = p.request('echo', 4, current, {'rows': [row()]}, history)
        self.assertNotEqual(req['type'], 'REFINE')

    def test_random_draw_is_legal_and_reproducible(self):
        req = {'guard_schema': p.schema_for([row()], b.strategy(), [])}
        answer = p.random_answer(req, 41)
        self.assertEqual(answer, p.random_answer(req, 41))
        p.check_answer(answer, req)
        self.assertTrue(p.gbnf(req['guard_schema']).startswith('root ::= '))

    def test_duplicate_proposal_excluded(self):
        current, r = b.strategy(), row()
        schema = p.schema_for([r], current, [])
        answer = p.random_answer({'guard_schema': schema}, 19)
        proposal = json.loads(answer)
        updated = p.schema_for([r], current, [{'proposal': proposal}])
        with self.assertRaises(ValueError):
            p.check_answer(answer, {'guard_schema': updated})


def measurement(levels, score=1, digest='trace'):
    return dict(levels=levels, score=score, trace_digest=digest,
                rows=[{'levels_completed': levels, 'score': score}])


class VerifierAndCustody(unittest.TestCase):
    def test_complete_phase_and_independent_reconstruction_without_games(self):
        def req(arm, index, current, measured, history):
            return dict(id=index, type='GENERIC', prompt_variants=['synthetic unit fixture'],
                        guard_schema={'version': 11, 'origin': 'DEVELOPMENT_A', 'groups': [], 'excluded': []})
        def verify(measure, label, request, answer, current, a, protected):
            return current, a, protected, dict(verdict='V3', reason='unit fixture',
                         base_sha256=b.sha(current), A={'gain': 0}, target_id=None)
        response = {'answer': '{"patches":[]}', 'usage': {'input_tokens': 1, 'max_output_tokens': 160}}
        with tempfile.TemporaryDirectory() as tmp, mock.object(b, 'ROOT', Path(tmp)), \
                mock.object(b, 'integrity', return_value={}), \
                mock.object(b, 'measurement', return_value=lambda *a, **kw: measurement(365)), \
                mock.object(b.prompts, 'request', side_effect=req), \
                mock.object(b.model, 'propose', return_value=response), \
                mock.object(b.model, 'load', return_value=response), \
                mock.object(b, 'verify', side_effect=verify), mock.object(b, 'publish'), mock.object(b, 'status'):
            original = b.run_phase('pilot')
            self.assertEqual(len(original['verdicts']), 54)
            self.assertEqual(original['model_calls'], 36)
            self.assertFalse(original['promote'])
            b.atomic(Path(tmp) / 'pilot-process.json', {'pid': -1})
            audited = b.run_phase('pilot', audit=True)
            self.assertEqual(original, audited)
            self.assertTrue(json.loads((Path(tmp) / 'pilot-audit.json').read_text())['valid'])
            step = next((Path(tmp) / 'steps').rglob('*.json'))
            bad = json.loads(step.read_text())
            bad['event']['reason'] = 'tampered'
            b.atomic(step, bad)
            with self.assertRaisesRegex(RuntimeError, 'reconstruction differs'):
                b.run_phase('pilot', audit=True)

    def test_replay_failure_stops(self):
        def measure(label, policy, specs, observed=True, replay=False):
            return measurement(4, digest='other' if replay else 'first')
        with self.assertRaisesRegex(RuntimeError, 'determinism failure'):
            b.reproduced(measure, 'case', b.strategy(), b.A)

    def test_V3_retains_two_level_threshold(self):
        current = b.strategy()
        req = {'guard_schema': p.schema_for([row()], current, [])}
        answer = p.random_answer(req, 41)
        calls = []
        def measure(label, policy, specs, **kwargs):
            calls.append(specs)
            return measurement(379)
        with mock.object(b.evidence, 'comparison', return_value={}):
            value, a, protected, result = b.verify(measure, 'case', req, answer, current,
                                                 measurement(378), measurement(180))
        self.assertEqual(result['verdict'], 'V3')
        self.assertEqual(value, current)
        self.assertTrue(all(specs == b.A for specs in calls))

    def test_V4_score_loss_rejects_even_if_levels_retained(self):
        current = b.strategy()
        req = {'guard_schema': p.schema_for([row()], current, [])}
        def measure(label, policy, specs, **kwargs):
            if specs == b.B:
                self.assertFalse(kwargs['observed'])
                return measurement(180, score=0.5)
            return measurement(383)
        with mock.object(b.evidence, 'comparison', return_value={}):
            _, _, _, result = b.verify(measure, 'case', req, p.random_answer(req, 41), current,
                                       measurement(378), measurement(180))
        self.assertEqual(result['verdict'], 'V4')

    def test_unapproved_partition_never_plays(self):
        with mock.object(b, '_play') as play:
            with self.assertRaises(ValueError):
                b.play_one((b.strategy(), (2, 24920, 0, 2000), None))
            play.assert_not_called()

    def test_exam_is_gated_before_any_environment(self):
        with tempfile.TemporaryDirectory() as tmp, mock.object(b, 'ROOT', Path(tmp)), \
                mock.object(b, 'integrity', return_value={}):
            with self.assertRaises(FileNotFoundError):
                exam.run()
            self.assertFalse((Path(tmp) / 'exam/opened.json').exists())

    def test_final_criteria_not_relaxed(self):
        totals = {a: {'levels': n, 'score': 1} for a, n in
                  (('echo', 104), ('semilla', 100), ('fijo', 104), ('sinfiltro', 104))}
        dev = {a: {'levels': 10, 'score': 1} for a in ('echo', 'semilla')}
        result = s6_precise_exam.checks(totals, dev, True)
        self.assertFalse(result['B1'])
        self.assertFalse(result['B2'])
        self.assertFalse(result['B3'])
        self.assertTrue(result['B4'] and result['B5'])

    def test_transport_has_no_automatic_gpu_or_context_shift(self):
        cmd = m.command(Path('prompt'), Path('grammar'), 4)
        self.assertEqual(cmd[cmd.index('--device') + 1], 'none')
        self.assertIn('--no-kv-offload', cmd)
        self.assertIn('--no-context-shift', cmd)
        self.assertLess(m.MAX_INPUT + m.MAX_OUTPUT, m.CONTEXT)
        self.assertEqual(m.answer_text('{"patches":[]}\n[end of text]'), '{"patches":[]}')
        with self.assertRaises(ValueError):
            json.loads(m.answer_text('prose {"patches":[]}'))

    def test_existing_observer_renders_real_verdict(self):
        import observe
        result = observe.render(dict(kind='verdict', arm='echo', seed=1, id=0,
                    verdict='V3', A=b.difference(measurement(378), measurement(379))))
        self.assertTrue(any('378 → 379' in line for line in result))


if __name__ == '__main__':
    unittest.main()
