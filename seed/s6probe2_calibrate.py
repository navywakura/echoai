"""Wait for the independent audit, then freeze and calibrate PROBE2 only."""
import json
import subprocess
import sys
import time

from seed import s6probe2 as p


def main():
    review = json.loads((p.ROOT / 'code-review.json').read_text())
    if review.get('valid') is not True or review.get('sources') != p.hashes():
        raise RuntimeError('reviewed PROBE2 sources changed')
    while not p.PROBE1_AUDIT.exists():
        state_file = p.PROBE1_AUDIT.parent / 'status.json'
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        if state.get('stage') == 'BLOCKED':
            raise RuntimeError('independent audit blocked: ' + state.get('message', ''))
        if review['sources'] != p.hashes():
            raise RuntimeError('PROBE2 sources changed while waiting')
        p.atomic(p.ROOT / 'queue-status.json', {'at': p.now(), 'stage': 'WAITING_INDEPENDENT_AUDIT',
                                              'games_started': False, 'audit': state})
        time.sleep(10)
    p.probe1_closure()
    for command in ('prepare', 'estimate'):
        subprocess.run([sys.executable, '-u', '-m', 'seed.s6probe2', command], check=True, cwd=p.REPO)
    estimate = json.loads((p.ROOT / 'estimate.json').read_text())
    parity = json.loads((p.ROOT / 'parity.json').read_text())
    if parity.get('valid') is not True or estimate.get('candidates') != 5 \
            or estimate.get('games_reserved') != 190 or estimate.get('full_run_started') is not False:
        raise RuntimeError('calibration parity or budget differs')
    p.atomic(p.ROOT / 'queue-status.json', {'at': p.now(), 'stage': 'ESTIMATE_READY',
                                         'full_run_started': False, 'estimate': estimate})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        p.atomic(p.ROOT / 'queue-status.json', {'at': p.now(), 'stage': 'BLOCKED',
                                             'error': type(exc).__name__, 'message': str(exc)})
        raise
