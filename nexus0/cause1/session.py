"""One new flight, isolated public consumer, private randomized intervention."""
import argparse
import hashlib
import json
import select
import shutil
import subprocess
import time
from pathlib import Path

from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.compose1_v3.space import Space, source_sdf
from echoai.nexus0.compose1_v3.rig import models
from echoai.nexus0.flight1s.worldbuild import build_effective
from echoai.nexus0.pattern1r_v4.contract import configuration
from .core import wsp
from .transport import Caged

HERE = Path(__file__).resolve().parent
ROOT = ECHOAI/'lab/cause1'
CONDITIONS = ('none', 'self', 'external', 'both')


def settings(seed, condition):
    if condition not in CONDITIONS:
        raise ValueError('condition')
    sign = 1 if seed % 2 else -1
    return dict(seed=seed, condition=condition, wall_mm=6000+500*(seed % 3),
                external_mm=-1000*sign if condition in ('external', 'both') else 0,
                intention=wsp((0 if sign == 1 else 1) if condition in ('self', 'both') else 6))


def source(config):
    base = source_sdf(Space(0), empty=True)
    size = '30 0.2 6'
    geometry = f'<geometry><box><size>{size}</size></box></geometry>'
    wall = (f'<model name="cause_wall"><static>true</static><pose>0 {config["wall_mm"]/1000} 3 0 0 0</pose>'
            f'<link name="link"><collision name="collision">{geometry}</collision>'
            f'<visual name="visual">{geometry}</visual></link></model>\n').encode()
    return base.replace(b'  </world>', wall+b'  </world>')


def run(root, seed, condition, *, physics_seed=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    out = root/'out'
    out.mkdir()
    config = settings(seed, condition)
    world = source(config)
    effective = build_effective(world, hashlib.sha256(world).hexdigest()).data
    effective = effective.replace(b'  </world>',
        b'<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">'
        b'<render_engine>ogre2</render_engine></plugin>\n  </world>')
    (root/'source.sdf').write_bytes(world)
    (root/'world.sdf').write_bytes(effective)
    for name, content in models().items():
        dest = root/'models'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    for path, name in ((HERE/'assets/runner.py', 'runner.py'),
                       (HERE/'core.py', 'cause_core.py'),
                       (HERE.parent/'compose1_v3/assets/live_runner.py', 'live_runner.py'),
                       (HERE.parent/'pattern1r_v4/assets/flightrunner_survey.py', 'flightrunner_survey.py')):
        shutil.copyfile(path, root/name)
    cfg = configuration()
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    save(root/'configuration.json', dict(**config, runtime=runtime, config=cfg, physics_seed=physics_seed))
    agent = Caged()
    errors = open(root/'container.err', 'x')
    journal = open(root/'journal.jsonl', 'x', buffering=1)
    argv = ['podman', 'run', '--rm', '--pull=never', '--network=none', '--security-opt',
            'label=disable', '--tmpfs', '/tmp', '-i', '-e', 'HOME=/out/wd',
            '-e', 'FLIGHT1S_HEARTBEAT_S=30',
            '-e', 'FLIGHT1S_PARAMETERS='+json.dumps(cfg['px4_parameters'], sort_keys=True),
            '-v', f'{root}:/flight:ro', '-v', f'{out}:/out', runtime['image_id'],
            'python3', '/flight/runner.py', json.dumps(dict(timeouts=cfg['timeouts'],
                wall_mm=config['wall_mm'], external_mm=config['external_mm'], physics_seed=physics_seed), sort_keys=True)]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=errors, text=True, bufsize=1)
    started = time.monotonic()
    result = dict(ok=False, error='no_result')
    try:
        while time.monotonic()-started < 260:
            if not select.select([process.stdout], [], [], 1)[0]:
                if process.poll() is not None:
                    break
                continue
            line = process.stdout.readline()
            if not line:
                break
            try:
                event = json.loads(line)
            except ValueError:
                continue
            journal.write(json.dumps(dict(side='backend', event=event), sort_keys=True)+'\n')
            if event.get('kind') == 'before':
                request = dict(intention=config['intention'], before=event['raw'])
                call_start = time.monotonic_ns()
                response = agent.call(request)
                journal.write(json.dumps(dict(side='agent', request=request, response=response,
                    call_latency_ns=time.monotonic_ns()-call_start), sort_keys=True)+'\n')
                process.stdin.write(json.dumps(dict(wsp=response['wsp']))+'\n')
                process.stdin.flush()
            elif event.get('kind') == 'after':
                request = dict(execution=event['execution'], after=event['raw'])
                call_start = time.monotonic_ns()
                response = agent.call(request)
                journal.write(json.dumps(dict(side='agent', request=request, response=response,
                    call_latency_ns=time.monotonic_ns()-call_start), sort_keys=True)+'\n')
                print(root.name, response['label'], response['north_delta_mm'],
                      response['external_delta_mm'], flush=True)
            elif event.get('kind') == 'result':
                result = event
                break
        process.stdin.close()
        process.wait(timeout=35)
    except Exception as exc:
        result = dict(ok=False, error=repr(exc))
        if not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=40)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
    finally:
        agent.close()
        errors.close()
        journal.close()
        process.stdout.close()
    save(root/'session.json', dict(result=result, returncode=process.returncode, wall_s=time.monotonic()-started))
    print(root.name, 'flight_ok', result['ok'], result.get('error'), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--seed', type=int, default=20262501)
    parser.add_argument('--condition', choices=CONDITIONS, default='self')
    args = parser.parse_args()
    if not run(ROOT/'development'/args.label, args.seed, args.condition)['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
