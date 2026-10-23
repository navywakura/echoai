"""Source-bound development browser check. No browser or episode at import."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'echo5.browser-check.v2'
REQUIRED_ARTIFACTS = ('desktop.png', 'mobile.png', 'observed-state.json',
                      'terminal-state.json', 'server-identity.json')
REQUIRED_CHECKS = (
    'visible_local_font', 'real_session', 'step', 'play', 'pause',
    'measured_neural_activity', 'visible_journal', 'no_page_errors',
    'mobile_no_overflow', 'external_terminal_verdict',
    'server_boot_sources', 'server_source_freshness', 'session_identity_binding',
    'terminal_receipt_binding',
)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validate_identity(identity, sources, boot_id=None):
    """Reject a stale server, a different checkout, or a mid-check restart."""
    expected = {key: value['sha256'] for key, value in sources.items()}
    if (identity.get('schema') != 'echo5.control.source-identity.v1'
            or identity.get('fresh') is not True or identity.get('error') is not None
            or identity.get('boot_source_sha256') != expected['own']
            or identity.get('current_source_sha256') != expected['own']
            or identity.get('boot_full_sources_sha256') != canonical_digest(sources)
            or identity.get('current_full_sources_sha256') != canonical_digest(sources)
            or identity.get('boot_source_groups') != expected
            or identity.get('current_source_groups') != expected):
        raise ValueError('Server does not match the frozen sources; apply sources and restart it')
    actual_boot = identity.get('boot_id')
    if (not isinstance(actual_boot, str) or not re.fullmatch(r'[0-9a-f]{32}', actual_boot)
            or boot_id is not None and actual_boot != boot_id
            or type(identity.get('pid')) is not int or identity['pid'] <= 0
            or type(identity.get('started_ns')) is not int
            or type(identity.get('checked_ns')) is not int
            or not 0 < identity['started_ns'] <= identity['checked_ns']):
        raise ValueError('Missing or changed server boot identity')
    return actual_boot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT / 'src'))
    from echo5.closure import freeze, preserve
    from echo5.trace import verify_journal
    sources = freeze(out)
    errors, records = [], []
    error = integrity = final_state = observed_state = None
    session_id = boot_id = None

    def check(name, passed, **facts):
        record = {'name': name, 'passed': bool(passed), 'checked_ns': time.time_ns(), 'facts': facts}
        records.append(record)
        if not passed:
            raise AssertionError(name + ': ' + json.dumps(facts, ensure_ascii=False))

    try:
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1080}, reduced_motion='reduce')
                page.on('pageerror', lambda e: errors.append(str(e)))

                def fetch(path, artifact=None):
                    response = page.request.get(args.url.rstrip('/') + path)
                    raw = response.body()
                    if response.status != 200:
                        raise RuntimeError(f'{path}: HTTP {response.status}: ' + raw.decode(errors='replace')[:1000])
                    if artifact is not None:
                        (out / artifact).write_bytes(raw)
                    return json.loads(raw)

                before = fetch('/api/identity')
                boot_id = validate_identity(before, sources)
                identity_evidence = {
                    **before, 'expected_source_sha256': sources['own']['sha256'],
                    'expected_full_sources_sha256': canonical_digest(sources),
                    'expected_source_groups': {k: v['sha256'] for k, v in sources.items()},
                    'observations': {'before': before, 'after': None},
                }
                save(out / 'server-identity.json', identity_evidence)
                check('server_boot_sources', True, boot_id=boot_id,
                      expected_source_sha256=sources['own']['sha256'],
                      boot_source_sha256=before['boot_source_sha256'],
                      boot_full_sources_sha256=before['boot_full_sources_sha256'])
                page.goto(args.url, wait_until='networkidle')
                expect(page.locator('#connection')).to_have_text('Conectado')
                title_box = page.locator('h1').bounding_box()
                check('visible_local_font', bool(title_box and title_box['height'] > 20), bounds=title_box)
                page.locator('#scenario').select_option('door_key')
                page.locator('#seed').fill('101')
                page.locator('#max-steps').fill('192')
                page.locator('#neural-enabled').select_option('on')
                page.locator('#new-mission').click()
                expect(page.locator('#step')).to_be_enabled()
                initial = fetch('/api/state')
                session_id = initial.get('session_id')
                check('real_session', isinstance(session_id, str) and bool(session_id)
                      and initial['boot_id'] == boot_id and type(initial['state']['step']) is int
                      and initial['state']['step'] == 0 and initial['state']['done'] is False
                      and initial['error'] is None, session_id=session_id, initial_state=initial['state'])
                for i in range(8):
                    page.locator('#step').click()
                    expect(page.locator('#step-count')).to_have_text(str(i+1))
                observed_state = fetch('/api/state', 'observed-state.json')
                check('step', type(observed_state['state']['step']) is int
                      and observed_state['state']['step'] == 8 and observed_state['error'] is None,
                      observed_step=observed_state['state']['step'], artifact='observed-state.json')
                neural = observed_state['neural'] or {}
                check('measured_neural_activity', neural.get('neurons') == 256
                      and neural.get('drives_policy') is False and len(neural.get('frames', [])) == 16
                      and observed_state['diagnostic']['status'] == 'ready',
                      artifact='observed-state.json', module=neural.get('module'),
                      input_sha256=neural.get('input_sha256'))
                page.locator('#tick').focus()
                page.locator('#tick').press('Home')
                for _ in range(5):
                    page.locator('#tick').press('ArrowRight')
                expect(page.locator('#tick-output')).to_have_text('5 / 15')
                expect(page.locator('#error')).not_to_be_visible()
                page.screenshot(path=str(out / 'desktop.png'), full_page=True)
                page.locator('#play').click()
                expect(page.locator('#step-count')).not_to_have_text('8')
                playing = fetch('/api/state')
                check('play', playing['state']['step'] > 8 and playing['error'] is None,
                      state=playing)
                page.locator('#pause').click()
                expect(page.locator('#status')).not_to_have_text('En ejecución')
                stopped = fetch('/api/state')
                page.wait_for_timeout(900)
                after_pause = fetch('/api/state')
                check('pause', after_pause['state']['step'] == stopped['state']['step']
                      and after_pause['playing'] is False and stopped['playing'] is False
                      and not after_pause['state']['done'], before=stopped, after=after_pause)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.screenshot(path=str(out / 'mobile.png'), full_page=True)
                overflow = page.locator('html').evaluate('(el) => el.scrollWidth > window.innerWidth + 1')
                check('mobile_no_overflow', not overflow, viewport={'width': 390, 'height': 844}, overflow=overflow)
                page.locator('#play').click()
                expect(page.locator('#status')).to_have_text(re.compile(r'^(Completada|Finalizada)$'), timeout=90000)
                final_state = fetch('/api/state', 'terminal-state.json')
                verdict = final_state.get('evaluation') or {}
                check('external_terminal_verdict', final_state['state']['done'] is True
                      and type(final_state['state']['step']) is int and final_state['state']['step'] >= 8
                      and type(verdict.get('success')) is bool and verdict.get('actor_claim_used') is False
                      and final_state['error'] is None, artifact='terminal-state.json', adjudication=verdict)
                receipt = fetch('/api/result', 'session-result.json')
                payload = receipt['receipt']['payload']
                check('terminal_receipt_binding', payload['adjudication'] == verdict
                      and payload['done'] is True and payload['actions'] == final_state['state']['step']
                      and payload['config']['seed'] == 101 and payload['config']['scenario'] == 'door_key'
                      and payload['config']['mode'] == 'informative'
                      and payload['final_observation'] == final_state['state']['observation']
                      and len(payload['transcript']) >= 8
                      and payload['transcript'][7]['after'] == observed_state['state']['observation'],
                      artifact='session-result.json', adjudication=payload['adjudication'])
                journal_response = page.request.get(args.url.rstrip('/') + '/api/journal')
                if journal_response.status != 200:
                    raise RuntimeError('Session journal download failed')
                (out / 'session-journal.jsonl').write_bytes(journal_response.body())
                chain = verify_journal(out / 'session-journal.jsonl')
                journal_events = [json.loads(line) for line in (out / 'session-journal.jsonl').read_text().splitlines()]
                starts = [r for r in journal_events if r.get('kind') == 'panel_session']
                steps = [r for r in journal_events if r.get('kind') == 'sandbox_step']
                check('visible_journal', bool(observed_state['events']) and chain['events'] > 0
                      and len(starts) == 1 and starts[0]['session_id'] == session_id
                      and starts[0]['boot_id'] == boot_id and len(steps) == payload['actions'],
                      artifact='session-journal.jsonl', chain=chain, native_steps=len(steps))
                check('session_identity_binding', all(s['boot_id'] == boot_id and s['session_id'] == session_id
                      for s in (initial, observed_state, playing, stopped, after_pause, final_state)),
                      boot_id=boot_id, session_id=session_id)
                after = fetch('/api/identity')
                validate_identity(after, sources, boot_id)
                identity_evidence.update(after)
                identity_evidence['observations']['after'] = after
                save(out / 'server-identity.json', identity_evidence)
                check('server_source_freshness', True, boot_id=boot_id,
                      before_checked_ns=before['checked_ns'], after_checked_ns=after['checked_ns'])
                check('no_page_errors', not errors, page_errors=list(errors))
            finally:
                browser.close()
        integrity = preserve(sources)
        if len(records) != len(REQUIRED_CHECKS) or {r['name'] for r in records} != set(REQUIRED_CHECKS):
            raise ValueError('Missing or duplicate required browser checks')
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'

    save(out / 'semantic-checks.json', records)
    def hashes(names):
        return {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                for name in names if (out / name).is_file()}
    artifact_hashes = hashes(REQUIRED_ARTIFACTS)
    valid = (error is None and not errors and len(artifact_hashes) == len(REQUIRED_ARTIFACTS)
             and len(records) == len(REQUIRED_CHECKS) and all(r['passed'] for r in records))
    if error is None and not valid:
        error = 'Incomplete browser evidence'
    receipt = {'schema': SCHEMA, 'valid': valid, 'error': error, 'page_errors': errors,
               'seed': 101, 'phase': 'development_only', 'neural_frames': 16,
               'checks': [r['name'] for r in records if r['passed']],
               'required_checks': list(REQUIRED_CHECKS), 'semantic_checks': records,
               'demonstration_success': ((final_state or {}).get('evaluation') or {}).get('success'),
               'demonstration_steps': ((final_state or {}).get('state') or {}).get('step'),
               'session_id': session_id, 'server_boot_id': boot_id,
               'screenshots': ['desktop.png', 'mobile.png'],
               'artifact_hashes': artifact_hashes,
               'evidence_hashes': hashes(('session-result.json', 'session-journal.jsonl', 'semantic-checks.json')),
               'sources_sha256': sources['own']['sha256'],
               'full_sources_sha256': canonical_digest(sources), 'integrity': integrity}
    save(out / 'result.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
