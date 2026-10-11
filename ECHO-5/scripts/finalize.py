"""Produce release readiness only from bound, independently audited receipts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not sys.flags.isolated or Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
        raise RuntimeError('Use ECHO-5 .venv/bin/python -I')
    sys.path.insert(0, str(ROOT / 'src'))
    from echo5.release import finalize
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('campaign', 'checks', 'browser', 'sitl', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    result = finalize(args.campaign, args.checks, args.browser, args.sitl, args.output)
    print(json.dumps(result, indent=2))
    return 0 if result['release_eligible'] else 1


if __name__ == '__main__':
    sys.exit(main())
