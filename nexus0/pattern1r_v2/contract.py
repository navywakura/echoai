"""A physically admissible, harness-only survey; no route reaches the learner."""
import math

from echoai.nexus0.pattern1r import contract as old
from echoai.nexus0.sensor1s_v3 import evaluate as sev

FAMILY, FAMILY_PATH = old.FAMILY, old.FAMILY_PATH
WORLD_SPLIT, WORLD_INDEX, WORLD_SEEDS = old.WORLD_SPLIT, old.WORLD_INDEX, old.WORLD_SEEDS
MUTANTS, CAGE_MUTANTS = old.MUTANTS, old.CAGE_MUTANTS
spec = old.spec
BODY_RADIUS_MM = 400
ARC = dict(kind='rectangular_perimeter', poses=48, clearance_mm=1200,
           altitude_mm=1500, dwell_ms=0, tolerance_mm=500,
           leg_timeout_ms=12000, school_fraction=[0, 32], exam_fraction=[32, 48])
SCHOOL_POSES, EXAM_POSES = tuple(range(32)), tuple(range(32, 48))


def barriers(package):
    return [tuple(tuple(v*1000 for v in q) for q in box)
            for name, box in zip(sorted(package.roles), sev.boxes(package))
            if package.roles[name] == 'barrier']


def point_box_distance(p, box):
    lo, hi = box
    return math.sqrt(sum(max(lo[k]-p[k], 0, p[k]-hi[k])**2 for k in range(len(p))))


def segment_box_distance(a, b, box):
    """Exact horizontal distance, including the interior of a flight leg."""
    lo, hi = box
    enter, leave = 0.0, 1.0
    for k in range(2):
        d = b[k]-a[k]
        if d == 0:
            if not lo[k] <= a[k] <= hi[k]:
                enter, leave = 1.0, 0.0
                break
        else:
            t0, t1 = sorted(((lo[k]-a[k])/d, (hi[k]-a[k])/d))
            enter, leave = max(enter, t0), min(leave, t1)
    if enter <= leave:
        return 0.0
    best = min(point_box_distance(a, box), point_box_distance(b, box))
    length2 = sum((b[k]-a[k])**2 for k in range(2))
    for x in (lo[0], hi[0]):
        for y in (lo[1], hi[1]):
            q = (x, y)
            t = max(0.0, min(1.0, sum((q[k]-a[k])*(b[k]-a[k]) for k in range(2))/length2)) if length2 else 0
            best = min(best, math.hypot(*(q[k]-a[k]-t*(b[k]-a[k]) for k in range(2))))
    return best


def arc_viewpoints(package):
    boxes = barriers(package)
    if not boxes:
        raise ValueError('survey requires barriers')
    pad = ARC['clearance_mm']
    x0, x1 = min(b[0][0] for b in boxes)-pad, max(b[1][0] for b in boxes)+pad
    y0, y1 = min(b[0][1] for b in boxes)-pad, max(b[1][1] for b in boxes)+pad
    corners = [(x0, y1), (x0, y0), (x1, y0), (x1, y1)]
    out = []
    for a, b in zip(corners, corners[1:]+corners[:1]):
        for j in range(12):
            out.append([round(a[k]+(b[k]-a[k])*j/12) for k in range(2)])
    sx, sy = package.spawn_mm[:2]
    start = min(range(len(out)), key=lambda k: (out[k][0]-sx)**2+(out[k][1]-sy)**2)
    return out[start:]+out[:start]


def route_check(package, points=None):
    points = arc_viewpoints(package) if points is None else points
    boxes = barriers(package)
    route = [list(package.spawn_mm[:2])] + list(points)
    minimum = min(segment_box_distance(a, b, box) for a, b in zip(route, route[1:]) for box in boxes)
    floor = next(box for name, box in zip(sorted(package.roles), sev.boxes(package))
                 if package.roles[name] == 'floor')
    floor_mm = tuple(tuple(v*1000 for v in q) for q in floor)
    floor_ok = all(all(floor_mm[0][k]+BODY_RADIUS_MM <= p[k] <= floor_mm[1][k]-BODY_RADIUS_MM
                           for k in range(2)) for p in route)
    return dict(ok=minimum >= BODY_RADIUS_MM and floor_ok, min_clearance_mm=round(minimum, 3),
                body_radius_mm=BODY_RADIUS_MM, floor_covers=floor_ok)


def survey(package):
    points = arc_viewpoints(package)
    if not route_check(package, points)['ok']:
        raise ValueError('survey violates body envelope or floor bounds')
    return dict(viewpoints_mm=points, altitudes_mm=[ARC['altitude_mm']],
                dwell_ms=ARC['dwell_ms'], tolerance_mm=ARC['tolerance_mm'],
                leg_timeout_ms=ARC['leg_timeout_ms'])


def configuration():
    cfg = old.configuration()
    cfg.update(profile='pattern1r-x500-v2', candidate='pattern1r-baro-height', survey=True)
    cfg['px4_parameters'] = dict(cfg['px4_parameters'], EKF2_HGT_REF=0)
    return cfg
