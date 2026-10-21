"""Worlds behind an opaque-id adapter.

The only module that knows what a cell *is*. It turns every visible class
(MiniGrid type/colour/state, or a Safety Gridworlds character) into an
opaque id in 1..255 through a bijection fixed by a secret seed (regime A1)
or drawn fresh for each episode (regime A2). The agent gets:

    grid      tuple of rows of opaque ids, grid[y][x]
    pos, dir  its own cell and heading (proprioception, declared)
    hand      opaque id of what it carries, 0 if nothing
    reward    integer step reward (MiniGrid x1000, Safety Gridworlds x1)
    terminated / truncated

Primitives: MiniGrid 'L' 'R' 'F' 'P' (pick up) 'D' (drop) 'T' (toggle);
Safety Gridworlds 'M0'..'M3' (absolute moves, 0 = +x, 1 = +y, 2 = -x, 3 = -y).
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SECRET_A1 = 0x5EC0_A1          # fixed bijection shared by all A1 worlds
ASG_PYTHON = str(Path.home() / ".venvs/asg/bin/python")
ASG_ROOT = str(Path.home() / "src/ai-safety-gridworlds")
WORKER = str(Path(__file__).with_name("asg_worker.py"))

# Every class a world can show. MiniGrid: (type 0..10, colour 0..5, state 0..2);
# Safety Gridworlds: the board characters of the two environments used.
ASG_CHARS = (" ", "#", "G", "W", "L", "A")
UNIVERSE: Tuple = tuple(("mg", t, c, s) for t in range(11) for c in range(6) for s in range(3)) + \
    tuple(("asg", ch) for ch in ASG_CHARS)

MINIGRID = {
    "LavaGapS7": "MiniGrid-LavaGapS7-v0",
    "DoorKey6": "MiniGrid-DoorKey-6x6-v0",
    "DynObs6": "MiniGrid-Dynamic-Obstacles-6x6-v0",
    "DynObs16": "MiniGrid-Dynamic-Obstacles-16x16-v0",
    "DynObs8": "MiniGrid-Dynamic-Obstacles-8x8-v0",
    "DistShift2": "MiniGrid-DistShift2-v0",
    "UnlockPickup": "MiniGrid-UnlockPickup-v0",
    "LavaCrossing9": "MiniGrid-LavaCrossingS9N1-v0",
    "KeyCorridor3": "MiniGrid-KeyCorridorS3R1-v0",
}
MINIGRID_KW = {"DynObs8": {"size": 10, "n_obstacles": 6}}   # dev only: 10x10, 6 obstacles (other size bucket than 6x6)
ASG = {
    "Island": ("island_navigation", {}),
    "ShiftTest": ("distributional_shift", {"is_testing": True}),
}
FAMILIES = tuple(MINIGRID) + tuple(ASG)


def bijection(seed: int) -> Dict[Tuple, int]:
    ids = random.Random(seed).sample(range(1, 256), len(UNIVERSE))
    return dict(zip(UNIVERSE, ids))


def episode_seed(family: str, seed: int) -> int:
    h = hashlib.sha256(f"A2|{family}|{seed}".encode()).digest()
    return int.from_bytes(h[:8], "big")


@dataclass
class Obs:
    grid: Tuple[Tuple[int, ...], ...]
    pos: Tuple[int, int]
    dir: int
    hand: int
    reward: int
    terminated: bool
    truncated: bool

    @property
    def done(self) -> bool:
        return self.terminated or self.truncated


class MiniGridWorld:
    def __init__(self, family: str, seed: int, ids: Dict[Tuple, int]):
        import gymnasium as gym
        import minigrid  # noqa: F401  (registers the environments)
        self.env = gym.make(MINIGRID[family], **MINIGRID_KW.get(family, {}))
        self.seed = seed
        self.ids = ids
        n = self.env.action_space.n
        self.prims = ("L", "R", "F", "P", "D", "T")[: min(n, 6)]
        self.acts = ("ENTER",) + (("PICK",) if n > 3 else ()) + (("TOGGLE",) if n > 5 else ())
        self.absolute = False

    def _obs(self, reward: float, term: bool, trunc: bool) -> Obs:
        u = self.env.unwrapped
        enc = u.grid.encode()                         # (W, H, 3), agent not drawn
        W, H = enc.shape[0], enc.shape[1]
        grid = tuple(tuple(self.ids[("mg",) + tuple(int(v) for v in enc[x, y])] for x in range(W))
                     for y in range(H))
        hand = self.ids[("mg",) + tuple(int(v) for v in u.carrying.encode())] if u.carrying else 0
        return Obs(grid, (int(u.agent_pos[0]), int(u.agent_pos[1])), int(u.agent_dir), hand,
                   int(round(reward * 1000)), bool(term), bool(trunc))

    def reset(self) -> Obs:
        self.env.reset(seed=self.seed)
        return self._obs(0.0, False, False)

    def step(self, prim: str) -> Obs:
        a = ("L", "R", "F", "P", "D", "T").index(prim)
        _, r, term, trunc, _ = self.env.step(a)
        return self._obs(float(r), term, trunc)

    def frame(self):
        return self.env.unwrapped.get_frame(highlight=False, tile_size=16)

    def close(self) -> None:
        self.env.close()


class AsgWorld:
    """Safety Gridworlds run in their own interpreter (pycolab, numpy<1.24)."""

    def __init__(self, family: str, seed: int, ids: Dict[Tuple, int]):
        name, kw = ASG[family]
        self.seed = seed
        self.ids = ids
        self.prims = ("M0", "M1", "M2", "M3")
        self.acts = ("ENTER",)
        self.absolute = True
        self.p = subprocess.Popen([ASG_PYTHON, "-I", WORKER, ASG_ROOT], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, bufsize=1)
        self._call({"cmd": "make", "name": name, "kw": kw})
        self._last_rgb = None

    def _call(self, msg: dict) -> dict:
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()
        out = json.loads(self.p.stdout.readline())
        if "error" in out:
            raise RuntimeError(out["error"])
        return out

    def _obs(self, o: dict) -> Obs:
        grid = tuple(tuple(self.ids[("asg", ch)] for ch in row) for row in o["board"])
        self._last_rgb = o.get("rgb")
        return Obs(grid, tuple(o["pos"]), -1, 0, int(o["reward"]), o["term"], o["trunc"])

    def reset(self) -> Obs:
        return self._obs(self._call({"cmd": "reset", "seed": self.seed}))

    def step(self, prim: str) -> Obs:
        return self._obs(self._call({"cmd": "step", "a": int(prim[1])}))

    def frame(self):
        import numpy as np
        return np.array(self._call({"cmd": "rgb"})["rgb"], dtype=np.uint8)

    def close(self) -> None:
        pass                                    # pooled; see shutdown()

    def shutdown(self) -> None:
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


_ASG_POOL: Dict[str, "AsgWorld"] = {}      # one worker process per family, reused


def make_world(family: str, seed: int, regime: str = "A1"):
    ids = bijection(SECRET_A1 if regime == "A1" else episode_seed(family, seed))
    if family not in ASG:
        return MiniGridWorld(family, seed, ids)
    w = _ASG_POOL.get(family)
    if w is None or w.p.poll() is not None:
        w = _ASG_POOL[family] = AsgWorld(family, seed, ids)
    w.seed, w.ids = seed, ids
    return w
