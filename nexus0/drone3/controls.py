"""Controls on the same recorded observations and budgets. None is ever flown.

- horizon one and reactive Q: decision replay on the flight's own observations
  (first divergence and whether the control's proposal would pass the gates),
  plus COMPOSE-1's functional twin on the same room geometry;
- fixed battery percentage: POWER-1's `fixed` Guard on the recorded battery;
- a link that takes the ACK as arrival: the gateway mutant replayed on the
  recorded ACK/telemetry stream, judged against the private pose at ACK time;
- gate ablations: an agent without evidence gating, and SAFE without agent
  liveness or without the latch, replayed on the recorded inputs.
"""
import json
import math
from pathlib import Path

from echoai.nexus0.compose1_v2.functional import mission
from echoai.nexus0.compose1_v3.perception import project
from echoai.nexus0.compose1_v3.space import Space
from echoai.nexus0.power1.core import Guard
from echoai.nexus0.transfer3 import calib_c1
from . import contract as c
from . import gates
from .agent import MissionAgent
from .calibration import abstract
from .energy import battery_sample, guard_frame
from .evaluate import lines, school
from .gateway import CellGateway
from .supervisor import MissionSupervisor


def flight(root):
    root = Path(root)
    cfg = json.loads((root/'configuration.json').read_text())
    rows = lines(root/'out/trace.jsonl')
    journal = lines(root/'journal.jsonl')
    truth = [r for r in lines(root/'out/private.jsonl') if 'body' in r]
    return cfg, rows, journal, truth


def agent_init(cfg, mode):
    spec = cfg['spec']
    space = Space(spec['seed'], 'dynamic' if spec['condition'] == 'contradiction' else 'static')
    return dict(model=school(), goal=list(space.goal), offset=spec['offset'], power_model=spec['power_model'],
                mode=mode, power_policy=cfg['power_policy']), space


def solids_at(root, space, now):
    """Private occupancy at `now`, after the preregistered intervention if any."""
    changes = [r for r in lines(Path(root)/'out/private.jsonl') if r.get('kind') == 'world_change']
    if changes and now >= changes[0]['now_ns']:
        return space.make_solids(-space.gap_y)
    return space.solids


def frame_of(obs):
    return project({k: v for k, v in obs['raw'].items() if k != 'battery'}, 240)


def horizon(root):
    """First decision where one-step / reactive Q differ from the full agent."""
    cfg, rows, journal, truth = flight(root)
    relayed = {r['epoch'] for r in journal if r.get('side') == 'agent' and 'epoch' in r}
    observations = [r for r in rows if r['kind'] == 'observation' and r['epoch'] in relayed]
    init, space = agent_init(cfg, 'echo32')
    out = {}
    for mode in ('one_step', 'q'):
        full, control = MissionAgent(**init), MissionAgent(**dict(init, mode=mode))
        record = dict(identical_decisions=0, first_divergence=None)
        for obs in observations:
            a, b = full.decide(obs['raw']), control.decide(obs['raw'])
            if (a['wsp'], a['prediction']) == (b['wsp'], b['prediction']):
                record['identical_decisions'] += 1
                continue
            kind, _ = c.intention(b['wsp'])
            target = tuple(b['prediction'][:2])
            gate = gates.epistemic(frame_of(obs), kind, target, obs['raw']['now_ns'], cfg['spec']['offset'])
            record['first_divergence'] = dict(epoch=obs['epoch'], full=[a['status'], a['prediction']],
                                              control=[b['status'], b['prediction']],
                                              control_admitted=gate['allowed'],
                                              control_target_occupied=(target+(0,)) in
                                              solids_at(root, space, obs['now_ns']))
            break
        out[mode] = record
    return out


def twin(seed, condition):
    """COMPOSE-1's functional twin of the same room: kinematic, abstract energy."""
    name = 'dynamic' if condition == 'contradiction' else 'static'
    rows = {}
    for mode in ('echo32', 'one_step', 'q'):
        r = mission(school(), seed, name, mode)
        rows[mode] = dict(reached=r['reached'], steps=r['steps'], collisions=r['collisions'],
                          false_facts=r['false_facts'], reserve_violations=r['reserve_violations'])
    return rows


def fixed_battery(root):
    """POWER-1's fixed 20 % policy on the flight's own battery and routes."""
    cfg, rows, journal, truth = flight(root)
    spec = cfg['spec']
    init, space = agent_init(cfg, 'echo32')
    agent = MissionAgent(**init)
    fixed = Guard(spec['power_model'], 'fixed')
    decisions = []
    for obs in [r for r in rows if r['kind'] == 'observation']:
        response = agent.decide(obs['raw'])
        battery = battery_sample(obs['raw']['battery'])
        cell = tuple(obs['cell'])
        route = agent.back_route()
        frame = guard_frame(obs['raw']['now_ns'], battery, cell, space.goal[:2], (0, 0),
                            None if route is None else len(route), agent.reached)
        decisions.append(dict(epoch=obs['epoch'], cost=(response.get('power') or {}).get('reason'),
                              fixed=fixed.decide(frame)['reason']))
        if agent.stopped:
            break
    return decisions


def ack_as_arrival(root):
    """Where the body truly was when a link that trusts the ACK would call arrival."""
    cfg, rows, journal, truth = flight(root)

    def pose(now):
        row = min(truth, key=lambda r: abs(r['now_ns']-now))
        return row['body'][1]*1000, row['body'][2]*1000

    sends = [r for r in rows if r['kind'] == 'send']
    acks = [r for r in rows if r['kind'] == 'ack' and r['accepted']]
    premature = []
    for send, ack in zip(sends, acks):
        x, y = pose(ack['ack']['received_ns'])
        premature.append(round(math.hypot(x-send['target_mm'][0], y-send['target_mm'][1])))
    return dict(transactions=len(premature), claimed_early=sum(d > c.ARRIVAL_MM for d in premature),
                true_distance_at_ack_mm=premature)


def greedy_move(cell, goal):
    """The move a planner without evidence would take: straight at the goal."""
    dx, dy = goal[0]-cell[0], goal[1]-cell[1]
    if dx:
        return (cell[0]+(1 if dx > 0 else -1), cell[1])
    if dy:
        return (cell[0], cell[1]+(1 if dy > 0 else -1))
    return None


def evidence_ablation(root):
    """Epistemic-gate ablation on the same observations.

    COMPOSE-1 v3's search itself only expands admitted cells, so its
    `ignore_evidence` mode changes nothing here. The ablated control is the
    planner without evidence: at each recorded observation, the move straight
    toward the goal hypothesis. Counted: how many of those the epistemic gate
    blocks, and how many blocked targets are truly occupied (private).
    """
    cfg, rows, journal, truth = flight(root)
    init, space = agent_init(cfg, 'echo32')
    proposals = blocked = occupied = forwarded_into_solid = 0
    for obs in [r for r in rows if r['kind'] == 'observation']:
        target = greedy_move(tuple(obs['cell']), space.goal[:2])
        if target is None:
            continue
        proposals += 1
        solid = (target+(0,)) in solids_at(root, space, obs['now_ns'])
        forwarded_into_solid += solid
        if not gates.epistemic(frame_of(obs), 'move', target, obs['raw']['now_ns'], cfg['spec']['offset'])['allowed']:
            blocked += 1
            occupied += solid
    return dict(proposals=proposals, blocked_by_gate=blocked, blocked_targets_truly_occupied=occupied,
                ablated_gate_would_forward_into_solid=forwarded_into_solid)


def safe_ablation(root):
    """SAFE without agent liveness / without the latch, on the recorded health.

    `vetoes` says whether the ablated supervisor still refuses at the check where
    the real one vetoed; `resumes` counts recovery probes it would accept.
    """
    cfg, rows, journal, truth = flight(root)
    spec = cfg['spec']
    veto = next((r for r in rows if r['kind'] == 'veto'), None)
    out = {}
    for mutant in ('', 'no_liveness', 'no_latch'):
        sup = MissionSupervisor(spec['power_model'], spec['offset'], (0, 0), mutant=mutant)
        refused_at_veto = None
        resumes = 0
        for r in rows:
            if r['kind'] == 'check':
                ok = sup.check(r['health'])
                if veto and r['mono_ns'] <= veto['mono_ns'] and not r['ok']:
                    refused_at_veto = not ok
            elif r['kind'] == 'recovery_probe':
                resumes += bool(sup.check(r['health']))
            elif r['kind'] == 'observation':
                sup.occupied(r['cell'])
        out[mutant or 'full'] = dict(vetoes=refused_at_veto, resumes=resumes)
    return out


def calibration(root):
    """C1's two integers on this body's own frames.

    `best_offset` is C1's own consistency estimator run on the flight's frames:
    the transferred calibration should be the best explanation of camera-LiDAR
    agreement here too. `admission_changes` counts cell admissions that a wrong
    mount (1, 0) would change on the same frames: the channel is live, not a flag.
    """
    cfg, rows, journal, truth = flight(root)
    frames = [(obs, frame_of(obs)) for obs in rows if obs['kind'] == 'observation']
    abstracted = [abstract(f) for _, f in frames]
    estimate = calib_c1.estimate(abstracted)
    changes = checked = 0
    for obs, frame in frames:
        for cell in frame['cells']:
            target = tuple(cell['position'][:2])
            now = obs['raw']['now_ns']
            right = gates.epistemic(frame, 'move', target, now, cfg['spec']['offset'])['allowed']
            wrong = gates.epistemic(frame, 'move', target, now, [1, 0])['allowed']
            checked += 1
            changes += right != wrong
    return dict(transferred=cfg['spec']['offset'], best_offset=estimate['offset'],
                agreement=estimate['agreement'], disagreement=estimate['disagreement'],
                consistent=estimate['offset'] == cfg['spec']['offset'],
                admission_changes_with_wrong_mount=changes, cells_checked=checked)
