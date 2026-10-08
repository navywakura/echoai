"""``python3 -m echoai.gui4`` — open the GUI-4 window."""
from __future__ import annotations

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
