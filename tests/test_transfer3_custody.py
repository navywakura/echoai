"""Preparation tests, not TRANSFER-3 acceptance."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from echoai.nexus0.transfer3.custody import (
    rehearsal, validate_notice, verify_reveal, verify_protocol,
)
from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, Sim3Error
from echoai.nexus0.sim3.seal import (
    REHEARSAL_SECRET, REHEARSAL_SALT, derive_seed, seal, open_once,
    read_seal, inventory_bytes,
)


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.notice = rehearsal()['public_notice']
        self.entries = [dict(split='C', index=i, package_sha256=sha256_bytes(
            canonical_bytes({'dummy_seed': derive_seed(REHEARSAL_SECRET, 'C', i)})))
            for i in range(2)]

    def test_rehearsal_is_not_a_certificate(self):
        result = rehearsal()
        self.assertTrue(result['rehearsal_ok'])
        for key in ('transfer3_green', 'campaign_created', 'campaign_C_opened'):
            self.assertFalse(result[key])
        self.assertEqual(result['dummy_states'], {'B': 'consumed', 'C': 'consumed'})

    def test_valid_reveal_order_independent(self):
        self.assertEqual(verify_reveal(self.notice, 'C', self.entries[::-1], REHEARSAL_SALT),
                         sha256_bytes(inventory_bytes(self.entries)))

    def test_wrong_salt(self):
        with self.assertRaises(ValueError):
            verify_reveal(self.notice, 'C', self.entries, bytes(32))

    def test_changed_commitment(self):
        self.notice['splits']['C']['inventory_commitment'] = '0'*64
        with self.assertRaises(ValueError):
            verify_reveal(self.notice, 'C', self.entries, REHEARSAL_SALT)

    def test_inventory_mutations(self):
        for key, value in [('package_sha256', '0'*64), ('split', 'B'),
                           ('index', True), ('index', -1), ('index', 2**32)]:
            with self.subTest(key=key, value=value):
                rows = copy.deepcopy(self.entries)
                rows[0][key] = value
                with self.assertRaises(ValueError):
                    verify_reveal(self.notice, 'C', rows, REHEARSAL_SALT)

    def test_missing_extra_duplicate_entries(self):
        for rows in (self.entries[:1], self.entries*2, [self.entries[0]]*2):
            with self.assertRaises(ValueError):
                verify_reveal(self.notice, 'C', rows, REHEARSAL_SALT)

    def test_notice_rejects_private_fields(self):
        for field in ('secret', 'salt', 'seeds', 'worlds'):
            notice = dict(self.notice, **{field: 'forbidden'})
            with self.assertRaises(ValueError):
                validate_notice(notice)

    def test_notice_bad_count_or_hash(self):
        for key, value in [('count', True), ('count', 0), ('count', 1.0),
                           ('inventory_commitment', 'G'*64)]:
            notice = copy.deepcopy(self.notice)
            notice['splits']['B'][key] = value
            with self.assertRaises(ValueError):
                validate_notice(notice)

    def test_protocol_and_secret_bound(self):
        protocol = canonical_bytes({'scope': 'custody-rehearsal-only', 'version': 1})
        verify_protocol(self.notice, protocol, REHEARSAL_SECRET)
        for raw, secret in ((protocol+b' ', REHEARSAL_SECRET), (protocol, bytes(32))):
            with self.assertRaises(ValueError):
                verify_protocol(self.notice, raw, secret)

    def test_failure_consumes_exam_and_concurrent_open_refused(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'dummy-C.json'
            seal(path, split='C', commitment=self.notice['splits']['C']['inventory_commitment'],
                 inventory_sha256=sha256_bytes(inventory_bytes(self.entries)),
                 custodian='test', n_packages=2)
            with self.assertRaisesRegex(RuntimeError, 'exam failed'):
                with open_once(path):
                    with self.assertRaises(Sim3Error) as caught:
                        with open_once(path):
                            self.fail('concurrent opening allowed')
                    self.assertEqual(caught.exception.code, 'seal_busy')
                    raise RuntimeError('exam failed')
            self.assertEqual(read_seal(path).state, 'consumed')
            with self.assertRaises(Sim3Error):
                with open_once(path):
                    self.fail('reopening allowed')


if __name__ == '__main__':
    unittest.main()
