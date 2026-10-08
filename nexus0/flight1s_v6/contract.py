"""v4 acceptance, unchanged; a chain that no single row can stop.

The v5 chain flew all 64 A flights and then stopped: the inherited v2
repetition aggregator read hover_horiz_rms_mm from an episode that never
flew, raised KeyError, and neither the negatives nor report.json existed.
Here the same frozen pieces run one group at a time. When every flight is
measured the groups are identical to v4.verdict; a missing measurement is a
failed case; an unexpected error fails its group and the chain goes on.

The episode that never flew was PX4's MAVLink module going silent about 2 s
after boot (1 telemetry_status sample per instance instead of one per
second; 2 of 343 flights, v3 and v5). It happens before any parameter,
command, arming or force. v6 preregisters one relaunch for exactly that.
"""
import math
from pathlib import Path

from echoai.nexus0.flight1s_v4.contract import (
    group, sign_tail, lower_bound, separation, displacement,
)
from echoai.nexus0.flight1s_v5 import contract as v5
from echoai.nexus0.flight1s.v2.bench import Bench
from echoai.nexus0.flight1s.v3 import campaign as c

# Successful boots: container start to first heartbeat <= 21.2 s over 341
# flights (an upper bound, teardown included); the relaunch waits 30 s.
BOOT = dict(heartbeat_s=30, restarts=1)
STAGE_KEYS = {'climb': 'takeoff_hold_ms', 'stabilize': 'stabilize_ms',
              'hover': 'hover_ms', 'disturb': 'disturb_ms', 'recover': 'recover_ms'}


def protocol():
    p = v5.protocol()
    p.update(version=6, boot=dict(BOOT), aggregation='per_group_no_raise')
    p['stages']['validation']['seed'] = 20260925
    p['stages']['bench']['seed'] = 20260926
    return p


def validate(p):
    if p != protocol():
        raise ValueError('v6 protocol differs from preregistration')


def boot_hung(trace):
    """PX4 never answered: no parameter, command, arming, sample or force."""
    return ((trace.get('cause') or {}).get('code') == 'mavlink_no_heartbeat'
            and not trace.get('driver_events') and not trace.get('samples')
            and trace.get('wrench_published', 0) == 0)


def plan_ok(ep, cfg):
    """Stages run in order with their preregistered durations. A completed
    flight ran all five; one that never took off has none to check."""
    plan = ep.stage_marks.get('plan', [])
    names = [x[0] for x in plan]
    ok = (names == list(STAGE_KEYS)[:len(names)]
          and all(b-a == cfg['stages'][STAGE_KEYS[n]]*1_000_000 for n, a, b in plan))
    return ok and (len(plan) == len(STAGE_KEYS) or not ep.ok)


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def error_group(where, exc):
    return group([dict(ok=False, why='aggregator_error', where=where,
                       error=type(exc).__name__+': '+str(exc)[:300])])


def repetition(rows, cfg):
    """v2 paired repeats. Unmeasured rows are withheld from the frozen code
    and listed as failed cases, so it never reads a missing field."""
    measured = {(m['package_id'], m['repeat'], m['condition']): m for m in rows
                if m['repeat'] <= 2 and finite(m.get('hover_horiz_rms_mm'))}
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    b._group_repetition(measured, cfg)
    g = b.groups['repetition']
    missing = sorted(m['label'] for m in rows
                     if m['repeat'] <= 2 and not finite(m.get('hover_horiz_rms_mm')))
    if missing:
        g['cases'] += [dict(label=x, ok=False, why='missing measurement') for x in missing]
        g['status'] = 'fail'
    return g


def envelope(packages, cfg):
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    b._group_envelope(packages, cfg)
    return b.groups['envelope']


def verdict(rows, stage, p, packages):
    """Same groups, same order and same arithmetic as v4.verdict."""
    cfg = p['configuration']
    gs = {}
    try:
        legacy = c.groups(rows, cfg)
        legacy.pop('challenge')
        gs.update(legacy)
    except Exception as exc:
        gs['episodes'] = error_group('v2_groups', exc)
    expected = p['stages'][stage]['worlds']*p['stages'][stage]['repeats']*2
    steps = (
        ('challenge_perturbed', lambda: group([m['challenge'] for m in rows
                                               if m['condition'] == 'perturbed'])),
        ('physical_envelope', lambda: group([dict(label=m['label'], **m['v4_displacement'])
                                             for m in rows])),
        ('separation', lambda: separation(rows, stage, p)),
        ('denominator', lambda: group([dict(ok=len(rows) == expected, observed=len(rows),
                                            expected=expected)])),
        ('repetition', lambda: repetition(rows, cfg)),
        ('envelope', lambda: envelope(packages, cfg)),
    )
    for name, fn in steps:
        try:
            gs[name] = fn()
        except Exception as exc:
            gs[name] = error_group(name, exc)
    return gs


def failed_row(meta, exc):
    """A job whose flight raised before producing metrics. It carries the
    fields every group reads, all failing, so it is counted, not lost."""
    return dict(meta, ok=False, status='not_measured',
                cause=dict(code='coordinator_exception', detail=type(exc).__name__+': '+str(exc)[:300]),
                challenge=dict(label=meta['label'], condition=meta['condition'], ok=False),
                stimulus=dict(label=meta['label'], condition=meta['condition'], ok=False),
                recovery_verdict=dict(label=meta['label'], condition=meta['condition'], ok=False),
                parameters=dict(ok=False), v4_displacement=dict(ok=False, max_mm=None))
