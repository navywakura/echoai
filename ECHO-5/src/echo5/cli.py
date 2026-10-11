"""Small reproducible CLI for grounded solving, development banks and audit."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

from .budget import Budget
from .evaluation import check_sources, digest, source_snapshot
from .distribution import CORE_FILES
from .trace import Recorder, verify_journal

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def progress(path, phase):
    value = {'phase': phase, 'utc': datetime.now(timezone.utc).isoformat()}
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value) + '\n')
    pending.replace(path)
    print(json.dumps(value), flush=True)


def bench(output, contract):
    from .evaluation import grid_benchmark
    from .adversarial import run_benchmark as curriculum
    from .interaction import run_benchmark as interaction
    from .robotics import run_benchmark as robotics
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    config = json.loads(Path(contract).read_text())
    write_json(output / 'contract.json', config)
    source = source_snapshot(ROOT, ['src', 'scripts', 'tests', 'docs/BENCHMARK-CONTRACT.json',
                                    'pyproject.toml', '.python-version'],
                             suffixes=('.py', '.json', '.toml', ''))
    legacy_folders = ['seed', 'echo_arc', 'echo4', 'nexus0', '__init__.py']
    original = source_snapshot(ROOT.parent, legacy_folders,
                               suffixes=('.py', '.json', '.bnf', '.txt'))
    host = source_snapshot(ROOT.parent, CORE_FILES)
    write_json(output / 'sources.json', source)
    write_json(output / 'legacy-sources.json', original)
    write_json(output / 'host-sources.json', host)
    with zipfile.ZipFile(output / 'sources.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for prefix, base, receipt in (('ECHO-5', ROOT, source),
                                       ('echoai', ROOT.parent, original),
                                       ('host', ROOT.parent, host)):
            for name in receipt['files']:
                archive.write(base / name, arcname=f'{prefix}/{name}')
    start = time.monotonic()
    try:
        with Recorder(output / 'thought.jsonl') as journal:
            journal.write(kind='experiment_contract', contract_sha256=digest(config),
                          source_sha256=source['sha256'], neocortex='off')
            progress(output / 'status.json', 'grid_acquisition_and_transfer')
            grid = grid_benchmark(config['grid'], journal=journal)
            write_json(output / 'grid.json', grid)
            progress(output / 'status.json', 'counterexample_curriculum')
            adversarial = curriculum(config['curriculum'], journal=journal)
            write_json(output / 'curriculum.json', adversarial)
            progress(output / 'status.json', 'interaction')
            interact = interaction(**config['interaction'], journal=journal)
            write_json(output / 'interaction.json', interact)
            progress(output / 'status.json', 'robotics_integration')
            robot = robotics(**config['robotics'], journal=journal)
            write_json(output / 'robotics.json', robot)
            preservation = check_sources(ROOT.parent, original)
            own_sources = check_sources(ROOT, source)
            host_preservation = check_sources(ROOT.parent, host)
            if not (preservation['unchanged'] and own_sources['unchanged'] and host_preservation['unchanged']):
                raise RuntimeError('sources changed during experiment')
            journal.write(kind='experiment_complete', legacy_unchanged=True,
                          new_sources_unchanged=True, s6_green=False)
        report = {'schema': 'echo5.integration-results.v1', 'status': 'measured_pending_audit',
                  'scope': config['scope'], 'seconds': time.monotonic()-start, 'python': sys.version,
                  'contract_sha256': digest(config), 'sources_sha256': source['sha256'],
                  'legacy': preservation, 'host_dependencies': host_preservation, 'grid': grid['arms'],
                  'grid_comparisons': grid['comparisons'], 'curriculum': adversarial['totals'],
                  'curriculum_comparisons': adversarial['comparisons'],
                  'journal': verify_journal(output / 'thought.jsonl'),
                  's6_green': False, 'official_arc_score': None, 'llm_calls': 0}
        write_json(output / 'result.json', report)
        manifest = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(output.iterdir()) if p.is_file() and p.name != 'status.json'}
        write_json(output / 'manifest.json', manifest)
        progress(output / 'status.json', 'complete_pending_independent_audit')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        progress(output / 'status.json', 'instrument_stopped')
        write_json(output / 'instrument-error.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description='ECHO-5: desarrollo y evidencia, neocórtex apagado')
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('bench', help='banco controlado sintético con recibos y trazas')
    run.add_argument('--output', required=True)
    run.add_argument('--contract', default=str(ROOT / 'docs/BENCHMARK-CONTRACT.json'))
    audit = commands.add_parser('audit', help='recalcular resultados; opcionalmente repetir casos')
    audit.add_argument('folder')
    audit.add_argument('--replay', action='store_true')
    solve = commands.add_parser('solve', help='inferir una regla desde demostraciones JSON')
    solve.add_argument('task')
    solve.add_argument('--budget', type=int, default=2_000_000)
    solve.add_argument('--memory')
    solve.add_argument('--learn-to', help='guardar memoria adquirida en archivo NUEVO de desarrollo')
    solve.add_argument('--trace', help='diario nuevo de decisiones observadas')
    solve.add_argument('--synthesis-strategy', choices=('baseline', 'memoized', 'certified'),
                       help='síntesis profunda opcional; gramática completa, profundidad 4 y beam 24')
    solve.add_argument('--ranking-bound', action='store_true',
                       help='poda por cota de pérdida; requiere --synthesis-strategy certified')
    args = parser.parse_args(argv)
    if args.command == 'solve' and args.ranking_bound and args.synthesis_strategy != 'certified':
        parser.error('--ranking-bound requires --synthesis-strategy certified')
    try:
        if args.command == 'bench':
            bench(args.output, args.contract)
        elif args.command == 'audit':
            from .audit import audit_bundle
            report = audit_bundle(Path(args.folder), replay=args.replay)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            from .concepts import Library
            from .solver import solve as infer
            library = Library.load(args.memory) if args.memory else Library()
            ledger = Budget(args.budget)
            journal = Recorder(args.trace) if args.trace else None
            try:
                result = infer(json.loads(Path(args.task).read_text()), budget=ledger,
                               library=library, learn=bool(args.learn_to), journal=journal,
                               synthesis=({'strategy': args.synthesis_strategy, 'ranking_bound': args.ranking_bound}
                                          if args.synthesis_strategy else None),
                               cache_policy='interned' if args.synthesis_strategy else 'legacy')
                if args.learn_to:
                    if Path(args.learn_to).exists():
                        raise FileExistsError(args.learn_to)
                    library.save(args.learn_to)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            finally:
                if journal:
                    journal.close()
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
