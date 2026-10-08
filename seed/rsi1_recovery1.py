"""Declared CPU transport recovery of RSI1; original run remains immutable."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import signal
import sys

from seed import rsi1 as r
from seed import rsi1_queue as q

ORIGINAL = r.ROOT
ROOT = r.REPO / 'lab/research/echo-rsi1-recovery1-20261002'
BACKEND = Path('/usr/bin/llama-cli')
LAUNCHER = r.REPO / 'lab/tools/rsi1-recovery1/llama-cpu'
BASE_SOURCES = r.SOURCES
BASE_CONFIGURATION = deepcopy(r.CFG)
BASE_INTEGRITY = r.integrity
BASE_PROPOSE = r.propose
EXTRA_SOURCES = ('seed/rsi1_recovery1.py', 'tests/test_rsi1_recovery1.py',
                 'docs/ECHO-RSI1-RECOVERY1.md', 'lab/tools/rsi1-recovery1/llama-cpu')


def original_receipt(root=ORIGINAL):
    """Only the first-call transport failure with no model output is recoverable."""
    status = json.loads((root / 'status.json').read_text())
    budget = json.loads((root / 'budget.json').read_text())
    if status.get('stage') != 'BLOCKED' or 'local model process exited -6' not in status.get('message', ''):
        raise RuntimeError('original is not the declared first-call CPU transport failure')
    if budget.get('model_calls_reserved') != 1 or budget.get('reserved_call_ids') != ['311-llm_only-1']:
        raise RuntimeError('original model call history differs; no implicit restart')
    if (root / 'result.json').exists() or (root / 'exam-freeze.json').exists() \
            or any((root / 'calls').glob('*.json')):
        raise RuntimeError('original has model or exam results; restart must be reconsidered')
    profile = json.loads((root / 'profile.json').read_text())
    if profile['runtime'] != sys.version or profile['configuration'] != BASE_CONFIGURATION:
        raise RuntimeError('original runtime or scientific configuration differs')
    if any(r.file_sha(r.REPO / src) != sha for src, sha in profile['sources'].items()):
        raise RuntimeError('original frozen sources changed')
    return {'model_calls_reserved': 1, 'spend_eur': 0,
            'files': {str(p.relative_to(root)): r.file_sha(p)
                      for p in sorted(root.rglob('*')) if p.is_file()},
            'model_sha256': profile['model_sha256'], 'backend_sha256': profile['llama_cli_sha256'],
            'model_path': profile['model_path'], 'generations_saved': len(list((root / 'generations').glob('*/*/*.json')))}


def configure():
    r.ROOT = ROOT
    r.SOURCES = BASE_SOURCES + EXTRA_SOURCES
    r.CFG = deepcopy(BASE_CONFIGURATION)


def integrity():
    profile = BASE_INTEGRITY()
    receipt = json.loads((ROOT / 'recovery.json').read_text())
    if original_receipt() != receipt['original']:
        raise RuntimeError('original blocked evidence changed')
    if r.file_sha(BACKEND) != receipt['original']['backend_sha256']:
        raise RuntimeError('underlying llama backend changed')
    if r.file_sha(ROOT / 'preflight.json') != receipt['preflight_sha256']:
        raise RuntimeError('transport preflight changed')
    if r.file_sha(q.PROBE / 'result.json') != receipt['probe2_result_sha256'] or not q.gate():
        raise RuntimeError('PROBE2 completion evidence changed')
    preflight = json.loads((ROOT / 'preflight.json').read_text())
    for filename, field in (('preflight-prompt.txt', 'prompt_sha256'),
                            ('preflight.stdout.log', 'stdout_sha256'),
                            ('preflight.stderr.log', 'stderr_sha256')):
        if r.file_sha(ROOT / filename) != preflight[field]:
            raise RuntimeError('transport preflight raw evidence changed')
    return profile


def accounting():
    receipt = json.loads((ROOT / 'recovery.json').read_text())
    path = ROOT / 'budget.json'
    measured = json.loads(path.read_text()) if path.exists() else {'model_calls_reserved': 0}
    spent = measured['model_calls_reserved'] + receipt['prior_calls'] + receipt['preflight_calls']
    if spent > 59:
        raise RuntimeError('recovery aggregate model-call budget exceeded')
    value = {'at': r.now(), 'original_failed_calls': receipt['prior_calls'],
             'transport_preflight_calls': receipt['preflight_calls'],
             'recovery_calls_reserved': measured['model_calls_reserved'],
             'total_calls_reserved': spent, 'cap': 59, 'spend_eur': 0,
             'original_cpu_generations_retained': receipt['original']['generations_saved'],
             'original_cpu_generations_reused': False}
    r.atomic(ROOT / 'total-budget.json', value)
    return value


def prepare():
    original = original_receipt()
    if r.file_sha(BACKEND) != original['backend_sha256']:
        raise RuntimeError('original backend changed')
    preflight = json.loads((ROOT / 'preflight.json').read_text())
    if preflight.get('returncode') != 0 or preflight.get('model_calls') != 1 \
            or preflight.get('gpu_compute_detected') is not False \
            or preflight.get('cpu_compute_detected') is not True:
        raise RuntimeError('one successful CPU-only fixture preflight is required')
    if preflight['model_sha256'] != original['model_sha256'] \
            or preflight['launcher_sha256'] != r.file_sha(LAUNCHER):
        raise RuntimeError('transport preflight used a different model or launcher')
    if not q.gate():
        raise RuntimeError('valid completed PROBE2 receipt is required')
    if not (ROOT / 'profile.json').exists():
        r.atomic(ROOT / 'recovery.json', {'at': r.now(), 'original': original,
                 'prior_calls': 1, 'preflight_calls': 1, 'cap': 59,
                 'preflight_sha256': r.file_sha(ROOT / 'preflight.json'),
                 'probe2_result_sha256': r.file_sha(q.PROBE / 'result.json'),
                 'change': 'CPU transport only; no scientific thresholds or data changed'})
        r.prepare(original['model_path'], LAUNCHER)
    integrity()
    accounting()


def propose(*args, **kwargs):
    try:
        return BASE_PROPOSE(*args, **kwargs)
    finally:
        accounting()


def interrupted(signum, frame):
    accounting()
    r.status('BLOCKED', error='Signal', message=f'recovery interrupted by signal {signum}; no automatic retry')
    raise SystemExit(128 + signum)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    args = parser.parse_args()
    configure()
    r.integrity = integrity
    r.propose = propose
    prepare()
    if args.command == 'run':
        signal.signal(signal.SIGTERM, interrupted)
        try:
            r.run()
        except Exception as exc:
            accounting()
            r.status('BLOCKED', error=type(exc).__name__, message=str(exc))
            raise
        finally:
            accounting()


if __name__ == '__main__':
    main()
