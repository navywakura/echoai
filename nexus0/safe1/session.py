"""Pinned, isolated SITL fault session. Previous milestone sources stay intact."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.compose1_v3.space import Space, source_sdf
from echoai.nexus0.compose1_v3.rig import models
from echoai.nexus0.flight1s.worldbuild import build_effective
from echoai.nexus0.pattern1r_v4.contract import configuration

HERE = Path(__file__).resolve().parent
ROOT = ECHOAI/'lab/safe1'
CONDITIONS = ('nominal', 'sensor_stale', 'network_stale', 'process_exit', 'process_hang', 'bad_proposal')
SOURCES = {'runner.py': HERE/'assets/runner.py', 'worker.py': HERE/'assets/worker.py',
           'model.json': ECHOAI/'lab/power1/model.json',
           'live_runner.py': HERE.parent/'compose1_v3/assets/live_runner.py',
           'flightrunner_survey.py': HERE.parent/'pattern1r_v4/assets/flightrunner_survey.py'}
for package, module in [('safe1', 'core'), ('safe1', 'ipc'), ('safe1', 'service'), ('cause1', 'core'), ('px41', 'core'), ('power1', 'core')]:
    SOURCES[f'echoai/nexus0/{package}/{module}.py'] = HERE.parent/package/(module+'.py')


def world():
    source = source_sdf(Space(0), empty=True)
    plugin = b'<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>\n'
    source = source.replace(b'  </world>', plugin+b'  </world>')
    return source, build_effective(source, hashlib.sha256(source).hexdigest()).data


def run(root, seed, condition):
    if condition not in CONDITIONS:
        raise ValueError('condition')
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    out = root/'out'
    out.mkdir()
    source, effective = world()
    (root/'source.sdf').write_bytes(source)
    (root/'world.sdf').write_bytes(effective)
    for name, content in models().items():
        dest = root/'models'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    for dest, source in SOURCES.items():
        target = root/dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    config = configuration()
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    cfg = dict(seed=seed, condition=condition, physics_seed=seed*10+CONDITIONS.index(condition), timeouts=config['timeouts'])
    save(root/'configuration.json', dict(**cfg, flight=config, runtime=runtime))
    argv = ['podman', 'run', '--rm', '--pull=never', '--network=none', '--security-opt', 'label=disable',
            '--tmpfs', '/tmp', '-e', 'HOME=/out/wd', '-e', 'FLIGHT1S_HEARTBEAT_S=30',
            '-e', 'FLIGHT1S_PARAMETERS='+json.dumps(config['px4_parameters'], sort_keys=True),
            '-v', f'{root}:/flight:ro', '-v', f'{out}:/out', runtime['image_id'],
            'python3', '/flight/runner.py', json.dumps(cfg, sort_keys=True)]
    with open(root/'stdout.log', 'x') as stdout, open(root/'stderr.log', 'x') as stderr:
        process = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=260)
    save(root/'session.json', dict(returncode=process.returncode))
    print(root.name, 'exit', process.returncode, flush=True)
    return process.returncode == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--seed', type=int, default=20263401)
    parser.add_argument('--condition', choices=CONDITIONS, default='nominal')
    args = parser.parse_args()
    if not run(ROOT/'pilot'/args.label, args.seed, args.condition):
        raise SystemExit(1)
