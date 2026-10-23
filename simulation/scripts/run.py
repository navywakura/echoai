"""Pinned, isolated entry point for ECHO-5 development. No cloud/model calls."""

from pathlib import Path
import sys

if __name__ == '__main__':
    # -I deliberately omits the script directory; add only our own helper path.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dev import check_environment
    check_environment()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from echo5.cli import main
    sys.exit(main())
