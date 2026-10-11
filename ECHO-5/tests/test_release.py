from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from echo5 import closure, release
from echo5.release import (ROOT, required_gates, verify_domain_audits, verify_sitl_evidence,
                          check_sitl_aggregate, verify_checks_evidence, verify_browser_evidence)
from echo5.release import verify_snapshot_identity
from echo5.evaluation import digest
from echo5.closure import DOMAINS


class ReleaseVerdictTests(unittest.TestCase):
    def checks_fixture(self, folder):
        commands = [
            ('environment', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'check']),
            ('core_tests', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'test']),
            ('sandbox_tests', [str(ROOT / '.venv-sandbox/bin/python'), '-I', str(ROOT / 'scripts/closure.py'), 'test-external']),
            ('javascript_syntax', ['node', '--check', str(ROOT / 'src/echo5/web/app.js')]),
        ]
        hashes = {}
        for name, argv in commands:
            path = folder / (name + '.log')
            binding = {'schema': 'echo5.check-log.v1', 'name': name, 'argv': argv,
                       'pid': 123, 'sources_sha256': 'build'}
            path.write_text(json.dumps(binding) + '\n' + ('Ran 3 tests in 0.01s\n\nOK\n' if 'tests' in name else ''))
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return {'schema': 'echo5.required-checks.v2', 'valid': True, 'error': None,
                'sources_sha256': 'build',
                'commands': [{'name': name, 'argv': argv, 'exit_code': 0, 'timed_out': False, 'pid': 123} for name, argv in commands],
                'artifact_hashes': hashes, 'integrity': {k: {'unchanged': True} for k in ('own', 'legacy', 'host')}}

    def test_check_receipts_must_reconcile_all_commands_and_log_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = self.checks_fixture(folder)
            verify_checks_evidence(folder, report)
            for kind in ('missing', 'duplicate', 'failed', 'timeout', 'stale'):
                changed = deepcopy(report)
                if kind == 'missing': changed['commands'].pop()
                if kind == 'duplicate': changed['commands'][1] = changed['commands'][0]
                if kind == 'failed': changed['commands'][1]['exit_code'] = 1
                if kind == 'timeout': changed['commands'][1]['timed_out'] = True
                if kind == 'stale': changed['integrity']['own']['unchanged'] = False
                with self.assertRaises(ValueError, msg=kind):
                    verify_checks_evidence(folder, changed)
            header = (folder / 'core_tests.log').read_text().partition('\n')[0]
            (folder / 'core_tests.log').write_text(header + '\nRan 0 tests in 0.01s\n\nOK\n')
            with self.assertRaises(ValueError):
                verify_checks_evidence(folder, report)
            report['artifact_hashes']['core_tests.log'] = hashlib.sha256((folder / 'core_tests.log').read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                verify_checks_evidence(folder, report)
            report['valid'] = False
            verify_checks_evidence(folder, report)

    def test_checks_reject_swapped_logs_all_skipped_and_misleading_earlier_summary(self):
        for kind in ('swapped', 'all_skipped', 'earlier_success'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                report = self.checks_fixture(folder)
                log = folder / 'core_tests.log'
                header = log.read_text().partition('\n')[0]
                if kind == 'swapped':
                    log.write_bytes((folder / 'sandbox_tests.log').read_bytes())
                elif kind == 'all_skipped':
                    log.write_text(header + '\nRan 3 tests in 0.01s\n\nOK (skipped=3)\n')
                else:
                    log.write_text(header + '\nRan 3 tests in 0.01s\n\nOK\nRan 0 tests in 0.01s\n\nOK\n')
                report['artifact_hashes'][log.name] = hashlib.sha256(log.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    verify_checks_evidence(folder, report)

    def test_snapshots_reject_declared_hash_mismatch_and_reduced_coverage(self):
        expected = {k: {'folders': ['src'], 'suffixes': ['.py'], 'files': {'src/a.py': 'a', 'src/b.py': 'b'}}
                    for k in ('own', 'legacy', 'host')}
        for value in expected.values():
            value['sha256'] = digest(value['files'])
        verify_snapshot_identity(expected, expected)
        for kind in ('hash', 'coverage', 'scope'):
            changed = deepcopy(expected)
            if kind == 'hash': changed['own']['sha256'] = 'incorrect'
            if kind == 'scope': changed['own']['folders'] = ['src/a.py']
            if kind == 'coverage':
                del changed['own']['files']['src/b.py']
                changed['own']['sha256'] = digest(changed['own']['files'])
            with self.assertRaises(ValueError):
                verify_snapshot_identity(changed, expected)

    def browser_fixture(self, folder):
        from echo5.neural_observer import NeuralObserver
        from echo5.interaction import _seal
        from echo5.trace import Recorder
        boot = 'a' * 32
        observation = {'schema': 'unit_fixture', 'value': 8}
        state = {'session_id': 'demo-1', 'boot_id': boot, 'error': None,
                 'neural': NeuralObserver().observe(observation),
                 'state': {'step': 8, 'observation': observation}, 'events': [{'kind': 'measured'}]}
        terminal = {'session_id': 'demo-1', 'boot_id': boot, 'error': None,
                    'state': {'done': True, 'step': 20, 'observation': {'schema': 'unit_fixture', 'value': 20}},
                    'evaluation': {'success': True, 'actor_claim_used': False}}
        server = {'boot_id': boot, 'boot_source_sha256': 'build', 'current_source_sha256': 'build',
                  'boot_full_sources_sha256': 'full-build', 'current_full_sources_sha256': 'full-build',
                  'fresh': True, 'error': None}
        for name, value in [('observed-state.json', state), ('terminal-state.json', terminal),
                            ('server-identity.json', server)]:
            (folder / name).write_text(json.dumps(value))
        # File-signature fixtures; real render evidence is produced by Playwright.
        for name in ('desktop.png', 'mobile.png'):
            (folder / name).write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        checks = ['visible_local_font', 'real_session', 'step', 'play', 'pause',
                  'measured_neural_activity', 'visible_journal', 'no_page_errors',
                  'mobile_no_overflow', 'external_terminal_verdict', 'server_boot_sources',
                  'server_source_freshness', 'session_identity_binding', 'terminal_receipt_binding']
        semantic = [{'name': name, 'passed': True} for name in checks]
        (folder / 'semantic-checks.json').write_text(json.dumps(semantic))
        payload = {'adjudication': terminal['evaluation'], 'done': True, 'actions': 20,
                   'final_observation': terminal['state']['observation'],
                   'transcript': [{'after': observation} for _ in range(20)],
                   'config': {'seed': 101, 'scenario': 'door_key', 'mode': 'informative'}}
        (folder / 'session-result.json').write_text(json.dumps({'receipt': _seal(payload)}))
        with Recorder(folder / 'session-journal.jsonl') as journal:
            journal.write(kind='panel_session', session_id='demo-1', boot_id=boot)
            for step in range(20):
                journal.write(kind='sandbox_step', step=step)
        evidence = {'session-result.json', 'session-journal.jsonl', 'semantic-checks.json'}
        return {'schema': 'echo5.browser-check.v2', 'valid': True, 'phase': 'development_only',
                'error': None, 'page_errors': [], 'demonstration_success': True, 'demonstration_steps': 20,
                'checks': checks, 'semantic_checks': semantic,
                'evidence_hashes': {name: hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in evidence},
                'artifact_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in folder.iterdir() if p.name not in evidence}}

    def test_browser_receipt_cannot_certify_another_server_or_missing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = self.browser_fixture(folder)
            verify_browser_evidence(folder, report, 'build')
            verify_browser_evidence(folder, report, 'build', 'full-build')
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, report, 'build', 'old-legacy-build')
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, report, 'other-build')
            changed = deepcopy(report)
            changed['checks'].remove('external_terminal_verdict')
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, changed, 'build')
            changed = deepcopy(report)
            del changed['artifact_hashes']['mobile.png']
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, changed, 'build')
            terminal = json.loads((folder / 'terminal-state.json').read_text())
            terminal['evaluation']['actor_claim_used'] = True
            (folder / 'terminal-state.json').write_text(json.dumps(terminal))
            report['artifact_hashes']['terminal-state.json'] = hashlib.sha256((folder / 'terminal-state.json').read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, report, 'build')

    def test_browser_snapshots_require_same_session_and_monotonic_steps(self):
        for kind in ('other_session', 'backwards', 'missing_step', 'error'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                report = self.browser_fixture(folder)
                path = folder / 'terminal-state.json'
                value = json.loads(path.read_text())
                if kind == 'other_session': value['session_id'] = 'demo-2'
                if kind == 'backwards': value['state']['step'] = report['demonstration_steps'] = 1
                if kind == 'missing_step':
                    del value['state']['step']
                    del report['demonstration_steps']
                if kind == 'error': value['error'] = 'failed'
                path.write_text(json.dumps(value))
                report['artifact_hashes'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaises(ValueError):
                    verify_browser_evidence(folder, report, 'build')

    def test_browser_cannot_omit_inherited_build_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = self.browser_fixture(folder)
            path = folder / 'server-identity.json'
            value = json.loads(path.read_text())
            del value['boot_full_sources_sha256']
            path.write_text(json.dumps(value))
            report['artifact_hashes'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                verify_browser_evidence(folder, report, 'build', 'full-build')

    def test_browser_neural_drawing_must_match_the_actual_network(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            report = self.browser_fixture(folder)
            path = folder / 'observed-state.json'
            value = json.loads(path.read_text())
            value['neural']['frames'][0]['potential'][0] += 1
            path.write_text(json.dumps(value))
            report['artifact_hashes'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'neural frames'):
                verify_browser_evidence(folder, report, 'build')

    def receipts(self):
        return [
            {'phase': 'confirmation', 'sources_sha256': 'frozen'}, {'valid': True},
            {'transfer': {'gates': {'closure_candidate': True}},
             'curriculum': {'gates': {'scientific_success': True}},
             'sandbox': {'gates': {'closure': True}},
             'mission': {'gates': {'software_correctness': True}}},
            {'valid': True, 'sources_sha256': 'frozen'},
            {'valid': True, 'sources_sha256': 'frozen'},
            {'config': {'phase': 'confirmation'}},
            {'valid': True, 'gates': {'sitl_valid': True, 'measurements_pass': True,
                                     'independent_audit': True}, 'findings': []},
        ]

    def test_valid_audit_cannot_promote_negative_capability(self):
        receipts = self.receipts()
        self.assertTrue(all(required_gates(*receipts).values()))
        for domain, key in [('transfer', 'closure_candidate'), ('curriculum', 'scientific_success'),
                            ('sandbox', 'closure'), ('mission', 'software_correctness')]:
            modified = deepcopy(receipts)
            modified[2][domain]['gates'][key] = False
            self.assertFalse(all(required_gates(*modified).values()), domain)

    def test_unmeasured_stale_and_development_receipts_fail_closed(self):
        for index in range(7):
            modified = self.receipts()
            modified[index] = {}
            self.assertFalse(all(required_gates(*modified).values()), index)
        modified = self.receipts()
        modified[4]['sources_sha256'] = 'different-build'
        self.assertFalse(all(required_gates(*modified).values()))
        modified = self.receipts()
        modified[0]['phase'] = 'development'
        self.assertFalse(all(required_gates(*modified).values()))

    def test_another_valid_domain_audit_cannot_replace_bound_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hashes = {}
            for domain in DOMAINS:
                (root / domain).mkdir()
                raw = json.dumps({'valid': True, 'result_id': domain}).encode()
                (root / domain / 'audit.json').write_bytes(raw)
                hashes[domain] = hashlib.sha256(raw).hexdigest()
            verify_domain_audits(root, {'domain_audits_sha256': hashes})
            (root / 'transfer/audit.json').write_text('{"valid":true,"result_id":"another-run"}')
            with self.assertRaises(ValueError):
                verify_domain_audits(root, {'domain_audits_sha256': hashes})
            with self.assertRaises(ValueError):
                verify_domain_audits(root, {'valid': True})

    def test_fabricated_green_sitl_without_rows_or_sources_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cfg = {'phase': 'confirmation', 'seed': 861703, 'cases': 6}
            (root / 'configuration.json').write_text(json.dumps(cfg))
            (root / 'sources.json').write_text('{}')
            report = {'schema': 'echo5.sitl.campaign.v1', 'config': cfg}
            audit = {'schema': 'echo5.sitl.audit.v1', 'config': cfg,
                     'valid': True, 'gates': {'sitl_valid': True}}
            sources = {'own': {'files': {'src/actor.py': 'frozen-sha'}}}
            # Only path/config validation is replaced; custody checks stay real.
            with patch('echo5.sitl._config', return_value=cfg):
                with self.assertRaisesRegex(ValueError, 'rows'):
                    verify_sitl_evidence(root, report, audit, sources)
                report['rows'] = audit['rows'] = [{} for _ in range(18)]
                with self.assertRaisesRegex(ValueError, 'source'):
                    verify_sitl_evidence(root, report, audit, sources)

    def test_falsified_sitl_aggregate_cannot_promote_valid_negative_measurements(self):
        audit = self.receipts()[-1]
        with self.assertRaises(ValueError):
            check_sitl_aggregate({'measurements_pass': False}, audit)
        audit['valid'] = audit['gates']['sitl_valid'] = False
        check_sitl_aggregate({'measurements_pass': False}, audit)
        changed = self.receipts()
        changed[-1]['gates']['measurements_pass'] = False
        self.assertFalse(required_gates(*changed)['independent_sitl_validation'])


class ReleaseCampaignEvidenceTests(unittest.TestCase):
    """Synthetic custody fixtures; real closure reconciliation, no scientific runs."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / 'artifacts/campaign'
        self.folder.mkdir(parents=True)
        (self.root / 'docs').mkdir()
        # Replace only the scientific configuration boundary, not its custody
        # checks. These modules have no benchmark/auditor methods to execute.
        module = SimpleNamespace(normalize_config=self.normalize, _config=self.normalize)
        for item in (patch.object(closure, 'ROOT', self.root),
                     patch.object(release, 'ROOT', self.root),
                     patch.object(closure, 'domain_config', side_effect=self.config),
                     patch.object(closure, 'module_for', return_value=module)):
            item.start()
            self.addCleanup(item.stop)
        self.build_fixture()

    @staticmethod
    def config(domain, phase):
        return {'domain': domain, 'phase': phase, 'cases': 1}

    @staticmethod
    def normalize(config):
        return {**config, 'normalized': True}

    def read(self, name):
        return json.loads((self.folder / name).read_text())

    def write(self, name, value):
        (self.folder / name).write_text(json.dumps(value, sort_keys=True) + '\n')

    def build_fixture(self, phase='confirmation'):
        self.campaign = {'campaign_id': 'synthetic-release-campaign', 'phase': phase}
        self.sources = {'own': {'sha256': 'a' * 64}, 'legacy': {}, 'host': {}}
        self.result = {'schema': 'echo5.closure-campaign.v1', **self.campaign,
                       'sources_sha256': self.sources['own']['sha256']}
        self.audit = {'schema': 'echo5.closure-audit.v1',
                      'campaign_id': self.campaign['campaign_id'], 'valid': True, 'error': None,
                      'processes': [{'domain': d, 'exit_code': 0} for d in DOMAINS]}
        gates = {'transfer': {'closure_candidate': True, 'learned_vs_empty_semantic': True},
                 'curriculum': {'scientific_success': True}, 'sandbox': {'closure': True},
                 'mission': {'software_correctness': True}}
        contracts = {}
        for domain in DOMAINS:
            child = self.folder / domain
            child.mkdir(exist_ok=True)
            contract = contracts[domain] = {'schema': 'synthetic-contract', 'domain': domain}
            (self.root / closure.CONTRACTS[domain]).write_text(json.dumps(contract))
            config = self.config(domain, phase)
            report = {'config': self.normalize(config), 'rows': [],
                      'summary': {'cases': 1}, 'gates': gates[domain]}
            # One real hash-chain envelope, with no claimed episode or flight.
            event = {'schema': 'echo45-arc-decisions-v1', 'agent': 'echo5', 'index': 0,
                     'prev': '0' * 64, 'kind': 'synthetic_release_fixture', 'domain': domain}
            event['hash'] = digest(event)
            (child / 'thought.jsonl').write_text(json.dumps(event) + '\n')
            journal = {'events': 1, 'last_hash': event['hash']}
            receipt = {'domain': domain, 'split': phase,
                       'campaign_id': self.campaign['campaign_id'],
                       'config_sha256': digest(config), 'result_config_sha256': digest(report['config']),
                       'contract_sha256': digest(contract), 'result_sha256': digest(report),
                       'journal': journal}
            audited = {'verified' if domain == 'sandbox' else 'valid': True,
                       'summary': deepcopy(report['summary']), 'gates': deepcopy(report['gates'])}
            if domain == 'curriculum':
                audited['report_sha256'] = digest(report)
            wrapper = {'result': audited, 'domain': domain, 'split': phase,
                       'campaign_id': self.campaign['campaign_id'],
                       'result_sha256': digest(report), 'config_sha256': digest(config),
                       'result_config_sha256': digest(report['config']),
                       'receipt_sha256': digest(receipt), 'journal': journal}
            for name, value in (('config', config), ('result', report),
                                ('receipt', receipt), ('audit', wrapper)):
                self.write(f'{domain}/{name}.json', value)
        self.write('campaign.json', self.campaign)
        self.write('contracts.json', contracts)
        self.write('sources.json', self.sources)
        self.write('processes.json', [{'domain': d, 'exit_code': 0} for d in DOMAINS])
        with zipfile.ZipFile(self.folder / 'sources.zip', 'w'):
            pass
        self.refresh_links()

    def refresh_links(self, omitted=()):
        """Rehash the package without repairing domain receipts/audit contents."""
        reports = {d: self.read(f'{d}/result.json') for d in DOMAINS}
        self.result['domain_results'] = {d: digest(r) for d, r in reports.items()}
        self.result['gates'] = {d: deepcopy(r['gates']) for d, r in reports.items()}
        self.write('result.json', self.result)
        self.manifest = {str(p.relative_to(self.folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(self.folder.rglob('*')) if p.is_file()
                         and p.name not in ('manifest.json', 'audit.json')
                         and str(p.relative_to(self.folder)) not in omitted}
        self.write('manifest.json', self.manifest)
        self.audit.update(manifest_sha256=digest(self.manifest),
                          domain_gates=deepcopy(self.result['gates']),
                          domain_audits_sha256={d: hashlib.sha256(
                              (self.folder / d / 'audit.json').read_bytes()).hexdigest() for d in DOMAINS})
        self.write('audit.json', self.audit)

    def replace_report(self, domain, report):
        """Rebind outer identities, deliberately retain the auditor's verdict."""
        self.write(f'{domain}/result.json', report)
        receipt = self.read(f'{domain}/receipt.json')
        receipt['result_sha256'] = digest(report)
        self.write(f'{domain}/receipt.json', receipt)
        wrapper = self.read(f'{domain}/audit.json')
        wrapper.update(result_sha256=digest(report), receipt_sha256=digest(receipt))
        self.write(f'{domain}/audit.json', wrapper)
        self.refresh_links()

    def verify(self):
        return release.verify_campaign_evidence(
            self.folder, self.result, self.audit, self.manifest, self.sources)

    def assert_rejected_by_finalizer(self, message):
        output = self.root / 'artifacts/final'
        # Rejection must occur at the real campaign boundary, before unrelated
        # source scanning, browser/native verification or SITL evaluation.
        with patch.object(release, 'current_release_sources', side_effect=AssertionError(
                'Invalid campaign reached downstream validation')):
            with self.assertRaisesRegex(ValueError, message):
                release.finalize(self.folder, self.root / 'artifacts/checks',
                                 self.root / 'artifacts/browser', self.root / 'artifacts/sitl', output)
        self.assertFalse(output.exists())
        self.assertFalse((self.root / 'artifacts/closure-latest.json').exists())

    def test_complete_synthetic_custody_accepts_matching_audits_without_replay(self):
        reports = self.verify()
        self.assertEqual(set(reports), {'transfer', 'curriculum', 'sandbox', 'mission'})
        self.assertTrue(reports['transfer']['gates']['closure_candidate'])
        self.assertTrue(reports['sandbox']['gates']['closure'])

    def test_valid_negative_audit_cannot_certify_rehashed_positive_report(self):
        report = self.read('transfer/result.json')
        report['gates'].update(closure_candidate=False, learned_vs_empty_semantic=False)
        wrapper = self.read('transfer/audit.json')
        wrapper['result']['gates'] = deepcopy(report['gates'])
        self.write('transfer/audit.json', wrapper)
        self.replace_report('transfer', report)
        reports = self.verify()
        self.assertFalse(reports['transfer']['gates']['closure_candidate'])
        self.assertTrue(self.audit['valid'])
        gates = required_gates(self.result, self.audit, reports, {}, {}, {}, {})
        self.assertFalse(gates['structural_transfer_memory_hierarchy'])
        self.assertTrue(gates['independent_domain_audit'])
        # Update all outer hashes/identities; the audited scientific gate stays
        # negative, so stale-byte detection alone cannot catch this promotion.
        report['gates']['closure_candidate'] = True
        self.replace_report('transfer', report)
        self.assert_rejected_by_finalizer('independently recomputed gates')

    def test_development_cannot_be_relabelled_as_confirmation(self):
        self.build_fixture('development')
        self.verify()
        self.result['phase'] = 'confirmation'
        self.refresh_links()
        self.assert_rejected_by_finalizer('campaign phase')
        # Relabelling the campaign header too cannot change the requested and
        # normalized configurations still belonging to development.
        self.campaign['phase'] = 'confirmation'
        self.write('campaign.json', self.campaign)
        self.refresh_links()
        self.assert_rejected_by_finalizer('requested config')

    def test_every_required_receipt_remains_required_after_rehashing(self):
        names = ['campaign.json', 'contracts.json', 'processes.json'] + [
            f'{domain}/{name}' for domain in DOMAINS
            for name in ('config.json', 'result.json', 'receipt.json', 'thought.jsonl')]
        for name in names:
            with self.subTest(file=name):
                path = self.folder / name
                raw = path.read_bytes()
                self.refresh_links(omitted={name})
                self.assert_rejected_by_finalizer('Incomplete manifest')
                try:
                    path.unlink()
                    self.assert_rejected_by_finalizer('Incomplete manifest')
                finally:
                    path.write_bytes(raw)
                    self.refresh_links()

    def test_domain_audit_envelopes_and_recomputed_values_are_bound(self):
        for domain in DOMAINS:
            name = f'{domain}/audit.json'
            original = self.read(name)
            replacements = [('campaign_id', 'another-campaign'), ('domain', 'another-domain'),
                            ('split', 'development'), ('result_sha256', 'wrong-result'),
                            ('config_sha256', 'wrong-config'), ('result_config_sha256', 'wrong-normalized-config'),
                            ('receipt_sha256', 'wrong-receipt'), ('journal', {'events': 0})]
            for field, value in replacements:
                with self.subTest(domain=domain, field=field):
                    self.write(name, {**original, field: value})
                    self.refresh_links()
                    self.assert_rejected_by_finalizer('audit.' + field)
                    self.write(name, original)
            for field in ('summary', 'gates'):
                with self.subTest(domain=domain, result=field):
                    changed = deepcopy(original)
                    changed['result'][field] = {}
                    self.write(name, changed)
                    self.refresh_links()
                    self.assert_rejected_by_finalizer('independently recomputed ' + field)
                    self.write(name, original)
            self.refresh_links()

    def test_aggregate_audit_belongs_to_the_same_campaign(self):
        self.audit['campaign_id'] = 'another-campaign'
        self.refresh_links()
        self.assert_rejected_by_finalizer('audit campaign identity')

    def test_optional_auditor_report_hash_is_reconciled(self):
        wrapper = self.read('curriculum/audit.json')
        wrapper['result']['report_sha256'] = 'another-report'
        self.write('curriculum/audit.json', wrapper)
        self.refresh_links()
        self.assert_rejected_by_finalizer('auditor report hash')
