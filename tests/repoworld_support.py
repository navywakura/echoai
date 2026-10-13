"""Load this checkout, even when its worktree directory is not named echoai."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if 'echoai' not in sys.modules:
    spec = importlib.util.spec_from_file_location('echoai', ROOT / '__init__.py',
                                                 submodule_search_locations=[str(ROOT)])
    package = importlib.util.module_from_spec(spec)
    sys.modules['echoai'] = package
    spec.loader.exec_module(package)
