"""DYNAMIC-1 evaluator: GROUND-1 groups, plus what the motion records claim.

The consumer file is loaded here and fed the records rebuilt from the private
raw samples, so its output must be reproducible from the sensors alone. Each
record is then matched to the object that produced it by ray casts against the
truth boxes at that instant — the mover's box is where the harness had walked
it to — and judged: was the moving object called moving, were the still ones
left alone, and was the predicted displacement the real one?
"""
import hashlib
import importlib.util
import json
import math
from collections import Counter
from pathlib import Path

from echoai.nexus0.ground1 import evaluate as gev
from echoai.nexus0.sensor1s import contract as s1
from echoai.nexus0.sensor1s_v3 import evaluate as sev
from . import contract as d1

HERE = Path(__file__).resolve().parent
CONSUMER = HERE/'assets/consumer.py'
_spec = importlib.util.spec_from_file_location('dynamic1_consumer', CONSUMER)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

EXTRA_KEYS = {'wsp', 'motion'}
LIMITS = sev.LIMITS
CLOSED, BASE_LINK_IN_MODEL, GROUND_LIMITS = gev.CLOSED, gev.BASE_LINK_IN_MODEL, gev.GROUND_LIMITS
load_private, load_transcript, noise_verdict = sev.load_private, sev.load_transcript, sev.noise_verdict
case, rebuild, feed = gev.case, gev.rebuild, gev.feed
# Amendment 1, corrected by amendment 2: fixed on the development batch of 8
# flights, under its worst case, and against what the world actually did.
# Detection 0.873-0.967; prediction 29-58 mm median and 89-102 p95; still
# objects flagged 0.158-0.241 while something moved and 0.091-0.093 when
# nothing did, because a hovering body drifts and cannot know it. A consumer
# that predicts stillness scores 118 mm, so the median limit sits below that.
DYNAMIC_LIMITS = dict(detect=0.80, quiet=0.30, quiet_control=0.15, gap=0.50,
                      predict_mm=90, predict_p95_mm=160, min_records=50, vote_beams=9,
                      moved_mm=2000)


def recompute(records):
    g = G.Ground('')
    for r in records:
        feed(g, r)
    g.close()
    return g.motion


def canonical_sha256(transcript, packets, motion):
    line = json.dumps(dict(sev.mirror_tally(transcript), wsp=packets, motion=motion),
                      sort_keys=True) + '\n'
    return hashlib.sha256(line.encode()).hexdigest()


def mover_truth(trace):
    """The mover's world position over time, as the world published it."""
    m = (trace.get('stage_marks') or {}).get('mover') or {}
    steps = [(s['sim_time_ns'], s['seen_mm']) for s in m.get('steps', []) if s.get('seen_mm')]
    return m, steps


def position_at(steps, t_ns):
    if not steps:
        return None
    if t_ns <= steps[0][0]:
        return steps[0][1]
    for (t0, p0), (t1, p1) in zip(steps, steps[1:]):
        if t0 <= t_ns <= t1 and t1 > t0:
            f = (t_ns - t0) / (t1 - t0)
            return [p0[k] + (p1[k] - p0[k]) * f for k in range(3)]
    return steps[-1][1]


def boxes_at(package, mover, t_ns, steps):
    """The truth boxes, with the mover where it was at that instant."""
    boxes = list(sev.boxes(package))
    names = sorted(package.roles)
    if not mover:
        return boxes, None
    try:
        index = names.index(mover['model'])
    except ValueError:
        return boxes, None
    home = mover['home_mm']
    now = position_at(steps, t_ns) or home
    dx = (now[0] - home[0])/1000.0
    dy = (now[1] - home[1])/1000.0
    lo, hi = boxes[index]
    boxes[index] = ((lo[0]+dx, lo[1]+dy, lo[2]), (hi[0]+dx, hi[1]+dy, hi[2]))
    return boxes, index


def sensor_pose(entry):
    R = sev.rotation(*entry['body'][4:7])
    m = sev.apply(R, tuple(BASE_LINK_IN_MODEL[k] + s1.MOUNT_M[k] for k in range(3)))
    return R, (entry['body'][1]+m[0], entry['body'][2]+m[1], entry['body'][3]+m[2])


def beam_box(R, o, entry, boxes, i):
    s = entry['sample']
    a = s['angle_min'] + i*s['angle_step']
    d = sev.apply(R, (math.cos(a), math.sin(a), 0.0))
    best, who = math.inf, None
    for b, (lo, hi) in enumerate(boxes):
        h = sev.hit_box(o, d, lo, hi)
        if h and 0.2 < h[0] < best:
            best, who = h[0], b
    return who


def world_velocity_in_sensor(entry, velocity_mm_s):
    """The mover's velocity, as the sensor frame sees it (yaw only; the body hovers)."""
    yaw = entry['body'][6]
    vx, vy = velocity_mm_s[0], velocity_mm_s[1]
    return (vx*math.cos(-yaw) - vy*math.sin(-yaw), vx*math.sin(-yaw) + vy*math.cos(-yaw))


def dynamics(trace, records, package, report, lim=DYNAMIC_LIMITS):
    g = {}
    emitted = report.get('motion') if isinstance(report.get('motion'), list) else None
    honest = recompute(records)
    g['signals_only'] = [case('recomputed_from_raw_samples', emitted == honest,
                              emitted=len(emitted or []), recomputed=len(honest)),
                         case('shape', bool(emitted) and all(
                             isinstance(x, list) and len(x) == 6 and all(type(v) is int for v in x)
                             and x[3] in (0, 1) for x in emitted))]
    mover, steps = mover_truth(trace)
    walked = 0
    if steps:
        walked = int(math.hypot(steps[-1][1][0]-steps[0][1][0], steps[-1][1][1]-steps[0][1][1]))
    # A control flight has no mover on purpose: there is nothing to walk.
    g['mover'] = [case('world_moved_it', walked >= lim['moved_mm'] if mover else True,
                       control=not mover, steps=len(steps), walked_mm=walked,
                       model=mover.get('model'))]
    if emitted is None or len(emitted) != len(honest):
        # Without one record per silhouette there is nothing to line up. A
        # stream that differs in value is still judged: that is the lie.
        for name in ('detection', 'prediction'):
            g[name] = [case('aligned_records', False, emitted=len(emitted or []),
                            recomputed=len(honest))]
        return g
    lidar = [r for r in records if r['source'] == 'lidar']
    k = skipped = 0
    seen = dict(mover=[], still=[])
    for r in lidar:
        if not (r['valid'] and r['status'] == 'ok') or len(r['values']) != len(G.COS):
            continue
        if not r['raw'] or not r['raw'].get('body'):
            # The consumer spoke for this scan; without a body pose there is no
            # truth to match it to. Skip its records, never the count.
            skipped += sum(1 for _, count, _ in G.silhouettes(r['values'])
                           if count >= G.EMIT_MIN_BEAMS)
            k += sum(1 for _, count, _ in G.silhouettes(r['values'])
                     if count >= G.EMIT_MIN_BEAMS)
            continue
        runs = G.silhouettes(r['values'])
        boxes, index = boxes_at(package, mover, r['capture_ns'], steps)
        R, o = sensor_pose(r['raw'])
        for first, count, _ in runs:
            if count < G.EMIT_MIN_BEAMS or k >= len(emitted):
                continue
            rec = emitted[k]
            k += 1
            votes = Counter()
            step = max(1, count // lim['vote_beams'])
            for j in range(0, count, step):
                who = beam_box(R, o, r['raw'], boxes, (first + j) % len(G.COS))
                if who is not None:
                    votes[who] += 1
            if not votes:
                continue
            who = votes.most_common(1)[0][0]
            if package.roles[sorted(package.roles)[who]] not in ('barrier',):
                continue
            moving_now = index is not None and who == index and steps \
                and steps[0][0] <= rec[0] <= steps[-1][0]
            seen['mover' if moving_now else 'still'].append((rec, r['raw']))
    detect = sum(1 for rec, _ in seen['mover'] if rec[3]) / len(seen['mover']) if seen['mover'] else None
    # With nothing moving, every flag is the body's own drift: judge it harder.
    quiet_limit = lim['quiet'] if steps else lim['quiet_control']
    quiet = sum(1 for rec, _ in seen['still'] if rec[3]) / len(seen['still']) if seen['still'] else None
    g['signals_only'].append(case('every_record_matched', skipped == 0, skipped=skipped))
    g['detection'] = [case('moving_called_moving',
                           True if not steps else (detect is not None and detect >= lim['detect']
                           and len(seen['mover']) >= lim['min_records']),
                           fraction=detect, records=len(seen['mover']), limit=lim['detect']),
                      case('still_left_alone', quiet is not None and quiet <= quiet_limit,
                           fraction=quiet, records=len(seen['still']), limit=quiet_limit),
                      case('told_apart', not steps or (detect is not None and quiet is not None
                           and detect - quiet >= lim['gap']),
                           gap=None if detect is None or quiet is None else round(detect-quiet, 3),
                           limit=lim['gap'])]
    errors = []
    judged = seen['mover'] if steps else seen['still']
    for rec, entry in judged:
        if steps:
            # What the world did, not what the harness asked for: set_pose lags,
            # and the body can only be judged against what actually happened.
            here = position_at(steps, rec[0])
            later = position_at(steps, rec[0] + d1.PREDICT_MS * 1_000_000)
            vx, vy = world_velocity_in_sensor(entry, [later[0]-here[0], later[1]-here[1]])
            want = (vx, vy)
        else:
            want = (0.0, 0.0)          # nothing moves: predict standing still
        got = (rec[4] - rec[1], rec[5] - rec[2])
        errors.append(math.hypot(got[0]-want[0], got[1]-want[1]))
    errors.sort()
    median = errors[len(errors)//2] if errors else None
    p95 = errors[int(len(errors)*0.95)] if errors else None
    g['prediction'] = [case('displacement', median is not None and median <= lim['predict_mm']
                            and (p95 or 0) <= lim['predict_p95_mm'],
                            median_mm=None if median is None else round(median),
                            p95_mm=None if p95 is None else round(p95),
                            records=len(errors), limit=lim['predict_mm'])]
    return g


def episode(trace, P, T, report, forwarder, package, spec, *, condition, bounds, cable=None,
            lim=None, glim=None, dlim=None):
    tally = {k: v for k, v in report.items() if k not in EXTRA_KEYS | {'debug'}}
    records = rebuild(T, P)
    try:
        groups = gev.episode(trace, P, T, dict(tally, wsp=report.get('wsp')), forwarder, package, spec,
                             condition=condition, bounds=bounds, lim=lim, cable=None, glim=glim)
    except Exception as exc:
        groups = {'execution': [case('sensor_evaluator', False, error=type(exc).__name__+': '+str(exc)[:200])]}
    c = cable if isinstance(cable, dict) else {}
    canon = canonical_sha256(T, report.get('wsp'), report.get('motion'))
    extra = set(report) - set(sev.mirror_tally([])) - EXTRA_KEYS
    groups['single_cable'] = [case('report_keys', not extra and report.get('motion') is not None,
                                   extra=sorted(extra)),
                              case('stream_bytes', c.get('stderr_lines') == 1 and c.get('back_bytes') == 0
                                   and c.get('returncode') == 0 and c.get('stderr_sha256') == canon,
                                   stderr_lines=c.get('stderr_lines'), back_bytes=c.get('back_bytes'),
                                   returncode=c.get('returncode'),
                                   canonical=c.get('stderr_sha256') == canon)]
    try:
        groups.update(dynamics(trace, records, package, report, lim=dlim or DYNAMIC_LIMITS))
    except Exception as exc:
        groups['detection'] = [case('dynamics_evaluator', False,
                                    error=type(exc).__name__+': '+str(exc)[:200])]
    return groups


summarize = sev.summarize
