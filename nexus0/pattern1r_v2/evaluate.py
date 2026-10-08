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
noise_verdict = sev.noise_verdict
case, rebuild, feed = gev.case, gev.rebuild, gev.feed
PATTERN_LIMITS = dict(identity=0.75, confusion=0.15, min_exam=20, min_school=20, vote_beams=9, min_family_evidence=32,
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


def annotated_sightings(records, package, lim=PATTERN_LIMITS):
    """Reconstruct each emission and its own real beams, in the same step.

    Truth is used only here. Skipping a small silhouette cannot shift the next
    signature, and gaps cannot invent a contiguous run of nonexistent echoes.
    """
    boxes = sev.boxes(package)
    barrier = {i for i, name in enumerate(sorted(package.roles)) if package.roles[name] == 'barrier'}
    consumer, annotated = G.Ground(''), []
    for r in records:
        before = len(consumer.sightings)
        feed(consumer, r)
        for k in range(before, len(consumer.sightings)):
            capture, sig = consumer.sightings[k]
            beams = consumer.sighting_beams[k]
            votes, why = Counter(), 'missing_pose'
            if r['raw'] and r['raw'].get('body'):
                R, origin = sensor_pose(r['raw'])
                sample = beams[::max(1, len(beams)//lim['vote_beams'])]
                for beam in sample:
                    votes[beam_box(R, origin, r['raw'], boxes, beam)] += 1
                top, count = votes.most_common(1)[0]
                if top in barrier and count/len(sample) >= 0.6:
                    who, why = top, 'barrier'
                else:
                    who, why = None, 'ambiguous_or_other'
            else:
                who = None
            annotated.append(dict(capture=capture, signature=sig, who=who, why=why))
    consumer.close()
    return consumer.sightings, annotated


def score_identity(school, exam, expected, lim=PATTERN_LIMITS, mutant=None):
    """No truth reaches observe/predict; labels are only the external judge."""
    mem, fam = InvariantPatternMemory(min_hits=lim['min_family_evidence']), {}
    for who, sig in school:
        f = mem.observe(sig, 0)
        fam.setdefault(who, Counter())[f] += 1
    home = {who: c.most_common(1)[0][0] for who, c in fam.items()}
    before = mem.snapshot_hash()
    same = other = unknown = 0
    for who, sig in exam:
        if mutant == 'frozen_write':
            mem.observe(sig, 0)
        pred = mem.predict(sig)
        f = pred[0] if pred else None
        if f is None:
            unknown += 1
        elif home.get(who) == f:
            same += 1
        else:
            other += 1
    after, n = mem.snapshot_hash(), len(exam)
    accuracy, confusion = (same/n, other/n) if n else (None, None)
    purity = {who: c.most_common(1)[0][1]/sum(c.values()) for who, c in fam.items()}
    school_counts, exam_counts = Counter(w for w, _ in school), Counter(w for w, _ in exam)
    identity_cases = [
        case('same_object', n >= lim['min_exam'] and len(school) >= lim['min_school']
             and accuracy is not None and accuracy >= lim['identity'],
             accuracy=accuracy, exam=n, school=len(school), same=same, objects=len(home), limit=lim['identity']),
        case('other_object', confusion is not None and confusion <= lim['confusion'],
             confusion=confusion, confused=other, exam=n, unknown=unknown, limit=lim['confusion']),
        case('objects_separated', set(home) == set(expected) and None not in home.values()
             and len(set(home.values())) == len(expected) and len(expected) > 1
             and min(purity.values(), default=0) >= lim['purity'],
             objects=len(home), families=len(set(home.values())), purity=min(purity.values(), default=0)),
        case('each_object_examined', bool(expected) and all(
             school_counts[w] >= lim['min_school'] and exam_counts[w] >= lim['min_exam'] for w in expected),
             counts=[dict(object=w, school=school_counts[w], exam=exam_counts[w]) for w in sorted(expected)])]
    return dict(identity=identity_cases, frozen=[
        case('exam_writes_nothing', before == after, before=before, after=after),
        case('cam_intact', mem.capacity == 64)])


def survey_geometry(trace, package):
    check = p1r.route_check(package)
    marks = (trace.get('stage_marks') or {}).get('survey') or []
    expected = [p+[p1r.ARC['altitude_mm']] for p in p1r.arc_viewpoints(package)]
    targets = [m.get('target_mm') for m in marks]
    windows = [(m['begin_ns'], m['end_ns']) for m in marks if m.get('begin_ns') and m.get('end_ns')]
    samples = [s for s in trace.get('samples', []) if any(a <= s[0] <= b for a, b in windows)]
    boxes = p1r.barriers(package)
    distances = [p1r.point_box_distance([s[k]/1000 for k in (1, 2, 3)], b)
                 for s in samples for b in boxes]
    minimum = min(distances) if distances else None
    return [case('admissible_route', check['ok'], **{k:v for k,v in check.items() if k != 'ok'}),
            case('prescribed_targets', targets == expected, observed=len(targets), expected=len(expected)),
            case('observed_body_clearance', minimum is not None and minimum >= p1r.BODY_RADIUS_MM,
                 samples=len(samples), minimum_mm=round(minimum, 3) if minimum is not None else None,
                 required_mm=p1r.BODY_RADIUS_MM)]


def identity(trace, records, package, report, lim=PATTERN_LIMITS, mutant=None):
    emitted = report.get('sightings') if isinstance(report.get('sightings'), list) else None
    honest, annotations = annotated_sightings(records, package, lim)
    g = dict(signatures_only=[
        case('recomputed_from_raw_samples', emitted == honest, emitted=len(emitted or []), recomputed=len(honest)),
        case('shape', bool(emitted) and all(isinstance(x, list) and len(x) == 2
             and all(type(v) is int for v in x) and 0 <= x[1] <= 0xFFFF for x in emitted)),
        case('emission_alignment', len(honest) == len(annotations) and all(
             row[0] == a['capture'] and row[1] == a['signature'] for row,a in zip(honest, annotations)),
             emitted=len(honest), annotated=len(annotations))])
    plan = legs(trace)
    g['survey'] = [case('legs_settled', len(plan) >= lim['settled']*p1r.ARC['poses'],
                         settled=len(plan), planned=p1r.ARC['poses'], limit=lim['settled']),
                   case('both_halves', {leg['school'] for leg in plan} == {True, False})]
    g['geometry'] = survey_geometry(trace, package)
    aligned = (isinstance(emitted, list) and len(emitted) == len(honest)
               and bool(emitted) and all(isinstance(row, list) and len(row) == 2
                   and all(type(v) is int for v in row) and row[0] == expected_row[0]
                   and 0 <= row[1] <= 0xFFFF for row, expected_row in zip(emitted, honest)))
    if not aligned:
        for name in ('identity', 'frozen'):
            g[name] = [case('aligned_sightings', False, emitted=len(emitted or []), recomputed=len(honest))]
        return g
    school, exam, excluded = [], [], Counter()
    for a, actual in zip(annotations, emitted):
        leg = leg_of(a['capture'], plan)
        if leg is None:
            excluded['outside_reached_legs'] += 1
        elif a['who'] is None:
            excluded[a['why']] += 1
        else:
            (school if leg['school'] else exam).append((a['who'], actual[1]))
    g['signatures_only'].append(case('accounted_observations',
        len(school)+len(exam)+sum(excluded.values()) == len(honest),
        school=len(school), exam=len(exam), excluded=dict(excluded), total=len(honest)))
    expected = {i for i,name in enumerate(sorted(package.roles)) if package.roles[name] == 'barrier'}
    g.update(score_identity(school, exam, expected, lim, mutant))
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
