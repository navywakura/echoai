import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from seed import s6b11_recovery as r


class TransportTests(unittest.TestCase):
    def test_lossless_recovery_preserves_every_byte_and_declares_receipt(self):
        source = ('# Unicode: recuperación\nresult = "same literal \\n"\n' * 30).encode()
        code, receipt = r.pack(source, 'extension-profile')
        self.assertEqual(r.unpack(code), source)
        self.assertEqual(receipt['executed_source_sha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(receipt['executed_source_bytes'], len(source))

    def test_wrapper_executes_original_code_and_writes_provenance_before_it(self):
        source = b'answer = sum(range(10))\n'
        code, expected = r.pack(source, 'test-profile')
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'receipt.json'
            with patch('pathlib.Path', return_value=target):
                namespace = {'__name__': '__main__'}
                exec(code, namespace)
            self.assertEqual(namespace['answer'], 45)
            self.assertEqual(json.loads(target.read_text()), expected)

    def test_real_prepared_payload_is_compressed_without_prompt_or_seed_changes(self):
        path = r.s.BASE / 'p0/notebook/run.py'
        if not path.exists():
            self.skipTest('prepared initial wrapper unavailable')
        original = path.read_bytes()
        packed, receipt = r.pack(original, 'test-profile')
        self.assertEqual(r.unpack(packed), original)
        self.assertLess(len(packed.encode()), len(original) // 10)

    def test_audit_correlates_prepared_submitted_and_remotely_executed_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            folder = base / 'p0'
            (folder / 'notebook').mkdir(parents=True)
            source = b'answer = 1\n'
            (folder / 'notebook/run.py').write_bytes(source)
            meta = {'id': 'navywakura/echo45-s6b11-p0-20260929', 'is_private': True}
            r.s.atomic(folder / 'notebook/kernel-metadata.json', meta)
            r.s.atomic(folder / 'submission.json', {'ref': meta['id'], 'wrapper_sha256': r.digest(source)})
            with patch.object(r.s, 'BASE', base), patch.object(r, 'integrity', return_value={}), \
                 patch.object(r, 'native_generator', return_value=SimpleNamespace(metadata=lambda stage: meta)):
                packed_dir = r.package('p0')
                packed = (packed_dir / 'run.py').read_bytes()
                _, expected = r.pack(source, r.s.sha({}))
                submitted = {'submitted': True, 'ref': meta['id'], 'transport_wrapper_sha256': r.digest(packed),
                             'executed_source_sha256': r.digest(source)}
                r.s.atomic(folder / 'submitted.json', submitted)
                r.s.atomic(folder / 'transport/submitted.json', submitted)
                r.s.atomic(folder / 'output/transport-receipt.json', expected)
                self.assertTrue(r.audit_transport('p0')['valid'])
                r.s.atomic(folder / 'output/transport-receipt.json', dict(expected, executed_source_sha256='tampered'))
                with self.assertRaises(AssertionError):
                    r.audit_transport('p0')


if __name__ == '__main__':
    unittest.main()
