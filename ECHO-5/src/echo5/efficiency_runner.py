"""Frozen-source paired efficiency pilot, with separate-process reproduction."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from .closure import ROOT, freeze, preserve, verify_archive, run_process, status, write_json
from .evaluation import digest
from .trace import Recorder, verify_journal
from .budget import BudgetExceeded

PROTOCOL = ROOT/'docs/SEARCH-EFFICIENCY-PILOT.json'
STAGES = ('search_development', 'search_fresh', 'exploration', 'curriculum')


def validate_protocol(plan):
    if (plan.get('schema') != 'echo5.efficiency.pilot.v1'
            or plan.get('automatic_promotion') is not False
            or plan.get('stage') != 'paired_development_and_fresh_probe'
            or set(plan.get('stages', {})) != set(STAGES)):
        raise ValueError('registered non-promoting efficiency pilot required')
    return plan


def measure(stage, config, journal, progress):
    if stage.startswith('search_'):
        from .search_efficiency_study import run_benchmark
        return run_benchmark(config, journal=journal, progress=progress)
    if stage == 'exploration':
        from .exploration_study import run_benchmark
        return run_benchmark(config, journal=journal, progress=progress)
    if stage == 'curriculum':
        from .curriculum_lazy import run_efficient_benchmark
        return run_efficient_benchmark(**config, journal=journal)
    raise ValueError('unregistered stage')


def worker(folder, stage, action):
    folder = Path(folder)
    parent = folder.parent
    sources = json.loads((parent/'sources.json').read_text())
    plan = validate_protocol(json.loads((parent/'plan.json').read_text()))
    preserve(sources)
    verify_archive(parent, sources)
    if digest(plan) != digest(json.loads(PROTOCOL.read_text())):
        raise ValueError('registered plan changed')
    started = time.monotonic()
    def progress(**facts):
        elapsed = time.monotonic()-started
        facts.pop('elapsed_seconds', None)
        if facts.get('completed') and facts.get('total'):
            facts['estimated_remaining_seconds'] = elapsed / facts['completed'] * (facts['total']-facts['completed'])
        status(folder, action, stage=stage, pid=os.getpid(), elapsed_seconds=elapsed, **facts)
    with Recorder(folder/('thought.jsonl' if action == 'measure' else 'audit-thought.jsonl')) as journal:
        journal.write(kind='efficiency_stage_begin', stage=stage, operation=action,
                      source_sha256=sources['own']['sha256'], plan_sha256=digest(plan))
        if action not in ('measure', 'audit'):
            raise ValueError('invalid worker action')
        extra = {}
        try:
            if action == 'audit' and stage == 'exploration':
                from .exploration_study import audit_benchmark, normalize_config
                report = json.loads((folder/'result.json').read_text())
                if report.get('config') != normalize_config(plan['stages'][stage]):
                    raise ValueError('native report differs from registered cohort')
                extra = audit_benchmark(report, progress=progress)
                if extra.get('valid') is not True:
                    raise ValueError('native trajectory audit failed')
            else:
                report = measure(stage, plan['stages'][stage], journal, progress)
        except BudgetExceeded as exc:
            journal.write(kind='efficiency_budget_exhausted', stage=stage, error=str(exc), instrument_error=False)
            status(folder, 'budget_exhausted', stage=stage, error=str(exc), instrument_error=False)
            raise
        if report.get('instrument_valid') is False:
            raise ValueError('invalid measurement instrument')
        if action == 'measure':
            write_json(folder/'result.json', report)
        else:
            original = json.loads((folder/'result.json').read_text())
            if digest(original) != digest(report):
                raise ValueError('fresh-process reproduction differs from recorded result')
            write_json(folder/'audit.json', {'valid': True, 'fresh_process_reproduction': True,
                'native_audit': extra, 'result_sha256': digest(original),
                'plan_sha256': digest(plan), 'source_sha256': sources['own']['sha256'],
                'journal': verify_journal(folder/'thought.jsonl'), 'promotion': False,
                'scope': 'receipt reproduction, with independent native/construction judges; not a universal proof'})
        journal.write(kind='efficiency_stage_end', stage=stage, operation=action)
    preserve(sources)
    status(folder, 'measured' if action == 'measure' else 'audited', stage=stage,
           elapsed_seconds=time.monotonic()-started, pid=os.getpid(), promotion=False)


def run(folder):
    folder = Path(folder)
    started, completed = time.monotonic(), {}
    try:
        sources = freeze(folder)
        verify_archive(folder, sources)
        plan = validate_protocol(json.loads(PROTOCOL.read_text()))
        write_json(folder/'plan.json', plan)
        for stage in STAGES:
            target = folder/stage
            target.mkdir()
            for action in ('measure', 'audit'):
                status(folder, action, stage=stage, completed_stages=list(completed),
                       pid=os.getpid(), elapsed_seconds=time.monotonic()-started)
                command = [sys.executable, '-I', str(ROOT/'scripts/efficiency.py'),
                           'worker', '--output', str(target), '--stage', stage, '--action', action]
                receipt = run_process(command, target/(action+'.log'), cwd=ROOT, timeout=7200)
                write_json(target/(action+'-process.json'), receipt)
                if receipt['exit_code'] != 0 or receipt['timed_out']:
                    child_status = target/'status.json'
                    if child_status.exists() and json.loads(child_status.read_text()).get('phase') == 'budget_exhausted':
                        raise BudgetExceeded(f'{stage}/{action}: measurement incomplete within budget')
                    raise RuntimeError(f'{stage}/{action}: {receipt}')
                preserve(sources)
            report = json.loads((target/'result.json').read_text())
            audit = json.loads((target/'audit.json').read_text())
            if (audit.get('valid') is not True or audit.get('result_sha256') != digest(report)
                    or audit.get('source_sha256') != sources['own']['sha256']
                    or audit.get('plan_sha256') != digest(plan)):
                raise ValueError('audit does not bind registered report, plan and sources')
            completed[stage] = {'result_sha256': digest(report), 'audit_sha256': digest(audit),
                                'audit_valid': True, 'result': str(target/'result.json')}
        verify_archive(folder, sources)
        write_json(folder/'result.json', {'schema': 'echo5.efficiency.run.v1', 'stages': completed,
            'audits_valid': True, 'promotion': False, 'S6': 'out_of_scope',
            'source_sha256': sources['own']['sha256'], 'plan_sha256': digest(plan),
            'elapsed_seconds': time.monotonic()-started, 'sources': preserve(sources)})
        status(folder, 'completed_audited_pilot', completed_stages=list(completed),
               elapsed_seconds=time.monotonic()-started, promotion=False)
    except Exception as exc:
        status(folder, 'budget_exhausted' if isinstance(exc, BudgetExceeded) else 'instrument_error',
               error=str(exc), traceback=traceback.format_exc(),
               completed_stages=list(completed), elapsed_seconds=time.monotonic()-started, promotion=False)
        raise


def launch(folder):
    folder = Path(folder).resolve()
    if not folder.is_relative_to((ROOT/'artifacts').resolve()):
        raise ValueError('output must be in artifacts/')
    folder.mkdir(parents=True, exist_ok=False)
    command = [str(ROOT/'.venv-sandbox/bin/python'), '-I', str(ROOT/'scripts/efficiency.py'),
               'run', '--output', str(folder)]
    try:
        with (folder/'process.log').open('x') as stream:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as exc:
        status(folder, 'launch_error', error=str(exc), pid=None)
        raise
    receipt = {'pid': process.pid, 'launched_utc': datetime.now(timezone.utc).isoformat(),
               'command': command, 'output': str(folder), 'log': str(folder/'process.log')}
    write_json(folder/'launched.json', receipt)
    return receipt
