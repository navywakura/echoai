"""Batch evaluation must not leak labels, hide failures or rescore guesses as proofs."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from seed import arc_v3_batch as batch


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'lab/seed/relational-v3-20261003/primary/candidate.json'
IDENTITY = {'train': [{'input': [[1, 0], [0, 2]], 'output': [[1, 0], [0, 2]]},
                     {'input': [[3, 0], [0, 4]], 'output': [[3, 0], [0, 4]]}],
            'test': [{'input': [[5, 0], [0, 6]], 'output': [[5, 0], [0, 6]]}]}


class Batch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.tasks = self.home / 'tasks'
        self.tasks.mkdir()
        (self.tasks / 'example.json').write_text(json.dumps(IDENTITY))
        self.run_dir = self.home / 'run'

    def prepare(self, **kw):
        return batch.prepare(self.tasks, CANDIDATE, self.run_dir,
                             label='synthetic-test', workers=1, **kw)

    def test_prepare_removes_test_labels_and_metadata_from_worker_input(self):
        value = copy.deepcopy(IDENTITY)
        value['answer_hint'] = 'do not send me'
        value['test'][0]['answer_hint'] = 'secret'
        (self.tasks / 'example.json').write_text(json.dumps(value))
        self.prepare()
        public = batch.read(self.run_dir / 'inputs/example.json')
        self.assertEqual(set(public), {'train', 'test'})
        self.assertEqual(public['test'], [{'input': [[5, 0], [0, 6]]}])
        self.assertEqual(batch.read(self.run_dir / 'labels/example.json'), [[[5, 0], [0, 6]]])

    def test_multiple_test_outputs_need_all_exact_for_task_success(self):
        score = batch.grade([[[1]], [[3]]], [[[1]], [[2]]])
        self.assertEqual(score, {'scored': True, 'exact_task': False,
                                 'exact_outputs': 1, 'test_outputs': 2, 'abstained_outputs': 0})

    def test_abstention_is_not_scored_as_submission_zero_fallback(self):
        score = batch.grade(None, [[[0]]], test_outputs=1)
        self.assertFalse(score['exact_task'])
        self.assertEqual(score['abstained_outputs'], 1)
        submission, meta = batch.submission({'example': {'predictions': None, 'test_outputs': 1}})
        self.assertEqual(submission, {'example': [{'attempt_1': [[0]], 'attempt_2': [[0]]}]})
        self.assertEqual(meta['fallback_outputs'], 1)
        self.assertEqual(meta['distinct_attempts_per_output'], 1)

    def test_unlabelled_challenges_are_unscored_not_zero_accuracy(self):
        challenge = self.home / 'challenges.json'
        value = copy.deepcopy(IDENTITY)
        del value['test'][0]['output']
        challenge.write_text(json.dumps({'example': value}))
        batch.prepare(challenge, CANDIDATE, self.run_dir, label='unlabelled')
        self.assertIsNone(batch.read(self.run_dir / 'labels/example.json'))
        self.assertIsNone(batch.grade([[[5]]], None, test_outputs=1)['exact_task'])

    def test_external_solution_count_must_match_test_inputs(self):
        solution = self.home / 'solutions.json'
        solution.write_text(json.dumps({'example': []}))
        with self.assertRaisesRegex(ValueError, 'solution'):
            self.prepare(solutions=solution)

    def test_duplicate_json_keys_and_unsafe_ids_are_rejected(self):
        bad = self.home / 'bad.json'
        bad.write_text('{"example": {}, "example": {}}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            batch.read(bad)
        bad.write_text(json.dumps({'../escape': IDENTITY}))
        with self.assertRaisesRegex(ValueError, 'task id'):
            batch.prepare(bad, CANDIDATE, self.run_dir, label='bad')

    def test_public_evaluation_waits_for_b24_closure_before_reading_tasks(self):
        with self.assertRaisesRegex(PermissionError, 'B24'):
            batch.prepare(self.home / 'not-opened', CANDIDATE, self.run_dir,
                          label='ARC-1 evaluation', scope='public-evaluation')
        self.assertFalse(self.run_dir.exists())

    def test_known_sealed_paths_are_rejected_as_development_even_via_symlink(self):
        from echoai.seed import gym
        linked = self.home / 'pretend-training'
        linked.symlink_to(gym.SEALED[0], target_is_directory=True)
        with self.assertRaises(PermissionError):
            batch.prepare(linked, CANDIDATE, self.run_dir, label='bad')

    def test_worker_rejects_label_bearing_input(self):
        with self.assertRaisesRegex(ValueError, 'label'):
            batch.solve_one(IDENTITY, CANDIDATE, budget=500000)

    def test_development_decisions_are_discovered_by_existing_observer(self):
        import observe
        self.run_dir = self.home/'lab/seed/batch-fixture'
        self.prepare()
        batch.run(self.run_dir)
        diaries = observe.discover(self.home)
        self.assertEqual(len(diaries), 1)
        events = [json.loads(line) for line in diaries[0].read_text().splitlines()]
        self.assertTrue(any(observe.render(event, False) for event in events))

    def test_fresh_process_prediction_and_resume_do_not_replay_completed_work(self):
        self.prepare()
        before = CANDIDATE.read_bytes()
        report = batch.run(self.run_dir)
        self.assertEqual(report['tasks_total'], 1)
        self.assertEqual(report['tasks_completed'], 1)
        self.assertEqual(report['exact_tasks'], 1)
        self.assertEqual(report['model_calls'], 0)
        result = self.run_dir / 'results/example.json'
        saved = result.read_bytes()
        stamp = result.stat().st_mtime_ns
        again = batch.run(self.run_dir)
        self.assertEqual(again['exact_tasks'], 1)
        self.assertEqual(result.read_bytes(), saved)
        self.assertEqual(result.stat().st_mtime_ns, stamp)
        self.assertEqual(CANDIDATE.read_bytes(), before)
        self.assertEqual(batch.read(self.run_dir/'inputs/example.json')['test'],
                         [{'input': [[5, 0], [0, 6]]}])

    def test_changed_labels_and_changed_receipts_block_resume(self):
        self.prepare()
        batch.run(self.run_dir)
        label = self.run_dir / 'labels/example.json'
        old = label.read_bytes()
        label.write_text('[[[9]]]')
        with self.assertRaisesRegex(ValueError, 'changed'):
            batch.run(self.run_dir)
        label.write_bytes(old)
        result = self.run_dir / 'results/example.json'
        receipt = batch.read(result)
        receipt['payload']['predictions'] = [[[9]]]
        result.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'receipt'):
            batch.run(self.run_dir)

    def test_timeout_is_recorded_and_kept_in_denominator(self):
        self.prepare(timeout=0.001)
        report = batch.run(self.run_dir)
        self.assertEqual(report['timeouts'], 1)
        self.assertEqual(report['scored_tasks'], 1)
        self.assertEqual(report['exact_tasks'], 0)
        self.assertFalse(report['instrument_clean'])
        self.assertEqual(batch.run(self.run_dir)['timeouts'], 1)

    def test_orphaned_started_task_is_accounted_without_a_free_retry(self):
        self.prepare()
        batch.save(self.run_dir/'started/example.json', {'at': 'interrupted-fixture'})
        report = batch.run(self.run_dir)
        self.assertEqual(report['interrupted'], 1)
        self.assertEqual(report['scored_tasks'], 1)
        self.assertEqual(report['tasks_with_unknown_work'], 1)
        self.assertFalse((self.run_dir/'requests/example.json').exists())
        self.assertFalse(report['instrument_clean'])

    def test_external_labels_never_become_embedded_worker_labels(self):
        value = copy.deepcopy(IDENTITY)
        del value['test'][0]['output']
        challenge = self.home/'challenge.json'
        solution = self.home/'solutions.json'
        challenge.write_text(json.dumps({'example': value}))
        solution.write_text(json.dumps({'example': [[[5, 0], [0, 6]]]}))
        batch.prepare(challenge, CANDIDATE, self.run_dir, label='test', solutions=solution)
        report = batch.run(self.run_dir)
        self.assertEqual(report['exact_tasks'], 1)
        request = batch.read(self.run_dir/'requests/example.json')
        self.assertEqual(request['public']['test'], [{'input': [[5, 0], [0, 6]]}])
        self.assertNotIn('solutions', request)
        self.assertNotIn('labels', request)

    def test_invalid_grids_are_rejected_before_worker(self):
        for bad in ([[True]], [[10]], [[1], [2, 3]], [], [[0]*31]):
            with self.subTest(grid=bad), self.assertRaises(ValueError):
                batch.arc_grid(bad)

    def test_recorder_change_invalidates_a_development_batch(self):
        self.prepare()
        original = batch.file_sha
        def changed(path):
            return 'f'*64 if str(path).endswith('echo_arc/observe.py') else original(path)
        with patch.object(batch, 'file_sha', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                batch.integrity(self.run_dir)

    def test_final_integrity_failure_never_publishes_clean_complete(self):
        self.prepare()
        original = batch.integrity
        calls = []
        def validate(path):
            calls.append(path)
            if len(calls) > 1:
                raise ValueError('simulated final integrity failure')
            return original(path)
        with patch.object(batch, 'integrity', side_effect=validate):
            with self.assertRaisesRegex(ValueError, 'final integrity failure'):
                batch.run(self.run_dir)
        self.assertNotEqual(batch.read(self.run_dir/'status.json')['stage'], 'COMPLETE')
        self.assertFalse(batch.read(self.run_dir/'report.json')['instrument_clean'])
        self.assertFalse((self.run_dir/'submission.json').exists())

    def test_unrelated_three_field_receipt_cannot_open_public_evaluation(self):
        receipt = self.home/'unrelated.json'
        receipt.write_text(json.dumps({'condition': 'NOT-B24', 'valid': True,
                                       'result': 'DIAGNOSTIC_COMPLETE', 'exam_opened': False}))
        with self.assertRaisesRegex(PermissionError, 'B24'):
            batch.prepare(self.home/'not-opened', CANDIDATE, self.run_dir,
                          label='evaluation', scope='public-evaluation', b24_closure=receipt)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux worker lifecycle contract')
    def test_cancellation_stops_active_worker_without_starting_queued_tasks(self):
        self._interrupt(signal.SIGINT)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux parent-death contract')
    def test_worker_dies_even_when_parent_is_killed_without_cleanup(self):
        self._interrupt(signal.SIGKILL)

    def _interrupt(self, sig):
        for tid in ('second', 'third'):
            (self.tasks/(tid+'.json')).write_text(json.dumps(IDENTITY))
        self.prepare(timeout=1)
        children = self.home/'children'
        child = ("import os,time;from pathlib import Path;from seed import arc_v3_batch as b;"
                 "getattr(b,'_worker_guard',lambda:None)();"
                 f"f=Path({str(children)!r}).open('a');f.write(str(os.getpid())+'\\n');f.close();"
                 "time.sleep(4)")
        script = self.home/'interrupt_fixture.py'
        script.write_text(
            f"import sys;sys.path.insert(0,{str(ROOT)!r})\n"
            "from pathlib import Path\nfrom seed import arc_v3_batch as b\n"
            "original=b.subprocess.Popen\n"
            f"def slow(cmd,**kw):return original([sys.executable,'-c',{child!r}],**kw)\n"
            "b.subprocess.Popen=slow\n"
            f"b.run(Path({str(self.run_dir)!r}))\n")
        with (self.home/'parent.log').open('w') as log:
            proc = subprocess.Popen([sys.executable, str(script)], cwd=ROOT, stdout=log, stderr=log)
            try:
                deadline=time.monotonic()+5
                while not children.exists() and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(children.exists(), 'controlled worker did not start')
                pid=int(children.read_text().splitlines()[0])
                proc.send_signal(sig)
                proc.wait(timeout=1)
                deadline=time.monotonic()+.5
                while self._alive(pid) and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertFalse(self._alive(pid), 'worker survived cancelled/dead parent')
                self.assertEqual(len(list((self.run_dir/'started').glob('*.json'))), 1)
            finally:
                if proc.poll() is None:
                    proc.kill();proc.wait(timeout=2)
                if children.exists():
                    for value in children.read_text().splitlines():
                        try:os.kill(int(value),signal.SIGKILL)
                        except ProcessLookupError:pass

    @staticmethod
    def _alive(pid):
        try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
        except FileNotFoundError:return False


if __name__ == '__main__':
    unittest.main()
