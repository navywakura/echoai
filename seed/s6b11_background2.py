"""B11 user-service supervisor. No repeated submissions or experimental changes."""
import fcntl
import json
import os
import subprocess
import sys

from seed import s6b11 as s

UNIT = 'echoai-s6b11'


def run():
    with (s.ROOT / 'supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        s.integrity()
        s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(), 'state': 'RUNNING', 'unit': UNIT})
        with (s.ROOT / 'process.log').open('a') as stream:
            module = 'seed.s6b11_recovery2' if (s.ROOT / 'transport-recovery2/profile.json').exists() else 'seed.s6b11'
            process = subprocess.run([sys.executable, '-u', '-m', module, 'follow'], cwd=s.REPO,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(), 'state': 'FINISHED',
                 'unit': UNIT, 'exit_code': process.returncode})
        return process.returncode


def start():
    s.integrity()
    assert not (s.ROOT / 'closed.json').exists(), 'B11 already closed'
    active = subprocess.run(['systemctl', '--user', 'is-active', UNIT + '.service'],
                            capture_output=True, text=True)
    assert active.stdout.strip() not in ('active', 'activating'), 'B11 already running'
    command = ['systemd-run', '--user', '--collect', '--unit=' + UNIT,
               '--property=Restart=no', '--property=KillMode=control-group',
               '--property=WorkingDirectory=' + str(s.REPO),
               '--property=StandardOutput=append:' + str(s.ROOT / 'supervisor.log'),
               '--property=StandardError=inherit', sys.executable, '-u', '-m', 'seed.s6b11_background2', 'run']
    subprocess.run(command, check=True)
    receipt = {'at': s.now(), 'unit': UNIT, 'profile_sha256': s.sha(s.integrity()), 'restart': 'no'}
    s.atomic(s.ROOT / 'launch.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['start']:
        start()
    elif sys.argv[1:] == ['run']:
        raise SystemExit(run())
    else:
        raise SystemExit('use start or run')
