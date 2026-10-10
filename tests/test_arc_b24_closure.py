"""Synthetic local B24 custody only: no runner, models, datasets or games."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from seed.arc_b24_closure import validate


def encoded(value):
    return (json.dumps(value, sort_keys=True) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def profile_digest(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


class CustodyFixture:
    """Small fixtures with the manager/exporter schemas, including original R1 totals."""

    def __init__(self, directory, recovery=False):
        self.directory = directory
        self.prefix = 'b24-r1-results' if recovery else 'b24-results'
        self.inputs = {'models.json': {'N7': {'fixture': True}},
                       'baseline.json': {'policy': {'fixture': True}},
                       'parent-closure.json': {'condition': 'S6-B24'}}
        if recovery:
            self.inputs['recovery.json'] = {
                'parent': {'charged_format_calls': 6},
                'limits': {'prior_format_calls': 6, 'current_format_calls': 8}}
        self.manifest = {
            'configuration': {'condition': 'S6-B24', 'exam_allowed': False,
                              'max_games': 8310,
                              'model': {'transport_revision': 'B24-R1'} if recovery else {}},
            'execution_root': '/kaggle/working/' + self.prefix,
            # R1 must use its archived source hashes, not current workspace hashes.
            'sources': {'seed/s6b24.py': digest(b'R1 source' if recovery else b'original source')},
            'inputs': {name: digest(encoded(value)) for name, value in self.inputs.items()},
            'python': '3.12.13', 'numpy': '2.3.2', 'arcengine': '0.9.3',
            'contract_sha256': digest(b'synthetic contract'),
            'tests_sha256': digest(b'synthetic tests'), 'test_sources': {}}
        self.profile = profile_digest(self.manifest)
        self.closed = {
            'valid': True, 'at': '2026-10-09T00:00:00+00:00', 's6_green': False,
            'exam_opened': False, 'transfer': {}, 'physical_games': 3, 'model_calls': 2,
            'format_calls': 8, 'total_model_calls': 10, 'result': 'DIAGNOSTIC_COMPLETE',
            'confirmation': 'NOT_RUN', 'campaign': 'NOT_RUN',
            'promotion': 'a later SEMILLA contract is required'}
        if recovery:
            self.closed.update(prior_format_calls=6, current_profile_format_calls=8,
                               format_calls=14, current_profile_total_model_calls=10,
                               total_model_calls=16,
                               recovery_sha256=digest(encoded(self.inputs['recovery.json'])))
        self.audit = {'valid': True, 'profile_sha256': self.profile,
                      'completed_games': 3, 'logical_attempts': 1, 'measurements': 3,
                      'model_calls': 2, 'exam_opened': False, 's6_green': False,
                      'slot_wall_seconds': 0.1, 'parent_cpu_seconds': 0.1,
                      'checkpoint_segments': 0}
        self.preflight = {'valid': True, 'profile_sha256': self.profile,
                          'model_calls': 8, 'cases_sha256': digest(b'synthetic cases')}
        self.path = directory / 'b24-closed.json'

    def write(self, *, members=None, extra_members=(), status_changes=None):
        status = dict(self.closed, condition='S6-B24', stage='CLOSED')
        status.update(status_changes or {})
        exported = {'closed.json': encoded(self.closed),
                    'arithmetic-review.json': encoded(self.audit),
                    'status.json': encoded(status), 'micro.json': encoded({'winners': {}}),
                    'transfer.json': encoded(self.closed['transfer'])}
        archive_files = dict(exported)
        archive_files.update({'input/' + name: encoded(value) for name, value in self.inputs.items()})
        archive_files['input/manifest.json'] = encoded(self.manifest)
        archive_files['format-preflight/receipt.json'] = encoded(self.preflight)
        # This must never be parsed as a game or replayed by the validator.
        archive_files['v-new/protected-fixture.bin'] = b'not a JSON game; do not inspect'
        archive_files.update(members or {})
        archive = self.directory / 'b24-evidence.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            for name, raw in archive_files.items():
                if raw is None:
                    continue
                item = tarfile.TarInfo(self.prefix + '/' + name)
                item.size = len(raw)
                stream.addfile(item, io.BytesIO(raw))
            for item, raw in extra_members:
                stream.addfile(item, io.BytesIO(raw))
        for name, raw in exported.items():
            (self.directory / ('b24-' + name)).write_bytes(raw)
        (self.directory / 'b24-models.json').write_bytes(encoded(self.inputs['models.json']))
        (self.directory / 'b24-native.tar.gz').write_bytes(b'synthetic native artifact; hash only')
        files = {p.name: digest(p.read_bytes()) for p in self.directory.iterdir()
                 if p.is_file() and p.name != 'collection.json'}
        (self.directory / 'collection.json').write_bytes(encoded({'version': 1, 'files': files}))


class B24Closure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.fixture = CustodyFixture(self.directory)
        self.fixture.write()

    def denied(self):
        with self.assertRaisesRegex(PermissionError, '^B24'):
            validate(self.fixture.path)

    def test_original_receipt_without_condition_has_bound_serializable_provenance(self):
        self.assertNotIn('condition', self.fixture.closed)
        result = validate(self.fixture.path)
        self.assertEqual(result['condition'], 'S6-B24')
        self.assertEqual(result['profile_sha256'], self.fixture.profile)
        self.assertEqual(result['archive_root'], 'b24-results')
        self.assertEqual(result['receipt'], self.fixture.closed)
        self.assertEqual(result['sha256'], digest(self.fixture.path.read_bytes()))
        self.assertEqual(result['collection_sha256'], digest((self.directory / 'collection.json').read_bytes()))
        self.assertEqual(json.loads(json.dumps(result, allow_nan=False)), result)

    def test_r1_archive_and_cumulative_accounting_are_accepted(self):
        self.fixture = CustodyFixture(self.directory, recovery=True)
        self.fixture.write()
        result = validate(self.fixture.path)
        self.assertEqual(result['archive_root'], 'b24-r1-results')
        self.assertEqual(result['profile_sha256'], self.fixture.profile)
        self.assertEqual(result['receipt']['total_model_calls'], 16)

    def test_tampered_collected_files_are_rejected(self):
        for name in ('b24-closed.json', 'b24-arithmetic-review.json', 'b24-evidence.tar.gz',
                     'b24-status.json', 'b24-native.tar.gz', 'b24-models.json'):
            with self.subTest(name=name):
                self.fixture.write()
                with (self.directory / name).open('ab') as stream:
                    stream.write(b' ')
                self.denied()

    def test_unrelated_manifest_is_rejected_even_with_valid_collection_hashes(self):
        self.fixture.manifest['configuration']['condition'] = 'S6-B23'
        self.fixture.audit['profile_sha256'] = profile_digest(self.fixture.manifest)
        self.fixture.write()
        self.denied()

    def test_wrong_audit_profile_is_rejected(self):
        self.fixture.audit['profile_sha256'] = '0' * 64
        self.fixture.write()
        self.denied()

    def test_archive_receipts_must_be_identical_to_collected_copies(self):
        for name in ('closed.json', 'arithmetic-review.json', 'status.json', 'micro.json',
                     'transfer.json', 'input/models.json'):
            with self.subTest(member=name):
                self.fixture.write(members={name: encoded({'unrelated': True})})
                self.denied()

    def test_partial_collection_and_partial_archive_are_rejected(self):
        for name in ('b24-arithmetic-review.json', 'b24-evidence.tar.gz', 'collection.json'):
            with self.subTest(file=name):
                self.fixture.write()
                (self.directory / name).unlink()
                self.denied()
        for name in ('closed.json', 'arithmetic-review.json', 'input/manifest.json',
                     'format-preflight/receipt.json'):
            with self.subTest(member=name):
                self.fixture.write(members={name: None})
                self.denied()

    def test_required_file_cannot_be_omitted_from_collection_hashes(self):
        path = self.directory / 'collection.json'
        value = json.loads(path.read_bytes())
        del value['files']['b24-closed.json']
        path.write_bytes(encoded(value))
        self.denied()

    def test_incomplete_invalid_or_exam_receipts_are_rejected(self):
        for document, key, value in ((self.fixture.closed, 'valid', False),
                                     (self.fixture.audit, 'valid', False),
                                     (self.fixture.closed, 'result', 'CHECKPOINT_READY'),
                                     (self.fixture.closed, 'exam_opened', True),
                                     (self.fixture.audit, 'exam_opened', True),
                                     (self.fixture.closed, 'campaign', 'RUN'),
                                     (self.fixture.closed, 'condition', 'S6-B23')):
            with self.subTest(key=key, value=value):
                original = document.copy()
                document[key] = value
                self.fixture.write()
                self.denied()
                document.clear()
                document.update(original)
        self.fixture.write(status_changes={'stage': 'CHECKPOINT_READY'})
        self.denied()

    def test_totals_must_match_audit_and_actual_format_receipt(self):
        for key, value in (('physical_games', 4), ('model_calls', 3), ('format_calls', 7),
                           ('total_model_calls', 9), ('physical_games', True), ('model_calls', -1)):
            with self.subTest(key=key, value=value):
                original = self.fixture.closed[key]
                self.fixture.closed[key] = value
                self.fixture.write()
                self.denied()
                self.fixture.closed[key] = original

    def test_r1_cannot_omit_prior_calls_or_use_unbound_recovery(self):
        self.fixture = CustodyFixture(self.directory, recovery=True)
        for key, value in (('prior_format_calls', 0), ('format_calls', 8),
                           ('current_profile_total_model_calls', 16), ('total_model_calls', 10),
                           ('recovery_sha256', '0' * 64)):
            with self.subTest(key=key):
                original = self.fixture.closed[key]
                self.fixture.closed[key] = value
                self.fixture.write()
                self.denied()
                self.fixture.closed[key] = original
        self.fixture.write(members={'input/recovery.json': None})
        self.denied()

    def test_wrong_prefix_mixed_prefixes_and_duplicate_members_are_rejected(self):
        self.fixture.prefix = 'unrelated-results'
        self.fixture.write()
        self.denied()
        self.fixture.prefix = 'b24-results'
        raw = encoded(self.fixture.closed)
        for name in ('b24-results/closed.json', 'b24-r1-results/closed.json',
                     'b24-results/./closed.json', '../b24-results/closed.json'):
            with self.subTest(member=name):
                item = tarfile.TarInfo(name)
                item.size = len(raw)
                self.fixture.write(extra_members=[(item, raw)])
                self.denied()

    def test_archive_links_and_path_escape_are_rejected(self):
        item = tarfile.TarInfo('b24-results/closed.json')
        item.type = tarfile.SYMTYPE
        item.linkname = '../foreign.json'
        self.fixture.write(members={'closed.json': None}, extra_members=[(item, b'')])
        self.denied()
        self.fixture.write()
        path = self.directory / 'collection.json'
        value = json.loads(path.read_bytes())
        value['files']['../foreign.json'] = '0' * 64
        path.write_bytes(encoded(value))
        self.denied()

    def test_malformed_duplicate_and_nonfinite_metadata_raise_permission_error(self):
        for raw in (b'{', b'[]', b'{"version":1,"version":2,"files":{}}',
                    b'{"version": NaN}', b'{"version": 1e400}'):
            with self.subTest(raw=raw):
                (self.directory / 'collection.json').write_bytes(raw)
                self.denied()

    def test_bare_or_missing_close_is_not_custody(self):
        self.fixture.path.unlink()
        self.denied()
        self.fixture.path.write_bytes(encoded({'valid': True, 'result': 'DIAGNOSTIC_COMPLETE',
                                              'exam_opened': False}))
        (self.directory / 'collection.json').unlink()
        self.denied()


if __name__ == '__main__':
    unittest.main()
