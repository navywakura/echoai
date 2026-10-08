import copy
import importlib.util
import json
import pickle
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock

from echo_arc import contrastive_evidence as e, contrastive_grammar as g, contrastive_requests as q
from seed import s6b11 as s


def features(**values):
    return {k: values.get(k, lo) for k, (lo, hi) in s.patch.FEATURES.items()}


def row(index=0, levels=2, score=2, action=1, **values):
    f = features(**values)
    return {'origin': 'DEVELOPMENT_A', 'version': 3, 'seed': index, 'rep': 0, 'budget': 2000,
            'game': 'PRIVATE_TASK', 'family': 'PRIVATE_FAMILY', 'levels_completed': levels, 'score': score,
            'actions': [['K', 1, None], ['K', action, None]], 'frames': ['frame0', 'frame1'],
            'actions_per_level': [5] * levels, 'resets': 0,
            'diagnostics': {'counts': {'contradictory_noop': 1},
                'contradiction_features': [{'features': f, 'count': 1}],
                'feature_counts': [{'features': f, 'count': 2}],
                'consumers': [{'parameter': 'HOLD', 'value': 40, 'features': f, 'count': 1}],
                'trajectory': {'features': list(e.FEATURE_ORDER), 'steps': [
                    {'f': [f[k] for k in e.FEATURE_ORDER], 'outcome': [False, False, False]},
                    {'f': [f[k] for k in e.FEATURE_ORDER], 'outcome': [True, False, False]}]}}}


def measure(rows):
    return {'rows': rows, 'levels': sum(r['levels_completed'] for r in rows),
            'score': sum(r['score'] for r in rows), 'trace_digest': s.sha(rows)}


class EvidenceTests(unittest.TestCase):
    def test_automatic_reset_is_not_fabricated_as_an_agent_decision(self):
        value = row()
        value['actions'] = [['K', 1, None], ['R', 0, None], ['R', 0, None]]
        value['automatic_reset_indices'], value['resets'] = [1], 1
        e.align_steps(value)
        self.assertTrue(e.step(value, 1)['automatic_reset'])
        self.assertNotIn('features', e.step(value, 1))
        self.assertIn('features', e.step(value, 2))

    def test_contrasts_preserve_both_signs_and_actual_first_divergence(self):
        before = [row(i) for i in range(4)]
        after = [row(0, score=1, action=2), row(1, score=1), row(2, levels=4, action=3), row(3)]
        c = e.comparison(measure(before), measure(after))
        self.assertEqual(c['losses'], 2)
        self.assertEqual(c['gains'], 1)
        self.assertEqual([x['case_index'] for x in c['contrasts']][:2], [0, 2])
        self.assertEqual(c['contrasts'][0]['first_different_action'], 1)
        self.assertEqual(c['contrasts'][0]['sequence'][-1]['candidate']['action']['key'], 2)
        history = [{'verdict': 'V4', 'A': {'gain': 2}, 'B': {'password': 'SECRET'},
                    'development': c, 'equivalent_calls': [0]}]
        text = json.dumps(e.feedback(history))
        for forbidden in ('SECRET', 'PRIVATE', 'case_index', 'frame0', 'password'):
            self.assertNotIn(forbidden, text)
        self.assertIn('protected_rejection', text)

    def test_protected_inputs_and_unpaired_games_rejected(self):
        a, b = row(), row()
        b['origin'] = 'PROTECTED_B'
        for function in (e.behavior_digest, g.witnesses):
            with self.assertRaises(ValueError):
                function([b])
        with self.assertRaises(ValueError):
            e.comparison(measure([a]), measure([b]))
        with self.assertRaises(ValueError):
            e.comparison(measure([a]), measure([row(1)]))

    def test_fingerprint_ignores_program_metadata_but_detects_actions_frames_and_efficiency(self):
        a = row()
        b = copy.deepcopy(a)
        b['policy_sha256'] = 'another-program'
        b['patch_hits'] = [9]
        self.assertEqual(e.behavior_digest([a]), e.behavior_digest([b]))
        for key, value in [('actions', [['K', 4, None]]), ('frames', ['another-frame']), ('score', 1.9)]:
            changed = dict(b, **{key: value})
            self.assertNotEqual(e.behavior_digest([a]), e.behavior_digest([changed]))

    def test_adaptive_evidence_changes_without_acceptance_and_fixed_does_not(self):
        rows = [row(i, levels=(i % 4) + 1, stagnation=i) for i in range(8)]
        echo0 = q.select(rows, 'echo', [], 0)[0]
        echo1 = q.select(rows, 'echo', [], 1)[0]
        self.assertNotEqual(echo0, echo1)
        self.assertEqual(q.select(rows, 'fijo', [], 0), q.select(rows, 'fijo', [], 1))
        history = [{'id': 0, 'type': 'CONTRADICTION', 'verdict': 'V3', 'A': {'gain': 2},
                    'development': {'contrasts': [{'case_index': 7}]}}]
        selected, focus = q.select(rows, 'echo', history, 2)
        self.assertEqual(focus, 'REFINE')
        self.assertEqual(selected[0], rows[7])
        trial = [{'id': 0, 'type': 'CONTRADICTION', 'verdict': 'V3', 'A': {'gain': 0}}]
        self.assertEqual(q.select(rows, 'echo', trial, 1)[1], 'WAIT')


class GrammarTests(unittest.TestCase):
    def test_control_read_witnesses_exclude_inert_waits_and_exact_repeats(self):
        observations = [row(hold_remaining=4)]
        guard = {'stagnation': ['ge', 0]}
        proposal = {'patches': [{'set': {'REVALIDATE_NOOP': 3}, 'when': guard}]}
        with mock.object(g, 'conditions', return_value=[guard, {'motor_ready': ['eq', 1]}]):
            schema = g.build_schema(observations, [{'proposal': proposal}])
        choices = {(p, v): guards for p, v, guards in g.choices(schema)}
        self.assertNotIn(('REVALIDATE_NOOP', 0), choices)
        self.assertNotIn(('REVALIDATE_NOOP', 3), choices)
        self.assertNotIn(('HOLD', 40), choices)
        self.assertIn(('COOLDOWN_CAP', 3), choices)
        self.assertNotIn(('COOLDOWN_CAP', 4), choices)
        with self.assertRaises(ValueError):
            g.validate_answer(json.dumps(proposal), schema)
        valid = {'patches': [{'set': {'REVALIDATE_NOOP': 4}, 'when': guard}]}
        self.assertEqual(g.validate_answer(json.dumps(valid), schema), valid)
        gram = g.Grammar(lambda text: list(map(ord, text)), 0, schema)
        output = g.canonical(valid)
        prefix = []
        for token in map(ord, output):
            self.assertIn(token, gram.allowed(prefix))
            prefix.append(token)
        self.assertIn(0, gram.allowed(prefix))

    def test_no_observations_requires_counted_abstention(self):
        schema = g.build_schema([], [])
        self.assertEqual(g.validate_answer('{"patches":[]}', schema), s.patch.EMPTY)
        with self.assertRaises(ValueError):
            g.validate_answer('{"patches":[{"set":{"HOLD":20},"when":{"level":["ge",1]}}]}', schema)

    def test_both_requests_sanitize_feedback_and_share_grammar(self):
        rows = [row(i) for i in range(3)]
        history = [{'id': 0, 'verdict': 'V4', 'reason': 'SECRET', 'B': {'seed': 24920}, 'A': {'gain': 0}}]
        with mock.object(g, 'conditions', return_value=[{'stagnation': ['ge', 0]}]):
            requests = [q.requests(arm, 1, 1, s.strategy(), measure(rows), history)[0] for arm in ('fijo', 'echo')]
        self.assertEqual(requests[0]['guard_schema'], requests[1]['guard_schema'])
        for request in requests:
            for secret in ('SECRET', '24920', 'PRIVATE_TASK', 'PRIVATE_FAMILY'):
                self.assertNotIn(secret, request['prompt'])


class ProtocolTests(unittest.TestCase):
    def test_promotion_requires_repeated_paired_advantage(self):
        def finals(echo):
            return [{'arm': arm, 'seed': i, 'A': value} for i, e in enumerate(echo)
                    for arm, value in [('fijo', 100), ('echo', e)]]
        self.assertFalse(s.promotion(finals([110, 100, 100]), 1, 'pilot')[0])
        self.assertFalse(s.promotion(finals([110, 110, 99]), 2, 'pilot')[0])
        self.assertFalse(s.promotion(finals([110, 110, 100]), 0, 'pilot')[0])
        self.assertTrue(s.promotion(finals([110, 110, 100]), 2, 'pilot')[0])
        self.assertFalse(s.promotion(finals([100]), 1, 'campaign')[0])

    def test_native_verifier_keeps_individual_protected_efficiency_gate(self):
        a = measure([row()])
        gained = measure([row(levels=4)])
        b = measure([dict(row(), origin='PROTECTED_B')])
        slower = measure([dict(row(score=1.999), origin='PROTECTED_B')])
        def measurement(label, *args, **kwargs):
            return slower if label.endswith(('/B', '/replay-B')) else gained
        # Diagnostic counts are supplied by the established result interface.
        with mock.object(s.capacity, 'result', side_effect=lambda before, after: {'gain': after['levels'] - before['levels']}):
            value, _, _, verdict = s.verifier(measurement)('x',
                '{"patches":[{"set":{"REVALIDATE_NOOP":4},"when":{"stagnation":["ge",16]}}]}',
                s.strategy(), a, b)
        self.assertEqual(verdict['verdict'], 'V4')
        self.assertEqual(value, s.strategy())
        self.assertEqual(verdict['development']['losses'], 0)

    def test_remote_bundle_is_self_contained_and_all_stages_private_cpu(self):
        generator = s.generator()
        compile(generator.template().replace('PAYLOAD', repr('e30=')), 'B11-wrapper', 'exec')
        self.assertIn('echo_arc/contrastive_grammar.py', generator.CODE)
        with tempfile.TemporaryDirectory() as directory:
            for path in generator.CODE:
                dest = Path(directory) / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((s.REPO / path).read_bytes())
            # A clean subprocess sees only the uploaded bundle, not this repo.
            import subprocess
            result = subprocess.run([__import__('sys').executable, '-c',
                'from echo_arc.contrastive_grammar import Grammar; print("bundle-ok")'],
                cwd=directory, env={'PATH': '/usr/bin:/bin'}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        for prefix in ('p', 'c'):
            for i in range(6):
                meta = generator.metadata(prefix + str(i))
                self.assertTrue(meta['is_private'])
                self.assertFalse(meta['enable_gpu'])
        pickle.dumps(s.play_one)
        from seed import s6b11_exam as exam
        pickle.dumps(exam.development_one)
        self.assertFalse({x[1] for x in s.A} & {x[1] for x in s.B})
        self.assertFalse({x[1] for x in s.A + s.B} & set(s.EXAM_SEEDS))
        self.assertEqual(s.config()['calls_including_calibration'], 100)

    def test_checkpoint_is_readable_after_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'checkpoint.json'
            s.atomic(target, {'state': 'first'})
            s.atomic(target, {'state': 'second'})
            self.assertEqual(json.loads(target.read_text()), {'state': 'second'})
            self.assertEqual(list(Path(directory).glob('*.tmp-*')), [])


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('arcengine'), 'managed ARC runtime')
class NativeTests(unittest.TestCase):
    def test_observer_preserves_baseline_and_active_repair(self):
        from echo_arc import agent, runner
        from echo_arc.observe import Journal
        from echo_arc.temporal_bench import _gym_env
        for program in (s.patch.EMPTY, {'patches': [{'set': {'REVALIDATE_NOOP': 3}, 'when': {'stagnation': ['ge', 8]}}]}):
            value = s.strategy(program)
            seed = runner.seed_for(_gym_env(3, 19).game_id, 0)
            agent._COMP_CACHE.clear()
            native = s.Execution.play(_gym_env(3, 19), 500, seed, value)
            with tempfile.TemporaryDirectory() as directory:
                recorder = e.Recorder(Journal(Path(directory) / 'arc-decisions.jsonl'),
                                      origin='DEVELOPMENT_A', program=program)
                agent._COMP_CACHE.clear()
                counted = s.old.accounting().ResetCounter(_gym_env(3, 19))
                try:
                    observed = s.Execution.play(counted, 500, seed, value, recorder)
                finally:
                    recorder.close()
                self.assertEqual(native, observed)
                observed.update(diagnostics=recorder.summary(), automatic_reset_indices=counted.automatic)
                e.align_steps(observed)
                trace = observed['diagnostics']['trajectory']
                self.assertEqual(len(trace['steps']), len(native['actions']))
                self.assertTrue(all(event is None or 'outcome' in event for event in trace['steps']))
                self.assertEqual(sum(event is None for event in trace['steps']), observed['resets'])


if __name__ == '__main__':
    unittest.main()
