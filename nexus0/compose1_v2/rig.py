"""Four depth views of one camera family; stock flight body is unchanged."""
from echoai.nexus0.sensor1s.model import build


def models():
    assets = build()
    key = 'x500_sensor1s_base/model.sdf'
    base = assets[key]
    # Front depth camera gets a documented 1.6 rad FOV; RGB stays stock.
    start = base.index('<sensor name="sensor1s_depth"')
    end = base.index('</sensor>', start)+len('</sensor>')
    front = base[start:end].replace('<horizontal_fov>1.2</horizontal_fov>',
                                   '<horizontal_fov>1.6</horizontal_fov>')
    extra = []
    for i, yaw in enumerate(('1.5707963267948966', '3.141592653589793', '-1.5707963267948966'), 1):
        extra.append(front.replace('sensor1s_depth', f'compose_depth_{i}')
                     .replace('sensor1s/depth', f'compose/depth_{i}')
                     .replace('0.12 0.03 0.242 0 0 0', f'0.12 0.03 0.242 0 0 {yaw}'))
    assets[key] = base[:start]+front+'\n'.join(extra)+base[end:]
    return assets
