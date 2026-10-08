"""GROUND-1 evaluator: SENSOR-1S v3's groups, plus what the translation claims.

The consumer's own file is loaded here and fed records rebuilt from the
private raw samples and the host transcript: if its packets depended on
anything but the sensors, the bytes would differ (`sensors_only`), and fed
one record at a time it must emit each packet at its own scan and never
revise one (no future). What the packets say is judged against the private
truth: the obstacle ahead from ray casts at the true sensor pose
(`distance`), the wrench event and touchdown (`push`), and the SENSOR-1S
validity markers of each window (`certainty`). `single_cable` counts every
byte the consumer sent back: one canonical stderr line, exit 0, nothing
else. `cam` runs the emitted stream through the Agent's own slot path
(`loop.Agent._slot_for`) on a real CAM: a structural check of the core, which only fails past 4096 distinct packets; vertex
distances are reported, not judged (contract amendments 1–3,
docs/GROUND1-DESIGN.md).

The true sensor pose corrects a SENSOR-1S truth-model error found while
preparing GROUND-1: PX4's x500_base places base_link 0.24 m above the model
frame whose pose Gazebo reports, and the sensor mount is relative to
base_link. SENSOR-1S's rest-window checks were insensitive to it.
"""
import hashlib
import importlib.util
import itertools
import json
import math
import re
import struct
from pathlib import Path
from types import SimpleNamespace

from echoai.nexus0.loop import Agent
from echoai.nexus0.sensor1s import contract as s1
from echoai.nexus0.sensor1s.model import STOCK
from echoai.nexus0.sensor1s_v3 import evaluate as sev
from echoai.core.cam import Cam
from echoai.core.qn import HAM_LIMIT, hamming16
from echoai.core.spoke import encode_event          # the packet's vertex, as loop.py computes it

HERE = Path(__file__).resolve().parent
CONSUMER = HERE/'assets/consumer.py'
_spec = importlib.util.spec_from_file_location('ground1_consumer', CONSUMER)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def _base_link_in_model():
    m = re.search(r"<model name='x500_base'>\s*<pose>([^<]+)</pose>", (STOCK/'x500_base/model.sdf').read_text())
    x, y, z, r, p, yaw = (float(v) for v in m.group(1).split())
    assert (r, p, yaw) == (0.0, 0.0, 0.0)
    return (x, y, z)


BASE_LINK_IN_MODEL = _base_link_in_model()        # (0, 0, 0.24) in the pinned stock SDF
GROUND_LIMITS = dict(accuracy_stage=0.95, accuracy_episode=0.90, ambiguous_m=0.15, vertical_m=0.05,
                     push_first_ns=400_000_000, push_last_ns=2_000_000_000,
                     touchdown_mm=20, touchdown_before_ns=100_000_000, touchdown_last_ns=2_000_000_000)
# The coordinator is SENSOR-1S v3's: it reads these names from its evaluator.
LIMITS = sev.LIMITS
load_private, load_transcript, noise_verdict = sev.load_private, sev.load_transcript, sev.noise_verdict
EXTRA_KEYS = {'wsp'}
PERCEPTS = [(G.OBSERVAR, G.ALLI), (G.OBSERVAR, G.FUERA), (G.CAMBIAR, G.ALLI),
            (G.CAMBIAR, G.FUERA), (G.DESCONOCIDO, G.DESCONOCIDO)]


def closed_set():
    out = {}
    for (rel, dst), c in itertools.product(PERCEPTS, (100, 40)):
        e = dict(C=c, U=40 if dst == G.ALLI else 0, A=80 if rel == G.CAMBIAR else 10)
        out[G.pack(G.YO, rel, dst, G.AHORA, e, domain=G.DOMAIN_PHYSICAL,
                   generator=G.GENERATOR_GROUND).hex()] = (rel, dst, c)
    return out


CLOSED = closed_set()


def as_packet(p):
    try:
        b = bytes.fromhex(p)
    except (TypeError, ValueError):
        return None
    return b if len(b) == 16 else None


def cam_slots(packets):
    """Slots the Agent's own `_slot_for` gives each packet, on a fresh CAM."""
    agent = SimpleNamespace(cam=Cam(), metrics=SimpleNamespace(unknown=0))
    slots = [Agent._slot_for(agent, w, encode_event(w)[0], '', tuple(struct.unpack('<6b', w[4:10])),
                             source='ground1') for w in packets]
    return agent.cam, slots, agent.metrics.unknown


def vertex_distance(packets):
    """Minimum vertex Hamming distance between distinct packets; diagnostic only."""
    v = {w: encode_event(w)[0] for w in packets}
    pairs = [hamming16(v[a], v[b]) for a, b in itertools.combinations(sorted(v), 2)]
    return min(pairs) if pairs else None


def cam_group(packets):
    raw = [as_packet(p) for p in packets or []]
    if packets is None or None in raw:
        return [case('agent_slot_path', False, malformed=raw.count(None))]
    cam, slots, unknown = cam_slots(raw)
    first = {}
    for w, s in zip(raw, slots):
        first.setdefault(w, s)
    same = all(first[w] == s for w, s in zip(raw, slots))
    distinct = len(set(first.values())) == len(first)
    return [case('agent_slot_path', same and distinct and unknown == 0 and cam.destroyed == 0,
                 structural=True, percepts=len(first), slots=len(set(slots)), unknown=unknown,
                 destroyed=cam.destroyed, vertex_min_bits_emitted=vertex_distance(first),
                 vertex_min_bits_closed=vertex_distance([bytes.fromhex(k) for k in CLOSED]),
                 ham_limit=HAM_LIMIT)]


def rebuild(transcript, P):
    """What the consumer received, as Ground.record arguments, in order."""
    raw = {s: {e['stamp']: e for e in P['raw'][s].values()} for s in s1.SOURCES}
    out = []
    for t in transcript:
        try:
            h = json.loads(t['h'])
        except (ValueError, TypeError):
            continue
        if not isinstance(h, dict) or set(h) != G.KEYS or h.get('v') != 2 or h['source'] not in G.SOURCES:
            continue
        if not all(isinstance(h[k], int) and not isinstance(h[k], bool) and h[k] >= 0
                   for k in ('seq', 'capture_ns', 'delivered_ns', 'gap', 'payload_len')):
            continue
        if h['status'] not in ('ok', 'stale') or h['payload_len'] != t.get('len', h['payload_len']):
            continue
        s, valid = h['source'], t['wire'] == h['payload_sha256']
        e = raw[s].get(h['capture_ns'])
        values = ()
        if valid and e is not None:
            values = tuple(e['sample'][:6]) if s == 'imu' else (tuple(e['sample']['ranges']) if s == 'lidar' else ())
        out.append(dict(source=s, capture_ns=h['capture_ns'], status=h['status'], gap=h['gap'],
                        valid=valid, values=values, raw=e))
    return out


def feed(g, r):
    g.record(r['source'], r['capture_ns'], r['status'], r['gap'], r['valid'], r['values'])


def recompute(records):
    g = G.Ground('')
    for r in records:
        feed(g, r)
    g.close()
    return g.packets


def causal_prefix(records):
    """Fed one record at a time, the translation emits exactly one packet at
    each LiDAR record, none elsewhere, and never revises an earlier one."""
    g, seen, n = G.Ground(''), [], 0
    for r in records:
        feed(g, r)
        n += r['source'] == 'lidar'
        if len(g.packets) != n or g.packets[:len(seen)] != seen:
            return False
        seen = list(g.packets)
    g.close()
    return g.packets == seen


def true_front(entry, solids, dz=0.0):
    """Nearest surface within the front sector at the true sensor pose,
    optionally raised by dz metres."""
    body, s = entry['body'], entry['sample']
    R = sev.rotation(*body[4:7])
    m = sev.apply(R, tuple(BASE_LINK_IN_MODEL[k] + s1.MOUNT_M[k] for k in range(3)))
    o = (body[1]+m[0], body[2]+m[1], body[3]+m[2]+dz)
    best = math.inf
    for i in G.FRONT:
        a = s['angle_min'] + i*s['angle_step']
        d = sev.apply(R, (math.cos(a), math.sin(a), 0.0))
        for lo, hi in solids:
            h = sev.hit_box(o, d, lo, hi)
            if h and h[0] < best:
                best = h[0]
    return best


def truth_band(entry, solids, lim=GROUND_LIMITS):
    """True near, False far, None ambiguous: truth within ambiguous_m of the
    threshold, or a band that changes when the sensor moves vertical_m up or
    down (rays grazing a box top; amendment 3)."""
    t = true_front(entry, solids)
    if abs(t*1000 - G.NEAR_MM) < lim['ambiguous_m']*1000:
        return None
    near = t*1000 < G.NEAR_MM
    for dz in (-lim['vertical_m'], lim['vertical_m']):
        if (true_front(entry, solids, dz)*1000 < G.NEAR_MM) != near:
            return None
    return near


def touchdown(trace, lim=GROUND_LIMITS):
    """Truth: first body sample after recovery within touchdown_mm of the rest
    height (contract amendment 2). None if the body never comes down."""
    try:
        sm, cols = trace['stage_marks'], trace['sample_columns']
        it, iz = cols.index('sim_time_ns'), cols.index('z_um')
        return next((s[it] for s in trace['samples'] if s[it] > sm['recovered_ns']
                     and s[iz] - sm['rest_z_um'] < lim['touchdown_mm']*1000), None)
    except (KeyError, ValueError, TypeError, IndexError):
        return None


def canonical_sha256(transcript, packets):
    """The one stderr line an honest consumer writes: the report the evaluator
    predicts from the transcript and the recomputed packets, byte for byte, so
    no field's type or format can carry anything."""
    line = json.dumps(dict(sev.mirror_tally(transcript), wsp=packets), sort_keys=True) + '\n'
    return hashlib.sha256(line.encode()).hexdigest()


def case(name, ok, **info):
    return dict(name=name, ok=bool(ok), **info)


def grounding(trace, P, T, report, package, *, condition, cable=None, lim=GROUND_LIMITS):
    """GROUND-1's own groups for one episode. Never raises on odd input."""
    g = {}
    packets = report.get('wsp') if isinstance(report.get('wsp'), list) else None
    records = rebuild(T, P)
    lidar = [r for r in records if r['source'] == 'lidar']
    honest = recompute(records)
    g['sensors_only'] = [case('recomputed_from_raw_samples', packets == honest,
                              packets=len(packets or []), recomputed=len(honest),
                              first_difference=next((i for i, (a, b) in enumerate(zip(packets or [], honest))
                                                     if a != b), None)),
                         case('causal_prefix', causal_prefix(records))]
    extra = set(report) - set(sev.mirror_tally([])) - EXTRA_KEYS
    c = cable if isinstance(cable, dict) else {}
    canon = canonical_sha256(T, honest)
    g['single_cable'] = [case('report_keys', not extra and packets is not None, extra=sorted(extra)),
                         case('stream_bytes', c.get('stderr_lines') == 1 and c.get('back_bytes') == 0
                              and c.get('returncode') == 0 and c.get('stderr_sha256') == canon,
                              stderr_lines=c.get('stderr_lines'), back_bytes=c.get('back_bytes'),
                              returncode=c.get('returncode'),
                              canonical=c.get('stderr_sha256') == canon)]
    outside = [i for i, p in enumerate(packets or []) if not isinstance(p, str) or p not in CLOSED]
    g['pinned'] = [case('closed_packet_set', not outside and packets is not None,
                        outside=outside[:5], count=len(outside))]
    g['cam'] = cam_group(packets)
    if packets is None or len(packets) != len(lidar):
        for name in ('distance', 'push', 'certainty'):
            g[name] = [case('aligned_turns', False, packets=len(packets or []), turns=len(lidar))]
        return g
    percept = [CLOSED.get(p) if isinstance(p, str) else None for p in packets]
    # Distance: every usable scan must say the true band; an unusable one must
    # say DESCONOCIDO; undecodable packets are misses (amendment 3).
    solids = sev.boxes(package)
    hits = judged = ambiguous = unusable = untruthed = 0
    for r, pc in zip(lidar, percept):
        if not (r['valid'] and r['status'] == 'ok'):
            unusable += 1
            judged += 1
            hits += pc is not None and pc[0] == G.DESCONOCIDO
            continue
        if not r['raw'] or not r['raw'].get('body'):
            untruthed += 1
            continue
        band = truth_band(r['raw'], solids, lim)
        if band is None:
            ambiguous += 1
            continue
        judged += 1
        hits += pc is not None and pc[0] != G.DESCONOCIDO and (pc[1] == G.ALLI) == band
    acc = hits/judged if judged else None
    g['distance'] = [case('front_band', acc is not None and acc >= lim['accuracy_episode'],
                          accuracy=acc, hits=hits, judged=judged, ambiguous=ambiguous,
                          unusable=unusable, untruthed=untruthed, turns=len(lidar))]
    # Push: CAMBIAR soon after the wrench; elsewhere only around touchdown,
    # [touchdown - 100 ms, +2 s] (amendments 2 and 3: ground contact is a real
    # change; allowed, not required).
    wrench = [e['sim_time_ns'] for e in trace.get('events', []) if e.get('ev') == 'wrench_applied']
    changes = [r['capture_ns'] for r, pc in zip(lidar, percept) if pc and pc[0] == G.CAMBIAR]
    td = touchdown(trace, lim)
    allowed = [(td - lim['touchdown_before_ns'], td + lim['touchdown_last_ns'])] if td is not None else []
    at_touchdown = sum(1 for t in changes if allowed and allowed[0][0] <= t <= allowed[0][1])
    if condition == 'perturbed':
        if not wrench:
            g['push'] = [case('change_after_wrench', False, error='perturbed_without_wrench_event')]
        else:
            tw = wrench[0]
            allowed.append((tw, tw + lim['push_last_ns']))
            early = [t for t in changes if tw <= t <= tw + lim['push_first_ns']]
            stray = [t - tw for t in changes if not any(a <= t <= b for a, b in allowed)]
            g['push'] = [case('change_after_wrench', bool(early) and not stray,
                              first_ms=(early[0]-tw)/1e6 if early else None, stray_ms=[x/1e6 for x in stray[:5]],
                              touchdown_found=td is not None, at_touchdown=at_touchdown)]
    else:
        stray = [t for t in changes if not any(a <= t <= b for a, b in allowed)]
        g['push'] = [case('quiet_without_force', not stray and not wrench, changes=len(changes),
                          stray=len(stray), wrench_events=len(wrench), touchdown_found=td is not None,
                          at_touchdown=at_touchdown)]
    # Certainty: C is 40 exactly on windows that carried a validity marker.
    wrong, marked, i = [], False, 0
    for r in records:
        if r['status'] == 'stale' or r['gap'] > 0 or not r['valid']:
            marked = True
        if r['source'] == 'lidar':
            want = 40 if marked else 100
            if percept[i] is None or percept[i][2] != want:
                wrong.append(i)
            marked, i = False, i + 1
    g['certainty'] = [case('validity_windows', not wrong, wrong=wrong[:5], count=len(wrong))]
    return g


def episode(trace, P, T, report, forwarder, package, spec, *, condition, bounds, lim=None, cable=None,
            glim=None):
    """SENSOR-1S v3 groups on the sensor tally, then GROUND-1's groups."""
    tally = {k: v for k, v in report.items() if k not in EXTRA_KEYS | {'debug'}}
    try:
        groups = sev.episode(trace, P, T, tally, forwarder, package, spec, condition=condition,
                             bounds=bounds, lim=lim or sev.LIMITS)
    except Exception as exc:
        groups = {'execution': [case('sensor_evaluator', False, error=type(exc).__name__+': '+str(exc)[:200])]}
    try:
        groups.update(grounding(trace, P, T, report, package, condition=condition, cable=cable,
                                lim=glim or GROUND_LIMITS))
    except Exception as exc:
        groups['sensors_only'] = [case('grounding_evaluator', False, error=type(exc).__name__+': '+str(exc)[:200])]
    return groups


summarize = sev.summarize
