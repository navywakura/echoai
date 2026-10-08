"""Mutant backend: a harness that moves the body instead of flying it.

Used only by the mutant group and named in the run label. It never arms
PX4; it writes poses straight into the backend so the recorded trace
looks like a takeoff, a hover and a landing. The evaluator must notice —
a teleported body has no armed interval, no motor commands and no
continuous dynamics — and the episode must go red for that reason.

If this ever passes as a flight, the whole slice is worthless.
"""

import json
import os
import subprocess
import sys
import time

import gz.math7  # noqa: F401
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.pose_pb2 import Pose
from gz.transport13 import Node

sys.path.insert(0, "/flight")
import flightrunner  # noqa: E402


def main():
    cfg = json.loads(sys.argv[1])
    world = cfg["world_name"]
    env = dict(os.environ)
    env["GZ_SIM_RESOURCE_PATH"] = flightrunner.PX4_MODELS
    gz = subprocess.Popen(
        ["gz", "sim", "-s", "-r", "--headless-rendering", cfg["world_path"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    node = Node()
    clock = {"ns": 0}
    node.subscribe(Clock, f"/world/{world}/clock",
                   lambda m: clock.__setitem__(
                       "ns", int(m.sim.sec) * 10 ** 9 + int(m.sim.nsec)))
    t0 = time.monotonic()
    while clock["ns"] == 0 and time.monotonic() - t0 < 60:
        time.sleep(0.1)

    x, y, _ = (float(v) for v in cfg["spawn_pose"].split(",")[:3])
    samples = []
    start = clock["ns"]
    for i in range(1500):
        t = clock["ns"]
        phase = i / 1500.0
        z = 1.5 * min(1.0, phase * 4) * (1.0 if phase < 0.85 else 0.0)
        samples.append([t, int(x * 1e6), int(y * 1e6), int(z * 1e6), 0, 0, 0, 0])
        time.sleep(0.002)
    end = clock["ns"]
    span = max(1, end - start)
    plan = []
    cursor = start
    for name, frac in (("climb", 0.25), ("stabilize", 0.1), ("hover", 0.25),
                       ("disturb", 0.05), ("recover", 0.35)):
        step = int(span * frac)
        plan.append([name, cursor, cursor + step])
        cursor += step
    flightrunner.emit({
        "ev": "episode", "ok": True, "cause": None,
        "condition": cfg["condition"],
        "stage_marks": {"rest_z_um": 0, "armed_ns": start, "takeoff_ns": start,
                        "disarmed_ns": end, "landed_ns": end, "plan": plan},
        "samples": samples,
        "sample_columns": ["sim_time_ns", "x_um", "y_um", "z_um", "roll_mdeg",
                           "pitch_mdeg", "yaw_mdeg", "wrench"],
        "wrench_published": 1 if cfg["condition"] == "perturbed" else 0,
        "force_n": [cfg["disturbance"]["force_mn"] / 1000.0, 0.0, 0.0],
        "body_pose_updates": len(samples), "clock_samples": 1,
        "driver_events": [{"event": "teleport_harness"}],
        "px4_tail": [], "ulog": None, "final_sim_time_ns": end,
    })
    gz.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
