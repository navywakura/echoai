"""NEURAL-VIZ-1 — live, read-only terminal cockpit for the real ECHO-2 loop.

It runs the normal ``Agent.turn`` loop.  The Q8 raster is a read-only monitor
of the exact WSP that this turn supplied to the agent; it never supplies an
action, edits Q/T/CAM, or opens another event bus.  ``--cortex`` merely enables
the existing optional cortex hook, whose proposal is still shown separately
from the action accepted by the gate.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from echoai.core.qn import Layer256, q8_nearest, simhash16

from echoai.nexus0 import view
from echoai.nexus0.encoder import compact
from echoai.nexus0.loop import Agent
from echoai.nexus0.thought import ACTION_NAME


LAB = Path(__file__).resolve().parents[1] / "lab"
CLEAR = "\x1b[2J\x1b[H"
SHORT_TURNS = 96
DEFAULT_TURNS = 352


def _bar(value: int, width: int = 12) -> str:
    value = max(-127, min(127, int(value)))
    n = abs(value) * width // 127
    return ("-" * n if value < 0 else "+" * n).ljust(width, "·")


def _spoke(wsp: bytes) -> dict:
    vertex = simhash16(wsp)
    stim = (vertex >> 8) & 0xFF
    run = Layer256().run(stim, q8_nearest(stim))
    return {"vertex": vertex, "stim": stim, "winner": run.winner,
            "target_tick": run.first_target_spike, "spikes": run.spikes_total,
            "counts": run.counts}


def _raster(counts: Sequence[int]) -> list[str]:
    peak = max([int(value) for value in counts] or [1])
    rows = []
    for start in range(0, 256, 16):
        cells = []
        for count in counts[start:start + 16]:
            level = int(count) * 4 // max(1, peak)
            cells.append("█" if level >= 3 else "▓" if level == 2
                         else "▒" if level == 1 else "·")
        rows.append("".join(cells))
    return rows


def _cortex_line(path: Path) -> str:
    if not path.is_file():
        return "sin llamadas todavía"
    try:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if line.strip():
                row = json.loads(line)
                return f"{row.get('reason_name')} | {row.get('wsp_in')}  →  {row.get('wsp_out')}"
    except (OSError, ValueError, TypeError):
        pass
    return "registro cortex no legible"


def render(agent: Agent, turn: int, cell, wsp: bytes, action: int,
           spoke: dict, cortex_path: Path) -> str:
    slot = agent.cam.get(wsp)
    q = agent.q.row(slot) if slot >= 0 else [0] * len(ACTION_NAME)
    layout = view.initial_layout()
    layout[cell.index] = cell.kind if isinstance(cell.kind, str) else layout.get(cell.index, "EMPTY")
    action_name = ACTION_NAME[action] if action < len(ACTION_NAME) else str(action)
    h = getattr(agent, "H", None)
    temp = getattr(agent, "temperature", None)
    occupied = sum(1 for row in agent.cam.slot if row.occupied)
    lines = [
        "╔════════════════════ ECHO-AI · NEURAL-VIZ-1 · LIVE ════════════════════╗",
        "║ Loop real: WSP → CAM/T/Q → gate → acción → mundo → aprendizaje       ║",
        "║ El raster Q8 es monitor sensorial; la acción la decide Q+gate.          ║",
        "╚═════════════════════════════════════════════════════════════════════════╝",
        f"TURNO {turn:04d}   celda={cell.index:03d}   acción={action_name:<9} "
        f"recompensa={getattr(agent, 'last_reward', getattr(agent.env, 'last_reward', 0)):+4d}   H={h if h is not None else '—'} "
        f"temperatura={temp if temp is not None else '—'}",
        "",
        "[ PERCEPCIÓN COMPARTIDA ]",
        f"WSP  {compact(wsp)}",
        f"QN   vertex=0x{spoke['vertex']:04X}  stim={spoke['stim']:03d}  "
        f"winner=0x{spoke['winner']:02X}  target_tick={spoke['target_tick']}  "
        f"spikes={spoke['spikes']}  pico_por_neurona={max(spoke['counts'])}",
        "Q8 / 256 LIF  intensidad relativa: █ alta · baja",
        *_raster(spoke["counts"]),
        "",
        "[ MEMORIA Y CONTROL ]",
        f"CAM  slot={slot:04d}  ocupadas={occupied}/4096  destroyed={agent.cam.destroyed}",
        f"T    predicción={agent.t.predict(slot, action) if slot >= 0 else None}  "
        f"surpresas={agent.metrics.surprises}  deltas={agent.metrics.deltas}",
        "Q    " + "  ".join(
            f"{name}:{value:+4d} {_bar(value)}" for name, value in zip(ACTION_NAME, q)),
        f"GATE decisión={agent.last_gate_decision}  propuesta={agent.last_proposed_action}  "
        f"explora={agent.last_explore}",
        "",
        "[ NEOCÓRTEX OPCIONAL ]",
        f"cortex_calls={agent.metrics.cortex_calls}  attend={agent.last_attend}  "
        f"propuesta_consumida={agent.last_cortex_action}",
        "última WSP del córtex: " + (_cortex_line(cortex_path)
                                      if getattr(agent, "cortex_enabled", False)
                                      else "apagado"),
        "",
        f"SEGURIDAD  false_facts={agent.metrics.false_facts}  cortex no escribe CAM/Q/T  "
        "Ctrl-C para detener",
    ]
    return "\n".join(lines)


def live(turns: int, fps: float, cortex: bool, heat: bool, sign: Optional[str]) -> int:
    cortex_path = LAB / "neural_viz_cortex.jsonl"
    if cortex:
        os.environ["NAVI_CORTEX_LOG"] = str(cortex_path)
        cortex_path.unlink(missing_ok=True)
    if heat:
        from echoai.nexus0 import heat1b
        agent = heat1b.new_agent()
        agent.thought_log = str(LAB / "neural_viz_thought.jsonl")
    elif sign:
        from echoai.nexus0.sign import SignEnv
        agent = Agent(cortex=cortex, ask=False, env=SignEnv(sign),
                      thought_log=str(LAB / "neural_viz_thought.jsonl"))
    else:
        agent = Agent(cortex=cortex, thought_log=str(LAB / "neural_viz_thought.jsonl"))
    delay = 1.0 / fps if fps > 0 else 0.0
    try:
        for turn in range(int(turns)):
            if getattr(agent, "episode_terminal", False):
                agent.respawn()
            # This is exactly the WSP `Agent.turn()` will consume this turn.
            cell = agent.env.cell()
            wsp = agent.observation(cell)
            sensory = _spoke(wsp)
            action = agent.turn(turn)
            sys.stdout.write(CLEAR + render(agent, turn, cell, wsp, action, sensory, cortex_path) + "\n")
            sys.stdout.flush()
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Live ECHO-2 neural monitor; Ctrl-C stops.")
    parser.add_argument("--short", action="store_true", help="96 real turns")
    parser.add_argument("--turns", type=int, default=None)
    parser.add_argument("--fps", type=float, default=4.0)
    parser.add_argument("--cortex", action="store_true",
                        help="enable the existing optional cortex hook")
    parser.add_argument("--heat", action="store_true",
                        help="show the real HEAT-1b survival loop (H and temperature)")
    parser.add_argument("--sign", choices=("prize", "trap"),
                        help="run the existing signed world so Qwen has a real extract")
    args = parser.parse_args(argv)
    turns = args.turns if args.turns is not None else (SHORT_TURNS if args.short else DEFAULT_TURNS)
    if turns <= 0 or args.fps < 0:
        parser.error("turns must be positive and fps must be non-negative")
    if args.heat and args.sign:
        parser.error("--heat and --sign are separate real environments")
    return live(turns, args.fps, args.cortex, args.heat, args.sign)


if __name__ == "__main__":
    raise SystemExit(main())
