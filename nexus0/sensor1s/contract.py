"""SENSOR-1S contract pieces: configuration, sources, declared noise, faults.

The flight is FLIGHT-1S v6 unchanged except for the body's name, which
the disturbance link has to follow. Floats here are lab measurements and
simulator parameters, never agent state.
"""
import copy
import random

from echoai.nexus0.flight1s_v6 import contract as v6
from echoai.nexus0.flight1s_v4.contract import group

MODEL = 'x500_sensor1s'
SOURCES = {
    'imu':   dict(topic='/world/{world}/model/{instance}/link/base_link/sensor/imu_sensor/imu',
                  period_ns=4_000_000, noise_ref='imu:px4-x500-base'),
    'rgb':   dict(topic='/sensor1s/rgb', period_ns=66_666_667, noise_ref='rgb:none'),
    'depth': dict(topic='/sensor1s/depth', period_ns=66_666_667, noise_ref='depth:gauss-10mm'),
    'lidar': dict(topic='/sensor1s/lidar', period_ns=100_000_000, noise_ref='lidar:gauss-10mm'),
}
# Every header field that is not a measurement is pinned per source, so no
# value can carry anything the evaluator has not predicted.
EXPECTED = {
    'imu':   dict(shape=[6], format='f64', payload_len=48),
    'rgb':   dict(shape=[240, 320, 3], format='rgb8', payload_len=230400),
    'depth': dict(shape=[120, 160], format='f32', payload_len=76800),
    'lidar': dict(shape=[360], format='f32', payload_len=1440),
}
# What each noise_ref promises. The IMU numbers are PX4's own SDF.
NOISE = {
    'imu:px4-x500-base': dict(accel_sd=0.00186, gyro_sd=0.00018665),
    'rgb:none': None,
    'depth:gauss-10mm': dict(sd_m=0.010),
    'lidar:gauss-10mm': dict(sd_m=0.010),
    'depth:gauss-5mm': dict(sd_m=0.005),
    'lidar:gauss-5mm': dict(sd_m=0.005),
}
MOUNT_M = (0.12, 0.03, 0.242)
FAULTS = dict(drop=dict(count=3), freeze=dict(count=2), delay=dict(count=5, delay_ns=50_000_000),
              corrupt=dict(count=1))
FAULT_TIMES_S = (8.0, 16.0, 24.0, 32.0)
MUTANTS = ('hide_loss', 'delivery_stamp', 'wall_clock', 'source_swap', 'leak_pose',
           'fresh_stale', 'noise_lie')
# Pre-lock amendment approved by Roger (2026-09-11): the approved contract said
# one IMU period (4 ms). Eight development pulses began 1-5 ms after the wrench
# (Gazebo applies it 1-5 ms after the message, then the 4 ms IMU grid). Three
# IMU periods. Exact capture stamps are checked separately.
ONSET_WINDOW_NS = 12_000_000
# Clean capture-to-delivery P99, proposed from development in A (devA2-devA4:
# 1 / 14-20 / 19-30 / 63-67 ms). Fixed in the lock, never after validation.
LATENCY_P99_BOUND_NS = dict(imu=10_000_000, rgb=50_000_000, depth=60_000_000,
                            lidar=150_000_000)


def configuration():
    cfg = copy.deepcopy(v6.protocol()['configuration'])
    cfg['body']['model'] = MODEL
    cfg['disturbance']['link'] = MODEL+'_0::base_link'
    cfg['profile'] = 'sensor1s-x500-v1'
    return cfg


def schedule(seed, faulted):
    """Fault calendar by raw index per source; the consumer never sees it."""
    if not faulted:
        return {s: [] for s in SOURCES}
    rng = random.Random(seed)
    out = {}
    for k, (source, spec) in enumerate(sorted(SOURCES.items())):
        kinds = sorted(FAULTS)
        rng.shuffle(kinds)
        items = []
        for t, kind in zip(FAULT_TIMES_S, kinds):
            start = int((t + 0.5*k) * 1e9) // spec['period_ns']
            items.append(dict(kind=kind, start=start, **FAULTS[kind]))
        out[source] = items
    return out


def spec(faults, mutant=None):
    if mutant is not None and mutant not in MUTANTS:
        raise ValueError('unknown mutant '+mutant)
    return dict(sources=copy.deepcopy(SOURCES), faults=faults, mutant=mutant,
                fifo='/out/sensors.fifo', private_log='/out/private.jsonl')


__all__ = ['group', 'configuration', 'schedule', 'spec', 'SOURCES', 'NOISE', 'MODEL',
           'MOUNT_M', 'FAULTS', 'MUTANTS']
