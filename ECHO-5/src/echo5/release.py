"""Combine independent closure receipts without changing domain thresholds."""
import hashlib
import json
from pathlib import Path
import re

from .closure import (ROOT, DOMAINS, verify_manifest, verify_archive, preserve, write_json,
                      _reconcile_campaign, _reconcile_domain_audits, _same)
from .evaluation import digest, source_snapshot
from .distribution import CORE_FILES


def required_gates(campaign, audit, reports, checks, browser, sitl, sitl_audit):
    """Pure verdict: valid auditing never substitutes for scientific success."""
    identity = campaign.get('sources_sha256')
    gates = {
        'confirmation_campaign': campaign.get('phase') == 'confirmation',
        'independent_domain_audit': audit.get('valid') is True,
        'software_checks': checks.get('valid') is True and checks.get('sources_sha256') == identity,
        'browser_check': browser.get('valid') is True and browser.get('sources_sha256') == identity,
        'structural_transfer_memory_hierarchy': reports.get('transfer', {}).get('gates', {}).get('closure_candidate') is True,
        'replicated_counterexamples': reports.get('curriculum', {}).get('gates', {}).get('scientific_success') is True,
        'external_partial_observation': reports.get('sandbox', {}).get('gates', {}).get('closure') is True,
        'mission_agent_integration': reports.get('mission', {}).get('gates', {}).get('software_correctness') is True,
        'new_sitl_confirmation': sitl.get('config', {}).get('phase') == 'confirmation',
        'independent_sitl_validation': sitl_audit.get('valid') is True and
                                       sitl_audit.get('gates', {}).get('sitl_valid') is True and
                                       sitl_audit.get('gates', {}).get('measurements_pass') is True and
                                       sitl_audit.get('gates', {}).get('independent_audit') is True and
                                       sitl_audit.get('findings') == [],
    }
    return gates


def _folder(value):
    path = Path(value).resolve()
    if not path.is_relative_to((ROOT / 'artifacts').resolve()):
        raise ValueError('Receipt paths must remain inside ECHO-5/artifacts')
    return path


def _read(folder, name):
    return json.loads((folder / name).read_text())


def verify_snapshot_identity(frozen, expected):
    """Reject reduced coverage and self-declared hashes inconsistent with files."""
    if type(frozen) is not dict or set(frozen) != {'own', 'legacy', 'host'}:
        raise ValueError('Complete source groups required')
    for key in ('own', 'legacy', 'host'):
        item = frozen[key]
        if (type(item) is not dict or not item.get('files') or
                item.get('sha256') != digest(item['files']) or item != expected[key]):
            raise ValueError('Source snapshot identity or coverage mismatch: ' + key)


def current_release_sources():
    # Fixed verifier scope; never choose coverage from a supplied receipt.
    return {
        'own': source_snapshot(ROOT, ['src', 'scripts', 'tests', 'docs', 'pyproject.toml',
                                     '.python-version', 'requirements-sandbox.lock'],
                               suffixes=('.py', '.json', '.js', '.css', '.html', '.toml', '.lock', '')),
        'legacy': source_snapshot(ROOT.parent, ['seed', 'echo_arc', 'echo4', 'nexus0', '__init__.py'],
                                  suffixes=('.py', '.json', '.bnf', '.txt')),
        'host': source_snapshot(ROOT.parent, CORE_FILES),
    }


def verify_checks_evidence(folder, report):
    """Reconcile declared success with every required command and its log."""
    commands = [
        ('environment', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'check']),
        ('core_tests', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'test']),
        ('sandbox_tests', [str(ROOT / '.venv-sandbox/bin/python'), '-I', str(ROOT / 'scripts/closure.py'), 'test-external']),
        ('javascript_syntax', ['node', '--check', str(ROOT / 'src/echo5/web/app.js')]),
    ]
    if report.get('schema') != 'echo5.required-checks.v2':
        raise ValueError('Required checks need command/log evidence')
    rows = report.get('commands')
    if type(rows) is not list or len(rows) != len(commands):
        raise ValueError('Missing required checks')
    passed = report.get('error') is None
    for row, (name, argv) in zip(rows, commands):
        if row.get('name') != name or row.get('argv') != argv:
            raise ValueError('Missing, substituted or duplicated check: ' + name)
        passed = passed and type(row.get('exit_code')) is int and row['exit_code'] == 0
        passed = passed and row.get('timed_out') is False
    verify_manifest(folder, report.get('artifact_hashes'), {name + '.log' for name, _ in commands})
    logs = {}
    for row, (name, argv) in zip(rows, commands):
        header, separator, log = (Path(folder) / (name + '.log')).read_text().partition('\n')
        binding = json.loads(header) if separator else {}
        expected = {'schema': 'echo5.check-log.v1', 'name': name, 'argv': argv,
                    'pid': row.get('pid'), 'sources_sha256': report.get('sources_sha256')}
        if binding != expected or type(row.get('pid')) is not int or row['pid'] <= 0:
            raise ValueError('Check log is bound to another command or source snapshot')
        logs[name] = log
    for name in ('core_tests', 'sandbox_tests'):
        log = logs[name]
        completed = re.search(r'^Ran ([0-9]+) tests? in [0-9.]+s\s*\n\s*OK(?: \(skipped=([0-9]+)\))?\s*\Z', log, re.MULTILINE)
        passed = passed and completed is not None and int(completed.group(1)) > int(completed.group(2) or 0)
        passed = passed and len(re.findall(r'^Ran [0-9]+ tests? in ', log, re.MULTILINE)) == 1
        passed = passed and re.search(r'^(FAILED|ERROR:|FAIL:)', log, re.MULTILINE) is None
    integrity = report.get('integrity', {})
    passed = passed and all(integrity.get(k, {}).get('unchanged') is True for k in ('own', 'legacy', 'host'))
    if report.get('valid') is not bool(passed):
        raise ValueError('Required checks verdict contradicts command/log evidence')


def verify_browser_evidence(folder, report, identity, full_identity=None):
    """Check recorded state and server identity, not only a success flag."""
    required_checks = {'visible_local_font', 'real_session', 'step', 'play', 'pause',
                       'measured_neural_activity', 'visible_journal', 'no_page_errors',
                       'mobile_no_overflow', 'external_terminal_verdict', 'server_boot_sources',
                       'server_source_freshness', 'session_identity_binding', 'terminal_receipt_binding'}
    required = {'desktop.png', 'mobile.png', 'observed-state.json', 'terminal-state.json', 'server-identity.json'}
    if report.get('schema') != 'echo5.browser-check.v2' or report.get('phase') != 'development_only':
        raise ValueError('Browser check needs measured evidence and source-bound server')
    verify_manifest(folder, report.get('artifact_hashes'), required)
    observed, terminal, server = (_read(Path(folder), name) for name in
                                 ('observed-state.json', 'terminal-state.json', 'server-identity.json'))
    if (server.get('boot_source_sha256') != identity or server.get('current_source_sha256') != identity or
            server.get('fresh') is not True or server.get('error') is not None):
        raise ValueError('Browser tested another or stale server build')
    if full_identity is not None and (server.get('boot_full_sources_sha256') != full_identity or
                                      server.get('current_full_sources_sha256') != full_identity):
        raise ValueError('Browser server inherited another legacy source snapshot')
    if any(not (Path(folder) / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for name in ('desktop.png', 'mobile.png')):
        raise ValueError('Browser screenshots are missing PNG evidence')
    n, state, evaluation = observed.get('neural', {}), terminal.get('state', {}), terminal.get('evaluation', {})
    sid, step = observed.get('session_id'), state.get('step')
    boot = server.get('boot_id')
    if (type(boot) is not str or not re.fullmatch(r'[0-9a-f]{32}', boot) or
            observed.get('boot_id') != boot or terminal.get('boot_id') != boot):
        raise ValueError('Browser snapshots belong to different server instances')
    evidence = {'session-result.json', 'session-journal.jsonl', 'semantic-checks.json'}
    verify_manifest(folder, report.get('evidence_hashes'), evidence)
    semantic = _read(Path(folder), 'semantic-checks.json')
    if (type(semantic) is not list or len(semantic) != len(required_checks) or
            {r.get('name') for r in semantic} != required_checks or
            any(r.get('passed') is not True for r in semantic) or
            report.get('semantic_checks') != semantic):
        raise ValueError('Browser semantic checks incomplete or contradictory')
    episode = _read(Path(folder), 'session-result.json')['receipt']
    payload = episode['payload']
    from .interaction import _canonical
    if episode.get('sha256') != hashlib.sha256(_canonical(payload).encode()).hexdigest():
        raise ValueError('Browser native episode seal differs from its transcript')
    if (payload.get('adjudication') != evaluation or payload.get('done') is not True or
            payload.get('actions') != step or payload.get('final_observation') != state.get('observation') or
            len(payload.get('transcript', [])) < 8 or
            payload['transcript'][7].get('after') != observed.get('state', {}).get('observation') or
            any(payload.get('config', {}).get(k) != v for k, v in
                [('seed', 101), ('scenario', 'door_key'), ('mode', 'informative')])):
        raise ValueError('Browser outcome is not bound to the recorded native episode')
    from .trace import verify_journal
    verify_journal(Path(folder) / 'session-journal.jsonl')
    events = [json.loads(line) for line in (Path(folder) / 'session-journal.jsonl').read_text().splitlines()]
    starts = [r for r in events if r.get('kind') == 'panel_session']
    if (len(starts) != 1 or starts[0].get('session_id') != sid or starts[0].get('boot_id') != boot or
            sum(r.get('kind') == 'sandbox_step' for r in events) != step):
        raise ValueError('Browser journal is from another or incomplete episode')
    from .neural_observer import NeuralObserver
    if n != NeuralObserver().observe(observed.get('state', {}).get('observation', {})):
        raise ValueError('Browser neural frames do not reproduce the measured source module')
    passed = (report.get('error') is None and report.get('page_errors') == [] and
              type(sid) is str and bool(sid) and terminal.get('session_id') == sid and
              observed.get('error') is None and terminal.get('error') is None and
              type(step) is int and step >= 8 and
              required_checks.issubset(report.get('checks', [])) and
              observed.get('state', {}).get('step') == 8 and bool(observed.get('events')) and
              n.get('neurons') == 256 and n.get('drives_policy') is False and len(n.get('frames', [])) == 16 and
              state.get('done') is True and type(evaluation.get('success')) is bool and
              evaluation.get('actor_claim_used') is False and
              report.get('demonstration_success') is evaluation.get('success') and
              report.get('demonstration_steps') == state.get('step'))
    if report.get('valid') is not bool(passed):
        raise ValueError('Browser verdict contradicts measured evidence')


def verify_domain_audits(folder, audit):
    hashes = audit.get('domain_audits_sha256')
    if type(hashes) is not dict or set(hashes) != set(DOMAINS):
        raise ValueError('Every domain audit must be bound to the aggregate audit')
    verify_manifest(folder, {f'{domain}/audit.json': sha for domain, sha in hashes.items()})


def verify_campaign_evidence(folder, result, audit, manifest, sources):
    """Reconcile the complete closure evidence without rerunning domain science."""
    folder = Path(folder)
    if (type(result) is not dict or result.get('schema') != 'echo5.closure-campaign.v1' or
            type(audit) is not dict or audit.get('schema') != 'echo5.closure-audit.v1'):
        raise ValueError('Campaign and independent audit schemas required')
    # Same mandatory measurement coverage as closure.audit_campaign. Domain
    # audits are produced later and bound by the aggregate audit's hash map.
    required = {'campaign.json', 'sources.json', 'sources.zip', 'contracts.json', 'result.json', 'processes.json'}
    required.update(f'{domain}/{name}' for domain in DOMAINS for name in
                    ('config.json', 'result.json', 'receipt.json', 'thought.jsonl'))
    verify_manifest(folder, manifest, required)
    verify_domain_audits(folder, audit)
    campaign = _read(folder, 'campaign.json')
    if (type(campaign) is not dict or not isinstance(campaign.get('campaign_id'), str) or
            not campaign['campaign_id'] or campaign.get('phase') not in ('development', 'confirmation')):
        raise ValueError('Invalid campaign identity')
    _same(audit.get('campaign_id'), campaign['campaign_id'], 'audit campaign identity')
    _same(audit.get('manifest_sha256'), digest(manifest), 'audit/measurement manifest')
    # These are closure's receipt/config/journal and auditor reconciliation
    # functions, not audit_campaign or any scientific evaluator/replay.
    reports = _reconcile_campaign(folder, campaign, result, sources)
    gates, hashes = _reconcile_domain_audits(folder, campaign, reports)
    _same(audit.get('domain_gates'), gates, 'independent and aggregate gates')
    _same(audit.get('domain_audits_sha256'), hashes, 'domain audit bytes')
    return reports


def check_sitl_aggregate(recomputed, audit):
    expected = (recomputed.get('measurements_pass') is True and
                audit.get('gates', {}).get('independent_audit') is True and
                audit.get('findings') == [])
    if audit.get('valid') is not expected or audit.get('gates', {}).get('sitl_valid') is not expected:
        raise ValueError('SITL aggregate disagrees with measured criteria and independent findings')


def verify_sitl_evidence(folder, report, audit, sources):
    from .sitl import _config, CONDITIONS, MODES, evaluate_episode, _campaign_gates
    if report.get('schema') != 'echo5.sitl.campaign.v1' or audit.get('schema') != 'echo5.sitl.audit.v1':
        raise ValueError('SITL receipt schemas required')
    cfg = _config(_read(folder, 'configuration.json'))
    if cfg != report.get('config') or cfg != audit.get('config') or cfg['phase'] != 'confirmation':
        raise ValueError('SITL confirmation configuration mismatch')
    rows = report.get('rows')
    if type(rows) is not list or len(rows) != cfg['cases'] * len(MODES) or rows != audit.get('rows'):
        raise ValueError('All scheduled SITL rows are required')
    expected_sources = {name: sha for name, sha in sources['own']['files'].items()
                        if name.startswith(('src/', 'scripts/')) and name.endswith('.py')}
    if not expected_sources or _read(folder, 'sources.json') != expected_sources:
        raise ValueError('SITL needs the complete frozen runtime source set')
    if _read(folder, 'contract.json') != _read(ROOT / 'docs', 'MISSION-CONTRACT.json'):
        raise ValueError('SITL contract mismatch')
    for index, row in enumerate(rows):
        case, mode = index // len(MODES), MODES[index % len(MODES)]
        identity = (f'sitl-{case:04d}', mode, CONDITIONS[case % len(CONDITIONS)], cfg['seed']+case)
        if tuple(row.get(k) for k in ('case_id', 'mode', 'condition', 'seed')) != identity:
            raise ValueError('SITL duplicate, substituted or missing case')
        episode = folder / f'{case:04d}-{mode}'
        manifest = _read(episode, 'evidence-manifest.json')
        if not manifest:
            raise ValueError('Empty SITL external evidence manifest')
        verify_manifest(episode, manifest, {'configuration.json', 'process-receipt.json', 'input-manifest.json'})
        actual = evaluate_episode(episode)
        if actual != row or actual.get('valid_receipt') is not True:
            raise ValueError('SITL row not confirmed by raw external evidence')
    recomputed = _campaign_gates(rows, cfg)
    for key, value in recomputed.items():
        if key not in ('independent_audit', 'sitl_valid') and audit.get('gates', {}).get(key) != value:
            raise ValueError('SITL audit gate mismatch: ' + key)
    check_sitl_aggregate(recomputed, audit)


def finalize(campaign_path, checks_path, browser_path, sitl_path, output):
    paths = {key: _folder(value) for key, value in
             [('campaign', campaign_path), ('checks', checks_path),
              ('browser', browser_path), ('sitl', sitl_path)]}
    campaign = _read(paths['campaign'], 'result.json')
    audit = _read(paths['campaign'], 'audit.json')
    manifest = _read(paths['campaign'], 'manifest.json')
    sources = _read(paths['campaign'], 'sources.json')
    reports = verify_campaign_evidence(paths['campaign'], campaign, audit, manifest, sources)
    verify_snapshot_identity(sources, current_release_sources())
    if campaign.get('sources_sha256') != sources['own']['sha256']:
        raise ValueError('Campaign source hash disagrees with its frozen files')
    verify_archive(paths['campaign'], sources)
    preserve(sources)
    checks, browser = (_read(paths[key], 'result.json') for key in ('checks', 'browser'))
    for key, report in [('checks', checks), ('browser', browser)]:
        frozen = _read(paths[key], 'sources.json')
        verify_snapshot_identity(frozen, sources)
        verify_archive(paths[key], frozen)
        actual_integrity = preserve(frozen)
        if report.get('integrity') != actual_integrity:
            raise ValueError('Validation integrity receipt is inconsistent: ' + key)
        if frozen['own']['sha256'] != report['sources_sha256']:
            raise ValueError('Validation source identity mismatch: ' + key)
    verify_checks_evidence(paths['checks'], checks)
    verify_browser_evidence(paths['browser'], browser, sources['own']['sha256'], digest(sources))
    sitl, sitl_audit = (_read(paths['sitl'], name) for name in ('report.json', 'audit.json'))
    verify_sitl_evidence(paths['sitl'], sitl, sitl_audit, sources)
    gates = required_gates(campaign, audit, reports, checks, browser, sitl, sitl_audit)
    result = {
        'schema': 'echo5.release-readiness.v1',
        'status': 'closure_verified' if all(gates.values()) else 'research_open',
        'release_eligible': all(gates.values()), 'gates': gates,
        'sources_sha256': sources['own']['sha256'],
        'receipts': {key: str(path.relative_to(ROOT)) for key, path in paths.items()},
        'receipt_hashes': {key: {name: hashlib.sha256((path / name).read_bytes()).hexdigest()
                                for name in ('result.json', 'report.json', 'audit.json')
                                if (path / name).is_file()} for key, path in paths.items()},
        'limits': ['Synthetic structural transfer and native MiniGrid/BabyAI tasks within frozen contracts',
                   'Gazebo/PX4 simulation; no physical flight or hardware certification',
                   'Neural activity is an observation diagnostic, not a policy-performance claim',
                   'No claim of arbitrary problem solving, zero hallucinations, RSI or official ARC score'],
        's6_in_scope': False,
    }
    output = _folder(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'result.json', result)
    write_json(ROOT / 'artifacts/closure-latest.json', result, replace=True)
    return result
