"""Host side of one DRONE-3 flight: world build, cage, container, relay.

The container gets the world, the models and read-only code; it never talks to
the agent directly. The agent gets public observations only. The host relays
the agent's WSP and published prediction, nothing else, and journals both
sides with host monotonic time. Fault injection for `agent_hang` freezes the
caged agent when the runner announces the preregistered point.
"""
import hashlib
import json
import select
import shutil
import subprocess
import time
from pathlib import Path

from echoai.nexus0.compose1_v3.rig import models
from echoai.nexus0.compose1_v3.space import Space, source_sdf
from echoai.nexus0.flight1s.worldbuild import build_effective
from echoai.nexus0.pattern1r_v4.contract import configuration
from .transport import MODULES as AGENT_MODULES, PARENT_MODULES as AGENT_PARENT, Caged

HERE = Path(__file__).resolve().parent
ECHOAI = HERE.parents[1]
RUNNER_MODULES = ('constants.py', 'gate.py', 'fusion1/core.py', 'fusion1/integration.py',
                  'compose1_v3/perception.py', 'cause1/core.py', 'px41/core.py', 'power1/core.py',
                  'safe1/core.py', 'safe1/service.py', 'transfer3/calib_c1.py',
                  'drone3/__init__.py', 'drone3/contract.py', 'drone3/calibration.py', 'drone3/energy.py',
                  'drone3/gates.py', 'drone3/gateway.py', 'drone3/supervisor.py', 'drone3/probes.py')
RUNNER_PARENT = ('core/qn.py', 'core/wsp.py')
ASSETS = {'runner.py': HERE/'assets/runner.py',
          'live_runner.py': ECHOAI/'nexus0/compose1_v3/assets/live_runner.py',
          'flightrunner_survey.py': ECHOAI/'nexus0/pattern1r_v4/assets/flightrunner_survey.py'}
WATCHDOG_S = 1800


def agent_code():
    """sha256 of every module mounted into the agent's cage."""
    out = {'nexus0/'+m: hashlib.sha256((ECHOAI/'nexus0'/m).read_bytes()).hexdigest() for m in AGENT_MODULES}
    out.update({'../'+m: hashlib.sha256((ECHOAI.parent/m).read_bytes()).hexdigest() for m in AGENT_PARENT})
    return out


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'x') as f:
        json.dump(value, f, sort_keys=True, indent=2)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def intervention(space):
    """COMPOSE-1's dynamic change: the open gap closes and the mirror one opens.

    Private trigger: the first observation in which the agent's own public
    evidence admits the open gap while the body is still on the home side of the
    wall. The decision taken on that observation is discarded unexecuted (it
    describes a world that no longer exists) and the agent observes again.
    """
    source_cell = space.rotate((space.wall_x, -space.gap_y, 0))
    target_cell = space.rotate((space.wall_x, space.gap_y, 0))
    home_side = sorted(list(space.rotate((x, y, 0))[:2]) for x in range(0, space.wall_x) for y in range(-2, 3))
    return dict(entity='barrier_'+str(sorted(space.solids).index(source_cell)),
                source=[source_cell[0]*3, source_cell[1]*3, 2],
                target=[target_cell[0]*3, target_cell[1]*3, 2], trigger='first_admitted_from_home_side',
                home_side=home_side)


def build(root, spec):
    """World, models and the container's code. Returns the runner configuration."""
    space = Space(spec['seed'], 'dynamic' if spec['condition'] == 'contradiction' else 'static')
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
    for name, source_path in ASSETS.items():
        shutil.copyfile(source_path, root/name)
    for name in RUNNER_MODULES:
        dest = root/'echoai/nexus0'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ECHOAI/'nexus0'/name, dest)
    for name in RUNNER_PARENT:
        shutil.copyfile(ECHOAI.parent/name, root/name)
    flight = configuration()
    timeouts = dict(flight['timeouts'], episode_s=WATCHDOG_S-120)
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    cfg = dict(seed=spec['seed'], condition=spec['condition'], physics_seed=spec['physics_seed'],
               timeouts=timeouts, battery=spec['battery'], power_model=spec['power_model'],
               offset=spec['offset'], handover_remaining=spec.get('handover_remaining'),
               fault=spec.get('fault'),
               world_intervention=intervention(space) if spec['condition'] == 'contradiction' else None)
    return space, cfg, flight, runtime, hashlib.sha256(source).hexdigest(), hashlib.sha256(data).hexdigest()


def run(root, spec, snapshot, *, mode='echo32', power_policy='cost', lock_sha256=None, echo=print):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    out = root/'out'
    out.mkdir()
    space, cfg, flight, runtime, source_sha, effective_sha = build(root, spec)
    init = dict(model=snapshot, goal=list(space.goal), offset=spec['offset'],
                power_model=spec['power_model'], mode=mode, power_policy=power_policy)
    save(root/'configuration.json', dict(spec=spec, runner=cfg, image_id=runtime['image_id'],
                                         px4_binary_sha256=runtime['px4_binary_sha256'],
                                         source_sha256=source_sha, effective_sha256=effective_sha,
                                         agent_init_sha256=digest(init), mode=mode, power_policy=power_policy,
                                         lock_sha256=lock_sha256, agent_code=agent_code()))
    agent = Caged(init)
    errors = open(root/'container.err', 'x')
    journal = open(root/'journal.jsonl', 'x', buffering=1)

    def note(side, **value):
        journal.write(json.dumps(dict(side=side, mono_ns=time.monotonic_ns(), **value), sort_keys=True)+'\n')

    note('agent', ready=agent.ready)
    argv = ['podman', 'run', '--rm', '--pull=never', '--network=none', '--security-opt', 'label=disable',
            '--tmpfs', '/tmp', '-i', '-e', 'HOME=/out/wd', '-e', 'FLIGHT1S_HEARTBEAT_S=30',
            '-e', 'FLIGHT1S_PARAMETERS='+json.dumps(flight['px4_parameters'], sort_keys=True),
            '-v', f'{root}:/flight:ro', '-v', f'{out}:/out', runtime['image_id'],
            'python3', '/flight/runner.py', json.dumps(cfg, sort_keys=True)]
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
                               text=True, bufsize=1)
    started = time.monotonic()
    result = dict(ok=False, cause='no result')
    frozen = False
    peak = 0
    latencies = []
    try:
        while True:
            if time.monotonic()-started > WATCHDOG_S:
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
            kind = event.get('kind')
            if kind == 'observation':
                note('backend', kind='observation', epoch=event['epoch'], raw_sha256=digest(event['raw']))
                if frozen:
                    note('host', kind='not_relayed', epoch=event['epoch'], reason='agent_frozen')
                    continue
                sent = time.monotonic_ns()
                try:
                    response = agent.call(event['raw'], deadline_s=5)
                except (TimeoutError, RuntimeError) as exc:
                    note('host', kind='agent_failure', epoch=event['epoch'], error=repr(exc))
                    continue
                elapsed = time.monotonic_ns()-sent
                latencies.append(elapsed)
                peak = max(peak, agent.peak_rss_kb())
                note('agent', epoch=event['epoch'], response=response, sent_mono_ns=sent, latency_ns=elapsed)
                # Only the WSP and its published prediction cross to execution.
                process.stdin.write(json.dumps(dict(wsp=response['wsp'], prediction=response['prediction']))+'\n')
                process.stdin.flush()
                echo(root.name, event['epoch'], response['status'], response['prediction'],
                     (response.get('power') or {}).get('reason'))
            elif kind == 'inject':
                agent.freeze()
                frozen = True
                note('host', kind='injection', fault=event['fault'])
            elif kind == 'result':
                result = event
                note('backend', kind='result', result=event)
                break
            elif kind == 'origin':
                note('backend', kind='origin')
        process.wait(timeout=60)
    except Exception as exc:
        result = dict(ok=False, cause=repr(exc))
        process.stdin.close()
        try:
            process.wait(timeout=90)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=15)
    finally:
        peak = max(peak, agent.peak_rss_kb())
        agent.close()
        errors.close()
        journal.close()
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()
    save(root/'session.json', dict(result=result, returncode=process.returncode,
                                   wall_s=time.monotonic()-started, agent_peak_rss_kb=peak,
                                   agent_latency_ns=latencies))
    echo(json.dumps(dict(case=root.name, ok=result.get('ok'), vetoed=result.get('vetoed'),
                         mission_end=result.get('mission_end'), error=result.get('error') or result.get('cause')),
                    sort_keys=True))
    return result
