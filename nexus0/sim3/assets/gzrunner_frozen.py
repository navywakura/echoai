"""Mutant backend: a Gazebo that runs but reports a clock that never moves.

Used only by the mutant group, and named in the run label. The bench must
notice that the observed sim time stopped advancing and go red with
``clock_not_monotonic`` — a supervisor that trusted the step counter and
synthesised times would sail past this.
"""

import sys

sys.path.insert(0, "/sim3")

import gzrunner  # noqa: E402

gzrunner._ns = lambda _stamp: 1_000_000

if __name__ == "__main__":
    sys.exit(gzrunner.main())
