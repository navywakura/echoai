"""PATTERN-1R: the survey script and what is fixed before flying.

The viewpoints run along the free perimeter of the room: the walls of this
world family are staggered around the middle, so the body never has to cross
one. School and exam viewpoints are fixed here, not chosen after looking.
"""
import copy

from echoai.nexus0.sensor1s import contract as s1

FAMILY = 'pattern1r-v1'
FAMILY_PATH = 'docs/examples/sim3-families/pattern1r-v1.json'
WORLD_SPLIT = 'B'                  # staggered walls: two objects, never twins
WORLD_INDEX = tuple(range(100, 112))
WORLD_SEEDS = tuple(900 + k for k in range(12))

# Amendment 1: a continuous arc, not fixed viewpoints. A silhouette seen from
# one bearing does not carry identity (measured: the two objects of a world
# land in one family in 10-12 of 12 worlds). Seen along an arc, the width
# accumulated while the object is tracked recovers its true length.
# Amendment 2: the arc must be flown, not hopped. At 15 deg between stops the
# bearing of an object moves further than continuity can follow without
# knowing one's own motion, and a track jumps from one wall to the other
# carrying its size. 48 poses, no dwell, and a wide arrival band keep the
# body moving so that bearings drift by under a degree per scan.
ARC = dict(poses=48, radius_mm=5000, altitude_mm=1500, dwell_ms=0,
           tolerance_mm=500, leg_timeout_ms=12000, school_fraction=[0, 32], exam_fraction=[32, 48])
SCHOOL_POSES = tuple(range(*ARC['school_fraction']))
EXAM_POSES = tuple(range(*ARC['exam_fraction']))


def arc_viewpoints(package):
    """The arc around the objects of one world, in world millimetres. Truth,
    and harness-side: it decides where to fly, never what the consumer sees."""
    import math
    from echoai.nexus0.sensor1s_v3 import evaluate as sev
    boxes = [b for i, b in enumerate(sev.boxes(package))
             if package.roles[sorted(package.roles)[i]] == 'barrier']
    cx = sum((lo[0]+hi[0])/2 for lo, hi in boxes)/len(boxes)
    cy = sum((lo[1]+hi[1])/2 for lo, hi in boxes)/len(boxes)
    out = []
    for k in range(ARC['poses']):
        a = 2*math.pi*k/ARC['poses']
        out.append([int(round((cx + ARC['radius_mm']/1000.0*math.cos(a))*1000)),
                    int(round((cy + ARC['radius_mm']/1000.0*math.sin(a))*1000))])
    # Start where the body already is: the first leg then never crosses a wall.
    sx, sy = package.spawn_mm[0], package.spawn_mm[1]
    start = min(range(len(out)), key=lambda k: (out[k][0]-sx)**2 + (out[k][1]-sy)**2)
    return out[start:] + out[:start]


def survey(package):
    return dict(viewpoints_mm=arc_viewpoints(package), altitudes_mm=[ARC['altitude_mm']],
                dwell_ms=ARC['dwell_ms'], tolerance_mm=ARC['tolerance_mm'],
                leg_timeout_ms=ARC['leg_timeout_ms'])


MUTANTS = ('constant_family', 'range_leak', 'beam_index', 'replay', 'frozen_write', 'extra_channel')
CAGE_MUTANTS = ('constant_family', 'range_leak', 'beam_index', 'replay', 'extra_channel')


def configuration():
    cfg = copy.deepcopy(s1.configuration())
    cfg['profile'] = 'pattern1r-x500-v1'
    # 18 legs fit in the episode: the inherited 420 s is the hover profile's.
    cfg['timeouts'] = dict(cfg['timeouts'], episode_s=900)
    return cfg


def spec(faults, mutant=None):
    if mutant is not None and mutant not in MUTANTS:
        raise ValueError('unknown mutant ' + mutant)
    return dict(s1.spec(faults), pattern_mutant=mutant)


__all__ = ['configuration', 'spec', 'survey', 'arc_viewpoints', 'ARC', 'SCHOOL_POSES', 'EXAM_POSES',
           'MUTANTS', 'CAGE_MUTANTS', 'FAMILY', 'FAMILY_PATH', 'WORLD_SPLIT', 'WORLD_INDEX', 'WORLD_SEEDS']
