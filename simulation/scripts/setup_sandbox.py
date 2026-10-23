"""Install/check the optional, isolated MiniGrid profile; never run episodes."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.venv-sandbox'
LOCK = ROOT / 'requirements-sandbox.lock'
PYTHON = '3.12.13'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='imports/versions only')
    parser.add_argument('--wheel-dir', type=Path,
                        help='install offline from this directory, with locked hashes')
    args = parser.parse_args()
    if not sys.flags.isolated or platform.python_version() != PYTHON:
        raise RuntimeError(f'Use python3.12 -I with CPython {PYTHON}')
    if ENV.is_symlink():
        raise RuntimeError('The sandbox environment must not be a symlink')
    if not ENV.exists():
        if args.check:
            raise RuntimeError('Run setup_sandbox.py without --check first')
        if sys.prefix != sys.base_prefix:
            raise RuntimeError('Create the sandbox with the system interpreter')
        venv.EnvBuilder(with_pip=True, system_site_packages=False).create(ENV)
    config = (ENV / 'pyvenv.cfg').read_text().lower()
    if 'include-system-site-packages = false' not in config:
        raise RuntimeError('Sandbox must exclude global packages')
    python = str(ENV / 'bin' / 'python')
    if not args.check:
        offline = (['--no-index', '--find-links', str(args.wheel_dir.resolve())]
                   if args.wheel_dir is not None else [])
        subprocess.run([python, '-I', '-m', 'pip', '--isolated', 'install', '--no-cache-dir',
                        '--disable-pip-version-check', '--require-hashes',
                        '--only-binary=:all:', *offline, '-r', str(LOCK)], check=True)
    # Import only: gym.make/reset/step and tests are intentionally absent.
    code = (
        'import sys,json; from pathlib import Path; '
        f'assert Path(sys.prefix).resolve() == Path({str(ENV)!r}).resolve(); '
        f'sys.path.insert(0, {str(ROOT / "src")!r}); '
        'from echo5.sandbox import dependency_status; '
        'print(json.dumps(dependency_status(require=True), sort_keys=True))'
    )
    subprocess.run([python, '-I', '-c', code], check=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        sys.exit(1)
