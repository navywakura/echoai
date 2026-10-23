"""Read-only mini terminal over the existing Recorder journals; no agent input."""
import argparse
from collections import deque
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from observe import Tail, clean


def facts(row):
    kind = row.get('kind', 'unknown')
    if kind == 'sandbox_step':
        action = row.get('action') or {}
        hypothesis = (row.get('hypotheses') or {}).get('exploration')
        yield f"paso {row.get('step')} | acción {action.get('name')} | {action.get('reason')}"
        if hypothesis:
            yield 'hipótesis de exploración: ' + clean(hypothesis)
        yield 'consecuencia observada: ' + clean(row.get('consequence'))
        yield 'presupuesto: ' + clean(row.get('budget'))
    elif kind == 'synthesis_candidate':
        yield f"prefijo profundidad {row.get('depth')} | {row.get('disposition')} | pérdida {row.get('loss')}"
        yield 'programa evaluado: ' + clean(row.get('program'))
    else:
        visible = {k:v for k,v in row.items() if k not in
                   ('schema','hash','prev','agent','time','index','kind','snapshot')}
        yield kind + ' | ' + clean(visible)


def watch(folder, once=False):
    followers, lines = {}, deque(maxlen=100)
    while True:
        for path in sorted(folder.glob('*/thought.jsonl')):
            new = path not in followers
            if new:
                followers[path] = Tail(path)
            try:
                rows = followers[path].read(history=2 if new else None)
                for row in rows:
                    lines.append(('HISTÓRICO' if new else 'REGISTRO') + ' | ' + path.parent.name)
                    lines.extend(facts(row))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                lines.append('Error de lectura: ' + clean(str(exc)))
        state = {}
        if (folder/'status.json').exists():
            try:
                state = json.loads((folder/'status.json').read_text())
            except (OSError, ValueError):
                pass
        width, height = shutil.get_terminal_size((110, 30))
        header = ['ECHO-5 | piloto de mecanismos | observaciones ≠ predicciones',
                  f"{state.get('phase','esperando')} | {state.get('stage','')} | diario pasivo; auditoría separada",
                  str(folder), '─'*min(width-1, 109)]
        output = header + list(lines)[-max(1, height-5):]
        if sys.stdout.isatty() and not once:
            print('\033[H\033[2J', end='')
        print('\n'.join(clean(line, width-1) for line in output), flush=True)
        if once:
            return
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.launch:
        terminal = shutil.which('xfce4-terminal')
        if not terminal:
            parser.error('No hay xfce4-terminal; ejecutar sin --launch')
        subprocess.Popen([terminal, '--disable-server', '--title=ECHO-5 · investigación',
            '--geometry=112x32', '-x', sys.executable, '-I', __file__, str(args.folder.resolve())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
    else:
        try:
            watch(args.folder.resolve(), args.once)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
