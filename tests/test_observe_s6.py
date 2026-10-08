"""Read-only display of paired requests, model receipts and measured outcomes."""
import json
from pathlib import Path
import tempfile
import unittest

from echoai import observe
from echo_arc.observe import Journal


class PairedDisplay(unittest.TestCase):
    def test_separate_batch_requests_and_answers_preserve_arm_and_actual_ids(self):
        request = {'kind': 'requests', 'requests': {
            'local-echo-7': [{'id': 2, 'type': 'MECHANISM_TRANSITION', 'prompt': 'observed contradiction'}],
            'local-fijo-7': [{'id': 2, 'type': 'GENERIC', 'prompt': 'three tasks'}]}}
        answer = {'kind': 'answers', 'answers': {'arms': {
            'local-echo-7': [{'id': 2, 'answer': '{"patches":[]}'}], 'local-fijo-7': []}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in (request, answer)) + '\n')
            before = path.read_bytes()
            rows = observe.Tail(path).read()
            requested, answered = ('\n'.join(observe.render(r)) for r in rows)
            self.assertIn('local-echo-7 · petición 3', requested)
            self.assertIn('local-fijo-7 · petición 3', requested)
            self.assertIn('observed contradiction', requested)
            self.assertIn('local-echo-7 · respuesta a petición 3', answered)
            self.assertNotIn('local-fijo-7', answered)
            self.assertNotIn('Petición registrada', answered)
            self.assertEqual(path.read_bytes(), before)

    def test_legacy_records_and_actual_new_verdict_metrics(self):
        old = {'kind': 'answers', 'requests': [{'id': 0, 'type': 'P1', 'prompt': 'old prompt'}],
               'answers': ['old answer']}
        self.assertIn('old answer', '\n'.join(observe.render(old)))
        new = {'kind': 'verdict', 'id': 1, 'arm': 'echo', 'seed': 7, 'verdict': 'V4',
               'A': {'before_levels': 10, 'after_levels': 12, 'gain': 2, 'loss_indices': []},
               'B': {'before_levels': 10, 'after_levels': 10, 'gain': 0, 'loss_indices': [3]}}
        text = '\n'.join(observe.render(new))
        self.assertIn('echo · 7 · V4', text)
        self.assertIn('10 → 12 niveles', text)
        self.assertIn('pérdidas 1', text)
        self.assertNotIn('no evaluado', text)

    def test_optional_mission_and_recorded_transition_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'arc-decisions.jsonl'
            journal = Journal(path)
            journal.write(kind='start', origin='DEVELOPMENT_A', agent='s6', budget=5)
            journal.write(kind='result', step=1, before={'hypotheses_count': 0},
                          after={'hypotheses_count': 0}, changed=False, game_over=False, level_up=False,
                          contradictory_noop=True, transition_revisions=[{'observations': 4}])
            journal.close()
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertNotIn('Misión', '\n'.join(observe.render(rows[0])))
            text = '\n'.join(observe.render(rows[1]))
            self.assertIn('Predicción contradicha', text)
            self.assertIn('Revisiones de transición registradas', text)
            rows[1]['contradictory_noop'] = False
            with self.assertRaisesRegex(ValueError, 'hash'):
                observe.render(rows[1])


if __name__ == '__main__':
    unittest.main()
