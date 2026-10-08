"""Configure PX4 through its parameter interface, then run the frozen driver.

No pose or sensor data are fed back. The per-run configuration is fixed on A.
This adapter is mounted beside the original flightrunner.py by session.py.
"""
import json
import math
import os
import sys
import threading

import flightrunner as original

PARAMETERS = json.loads(os.environ.get('FLIGHT1S_PARAMETERS', '{}'))
ALLOWED = {'EKF2_GPS_DELAY', 'MPC_XY_VEL_P_ACC', 'MPC_XY_VEL_D_ACC',
           'MPC_XY_VEL_I_ACC', 'EKF2_NOAID_NOISE', 'EKF2_GPS_P_NOISE'}
if not set(PARAMETERS) <= ALLOWED:
    raise ValueError('unexpected flight parameter')


class ConfiguredDriver(original.Driver):
    def connect(self, timeout_s):
        if not super().connect(timeout_s):
            return False
        for name, value in sorted(PARAMETERS.items()):
            if not super().set_param(name, value, original.mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
                return False
            actual = self.events[-1].get('value')
            if actual is None or not math.isclose(actual, value, abs_tol=1e-5):
                raise RuntimeError('PX4 parameter readback mismatch: ' + name)
        return True


if __name__ == '__main__':
    # PID 1 exits on wall time even when Gazebo's clock stops. Podman tears
    # down the container namespace and its children before host timeout.
    config = json.loads(sys.argv[1])
    def deadline():
        original.emit({'ev': 'watchdog_timeout', 'clock': 'wall'})
        os._exit(124)
    watchdog = threading.Timer(config['timeouts']['episode_s'], deadline)
    watchdog.daemon = True
    watchdog.start()
    mutant = os.environ.get('FLIGHT1S_MUTANT')
    if mutant == 'noforce':
        original.Backend.apply_wrench = lambda self, link, force: True
    elif mutant == 'frozen_clock':
        original.Backend.now_ns = lambda self: 1
    elif mutant == 'accumulate':
        apply = original.Backend.apply_wrench
        def accumulated(self, link, force):
            return all(apply(self, link, force) for _ in range(10))
        original.Backend.apply_wrench = accumulated
    original.Driver = ConfiguredDriver
    try:
        sys.exit(original.main())
    finally:
        watchdog.cancel()
