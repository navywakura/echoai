import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path

from echo5.control import SessionManager, SourceIdentity, SourceChanged, make_server
from echo5.evaluation import source_snapshot
from echo5.trace import verify_journal


class DeterministicSession:
    """Protocol fixture; actual MiniGrid integration is covered by test_sandbox."""
    def __init__(self, spec, journal=None):
        if spec.get('bad'):
            raise ValueError('invalid mission')
        self.n = 0
        self.journal = journal
        self.closed = False

    def step(self):
        self.n += 1
        self.journal.write(kind='observed_transition', step=self.n)

    def snapshot(self):
        return {'step': self.n, 'observation': {'x': self.n}, 'done': self.n == 2}

    def close(self):
        self.closed = True

    def result(self):
        if not self.snapshot()['done']:
            raise RuntimeError('terminal receipt requested before completion')
        return {'receipt': {'payload': {'adjudication': {
            'success': True, 'actor_claim_used': False, 'source': 'protocol_fixture'}}}}


def fixture_reader(root):
    """Real file hashing over an isolated source tree; never edit live files."""
    return lambda: {'own': source_snapshot(root, ['source.py'])}


class SourceIdentityTests(unittest.TestCase):
    def test_boot_identity_does_not_refresh_after_change_or_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'source.py'
            path.write_text('original\n')
            identity = SourceIdentity(reader=fixture_reader(root))
            first = identity.snapshot()
            self.assertTrue(first['fresh'])
            path.write_text('different\n')
            changed = identity.snapshot()
            self.assertFalse(changed['fresh'])
            self.assertEqual(changed['boot_source_sha256'], first['boot_source_sha256'])
            self.assertNotEqual(changed['current_source_sha256'], first['boot_source_sha256'])
            path.write_text('original\n')
            self.assertFalse(identity.snapshot()['fresh'])
            with self.assertRaises(SourceChanged):
                identity.require_fresh()

    def test_new_source_and_unreadable_source_require_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'source.py').write_text('original\n')
            identity = SourceIdentity(reader=lambda: {'own': source_snapshot(root, ['.'])})
            (root / 'added.py').write_text('new module\n')
            self.assertFalse(identity.snapshot()['fresh'])
            identity = SourceIdentity(reader=fixture_reader(root))
            (root / 'source.py').unlink()
            state = identity.snapshot()
            self.assertFalse(state['fresh'])
            self.assertIsNone(state['current_source_sha256'])
            self.assertIn('FileNotFoundError', state['error'])

    def test_browser_rejects_wrong_boot_stale_sources_and_restart(self):
        # Load the checker without importing Playwright or launching a browser.
        path = Path(__file__).resolve().parents[1] / 'scripts/check_browser.py'
        spec = importlib.util.spec_from_file_location('echo5_browser_identity_check', path)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'source.py').write_text('original\n')
            reader = fixture_reader(root)
            identity = SourceIdentity(reader=reader)
            expected = reader()
            good = identity.snapshot()
            checker.validate_identity(good, expected)
            bad = dict(good, boot_source_sha256='0' * 64)
            with self.assertRaises(ValueError):
                checker.validate_identity(bad, expected)
            with self.assertRaises(ValueError):
                checker.validate_identity(dict(good, fresh=False), expected)
            with self.assertRaises(ValueError):
                checker.validate_identity(dict(good, boot_id='another-boot'), expected, good['boot_id'])
            with self.assertRaises(ValueError):
                checker.validate_identity(dict(good, current_source_sha256='0' * 64), expected)
            with self.assertRaises(ValueError):
                checker.validate_identity(dict(good, boot_full_sources_sha256='0' * 64), expected)
            # Identical file hashes with different declared scope are not the same receipt.
            altered = json.loads(json.dumps(expected))
            altered['own']['folders'] = ['different_scope']
            with self.assertRaises(ValueError):
                checker.validate_identity(good, altered)

    def test_full_identity_detects_legacy_changes_with_identical_own_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('own.py', 'legacy.py', 'host.py'):
                (root / name).write_text(name + '\n')
            reader = lambda: {name: source_snapshot(root, [name + '.py'])
                              for name in ('own', 'legacy', 'host')}
            identity = SourceIdentity(reader=reader)
            first = identity.snapshot()
            (root / 'legacy.py').write_text('changed legacy module\n')
            changed = identity.snapshot()
            self.assertEqual(changed['boot_source_sha256'], changed['current_source_sha256'])
            self.assertEqual(changed['boot_full_sources_sha256'], first['boot_full_sources_sha256'])
            self.assertNotEqual(changed['current_full_sources_sha256'], first['boot_full_sources_sha256'])
            self.assertFalse(changed['fresh'])


class DiagnosticTests(unittest.TestCase):
    def test_opt_out_never_initializes_probe_or_changes_actor_spec(self):
        captured = []
        def factory(spec, journal):
            captured.append(spec)
            return DeterministicSession(spec, journal)
        def forbidden_probe():
            self.fail('disabled diagnostic was initialized')
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, factory, neural_factory=forbidden_probe)
            try:
                state = m.create({'diagnostics': {'neural': False}})
                self.assertEqual(captured, [{}])
                self.assertIsNone(state['neural'])
                self.assertEqual(state['diagnostic']['status'], 'disabled')
                self.assertFalse(state['diagnostic']['enabled'])
                m.command('step')
                terminal = m.command('step')
                self.assertTrue(terminal['evaluation']['success'])
                self.assertIsNone(terminal['error'])
            finally:
                m.close()

    def test_probe_initialization_failure_is_recorded_without_stopping_actor(self):
        def broken_probe():
            raise RuntimeError('diagnostic unavailable')
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, DeterministicSession, neural_factory=broken_probe)
            try:
                initial = m.create({})
                self.assertIsNone(initial['error'])
                self.assertIsNone(initial['neural'])
                self.assertEqual(initial['diagnostic']['status'], 'error')
                self.assertIn('diagnostic unavailable', initial['diagnostic']['error'])
                m.command('step')
                final = m.command('step')
                self.assertTrue(final['state']['done'])
                self.assertTrue(final['evaluation']['success'])
                failures = [e for e in final['events'] if e['kind'] == 'neural_diagnostic_error']
                self.assertEqual(len(failures), 1)
                self.assertEqual(failures[0]['stage'], 'initialize')
                self.assertEqual(failures[0]['step'], 0)
            finally:
                m.close()

    def test_terminal_result_is_on_disk_before_probe_failure_and_stale_frames_clear(self):
        with tempfile.TemporaryDirectory() as d:
            observed_terminal = []
            class Probe:
                def observe(self, observation):
                    if observation['x'] == 2:
                        stored = json.loads((m.folder / 'result.json').read_text())
                        observed_terminal.append(stored['receipt']['payload']['adjudication'])
                        state = json.loads((m.folder / 'state.json').read_text())
                        if not state['state']['done'] or not state['evaluation']['success']:
                            raise AssertionError('terminal state was not persisted before diagnostics')
                        raise RuntimeError('measured probe failure')
                    return {'drives_policy': False, 'observation_x': observation['x']}
            m = SessionManager(d, DeterministicSession, neural_factory=Probe)
            try:
                m.create({})
                m.command('step')
                final = m.command('step')
                self.assertEqual(len(observed_terminal), 1)
                self.assertFalse(observed_terminal[0]['actor_claim_used'])
                self.assertTrue(final['evaluation']['success'])
                self.assertIsNone(final['neural'])
                self.assertIsNone(final['error'])
                self.assertEqual(final['diagnostic']['error'], 'RuntimeError: measured probe failure')
                failures = [e for e in final['events'] if e['kind'] == 'neural_diagnostic_error']
                self.assertEqual(failures[0]['step'], 2)
                self.assertEqual(failures[0]['stage'], 'observe')
                self.assertFalse(failures[0]['session_continues'])
                self.assertTrue(failures[0]['terminal_result_persisted'])
                self.assertTrue(m.result()['receipt']['payload']['adjudication']['success'])
            finally:
                m.close()

    def test_initial_terminal_state_also_gets_receipt_without_a_step(self):
        class AlreadyDone(DeterministicSession):
            def __init__(self, spec, journal=None):
                super().__init__(spec, journal)
                self.n = 2
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, AlreadyDone)
            try:
                final = m.create({'diagnostics': {'neural': False}})
                self.assertTrue(final['evaluation']['success'])
                self.assertTrue((m.folder / 'result.json').is_file())
            finally:
                m.close()

    def test_invalid_diagnostic_setting_preserves_existing_session(self):
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, DeterministicSession)
            try:
                first = m.create({'diagnostics': {'neural': False}})
                for invalid in ({'neural': 'false'}, {'unknown': True}, None):
                    with self.assertRaises(ValueError):
                        m.create({'diagnostics': invalid})
                    self.assertEqual(m.snapshot()['session_id'], first['session_id'])
            finally:
                m.close()

    def test_source_drift_stops_steps_and_requires_new_server(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'source.py'
            path.write_text('original\n')
            identity = SourceIdentity(reader=fixture_reader(root))
            m = SessionManager(root / 'sessions', DeterministicSession, identity=identity)
            try:
                initial = m.create({'diagnostics': {'neural': False}})
                self.assertEqual(initial['boot_id'], identity.boot_id)
                path.write_text('changed\n')
                with self.assertRaises(SourceChanged):
                    m.command('step')
                self.assertEqual(m.snapshot()['state']['step'], 0)
                self.assertFalse(m.snapshot()['playing'])
                path.write_text('original\n')
                with self.assertRaises(SourceChanged):
                    m.create({'diagnostics': {'neural': False}})
            finally:
                m.close()


class ControlTests(unittest.TestCase):
    def test_pause_step_terminal_and_observer_do_not_change_actor(self):
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, DeterministicSession)
            try:
                initial = m.create({})
                self.assertEqual(initial['state']['step'], 0)
                result = m.command('step', initial['session_id'])
                self.assertEqual(result['state']['step'], 1)
                self.assertFalse(result['neural']['drives_policy'])
                result['state']['step'] = 90
                self.assertEqual(m.snapshot()['state']['step'], 1)
                m.command('step')
                m.command('step')
                self.assertEqual(m.snapshot()['state']['step'], 2)
                with self.assertRaises(ValueError):
                    m.command('play', 'stale_session')
                folder = m.folder
            finally:
                m.close()
            self.assertGreater(verify_journal(folder / 'thought.jsonl')['events'], 0)
            self.assertFalse(json.loads((folder / 'state.json').read_text())['actor_receives_neural_diagnostic'])

    def test_http_requires_same_origin_and_token_and_has_no_file_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, DeterministicSession)
            server = make_server(m, port=0)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            port = server.server_port
            def request(path, method='GET', value=None, headers=None):
                c = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                body = json.dumps(value) if value is not None else None
                h = {'Content-Type': 'application/json', **(headers or {})}
                c.request(method, path, body=body, headers=h)
                r = c.getresponse()
                result = r.status, r.read()
                c.close()
                return result
            try:
                code, raw = request('/api/identity')
                self.assertEqual(code, 200)
                identity = json.loads(raw)
                self.assertEqual(identity['schema'], 'echo5.control.source-identity.v1')
                self.assertTrue(identity['fresh'])
                self.assertEqual(identity['boot_source_sha256'], identity['current_source_sha256'])
                self.assertEqual(identity['boot_full_sources_sha256'], identity['current_full_sources_sha256'])
                self.assertEqual(request('/')[0], 200)
                self.assertEqual(request('/../../CLAUDE.md')[0], 404)
                self.assertEqual(request('/api/session', 'POST', {})[0], 403)
                self.assertEqual(request('/api/session', 'POST', {}, {'X-Echo-Token': m.token, 'Origin': 'https://evil.example'})[0], 403)
                self.assertEqual(request('/api/state', headers={'Host': 'evil.example'})[0], 403)
                self.assertEqual(request('/api/session', 'POST', {}, {'X-Echo-Token': m.token})[0], 200)
                self.assertEqual(json.loads(request('/api/state')[1])['boot_id'], identity['boot_id'])
                self.assertEqual(request('/api/result')[0], 409)
                self.assertEqual(request('/api/control', 'POST', {'action': 'shell'}, {'X-Echo-Token': m.token})[0], 400)
            finally:
                server.shutdown()
                server.server_close()
                t.join(timeout=2)
                m.close()

    def test_http_source_drift_returns_409_and_preserves_boot_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'source.py'
            source.write_text('original\n')
            identity = SourceIdentity(reader=fixture_reader(root))
            m = SessionManager(root / 'sessions', DeterministicSession, identity=identity)
            server = make_server(m, port=0)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            def get(path):
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                try:
                    connection.request('GET', path)
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    connection.close()
            try:
                initial = get('/api/identity')[1]
                source.write_text('changed\n')
                status, state = get('/api/state')
                self.assertEqual(status, 409)
                self.assertTrue(state['restart_required'])
                status, changed = get('/api/identity')
                self.assertEqual(status, 200)
                self.assertFalse(changed['fresh'])
                self.assertEqual(changed['boot_id'], initial['boot_id'])
                self.assertEqual(changed['boot_source_sha256'], initial['boot_source_sha256'])
            finally:
                server.shutdown()
                server.server_close()
                t.join(timeout=2)
                m.close()

    def test_bind_to_public_interfaces_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m = SessionManager(d, DeterministicSession)
            try:
                with self.assertRaises(ValueError):
                    make_server(m, host='0.0.0.0', port=0)
            finally:
                m.close()
