from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch
import zipfile

from echo5 import closure
from echo5.closure import verify_manifest, verify_archive, write_json
from echo5.evaluation import digest


class ClosureCustodyTests(unittest.TestCase):
    def test_manifest_rejects_modified_missing_and_escaping_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / 'run'
            child.mkdir()
            (child / 'result.json').write_bytes(b'{"success":false}')
            sha = hashlib.sha256((child / 'result.json').read_bytes()).hexdigest()
            manifest = {'result.json': sha}
            verify_manifest(child, manifest, {'result.json'})
            with self.assertRaises(ValueError):
                verify_manifest(child, manifest, {'audit.json'})
            (root / 'private.json').write_bytes(b'{"success":false}')
            with self.assertRaises(ValueError):
                verify_manifest(child, {'../private.json': sha})
            (child / 'result.json').write_bytes(b'{"success":true}')
            with self.assertRaises(ValueError):
                verify_manifest(child, manifest)

    def test_source_archive_is_checked_by_bytes_not_names_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipts = {key: {'files': {}} for key in ('own', 'legacy', 'host')}
            receipts['own']['files']['actor.py'] = hashlib.sha256(b'good').hexdigest()
            with zipfile.ZipFile(root / 'sources.zip', 'w') as z:
                z.writestr('simulation/actor.py', b'good')
            verify_archive(root, receipts)
            with zipfile.ZipFile(root / 'sources.zip', 'w') as z:
                z.writestr('simulation/actor.py', b'bad')
            with self.assertRaises(ValueError):
                verify_archive(root, receipts)

    def test_measurements_are_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.json'
            write_json(path, {'first': True})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_json(path, {'replacement': True})
            self.assertEqual(before, path.read_bytes())


class ClosureReconciliationTests(unittest.TestCase):
    """Tiny synthetic receipts: no actor, replay engine or subprocess runs."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folder = self.root / 'artifacts/run'
        self.folder.mkdir(parents=True)
        (self.root / 'config').mkdir()
        self.campaign = {'campaign_id': 'test-campaign', 'phase': 'development'}
        self.config = {'phase': 'development', 'cases': 1}
        self.journal = {'events': 0, 'last_hash': '0' * 64}
        self.sources = {'own': {'sha256': 'a' * 64, 'files': {}},
                        'legacy': {'files': {}}, 'host': {'files': {}}}
        self.reports, self.modules, contracts = {}, {}, {}
        for domain in closure.DOMAINS:
            child = self.folder / domain
            child.mkdir()
            contracts[domain] = {'domain': domain}
            write_json(self.root / closure.CONTRACTS[domain], contracts[domain])
            report = {'config': {**self.config, 'normalized': True},
                      'rows': [], 'summary': {'cases': 1}, 'gates': {'success': False}}
            self.reports[domain] = report
            write_json(child / 'config.json', self.config)
            write_json(child / 'result.json', report)
            (child / 'thought.jsonl').write_text('')
            write_json(child / 'receipt.json', {
                'domain': domain, 'split': 'development', 'campaign_id': 'test-campaign',
                'config_sha256': digest(self.config), 'result_config_sha256': digest(report['config']),
                'contract_sha256': digest(contracts[domain]), 'result_sha256': digest(report),
                'journal': self.journal})
            auditor = Mock(return_value={'valid': True, 'summary': deepcopy(report['summary']),
                                         'gates': deepcopy(report['gates'])})
            name = 'audit_report' if domain in ('mission', 'curriculum') else 'audit_benchmark'
            self.modules[domain] = SimpleNamespace(
                normalize_config=lambda config: {**config, 'normalized': True},
                _config=lambda config: {**config, 'normalized': True},
                run_benchmark=Mock(), **{name: auditor})
        self.result = {**self.campaign, 'sources_sha256': self.sources['own']['sha256'],
                       'domain_results': {d: digest(r) for d, r in self.reports.items()},
                       'gates': {d: deepcopy(r['gates']) for d, r in self.reports.items()}}
        for name, value in {'campaign': self.campaign, 'contracts': contracts, 'sources': self.sources,
                            'result': self.result, 'processes': [
                                {'domain': d, 'exit_code': 0} for d in closure.DOMAINS]}.items():
            write_json(self.folder / (name + '.json'), value)
        with zipfile.ZipFile(self.folder / 'sources.zip', 'x'):
            pass
        for item in (patch.object(closure, 'ROOT', self.root),
                     patch.object(closure, 'domain_config', return_value=self.config),
                     patch.object(closure, 'module_for', side_effect=self.modules.__getitem__)):
            item.start()
            self.addCleanup(item.stop)

    def manifest(self):
        manifest = {str(path.relative_to(self.folder)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in self.folder.rglob('*') if path.is_file()}
        write_json(self.folder / 'manifest.json', manifest)
        return manifest

    def test_reconciliation_rejects_aggregate_and_receipt_relabelling(self):
        self.assertEqual(closure._reconcile_campaign(
            self.folder, self.campaign, self.result, self.sources), self.reports)
        for key, replacement in [('gates', {}), ('domain_results', {}),
                                 ('campaign_id', 'other'), ('sources_sha256', 'wrong')]:
            with self.subTest(aggregate=key), self.assertRaises(ValueError):
                closure._reconcile_campaign(self.folder, self.campaign,
                                            {**self.result, key: replacement}, self.sources)
        for name, key, replacement in [('config', 'cases', 2), ('result', 'config', self.config),
                                       ('receipt', 'result_sha256', 'wrong'),
                                       ('receipt', 'config_sha256', 'wrong'),
                                       ('receipt', 'contract_sha256', 'wrong'),
                                       ('receipt', 'journal', {'events': 99})]:
            path = self.folder / 'mission' / (name + '.json')
            original = json.loads(path.read_text())
            with self.subTest(file=name, field=key):
                write_json(path, {**original, key: replacement}, replace=True)
                with self.assertRaises(ValueError):
                    closure._reconcile_campaign(self.folder, self.campaign, self.result, self.sources)
                write_json(path, original, replace=True)

    def test_mission_requires_explicit_audit_report_without_producer_fallback(self):
        module = self.modules['mission']
        del module.audit_report
        module.audit_benchmark = Mock()
        with self.assertRaisesRegex(ValueError, 'mission.audit_report'):
            closure.audit_worker('mission', self.folder / 'mission')
        module.run_benchmark.assert_not_called()
        module.audit_benchmark.assert_not_called()
        self.assertFalse((self.folder / 'mission/audit.json').exists())
        self.assertTrue((self.folder / 'mission/audit-error.json').is_file())

    def test_auditor_must_return_recomputed_summary_and_gates(self):
        for audit in ({'valid': True}, {'valid': True, 'summary': {'cases': 1}},
                      {'valid': True, 'summary': {'cases': 1}, 'gates': {'success': True}}):
            with self.subTest(audit=audit), self.assertRaises(ValueError):
                closure._validate_domain_audit('mission', self.reports['mission'], audit)

    def test_campaign_audit_binds_raw_audit_hashes_and_preserves_negative_gates(self):
        manifest = self.manifest()

        def invoke(domain, phase, folder, *, audit):
            self.assertTrue(audit)
            closure.audit_worker(domain, folder / domain)
            return {'domain': domain, 'exit_code': 0}

        with patch.object(closure, '_invoke', side_effect=invoke), \
                patch.object(closure, 'preserve', return_value={'unchanged': True}):
            self.assertEqual(closure.audit_campaign(self.folder, workers=1), 0)
        audit = json.loads((self.folder / 'audit.json').read_text())
        self.assertTrue(audit['valid'])
        self.assertEqual(audit['domain_gates'], self.result['gates'])
        self.assertEqual(audit['manifest_sha256'], digest(manifest))
        self.assertEqual(audit['domain_audits_sha256'], {
            d: hashlib.sha256((self.folder / d / 'audit.json').read_bytes()).hexdigest()
            for d in closure.DOMAINS})
        self.modules['transfer'].audit_benchmark.assert_called_once_with(self.reports['transfer'], replay=True)
        self.modules['mission'].audit_report.assert_called_once_with(self.reports['mission'])
        for module in self.modules.values():
            module.run_benchmark.assert_not_called()
        latest = json.loads((self.root / 'artifacts/closure-latest.json').read_text())
        self.assertEqual(latest['campaign_id'], self.campaign['campaign_id'])
        self.assertTrue(latest['audit_valid'])
        self.assertFalse(latest['release_eligible'])
        verify_manifest(self.folder, manifest)
        verify_manifest(self.folder, {f'{d}/audit.json': sha
                                      for d, sha in audit['domain_audits_sha256'].items()})
        path = self.folder / 'mission/audit.json'
        raw = path.read_bytes()
        path.write_bytes(raw + b' ')
        with self.assertRaisesRegex(ValueError, 'mission/audit.json'):
            verify_manifest(self.folder, manifest)
        path.write_bytes(raw)
        wrapper = json.loads(raw)
        write_json(path, {**wrapper, 'receipt_sha256': 'wrong'}, replace=True)
        with self.assertRaisesRegex(ValueError, 'receipt_sha256'):
            closure._reconcile_domain_audits(self.folder, self.campaign, self.reports)
        path.write_bytes(raw)
        del audit['domain_audits_sha256']['mission']
        write_json(self.folder / 'audit.json', audit, replace=True)
        with self.assertRaisesRegex(ValueError, 'every domain audit hash'):
            verify_manifest(self.folder, manifest)

    def test_audit_rejects_self_consistent_manifest_with_false_aggregate_gates(self):
        write_json(self.folder / 'result.json', {**self.result, 'gates': {}}, replace=True)
        self.manifest()
        with patch.object(closure, '_invoke') as invoke, \
                patch.object(closure, 'preserve', return_value={'unchanged': True}):
            self.assertEqual(closure.audit_campaign(self.folder), 1)
        invoke.assert_not_called()
        audit = json.loads((self.folder / 'audit.json').read_text())
        self.assertFalse(audit['valid'])
        self.assertIn('aggregate domain gates', audit['error']['message'])
        latest = json.loads((self.root / 'artifacts/closure-latest.json').read_text())
        self.assertEqual(latest['status'], 'audit_failed')
        self.assertEqual(latest['gates'], {})


class ClosureFailureTests(unittest.TestCase):
    def test_start_and_freeze_error_replace_stale_success_with_new_campaign_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'artifacts').mkdir()
            latest_path = root / 'artifacts/closure-latest.json'
            write_json(latest_path, {'campaign_id': 'old', 'status': 'closure_verified',
                                     'release_eligible': True, 'gates': {'passed': True}})

            def fail_freeze(folder):
                latest = json.loads(latest_path.read_text())
                self.assertEqual(latest['status'], 'running')
                self.assertNotEqual(latest['campaign_id'], 'old')
                self.assertEqual(latest['gates'], {})
                raise ImportError('missing instrument')

            folder = root / 'artifacts/new'
            with patch.object(closure, 'ROOT', root), patch.object(closure, 'freeze', side_effect=fail_freeze):
                self.assertEqual(closure.run_campaign(folder), 1)
            latest = json.loads(latest_path.read_text())
            self.assertEqual(latest['status'], 'instrument_error')
            self.assertEqual(latest['campaign_id'], json.loads((folder / 'campaign.json').read_text())['campaign_id'])
            self.assertEqual(latest['gates'], {})
            self.assertFalse(latest['audit_valid'])
            self.assertFalse(latest['release_eligible'])

    def test_worker_records_config_and_import_exceptions(self):
        for error in (ValueError('bad config'), ImportError('missing module')):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'worker'
                with patch.object(closure, 'domain_config', side_effect=error):
                    with self.assertRaises(type(error)):
                        closure.worker('mission', 'development', folder)
                receipt = json.loads((folder / 'instrument-error.json').read_text())
                self.assertEqual(receipt['type'], type(error).__name__)
                self.assertEqual(json.loads((folder / 'status.json').read_text())['phase'], 'instrument_error')

    def test_missing_executable_is_a_failed_launch_receipt(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(closure.subprocess, 'Popen', side_effect=FileNotFoundError('missing python')) as launch:
            result = closure.run_process(['absent'], Path(tmp) / 'launch.log', cwd=tmp, timeout=1)
        self.assertEqual(result['exit_code'], 127)
        self.assertIn('FileNotFoundError', result['error'])
        self.assertFalse(result['timed_out'])
        self.assertTrue(launch.call_args.kwargs['start_new_session'])

    def test_timeout_kills_owned_group_even_when_leader_exits_after_term(self):
        process = Mock(pid=12345)
        process.wait.side_effect = [subprocess.TimeoutExpired(['worker'], 1), 0, 0]
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(closure.subprocess, 'Popen', return_value=process), \
                patch.object(closure.os, 'killpg') as kill:
            result = closure.run_process(['worker'], Path(tmp) / 'timeout.log', cwd=tmp, timeout=1)
        self.assertEqual(result['exit_code'], 124)
        self.assertTrue(result['timed_out'])
        self.assertTrue(result['process_group_cleanup_attempted'])
        self.assertEqual(kill.call_args_list, [call(12345, signal.SIGTERM), call(12345, signal.SIGKILL)])

    def test_checks_write_invalid_receipts_for_launch_and_freeze_failures(self):
        script = Path(closure.__file__).resolve().parents[2] / 'scripts/checks.py'
        spec = importlib.util.spec_from_file_location('closure_checks_fixture', script)
        checks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checks)
        sources = {'own': {'sha256': 'a' * 64}}
        for freeze_error in (None, ImportError('missing instrument')):
            with self.subTest(freeze_error=freeze_error), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / 'checks'
                with patch.object(checks, 'ROOT', Path(tmp)), \
                        patch.object(closure, 'freeze', return_value=sources, side_effect=freeze_error), \
                        patch.object(closure, 'preserve', return_value={'unchanged': True}), \
                        patch.object(closure, 'run_process', return_value={
                            'exit_code': 127, 'error': 'FileNotFoundError'}) as run, \
                        patch.object(checks.sys, 'path', list(checks.sys.path)):
                    self.assertEqual(checks.main(folder), 1)
                receipt = json.loads((folder / 'result.json').read_text())
                self.assertFalse(receipt['valid'])
                self.assertEqual(run.call_count, 0 if freeze_error else 4)
                self.assertEqual(receipt['sources_sha256'], None if freeze_error else sources['own']['sha256'])
                if freeze_error:
                    self.assertEqual(receipt['error']['type'], 'ImportError')
