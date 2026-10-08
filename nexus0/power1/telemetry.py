"""External-unit adapter. Never invent current, capacity or measured joules."""
import math


def battery_sample(*, stamp_ns, remaining_fraction, capacity_mah, current_a, voltage_v):
    values = (remaining_fraction, capacity_mah, current_a, voltage_v)
    if (type(stamp_ns) is not int or stamp_ns < 0
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
            or not 0 <= remaining_fraction <= 1 or capacity_mah <= 0 or current_a < 0 or voltage_v <= 0):
        return dict(known=False, reason='unusable_battery_telemetry')
    # mAh * 3600 = mC. This is estimated charge, NOT measured mechanical energy.
    capacity = math.floor(capacity_mah*3600)
    if capacity <= 0:
        return dict(known=False, reason='unusable_battery_telemetry')
    return dict(known=True, battery=dict(capture_ns=stamp_ns, unit='mC', capacity=capacity,
                                       remaining=math.floor(capacity*remaining_fraction)))


def replay_px4():
    from pathlib import Path
    from pyulog import ULog
    from echoai.nexus0.px41.evaluate import digest
    root = Path(__file__).resolve().parents[2]/'lab/px41'
    rows = []
    for stage in ('development', 'validation', 'confirmation'):
        for folder in sorted((root/stage).iterdir()):
            path = next(folder.rglob('*.ulg'))
            data = ULog(str(path)).get_dataset('battery_status').data
            n, unknown = len(data['timestamp']), 0
            for i in range(n):
                value = battery_sample(stamp_ns=int(data['timestamp'][i])*1000,
                    remaining_fraction=float(data['remaining'][i]), capacity_mah=int(data['capacity'][i]),
                    current_a=float(data['current_a'][i]), voltage_v=float(data['voltage_v'][i]))
                unknown += not value['known']
            rows.append(dict(source=str(path.relative_to(root)), sha256=digest(path), samples=n, unknown=unknown))
    return dict(scope='read-only battery validity replay; not flight energy measurement',
                flights=len(rows), samples=sum(r['samples'] for r in rows),
                unknown=sum(r['unknown'] for r in rows), rows=rows)
