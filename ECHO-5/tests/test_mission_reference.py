"""Independent semantic fixtures and adversarial checks, written before the runner."""

from copy import deepcopy
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'src'))


def reference_module():
    # Give an assertion failure while the requested implementation is absent.
    try:
        return importlib.import_module('echo5.mission_reference')
    except ModuleNotFoundError as exc:
        if exc.name == 'echo5.mission_reference':
            raise AssertionError('The independent mission reference is not implemented') from exc
        raise


def native_available():
    try:
        return importlib.metadata.version('minigrid') == '3.0.0'
    except importlib.metadata.PackageNotFoundError:
        return False


class ReferenceTests(unittest.TestCase):
    def test_import_and_parser_checks_do_not_load_optional_packages(self):
        script = """
import importlib.abc, json, sys
sys.path.insert(0, sys.argv[1])
class RejectOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('minigrid', 'gymnasium', 'numpy', 'pygame'):
            raise AssertionError('optional import: ' + fullname)
sys.meta_path.insert(0, RejectOptional())
from echo5.mission_reference import run_benchmark
assert 'echo5.sandbox' not in sys.modules
report = run_benchmark(native=False)
assert report['parser']['passed'], report['parser']
assert not report['valid'] and not report['passed']
assert report['native']['status'] == 'not_requested'
print(json.dumps(report, allow_nan=False))
"""
        result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'src')],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['counters']['native_trajectories'], 0)

    def test_literal_expectations_cover_meaning_and_are_detached(self):
        ref = reference_module()
        cases = {row['id']: row for row in ref.reference_cases()}
        after = cases['after_doors']['expected']
        self.assertEqual(after, {'order': 'sequence', 'steps': [
            {'verb': 'open', 'target': {'type': 'door', 'color': 'red', 'location': None}},
            {'verb': 'open', 'target': {'type': 'door', 'color': 'blue', 'location': None}},
        ]})
        self.assertEqual(cases['and_doors']['expected']['order'], 'all')
        self.assertEqual(cases['putnext']['expected']['steps'][0]['reference'],
                         {'type': 'box', 'color': 'blue', 'location': None})
        locations = {desc['location'] for case in cases.values()
                     for step in case['expected']['steps']
                     for desc in (step['target'], step.get('reference', {})) if desc}
        self.assertTrue({None, 'left', 'right', 'front', 'behind'} <= locations)
        cases['after_doors']['expected']['steps'].clear()
        self.assertEqual(len(next(c for c in ref.reference_cases()
                                  if c['id'] == 'after_doors')['expected']['steps']), 2)

    def test_parser_suite_has_explicit_rejections_and_no_vacuous_full_pass(self):
        report = reference_module().run_benchmark(native=False)
        self.assertTrue(report['parser']['valid'], report['parser'])
        self.assertTrue(report['parser']['passed'], report['parser'])
        self.assertGreaterEqual(report['counters']['parser_cases'], 20)
        self.assertGreaterEqual(report['counters']['rejection_cases'], 10)
        self.assertEqual(report['counters']['parser_mismatches'], 0)
        self.assertFalse(report['valid'])
        self.assertFalse(report['instrument_valid'])
        self.assertFalse(report['semantic_pass'])
        self.assertFalse(report['passed'])
        json.dumps(report, allow_nan=False)

    def test_mutation_that_accepts_rejected_text_is_detected(self):
        ref = reference_module()
        from echo5 import sandbox
        original = sandbox.parse_mission

        def accept_pronoun(value):
            if value == 'pick up it':
                return original('pick up the red ball')
            return original(value)

        with patch.object(sandbox, 'parse_mission', accept_pronoun):
            report = ref.run_benchmark(native=False)
        self.assertFalse(report['parser']['passed'])
        self.assertGreater(report['counters']['rejection_failures'], 0)

    def test_missing_native_dependencies_are_invalid_not_success(self):
        ref = reference_module()
        with patch.object(ref, '_native_dependencies', return_value={
                'available': False, 'versions': {}, 'errors': ['test: missing minigrid']}):
            report = ref.run_benchmark()
        self.assertTrue(report['parser']['passed'])
        self.assertFalse(report['valid'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['native']['status'], 'unavailable')
        self.assertEqual(report['counters']['native_trajectories'], 0)

    def test_parser_exception_is_retained_as_diagnostic_data(self):
        ref = reference_module()
        from echo5 import sandbox
        original = sandbox.parse_mission

        def broken_parser(value):
            if value == 'pick up the red ball':
                raise RuntimeError('deliberate parser crash')
            return original(value)

        with patch.object(sandbox, 'parse_mission', broken_parser):
            report = ref.run_benchmark(native=False)
        row = next(row for row in report['cases'] if row['id'] == 'pickup')
        self.assertEqual(row['parser']['status'], 'error')
        self.assertEqual(row['parser']['error_type'], 'RuntimeError')
        self.assertIn('deliberate parser crash', row['parser']['error'])
        self.assertEqual(report['counters']['parser_errors'], 1)
        self.assertFalse(report['parser']['passed'])


@unittest.skipUnless(native_available(), 'native checks require ECHO-5/.venv-sandbox')
class NativeReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = reference_module()
        cls.report = cls.ref.run_benchmark()

    def case(self, name, report=None):
        return next(row for row in (report or self.report)['cases'] if row['id'] == name)

    def test_native_positive_negative_traces_and_evidence_agree(self):
        report = self.report
        self.assertTrue(report['valid'], report['native'])
        self.assertTrue(report['instrument_valid'])
        self.assertTrue(report['semantic_pass'])
        self.assertTrue(report['passed'], report['cases'])
        self.assertGreater(report['counters']['native_positive'], 0)
        self.assertGreater(report['counters']['native_negative'], 0)
        self.assertEqual(report['counters']['native_false_successes'], 0)
        self.assertEqual(report['counters']['reference_failures'], 0)
        for case in report['cases']:
            for row in case.get('trajectories', []):
                with self.subTest(case=case['id'], trajectory=row['id']):
                    self.assertEqual(row['reference']['success'], row['expected_success'])
                    self.assertEqual(row['candidate']['success'], row['expected_success'])
                    self.assertTrue(row['reference']['trace'])
                    self.assertLessEqual(len(row['reference']['trace']), len(row['actions']))
                    self.assertIn('state', row['reference']['trace'][-1])
                    self.assertIn('reward', row['reference']['trace'][-1])
        self.assertEqual(json.loads(json.dumps(report, allow_nan=False)), report)

    def test_and_allows_both_orders_but_after_does_not(self):
        after = {r['id']: r for r in self.case('after_doors')['trajectories']}
        conjunction = {r['id']: r for r in self.case('and_doors')['trajectories']}
        self.assertTrue(after['red_then_blue']['reference']['success'])
        self.assertFalse(after['blue_then_red']['reference']['success'])
        self.assertTrue(after['recover_order']['reference']['success'])
        self.assertTrue(conjunction['red_then_blue']['reference']['success'])
        self.assertTrue(conjunction['blue_then_red']['reference']['success'])
        self.assertFalse(conjunction['only_red']['reference']['success'])

    def test_ambiguity_preserves_all_referents_and_putnext_rejects_bad_worlds(self):
        case = self.case('ambiguous_ball')
        self.assertEqual(case['reference_binding']['target:0'], ['blue_ball', 'red_ball'])
        positive = [r for r in case['trajectories'] if r['expected_success']]
        self.assertEqual(len(positive), 2)
        for name, reason in [('missing_referent', 'no_match'),
                             ('putnext_overlap', 'overlap'),
                             ('putnext_already_adjacent', 'already_adjacent')]:
            row = self.case(name)
            self.assertEqual(row['reference_rejection'], reason)
            self.assertEqual(row['candidate_rejection'], reason)
            self.assertTrue(row['passed'])

    def test_shared_parser_mutations_produce_valid_negative_reports(self):
        from echo5 import sandbox, sandbox_eval
        original = sandbox.parse_mission

        def wrong_after(value):
            result = original(value)
            if ' after you ' in result['text']:
                result['steps'].reverse()
            return result

        def and_as_sequence(value):
            result = original(value)
            if result['order'] == 'all':
                result['order'] = 'sequence'
            return result

        def swap_locations(value):
            result = original(value)
            for step in result['steps']:
                for desc in (step['target'], step.get('reference', {})):
                    if desc.get('location') == 'left':
                        desc['location'] = 'right'
            return result

        def swap_putnext(value):
            result = original(value)
            for step in result['steps']:
                if step['verb'] == 'putnext':
                    step['target'], step['reference'] = step['reference'], step['target']
            return result

        for mutant, case_id in [(wrong_after, 'after_doors'), (and_as_sequence, 'and_doors'),
                                (swap_locations, 'left'), (swap_putnext, 'putnext')]:
            with self.subTest(mutation=mutant.__name__):
                # Both production consumers receive the same bug. The reference must not.
                with patch.object(sandbox, 'parse_mission', mutant), \
                        patch.object(sandbox_eval, 'parse_mission', mutant):
                    report = self.ref.run_benchmark()
                self.assertTrue(report['valid'], report['native'])
                self.assertTrue(report['instrument_valid'])
                self.assertFalse(report['semantic_pass'])
                self.assertFalse(report['passed'])
                self.assertGreater(report['counters']['parser_mismatches'], 0)
                self.assertGreater(report['counters']['native_disagreements'], 0)
                self.assertEqual(report['counters']['reference_failures'], 0)
                row = self.case(case_id, report)
                self.assertEqual(row['expected'], self.case(case_id)['expected'])
                self.assertEqual(row['reference_binding'], self.case(case_id)['reference_binding'])
                if mutant is not and_as_sequence:
                    self.assertGreater(report['counters']['native_false_successes'], 0)

    def test_custom_judge_mutation_is_detected_with_correct_parser(self):
        from echo5 import sandbox_eval
        original = sandbox_eval._native_instruction

        def ignore_order(mission):
            mission = deepcopy(mission)
            if mission['order'] == 'sequence':
                mission['order'] = 'all'
            return original(mission)

        with patch.object(sandbox_eval, '_native_instruction', ignore_order):
            report = self.ref.run_benchmark()
        self.assertTrue(report['valid'])
        self.assertTrue(report['parser']['passed'])
        self.assertFalse(report['passed'])
        self.assertGreater(report['counters']['native_false_successes'], 0)

    def test_reference_failure_invalidates_measurement(self):
        original = self.ref._reference_instruction
        from minigrid.envs.babyai.core import verifier as v

        def corrupt_reference(case):
            if case['id'] == 'after_doors':
                return v.AndInstr(v.OpenInstr(v.ObjDesc('door', 'red')),
                                  v.OpenInstr(v.ObjDesc('door', 'blue')))
            return original(case)

        with patch.object(self.ref, '_reference_instruction', corrupt_reference):
            report = self.ref.run_benchmark()
        self.assertFalse(report['valid'])
        self.assertFalse(report['passed'])
        self.assertGreater(report['counters']['reference_failures'], 0)

    def test_done_action_mode_cannot_silently_change_semantics(self):
        from minigrid.envs.babyai.core import verifier as v
        with patch.object(v, 'use_done_actions', True):
            report = self.ref.run_benchmark()
        self.assertFalse(report['valid'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['native']['status'], 'unavailable')
        self.assertIn('BABYAI_DONE_ACTIONS', ' '.join(report['native']['errors']))

    def test_parser_crash_is_semantic_failure_when_reference_executed_correctly(self):
        from echo5 import sandbox
        original = sandbox.parse_mission

        def broken_parser(value):
            if value == 'pick up the red ball':
                raise RuntimeError('deliberate parser crash')
            return original(value)

        with patch.object(sandbox, 'parse_mission', broken_parser):
            report = self.ref.run_benchmark()
        self.assertTrue(report['instrument_valid'], report['native'])
        self.assertTrue(report['valid'])
        self.assertFalse(report['semantic_pass'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['counters']['parser_errors'], 1)
        self.assertEqual(report['counters']['reference_failures'], 0)
        self.assertTrue(all(row['reference']['trace'] for row in
                            self.case('pickup', report)['trajectories']))

    def test_empty_corpus_cannot_be_valid(self):
        with patch.object(self.ref, 'reference_cases', return_value=[]):
            report = self.ref.run_benchmark()
        self.assertFalse(report['instrument_valid'])
        self.assertFalse(report['passed'])
        self.assertIn('empty', ' '.join(report['native']['errors']).lower())

    def test_native_engine_crash_is_an_instrument_error(self):
        with patch.object(self.ref, '_native_trial', side_effect=RuntimeError('engine crash')):
            report = self.ref.run_benchmark()
        self.assertFalse(report['instrument_valid'])
        self.assertFalse(report['passed'])
        self.assertGreater(report['counters']['instrument_errors'], 0)
        self.assertIn('engine crash', ' '.join(report['native']['errors']))

    def test_fresh_process_reports_replay_exactly_without_timing_exclusions(self):
        script = """
import json, sys
sys.path.insert(0, sys.argv[1])
from echo5.mission_reference import run_benchmark
print(json.dumps(run_benchmark(), sort_keys=True, allow_nan=False))
"""
        outputs = []
        for _ in range(2):
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'src')],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertTrue(json.loads(outputs[0])['instrument_valid'])
        self.assertEqual(outputs[0], outputs[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
