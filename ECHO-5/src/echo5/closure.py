"""Background closure orchestration with source custody and explicit verdicts."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import traceback
import zipfile

from .evaluation import digest, source_snapshot, check_sources
from .distribution import CORE_FILES
from .trace import Recorder, verify_journal

ROOT = Path(__file__).resolve().parents[2]
DOMAINS = ('transfer', 'curriculum', 'sandbox', 'mission')
CONTRACTS = {name: f'docs/{name.upper()}-CONTRACT.json' for name in DOMAINS}


def write_json(path, value, *, replace=False):
    path = Path(path)
    if replace:
        pending = path.with_suffix(path.suffix + '.pending')
        pending.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        pending.replace(path)
    else:
        with path.open('x') as f:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')


def status(folder, phase, **facts):
    state = {'phase': phase, 'updated_utc': datetime.now(timezone.utc).isoformat(), **facts}
    write_json(Path(folder) / 'status.json', state, replace=True)
    print(json.dumps(state), flush=True)


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _same(actual, expected, description):
    if digest(actual) != digest(expected):
        raise ValueError('Closure reconciliation mismatch: ' + description)


def campaign_status(folder, campaign, state, *, result=None, **facts):
    """Publish this campaign, never a previous campaign's successful gates."""
    status(folder, state, campaign_id=campaign['campaign_id'], split=campaign['phase'], **facts)
    latest = {**(result or {}), 'schema': 'echo5.closure-campaign.v1',
              'campaign_id': campaign['campaign_id'], 'campaign_path': str(folder),
              'phase': campaign['phase'], 'status': state,
              'updated_utc': datetime.now(timezone.utc).isoformat(),
              'release_eligible': False, **facts}
    if state not in ('measured_pending_independent_audit', 'audited'):
        latest['gates'] = {}
        latest['audit_valid'] = False
    (ROOT / 'artifacts').mkdir(parents=True, exist_ok=True)
    write_json(ROOT / 'artifacts/closure-latest.json', latest, replace=True)


def module_for(domain):
    if domain not in DOMAINS:
        raise ValueError('unknown domain')
    return importlib.import_module('echo5.' + ('sandbox_eval' if domain == 'sandbox' else domain))


def domain_config(domain, phase):
    module = module_for(domain)
    if domain in ('transfer', 'curriculum'):
        config = module.default_config(phase)
        if domain == 'curriculum' and phase == 'development':
            config.update(paired_runs=4, confirmation_cases_per_run=4, bootstrap_samples=256)
        return config
    contract = json.loads((ROOT / CONTRACTS[domain]).read_text())
    if domain == 'sandbox':
        return {'split': phase, 'cases_per_family': (
            contract['thresholds']['confirmation_cases_per_family'] if phase == 'confirmation' else 2)}
    sw = contract['software']
    return {'phase': phase, 'seed': sw[phase + '_seed'], 'cases': sw['cases'],
            'budget': sw['budget_per_case_mode'], 'max_decisions': sw['max_decisions']}


def freeze(folder):
    folder = Path(folder)
    own = source_snapshot(ROOT, ['src', 'scripts', 'tests', 'docs', 'pyproject.toml',
                                '.python-version', 'requirements-sandbox.lock'],
                          suffixes=('.py', '.json', '.js', '.css', '.html', '.toml', '.lock', ''))
    old = source_snapshot(ROOT.parent, ['seed', 'echo_arc', 'echo4', 'nexus0', '__init__.py'],
                          suffixes=('.py', '.json', '.bnf', '.txt'))
    host = source_snapshot(ROOT.parent, CORE_FILES)
    receipts = {'own': own, 'legacy': old, 'host': host}
    write_json(folder / 'sources.json', receipts)
    with zipfile.ZipFile(folder / 'sources.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for prefix, base, receipt in [('ECHO-5', ROOT, own), ('echoai', ROOT.parent, old),
                                      ('host', ROOT.parent, host)]:
            for name in receipt['files']:
                archive.write(base / name, f'{prefix}/{name}')
    write_json(folder / 'contracts.json', {d: json.loads((ROOT / p).read_text()) for d, p in CONTRACTS.items()})
    return receipts


def preserve(receipts):
    results = {key: check_sources(base, receipts[key]) for key, base in
               [('own', ROOT), ('legacy', ROOT.parent), ('host', ROOT.parent)]}
    if not all(r['unchanged'] for r in results.values()):
        raise RuntimeError('Sources changed during measurement: ' + json.dumps(results))
    return results


def _verify_files(folder, manifest, required=()):
    folder = Path(folder).resolve()
    if type(manifest) is not dict or not set(required).issubset(manifest):
        raise ValueError('Incomplete manifest')
    for name, expected in manifest.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError('Invalid manifest entry')
        path = (folder / name).resolve()
        if (Path(name).is_absolute() or not path.is_relative_to(folder) or
                not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError('Manifest mismatch: ' + name)


def verify_manifest(folder, manifest, required=()):
    """Check measurements and, once present, the linked domain audit bytes.

    The measurement manifest is immutable. This additional check also serves
    release.py's existing verify_manifest call without changing its API.
    """
    folder = Path(folder).resolve()
    _verify_files(folder, manifest, required)
    audit_path = folder / 'audit.json'
    # Only the complete measurement manifest carries campaign.json. Callers
    # such as release.py also verify subsets of files with this same helper.
    if audit_path.is_file() and 'campaign.json' in manifest:
        audit = _read(audit_path)
        if type(audit) is not dict or audit.get('schema') != 'echo5.closure-audit.v1':
            raise ValueError('Invalid closure audit schema')
        _same(audit['manifest_sha256'], digest(manifest), 'audit/measurement manifest')
        hashes = audit.get('domain_audits_sha256')
        if type(hashes) is not dict or set(hashes) - set(DOMAINS):
            raise ValueError('Invalid domain audit hash map')
        if audit.get('valid') is True and set(hashes) != set(DOMAINS):
            raise ValueError('Valid audit needs every domain audit hash')
        _verify_files(folder, {f'{domain}/audit.json': sha for domain, sha in hashes.items()})


def verify_archive(folder, receipts):
    with zipfile.ZipFile(Path(folder) / 'sources.zip') as archive:
        expected = {f'{prefix}/{name}': sha for prefix, key in
                    [('ECHO-5', 'own'), ('echoai', 'legacy'), ('host', 'host')]
                    for name, sha in receipts[key]['files'].items()}
        if len(archive.namelist()) != len(expected) or set(archive.namelist()) != set(expected):
            raise ValueError('Archive entries differ from frozen source manifest')
        for name, sha in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise ValueError('Archived bytes differ: ' + name)


def worker(domain, phase, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    try:
        campaign = _worker_campaign(output, phase)
        config = domain_config(domain, phase)
        write_json(output / 'config.json', config)
        status(output, 'running', domain=domain, split=phase)
        with Recorder(output / 'thought.jsonl') as journal:
            journal.write(kind='closure_case_contract', domain=domain, split=phase, config=config)
            result = module_for(domain).run_benchmark(config, journal=journal)
        write_json(output / 'result.json', result)
        write_json(output / 'receipt.json', {'domain': domain, 'split': phase,
                   'campaign_id': campaign['campaign_id'],
                   'config_sha256': digest(config), 'result_config_sha256': digest(result['config']),
                   'contract_sha256': digest(_read(ROOT / CONTRACTS[domain])),
                   'result_sha256': digest(result), 'seconds': time.monotonic() - start,
                   'journal': verify_journal(output / 'thought.jsonl'), 'python': sys.version})
        status(output, 'measured_pending_audit', domain=domain, seconds=time.monotonic() - start,
               gates=result.get('gates', {}))
    except Exception as exc:
        write_json(output / 'instrument-error.json', {'type': type(exc).__name__, 'message': str(exc),
                                                     'traceback': traceback.format_exc()})
        status(output, 'instrument_error', domain=domain, error=str(exc))
        raise


def _worker_campaign(folder, phase):
    path = Path(folder).parent / 'campaign.json'
    if path.is_file():
        campaign = _read(path)
        _same(campaign['phase'], phase, 'worker/campaign phase')
        return campaign
    # Retain the explicit standalone worker CLI; directory creation is exclusive.
    return {'campaign_id': 'standalone-' + digest(str(Path(folder).resolve()))[:24], 'phase': phase}


def _terminate_process_group(proc):
    """Only signal the process group created by our start_new_session=True."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # A leader can exit on TERM while a descendant ignores it. Kill the
        # remaining group even when wait() has already reaped the leader.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def run_process(argv, log, *, cwd, timeout):
    """Return a launch/timeout receipt; never run a command through a shell."""
    start = time.monotonic()
    result = {'argv': list(argv), 'exit_code': 127, 'pid': None,
              'timed_out': False, 'process_group_cleanup_attempted': False}
    try:
        with Path(log).open('x') as stream:
            try:
                proc = subprocess.Popen(argv, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                result['pid'] = proc.pid
                try:
                    result['exit_code'] = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    result.update(exit_code=124, timed_out=True, process_group_cleanup_attempted=True)
                    _terminate_process_group(proc)
            except OSError as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
                stream.write(result['error'] + '\n')
    except OSError as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    result['seconds'] = time.monotonic() - start
    return result


def _invoke(domain, phase, folder, *, audit=False):
    python = ROOT / ('.venv-sandbox' if domain == 'sandbox' else '.venv') / 'bin/python'
    command = [str(python), '-I', str(ROOT / 'scripts/closure.py'),
               'audit-worker' if audit else 'worker', domain, '--output', str(folder / domain)]
    if not audit:
        command += ['--phase', phase]
    log = folder / (domain + ('-audit' if audit else '-process') + '.log')
    return {**run_process(command, log, cwd=ROOT, timeout=7200), 'domain': domain,
            'log': str(log.relative_to(folder))}


def _domain_receipts(folder, domain, campaign, *, root=None):
    """Reconcile requested and normalized config, result, receipt and journal."""
    root = Path(root) if root is not None else Path(folder) / domain
    config, report, receipt = (_read(root / name) for name in ('config.json', 'result.json', 'receipt.json'))
    expected = domain_config(domain, campaign['phase'])
    _same(config, expected, domain + ' requested config')
    module = module_for(domain)
    normalize = getattr(module, '_config' if domain == 'curriculum' else 'normalize_config', None)
    normalized = normalize(config) if callable(normalize) else config
    _same(report['config'], normalized, domain + ' normalized result config')
    for key, value in {'domain': domain, 'split': campaign['phase'],
                       'campaign_id': campaign['campaign_id'], 'config_sha256': digest(config),
                       'result_config_sha256': digest(report['config']),
                       'contract_sha256': digest(_read(ROOT / CONTRACTS[domain])),
                       'result_sha256': digest(report)}.items():
        _same(receipt.get(key), value, domain + ' receipt.' + key)
    journal = verify_journal(root / 'thought.jsonl')
    _same(receipt.get('journal'), journal, domain + ' journal receipt')
    return report, config, receipt, journal


def _validate_domain_audit(domain, report, audit):
    if type(audit) is not dict or audit.get('valid', audit.get('verified', False)) is not True:
        raise ValueError('Domain audit did not validate: ' + domain)
    for key in ('summary', 'gates'):
        if key not in audit:
            raise ValueError('Explicit auditor must return recomputed ' + key + ': ' + domain)
        _same(audit[key], report[key], domain + ' independently recomputed ' + key)
    if 'report_sha256' in audit:
        _same(audit['report_sha256'], digest(report), domain + ' auditor report hash')


def _reconcile_campaign(folder, campaign, result, sources):
    _same(result['campaign_id'], campaign['campaign_id'], 'campaign identity')
    _same(result['phase'], campaign['phase'], 'campaign phase')
    _same(result['sources_sha256'], sources['own']['sha256'], 'campaign sources')
    contracts = _read(folder / 'contracts.json')
    _same(contracts, {d: _read(ROOT / p) for d, p in CONTRACTS.items()}, 'frozen contracts')
    processes = _read(folder / 'processes.json')
    if (len(processes) != len(DOMAINS) or {p['domain'] for p in processes} != set(DOMAINS) or
            any(type(p['exit_code']) is not int or p['exit_code'] != 0 for p in processes)):
        raise ValueError('Incomplete or failed measurement processes')
    reports = {d: _domain_receipts(folder, d, campaign)[0] for d in DOMAINS}
    _same(result['domain_results'], {d: digest(r) for d, r in reports.items()}, 'aggregate result hashes')
    _same(result['gates'], {d: r['gates'] for d, r in reports.items()}, 'aggregate domain gates')
    return reports


def run_campaign(folder, phase='development', workers=4):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    campaign = {'campaign_id': secrets.token_hex(16), 'phase': phase,
                'created_utc': datetime.now(timezone.utc).isoformat()}
    write_json(folder / 'campaign.json', campaign)
    completed = []
    try:
        campaign_status(folder, campaign, 'running', completed=[], workers=workers)
        if (phase not in ('development', 'confirmation') or
                type(workers) is not int or workers not in (1, 2, 3, 4)):
            raise ValueError('invalid campaign configuration')
        sources = freeze(folder)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_invoke, name, phase, folder) for name in DOMAINS]
            for future in as_completed(futures):
                completed.append(future.result())
                campaign_status(folder, campaign, 'running', completed=completed, workers=workers)
        write_json(folder / 'processes.json', completed)
        integrity = preserve(sources)
        failed = [p for p in completed if p['exit_code']]
        if failed:
            campaign_status(folder, campaign, 'instrument_error', failed=failed)
            return 1
        reports = {d: _read(folder / d / 'result.json') for d in DOMAINS}
        result = {'schema': 'echo5.closure-campaign.v1', **campaign,
                  'status': 'measured_pending_independent_audit', 'sources_sha256': sources['own']['sha256'],
                  'integrity': integrity, 'domain_results': {d: digest(r) for d, r in reports.items()},
                  'gates': {d: r['gates'] for d, r in reports.items()},
                  'release_eligible': False, 'sitl_required': True, 'browser_validation_required': True,
                  's6_in_scope': False}
        _reconcile_campaign(folder, campaign, result, sources)
        write_json(folder / 'result.json', result)
        manifest = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'status.json'}
        write_json(folder / 'manifest.json', manifest)
        campaign_status(folder, campaign, 'measured_pending_independent_audit', result=result)
        return 0
    except Exception as exc:
        write_json(folder / 'instrument-error.json', {'type': type(exc).__name__, 'message': str(exc),
                   'completed': completed, 'traceback': traceback.format_exc()})
        campaign_status(folder, campaign, 'instrument_error', error=f'{type(exc).__name__}: {exc}')
        return 1


def audit_worker(domain, output):
    folder = Path(output)
    started = time.monotonic()
    try:
        receipt = _read(folder / 'receipt.json')
        campaign = _worker_campaign(folder, receipt['split'])
        report, config, receipt, journal = _domain_receipts(folder.parent, domain, campaign, root=folder)
        module = module_for(domain)
        name = 'audit_report' if domain in ('curriculum', 'mission') else 'audit_benchmark'
        auditor = getattr(module, name, None)
        options = {'replay': True} if domain == 'transfer' else {}
        if not callable(auditor):
            raise ValueError('Explicit independent auditor required: ' + domain + '.' + name)
        audit = auditor(report, **options)
        _validate_domain_audit(domain, report, audit)
        _same(_domain_receipts(folder.parent, domain, campaign, root=folder),
              (report, config, receipt, journal), domain + ' evidence changed during audit')
        write_json(folder / 'audit.json', {'result': audit, 'domain': domain,
                   'split': campaign['phase'], 'campaign_id': campaign['campaign_id'],
                   'result_sha256': digest(report), 'config_sha256': digest(config),
                   'result_config_sha256': digest(report['config']), 'receipt_sha256': digest(receipt),
                   'seconds': time.monotonic() - started, 'journal': journal})
    except Exception as exc:
        write_json(folder / 'audit-error.json', {'type': type(exc).__name__, 'message': str(exc),
                                                'traceback': traceback.format_exc()})
        status(folder, 'audit_failed', domain=domain, error=str(exc))
        raise


def _reconcile_domain_audits(folder, campaign, reports):
    gates, hashes = {}, {}
    for domain in DOMAINS:
        path = folder / domain / 'audit.json'
        raw = path.read_bytes()
        wrapper = json.loads(raw)
        report, config, receipt, journal = _domain_receipts(folder, domain, campaign)
        _same(report, reports[domain], domain + ' report changed during audit')
        for key, expected in {'domain': domain, 'split': campaign['phase'],
                              'campaign_id': campaign['campaign_id'], 'result_sha256': digest(report),
                              'config_sha256': digest(config), 'result_config_sha256': digest(report['config']),
                              'receipt_sha256': digest(receipt), 'journal': journal}.items():
            _same(wrapper.get(key), expected, domain + ' audit.' + key)
        _validate_domain_audit(domain, report, wrapper['result'])
        gates[domain] = wrapper['result']['gates']
        hashes[domain] = hashlib.sha256(raw).hexdigest()
    return gates, hashes


def audit_campaign(folder, workers=4):
    folder = Path(folder).resolve()
    if type(workers) is not int or workers not in (1, 2, 3, 4):
        raise ValueError('invalid audit worker count')
    if (folder / 'audit.json').exists():
        raise FileExistsError('Audit receipt already exists; preserve it in place')
    campaign = {'campaign_id': None, 'phase': None}
    completed, manifest, integrity, gates, hashes = [], {}, {}, {}, {}
    result, error = None, None
    try:
        campaign = _read(folder / 'campaign.json')
        if (type(campaign) is not dict or not isinstance(campaign.get('campaign_id'), str) or
                not campaign['campaign_id'] or campaign.get('phase') not in ('development', 'confirmation')):
            campaign = {'campaign_id': None, 'phase': None}
            raise ValueError('Invalid campaign identity')
        campaign_status(folder, campaign, 'auditing', completed=[])
        manifest = _read(folder / 'manifest.json')
        required = {'campaign.json', 'sources.json', 'sources.zip', 'contracts.json', 'result.json', 'processes.json'}
        required.update(f'{domain}/{name}' for domain in DOMAINS for name in
                        ('config.json', 'result.json', 'receipt.json', 'thought.jsonl'))
        verify_manifest(folder, manifest, required)
        sources = _read(folder / 'sources.json')
        verify_archive(folder, sources)
        preserve(sources)
        result = _read(folder / 'result.json')
        reports = _reconcile_campaign(folder, campaign, result, sources)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for future in as_completed([pool.submit(_invoke, d, result['phase'], folder, audit=True) for d in DOMAINS]):
                completed.append(future.result())
                campaign_status(folder, campaign, 'auditing', completed=completed)
        # Replay must not mutate the measurements it claims to audit.
        verify_manifest(folder, manifest, required)
        integrity = preserve(sources)
        _reconcile_campaign(folder, campaign, result, sources)
        if len(completed) != len(DOMAINS) or any(p['exit_code'] != 0 for p in completed):
            raise ValueError('One or more independent domain auditors failed')
        gates, hashes = _reconcile_domain_audits(folder, campaign, reports)
        _same(gates, result['gates'], 'independent and aggregate gates')
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        hashes = {d: hashlib.sha256((folder / d / 'audit.json').read_bytes()).hexdigest()
                  for d in DOMAINS if (folder / d / 'audit.json').is_file()}
    valid = error is None
    receipt = {'schema': 'echo5.closure-audit.v1', 'campaign_id': campaign['campaign_id'],
               'valid': valid, 'processes': completed, 'integrity': integrity,
               'manifest_sha256': digest(manifest), 'domain_gates': gates,
               'domain_audits_sha256': hashes, 'error': error,
               'scientific_gates_not_implied_by_valid_audit': True}
    write_json(folder / 'audit.json', receipt)
    campaign_status(folder, campaign, 'audited' if valid else 'audit_failed', result=result,
                    audit_valid=valid, error=error)
    return 0 if valid else 1
