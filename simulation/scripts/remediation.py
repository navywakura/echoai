"""Post-r3 CPU research: launch, run or fresh-process audit a single stage."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from echo5.remediation import STAGES, launch, run, worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('launch', 'run', 'worker'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES)
    parser.add_argument('--action', choices=('measure', 'audit'))
    args = parser.parse_args()
    if args.command == 'launch':
        print(json.dumps(launch(args.output), indent=2))
    elif args.command == 'run':
        run(args.output)
    elif args.stage and args.action:
        worker(args.output, args.stage, args.action)
    else:
        parser.error('worker needs --stage and --action')


if __name__ == '__main__':
    main()
