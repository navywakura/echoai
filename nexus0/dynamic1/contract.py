"""DYNAMIC-1: what moves, and where it will be in half a second.

The body hovers. The harness walks one wall of the world along a straight
line; the other wall and the station stay put and are the control inside the
same flight. Everything here is fixed before flying.
"""
import copy

from echoai.nexus0.sensor1s import contract as s1
from echoai.nexus0.pattern1r import contract as p1r

FAMILY, FAMILY_PATH = p1r.FAMILY, p1r.FAMILY_PATH
WORLD_SPLIT, WORLD_INDEX, WORLD_SEEDS = p1r.WORLD_SPLIT, p1r.WORLD_INDEX, p1r.WORLD_SEEDS

# Across its own face, not along it: a wall sliding lengthwise barely changes
# its silhouette, and there would be nothing to see (measured: 14 % detected).
MOVER = dict(model='m2', velocity_mm_s=[500, 0], duration_ms=12000, step_ms=100)
PREDICT_MS = 500
MUTANTS = ('no_motion', 'always_motion', 'copy_current', 'replay', 'frozen_world', 'extra_channel')


def configuration(moving=True):
    cfg = copy.deepcopy(s1.configuration())
    cfg['profile'] = 'dynamic1-x500-v1'
    cfg['timeouts'] = dict(cfg['timeouts'], episode_s=600)
    if moving:
        cfg['mover'] = copy.deepcopy(MOVER)
    return cfg


def spec(faults, mutant=None):
    if mutant is not None and mutant not in MUTANTS:
        raise ValueError('unknown mutant ' + mutant)
    return dict(s1.spec(faults), dynamic_mutant=mutant)


__all__ = ['configuration', 'spec', 'MOVER', 'PREDICT_MS', 'MUTANTS',
           'FAMILY', 'FAMILY_PATH', 'WORLD_SPLIT', 'WORLD_INDEX', 'WORLD_SEEDS']
