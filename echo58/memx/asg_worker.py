"""Safety Gridworlds worker: JSON lines on stdin/stdout, run with ~/.venvs/asg.

Replies with the board as characters, the agent cell drawn over by what it
stands on, the integer step reward and whether the episode ended by its own
rules (term) or by the step limit (trunc).
"""
import json
import sys
import warnings

warnings.filterwarnings("ignore")

sys.path.insert(0, sys.argv[1])

import numpy as np  # noqa: E402
from ai_safety_gridworlds.helpers import factory  # noqa: E402
from ai_safety_gridworlds.environments.shared import safety_game  # noqa: E402
from ai_safety_gridworlds.environments.shared.termination_reason_enum import TerminationReason  # noqa: E402

ACTIONS = {0: 3, 1: 1, 2: 2, 3: 0}     # 0 +x right, 1 +y down, 2 -x left, 3 -y up


class W:
    def __init__(self, name, kw):
        self.env = factory.get_environment_obj(name, **kw)
        self.chars = {int(v): ch for ch, v in self.env._value_mapping.items()}
        self.agent = int(self.env._value_mapping["A"])
        self.under = {}
        self.pos = (0, 0)
        self.ts = None

    def view(self, ts):
        board = ts.observation["board"].astype(int)
        H, W_ = board.shape
        rows = []
        for y in range(H):
            row = []
            for x in range(W_):
                v = int(board[y, x])
                if v == self.agent:
                    self.pos = (x, y)
                    row.append(self.under.get((x, y), " "))
                else:
                    self.under[(x, y)] = self.chars[v]
                    row.append(self.chars[v])
            rows.append(row)
        term = trunc = False
        if ts.last():
            reason = safety_game.timestep_termination_reason(ts)
            trunc = reason == TerminationReason.MAX_STEPS
            term = not trunc
        return {"board": rows, "pos": list(self.pos), "reward": int(round(float(ts.reward or 0.0))),
                "term": term, "trunc": trunc}


def main():
    w = None
    for line in sys.stdin:
        msg = json.loads(line)
        try:
            if msg["cmd"] == "make":
                w = W(msg["name"], msg["kw"])
                out = {"ok": True}
            elif msg["cmd"] == "reset":
                np.random.seed(msg["seed"])
                w.under = {}
                w.ts = w.env.reset()
                out = w.view(w.ts)
            elif msg["cmd"] == "step":
                w.ts = w.env.step(ACTIONS[msg["a"]])
                out = w.view(w.ts)
            elif msg["cmd"] == "rgb":
                rgb = np.moveaxis(w.ts.observation["RGB"], 0, -1).astype(int)
                out = {"rgb": rgb.tolist()}
            else:
                out = {"error": "bad cmd"}
        except Exception as e:  # report, never hang the parent
            out = {"error": repr(e)}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
