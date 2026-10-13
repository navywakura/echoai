"""Study selection/audit tests; no model or candidate processes are launched."""
import copy
import importlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from echoai.pcworld.adversarial import fixed_order
from echoai.pcworld.pilot import save, source_manifest, CONTRACT
from echoai.pcworld.receipts import ReceiptStore, digest
from echoai.pcworld.repairs import repair_task_variants


class Scaling(unittest.TestCase):
    def setUp(self):
        self.s = importlib.import_module('echoai.pcworld.scaling')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'study'
        self.calls = []
        # Synthetic declarations only: run_pilot is mocked, no GPU is contacted.
        revision = '9d3053fce650fe1cdbdb75998c2a87add9d178ef'
        sha = '4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085'
        self.config = {'model': 'pcworld-qwen25-coder32b', 'revision': revision,
                       'tokenizer': 'embedded GGUF ' + sha, 'seed': 999, 'context_tokens': 4096}
        self.health = {'worker_ready': True, 'stopped': False, 'metadata': {
            'synthetic_test_fixture': True, 'model_profile': 'qwen25-coder32b',
            'model_revision': revision, 'model_sha256': sha, 'model_bytes': 19851335872,
            'requested_devices': ['CUDA0', 'CUDA1'], 'gpu_offload': [['65', '65']],
            'gpu_model_buffers_mib': {'CUDA0': 1024, 'CUDA1': 9500.25}}}
        self.runtime = SimpleNamespace(id='a' * 64)
        self.addCleanup(patch.stopall)
        patch.object(self.s, 'audit_run', return_value={'valid': True, 'records': 3}).start()
        patch.object(self.s, 'run_pilot', side_effect=self.child).start()

    def child(self, output, **kw):
        self.calls.append((Path(output), kw))
        output = Path(output);output.mkdir()
        task = next(t for t in repair_task_variants(24, seed=47) if t['id'] == kw['task_ids'][0])
        task.update(probe_catalog='expanded-v2', probe_order_seed=20261013)
        task['fixed_probe_order'] = list(fixed_order(task))
        arm = kw['arms'][0]
        ep = {'task': task['id'], 'arm': arm, 'development_accepted': arm != 'I2',
              'counterexamples_repaired': False, 'tokens': 101, 'llm_calls': 1,
              'repair_attempts': 0, 'wall_ms': 23, 'host_cpu_us': 5, 'error': None,
              'counterexamples': [], 'budget': {'used': {'tools': 7, 'critic_calls': 0, 'cpu_us': 4}}}
        if task['id'].endswith('-03') and task['family'] in getattr(self, 'repaired_families', ()):
            ep.update(counterexamples_repaired=True, repair_attempts=1)
        library = kw.get('shared_library')
        if library is not None:
            ep['shared_memory'] = {'lessons': len(library.lookup(task)), 'tools': 1, 'lookup_us': 1, 'cpu_us': 1}
        report = {'episodes': [ep], 'suite': 'repair-v2', 'sources_unchanged': True,
                  'scientific_claim': False, 'seeded_diagnostic': False}
        sources = source_manifest()
        provider = {'kind': 'http', 'config': kw['config'], 'local_evidence': kw['model_evidence']}
        protocol = json.loads(CONTRACT.read_text())
        for name, data in (('tasks', [task]), ('result', report), ('sources', sources),
                           ('provider', provider), ('contract', protocol)):
            save(output / (name + '.json'), data)
        store = ReceiptStore(output / 'receipts', output / 'authority')
        rc = {'kind': 'run_contract', 'arms': [arm], 'suite': 'repair-v2',
              'task_families': [task['family']], 'tasks_sha256': digest([task]),
              'sources_sha256': digest(sources), 'contract_sha256': digest(protocol),
              'provider_sha256': digest(provider), 'episode_ids': [task['id'] + '-' + arm],
              'runtime_snapshot': self.runtime.id, 'cache_properties': False,
              'seeded_diagnostic': False, 'episode_wall_seconds': 900}
        if library is not None:
            rc['shared_library'] = {'path': str(library.path.resolve()), 'identity': library.identity()}
        store.append(rc)
        store.append({'kind': 'run_result', 'result_sha256': digest(report)})
        return report

    def run_study(self):
        return self.s.run_scaling(self.root, self.config, self.runtime, self.health)

    def test_model_evidence_rejects_stopped_14b_and_incomplete_gpu_load_before_any_work(self):
        self.s.validate_model_evidence(self.config, self.health)
        cases = [((), None), (('worker_ready',), False), (('worker_ready',), 1),
                 (('stopped',), True), (('stopped',), 0), (('metadata',), None),
                 (('metadata', 'model_profile'), 'qwen25-coder14b'),
                 (('metadata', 'model_revision'), 'main'), (('metadata', 'model_sha256'), '0' * 64),
                 (('metadata', 'model_bytes'), 8988110272),
                 (('metadata', 'requested_devices'), ['CUDA0']),
                 (('metadata', 'gpu_offload'), [['49', '49']]),
                 (('metadata', 'gpu_offload'), [['40', '65']]),
                 (('metadata', 'gpu_offload'), []),
                 (('metadata', 'gpu_model_buffers_mib'), {'CUDA0': 9000}),
                 (('metadata', 'gpu_model_buffers_mib', 'CUDA1'), 1023.9),
                 (('metadata', 'gpu_model_buffers_mib', 'CUDA1'), float('nan')),
                 (('metadata', 'gpu_model_buffers_mib', 'CUDA1'), float('inf'))]
        for keys, value in cases:
            with self.subTest(keys=keys, value=value):
                bad = copy.deepcopy(self.health)
                if keys:
                    parent = bad
                    for key in keys[:-1]:parent = parent[key]
                    parent[keys[-1]] = value
                else:bad = value
                with self.assertRaises(ValueError):
                    self.s.run_scaling(self.root, self.config, self.runtime, bad)
                self.assertFalse(self.root.exists())
                self.assertEqual(self.calls, [])
        for key, value in (('model', 'pcworld-qwen25-coder14b'), ('revision', 'main'),
                           ('tokenizer', 'embedded GGUF wrong')):
            with self.subTest(config=key), self.assertRaises(ValueError):
                self.s.validate_model_evidence({**self.config, key: value}, self.health)

    def test_audit_revalidates_even_authenticated_bad_model_evidence(self):
        self.run_study()
        original = json.loads((self.root / 'contract.json').read_text())
        bodies = [r['body'] for r in ReceiptStore(self.root / 'receipts', self.root / 'authority').records]
        for stopped in (True, False):
            contract = copy.deepcopy(original);contract['model_evidence']['stopped'] = stopped
            save(self.root / 'contract.json', contract)
            changed = copy.deepcopy(bodies);changed[0]['contract'] = contract
            for path in (self.root / 'receipts/receipts.jsonl', self.root / 'authority/authority.json'):
                path.unlink()
            journal = ReceiptStore(self.root / 'receipts', self.root / 'authority')
            for body in changed:journal.append(body)
            audit = self.s.audit_scaling(self.root)
            self.assertEqual(audit['valid'], not stopped)
            if stopped:self.assertIn('model evidence', audit['errors'][0])

    def test_exact_66_jobs_and_old_target_values_with_five_rotated_conditions(self):
        result = self.run_study()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.calls), 66)
        self.assertEqual(len(result['donors']), 6)
        self.assertEqual(len(result['receivers']), 60)
        self.assertEqual(result['publications'], [])
        self.assertTrue(self.s.audit_scaling(self.root)['valid'])
        donors = [kw['task_ids'][0] for _, kw in self.calls[:6]]
        self.assertTrue(all(t.endswith('-03') for t in donors))
        self.assertTrue(all(kw.get('shared_library') is None for _, kw in self.calls[:6]))
        baseline = repair_task_variants(12, seed=47)
        for i, task in enumerate(baseline):
            rows = result['receivers'][i * 5:(i + 1) * 5]
            self.assertEqual({r['condition'] for r in rows}, {'S', 'I2', 'F', 'E', 'E_shared'})
            self.assertEqual({r['task_id'] for r in rows}, {task['id']})
            conditions = ['S', 'I2', 'F', 'E', 'E_shared']
            self.assertEqual([r['condition'] for r in rows], conditions[i % 5:] + conditions[:i % 5])
        self.assertEqual(repair_task_variants(24, seed=47)[:12], baseline)
        for path, kw in self.calls:
            self.assertEqual(kw['config']['seed'], 73)
            self.assertEqual(kw['episode_wall_seconds'], 900)
            self.assertEqual(kw['task_seed'], 47)
            self.assertFalse(kw['seeded_diagnostic'])
        for row, (_, kw) in zip(result['receivers'], self.calls[6:]):
            self.assertEqual(kw['arms'][0], 'E' if row['condition'] == 'E_shared' else row['condition'])
            self.assertEqual(kw['shared_library'].path.name,
                             'shared-library' if row['condition'] == 'E_shared' else 'empty-library')
        self.assertEqual(result['aggregates']['receivers']['S']['tokens'], 1212)
        self.assertEqual(result['aggregates']['receivers']['I2']['accepted'], 0)
        self.assertEqual(result['aggregates']['donors']['episodes'], 6)

    def test_ineligible_donors_never_publish_or_stop_receiver_matrix(self):
        with patch.object(self.s.SharedConceptLibrary, 'publish_from_run',
                          side_effect=AssertionError('unrepaired donor publication')):
            result = self.run_study()
        self.assertEqual(len(result['receivers']), 60)
        self.assertEqual(len(self.s.SharedConceptLibrary(self.root / 'shared-library').store.records), 1)

    def test_six_publications_before_receivers_and_only_matching_shared_cards(self):
        # Derivation/execution evidence is tested in test_pcworld_shared. Here
        # only derivation is mocked; persistent journals, contracts, AST checks,
        # lookup compatibility and study custody remain real.
        shared = importlib.import_module('echoai.pcworld.shared')
        tasks = {t['id']: t for t in repair_task_variants(24, seed=47)}
        self.repaired_families = {t['family'] for t in tasks.values()}
        def derive(run, task_id, arm, author):
            task = tasks[task_id];contract = shared._contract(task)
            lesson = {'schema': shared.SCHEMA, 'status': 'candidate', 'requires_verification': True,
                      'scope': 'synthetic orchestration fixture', 'contract': contract,
                      'compatibility_sha256': digest(contract), **shared._source('print(0)\n'),
                      'counterexample': {'input': [], 'observed': 1, 'expected': 0},
                      'provenance': {'run_dir': str(Path(run).resolve()), 'task_id': task_id,
                                     'family': task['family'], 'arm': arm, 'author_agent_id': author}}
            lesson['lesson_id'] = digest(lesson)
            return lesson
        with patch.object(shared, '_derive', side_effect=derive):
            result = self.run_study()
            self.assertEqual(len(result['publications']), 6)
            self.assertEqual(result['aggregates']['publication']['tools'], 6)
            for row in result['receivers']:
                self.assertEqual(row['shared_memory']['lessons'], int(row['condition'] == 'E_shared'))
            self.assertTrue(self.s.audit_scaling(self.root)['valid'])
            kinds = [r['body']['kind'] for r in ReceiptStore(self.root / 'receipts', self.root / 'authority').records]
            self.assertEqual(kinds, ['scaling_contract'] + ['child_result'] * 6 +
                             ['publication'] * 6 + ['libraries_frozen'] + ['child_result'] * 60 + ['scaling_result'])
            journal = self.root / 'shared-library/receipts/receipts.jsonl'
            raw = journal.read_bytes();journal.write_bytes(b'\n'.join(raw.splitlines()[:-1]) + b'\n')
            self.assertFalse(self.s.audit_scaling(self.root)['valid'])
            journal.write_bytes(raw)
            self.assertTrue(self.s.audit_scaling(self.root)['valid'])

    def test_signed_selection_change_and_unlisted_run_are_rejected(self):
        self.run_study()
        extra = self.root / 'receiver-extra';extra.mkdir()
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])
        extra.rmdir()
        contract = json.loads((self.root / 'contract.json').read_text())
        contract['jobs'][0]['task_id'] = 'repair-v2-records-00'
        save(self.root / 'contract.json', contract)
        records = ReceiptStore(self.root / 'receipts', self.root / 'authority').records
        bodies = [r['body'] for r in records];bodies[0]['contract'] = contract
        for path in (self.root / 'receipts/receipts.jsonl', self.root / 'authority/authority.json'):
            path.unlink()
        journal = ReceiptStore(self.root / 'receipts', self.root / 'authority')
        for body in bodies:journal.append(body)
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])

    def test_error_persists_completed_children_and_never_retries(self):
        original = self.child
        def failed(output, **kw):
            if len(self.calls) == 2:
                raise RuntimeError('infrastructure stopped')
            return original(output, **kw)
        with patch.object(self.s, 'run_pilot', side_effect=failed):
            with self.assertRaisesRegex(RuntimeError, 'infrastructure stopped'):
                self.run_study()
        result = json.loads((self.root / 'result.json').read_text())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(len(result['donors']), 2)
        self.assertEqual(result['receivers'], [])
        records = ReceiptStore(self.root / 'receipts', self.root / 'authority').records
        self.assertEqual(records[-1]['body']['result_sha256'], digest(result))
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])
        with self.assertRaises(FileExistsError):
            self.run_study()

    def test_audit_rejects_config_task_and_summary_changes_then_accepts_restore(self):
        result = self.run_study()
        child = self.root / result['receivers'][0]['run']
        for filename, mutate in (
                ('provider.json', lambda d: d['config'].update(seed=74)),
                ('tasks.json', lambda d: d[0].update(id='repair-v2-intervals-03')),
                ('result.json', lambda d: d['episodes'][0].update(tokens=0))):
            path = child / filename;raw = path.read_bytes();value = json.loads(raw)
            mutate(value);save(path, value)
            self.assertFalse(self.s.audit_scaling(self.root)['valid'], filename)
            path.write_bytes(raw)
        path = self.root / 'result.json';raw = path.read_bytes();value = json.loads(raw)
        value['aggregates']['receivers']['S']['accepted'] = 999;save(path, value)
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])
        path.write_bytes(raw)
        self.assertTrue(self.s.audit_scaling(self.root)['valid'])

    def test_audit_rejects_extra_library_record_and_missing_custody(self):
        self.run_study()
        lib = self.s.SharedConceptLibrary(self.root / 'empty-library')
        lib.store.append({'kind': 'unexpected'})
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])
        (self.root / 'authority/authority.json').unlink()
        self.assertFalse(self.s.audit_scaling(self.root)['valid'])
        self.assertFalse((self.root / 'authority/authority.json').exists())

    def test_publication_binds_family_exact_new_donor_author_and_card(self):
        job = {'run': 'donor-records-03', 'task_id': 'repair-v2-records-03', 'family': 'records'}
        card = {'source': 'pass', 'provenance': {'run_dir': str((self.root / job['run']).resolve()),
                'task_id': job['task_id'], 'family': 'records', 'arm': 'E',
                'author_agent_id': 'AGENT_A_records'}}
        pub = {'lesson_sha256': digest(card)}
        self.assertTrue(self.s.publication_matches(card, pub, self.root, job))
        for field in ('run_dir', 'task_id', 'family', 'arm', 'author_agent_id'):
            bad = copy.deepcopy(card);bad['provenance'][field] = 'wrong'
            self.assertFalse(self.s.publication_matches(bad, {'lesson_sha256': digest(bad)}, self.root, job))
        self.assertFalse(self.s.publication_matches({**card, 'source': 'other'}, pub, self.root, job))

    def test_audit_rejects_validly_signed_runtime_and_limit_drift(self):
        result = self.run_study()
        child = self.root / result['receivers'][0]['run']
        store = ReceiptStore(child / 'receipts', child / 'authority')
        originals = [r['body'] for r in store.records]
        for key, value in (('runtime_snapshot', 'b' * 64), ('episode_wall_seconds', 901),
                           ('cache_properties', True), ('seeded_diagnostic', True)):
            changed = copy.deepcopy(originals);changed[0][key] = value
            for path in (child / 'receipts/receipts.jsonl', child / 'authority/authority.json'):
                path.unlink()
            rebuilt = ReceiptStore(child / 'receipts', child / 'authority')
            for body in changed:rebuilt.append(body)
            self.assertFalse(self.s.audit_scaling(self.root)['valid'], key)
