"""Development flights (partition A). Pilots are kept and never counted."""
import argparse
import json
from pathlib import Path

from .calibration import provenance
from .protocol import CONDITIONS, FAULTS, FAULT_AFTER_MOVES, handover
from .session import run

ECHOAI = Path(__file__).resolve().parents[2]
LAB = ECHOAI/'lab/drone3'
SCHOOL = ECHOAI/'lab/compose1-v4/physical-school.json'
BATTERY = dict(drain_s=500.0, min_pct=5.0, usable_floor=0.2)
PROVISIONAL_POWER = {'unit': 'sim_u', 'costs': {
    '0': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    '1': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    'land': {'n': 8, 'nominal': 24, 'maximum': 27, 'upper': 34}}}


def compose_model():
    return json.loads(SCHOOL.read_text())['model']


def main():
    p = argparse.ArgumentParser()
    p.add_argument('label')
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--condition', default='access', choices=('access', 'low_reserve', 'contradiction', 'fault'))
    p.add_argument('--fault', default=None, choices=(None, 'agent_hang', 'lidar_stale'))
    p.add_argument('--handover', type=int, default=None)
    p.add_argument('--power', default=None, help='power model JSON path; provisional if absent')
    p.add_argument('--folder', default='pilot')
    args = p.parse_args()
    power = json.loads(Path(args.power).read_text())['model'] if args.power else PROVISIONAL_POWER
    fault = args.fault or (FAULTS[0] if args.condition == 'fault' else None)
    handover_remaining = args.handover
    if args.condition == 'low_reserve' and handover_remaining is None:
        handover_remaining = handover(args.seed, power)
    spec = dict(seed=args.seed, condition=args.condition,
                physics_seed=args.seed*10+CONDITIONS.index(args.condition),
                battery=BATTERY, power_model=power, offset=provenance()['offset'],
                handover_remaining=handover_remaining if args.condition == 'low_reserve' else None,
                fault=dict(kind=fault, after_moves=FAULT_AFTER_MOVES) if args.condition == 'fault' else None)
    run(LAB/args.folder/args.label, spec, compose_model())


if __name__ == '__main__':
    main()
