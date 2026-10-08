"""Immutable acceptance and grouped contrast; floats are lab measurements only."""
import math
import statistics
from pathlib import Path

from echoai.nexus0.flight1s.v3 import campaign as c
from echoai.nexus0.flight1s.v2.bench import Bench


def protocol():
    return dict(version=4, configuration=c.configuration('noaid_7n'), workers=2,
                stages={'validation': dict(worlds=4, repeats=8, seed=20260921),
                        'bench': dict(worlds=12, repeats=2, seed=20260922)},
                separation=dict(world_margin_mm=50, median_effect_mm=100,
                                bank_min_positive_worlds=10, alpha=0.025),
                max_displacement_from_start_mm=1000,
                nominal_250mm='diagnostic_only', automatic_retries=0)


def validate(p):
    if p != protocol():
        raise ValueError('v4 protocol differs from preregistration')


def group(cases):
    return dict(status='pass' if cases and all(x['ok'] for x in cases) else 'fail',
                cases=cases)


def sign_tail(k, n, probability=0.5):
    return sum(math.comb(n, j)*probability**j*(1-probability)**(n-j)
               for j in range(k, n+1))


def lower_bound(k, n):
    """Exact one-sided 95% binomial lower bound, no scipy dependency."""
    if k == 0 or n == 0:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low+high)/2
        if sign_tail(k, n, mid) < 0.05:
            low = mid
        else:
            high = mid
    return (low+high)/2


def separation(rows, stage, p):
    spec = p['stages'][stage]
    pairs = {}
    for m in rows:
        key = (m['package_id'], m['repeat'])
        pair = pairs.setdefault(key, {})
        value = m.get('disturb_excursion_mm')
        if (m['condition'] in pair or not isinstance(value, (float, int))
                or not math.isfinite(value)):
            return group([dict(name='complete_finite_pairs', ok=False)])
        pair[m['condition']] = value
    if (len(pairs) != spec['worlds']*spec['repeats']
            or any(set(x) != {'nominal', 'perturbed'} for x in pairs.values())):
        return group([dict(name='complete_finite_pairs', ok=False)])
    worlds = {}
    differences = []
    for (pid, repeat), pair in sorted(pairs.items()):
        d = pair['perturbed']-pair['nominal']
        differences.append(dict(package_id=pid, repeat=repeat, difference_mm=d))
        worlds.setdefault(pid, []).append(d)
    if len(worlds) != spec['worlds'] or any(len(v) != spec['repeats'] for v in worlds.values()):
        return group([dict(name='complete_world_blocks', ok=False)])
    means = {pid: math.fsum(v)/len(v) for pid, v in sorted(worlds.items())}
    s = p['separation']
    positives = sum(x > s['world_margin_mm'] for x in means.values())
    needed = spec['worlds'] if stage == 'validation' else s['bank_min_positive_worlds']
    med = statistics.median(means.values())
    result = group([dict(name='world_signs', ok=positives >= needed,
                         observed=positives, required=needed),
                    dict(name='practical_effect', ok=med >= s['median_effect_mm'],
                         observed_mm=med, required_mm=s['median_effect_mm'])])
    nominal = [v['nominal'] for v in pairs.values()]
    perturbed = [v['perturbed'] for v in pairs.values()]
    result.update(pairs=differences, world_mean_differences_mm=means,
                  nominal_range_mm=[min(nominal), max(nominal)],
                  perturbed_range_mm=[min(perturbed), max(perturbed)],
                  nominal_above_250mm=sum(x > 250 for x in nominal),
                  observed_global_gap_mm=min(perturbed)-max(nominal),
                  positive_worlds=positives, world_count=len(worlds),
                  one_sided_sign_p=sign_tail(positives, len(worlds)),
                  positive_world_fraction_lower95=lower_bound(positives, len(worlds)),
                  inference='conditional_on_independent_world_blocks' if stage=='bench'
                            else 'engineering_gate_only')
    return result


def displacement(trace):
    samples = trace.get('samples', [])
    if not samples:
        return dict(ok=False, max_mm=None)
    x0, y0 = samples[0][1:3]
    distances = [math.hypot(s[1]-x0, s[2]-y0)/1000 for s in samples]
    maximum = max(distances)
    return dict(ok=all(math.isfinite(x) for x in distances) and maximum <= 1000,
                max_mm=maximum, reference='first_recorded_body_position',
                limit_mm=1000, samples=len(samples))


def verdict(rows, stage, p, packages):
    cfg = p['configuration']
    gs = c.groups(rows, cfg)
    # Preserve legacy challenge in each row; replace only the aggregate question.
    gs.pop('challenge')
    gs['challenge_perturbed'] = group([m['challenge'] for m in rows
                                        if m['condition']=='perturbed'])
    gs['physical_envelope'] = group([dict(label=m['label'], **m['v4_displacement'])
                                     for m in rows])
    gs['separation'] = separation(rows, stage, p)
    expected = p['stages'][stage]['worlds']*p['stages'][stage]['repeats']*2
    gs['denominator'] = group([dict(ok=len(rows)==expected, observed=len(rows), expected=expected)])
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    b._group_repetition({(m['package_id'], m['repeat'], m['condition']):m
                         for m in rows if m['repeat'] <= 2}, cfg)
    b._group_envelope(packages, cfg)
    gs.update(b.groups)
    return gs
