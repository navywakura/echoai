"""
Watch echoAI think in the terminal.

The scientific program (NEXUS-0 … corridor) is closed. This is the
MVP: one process, one screen, the same thought.jsonl the tests use.
It is a replay of the fast loop, not a picture of a brain.

    PYTHONPATH=. python3 -m echoai.nexus0.demo           # live, 352 turns
    PYTHONPATH=. python3 -m echoai.nexus0.demo --short   # 48 turns, a taste
    PYTHONPATH=. python3 -m echoai.nexus0.demo --replay  # existing log
    PYTHONPATH=. python3 -m echoai.nexus0.demo --fps 8

Ctrl-C stops. Default 5 fps so a human can read a turn.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from echoai.nexus0.constants import BENCH_TURNS
from echoai.nexus0.loop import Agent
from echoai.nexus0 import view

LAB = Path(__file__).resolve().parents[1] / "lab"
DEFAULT_LOG = LAB / "thought.jsonl"
PHASE_F_TURNS = 64
SHORT_TURNS = 48


def _last_record(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if line.strip():
            return json.loads(line)
    raise RuntimeError(f"empty thought log: {path}")


def _paint(rec: dict, layout: dict, color: bool) -> None:
    layout[int(rec["cell"])] = rec["kind"]
    sys.stdout.write(view.CLEAR + view.render(rec, layout, color=color))
    sys.stdout.write("\n")
    sys.stdout.flush()


def live(path: Path, turns: int, fps: float, color: bool) -> int:
    """Run the agent and draw every turn as it happens."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    ag = Agent(thought_log=str(path))
    layout = view.initial_layout()
    delay = (1.0 / fps) if fps > 0 else 0.0
    n = max(1, int(turns))
    extra = 0 if n < BENCH_TURNS else PHASE_F_TURNS
    try:
        for t in range(n):
            ag.turn(t)
            _paint(_last_record(path), layout, color)
            if delay:
                time.sleep(delay)
        if extra:
            ag.env.move_threat(7, 8)
            for t in range(extra):
                ag.turn(n + t)
                _paint(_last_record(path), layout, color)
                if delay:
                    time.sleep(delay)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return 0
    return 0


def replay(path: Path, fps: float, color: bool) -> int:
    argv: List[str] = [str(path), "--fps", str(fps)]
    if not color:
        argv.append("--no-color")
    return view.main(argv)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m echoai.nexus0.demo",
        description="Watch the fast loop think. Cortex off. Ctrl-C to stop.",
    )
    ap.add_argument(
        "--fps", type=float, default=5.0,
        help="frames per second (default 5; 0 = as fast as possible)",
    )
    ap.add_argument(
        "--short", action="store_true",
        help=f"only {SHORT_TURNS} turns (a taste, no phase F)",
    )
    ap.add_argument(
        "--replay", action="store_true",
        help="replay an existing thought.jsonl instead of running live",
    )
    ap.add_argument(
        "--log", default=str(DEFAULT_LOG),
        help="thought jsonl path (default echoai/lab/thought.jsonl)",
    )
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.log)
    color = not args.no_color
    if args.replay:
        if not path.is_file():
            sys.stderr.write(
                f"no such log: {path}\n"
                "run without --replay first, or: "
                "python3 -m echoai.nexus0.bench --thought\n"
            )
            return 1
        return replay(path, args.fps, color)
    turns = SHORT_TURNS if args.short else BENCH_TURNS
    return live(path, turns, args.fps, color)


if __name__ == "__main__":
    sys.exit(main())
