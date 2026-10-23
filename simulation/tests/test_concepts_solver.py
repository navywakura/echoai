"""Independent expected outputs, poisoned labels, and measured counterexamples."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from echo5.budget import Budget
from echo5.concepts import Library, digest
from echo5.programs import execute
from echo5.solver import solve, verify_proposal
from echo5.trace import Recorder, verify_journal


ROT = {'steps': [{'op': 'rot90'}]}
DEMOS = [
    {'input': [[1, 2, 3], [4, 5, 6]], 'output': [[4, 1], [5, 2], [6, 3]]},
    {'input': [[7, 8], [0, 9], [1, 2]], 'output': [[1, 0, 7], [2, 9, 8]]},
]


class Poison(dict):
    def __getitem__(self, key):
        if key != 'input':
            raise AssertionError('query label accessed')
        return super().__getitem__(key)
    def get(self, key, *default):
        return self[key]
    def __iter__(self):
        raise AssertionError('query copied')
    def items(self):
        raise AssertionError('query serialized')
    def keys(self):
        raise AssertionError('query inspected')
    def values(self):
        raise AssertionError('query inspected')


def rotation_task():
    return {'train': deepcopy(DEMOS), 'test': [Poison(input=[[2, 7, 3], [5, 0, 8]])]}


class ConceptTests(unittest.TestCase):
    def acquire(self, lib):
        return lib.acquire('turn', ROT, DEMOS, budget=Budget(100000), provenance={'source': 'hand fixtures'})

    def test_independent_demonstrations_required_and_mismatch_cannot_be_learned(self):
        for demos in ([DEMOS[0]], [DEMOS[0], DEMOS[0]],
                      [DEMOS[0], {'input': DEMOS[1]['input'], 'output': [[9]]}]):
            lib = Library()
            with self.assertRaises(ValueError):
                lib.acquire('turn', ROT, demos, budget=Budget(100000), provenance={'source': 'test'})
            self.assertEqual(lib.state()['concepts'], [])

    def test_persistence_replays_evidence_and_detaches_mutable_state(self):
        lib = Library()
        self.acquire(lib)
        state = lib.state()
        restored = Library.restore(json.loads(json.dumps(state)), budget=Budget(500000))
        self.assertEqual(execute({'steps': [{'op': 'call', 'name': 'turn'}]}, [[1, 2]], library=restored, budget=Budget(100000)), ((1,), (2,)))
        state['concepts'][0]['program']['steps'][0]['op'] = 'identity'
        with self.assertRaises(ValueError):
            Library.restore(state, budget=Budget(500000))
        self.assertEqual(lib.resolve('turn', budget=Budget(100000)), ROT)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'concepts.json'
            lib.save(path)
            self.assertEqual(Library.load(path, budget=Budget(500000)).state(), lib.state())

    def test_named_composition_reuses_verified_concept(self):
        lib = Library()
        self.acquire(lib)
        program = {'steps': [{'op': 'call', 'name': 'turn'}, {'op': 'fliplr'}]}
        demos = [
            {'input': [[1, 2, 3], [4, 5, 6]], 'output': [[1, 4], [2, 5], [3, 6]]},
            {'input': [[7, 8], [0, 9], [1, 2]], 'output': [[7, 0, 1], [8, 9, 2]]},
        ]
        lib.acquire('transpose_via_turn', program, demos, budget=Budget(500000), provenance={'source': 'hand composed'})
        self.assertEqual(execute({'steps': [{'op': 'call', 'name': 'transpose_via_turn'}]}, [[1, 2]], library=lib, budget=Budget(200000)), ((1,), (2,)))

    def test_recomputed_hashes_do_not_certify_false_evidence(self):
        lib = Library()
        self.acquire(lib)
        state = lib.state()
        record = state['concepts'][0]
        record['program'] = {'steps': [{'op': 'identity'}]}
        record['expanded'] = deepcopy(record['program'])
        record['checksum'] = digest({k: v for k, v in record.items() if k != 'checksum'})
        state['checksum'] = digest({k: v for k, v in state.items() if k != 'checksum'})
        with self.assertRaises(ValueError):
            Library.restore(state, budget=Budget(500000))

    def test_counterexample_quarantines_dependent_programs(self):
        lib = Library()
        self.acquire(lib)
        lib.acquire('alias_turn', {'steps': [{'op': 'call', 'name': 'turn'}]}, DEMOS,
                    budget=Budget(500000), provenance={'source': 'independent verification'})
        lib.challenge('turn', [{'input': [[1, 2]], 'output': [[1, 2]]}],
                      budget=Budget(500000), provenance={'source': 'correction'})
        restored = Library.restore(lib.state(), budget=Budget(500000))
        self.assertEqual(restored.active_names(), ())
        with self.assertRaises(ValueError):
            execute({'steps': [{'op': 'call', 'name': 'alias_turn'}]}, [[1]], library=restored, budget=Budget(100000))

    def test_measured_counterexample_quarantines_and_survives_restore(self):
        lib = Library()
        self.acquire(lib)
        result = lib.challenge('turn', [{'input': [[1, 2]], 'output': [[1, 2]]}],
                               budget=Budget(100000), provenance={'source': 'external correction'})
        self.assertEqual(result['status'], 'quarantined')
        self.assertTrue(result['counterexamples'])
        restored = Library.restore(lib.state(), budget=Budget(500000))
        with self.assertRaises(ValueError):
            restored.resolve('turn', budget=Budget(100000))

    def test_truth_is_never_cached_and_support_is_reverified_each_task(self):
        lib = Library()
        self.acquire(lib)
        before = lib.state()
        for _ in range(2):
            result = solve(rotation_task(), budget=Budget(2_000_000), library=lib)
            self.assertEqual(result['status'], 'solved')
            self.assertGreater(result['metrics']['concepts_reverified'], 0)
            self.assertFalse(result['test_verified'])
        self.assertEqual(lib.state(), before)


class SolverTests(unittest.TestCase):
    def test_poison_labels_and_new_palette(self):
        result = solve(rotation_task(), budget=Budget(2_000_000))
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['predictions'], [[[5, 2], [0, 7], [8, 3]]])
        self.assertFalse(result['test_verified'])

    def test_consistent_programs_that_disagree_preserve_ambiguity(self):
        task = {'train': [{'input': [[1]], 'output': [[1]]}],
                'test': [Poison(input=[[1, 2], [3, 4]])],
                'proposals': [ROT, {'steps': [{'op': 'identity'}]}]}
        result = solve(task, budget=Budget(2_000_000))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['predictions'], [])
        self.assertGreater(result['metrics']['unique_predictions'], 1)

    def test_query_role_tie_does_not_become_a_verified_prediction(self):
        proposal = {'steps': [{'op': 'relate', 'role': 'largest', 'relation': 'all', 'effect': 'extract'}]}
        task = {'train': [{'input': [[0]*5, [0, 2, 0, 3, 0], [0, 2, 0, 0, 0], [0]*5], 'output': [[2], [2]]}],
                'test': [Poison(input=[[0]*5, [0, 4, 0, 5, 0], [0]*5])]}
        result = verify_proposal(proposal, task, budget=Budget(100000))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['predictions'], [])

    def test_proposal_authority_is_rejected_and_no_model_is_called(self):
        proposal = {**ROT, 'test_verified': True}
        result = verify_proposal(proposal, rotation_task(), budget=Budget(100000))
        self.assertEqual(result['status'], 'rejected')
        self.assertFalse(result['test_verified'])
        self.assertGreater(result['metrics']['used'], 0)

    def test_small_budget_abstains_with_exact_shared_cost(self):
        budget = Budget(100)
        result = solve(rotation_task(), budget=budget)
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertEqual(result['predictions'], [])
        self.assertEqual(result['metrics']['used'], budget.used)
        self.assertLessEqual(budget.used, budget.limit)

    def test_spatial_rule_transfers_beyond_same_row_and_v3(self):
        examples = []
        # Every expected edit is specified by the fixture, not an engine helper.
        for color, other, source, right, below in (
            (2, 4, (2, 3), (2, 8), (6, 3)),
            (7, 3, (3, 2), (1, 7), (6, 2)),
            (9, 6, (1, 3), (5, 9), (6, 3)),
        ):
            inp = [[0]*12 for _ in range(9)]
            y, x = source
            for yy, xx in ((y, x), (y+1, x), (y+1, x+1)):
                inp[yy][xx] = color
            inp[right[0]][right[1]] = other
            inp[below[0]][below[1]] = other
            out = deepcopy(inp)
            out[right[0]][right[1]] = color
            examples.append({'input': inp, 'output': out})
        task = {'train': examples[:2], 'test': [Poison(input=examples[2]['input'])]}
        result = solve(task, budget=Budget(2_000_000))
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['predictions'], [examples[2]['output']])
        old = solve(task, budget=Budget(2_000_000), relational=False)
        self.assertNotEqual(old['status'], 'solved')

    def test_invalid_proposals_are_rejected_without_influencing_search(self):
        task = rotation_task()
        task['proposals'] = [{**ROT, 'test_verified': True}]
        result = solve(task, budget=Budget(2_000_000))
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['metrics']['rejected_proposals'], 1)

    def test_empty_task_and_contradictory_demos_fail_without_predictions(self):
        self.assertEqual(solve({}, budget=10000)['status'], 'invalid_task')
        task = {'train': [{'input': [[1]], 'output': [[1]]}, {'input': [[1]], 'output': [[2]]}],
                'test': [Poison(input=[[3]])]}
        self.assertEqual(solve(task, budget=100000)['status'], 'invalid_task')

    def test_composed_transfer_and_equal_control_candidate_set(self):
        task = {
            'train': [
                {'input': [[0]*7, [0, 2, 0, 0, 4, 0, 0], [0, 2, 2, 0, 0, 0, 0], [0]*7], 'output': [[2, 2], [2, 0]]},
                {'input': [[0]*7, [0, 0, 0, 0, 3, 0, 0], [0, 7, 7, 0, 0, 0, 0], [0, 7, 0, 0, 0, 0, 0], [0]*7], 'output': [[7, 7], [0, 7]]},
            ],
            'test': [Poison(input=[[0]*8, [0, 0, 9, 9, 0, 0, 6, 0], [0, 0, 9, 0, 0, 0, 0, 0], [0]*8])],
        }
        cached = solve(task, budget=Budget(2_000_000), hierarchical=True)
        flat = solve(task, budget=Budget(2_000_000), hierarchical=False)
        self.assertEqual(cached['status'], 'solved')
        self.assertEqual(cached['predictions'], [[[9, 9], [0, 9]]])
        self.assertEqual(flat['predictions'], cached['predictions'])
        self.assertEqual(cached['metrics']['candidates'], flat['metrics']['candidates'])
        self.assertGreater(cached['metrics']['cache_hits'], 0)
        self.assertLess(cached['metrics']['used'], flat['metrics']['used'])

    def test_learning_stores_only_demonstrations_and_journal_is_passive(self):
        lib = Library()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'trace.jsonl'
            with Recorder(path) as journal:
                result = solve(rotation_task(), budget=Budget(2_000_000), library=lib, learn=True, journal=journal)
            self.assertEqual(result['status'], 'solved')
            self.assertGreater(verify_journal(path)['events'], 1)
        state = lib.state()
        self.assertTrue(state['concepts'])
        self.assertEqual(state['concepts'][0]['demonstrations'][0]['output'], DEMOS[0]['output'])
        self.assertNotIn('predictions', json.dumps(state))


if __name__ == '__main__':
    unittest.main()
