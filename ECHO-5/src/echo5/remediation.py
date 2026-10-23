"""Bounded post-r3 research runner. Separate artifacts; never release or S6."""
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from .closure import ROOT, freeze, preserve, run_process, status, write_json, verify_archive
from .budget import BudgetExceeded
from .evaluation import digest
from .trace import Recorder, verify_journal

STAGES = ('exploration', 'semantics', 'transfer', 'search', 'curriculum')
MODULES = dict(exploration='exploration_study', semantics='mission_reference',
               transfer='transfer_independent', search='search_diagnostics',
               curriculum='curriculum_lazy')
PROTOCOL = ROOT / 'config/remediation.json'


def validate_protocol(plan):
    if (type(plan) is not dict or plan.get('schema') != 'echo5.remediation.pilot.v1'
            or plan.get('stage') != 'development_pilot_not_confirmation'
            or plan.get('automatic_promotion') is not False or not all(s in plan for s in STAGES)):
        raise ValueError('development-only remediation protocol required')
    return plan


def _module(stage):
    if stage not in STAGES:
        raise ValueError('unknown research stage')
    return importlib.import_module('echo5.' + MODULES[stage])


def _run(stage, config, journal, progress):
    module = _module(stage)
    if stage == 'exploration':
        return module.run_benchmark(config, journal=journal, progress=progress)
    if stage in ('search', 'transfer', 'curriculum'):
        return module.run_benchmark(**config, journal=journal)
    return module.run_benchmark(**config)


def worker(folder, stage, action):
    """Separate interpreter for each measurement and for each reproduction."""
    folder = Path(folder)
    parent = folder.parent
    sources = json.loads((parent/'sources.json').read_text())
    plan = validate_protocol(json.loads((parent/'plan.json').read_text()))
    preserve(sources)
    verify_archive(parent, sources)
    if digest(plan) != digest(json.loads(PROTOCOL.read_text())):
        raise ValueError('run plan differs from frozen preregistration')
    started = time.monotonic()
    def progress(**facts):
        if facts.get('completed') and facts.get('elapsed_seconds'):
            facts['estimated_remaining_seconds'] = facts['elapsed_seconds']/facts['completed']*(facts['total']-facts['completed'])
        status(folder, action, stage=stage, pid=os.getpid(), **facts)
    status(folder, action, stage=stage, pid=os.getpid())
    with Recorder(folder/('thought.jsonl' if action == 'measure' else 'audit-thought.jsonl')) as journal:
        journal.write(kind='remediation_stage_begin', stage=stage, operation=action,
                      plan_sha256=digest(plan), own_source_sha256=sources['own']['sha256'])
        if action == 'measure':
            try:
                report = _run(stage, plan[stage], journal, progress)
            except BudgetExceeded as exc:
                journal.write(kind='remediation_budget_exhausted', stage=stage,
                              instrument_error=False, error=str(exc))
                status(folder, 'budget_exhausted', stage=stage, error=str(exc),
                       instrument_error=False, measurement_complete=False)
                raise
            write_json(folder/'result.json', report)
            if report.get('instrument_valid') is False:
                raise RuntimeError('measurement instrument invalid: ' + stage)
            result = {'phase': 'measured_pending_audit', 'report_sha256': digest(report)}
        elif action == 'audit':
            report = json.loads((folder/'result.json').read_text())
            if report.get('instrument_valid') is False:
                raise RuntimeError('cannot validate an invalid instrument: ' + stage)
            journal_check = verify_journal(folder/'thought.jsonl')
            if stage == 'exploration':
                module = _module(stage)
                if digest(report.get('config')) != digest(module.normalize_config(plan[stage])):
                    raise ValueError('exploration report differs from registered cohort/budget')
                audit = module.audit_benchmark(report, progress=progress)
            else:
                # Fresh process, same public protocol. Independent data oracles
                # are part of each instrument; replay alone isn't semantic proof.
                replay = _run(stage, plan[stage], journal, progress)
                if digest(report) != digest(replay):
                    raise ValueError('fresh-process reproduction mismatch: ' + stage)
                audit = {'valid': True, 'result_sha256': digest(report),
                         'fresh_process_reproduction': True,
                         'semantic_scope': 'independent references where provided; not formal proof'}
            audit.update(journal=journal_check, own_source_sha256=sources['own']['sha256'],
                         source_unchanged=preserve(sources), promotion=False,
                         result_sha256=digest(report), plan_sha256=digest(plan), stage=stage)
            write_json(folder/'audit.json', audit)
            result = {'phase': 'audited', 'audit_valid': audit['valid']}
        else:
            raise ValueError('unknown worker operation')
        journal.write(kind='remediation_stage_end', stage=stage, operation=action,
                      result=result, elapsed_seconds=time.monotonic()-started)
    preserve(sources)
    verify_archive(parent, sources)
    status(folder, result.pop('phase'), stage=stage, elapsed_seconds=time.monotonic()-started, **result)


def run(folder):
    folder = Path(folder)
    started = time.monotonic()
    stages = {}
    try:
        sources = freeze(folder)
        verify_archive(folder, sources)
        plan = validate_protocol(json.loads(PROTOCOL.read_text()))
        write_json(folder/'plan.json', plan)
        write_json(folder/'identity.json', {'schema': 'echo5.remediation.run.v1',
            'started_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
            'plan_sha256': digest(plan), 'own_source_sha256': sources['own']['sha256'],
            'prior_release_preserved': 'closure-verdict-20261011-r3', 'automatic_promotion': False})
        for stage in STAGES:
            target = folder/stage
            target.mkdir()
            for action in ('measure', 'audit'):
                status(folder, action, stage=stage, completed_stages=list(stages), pid=os.getpid(),
                       elapsed_seconds=time.monotonic()-started)
                argv = [sys.executable, '-I', str(ROOT/'scripts/remediation.py'),
                        'worker', '--output', str(target), '--stage', stage, '--action', action]
                rc = run_process(argv, target/(action+'.log'), cwd=ROOT, timeout=7200)
                # run_process returns a launch/timeout receipt; never interpret an exception
                # or a absent receipt as an inconclusive scientific measurement.
                write_json(target/(action+'-process.json'), rc)
                if rc['exit_code'] != 0 or rc['timed_out']:
                    worker_status = target/'status.json'
                    if worker_status.exists() and json.loads(worker_status.read_text()).get('phase') == 'budget_exhausted':
                        raise BudgetExceeded(f'{stage}: measurement incomplete within budget')
                    raise RuntimeError(f'{stage}/{action} exited {rc["exit_code"]}')
                required = target/('result.json' if action == 'measure' else 'audit.json')
                if not required.is_file():
                    raise RuntimeError(f'{stage}/{action} did not write its receipt')
                preserve(sources)
            audit = json.loads((target/'audit.json').read_text())
            if audit.get('valid') is not True:
                raise RuntimeError('invalid research instrument: ' + stage)
            report = json.loads((target/'result.json').read_text())
            if report.get('instrument_valid') is False or audit.get('result_sha256') != digest(report):
                raise ValueError('audit does not bind the current valid report: ' + stage)
            if (audit.get('plan_sha256') != digest(plan) or audit.get('stage') != stage
                    or audit.get('own_source_sha256') != sources['own']['sha256']):
                raise ValueError('audit belongs to another plan, stage or source revision')
            stages[stage] = {'audit_valid': True, 'result_sha256': digest(report),
                             'audit_sha256': digest(audit),
                             'result': str(target/'result.json'), 'audit': str(target/'audit.json')}
        verify_archive(folder, sources)
        result = {'schema': 'echo5.remediation.result.v1', 'stages': stages,
                  'instrument_audits_valid': True, 'scientific_superiority': 'read_each_experiment',
                  'stage': 'development_pilot_not_confirmation', 'automatic_promotion': False,
                  'S6': 'out_of_scope', 'elapsed_seconds': time.monotonic()-started,
                  'own_source_sha256': sources['own']['sha256'], 'sources': preserve(sources)}
        write_json(folder/'result.json', result)
        status(folder, 'completed_audited_pilot', stages=stages, elapsed_seconds=time.monotonic()-started,
               promotion=False)
    except Exception as exc:
        status(folder, 'budget_exhausted' if isinstance(exc, BudgetExceeded) else 'instrument_error',
               error=str(exc), error_type=type(exc).__name__,
               completed_stages=list(stages), elapsed_seconds=time.monotonic()-started,
               traceback=traceback.format_exc(), promotion=False)
        raise


def launch(folder):
    folder = Path(folder).resolve()
    if not folder.is_relative_to((ROOT/'artifacts').resolve()):
        raise ValueError('research output must be under artifacts/')
    folder.mkdir(parents=True, exist_ok=False)
    command = [str(ROOT/'.venv-sandbox/bin/python'), '-I', str(ROOT/'scripts/remediation.py'),
               'run', '--output', str(folder)]
    try:
        with (folder/'process.log').open('x') as stream:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as exc:
        status(folder, 'launch_error', error=str(exc), pid=None)
        raise
    receipt = {'pid': process.pid, 'launched_utc': datetime.now(timezone.utc).isoformat(),
               'command': command, 'output': str(folder), 'log': str(folder/'process.log'),
               'stage': 'development_pilot_not_confirmation'}
    write_json(folder/'launched.json', receipt)
    return receipt
