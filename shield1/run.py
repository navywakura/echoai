"""SHIELD-1 runner on Safety-Gymnasium (docs/SHIELD1-DESIGN.md).

Boundary only: lidar floats -> int closeness 0..100, chosen heading ->
actuator floats. Decisions are made in shield1/gate.py with ints.

Policies:
  RND     uniform random actions
  SEEK    blind goal seeker: heads for the strongest goal-lidar bin
  ECHO-P  SEEK + gate told which channels cost (ablation)
  ECHO-L  SEEK + gate that learns risk from cost (tables start at 0)
"""

from __future__ import annotations

import os

os.environ.setdefault("MUJOCO_GL", "egl")

from typing import Dict, List, Optional, Tuple

import numpy as np

from echoai.shield1.gate import BINS, MARGIN, Gate, ang

FORWARD_BIN = {"Point": 0, "Car": 12}   # ego lidar bin the robot drives toward (measured)
STEPS = 1000
VERDICTS = {0: "OK", 1: "MODIFY", 2: "BLOCK"}


def make(task: str, render: bool = False):
    import safety_gymnasium as sg
    return (sg.make(task, render_mode="rgb_array", width=320, height=320, camera_name="track")
            if render else sg.make(task))


def slices(env) -> Dict[str, slice]:
    out, i = {}, 0
    for k, sp in env.task.obs_info.obs_space_dict.items():
        n = int(np.prod(sp.shape))
        out[k] = slice(i, i + n)
        i += n
    return out


def lidar_ints(obs, sl: Dict[str, slice]) -> Dict[str, List[int]]:
    return {k[:-6]: [int(round(float(v) * 100)) for v in obs[s]] for k, s in sl.items() if k.endswith("_lidar")}


def costly_channels(env) -> Tuple[str, ...]:
    t = env.task
    out = []
    for name in ("hazards", "vases", "pillars", "gremlins"):
        obj = getattr(t, name, None)
        if obj is not None and getattr(obj, "num", 0) and getattr(obj, "is_constrained", False):
            out.append(name)
    return tuple(out)


def move_bin(env, robot: str) -> Optional[int]:
    """Ego lidar bin of the velocity, None below 0.2 m/s (boundary, float)."""
    vel = env.task.agent.vel[:2]
    if float(np.hypot(*vel)) < 0.2:
        return None
    ev = env.task.agent.mat[:2, :2].T @ vel
    return int((np.arctan2(ev[1], ev[0]) % (2 * np.pi)) // (2 * np.pi / BINS)) % BINS


def forward_speed(env, robot: str) -> float:
    ev = env.task.agent.mat[:2, :2].T @ env.task.agent.vel[:2]
    return float(ev[0]) if robot == "Point" else float(-ev[1])


def actuate(robot: str, heading: int, brake: bool = False, vf: float = 0.0) -> np.ndarray:
    rel = (heading - FORWARD_BIN[robot]) % BINS
    a = rel if rel < BINS // 2 else rel - BINS          # + = counter-clockwise
    err = a * 2 * np.pi / BINS
    if robot == "Point":
        fwd = float(np.clip(-2 * vf, -1, 1)) if brake else (1.0 if abs(a) <= 2 else 0.0)
        return np.array([fwd, float(np.clip(err * 2, -1, 1))])
    v = float(np.clip(-2 * vf, -1, 1)) if brake else (1.0 if abs(a) <= 1 else (0.3 if abs(a) <= 3 else 0.0))
    k = float(np.clip(err * 1.5, -1, 1))
    return np.clip(np.array([v + k, v - k]), -1, 1)


def episode(env, task: str, policy: str, seed: int, gate: Optional[Gate] = None,
            frames: Optional[list] = None, frame_every: int = 4, actor=None) -> Dict:
    robot = "Point" if "Point" in task else "Car"
    sl = slices(env)
    obs, _ = env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    ret = 0.0
    cost = 0
    goals = 0
    verdicts = [0, 0, 0]
    last = None
    for t in range(STEPS):
        if policy == "RND":
            act = rng.uniform(-1, 1, size=2)
        elif actor is not None:
            act = actor(obs)
        else:
            lid = lidar_ints(obs, sl)
            g = lid["goal"]
            proposed = max(range(BINS), key=lambda b: (g[b], -ang(b, FORWARD_BIN[robot])))
            heading, brake = proposed, False
            if gate is not None:
                heading, brake, v = gate.decide(lid, proposed, move_bin(env, robot))
                verdicts[v] += 1
                last = v
            act = actuate(robot, heading, brake, forward_speed(env, robot))
        obs, r, c, term, trunc, info = env.step(act)
        c = int(c > 0)
        ret += float(r)
        cost += c
        goals += int(bool(info.get("goal_met", False)))
        if gate is not None:
            gate.observe(lidar_ints(obs, sl), c)
        if frames is not None and t % frame_every == 0:
            frames.append((env.render(), t, cost, last, goals))
        if term or trunc:
            break
    return {"seed": seed, "return": round(ret, 3), "cost": cost, "goals": goals,
            "ok": verdicts[0], "modify": verdicts[1], "block": verdicts[2]}


def new_gate(env, policy: str, margin: int = MARGIN) -> Optional[Gate]:
    chans = tuple(k[:-6] for k in slices(env) if k.endswith("_lidar"))
    if policy == "ECHO-L":
        return Gate(chans, "learned", margin=margin)
    if policy == "ECHO-P":
        return Gate(chans, "prior", costly_channels(env), margin=margin)
    return None


def train(task: str, seeds) -> Tuple[Gate, List[Dict]]:
    """ECHO-L learns on its own training worlds; returns the gate and the
    cost paid while learning (safe-RL counts it)."""
    env = make(task)
    gate = new_gate(env, "ECHO-L")
    log = [episode(env, task, "ECHO-L", s, gate) for s in seeds]
    env.close()
    gate.learning = False
    return gate, log

