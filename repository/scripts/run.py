#!/usr/bin/env python3
"""Repository-local PCWORLD entry point; never imports another installation."""
import importlib.util
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('echoai', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules['echoai'] = package
spec.loader.exec_module(package)
if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='test':
        import unittest
        names=sys.argv[2:]
        suite=(unittest.defaultTestLoader.loadTestsFromNames(names) if names else
               unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_pcworld_*.py',top_level_dir=str(ROOT)))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(not result.wasSuccessful())
    from echoai.pcworld.cli import main
    raise SystemExit(main())
