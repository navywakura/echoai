"""
NEXUS-4c — replay the thought log in a terminal.

    python3 -m echoai.nexus0.view echoai/lab/thought.jsonl
    python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --fps 20
    python3 -m echoai.nexus0.view echoai/lab/thought.jsonl --follow

Stdlib only: no pygame, no web, no matplotlib. This draws what the log
says and nothing else — it is a replay of the fast loop, not a picture
of a brain.

The ring backdrop starts from the env's initial layout and is corrected
from the log as the agent stands on cells: that is how the phase F
threat move (7 → 8) shows up. Cells the agent never visits keep their
initial symbol.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from echoai.nexus0.constants import N_CELLS
from echoai.nexus0.env import KIND_GOAL, KIND_NAME, KIND_NOVEL, KIND_THREAT, RingEnv
from echoai.nexus0.thought import ACTION_NAME

SYMBOL = {"EMPTY": "·", "GOAL": "G", "THREAT": "T", "NOVEL": "N"}
AGENT = "@"
ROW = 16
BAR = 12  # columns for a full-scale Q bar

CLEAR = "\x1b[2J\x1b[H"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"


def initial_layout() -> Dict[int, str]:
    env = RingEnv()
    return {i: KIND_NAME[k] for i, k in enumerate(env.kind)}


def _bar(v: int, width: int = BAR) -> str:
    """Integer bar, signed. Left of the centre is negative."""
    n = max(-width, min(width, int(v) * width // 127 if abs(v) > width else int(v)))
    if n >= 0:
        return " " * width + "|" + "#" * n + " " * (width - n)
    return " " * (width + n) + "#" * (-n) + "|" + " " * width


def render(record: dict, layout: Dict[int, str], color: bool = True) -> str:
    """One turn as text. Returns a string so it can be tested."""
    b, d, r = (BOLD, DIM, RESET) if color else ("", "", "")
    cell = int(record["cell"])
    layout = dict(layout)
    layout[cell] = record["kind"]

    lines: List[str] = []
    for start in range(0, N_CELLS, ROW):
        span = range(start, start + ROW)
        idx = "".join(f"{i % 10}" for i in span)
        # The ring keeps the true kind; the agent gets its own row, so
        # standing on the NOVEL cell does not erase the N.
        row = "".join(SYMBOL.get(layout.get(i, "EMPTY"), "?") for i in span)
        mark = "".join(AGENT if i == cell else " " for i in span)
        lines.append(f"  {d}{idx}{r}")
        lines.append(f"  {b}{row}{r}")
        lines.append(f"  {mark}")

    q = record["q_row"]
    lines.append("")
    for name, v in zip(ACTION_NAME, q):
        mark = " <" if ACTION_NAME[int(record["action"])] == name else ""
        lines.append(f"  {name:<9}{v:+5d}  {_bar(v)}{mark}")

    lines.append("")
    lines.append(f"  {b}{record['wsp']}{r}")
    att = record["reason_name"].upper() if record["attend_on"] else "OFF"
    lines.append(
        f"  turn {record['turn']:>3}  cell {cell:>2} {record['kind']:<6}"
        f"  r {record['reward']:+3d}  ATTEND {att}"
    )
    lines.append(
        f"  {d}t_pred {record['t_pred']}  questions {record['questions']}"
        f"  cortex_calls {record['cortex_calls']}{r}"
    )
    return "\n".join(lines)


def read_records(path: Path) -> List[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def follow(path: Path, poll: float = 0.2) -> Iterator[dict]:
    """tail -f the jsonl. Ctrl-C to stop."""
    with path.open("r", encoding="utf-8") as fh:
        fh.seek(0, 2)
        while True:
            line = fh.readline()
            if not line:
                time.sleep(poll)
                continue
            line = line.strip()
            if line:
                yield json.loads(line)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m echoai.nexus0.view",
        description="Replay echoai/lab/thought.jsonl in the terminal.",
    )
    ap.add_argument("path", help="thought jsonl written by bench --thought")
    ap.add_argument("--fps", type=float, default=10.0, help="frames per second")
    ap.add_argument("--follow", action="store_true", help="tail the log instead")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        sys.stderr.write(f"no such log: {path}\n")
        return 1

    delay = 1.0 / args.fps if args.fps > 0 else 0.0
    layout = initial_layout()
    source = follow(path) if args.follow else iter(read_records(path))
    try:
        for rec in source:
            layout[int(rec["cell"])] = rec["kind"]
            sys.stdout.write(CLEAR + render(rec, layout, color=not args.no_color))
            sys.stdout.write("\n")
            sys.stdout.flush()
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
