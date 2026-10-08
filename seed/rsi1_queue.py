"""Wait for a valid PROBE2 completion, then execute the private free RSI assay."""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

from seed import rsi1 as r

PROBE = r.REPO / 'lab/seed/s6probe2-20261001'


def gate(root=PROBE):
    path = root / 'status.json'
    status = json.loads(path.read_text()) if path.exists() else {}
    if status.get('stage') == 'BLOCKED':
        raise RuntimeError('PROBE2 stopped: resolve its instrument failure before RSI')
    if status.get('stage') != 'DONE':
        return False
    result = json.loads((root / 'result.json').read_text())
    if result['screened'] != 874 or result['model_calls'] != 0 or result['B_measured'] is not False \
            or result['exam_opened'] is not False or result['screen_replays'] != 88 \
            or len(result['soundness_checks']) != 5 \
            or any(c['untouched_identical'] is not True for c in result['soundness_checks']) \
            or any(v['replay_ok'] is not True for v in result['verified']) \
            or result['budget']['scheduled_games'] > 14544:
        raise RuntimeError('PROBE2 completion receipt failed the private-run gate')
    return True


def wait(poll=30, once=False):
    r.integrity()
    with (r.ROOT / 'queue.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while not gate():
            r.integrity()
            r.atomic(r.ROOT / 'queue-status.json', {'at': r.now(), 'stage': 'WAITING_PROBE2',
                'model_calls_started': False, 'spend_eur': 0, 'automatic_run': True})
            if once:
                return
            time.sleep(poll)
        if once:
            return
        from seed import s6probe2
        s6probe2.integrity()  # Read only; never modify the running/frozen condition.
        if (r.ROOT / 'result.json').exists():
            r.atomic(r.ROOT / 'queue-status.json', {'at': r.now(), 'stage': 'ALREADY_DONE'})
            return
        r.atomic(r.ROOT / 'queue-status.json', {'at': r.now(), 'stage': 'RUNNING_RSI1', 'spend_eur': 0})
        subprocess.run([sys.executable, '-u', '-m', 'seed.rsi1', 'run'], cwd=r.REPO, check=True)
        r.atomic(r.ROOT / 'queue-status.json', {'at': r.now(), 'stage': 'DONE', 'spend_eur': 0})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    try:
        wait(once=args.once)
    except Exception as exc:
        r.atomic(r.ROOT / 'queue-status.json', {'at': r.now(), 'stage': 'BLOCKED',
                 'error': type(exc).__name__, 'message': str(exc)})
        raise
