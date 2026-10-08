"""Mutant backend: a real flight whose reported clock never advances."""

import sys

sys.path.insert(0, "/flight")
import flightrunner  # noqa: E402

_FROZEN = 1_000_000


def _frozen(self):  # noqa: ARG001
    return _FROZEN


flightrunner.Backend.now_ns = _frozen

if __name__ == "__main__":
    sys.exit(flightrunner.main())
