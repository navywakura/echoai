"""Loopback control and passive evidence viewer; no LLM or shell execution."""
from collections import deque
import copy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit, parse_qs

from .trace import Recorder
from .distribution import CORE_FILES

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).with_name('web')


def source_receipts():
    """Use the same source scope and digest format as closure.freeze, without writes.

    Browser validation compares every group with its independently frozen copy.
    A change to the closure scope therefore fails binding until both agree.
    """
    from .evaluation import source_snapshot
    return {
        'own': source_snapshot(ROOT, ['src', 'scripts', 'tests', 'config', 'pyproject.toml',
                                     '.python-version', 'requirements-sandbox.lock'],
                               suffixes=('.py', '.json', '.js', '.css', '.html', '.toml', '.lock', '')),
        'legacy': source_snapshot(ROOT.parent, ['seed', 'echo_arc', 'echo4', 'nexus0', '__init__.py'],
                                  suffixes=('.py', '.json', '.bnf', '.txt')),
        'host': source_snapshot(ROOT.parent, CORE_FILES),
    }


# Captured once when this control module is loaded, never refreshed by a reset.
# Serve this code from a fresh isolated process after applying new sources.
_BOOT_SOURCES = source_receipts()


class SourceChanged(ValueError):
    pass


class SourceIdentity:
    """Immutable boot identity and a latched, read-only freshness check."""
    def __init__(self, reader=None):
        from .evaluation import digest
        self.reader = reader or source_receipts
        self.boot = copy.deepcopy(_BOOT_SOURCES if reader is None else reader())
        self.boot_full_sha256 = digest(self.boot)
        self.boot_id = secrets.token_hex(16)
        self.started_ns = time.time_ns()
        self.lock = threading.RLock()
        self.failure = None

    def snapshot(self):
        from .evaluation import digest
        with self.lock:
            current = {}
            current_full_sha256 = None
            try:
                receipts = self.reader()
                current = {k: v['sha256'] for k, v in receipts.items()}
                current_full_sha256 = digest(receipts)
                if receipts != self.boot:
                    self.failure = self.failure or 'Sources changed since server boot; restart required'
            except Exception as exc:
                self.failure = self.failure or f'{type(exc).__name__}: {exc}; restart required'
            boot = {k: v['sha256'] for k, v in self.boot.items()}
            return {'schema': 'echo5.control.source-identity.v1',
                    'boot_id': self.boot_id, 'pid': os.getpid(),
                    'started_ns': self.started_ns, 'checked_ns': time.time_ns(),
                    'boot_source_sha256': boot['own'],
                    'current_source_sha256': current.get('own'),
                    'boot_full_sources_sha256': self.boot_full_sha256,
                    'current_full_sources_sha256': current_full_sha256,
                    'boot_source_groups': boot, 'current_source_groups': current,
                    'fresh': self.failure is None, 'error': self.failure}

    def require_fresh(self):
        identity = self.snapshot()
        if not identity['fresh']:
            raise SourceChanged(identity['error'])
        return identity


def neural_probe():
    # Opting out must not import or initialize the optional diagnostic.
    from .neural_observer import NeuralObserver
    return NeuralObserver()


def portable(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


class EventTap:
    """Observes the existing journal; it is never a policy input."""
    def __init__(self, recorder):
        self.recorder = recorder
        self.events = deque(maxlen=200)
        self.sequence = 0

    def write(self, **event):
        saved = portable(event)
        self.recorder.write(**saved)
        self.events.append({'sequence': self.sequence, **saved})
        self.sequence += 1

    def close(self):
        self.recorder.close()


def default_factory(spec, journal):
    from .sandbox import Session
    return Session(spec, journal=journal)


class SessionManager:
    def __init__(self, root=None, factory=default_factory, *, neural_factory=neural_probe, identity=None):
        self.root = Path(root or ROOT / 'artifacts/control').resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.factory = factory
        self.neural_factory = neural_factory
        self.identity = identity or SourceIdentity()
        self.lock = threading.RLock()
        self.shutdown = threading.Event()
        self.session = None
        self.tap = None
        self.folder = None
        self.ident = None
        self.playing = False
        self.error = None
        self.last = None
        self.neural = None
        self.neural_seconds = 0.0
        self.evaluation = None
        self.probe = None
        self.diagnostic = {'enabled': True, 'status': 'idle', 'error': None}
        self.receipt = None
        self.token = secrets.token_urlsafe(32)
        self.thread = None

    def start_worker(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._worker, daemon=True, name='echo5-panel')
            self.thread.start()

    def _worker(self):
        while not self.shutdown.wait(.30):
            with self.lock:
                if self.playing:
                    self._advance()

    @staticmethod
    def done(state):
        return bool(state and (state.get('done') or state.get('terminated') or
                               state.get('truncated') or state.get('status') in
                               ('success', 'failed', 'budget_exhausted', 'completed', 'error')))

    def create(self, spec):
        if not isinstance(spec, dict):
            raise ValueError('La misión debe ser un objeto JSON')
        # Session owns environment-specific validation; these enforce UI limits.
        if len(json.dumps(spec)) > 16_384:
            raise ValueError('Configuración demasiado grande')
        diagnostics = spec.get('diagnostics', {'neural': True})
        if (type(diagnostics) is not dict or set(diagnostics) != {'neural'}
                or type(diagnostics['neural']) is not bool):
            raise ValueError('diagnostics debe ser {"neural": true|false}')
        actor_spec = {k: copy.deepcopy(v) for k, v in spec.items() if k != 'diagnostics'}
        with self.lock:
            self.require_fresh()
            self._close_session()
            now = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
            self.ident = now + '-' + secrets.token_hex(4)
            self.folder = self.root / self.ident
            self.folder.mkdir()
            (self.folder / 'request.json').write_text(json.dumps(spec, indent=2) + '\n')
            self.tap = EventTap(Recorder(self.folder / 'thought.jsonl'))
            self.error, self.neural, self.neural_seconds, self.last = None, None, 0.0, None
            self.evaluation = None
            self.receipt = None
            self.probe = None
            self.diagnostic = {'enabled': diagnostics['neural'],
                               'status': 'pending' if diagnostics['neural'] else 'disabled', 'error': None}
            try:
                self.session = self.factory(actor_spec, self.tap)
                self.last = portable(self.session.snapshot())
                self.tap.write(kind='panel_session', session_id=self.ident, spec=spec,
                               boot_id=self.identity.boot_id,
                               diagnostic_drives_policy=False, diagnostic_enabled=diagnostics['neural'])
                self._persist_terminal()
                self._persist()
                self._observe_neural()
                self._persist()
            except Exception:
                self._close_session()
                raise
            return self.snapshot()

    def _observe_neural(self):
        if not self.diagnostic['enabled'] or self.diagnostic['status'] == 'error':
            return
        # Exclude adjudicator fields/results: probe only public observation.
        observed = self.last.get('observation', self.last.get('observations', {}))
        before = time.monotonic()
        stage = 'initialize' if self.probe is None else 'observe'
        self.neural = None
        try:
            if self.probe is None:
                self.probe = self.neural_factory()
            stage = 'observe'
            self.neural = portable(self.probe.observe(observed))
        except Exception as exc:
            self.probe = None
            self.diagnostic.update(status='error', error=f'{type(exc).__name__}: {exc}')
            self.tap.write(kind='neural_diagnostic_error', stage=stage,
                           step=self.last.get('step'), error=self.diagnostic['error'],
                           drives_policy=False, session_continues=not self.done(self.last),
                           terminal_result_persisted=self.receipt is not None)
            return
        finally:
            self.neural_seconds += time.monotonic() - before
        self.diagnostic.update(status='ready', error=None)
        # Persist measured frames for inspection without putting them in agent memory.
        self.tap.recorder.write(kind='neural_diagnostic', measurement=self.neural)

    def require_fresh(self):
        with self.lock:
            try:
                return self.identity.require_fresh()
            except SourceChanged as exc:
                self.playing = False
                if self.error != str(exc) and self.tap is not None:
                    self.tap.write(kind='panel_source_changed', error=str(exc),
                                   boot_id=self.identity.boot_id, restart_required=True)
                self.error = str(exc)
                raise

    def _persist_terminal(self):
        if self.done(self.last) and self.receipt is None and hasattr(self.session, 'result'):
            receipt = portable(self.session.result())
            pending = self.folder / 'result.pending'
            pending.write_text(json.dumps(receipt, ensure_ascii=False, allow_nan=False) + '\n')
            pending.replace(self.folder / 'result.json')
            self.receipt = receipt
            evidence = receipt.get('receipt', {})
            self.evaluation = evidence.get('payload', evidence).get('adjudication')

    def result(self):
        with self.lock:
            if self.receipt is None:
                raise ValueError('No hay un recibo terminal persistido')
            return portable(self.receipt)

    def _persist(self):
        data = {'session_id': self.ident, 'state': self.last, 'error': self.error,
                'boot_id': self.identity.boot_id, 'evaluation': self.evaluation,
                'diagnostic': self.diagnostic, 'observer_seconds': self.neural_seconds,
                'actor_receives_neural_diagnostic': False}
        pending = self.folder / 'state.pending'
        pending.write_text(json.dumps(data, ensure_ascii=False) + '\n')
        pending.replace(self.folder / 'state.json')

    def _advance(self):
        if self.session is None or self.done(self.last):
            self.playing = False
            return
        try:
            self.require_fresh()
            self.session.step()
            self.last = portable(self.session.snapshot())
            if self.done(self.last):
                self.playing = False
                self._persist_terminal()
            # A diagnostic exception must never lose an already completed step/result.
            self._persist()
            self._observe_neural()
        except Exception as exc:
            self.playing = False
            self.error = f'{type(exc).__name__}: {exc}'
            self.tap.write(kind='panel_error', error=self.error)
        self._persist()

    def command(self, action, session_id=None):
        with self.lock:
            if session_id is not None and session_id != self.ident:
                raise ValueError('La sesión cambió; actualiza el panel')
            if self.session is None:
                raise ValueError('Primero crea una misión')
            if action in ('play', 'step'):
                self.require_fresh()
            if action == 'play':
                if not self.done(self.last) and not self.error:
                    self.playing = True
            elif action == 'pause':
                self.playing = False
            elif action == 'step':
                self.playing = False
                if not self.error:
                    self._advance()
            else:
                raise ValueError('Acción desconocida')
            return self.snapshot()

    def snapshot(self):
        with self.lock:
            return portable({'schema': 'echo5.control.v1', 'session_id': self.ident,
                             'boot_id': self.identity.boot_id,
                             'playing': self.playing, 'error': self.error, 'state': self.last,
                             'neural': self.neural, 'events': list(self.tap.events) if self.tap else [],
                             'diagnostic': self.diagnostic,
                             'evaluation': self.evaluation,
                             'observer_seconds': round(self.neural_seconds, 6),
                             'llm_calls': 0, 'mode': 'live' if self.session else 'idle'})

    def _close_session(self):
        self.playing = False
        if self.session is not None:
            self.session.close()
            self.session = None
        if self.tap is not None:
            self.tap.close()
            self.tap = None

    def close(self):
        self.shutdown.set()
        if self.thread:
            self.thread.join(timeout=3)
        with self.lock:
            self._close_session()


def make_server(manager, host='127.0.0.1', port=8765):
    if host != '127.0.0.1':
        raise ValueError('El panel sólo admite loopback IPv4')
    manager.require_fresh()

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ECHO5Local/1'

        def log_message(self, fmt, *args):
            if args and str(args[1] if len(args) > 1 else '') not in ('200', '304'):
                super().log_message(fmt, *args)

        def _valid_host(self):
            actual = self.headers.get('Host', '')
            names = ('127.0.0.1', 'localhost', 'echoai.localhost', 'echoai.internal')
            return actual in {f'{name}:{self.server.server_port}' for name in names}

        def _reply(self, code, payload, mime='application/json; charset=utf-8'):
            raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self._valid_host():
                return self._reply(403, {'error': 'Host no autorizado'})
            path = urlsplit(self.path).path
            if path == '/api/identity':
                with manager.lock:
                    identity = manager.identity.snapshot()
                    if not identity['fresh']:
                        try:
                            manager.require_fresh()
                        except SourceChanged:
                            pass
                return self._reply(200, identity)
            if path == '/api/result':
                try:
                    return self._reply(200, manager.result())
                except ValueError as exc:
                    return self._reply(409, {'error': str(exc)})
            # The journal and terminal receipt remain readable after a drift veto.
            if path not in ('/api/journal', '/api/closure'):
                try:
                    identity = manager.require_fresh()
                except SourceChanged as exc:
                    return self._reply(409, {'error': str(exc), 'restart_required': True})
            if path == '/api/state':
                return self._reply(200, manager.snapshot())
            if path == '/api/config':
                from .sandbox import catalogue
                return self._reply(200, {'token': manager.token, 'catalogue': catalogue(),
                                         'version': '5.8.3', 'neocortex': 'off',
                                         'source_identity': identity,
                                         'diagnostics': {'neural': {'default': True, 'optional': True,
                                                                  'drives_policy': False}}})
            if path == '/api/journal':
                with manager.lock:
                    if manager.folder is None:
                        return self._reply(404, {'error': 'No hay un diario activo'})
                    raw = (manager.folder / 'thought.jsonl').read_bytes()
                return self._reply(200, raw, 'application/x-ndjson; charset=utf-8')
            if path == '/api/closure':
                latest = ROOT / 'artifacts/closure-latest.json'
                value = json.loads(latest.read_text()) if latest.is_file() else {'status': 'not_run', 'gates': {}}
                return self._reply(200, value)
            files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                     '/style.css': ('style.css', 'text/css')}
            if path not in files:
                return self._reply(404, {'error': 'Ruta desconocida'})
            name, mime = files[path]
            return self._reply(200, (ASSETS / name).read_bytes(), mime + '; charset=utf-8')

        def do_POST(self):
            origin = self.headers.get('Origin')
            if (not self._valid_host() or (origin is not None and origin != 'http://' + self.headers.get('Host', ''))
                    or not secrets.compare_digest(self.headers.get('X-Echo-Token', ''), manager.token)):
                return self._reply(403, {'error': 'Solicitud local no autorizada'})
            try:
                manager.require_fresh()
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16384:
                    raise ValueError('Tamaño de petición fuera de límite')
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('Se requiere JSON')
                value = json.loads(self.rfile.read(size))
                if not isinstance(value, dict):
                    raise ValueError('Se requiere un objeto JSON')
                path = urlsplit(self.path).path
                if path == '/api/session':
                    result = manager.create(value)
                elif path == '/api/control':
                    result = manager.command(value.get('action'), value.get('session_id'))
                else:
                    return self._reply(404, {'error': 'Ruta desconocida'})
                return self._reply(200, result)
            except SourceChanged as exc:
                return self._reply(409, {'error': str(exc), 'restart_required': True})
            except (ValueError, TypeError, KeyError) as exc:
                return self._reply(400, {'error': str(exc)})
            except Exception as exc:
                return self._reply(500, {'error': f'{type(exc).__name__}: {exc}'})

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server


def serve(port=8765, root=None):
    manager = SessionManager(root=root)
    server = make_server(manager, port=port)
    manager.start_worker()
    print(json.dumps({'url': f'http://echoai.localhost:{server.server_port}',
                      'loopback': f'http://127.0.0.1:{server.server_port}', 'status': 'listening',
                      'boot_id': manager.identity.boot_id,
                      'boot_source_sha256': manager.identity.boot['own']['sha256']}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        manager.close()
