"""Live bidirectional session; no harness route reaches PX4."""
import argparse
import hashlib
import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path

from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.flight1s.worldbuild import build_effective
from echoai.nexus0.pattern1r_v4.contract import configuration
from .development import train
from .rig import models
from .space import Space, source_sdf
from .transport import Caged

HERE = Path(__file__).resolve().parent
ROOT = ECHOAI/'lab/compose1-v3/sitl-development'


def run(root, seed, mode='echo32', *, condition='static', snapshot=None):
    root.mkdir(parents=True, exist_ok=False)
    out = root/'out'
    out.mkdir()
    space = Space(seed, condition)
    source = source_sdf(space)
    effective = build_effective(source, hashlib.sha256(source).hexdigest())
    marker = b'  </world>'
    data = effective.data.replace(marker,
        b'    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">'
        b'<render_engine>ogre2</render_engine></plugin>\n'+marker)
    (root/'source.sdf').write_bytes(source)
    (root/'world.sdf').write_bytes(data)
    for name, text in models().items():
        path = root/'models'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    shutil.copyfile(HERE/'assets/live_runner.py', root/'live_runner.py')
    shutil.copyfile(HERE.parent/'pattern1r_v4/assets/flightrunner_survey.py', root/'flightrunner_survey.py')
    cfg = configuration()
    cfg['timeouts'] = dict(cfg['timeouts'], episode_s=600)
    intervention = None
    if condition == 'dynamic':
        source_cell = space.rotate((space.wall_x, -space.gap_y, 0))
        target_cell = space.rotate((space.wall_x, space.gap_y, 0))
        intervention = dict(entity='barrier_'+str(sorted(space.solids).index(source_cell)),
                            source=[source_cell[0]*3, source_cell[1]*3, 2],
                            target=[target_cell[0]*3, target_cell[1]*3, 2], after_movements=2)
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    save(root/'configuration.json', dict(seed=seed, mode=mode, condition=condition,
        image_id=runtime['image_id'], px4_binary_sha256=runtime['px4_binary_sha256'],
        source_sha256=hashlib.sha256(source).hexdigest(), effective_sha256=hashlib.sha256(data).hexdigest(),
        config=cfg, world_intervention=intervention))
    snapshot = snapshot or train()
    save(root/'training.json', snapshot)
    (root/'code').mkdir()
    for path in HERE.glob('*.py'):
        shutil.copyfile(path, root/'code'/path.name)
    agent = Caged(snapshot, space.goal, mode, space.energy)
    errors = open(root/'container.err', 'x')
    journal = open(root/'journal.jsonl', 'x', buffering=1)
    argv = ['podman', 'run', '--rm', '--pull=never', '--network=none', '--security-opt',
            'label=disable', '--tmpfs', '/tmp', '-i',
            '-e', 'HOME=/out/wd', '-e', 'FLIGHT1S_HEARTBEAT_S=30',
            '-e', 'FLIGHT1S_PARAMETERS='+json.dumps(cfg['px4_parameters'], sort_keys=True),
            '-v', f'{root}:/flight:ro', '-v', f'{out}:/out',
            runtime['image_id'], 'python3', '/flight/live_runner.py',
            json.dumps(dict(timeouts=cfg['timeouts'], world_intervention=intervention), sort_keys=True)]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=errors, text=True, bufsize=1)
    started = time.monotonic()
    result = dict(ok=False, cause='no result')
    try:
        while True:
            if time.monotonic()-started > 750:
                raise TimeoutError('container watchdog')
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
            if event.get('kind') == 'observation':
                response = agent.call(event['raw'])
                journal.write(json.dumps(dict(side='agent', epoch=event['epoch'], response=response), sort_keys=True)+'\n')
                # Only this WSP can affect execution. Diagnostics never enter PX4.
                process.stdin.write(json.dumps(dict(wsp=response['wsp']))+'\n')
                process.stdin.flush()
                print(root.name, event['epoch'], response['status'],
                      response.get('prediction'), 'depth', response.get('depth'), flush=True)
            elif event.get('kind') == 'result':
                result = event
                break
        process.wait(timeout=30)
    except Exception as exc:
        result = dict(ok=False, cause=repr(exc))
        # EOF lets the private runner abort and land; preserve all evidence.
        process.stdin.close()
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
    finally:
        agent.close()
        errors.close()
        journal.close()
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()
    save(root/'session.json', dict(result=result, returncode=process.returncode,
                                   wall_s=time.monotonic()-started))
    print(json.dumps({k: result.get(k) for k in ('ok', 'error', 'cause', 'steps', 'wall_s')}, sort_keys=True), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--seed', type=int, default=20261901)
    parser.add_argument('--mode', default='echo32')
    parser.add_argument('--condition', default='static', choices=('static', 'dynamic', 'closed', 'low_energy'))
    args = parser.parse_args()
    run(ROOT/args.label, args.seed, args.mode, condition=args.condition)


if __name__ == '__main__':
    main()
