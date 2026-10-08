"""Read-only ULog/sensor diagnostics, with an optional decoded camera artifact."""
import argparse
import json
from pathlib import Path
from pyulog import ULog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    log = next((args.root/'out/wd/log').rglob('*.ulg'))
    ulog = ULog(str(log))
    print('parameters', {k: v for k, v in ulog.initial_parameters.items()
                         if k in ('EKF2_MAG_TYPE', 'EKF2_MAG_CTRL', 'SYS_HAS_MAG', 'SENS_EN_MAGSIM',
                                  'EKF2_GPS_CTRL', 'MPC_YAW_MODE')})
    for name, keys in [('vehicle_local_position', ['heading_good_for_control', 'heading', 'xy_valid']),
                       ('position_setpoint_triplet', ['current.yaw']),
                       ('trajectory_setpoint', ['yaw']),
                       ('vehicle_attitude_setpoint', ['yaw_body'])]:
        datasets = [d for d in ulog.data_list if d.name == name]
        if not datasets:
            continue
        data = datasets[0].data
        for key in keys:
            if key in data:
                values = data[key][len(data[key])//4:]
                print(name, key, 'min/max', float(min(values)), float(max(values)))
    for line in (args.root/'journal.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['side'] == 'backend' and row['event'].get('kind') == 'observation':
            event = row['event']
            pixels = bytes.fromhex(event['raw']['rgb']['pixels_hex'])
            green = sum(g > 80 and g > r*2 and g > b*2
                        for r, g, b in zip(pixels[::3], pixels[1::3], pixels[2::3]))
            print('camera', event['epoch'], 'green', green, 'yaw', event['raw']['estimate']['yaw_mrad'])


if __name__ == '__main__':
    main()
