"""Mutant backend: declares the disturbance and never publishes the wrench.

Everything else is the real runner — real Gazebo, real PX4, real flight.
Only ``apply_wrench`` is disarmed, and it still reports success, exactly
as a broken or dishonest harness would. The impulse check has to catch
it: no wrench means no change of momentum, so the ratio collapses toward
zero while the episode otherwise looks perfect.
"""

import sys

sys.path.insert(0, "/flight")
import flightrunner  # noqa: E402


def _no_force(self, link, force_n):  # noqa: ARG001
    return True


flightrunner.Backend.apply_wrench = _no_force

if __name__ == "__main__":
    sys.exit(flightrunner.main())
