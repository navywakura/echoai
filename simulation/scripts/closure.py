"""Explicit CLI for background CPU validation; no cloud or physical hardware."""
import argparse
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not sys.flags.isolated or platform.python_version() != (ROOT / '.python-version').read_text().strip():
        raise RuntimeError('Pinned Python with -I required')
    if Path(sys.prefix).resolve() not in {(ROOT / '.venv').resolve(), (ROOT / '.venv-sandbox').resolve()}:
        raise RuntimeError('Use an ECHO-5 managed environment')
    sys.path.insert(0, str(ROOT / 'src'))
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('campaign', 'audit'):
        sub = commands.add_parser(name)
        sub.add_argument('--output', required=True)
        sub.add_argument('--workers', type=int, default=4)
        if name == 'campaign':
            sub.add_argument('--phase', choices=('development', 'confirmation'), default='development')
    for name in ('worker', 'audit-worker'):
        sub = commands.add_parser(name)
        sub.add_argument('domain', choices=('transfer', 'curriculum', 'sandbox', 'mission'))
        sub.add_argument('--output', required=True)
        if name == 'worker':
            sub.add_argument('--phase', choices=('development', 'confirmation'), default='development')
    tests = commands.add_parser('test-external')
    tests.add_argument('--pattern', default='test_sandbox.py')
    args = parser.parse_args()
    from echo5.closure import run_campaign, audit_campaign, worker, audit_worker
    if args.command == 'campaign':
        return run_campaign(args.output, args.phase, args.workers)
    if args.command == 'audit':
        return audit_campaign(args.output, args.workers)
    if args.command == 'worker':
        worker(args.domain, args.phase, args.output)
        return 0
    if args.command == 'audit-worker':
        audit_worker(args.domain, args.output)
        return 0
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=args.pattern)
    if not suite.countTestCases():
        raise RuntimeError('No external tests selected')
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
