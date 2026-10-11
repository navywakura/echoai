"""Launch a bounded, named local job and retain its PID/log after this session."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', choices=('checks', 'development', 'confirmation', 'audit', 'panel'))
    parser.add_argument('--output')
    parser.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=4)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    base = ROOT / 'artifacts'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    target = Path(args.output).resolve() if args.output else base / f'closure-{args.job}-{stamp}'
    if not target.is_relative_to(base.resolve()):
        raise ValueError('Output must stay under ECHO-5/artifacts')
    python = ROOT / '.venv/bin/python'
    if args.job == 'checks':
        command = [str(python), '-I', str(ROOT / 'scripts/checks.py'), str(target)]
    elif args.job == 'panel':
        command = [str(ROOT / '.venv-sandbox/bin/python'), '-I', str(ROOT / 'scripts/control.py'), '--port', str(args.port)]
    else:
        command = [str(python), '-I', str(ROOT / 'scripts/closure.py'),
                   'audit' if args.job == 'audit' else 'campaign', '--output', str(target),
                   '--workers', str(args.workers)]
        if args.job != 'audit':
            command += ['--phase', args.job]
    jobs = base / 'jobs'
    jobs.mkdir(parents=True, exist_ok=True)
    name = f'{args.job}-{stamp}-{os.getpid()}'
    log_path = jobs / f'{name}.log'
    with log_path.open('x') as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    receipt = {'job': args.job, 'pid': process.pid, 'launched_utc': datetime.now(timezone.utc).isoformat(),
               'command': command, 'log': str(log_path), 'output': str(target),
               'status': 'launched_not_yet_validated'}
    (jobs / f'{name}.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
