"""Persistent lessons use real custody/snapshots; only whole-run audit is mocked.

These synthetic donor receipts avoid launching candidate processes. Whole-run
execution replay is pilot.audit_run's responsibility and is tested separately.
"""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.pcworld.receipts import ReceiptStore, canonical, digest
from echoai.pcworld.repairs import repair_tasks
from echoai.pcworld.snapshots import SnapshotStore


SOURCE = "import json,sys\nx=json.load(sys.stdin)\nseen=set()\nresult=[]\nfor row in x:\n if row['id'] not in seen:\n  seen.add(row['id']); result.append(row)\nprint(json.dumps(result))\n"
CE = [{'id': 'a', 'value': 4}, {'id': 'a', 'value': 9}]


def donor(root, *, accepted=True, commit=True, support=True, public=True,
          final_only=False, commit_wrong=False, source=SOURCE, task_id='donor-a'):
    run = root / task_id
    run.mkdir()
    task = dict(repair_tasks()[1], id=task_id,
                development_inputs=['HIDDEN_TEST_SENTINEL'])
    (run / 'tasks.json').write_bytes(canonical([task]))
    episode = run / (task_id + '-E')
    episode.mkdir()
    snapshots = SnapshotStore(episode / 'snapshots')
    initial = root / (task_id + '-initial')
    initial.mkdir()
    (initial / 'solution.py').write_text(task['initial'])
    before = snapshots.capture(initial)
    repaired = root / (task_id + '-repaired')
    repaired.mkdir()
    (repaired / 'solution.py').write_text(source)
    after = snapshots.capture(repaired)
    store = ReceiptStore(episode / 'receipts', episode / 'authority')
    store.append({'kind': 'observation', 'task': task_id, 'arm': 'E',
                  'task_sha256': digest(task), 'snapshot': before.id})

    def prop(snapshot, value, status, observed, expected, final=False):
        execution = store.append({'kind': 'observation', 'candidate_snapshot': snapshot,
                                  'input': value, 'execution': {'snapshot': snapshot}})
        return store.append({'kind': 'property', 'final_evaluation': final,
                             'execution_receipt': execution['sha256'],
                             'property': {'snapshot': snapshot, 'input': value,
                                          'observed': observed, 'expected': expected,
                                          'scope': task['property'], 'checker': task['checker'],
                                          'status': status}})

    refutation = prop(before.id, CE, 'contradicted', [CE[1]], [CE[0]], final=final_only)
    public_receipts = []
    if public:
        for value in task['public_inputs']:
            public_receipts.append(prop(after.id, value, 'supported', value, value))
    supported = prop(after.id, CE, 'supported', [CE[0]], [CE[0]], final=final_only) if support else None
    committed = None
    if commit:
        committed = store.append({'kind': 'observation', 'operation': 'repair_committed',
                                  'snapshot': before.id if commit_wrong else after.id,
                                  'base_snapshot': before.id, 'attempt': 1,
                                  'verified_inputs': task['public_inputs'] + [CE]})
    store.append({'kind': 'observation', 'operation': 'candidate_frozen', 'snapshot': after.id})
    final = prop(after.id, 'HIDDEN_TEST_SENTINEL', 'supported', 'HIDDEN_OUTPUT_SENTINEL',
                 'HIDDEN_OUTPUT_SENTINEL', final=True)
    result = {'task': task_id, 'arm': 'E', 'candidate': after.id,
              'development_accepted': accepted, 'final_cases_passed': accepted,
              'counterexamples_repaired': support and commit, 'error': None,
              'counterexamples': [CE], 'final_properties': [final['body']['property']],
              'required_inputs': ['HIDDEN_TEST_SENTINEL']}
    result_receipt = store.append({'kind': 'property', 'task_result': result})
    (episode / 'result.json').write_bytes(canonical(result))
    report = {'episodes': [result], 'scientific_claim': False}
    (run / 'result.json').write_bytes(canonical(report))
    root_store = ReceiptStore(run / 'receipts', run / 'authority')
    root_store.append({'kind': 'run_contract', 'tasks_sha256': digest([task]),
                       'episode_ids': [task_id + '-E'], 'arms': ['E']})
    root_store.append({'kind': 'run_result', 'result_sha256': digest(report)})
    return {'run': run, 'task': task, 'store': store, 'episode': episode,
            'after': after, 'before': before, 'refutation': refutation,
            'supported': supported, 'committed': committed,
            'result_receipt': result_receipt, 'public_receipts': public_receipts}


class SharedLessons(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module('echoai.pcworld.shared')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.audit = patch('echoai.pcworld.pilot.audit_run', return_value={
            'valid': True, 'errors': [], 'episodes': 1, 'records': 12,
            'scientific_claim': False}).start()
        self.addCleanup(patch.stopall)
        self.library = self.api.SharedConceptLibrary(self.root / 'library')

    def target(self, fixture, **changes):
        return dict(fixture['task'], id='receiver-b', public_inputs=[],
                    development_inputs=['RECEIVER_HIDDEN'], variant=99, **changes)

    def publish(self, fixture, library=None):
        return (library or self.library).publish_from_run(
            fixture['run'], fixture['task']['id'], 'E', 'agent-a')

    def test_restart_returns_actual_repaired_source_and_only_nonfinal_evidence(self):
        f = donor(self.root)
        empty_identity = self.library.identity()
        lesson = self.publish(f)
        self.assertNotEqual(empty_identity, self.library.identity())
        fresh = self.api.SharedConceptLibrary(self.root / 'library')
        self.assertEqual(fresh.identity(), self.library.identity())
        self.assertEqual(fresh.lookup(self.target(f)), [lesson])
        self.assertEqual(lesson['source'], SOURCE)
        self.assertEqual(lesson['source_sha256'], hashlib.sha256(SOURCE.encode()).hexdigest())
        self.assertEqual(lesson['ast_sha256'], hashlib.sha256(ast.dump(
            ast.parse(SOURCE), include_attributes=False).encode()).hexdigest())
        self.assertTrue(lesson['requires_verification'])
        self.assertEqual(lesson['status'], 'candidate')
        self.assertEqual(lesson['counterexample']['input'], CE)
        self.assertEqual(lesson['counterexample']['observed'], [CE[1]])
        self.assertEqual(lesson['counterexample']['expected'], [CE[0]])
        p = lesson['provenance']
        self.assertEqual(p['run_dir'], str(f['run'].resolve()))
        self.assertEqual(p['task_id'], 'donor-a')
        self.assertEqual(p['author_agent_id'], 'agent-a')
        self.assertEqual(p['family'], 'records')
        self.assertEqual(p['checker'], f['task']['checker'])
        self.assertEqual(p['snapshot'], f['after'].id)
        encoded = canonical(lesson)
        for forbidden in (b'HIDDEN_TEST_SENTINEL', b'HIDDEN_OUTPUT_SENTINEL',
                          b'development_inputs', b'final_properties', b'required_inputs'):
            self.assertNotIn(forbidden, encoded)
        self.assertIn(f['refutation']['sha256'].encode(), encoded)
        self.assertIn(f['supported']['sha256'].encode(), encoded)
        self.assertIn(f['committed']['sha256'].encode(), encoded)

    def test_identity_is_public_digest_and_duplicate_publish_is_idempotent(self):
        f = donor(self.root)
        first = self.publish(f)
        identity = self.library.identity()
        self.assertEqual(self.publish(f), first)
        self.assertEqual(self.library.identity(), identity)
        first['source'] = 'mutated return value'
        self.assertEqual(self.library.lookup(self.target(f))[0]['source'], SOURCE)
        public = [json.loads(line) for line in
                  (self.root / 'library/receipts/receipts.jsonl').read_text().splitlines()]
        self.assertEqual(identity, digest(public))

    def test_exact_public_contract_excludes_variant_values_but_rejects_semantic_mismatch(self):
        f = donor(self.root)
        self.publish(f)
        self.assertEqual(self.library.lookup(f['task']), [])
        self.assertEqual(len(self.library.lookup(self.target(f))), 1)
        for key, value in (('description', 'keep the last record'), ('property', 'repair.path'),
                           ('family', 'path'), ('checker', 'new-checker'),
                           ('input_schema', 'changed-domain'), ('input_json_schema', {'type': 'string'}),
                           ('preconditions', ['another-domain'])):
            with self.subTest(key=key):
                self.assertEqual(self.library.lookup(self.target(f, **{key: value})), [])

    def test_returns_at_most_one_deterministically(self):
        a = donor(self.root, task_id='donor-a')
        b = donor(self.root, task_id='donor-c')
        first = self.publish(a)
        self.publish(b)
        self.assertEqual(self.library.lookup(self.target(a)), [first])

    def test_failed_unrepaired_wrong_snapshot_or_unwitnessed_donors_rejected(self):
        cases = ({'accepted': False}, {'commit': False}, {'support': False},
                 {'public': False}, {'final_only': True}, {'commit_wrong': True},
                 {'source': 'not python !'})
        before = self.library.identity()
        for i, flags in enumerate(cases):
            with self.subTest(flags=flags):
                f = donor(self.root, task_id=f'bad-{i}', **flags)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.publish(f)
                self.assertEqual(self.library.identity(), before)

    def test_invalid_whole_run_audit_blocks_publish_and_retrieval(self):
        f = donor(self.root)
        self.audit.return_value = {'valid': False, 'errors': ['property replay differs']}
        with self.assertRaises((ValueError, RuntimeError)):
            self.publish(f)
        self.audit.return_value = {'valid': True}
        lesson = self.publish(f)
        self.audit.return_value = {'valid': False, 'errors': ['custody differs']}
        with self.assertRaises((ValueError, RuntimeError)):
            self.library.lookup(self.target(f))
        self.audit.return_value = {'valid': True}
        self.assertEqual(self.library.lookup(self.target(f)), [lesson])

    def test_journal_tamper_suffix_deletion_and_restore(self):
        f = donor(self.root)
        lesson = self.publish(f)
        journal = self.root / 'library/receipts/receipts.jsonl'
        original = journal.read_bytes()
        for bad in (original.replace(b'agent-a', b'agent-z'), original.splitlines(keepends=True)[0], b''):
            journal.write_bytes(bad)
            with self.assertRaises((ValueError, RuntimeError)):
                self.library.lookup(self.target(f))
            with self.assertRaises((ValueError, RuntimeError)):
                self.library.identity()
            journal.write_bytes(original)
        self.assertEqual(self.library.lookup(self.target(f)), [lesson])

    def test_missing_library_custody_is_not_reinitialized(self):
        self.publish(donor(self.root))
        for name in ('receipts/receipts.jsonl', 'authority/authority.json'):
            path = self.root / 'library' / name
            original = path.read_bytes()
            path.unlink()
            with self.assertRaises((ValueError, RuntimeError, OSError)):
                self.api.SharedConceptLibrary(self.root / 'library')
            self.assertFalse(path.exists())
            path.write_bytes(original)

    def test_donor_custody_deletion_and_source_tamper_fail_even_with_mocked_audit(self):
        f = donor(self.root)
        lesson = self.publish(f)
        paths = [f['run'] / 'receipts/receipts.jsonl',
                 f['episode'] / 'authority/authority.json',
                 f['episode'] / 'receipts/receipts.jsonl',
                 f['after'].root / 'solution.py']
        for path in paths:
            with self.subTest(path=path.name):
                raw = path.read_bytes()
                mode = path.stat().st_mode & 0o777
                path.chmod(0o600)
                path.write_bytes(raw.replace(b'result', b'BROKEN') if path.name=='solution.py' else b'')
                with self.assertRaises((ValueError, RuntimeError, OSError)):
                    self.library.lookup(self.target(f))
                path.write_bytes(raw)
                path.chmod(mode)
                self.assertEqual(self.library.lookup(self.target(f)), [lesson])

    def test_donor_missing_receipts_are_not_created_on_lookup(self):
        f = donor(self.root)
        self.publish(f)
        path = f['run'] / 'authority/authority.json'
        path.unlink()
        with self.assertRaises((ValueError, RuntimeError, OSError)):
            self.library.lookup(self.target(f))
        self.assertFalse(path.exists())

    def test_changed_task_or_result_cannot_reuse_authenticated_donor(self):
        f = donor(self.root)
        self.publish(f)
        for path in (f['run'] / 'tasks.json', f['run'] / 'result.json', f['episode'] / 'result.json'):
            raw = path.read_bytes()
            path.write_bytes(raw.replace(b'donor-a', b'donor-z'))
            with self.assertRaises((ValueError, RuntimeError)):
                self.library.lookup(self.target(f))
            path.write_bytes(raw)
        self.assertEqual(len(self.library.lookup(self.target(f))), 1)

    def test_author_and_task_paths_are_bounded_and_not_path_traversals(self):
        f = donor(self.root)
        for task_id, author in (('../outside', 'agent-a'), ('donor-a', ''),
                                ('donor-a', 'x' * 5000)):
            with self.assertRaises(ValueError):
                self.library.publish_from_run(f['run'], task_id, 'E', author)

    def test_oversize_source_is_rejected_before_publication(self):
        f = donor(self.root, source=SOURCE + '#' + 'x' * 70000)
        with self.assertRaises((ValueError, RuntimeError)):
            self.publish(f)

