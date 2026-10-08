import copy
import json
from pathlib import Path
import tempfile
import unittest

from seed import arc_capabilities as cap, arc_comparison as c
from echoai.seed import dsl, refinement
from echo_arc.observe import Journal
import observe


class ForbiddenOutput:
    def __deepcopy__(self, memo):
        raise AssertionError('test output reached solver')


class CapabilityTests(unittest.TestCase):
    def test_generator_is_reproducible_and_case_ids_unique(self):
        tasks = cap.suite()
        self.assertEqual(tasks, cap.suite())
        self.assertEqual(len(tasks), 12)
        self.assertEqual(len({t['id'] for t in tasks}), 12)
        self.assertTrue(all(t['origin'] == 'SYNTHETIC_DEVELOPMENT' for t in tasks))

    def test_independent_generator_oracle_matches_known_dsl_programs(self):
        dsl.enable_s2v()
        library = refinement.RefinementLibrary()
        programs = {'objects': [('crop_largest_any',)],
                    'composition': [('crop_largest_any',), ('rot90',)],
                    'marker_relation': [('marker_recolor', 0)], 'size_relation': [('objects_to_row', 0)]}
        for task in cap.suite():
            for sample in task['task']['train'] + task['task']['test']:
                got = refinement.execute(refinement.grid(sample['input']), programs[task['capabilities'][0]], library)
                self.assertEqual(got, refinement.grid(sample['output']), task['id'])

    def test_solver_never_receives_test_outputs_and_judge_requires_every_test(self):
        task = copy.deepcopy(cap.suite()[0]['task'])
        for p in task['test']:
            p['output'] = ForbiddenOutput()
        public = c.solver_input(task)
        self.assertTrue(all(set(p) == {'input'} for p in public['test']))
        real = cap.suite()[0]['task']
        result = {'program': [('crop_largest_any',)], 'predictions': [p['output'] for p in real['test']]}
        self.assertTrue(c.judge(real, result))
        result['predictions'] = result['predictions'][:1]
        self.assertFalse(c.judge(real, result))

    def test_flat_ablation_cannot_import_a_composed_learned_macro(self):
        state = {'concepts': {'two': {'steps': [('rot90',), ('crop',)]}}, 'prior': {}}
        flat = cap.library_for('without_composition', state)
        full = cap.library_for('full', state)
        self.assertNotIn('two', flat.moves({0, 1}, {0, 1}))
        self.assertIn('two', full.moves({0, 1}, {0, 1}))
        self.assertTrue(all(len(flat.expand(m)) <= 1 for m in flat.moves({0, 1}, {0, 1})))

    def test_without_relations_removes_only_added_relational_moves(self):
        state = {'concepts': {}, 'prior': {}}
        full = set(cap.library_for('full', state).moves({0, 1}, {0, 1}))
        without = set(cap.library_for('without_relations', state).moves({0, 1}, {0, 1}))
        self.assertTrue(without < full)
        self.assertEqual({m[0] for m in full - without},
                         {'objects_to_row', 'marker_recolor', 'recolor_by_size', 'connect_color'})

    def test_partial_diagnostic_cannot_be_reported_as_complete(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            cap.compare([])

    def test_existing_journal_renders_actual_refinement_without_fake_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'arc-decisions.jsonl'
            journal = Journal(path)
            journal.write(kind='verified_hypothesis', program=[['rot90']], demonstrations=3, test_verified=False)
            journal.write(kind='refinement_round', iteration=1, trials=20, verified=1, best_errors=[])
            journal.write(kind='refinement_result', status='AMBIGUOUS', trials=20, prediction_groups=2)
            journal.close()
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            text = '\n'.join(line for row in rows for line in observe.render(row))
            self.assertIn('sin verificar', text)
            self.assertIn('AMBIGUOUS', text)
            rows[0]['demonstrations'] = 999
            with self.assertRaisesRegex(ValueError, 'hash'):
                observe.render(rows[0])


if __name__ == '__main__':
    unittest.main()
