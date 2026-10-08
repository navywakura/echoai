"""Durable user service, bounded transport recovery and truthful desktop notice."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from seed import s6b12 as s

UNIT = 'echoai-s6b12'


def notify():
    path = s.ROOT / 'closed.json'
    result = json.loads(path.read_text()) if path.exists() else {}
    audit_path = s.ROOT / 'exam/audit.json'
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    green = bool(result.get('s6_green') and audit.get('green') and
                 set(audit.get('checks', {})) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(audit['checks'].values()))
    title = 'ECHO · S6 VERDE, B1–B5 aprobados' if green else 'ECHO · S6 necesita revisión'
    body = ('Resultado y auditoría en docs/ECHO45-S6-B12-RESULTS.md. '
            'El verde global de ECHO-4.5 depende de las demás puertas del roadmap.')
    command = shutil.which('notify-send')
    delivered = False
    if command:
        sent = subprocess.run([command, '--app-name=echoAI', title, body], capture_output=True, text=True)
        delivered = sent.returncode == 0
    s.atomic(s.ROOT / 'notification.json', {'at': s.now(), 'title': title, 'body': body,
        's6_green': green, 'echo45_green': False, 'desktop_delivered': delivered})


def recoverable():
    status = json.loads((s.ROOT / 'status.json').read_text())
    terminals = [json.loads(p.read_text())['status'] for p in s.BASE.glob('c*/terminal.json')]
    return (status.get('message') == 'B12 transport failed; original attempt and details preserved' and
            not any(t != 'COMPLETE' for t in terminals))


def run():
    with (s.ROOT / 'supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        s.integrity()
        result = None
        for attempt in range(1, 4):
            s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(),
                'state': 'RUNNING', 'unit': UNIT, 'attempt': attempt})
            with (s.ROOT / 'process.log').open('a') as log:
                result = subprocess.run([sys.executable, '-u', '-m', 'seed.s6b12', 'follow'],
                    cwd=s.REPO, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            if not result.returncode or attempt == 3 or not recoverable():
                break
            s.atomic(s.ROOT / ('transport-recovery-' + str(attempt) + '.json'),
                     {'at': s.now(), 'reason': 'transport interrupted; same immutable jobs only',
                      'delay_seconds': 30, 'new_sampling_allowed': False})
            time.sleep(30)
        s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(),
            'state': 'FINISHED', 'unit': UNIT, 'attempts': attempt, 'exit_code': result.returncode})
        notify()
        return result.returncode


def start():
    s.integrity()
    assert not (s.ROOT / 'closed.json').exists(), 'B12 already closed'
    active = subprocess.run(['systemctl', '--user', 'is-active', UNIT + '.service'], capture_output=True, text=True)
    assert active.stdout.strip() not in ('active', 'activating'), 'B12 already running'
    command = ['systemd-run', '--user', '--collect', '--unit=' + UNIT,
        '--property=Restart=no', '--property=KillMode=control-group',
        '--property=WorkingDirectory=' + str(s.REPO),
        '--property=StandardOutput=append:' + str(s.ROOT / 'supervisor.log'),
        '--property=StandardError=inherit',
        'systemd-inhibit', '--what=sleep:idle', '--mode=block', '--who=echoAI',
        '--why=S6-B12 campaign and audit in progress',
        sys.executable, '-u', '-m', 'seed.s6b12_background', 'run']
    subprocess.run(command, check=True)
    receipt = {'at': s.now(), 'unit': UNIT, 'profile_sha256': s.sha(s.integrity()),
               'restart': 'no', 'sleep_inhibitor': 'sleep:idle', 'transport_recoveries_max': 2}
    s.atomic(s.ROOT / 'launch.json', receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['start']:
        start()
    elif sys.argv[1:] == ['run']:
        raise SystemExit(run())
    else:
        raise SystemExit('use start or run')
