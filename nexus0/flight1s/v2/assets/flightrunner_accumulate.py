"""Mutant backend: republishes the wrench on every sample of the window.

``/world/<w>/wrench/persistent`` adds a wrench per message rather than
replacing it, so publishing it in the sampling loop sums into kilonewtons.
This is not hypothetical: it is what happened during v1 development and it
threw the X500 fifty-four metres. The v2 stimulus group must refuse it,
either because the publication count is not one or because the measured
impulse ratio leaves the frozen band.
"""

import sys

sys.path.insert(0, "/flight")
import flightrunner  # noqa: E402

_real_apply = flightrunner.Backend.apply_wrench


def _accumulate(self, link, force_n):
    # No "already applied" guard: the supervisor loop calls this once, so
    # the mutation is to keep pushing for the rest of the window.
    ok = _real_apply(self, link, force_n)
    for _ in range(9):
        _real_apply(self, link, force_n)
    return ok


flightrunner.Backend.apply_wrench = _accumulate

if __name__ == "__main__":
    sys.exit(flightrunner.main())
