"""T05/T15: authenticated custody, bounded records and real restart faults.

Only temporary sibling journal/authority directories are used. The authority
is read by the test supervisor to check signatures and construct a full log;
none of these fixtures execute candidate code or certify task success.
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GENESIS = '0' * 64


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        try:
            self.api = importlib.import_module('pcworld.receipts')
        except ModuleNotFoundError as exc:
            if exc.name != 'pcworld.receipts':
                raise
            self.fail('ReceiptStore implementation is absent')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'journal'
        self.authority = self.root / 'authority'
        self.store = self.api.ReceiptStore(self.directory, self.authority)
        self.journal = self.directory / 'receipts.jsonl'
        self.anchor = self.authority / 'authority.json'

    def rewrite(self, records):
        self.journal.write_bytes(b''.join(encoded(record) + b'\n' for record in records))

    def assert_corrupt(self):
        result = self.store.audit()
        self.assertFalse(result['ok'])
        self.assertTrue(result['errors'])
        with self.assertRaises(self.api.ReceiptIntegrityError):
            self.api.ReceiptStore(self.directory, self.authority)
        with self.assertRaises(self.api.ReceiptIntegrityError):
            self.store.append({'observation': 'must not append'})

    def test_canonical_sorted_utf8_json_and_sha256(self):
        value = {'z': [3, {'b': True, 'a': None}], 'a': 'á'}
        expected = '{"a":"á","z":[3,{"a":null,"b":true}]}'.encode('utf-8')
        self.assertEqual(self.api.canonical(value), expected)
        self.assertEqual(self.api.digest(value), hashlib.sha256(expected).hexdigest())
        self.assertEqual(self.api.digest({}),
                         '44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a')

    def test_canonical_rejects_lossy_or_non_json_values(self):
        cycle = []
        cycle.append(cycle)
        for value in ({1: 'a'}, {1: 'a', '1': 'b'}, (1, 2), {1}, b'bytes',
                      float('nan'), float('inf'), cycle):
            with self.subTest(kind=type(value).__name__), self.assertRaises((TypeError, ValueError)):
                self.api.canonical(value)

    def test_chain_and_mac_authenticate_every_envelope_field(self):
        first = self.store.append({'observation': {'exit_code': 0}})
        second = self.store.append({'property': {'status': 'unknown'}})
        self.assertEqual(first['schema'], 'pcworld.receipt.v1')
        self.assertEqual((first['n'], first['prev']), (1, GENESIS))
        self.assertEqual((second['n'], second['prev']), (2, first['sha256']))
        key = bytes.fromhex(json.loads(self.anchor.read_bytes())['key'])
        for record in (first, second):
            payload = {name: record[name] for name in ('schema', 'n', 'prev', 'body')}
            self.assertEqual(record['sha256'], hashlib.sha256(encoded(payload)).hexdigest())
            signed = dict(payload, sha256=record['sha256'])
            self.assertEqual(record['hmac'], hmac.new(key, encoded(signed), 'sha256').hexdigest())
        self.assertEqual(self.store.audit(), {'ok': True, 'count': 2,
                                             'head': second['sha256'], 'errors': []})

    def test_observation_property_and_task_fields_preserved_without_inference(self):
        body = {'schema': 'supervisor.observation.v1',
                'observation': {'exit_code': 0, 'integrity': 'supported'},
                'property': {'status': 'contradicted', 'checker': 'reference'},
                'task': {'status': 'unknown'}, 'extra': [None, False]}
        original = json.loads(encoded(body))
        record = self.store.append(body)
        self.assertEqual(record['body'], original)
        self.assertNotIn('verified', record)
        self.assertNotIn('task_success', record)
        body['task']['status'] = 'supported'
        record['body']['property']['status'] = 'supported'
        records = self.store.records
        records[0]['body']['extra'].append('mutable')
        self.assertEqual(self.store.records[0]['body'], original)

    def test_restart_preserves_key_head_and_records(self):
        first = self.store.append({'event': 'first'})
        authority_before = self.anchor.read_bytes()
        reopened = self.api.ReceiptStore(self.directory, self.authority)
        self.assertEqual(reopened.records, [first])
        self.assertEqual(reopened.head, first['sha256'])
        self.assertEqual(self.anchor.read_bytes(), authority_before)
        self.assertEqual(reopened.append({'event': 'second'})['n'], 2)

    def test_T05_recalculated_chain_without_key_is_rejected(self):
        self.store.append({'observation': {'exit_code': 1}})
        self.store.append({'property': {'status': 'contradicted'}})
        records = self.store.records
        records[0]['body']['observation']['exit_code'] = 0
        previous = GENESIS
        for record in records:
            record['prev'] = previous
            payload = {name: record[name] for name in ('schema', 'n', 'prev', 'body')}
            record['sha256'] = hashlib.sha256(encoded(payload)).hexdigest()
            previous = record['sha256']
        self.rewrite(records)
        self.assert_corrupt()

    def test_T05_suffix_deletion_is_detected_against_external_anchor(self):
        first = self.store.append({'event': 1})
        self.store.append({'event': 2})
        self.rewrite([first])
        self.assert_corrupt()

    def test_T05_entire_journal_deletion_is_not_a_fresh_store(self):
        self.store.append({'event': 1})
        self.journal.unlink()
        self.assert_corrupt()

    def test_T05_valid_older_chain_cannot_replace_current_chain(self):
        self.store.append({'event': 1})
        old = self.journal.read_bytes()
        self.store.append({'event': 2})
        self.journal.write_bytes(old)
        self.assert_corrupt()

    def test_untrusted_torn_tail_is_rejected_without_truncating_evidence(self):
        self.store.append({'event': 1})
        damaged = self.journal.read_bytes() + b'{"n":2'
        self.journal.write_bytes(damaged)
        self.assert_corrupt()
        self.assertEqual(self.journal.read_bytes(), damaged)

    def test_missing_authority_cannot_rekey_an_existing_journal(self):
        self.store.append({'event': 1})
        self.anchor.unlink()
        self.assert_corrupt()

    def test_authority_is_bound_to_one_journal_directory(self):
        self.store.append({'event': 1})
        with self.assertRaises(self.api.ReceiptIntegrityError):
            self.api.ReceiptStore(self.root / 'replacement', self.authority)

    def test_authority_is_separate_and_private(self):
        self.assertFalse(self.anchor.is_relative_to(self.directory))
        self.assertEqual(self.anchor.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.authority.stat().st_mode & 0o777, 0o700)
        for directory, authority in ((self.directory, self.directory),
                                     (self.directory, self.directory / 'secrets'),
                                     (self.authority / 'journal', self.authority)):
            with self.subTest(directory=directory), self.assertRaises(ValueError):
                self.api.ReceiptStore(directory, authority)

    def test_journal_symlink_is_rejected_without_touching_target(self):
        self.store.append({'event': 1})
        target = self.root / 'sentinel'
        target.write_text('private')
        self.journal.unlink()
        self.journal.symlink_to(target)
        self.assert_corrupt()
        self.assertEqual(target.read_text(), 'private')

    def test_authority_symlink_is_rejected(self):
        self.store.append({'event': 1})
        target = self.root / 'saved-authority'
        self.anchor.rename(target)
        self.anchor.symlink_to(target)
        self.assert_corrupt()

    def test_bad_body_cannot_create_a_pending_commit(self):
        before = self.anchor.read_bytes()
        for body in ([], {'value': float('nan')}, {'value': (1, 2)}):
            with self.subTest(body=body), self.assertRaises((ValueError, TypeError)):
                self.store.append(body)
        self.assertEqual(self.anchor.read_bytes(), before)
        self.assertEqual(self.store.records, [])

    def seed_full_journal(self, count):
        # Independent supervisor fixture: real signed bytes at the actual bound,
        # avoiding thousands of unrelated durable commits in a unit test.
        state = json.loads(self.anchor.read_bytes())
        key = bytes.fromhex(state['key'])
        records = []
        previous = GENESIS
        for n in range(1, count + 1):
            record = {'schema': 'pcworld.receipt.v1', 'n': n, 'prev': previous,
                      'body': {'observation': {'index': n}}}
            record['sha256'] = hashlib.sha256(encoded(record)).hexdigest()
            record['hmac'] = hmac.new(key, encoded(record), 'sha256').hexdigest()
            previous = record['sha256']
            records.append(record)
        self.rewrite(records)
        state.update(n=count, head=previous, pending=None)
        self.anchor.write_bytes(encoded(state))

    def test_T15_full_4096_record_store_fails_explicitly_without_wrap_or_loss(self):
        self.seed_full_journal(4096)
        before = self.journal.read_bytes()
        self.assertEqual(self.store.audit()['count'], 4096)
        with self.assertRaises(self.api.ReceiptLimitExceeded):
            self.store.append({'observation': 'overflow'})
        self.assertEqual(self.journal.read_bytes(), before)
        self.assertEqual(self.store.records[-1]['n'], 4096)

    def test_T15_over_capacity_journal_is_rejected_on_restart(self):
        self.seed_full_journal(4097)
        self.assert_corrupt()

    def test_threads_and_store_instances_cannot_fork_the_chain(self):
        stores = [self.api.ReceiptStore(self.directory, self.authority) for _ in range(8)]
        barrier = Barrier(8)

        def append(index):
            barrier.wait(timeout=5)
            return stores[index].append({'observation': {'worker': index}})

        with ThreadPoolExecutor(max_workers=8) as pool:
            records = list(pool.map(append, range(8)))
        self.assertEqual({record['n'] for record in records}, set(range(1, 9)))
        self.assertEqual(self.store.audit()['count'], 8)
        self.assertEqual({record['body']['observation']['worker'] for record in self.store.records},
                         set(range(8)))

    def test_process_initialization_and_appends_share_authority_lock(self):
        directory, authority = self.root / 'race-journal', self.root / 'race-authority'
        script = """
from pathlib import Path
import sys
from pcworld.receipts import ReceiptStore
sys.stdin.read(1)
store = ReceiptStore(Path(sys.argv[1]), Path(sys.argv[2]))
for i in range(5):
    store.append({'worker': int(sys.argv[3]), 'i': i})
"""
        processes = []
        try:
            for index in range(4):
                processes.append(subprocess.Popen(
                    [sys.executable, '-B', '-c', script, str(directory), str(authority), str(index)],
                    cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            for process in processes:
                process.stdin.write(b'x')
                process.stdin.flush()
            for process in processes:
                stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, (stdout, stderr))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        store = self.api.ReceiptStore(directory, authority)
        self.assertEqual(store.audit()['count'], 20)
        self.assertEqual(len({(r['body']['worker'], r['body']['i']) for r in store.records}), 20)

    def test_T15_process_death_at_each_commit_replace_and_fsync_boundary(self):
        script = """
from pathlib import Path
import os, sys
from pcworld.receipts import ReceiptStore
store = ReceiptStore(Path(sys.argv[1]), Path(sys.argv[2]))
name, wanted, edge = sys.argv[3], int(sys.argv[4]), sys.argv[5]
real = getattr(os, name)
calls = 0
def crash(*args, **kwargs):
    global calls
    calls += 1
    if calls == wanted and edge == 'before':
        os._exit(73)
    result = real(*args, **kwargs)
    if calls == wanted and edge == 'after':
        os._exit(73)
    return result
setattr(os, name, crash)
store.append({'observation': 'interrupted'})
"""
        for name, count in (('replace', 3), ('fsync', 6)):
            for index in range(1, count + 1):
                for edge in ('before', 'after'):
                    with self.subTest(name=name, index=index, edge=edge):
                        root = self.root / f'{name}-{index}-{edge}'
                        directory, authority = root / 'journal', root / 'authority'
                        store = self.api.ReceiptStore(directory, authority)
                        first = store.append({'observation': 'first'})
                        result = subprocess.run(
                            [sys.executable, '-B', '-c', script, str(directory), str(authority),
                             name, str(index), edge], cwd=ROOT, capture_output=True, timeout=15)
                        self.assertEqual(result.returncode, 73, result.stderr)
                        pending_or_committed = json.loads((authority / 'authority.json').read_bytes())
                        expected_count = (2 if pending_or_committed['pending'] is not None
                                          or pending_or_committed['n'] == 2 else 1)
                        reopened = self.api.ReceiptStore(directory, authority)
                        self.assertEqual(reopened.audit()['count'], expected_count)
                        self.assertEqual(reopened.records[0], first)
                        self.assertEqual(len(reopened.records), expected_count)
                        self.assertEqual(reopened.append({'observation': 'after restart'})['n'],
                                         expected_count + 1)

    def test_T15_partial_temporary_write_recovers_authenticated_pending_record(self):
        self.store.append({'event': 'first'})
        script = """
from pathlib import Path
import os, sys
from pcworld.receipts import ReceiptStore
store = ReceiptStore(Path(sys.argv[1]), Path(sys.argv[2]))
real = os.write
calls = 0
def partial(fd, data):
    global calls
    calls += 1
    if calls == 2:
        real(fd, data[:7])
        os._exit(73)
    return real(fd, data)
os.write = partial
store.append({'event': 'pending'})
"""
        result = subprocess.run([sys.executable, '-B', '-c', script,
                                 str(self.directory), str(self.authority)], cwd=ROOT,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 73, result.stderr)
        reopened = self.api.ReceiptStore(self.directory, self.authority)
        self.assertEqual([r['body']['event'] for r in reopened.records], ['first', 'pending'])
        self.assertEqual(reopened.audit()['count'], 2)

    def test_pending_commit_does_not_authorize_repair_of_tampered_prefix(self):
        self.store.append({'event': 'first'})
        real_replace = os.replace

        def stop_journal(source, destination, *args, **kwargs):
            if Path(destination) == self.journal:
                raise OSError('simulated disk failure')
            return real_replace(source, destination, *args, **kwargs)

        with patch.object(self.api.os, 'replace', side_effect=stop_journal):
            with self.assertRaises(OSError):
                self.store.append({'event': 'pending'})
        self.journal.write_bytes(b'')
        self.assert_corrupt()

    def test_recovery_syncs_already_replaced_journal_before_advancing_anchor(self):
        self.store.append({'event': 'first'})
        real_fsync = os.fsync
        directory_identity = self.directory.stat()

        def fail_journal_directory_sync(fd):
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) == (directory_identity.st_dev, directory_identity.st_ino):
                raise OSError('journal directory could not be synced')
            return real_fsync(fd)

        # The data rename has completed, but its directory entry is not durable.
        with patch.object(self.api.os, 'fsync', side_effect=fail_journal_directory_sync):
            with self.assertRaises(OSError):
                self.store.append({'event': 'pending'})
            self.assertEqual(len(self.journal.read_bytes().splitlines()), 2)
            with self.assertRaises(OSError):
                self.api.ReceiptStore(self.directory, self.authority)
        state = json.loads(self.anchor.read_bytes())
        self.assertEqual(state['n'], 1)
        self.assertIsNotNone(state['pending'])
        reopened = self.api.ReceiptStore(self.directory, self.authority)
        self.assertEqual(reopened.audit()['count'], 2)


if __name__ == '__main__':
    unittest.main()
