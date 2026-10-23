"""R1 rejects changed results and duplicate submissions; never relaxes B12 gates."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from seed import s6b12_recovery1 as r


def partial_fixture():
    return {'complete': False, 'requests_sha256': 'requests', 'profile': {'revision': 'pinned'},
        'calibration': [], 'arms': {
            'local-fijo-705001': [{'id': i, 'answer': 'unchanged', 'usage': {'prompt_tokens': 4646}} for i in range(10, 15)],
            'local-echo-705001': [{'id': i, 'answer': 'unchanged', 'usage': {'prompt_tokens': 3105}} for i in range(10, 12)]}}


def completed_fixture(partial):
    result = copy.deepcopy(partial)
    result['complete'] = True
    result['arms']['local-echo-705001'].extend({'id': i, 'answer': 'remaining'} for i in range(12, 15))
    return result


class PrefixTests(unittest.TestCase):
    def test_exact_prefix_is_required_and_counted(self):
        partial = partial_fixture()
        completed = completed_fixture(partial)
        receipt = r.ensure_prefix_replay(partial, completed)
        self.assertEqual(receipt['exact_saved_answers_reproduced'], 7)
        self.assertEqual(partial['complete'], False)
        self.assertEqual(len(partial['arms']['local-echo-705001']), 2)

    def test_changed_answer_or_usage_cannot_replace_saved_answer(self):
        partial = partial_fixture()
        for key, value in [('answer', 'a more successful proposal'), ('usage', {'prompt_tokens': 5999})]:
            with self.subTest(key=key):
                completed = completed_fixture(partial)
                completed['arms']['local-fijo-705001'][0][key] = value
                with self.assertRaisesRegex(AssertionError, 'saved answer changed'):
                    r.ensure_prefix_replay(partial, completed)

    def test_changed_runtime_or_requests_cannot_pass(self):
        partial = partial_fixture()
        for key in ('profile', 'requests_sha256', 'calibration'):
            with self.subTest(key=key):
                completed = completed_fixture(partial)
                completed[key] = 'different'
                with self.assertRaisesRegex(AssertionError, 'provenance differs'):
                    r.ensure_prefix_replay(partial, completed)

    def test_incomplete_or_short_replay_is_rejected(self):
        partial = partial_fixture()
        completed = completed_fixture(partial)
        completed['arms']['local-fijo-705001'].pop()
        with self.assertRaises(AssertionError):
            r.ensure_prefix_replay(partial, completed)
        with self.assertRaises(AssertionError):
            r.ensure_prefix_replay(partial, copy.deepcopy(partial))


class ContinuationTests(unittest.TestCase):
    def test_original_c2_source_matches_frozen_payload_and_rejects_changes(self):
        payload = json.loads((r.s.BASE / 'c2/payload.json').read_text())
        source = (r.s.BASE / 'c2/notebook/run.py').read_bytes()
        r.check_source(source, payload)
        with self.assertRaisesRegex(AssertionError, 'inference source differs'):
            r.check_source(source + b'\nprint("altered inference")\n', payload)
        payload['model']['temperature'] = 0.9
        with self.assertRaisesRegex(AssertionError, 'embedded payload differs'):
            r.check_source(source, payload)

    def test_failed_recovery_job_is_never_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'c2').mkdir()
            (base / 'c2/terminal.json').write_text(json.dumps({'status': 'CANCEL_ACKNOWLEDGED'}))
            with patch.object(r, 'BASE', base), patch.object(r, 'integrity', return_value={}), \
                 patch.object(r, 'build_job') as build, patch.object(r, 'transport') as send:
                with self.assertRaisesRegex(AssertionError, 'no second inference retry'):
                    r.propose('c2', {}, {})
                build.assert_not_called()
                send.assert_not_called()

    def test_completed_job_is_audited_without_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'c2').mkdir()
            (base / 'c2/terminal.json').write_text(json.dumps({'status': 'COMPLETE'}))
            with patch.object(r, 'BASE', base), patch.object(r, 'integrity', return_value={}), \
                 patch.object(r, 'audit_model', return_value={'checked': True}) as audit, \
                 patch.object(r, 'transport') as send:
                self.assertEqual(r.propose('c2', {'requests': 'same'}, {}), {'checked': True})
                audit.assert_called_once_with('c2', {'requests': 'same'})
                send.assert_not_called()

    def test_old_stages_retain_original_audit(self):
        with patch.object(r, 'original_audit', return_value={'original': True}) as audit:
            for stage in ('p0', 'p5', 'c0', 'c1'):
                self.assertEqual(r.audit_model(stage), {'original': True})
            self.assertEqual(audit.call_count, 4)

    def test_resume_requires_exact_original_payload_before_building_remote_job(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old = base / 'old'
            (old / 'c2').mkdir(parents=True)
            (old / 'c2/payload.json').write_text(json.dumps({'original': True}))
            with patch.object(r, 'BASE', base / 'new'), patch.object(r.s, 'BASE', old), \
                 patch.object(r, 'integrity', return_value={}), \
                 patch.object(r, 'payload_for', return_value={'original': False}):
                with self.assertRaises(AssertionError):
                    r.build_job('c2', {}, {})
            self.assertFalse((base / 'new/c2/notebook/run.py').exists())

    def test_new_metadata_is_private_cpu_and_scoped(self):
        spec = importlib.util.spec_from_file_location('_r1_transport_test',
            r.s.BASE / 'recovery_transport1.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for stage in r.STAGES:
            meta = r.metadata(stage)
            module.validate_metadata(meta)
            self.assertFalse(meta['enable_gpu'])
            self.assertTrue(meta['is_private'])
        for ref in ('navywakura/echo45-s6b12-c2-20260930',
                    'navywakura/echo45-s6b12-r1-c6-20260930'):
            self.assertFalse(module.valid_ref(ref))

    def test_ambiguous_absent_upload_cannot_be_sent_again(self):
        spec = importlib.util.spec_from_file_location('_r1_transport_test2',
            r.s.BASE / 'recovery_transport1.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            packed = base / 'c2/packed/notebook'
            packed.mkdir(parents=True)
            code = b'print("test")\n'
            code_hash = r.digest(code)
            meta = r.metadata('c2')
            (packed / 'run.py').write_bytes(code)
            (packed / 'kernel-metadata.json').write_text(json.dumps(meta))
            receipt = {'submitted_wrapper_sha256': code_hash, 'ref': meta['id']}
            (packed.parent / 'package.json').write_text(json.dumps(receipt))
            (packed.parent / 'intent.json').write_text(json.dumps(receipt))
            api = Mock()
            with patch.object(module, 'BASE', base), patch.object(module, 'check_sources'), \
                 patch.object(module, 'inventory', return_value=[]):
                with self.assertRaisesRegex(AssertionError, 'never resubmit'):
                    module.push(api, packed)
            api.kernels_push.assert_not_called()


if __name__ == '__main__':
    unittest.main()
