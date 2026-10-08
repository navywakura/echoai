"""Sensor adapter: SI geometry outside the integer decision step."""
import math
from statistics import median_low


def project(raw):
    if set(raw) != {'now_ns', 'estimate', 'lidar'}:
        raise ValueError('public observation schema')
    estimate, scan = raw['estimate'], raw['lidar']
    if set(estimate) != {'position_mm', 'yaw_mrad', 'received_ns', 'px4_boot_ms',
                         'tilt_mrad', 'speed_mm_s'}:
        raise ValueError('estimator schema')
    if set(scan) != {'capture_ns', 'delivered_ns', 'angles_mrad', 'ranges_mm'}:
        raise ValueError('LiDAR schema')
    if len(scan['angles_mrad']) != len(scan['ranges_mm']):
        raise ValueError('ray arrays')
    if (len(estimate['position_mm']) != 3 or
            any(type(v) is not int for v in estimate['position_mm']) or
            any(type(estimate[k]) is not int for k in estimate if k != 'position_mm')):
        raise ValueError('integer estimator')
    projected = []
    for angle, distance in zip(scan['angles_mrad'], scan['ranges_mm']):
        if type(angle) is not int or type(distance) is not int:
            raise ValueError('ray type')
        bearing = angle/1000+estimate['yaw_mrad']/1000
        offset = (bearing-math.pi/2+math.pi) % (2*math.pi)-math.pi
        if abs(offset) <= .10 and 300 <= distance <= 30000:
            projected.append(round(distance*math.cos(offset)))
    return dict(now_ns=raw['now_ns'], capture_ns=scan['capture_ns'],
                delivered_ns=scan['delivered_ns'], odometry_ns=estimate['received_ns'],
                north_mm=estimate['position_mm'][1], yaw_mrad=estimate['yaw_mrad'],
                distance_mm=median_low(projected) if projected else -1,
                rays=len(projected) if 0 <= estimate['tilt_mrad'] < 80 and 0 <= estimate['speed_mm_s'] < 100 else 0)
