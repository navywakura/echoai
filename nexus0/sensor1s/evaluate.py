"""SENSOR-1S evaluator: private truth against what the consumer received.

Two independent sources judge everything. The tap's raw log holds every
message as Gazebo delivered it, written before the injector or the adapter
can touch it. The host transcript holds every header the consumer was
sent and the hash of the bytes that actually crossed. The adapter's own
send log is only compared with the transcript, never walked. The
consumer's tally is recomputed from the transcript and must match.

Every transcript record is matched to exactly one raw capture by (source,
capture time, payload hash); every raw capture the injector did not remove
must be delivered exactly once; every header field that is not a
measurement is pinned; every delivery time is bounded below by when the
tap received the message and when the injector released it. Floats are
lab measurements, never agent state.
"""
import hashlib
import json
import math
import statistics

from . import contract

HEADER_KEYS = {'v', 'source', 'seq', 'capture_ns', 'delivered_ns', 'gap', 'status',
               'noise_ref', 'shape', 'format', 'payload_len', 'payload_sha256'}
LIMITS = dict(
    # Adapter wait = delivered - max(tap arrival, injector release), per record.
    wait_p99_ns=2_000_000,            # p99 per source (development: 1 ms)
    wait_max_ns=30_000_000,           # any record (development host stalls: <= 23 ms)
    onset_window_ns=contract.ONSET_WINDOW_NS,
    onset_threshold=1.0,              # m/s^2 horizontal change; the 7 N pulse is 3.39
    noise_band=(0.8, 1.25), bias_max_m=0.010,
    n_min_episode=200, edge_margin_m=0.03, incidence_min=0.2, clearance_m=0.05,
    settle_m=0.001, settle_ns=500_000_000,
)
DEPTH = dict(width=160, height=120, hfov=1.2)


def case(name, ok, **info):
    return dict(name=name, ok=bool(ok), **info)


def load_private(path):
    raw = {s: {} for s in contract.SOURCES}
    injects = {s: {} for s in contract.SOURCES}
    sends, other = [], []
    with open(path) as fh:
        for line in fh:
            e = json.loads(line)
            if e['k'] == 'raw':
                raw[e['src']][e['n']] = e
            elif e['k'] == 'inject':
                injects[e['src']][e['n']] = e
            elif e['k'] == 'send':
                sends.append(e)
            else:
                other.append(e)
    return dict(raw=raw, injects=injects, sends=sends, other=other)


def load_transcript(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def planned(spec):
    out = {s: {} for s in contract.SOURCES}
    for source, items in spec['faults'].items():
        for f in items:
            for i in range(f['count']):
                out[source][f['start']+i] = f['kind']
    return out


# ---------------------------------------------------------------- consumer
def _pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs)-1, (len(xs)*q)//100)]


def mirror_tally(transcript):
    """What consumer.py must have reported, recomputed from the transcript."""
    per = {s: dict(n=0, seq_breaks=0, gap_sum=0, stale=0, invalid=0, non_monotonic=0,
                   lat=[], last_seq=None, last_capture=None) for s in contract.SOURCES}
    schema, unknown, digest = 0, 0, hashlib.sha256()
    for t in transcript:
        hb = t['h'].encode()
        digest.update(len(hb).to_bytes(4, 'big') + hb)
        try:
            h = json.loads(hb)
        except ValueError:
            schema += 1
            continue
        if not isinstance(h, dict) or set(h) != HEADER_KEYS or h.get('v') != 2:
            schema += 1
            continue
        if h['source'] not in per:
            unknown += 1
            continue
        p = per[h['source']]
        ints = all(isinstance(h[k], int) and not isinstance(h[k], bool) and h[k] >= 0
                   for k in ('seq', 'capture_ns', 'delivered_ns', 'gap', 'payload_len'))
        if not ints or h['status'] not in ('ok', 'stale') or h['payload_len'] != t.get('len', h['payload_len']):
            schema += 1
            continue
        p['n'] += 1
        if p['last_seq'] is not None and h['seq'] != p['last_seq'] + 1:
            p['seq_breaks'] += 1
        p['last_seq'] = h['seq']
        p['gap_sum'] += h['gap']
        p['stale'] += h['status'] == 'stale'
        p['invalid'] += t['wire'] != h['payload_sha256']
        if p['last_capture'] is not None and h['capture_ns'] < p['last_capture']:
            p['non_monotonic'] += 1
        p['last_capture'] = h['capture_ns']
        p['lat'].append(h['delivered_ns'] - h['capture_ns'])
    out = dict(frames=len(transcript), schema_errors=schema, unknown_source=unknown, truncated=False,
               header_digest=digest.hexdigest(), sources={})
    for s, p in per.items():
        lat = p.pop('lat')
        p.pop('last_seq'), p.pop('last_capture')
        p.update(negative_latency=sum(x < 0 for x in lat), latency_p50_ns=_pct(lat, 50),
                 latency_p99_ns=_pct(lat, 99), latency_max_ns=max(lat) if lat else None)
        out['sources'][s] = p
    return out


# ---------------------------------------------------------------- geometry
def boxes(package):
    return [(tuple(v/1000 for v in m.aabb.lo), tuple(v/1000 for v in m.aabb.hi))
            for m in package.sdf.models]


def rotation(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = (math.cos(roll), math.sin(roll), math.cos(pitch),
                              math.sin(pitch), math.cos(yaw), math.sin(yaw))
    return ((cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr),
            (sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr),
            (-sp, cp*sr, cp*cr))


def apply(R, v):
    return tuple(sum(R[i][j]*v[j] for j in range(3)) for i in range(3))


def hit_box(o, d, lo, hi):
    """Slab test: (t, axis) of the entry face, or None."""
    tmin, tmax, axis = -math.inf, math.inf, None
    for a in range(3):
        if abs(d[a]) < 1e-12:
            if o[a] < lo[a] or o[a] > hi[a]:
                return None
            continue
        t1, t2 = (lo[a]-o[a])/d[a], (hi[a]-o[a])/d[a]
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > tmin:
            tmin, axis = t1, a
        tmax = min(tmax, t2)
    if tmax < max(tmin, 0) or tmin <= 0 or axis is None:
        return None
    return tmin, axis


def cast(o, d, solids, lim=LIMITS):
    """Nearest surface, or None when the ray is ambiguous near an edge,
    grazes a face, or has a second surface within the clearance."""
    hits = sorted(h + (i,) for i, (lo, hi) in enumerate(solids) if (h := hit_box(o, d, lo, hi)))
    if not hits:
        return math.inf
    t, axis, i = hits[0]
    if len(hits) > 1 and hits[1][0] - t < lim['clearance_m']:
        return None
    if abs(d[axis]) < lim['incidence_min']:
        return None
    lo, hi = solids[i]
    p = [o[k] + t*d[k] for k in range(3)]
    for k in range(3):
        if k != axis and min(p[k]-lo[k], hi[k]-p[k]) < lim['edge_margin_m']:
            return None
    return t


def sensor_origin(body):
    R = rotation(*body[4:7])
    m = apply(R, contract.MOUNT_M)
    return R, (body[1]+m[0], body[2]+m[1], body[3]+m[2])


def lidar_beams(entry, solids):
    """[(beam, measured, true)] for rays with an unambiguous true surface."""
    s = entry['sample']
    R, o = sensor_origin(entry['body'])
    out = []
    for i, r in enumerate(s['ranges']):
        a = s['angle_min'] + i*s['angle_step']
        t = cast(o, apply(R, (math.cos(a), math.sin(a), 0.0)), solids)
        if t is not None and math.isfinite(t) and 0.3 < t < 29.0 and math.isfinite(r):
            out.append((i, r, t))
    return out


def depth_beams(entry, solids):
    s = entry['sample']
    R, o = sensor_origin(entry['body'])
    f = (DEPTH['width']/2) / math.tan(DEPTH['hfov']/2)
    v = s['row'] + 0.5 - DEPTH['height']/2
    out = []
    for u, val in enumerate(s['values']):
        cam = (1.0, -(u + 0.5 - DEPTH['width']/2)/f, -v/f)
        n = math.sqrt(sum(x*x for x in cam))
        t = cast(o, apply(R, tuple(x/n for x in cam)), solids)
        if t is not None and math.isfinite(t) and 0.2 < t < 19.0 and math.isfinite(val):
            out.append((u, val, t/n))
    return out


def lidar_residuals(entry, solids):
    return [r - t for _, r, t in lidar_beams(entry, solids)]


def depth_residuals(entry, solids):
    return [r - t for _, r, t in depth_beams(entry, solids)]


def settled(raw, start_ns, lim=LIMITS):
    """Start of the rest window after the body stopped falling, or None."""
    bodies = sorted((e for s in ('lidar', 'depth') for e in raw[s].values()
                     if e.get('body') and e['stamp'] < start_ns), key=lambda e: e['stamp'])
    if not bodies:
        return None
    rest_z = statistics.median(e['body'][3] for e in bodies[-10:])
    since = None
    for e in bodies:
        if abs(e['body'][3]-rest_z) > lim['settle_m']:
            since = None
        elif since is None:
            since = e['stamp']
    return since + lim['settle_ns'] if since is not None else None


def within_beam(samples):
    """Pool temporal scatter per beam (body at rest: the only change is noise)
    and the bias of beam means against the traced truth."""
    beams = {}
    for b, v, t in samples:
        beams.setdefault(b, []).append((v, t))
    ss = df = bias_sum = bias_n = sys_sq = nb = 0
    for vals in beams.values():
        if len(vals) < 2:
            continue
        mv = math.fsum(v for v, _ in vals)/len(vals)
        mt = math.fsum(t for _, t in vals)/len(vals)
        ss += math.fsum((v-mv)**2 for v, _ in vals)
        df += len(vals) - 1
        bias_sum += math.fsum(v-t for v, t in vals)
        bias_n += len(vals)
        sys_sq += (mv-mt)**2
        nb += 1
    return dict(ss=ss, df=df, bias_sum=bias_sum, bias_n=bias_n, beams=nb,
                systematic_rms_m=math.sqrt(sys_sq/nb) if nb else None)


def noise_verdict(acc, declared, lim, n_min):
    if not declared or acc['df'] < n_min or not acc['bias_n']:
        return None, dict(n=acc['df'])
    sd = math.sqrt(acc['ss']/acc['df'])
    bias = acc['bias_sum']/acc['bias_n']
    ok = abs(bias) <= lim['bias_max_m'] and lim['noise_band'][0] <= sd/declared <= lim['noise_band'][1]
    return ok, dict(n=acc['df'], sd_m=sd, ratio=sd/declared, bias_m=bias)


# ---------------------------------------------------------------- episode
def episode(trace, private, transcript, tally, forwarder, package, spec, *, condition,
            bounds, lim=LIMITS):
    """All per-episode cases, grouped."""
    P = private
    raw, inj, sends = P['raw'], P['injects'], P['sends']
    actual = {s: {n: e['kind'] for n, e in inj[s].items()} for s in contract.SOURCES}
    ends = [e for e in P['other'] if e['k'] == 'end']
    errors = [e for e in P['other'] if e['k'] == 'error']
    g = {}
    g['execution'] = [
        case('flight', trace.get('ok') is True, cause=trace.get('cause')),
        case('pipe', forwarder.get('error') is None and not tally.get('truncated')
             and tally.get('frames') == forwarder.get('frames') == len(transcript) == len(sends),
             frames=len(transcript)),
        case('tap', len(ends) == 1 and not ends[0]['sender_alive'] and not errors, errors=errors[:3]),
        case('faults_as_planned', actual == planned(spec)),
    ]
    parsed = []
    for t in transcript:
        try:
            parsed.append(json.loads(t['h']))
        except (ValueError, TypeError):
            parsed.append(None)
    # Pinned fields: nothing in a header may vary except measured values. A
    # header that is readable but breaks a pin is still matched to truth, so
    # a relabelled or mistimed record is judged for what it is.
    unusable, bad, seqs = set(), set(), {s: 0 for s in contract.SOURCES}
    for i, h in enumerate(parsed):
        usable = (isinstance(h, dict) and set(h) == HEADER_KEYS and h.get('v') == 2
                  and h.get('source') in contract.SOURCES and h.get('status') in ('ok', 'stale')
                  and isinstance(h.get('payload_sha256'), str)
                  and all(isinstance(h[k], int) and not isinstance(h[k], bool) and h[k] >= 0
                          for k in ('seq', 'capture_ns', 'delivered_ns', 'gap')))
        if not usable:
            unusable.add(i)
            bad.add(i)
            continue
        s = h['source']
        want = contract.EXPECTED[s]
        if not (h['noise_ref'] == contract.SOURCES[s]['noise_ref'] and h['shape'] == want['shape']
                and h['format'] == want['format'] and h['payload_len'] == want['payload_len']
                and h['seq'] == seqs[s]):
            bad.add(i)
        seqs[s] += 1
    g['schema'] = [case('pinned_fields', not bad, bad=sorted(bad)[:5], count=len(bad)),
                   case('host_saw_what_adapter_sent', parsed == [s['header'] for s in sends]),
                   case('consumer_tally_matches_transcript', tally == mirror_tally(transcript))]
    g['isolation'] = [case('canaries', forwarder.get('canary_hits') == [],
                           hits=forwarder.get('canary_hits'))]
    by_sha = {}
    for s in contract.SOURCES:
        for e in raw[s].values():
            by_sha.setdefault(e['sha'], []).append(e)
    per = {s: dict(mislabel=[], wrong_time=[], fabricated=[], status=[], wire=[], gap=[],
                   non_mono=0, delivered={}, repeats=[], waits=[], clean=[], early=[], over=[])
           for s in contract.SOURCES}
    stamp_ix = {s: {e['stamp']: n for n, e in raw[s].items()} for s in contract.SOURCES}
    unique = all(len(stamp_ix[s]) == len(raw[s]) for s in contract.SOURCES)
    last_cap = {s: None for s in contract.SOURCES}
    prev_ok = {s: None for s in contract.SOURCES}
    release, held, freezes = {}, {}, {}
    for s, spec_s in contract.SOURCES.items():
        rel, last, hs = {}, 0, set()
        for n in sorted(raw[s]):
            kind = actual[s].get(n)
            if kind in ('drop', 'freeze_skipped'):
                continue
            stamp = inj[s][n]['stamp'] if kind == 'freeze' else raw[s][n]['stamp']
            rel[n] = max(stamp + (inj[s][n].get('delay_ns', 0) if kind == 'delay' else 0), last)
            if rel[n] > stamp:
                hs.add(n)
            last = rel[n]
        release[s], held[s] = rel, hs
        freezes[s] = sorted(n for n, k in actual[s].items() if k == 'freeze')
    for i, h in enumerate(parsed):
        if i in unusable:
            continue
        s, c, sha = h['source'], h['capture_ns'], h['payload_sha256']
        q = per[s]
        n = stamp_ix[s].get(c)
        if n is None or raw[s][n]['sha'] != sha:
            others = by_sha.get(sha, [])
            if any(e['src'] != s for e in others):
                q['mislabel'].append(i)
            elif others:
                q['wrong_time'].append(i)
            else:
                q['fabricated'].append(i)
            continue
        repeat = n in q['delivered']
        if last_cap[s] is not None and (c < last_cap[s] or (not repeat and c == last_cap[s])):
            q['non_mono'] += 1
        last_cap[s] = c
        if (h['status'] == 'stale') != repeat:
            q['status'].append(i)
        corrupt = not repeat and actual[s].get(n) == 'corrupt'
        if (transcript[i]['wire'] != sha) != corrupt:
            q['wire'].append(i)
        if repeat:
            k = len(q['repeats'])
            q['repeats'].append(c)
            trigger = freezes[s][k] if k < len(freezes[s]) else None
        else:
            q['delivered'][n] = q['delivered'].get(n, 0) + 1
            want = 0 if prev_ok[s] is None else max(
                0, round((c - prev_ok[s])/contract.SOURCES[s]['period_ns']) - 1)
            if h['gap'] != want:
                q['gap'].append(i)
            prev_ok[s] = c
            trigger = n
        if trigger is None or trigger not in release[s]:
            q['status'].append(i)
            continue
        floor = max(raw[s][trigger].get('arrive', 0), release[s][trigger])
        wait = h['delivered_ns'] - floor
        q['waits'].append(wait)
        if wait < 0:
            q['early'].append(i)
        elif wait > lim['wait_max_ns']:
            q['over'].append(i)
        if not repeat and trigger not in held[s]:
            q['clean'].append(h['delivered_ns'] - c)
    src_cases, time_cases, valid_cases, loss_cases, lat_cases = [], [], [], [], []
    for s, spec_s in contract.SOURCES.items():
        q = per[s]
        removed = {n for n, k in actual[s].items() if k in ('drop', 'freeze', 'freeze_skipped')}
        expected = set(raw[s]) - removed
        missing = sorted(expected - set(q['delivered']))
        twice = sorted(n for n, k in q['delivered'].items() if k > 1)
        extra = sorted(set(q['delivered']) - expected)
        frozen_stamps = [inj[s][n]['stamp'] for n in freezes[s]]
        stamps = [raw[s][n]['stamp'] for n in sorted(expected) if n in q['delivered']]
        span = [raw[s][n]['stamp'] for n in sorted(raw[s])
                if stamps and stamps[0] <= raw[s][n]['stamp'] <= stamps[-1]]
        natural = sum(max(0, round((b-a)/spec_s['period_ns']) - 1) for a, b in zip(span, span[1:]))
        removed_in_span = sum(1 for n in removed if stamps and stamps[0] < raw[s][n]['stamp'] < stamps[-1])
        gap_total = sum(h['gap'] for i, h in enumerate(parsed) if i not in unusable
                        and h['source'] == s and h['status'] == 'ok')
        waits = sorted(q['waits'])
        clean = sorted(q['clean'])
        src_cases.append(case(s, not q['mislabel'] and not q['fabricated'] and unique,
                              mislabeled=q['mislabel'][:5], fabricated=q['fabricated'][:5]))
        time_cases.append(case(s, not q['wrong_time'] and q['non_mono'] == 0,
                               wrong=q['wrong_time'][:5], non_monotonic=q['non_mono']))
        valid_cases.append(case(s, not q['status'] and not q['wire'] and q['repeats'] == frozen_stamps
                                and not twice, status=q['status'][:5], wire=q['wire'][:5],
                                stale=len(q['repeats']), frozen=len(frozen_stamps), twice=twice[:5]))
        loss_cases.append(case(s, not q['gap'] and not missing and not extra
                               and gap_total == natural + removed_in_span,
                               reported=gap_total, injected=removed_in_span, natural=natural,
                               missing=len(missing), extra=len(extra), mismatched=q['gap'][:5]))
        p99 = _pct(clean, 99)
        wp99 = _pct(waits, 99)
        lat_cases.append(case(s, not q['early'] and not q['over'] and wp99 is not None
                              and wp99 <= lim['wait_p99_ns'] and p99 is not None and p99 <= bounds[s],
                              clean_p99_ns=p99, bound_ns=bounds[s], wait_p99_ns=wp99,
                              wait_max_ns=waits[-1] if waits else None, held=len(held[s]),
                              before_arrival_or_release=q['early'][:5], over_max=q['over'][:5]))
    g['source'], g['time'], g['validity'], g['loss'], g['latency'] = (
        src_cases, time_cases, valid_cases, loss_cases, lat_cases)
    g['time'].append(causal(trace, P, condition, lim))
    g['noise'] = noise(trace, P, parsed, unusable, package, lim)
    return g


def causal(trace, P, condition, lim):
    imu = sorted(P['raw']['imu'].values(), key=lambda e: e['stamp'])
    wrench = [e for e in trace.get('events', []) if e.get('ev') == 'wrench_applied']
    plan = dict((x[0], x[1]) for x in trace.get('stage_marks', {}).get('plan', []))
    ref = wrench[0]['sim_time_ns'] if wrench else plan.get('disturb')
    if ref is None:
        return case('causal_onset', False, why='no reference time')
    base = [e['sample'][:2] for e in imu if ref-200_000_000 <= e['stamp'] < ref-20_000_000]
    if not base:
        return case('causal_onset', False, why='no imu baseline')
    bx, by = statistics.median(b[0] for b in base), statistics.median(b[1] for b in base)
    onset = None
    for e in imu:
        if e['stamp'] >= ref-100_000_000 and math.hypot(e['sample'][0]-bx, e['sample'][1]-by) > lim['onset_threshold']:
            onset = e['stamp'] - ref
            break
    if condition == 'perturbed':
        return case('causal_onset', onset is not None and 0 <= onset <= lim['onset_window_ns'],
                    onset_ns=onset)
    return case('causal_quiet_without_force', onset is None or onset > 700_000_000, onset_ns=onset)


def noise(trace, P, parsed, bad, package, lim):
    start = trace.get('stage_marks', {}).get('start_ns')
    if start is None:
        return [case('rest_window', False, why='no start mark')]
    since = settled(P['raw'], start, lim)
    if since is None:
        return [case('rest_window', False, why='body never settled')]
    refs = {s: set() for s in contract.SOURCES}
    for i, h in enumerate(parsed):
        if isinstance(h, dict) and h.get('source') in refs:
            refs[h['source']].add(h.get('noise_ref'))
    declared = {s: contract.NOISE.get(next(iter(v))) if len(v) == 1 else None for s, v in refs.items()}
    out = []
    imu = sorted((e for e in P['raw']['imu'].values() if since <= e['stamp'] < start),
                 key=lambda e: e['stamp'])
    ref = declared['imu']
    for k, name in enumerate(('ax', 'ay', 'az', 'gx', 'gy', 'gz')):
        v = [e['sample'][k] for e in imu]
        dv = [b-a for a, b in zip(v, v[1:])]
        sd = statistics.pstdev(dv)/math.sqrt(2) if len(dv) > 1 else None
        want = (ref or {}).get('accel_sd' if k < 3 else 'gyro_sd')
        ratio = sd/want if sd is not None and want else None
        out.append(case('imu_'+name, ratio is not None and lim['noise_band'][0] <= ratio <= lim['noise_band'][1],
                        n=len(v), sd=sd, declared=want, ratio=ratio))
    out.append(case('rgb_declared', len(refs['rgb']) == 1 and declared['rgb'] is None
                    and refs['rgb'] == {contract.SOURCES['rgb']['noise_ref']}, refs=sorted(refs['rgb'], key=str)))
    solids = boxes(package)
    for source, fn in (('lidar', lidar_beams), ('depth', depth_beams)):
        entries = [e for e in P['raw'][source].values() if since <= e['stamp'] < start and e.get('body')]
        acc = within_beam([x for e in entries for x in fn(e, solids)])
        want = (declared[source] or {}).get('sd_m')
        ok, st = noise_verdict(acc, want, lim, lim['n_min_episode'])
        out.append(case(source, want is not None and ok is not False, scans=len(entries),
                        declared=want, judged=ok is not None, **st, **acc))
    return out


def summarize(groups):
    return {name: dict(status='pass' if cases and all(c['ok'] for c in cases) else 'fail', cases=cases)
            for name, cases in groups.items()}
