"""ECHO-AI source distribution; deterministic core and optional adviser harness."""
from pathlib import Path
import sys
__version__='5.8.0'
# The flat research tree has established top-level development imports.
# Keep them working in a wheel without external parent modules.
_source=str(Path(__file__).resolve().parent)
if _source not in sys.path:sys.path.append(_source)
