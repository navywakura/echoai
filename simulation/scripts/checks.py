"""Run required checks after implementation; intended for a background job."""
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]


def main(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    commands = [
        ('environment', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'check']),
        ('core_tests', [str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/dev.py'), 'test']),
        ('sandbox_tests', [str(ROOT / '.venv-sandbox/bin/python'), '-I', str(ROOT / 'scripts/closure.py'), 'test-external']),
        ('javascript_syntax', ['node', '--check', str(ROOT / 'src/echo5/web/app.js')]),
    ]
    rows, sources, integrity, error = [], None, {}, None
    try:
        sys.path.insert(0, str(ROOT / 'src'))
        from echo5.closure import freeze, preserve, run_process
        sources = freeze(output)
        for name, argv in commands:
            (output / 'status.json').write_text(json.dumps({'phase': name, 'completed': rows}) + '\n')
            result = run_process(argv, output / f'{name}.log', cwd=ROOT, timeout=1800)
            binding = {'schema': 'echo5.check-log.v1', 'name': name, 'argv': argv,
                       'pid': result.get('pid'), 'sources_sha256': sources['own']['sha256']}
            log = output / f'{name}.log'
            raw = log.read_bytes() if log.exists() else b''
            log.write_bytes((json.dumps(binding, sort_keys=True) + '\n').encode() + raw)
            rows.append({'name': name, **result})
            print(json.dumps(rows[-1]), flush=True)
        integrity = preserve(sources)
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    valid = error is None and len(rows) == len(commands) and all(r['exit_code'] == 0 for r in rows)
    artifact_hashes = {f'{name}.log': hashlib.sha256((output / f'{name}.log').read_bytes()).hexdigest()
                       for name, _ in commands if (output / f'{name}.log').is_file()}
    receipt = {'schema': 'echo5.required-checks.v2', 'valid': valid,
               'commands': rows, 'cpu_background': True,
               'artifact_hashes': artifact_hashes,
               'sources_sha256': sources['own']['sha256'] if sources else None,
               'integrity': integrity, 'error': error}
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'status.json').write_text(json.dumps({
        'phase': 'instrument_error' if error else 'complete', **receipt}) + '\n')
    return 0 if receipt['valid'] else 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -I scripts/checks.py OUTPUT_NEW_DIRECTORY')
    sys.exit(main(sys.argv[1]))
