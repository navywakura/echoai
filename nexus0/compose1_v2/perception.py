"""Sensor boundary: floating-point projection -> bounded integer WSP.

Only public range images and PX4's estimated pose. No world/generator import.
Full-height extruded obstacles and level flight are declared domain limits.
"""
import hashlib
import json
import math

from echoai.nexus0.fusion1.core import packet

CELL_MM = 3000
CLEARANCE_MM = 900  # body 400 + estimator/attitude/ray margin 500
DEPTH_FOV = 1.6
CAMERA_YAWS = (0, math.pi/2, math.pi, -math.pi/2)


def wrap(a):
    return (a+math.pi) % (2*math.pi)-math.pi


def grid(p):
    return (round(p[0]/CELL_MM), round(p[1]/CELL_MM), 0)


def source_hash(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def classify(target, position, yaw, source):
    """Finite measured rays must cover the target disc; no-return is unknown."""
    dx, dy = target[0]-position[0], target[1]-position[1]
    d = math.hypot(dx, dy)
    if d < CLEARANCE_MM:
        return -1
    bearing = wrap(math.atan2(dy, dx)-yaw)
    half = math.asin(min(1, CLEARANCE_MM/d))
    angles, ranges = source['angles_mrad'], source['ranges_mm']
    covered = [(a/1000, r) for a, r in zip(angles, ranges)
               if abs(wrap(a/1000-bearing)) <= half]
    if not covered:
        return -1
    centre = min(zip(angles, ranges), key=lambda ar: abs(wrap(ar[0]/1000-bearing)))
    centre_angle, centre_range = centre[0]/1000, centre[1]
    if centre_range > 0 and abs(wrap(centre_angle-bearing)) < 0.03:
        # Test the protected disc, not rounding an entire 3 m cell occupied.
        # Estimator error near a cell boundary otherwise moves the wall into
        # an empty target cell despite adequate measured clearance.
        hit = (position[0]+centre_range*math.cos(centre_angle+yaw),
               position[1]+centre_range*math.sin(centre_angle+yaw))
        if math.hypot(hit[0]-target[0], hit[1]-target[1]) < CLEARANCE_MM:
            return 1
    errors = [wrap(a-bearing) for a, _ in covered]
    if min(errors) > -half+0.04 or max(errors) < half-0.04:
        return -1
    return 0 if all(r > d+CLEARANCE_MM for _, r in covered) else -1


def project(raw, energy):
    if set(raw) != {'now_ns', 'estimate', 'lidar', 'depth', 'rgb'}:
        raise ValueError('private or missing raw field')
    estimate = raw['estimate']
    if set(estimate) != {'position_mm', 'yaw_mrad', 'received_ns', 'px4_boot_ms', 'tilt_mrad', 'speed_mm_s'}:
        raise ValueError('estimate schema')
    if not 0 <= raw['now_ns']-estimate['received_ns'] <= 250_000_000:
        raise ValueError('stale odometry')
    if estimate['tilt_mrad'] > 100 or estimate['speed_mm_s'] > 250:
        raise ValueError('projection requires settled level observation')
    position = estimate['position_mm']
    yaw = estimate['yaw_mrad']/1000
    pos = grid(position)
    lidar = raw['lidar']
    depths = raw['depth']
    if len(depths) != 4:
        raise ValueError('camera count')
    cells = []
    for x in range(pos[0]-6, pos[0]+7):
        for y in range(pos[1]-6, pos[1]+7):
            p = (x, y, 0)
            if p == pos:
                continue
            target = (x*CELL_MM, y*CELL_MM)
            # Sensor mount translation, rotated with PX4's attitude estimate.
            sensor_pos = (position[0]+120*math.cos(yaw)-30*math.sin(yaw),
                          position[1]+120*math.sin(yaw)+30*math.cos(yaw))
            lv = classify(target, sensor_pos, yaw, lidar)
            bearing = wrap(math.atan2(target[1]-sensor_pos[1], target[0]-sensor_pos[0])-yaw)
            index = min(range(4), key=lambda i: abs(wrap(bearing-CAMERA_YAWS[i])))
            depth = depths[index]
            dv = classify(target, sensor_pos, yaw, depth)
            if lv == dv == -1:
                continue
            records = []
            for source, value, record in [('lidar', lv, lidar), ('depth', dv, depth)]:
                records.append(dict(source=source, wsp=packet(value, 40 if value != -1 else 0).hex(),
                                    capture_ns=record['capture_ns'], delivered_ns=record['delivered_ns'],
                                    raw_sha256=source_hash(record)))
            cells.append(dict(position=list(p), sources=records))
    rgb = raw['rgb']
    pixels = bytes.fromhex(rgb['pixels_hex'])
    green = sum(g > 80 and g > r*2 and g > b*2
                for r, g, b in zip(pixels[::3], pixels[1::3], pixels[2::3]))
    visible = (0 <= raw['now_ns']-rgb['capture_ns'] <= 250_000_000
               and green >= 30)
    return dict(physical=True, now_ns=raw['now_ns'], odometry=list(pos),
                energy=energy, station_observed=visible, cells=cells)
