import unittest
from unittest.mock import patch
from echo5.search_diagnostics import diagnose, _Tap
from echo5.solver import solve


TASK = {'train': [{'input': [[1,2],[3,4]], 'output': [[4,3],[2,1]]},
                  {'input': [[5,6],[7,8]], 'output': [[8,7],[6,5]]}],
        'test': [{'input': [[1,5],[2,9]]}]}
WITNESS = {'steps': [{'op':'rot90'}, {'op':'rot90'}]}
CONFIG = {'max_depth': 2, 'beam_width': 4, 'max_candidates': 100,
          'grammar': {'geometry': ['rot90']}}


class SearchDiagnosticsTests(unittest.TestCase):
    def test_tracing_does_not_change_search_order_answer_or_cost(self):
        plain = solve(TASK, synthesis=CONFIG, cache_policy='interned')
        tap = _Tap(None)
        traced = solve(TASK, synthesis=CONFIG, cache_policy='interned', diagnostic=True, journal=tap)
        self.assertEqual(plain, traced)
        self.assertTrue(any(e['kind'] == 'synthesis_candidate' for e in tap.events))

    def test_known_composition_is_diagnosed_after_search(self):
        report = diagnose(TASK, WITNESS, synthesis=CONFIG)
        self.assertEqual(report['result']['status'], 'solved')
        self.assertEqual(report['prefixes'][0]['disposition'], 'retained')
        self.assertFalse(report['witness_passed_to_solver'])
        self.assertGreater(report['diagnostic_work']['used'], 0)

    def test_missing_operator_is_not_misreported_as_beam_failure(self):
        report = diagnose(TASK, WITNESS, synthesis={**CONFIG, 'grammar': {'geometry': ['identity']}})
        self.assertEqual(report['diagnosis'], 'witness_outside_search_alphabet')
        self.assertNotEqual(report['result']['status'], 'solved')

    def test_witness_cannot_change_search_and_query_truth_is_not_read(self):
        class Query(dict):
            def __getitem__(self, key):
                if key != 'input':
                    raise AssertionError('query truth read')
                return super().__getitem__(key)
        task = {**TASK, 'test': [Query(input=[[1,5],[2,9]], output='poison')]}
        a = diagnose(task, WITNESS, synthesis=CONFIG)
        b = diagnose(task, {'steps':[{'op':'identity'}]}, synthesis=CONFIG)
        self.assertEqual(a['result'], b['result'])
        self.assertEqual(a['trace'], b['trace'])
        self.assertEqual(b['diagnosis'], 'invalid_witness')

    def test_budget_failure_is_not_solution_impossibility(self):
        report = diagnose(TASK, WITNESS, synthesis=CONFIG, budget=1)
        self.assertEqual(report['diagnosis'], 'resource_limit_before_witness_path')

    def test_autopsy_locates_pruned_non_improving_witness_prefix(self):
        config = {**CONFIG, 'beam_width': 1, 'grammar': {'geometry': ['identity','rot90']}}
        report = diagnose(TASK, WITNESS, synthesis=config)
        self.assertEqual(report['diagnosis'], 'known_witness_prefix_pruned')
        self.assertEqual(report['prefixes'][0]['disposition'], 'beam_pruned')

    def test_fit_before_candidate_limit_is_not_called_unreached(self):
        task = {'train': [{'input': [[1,2],[3,4]], 'output': [[3,1],[4,2]]}],
                'test': [{'input': [[1,5],[2,9]]}]}
        report = diagnose(task, {'steps':[{'op':'rot90'}]}, synthesis={
            **CONFIG, 'grammar': {'geometry':['rot90','identity']}, 'max_candidates':1})
        self.assertEqual(report['prefixes'][0]['disposition'], 'demonstration_fit_reached')
        self.assertEqual(report['diagnosis'], 'resource_limit_before_tier_complete')

    def test_invalid_solver_result_invalidates_the_instrument(self):
        with patch('echo5.search_diagnostics.solve', return_value={
                'status':'invalid_search', 'metrics':{'used':1}, 'predictions':[]}):
            report=diagnose(TASK, WITNESS, synthesis=CONFIG)
        self.assertFalse(report['instrument_valid'])

    def test_undefined_query_is_not_evidence_of_competing_predictions(self):
        witness = {'steps':[{'op':'relate','role':'largest','relation':'all','effect':'extract'}]}
        task = {'train':[{'input':[[0]*5,[0,2,0,3,0],[0,2,0,0,0],[0]*5], 'output':[[2],[2]]}],
                'test':[{'input':[[0]*5,[0,4,0,5,0],[0]*5]}]}
        config = {**CONFIG, 'grammar':{'roles':['largest'], 'relations':['all'], 'effects':['extract']}}
        report=diagnose(task,witness,synthesis=config)
        self.assertEqual(report['result']['status'], 'ambiguous')
        self.assertEqual(report['diagnosis'], 'query_execution_undefined')
