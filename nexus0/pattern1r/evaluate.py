"""PATTERN-1R evaluator: GROUND-1's groups, plus what identity claims.

The consumer's own file is loaded here and fed the records rebuilt from the
private raw samples, so its signatures must be reproducible from the sensors
alone. Each emitted signature is matched to the silhouette that produced it,
and that silhouette to the true object by ray casts the consumer never sees.
School and exam are split by survey leg, fixed in the contract. The learner is
PATTERN-1's memory, imported: it sees signatures and nothing else, and the
exam writes nothing.
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
from echoai.nexus0.pattern1 import InvariantPatternMemory
from . import contract as p1r

HERE = Path(__file__).resolve().parent
CONSUMER = HERE/'assets/consumer.py'
_spec = importlib.util.spec_from_file_location('pattern1r_consumer', CONSUMER)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

EXTRA_KEYS = {'wsp', 'sightings'}
# GROUND-1's own constants travel with its groups.
CLOSED, BASE_LINK_IN_MODEL, GROUND_LIMITS = gev.CLOSED, gev.BASE_LINK_IN_MODEL, gev.GROUND_LIMITS
LIMITS = sev.LIMITS
load_private, load_transcript = sev.load_private, sev.load_transcript
case, rebuild, feed = gev.case, gev.rebuild, gev.feed
PATTERN_LIMITS = dict(identity=0.75, confusion=0.15, min_exam=20, min_school=20, vote_beams=9,
                      settled=0.9, purity=0.6)


def recompute(records):
    g = G.Ground('')
    for r in records:
        feed(g, r)
    g.close()
    return g.sightings


def canonical_sha256(transcript, packets, sightings):
    line = json.dumps(dict(sev.mirror_tally(transcript), wsp=packets, sightings=sightings),
                      sort_keys=True) + '\n'
    return hashlib.sha256(line.encode()).hexdigest()


def legs(trace):
    """Survey legs that reached their goal, with the window they were flown in."""
    out = []
    for leg in (trace.get('stage_marks') or {}).get('survey') or []:
        # The arc is flown, not hopped (amendment 2): the whole leg is the
        # window, because the body is looking the whole time.
        if leg.get('settled_ns') and leg.get('end_ns') and leg.get('begin_ns'):
            out.append(dict(view=leg['view'], begin=leg['begin_ns'], end=leg['end_ns'],
                            school=leg['view'] in p1r.SCHOOL_POSES))
    return out


def leg_of(capture_ns, legs_):
    for leg in legs_:
        if leg['begin'] <= capture_ns <= leg['end']:
            return leg
    return None


def sensor_pose(entry):
    R = sev.rotation(*entry['body'][4:7])
    m = sev.apply(R, tuple(gev.BASE_LINK_IN_MODEL[k] + s1.MOUNT_M[k] for k in range(3)))
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


def sightings_truth(records, package, lim=PATTERN_LIMITS):
    """Per LiDAR record, the true object of each silhouette, in the consumer's
    own order. None where the truth cannot be cast."""
    boxes = sev.boxes(package)
    barrier = {i for i, name in enumerate(sorted(package.roles)) if package.roles[name] == 'barrier'}
    out = []
    for r in records:
        if r['source'] != 'lidar':
            continue
        if not (r['valid'] and r['status'] == 'ok') or len(r['values']) != len(G.COS) \
                or not r['raw'] or not r['raw'].get('body'):
            out.append([])
            continue
        R, o = sensor_pose(r['raw'])
        per = []
        for first, count, _ in G.silhouettes(r['values']):
            votes = Counter()
            step = max(1, count // lim['vote_beams'])
            for k in range(0, count, step):
                who = beam_box(R, o, r['raw'], boxes, (first + k) % len(G.COS))
                if who is not None:
                    votes[who] += 1
            top = votes.most_common(1)[0][0] if votes else None
            per.append(top if top in barrier else None)
        out.append(per)
    return out


def identity(trace, records, package, report, lim=PATTERN_LIMITS, mutant=None):
    """The learner: school on its legs, then a frozen exam on the others."""
    g = {}
    emitted = report.get('sightings') if isinstance(report.get('sightings'), list) else None
    honest = recompute(records)
    g['signatures_only'] = [case('recomputed_from_raw_samples', emitted == honest,
                                 emitted=len(emitted or []), recomputed=len(honest)),
                            case('shape', bool(emitted) and all(
                                isinstance(x, list) and len(x) == 2 and all(isinstance(v, int) for v in x)
                                and 0 <= x[1] <= 0xFFFF for x in emitted))]
    plan = legs(trace)
    planned = p1r.ARC['poses']
    g['survey'] = [case('legs_settled', len(plan) >= lim['settled']*planned,
                        settled=len(plan), planned=planned, limit=lim['settled']),
                   case('both_halves', {leg['school'] for leg in plan} == {True, False})]
    truth = sightings_truth(records, package)
    lidar = [r for r in records if r['source'] == 'lidar']
    if emitted is None or emitted != honest or len(truth) != len(lidar):
        for name in ('identity', 'frozen'):
            g[name] = [case('aligned_sightings', False, emitted=len(emitted or []), recomputed=len(honest))]
        return g
    # Walk the emitted stream in order, tagging each signature with its object.
    school, exam = [], []
    k = 0
    for r, per in zip(lidar, truth):
        for who in per:
            if k >= len(emitted):
                break
            capture, sig = emitted[k]
            k += 1
            leg = leg_of(capture, plan)
            if leg is None or who is None:
                continue
            (school if leg['school'] else exam).append((who, sig))
    mem = InvariantPatternMemory()
    fam = {}
    for who, sig in school:
        f = mem.observe(sig, 0)
        fam.setdefault(who, Counter())[f] += 1
    home = {who: c.most_common(1)[0][0] for who, c in fam.items()}
    before = mem.snapshot_hash()
    same = other = unknown = 0
    for who, sig in exam:
        if mutant == 'frozen_write':
            mem.observe(sig, 0)          # studying during the exam
        p = mem.predict(sig)
        f = p[0] if p else None
        if f is None:
            unknown += 1
        elif home.get(who) == f:
            same += 1
        else:
            other += 1
    after = mem.snapshot_hash()
    n = len(exam)
    acc = same/n if n else None
    conf = other/n if n else None
    g['identity'] = [case('same_object', acc is not None and n >= lim['min_exam']
                          and len(school) >= lim['min_school'] and acc >= lim['identity'],
                          accuracy=acc, exam=n, school=len(school), objects=len(home),
                          limit=lim['identity']),
                     case('other_object', conf is not None and conf <= lim['confusion'],
                          confusion=conf, unknown=unknown/n if n else None, limit=lim['confusion'])]
    # Two objects in one family would score a perfect exam and mean nothing.
    purity = {who: c.most_common(1)[0][1]/sum(c.values()) for who, c in fam.items()}
    g['identity'].append(case('objects_separated',
                              len(set(home.values())) == len(home) and len(home) > 1
                              and min(purity.values(), default=0) >= lim['purity'],
                              objects=len(home), families=len(set(home.values())),
                              purity=round(min(purity.values(), default=0), 3)))
    g['frozen'] = [case('exam_writes_nothing', before == after, before=before[:12], after=after[:12]),
                   case('cam_intact', mem.capacity == 64)]
    return g


def episode(trace, P, T, report, forwarder, package, spec, *, condition, bounds, cable=None,
            lim=None, glim=None, plim=None):
    """SENSOR-1S and GROUND-1 groups on the packets, then PATTERN-1R's own."""
    tally = {k: v for k, v in report.items() if k not in EXTRA_KEYS | {'debug'}}
    records = rebuild(T, P)
    try:
        groups = gev.episode(trace, P, T, dict(tally, wsp=report.get('wsp')), forwarder, package, spec,
                             condition=condition, bounds=bounds, lim=lim, cable=None, glim=glim)
    except Exception as exc:
        groups = {'execution': [case('sensor_evaluator', False, error=type(exc).__name__+': '+str(exc)[:200])]}
    c = cable if isinstance(cable, dict) else {}
    canon = canonical_sha256(T, report.get('wsp'), report.get('sightings'))
    extra = set(report) - set(sev.mirror_tally([])) - EXTRA_KEYS
    groups['single_cable'] = [case('report_keys', not extra and report.get('sightings') is not None,
                                   extra=sorted(extra)),
                              case('stream_bytes', c.get('stderr_lines') == 1 and c.get('back_bytes') == 0
                                   and c.get('returncode') == 0 and c.get('stderr_sha256') == canon,
                                   stderr_lines=c.get('stderr_lines'), back_bytes=c.get('back_bytes'),
                                   returncode=c.get('returncode'),
                                   canonical=c.get('stderr_sha256') == canon)]
    try:
        groups.update(identity(trace, records, package, report, lim=plim or PATTERN_LIMITS,
                               mutant=spec.get('pattern_mutant')))
    except Exception as exc:
        groups['identity'] = [case('identity_evaluator', False, error=type(exc).__name__+': '+str(exc)[:200])]
    return groups


summarize = sev.summarize
