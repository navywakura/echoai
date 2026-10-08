"""Pinned simulator session; fixture intentions never depend on true pose."""
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
ROOT = ECHOAI/'lab/px41'
CONDITIONS = ('nominal', 'link_loss')


def run(root, seed, condition):
    if condition not in CONDITIONS:
        raise ValueError('condition')
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    out = root/'out'
    out.mkdir()
    source = source_sdf(Space(0), empty=True)
    effective = build_effective(source, hashlib.sha256(source).hexdigest()).data
    (root/'source.sdf').write_bytes(source)
    (root/'world.sdf').write_bytes(effective)
    for name, content in models().items():
        dest = root/'models'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    for source, dest in [(HERE/'assets/runner.py', 'runner.py'),
                         (HERE/'core.py', 'echoai/nexus0/px41/core.py'),
                         (HERE.parent/'cause1/core.py', 'echoai/nexus0/cause1/core.py'),
                         (HERE.parent/'compose1_v3/assets/live_runner.py', 'live_runner.py'),
                         (HERE.parent/'pattern1r_v4/assets/flightrunner_survey.py', 'flightrunner_survey.py')]:
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
    parser.add_argument('--seed', type=int, default=20262801)
    parser.add_argument('--condition', choices=CONDITIONS, default='nominal')
    args = parser.parse_args()
    if not run(ROOT/'pilot'/args.label, args.seed, args.condition):
        raise SystemExit(1)
