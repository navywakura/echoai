"""Run the local viewer in the separately pinned MiniGrid environment."""
import argparse
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    if not sys.flags.isolated or platform.python_version() != (ROOT / '.python-version').read_text().strip():
        raise SystemExit('Usa Python 3.12.13 con -I en el entorno aislado de ECHO-5')
    if Path(sys.prefix).resolve() not in {(ROOT / '.venv').resolve(), (ROOT / '.venv-sandbox').resolve()}:
        raise SystemExit('Se requiere .venv o .venv-sandbox de ECHO-5')
    parser = argparse.ArgumentParser(description='Panel local de decisiones ECHO-5')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--root')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'src'))
    from echo5.control import serve
    serve(args.port, args.root)
