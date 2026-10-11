"""Explicit local imports of existing components, without copying their logic.

Both historical ``seed`` and ``echoai.seed`` spellings share module objects.
No site-package bridge, interpreter install, or benchmark is invoked here.
"""

import importlib
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
PREFIXES = ('seed', 'echo_arc', 'echo4', 'nexus0', 'core')


def module(name):
    # Shared sources are read-only dependencies of this distribution. In
    # particular, importing them must not create caches outside ECHO-5.
    sys.dont_write_bytecode = True
    if not isinstance(name, str):
        raise ValueError('module name required')
    short = name.removeprefix('echoai.')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*(\.[a-zA-Z_][a-zA-Z_0-9]*)*', short):
        raise ValueError('invalid module name')
    if short.split('.')[0] not in PREFIXES:
        raise ValueError('module is outside the integration boundary')
    if any(part.startswith(('s6b', 's6probe')) for part in short.split('.')):
        raise ValueError('sealed experiment imports are forbidden')
    package = sys.modules.get('echoai')
    if package is None:
        spec = importlib.util.spec_from_file_location(
            'echoai', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
        if spec is None or spec.loader is None:
            raise RuntimeError('local echoai source package is missing')
        package = importlib.util.module_from_spec(spec)
        sys.modules['echoai'] = package
        spec.loader.exec_module(package)
    elif str(ROOT) not in getattr(package, '__path__', ()):
        raise RuntimeError('another echoai installation is already loaded')
    # Some unmodified legacy modules still use bare imports. The local directory
    # is made visible only when a caller explicitly requests an integration.
    for path in (ROOT,):
        if str(path) not in sys.path:
            sys.path.append(str(path))
    _aliases()
    result = importlib.import_module('echoai.' + short)
    _aliases()
    return result


def _aliases():
    for name, value in list(sys.modules.items()):
        short = name.removeprefix('echoai.')
        if short.split('.')[0] not in PREFIXES:
            continue
        canonical = 'echoai.' + short
        other = short if name == canonical else canonical
        old = sys.modules.get(other)
        if old is not None and old is not value:
            raise RuntimeError(f'duplicate legacy module identity: {short}')
        sys.modules[other] = value
