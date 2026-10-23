"""Mechanical preflight in a bounded subprocess; runtime still uses the interpreter."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from types import SimpleNamespace
from .language import Program
from .runtime import View, Context, HAgent


def tuples(value):
    if isinstance(value, (list, tuple)):
        return tuple(tuples(x) for x in value)
    if isinstance(value, dict):
        return {k: tuples(v) for k, v in value.items()}
    return value


def evaluate(source, states):
    try:
        program = Program(source)
    except Exception as exc:
        return {'green': False, 'stage': 'AST', 'error': type(exc).__name__, 'detail': str(exc)[:160]}
    if len(states) != 200:
        return {'green': False, 'stage': 'states', 'error': 'expected 200'}
    signatures = []
    for index, row in enumerate(states):
        view = View(**tuples(row['view']))
        context = Context(**tuples(row['context']))
        try:
            effects = program(row['moment'], view, context)
        except Exception as exc:
            return {'green': False, 'stage': 'execution', 'index': index, 'error': type(exc).__name__, 'detail': str(exc)[:160]}
        try:
            obs = SimpleNamespace(grid=view.grid, pos=view.pos, hand=view.hand)
            world = SimpleNamespace(acts=('ENTER', 'PICK', 'TOGGLE'))
            HAgent._validate(None, effects, row['moment'], obs, world, context, view)
        except Exception as exc:
            return {'green': False, 'stage': 'effects', 'index': index, 'error': type(exc).__name__, 'detail': str(exc)[:160]}
        signatures.append(effects)
    return {'green': True, 'states': len(states), 'responses': signatures}


def check(source, states):
    root = Path(__file__).resolve().parents[3]
    env = {'PATH': os.defpath, 'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'}
    try:
        result = subprocess.run([sys.executable, '-m', 'echoai.echo58.crece.mechanical'],
                                input=json.dumps({'source': source, 'states': states}),
                                text=True, capture_output=True, env=env, timeout=30, cwd=root)
    except subprocess.TimeoutExpired:
        return {'green': False, 'stage': 'process', 'error': 'timeout'}
    if result.returncode != 0:
        return {'green': False, 'stage': 'process', 'error': 'worker_exit', 'returncode': result.returncode}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {'green': False, 'stage': 'process', 'error': 'invalid_worker_response'}


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    payload = json.loads(sys.stdin.read(16 * 1024 * 1024))
    print(json.dumps(evaluate(payload['source'], payload['states'])))
