#!/usr/bin/env python3
"""NEURAL-VIZ-1 native GUI for the real ECHO-2 agent.

The Tk renderer is an observer.  A worker calls the configured, existing
``Agent.turn`` and publishes immutable snapshots; the renderer never chooses
an action or writes CAM, T or Q.  Tasks are JSON descriptions of Python
factories, so the GUI contains no world layout or scenario policy.

The neural volume has two explicitly different roles:

* WSP -> LIF512 -> Adaptive-LIF128 is the exact CAPACITY-1 monitor.
* Q -> gate -> action is the causal control path used by ``Agent.turn``.

Keeping those labels visible matters: CAPACITY-1 is measured, but it has not
been installed as a replacement policy in NEXUS-0.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

# Keep the file directly executable from echoai/ as well as importable with
# ``python -m``.  The repository root holds navi10_* and the echoai package.
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from echoai.core.qn import Layer256, q8_nearest, simhash16
from echoai.core.wsp import unpack

from echoai.nexus0.capacity1 import LIF512, TemporalHead, signature_for
from echoai.nexus0.encoder import ATOM_ID, ATOM_NAME, CELL_ATOMS, compact
from echoai.nexus0.env import KIND_NAME
from echoai.nexus0.sleep2 import consolidate
from echoai.nexus0.thought import ACTION_NAME


ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "viz_tasks"
LAB = ROOT / "lab"
CORTEX_LOG = LAB / "neural_viz_cortex.jsonl"
THOUGHT_LOG = LAB / "neural_viz_native.jsonl"


class TaskError(ValueError):
    pass


def _symbol(name: str):
    if not isinstance(name, str) or ":" not in name:
        raise TaskError("factory must be 'module:symbol'")
    module_name, symbol_name = name.split(":", 1)
    value = importlib.import_module(module_name)
    for part in symbol_name.split("."):
        value = getattr(value, part)
    if not callable(value):
        raise TaskError(f"factory is not callable: {name}")
    return value


def _materialise(value: Any, context: Optional[dict] = None) -> Any:
    """Build nested JSON factory values; no scenario names are interpreted."""
    context = context or {}
    if isinstance(value, str) and value.startswith("$"):
        key = value[1:]
        if key not in context:
            raise TaskError(f"unknown runtime value: {value}")
        return context[key]
    if isinstance(value, list):
        return [_materialise(v, context) for v in value]
    if not isinstance(value, dict):
        return value
    if "factory" not in value:
        return {k: _materialise(v, context) for k, v in value.items()}
    fn = _symbol(value["factory"])
    args = [_materialise(v, context) for v in value.get("args", [])]
    kwargs = {k: _materialise(v, context)
              for k, v in value.get("kwargs", {}).items()}
    return fn(*args, **kwargs)


@dataclass(frozen=True)
class TaskSpec:
    path: Path
    ident: str
    title: str
    description: str
    agent: dict
    greedy: bool
    ticks_per_second: int
    sleep_every: int
    child: Optional[dict]
    environment: Dict[str, str]

    @classmethod
    def load(cls, path: Path | str) -> "TaskSpec":
        source = Path(path).expanduser().resolve()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskError(f"cannot read task {source}: {exc}") from exc
        required = ("id", "title", "agent")
        if any(key not in raw for key in required):
            raise TaskError("task needs id, title and agent")
        if not isinstance(raw["agent"], dict) or "factory" not in raw["agent"]:
            raise TaskError("task agent needs a factory")
        rate = int(raw.get("ticks_per_second", 12))
        sleep_every = int(raw.get("sleep_every", 128))
        if rate < 1 or rate > 500 or sleep_every < 0:
            raise TaskError("invalid task timing")
        child = raw.get("child")
        if child is not None:
            if not isinstance(child, dict) or "factory" not in child:
                raise TaskError("child needs a factory")
            if int(child.get("every_deaths", 0)) <= 0:
                raise TaskError("child.every_deaths must be positive")
        environment = raw.get("environment", {})
        if not isinstance(environment, dict) or not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in environment.items()):
            raise TaskError("environment must map strings to strings")
        return cls(source, str(raw["id"]), str(raw["title"]),
                   str(raw.get("description", "")), raw["agent"],
                   bool(raw.get("greedy", False)), rate, sleep_every, child,
                   environment)

    def make_agent(self):
        agent = _materialise(self.agent)
        if not callable(getattr(agent, "turn", None)):
            raise TaskError("agent factory did not return an Agent-compatible object")
        return agent

    def make_child(self, parent):
        if self.child is None:
            return None
        return _materialise(self.child, {"agent": parent})


def discover_tasks(directory: Path = TASK_DIR) -> list[TaskSpec]:
    tasks = []
    for path in sorted(directory.glob("*.json")):
        try:
            tasks.append(TaskSpec.load(path))
        except TaskError:
            continue
    return tasks


def _occupied(agent) -> int:
    return int(getattr(agent.cam, "used",
                       sum(1 for slot in agent.cam.slot if slot.occupied)))


def _lif512(wsp: bytes) -> tuple[list[int], list[int], int]:
    """Two fresh imported LIF banks, driven by the current WSP vertex."""
    vertex = simhash16(wsp)
    hi, lo = (vertex >> 8) & 0xFF, vertex & 0xFF
    left = Layer256().run(hi, q8_nearest(hi))
    right = Layer256().run(lo, q8_nearest(lo))
    return list(left.counts), list(right.counts), vertex


def _tail_json(path: Path) -> Optional[dict]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - 65536))
            lines = handle.read().decode("utf-8", "replace").splitlines()
        for line in reversed(lines):
            if line.strip():
                value = json.loads(line)
                return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        pass
    return None


class RuntimeEngine:
    """Run one configured real agent without ever blocking Tk's event loop."""

    def __init__(self, spec: TaskSpec, ticks_per_second: Optional[int] = None,
                 thought_log: Path = THOUGHT_LOG,
                 cortex_log: Path = CORTEX_LOG):
        self.spec = spec
        for key, value in spec.environment.items():
            os.environ[key] = value.replace("${ROOT}", str(ROOT))
        self.agent = spec.make_agent()
        self.thought_log = Path(thought_log)
        self.cortex_log = Path(cortex_log)
        if bool(getattr(self.agent, "cortex_enabled", False)):
            self.agent.cortex_log = str(self.cortex_log)
        self.agent.thought_log = str(self.thought_log)
        LAB.mkdir(parents=True, exist_ok=True)
        self.thought_log.parent.mkdir(parents=True, exist_ok=True)
        self.thought_log.unlink(missing_ok=True)
        self.rate = int(ticks_per_second or spec.ticks_per_second)
        self.out: queue.Queue = queue.Queue(maxsize=3)
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self._step_lock = threading.Lock()
        self._steps = 0
        self.thread: Optional[threading.Thread] = None
        self.turn = 0
        self.generation = 0
        self.total_deaths = 0
        self.rules_size = 0
        self.rules_report: Dict[str, int] = {}
        self.head = TemporalHead(adapt_gain=8, memory_ticks=16)
        self.events: deque[str] = deque(maxlen=16)
        self.step_started = 0.0
        self.last_error = ""

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, daemon=True,
                                       name=f"echo2-{self.spec.ident}")
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_event.clear()
        else:
            self.pause_event.set()

    def step_once(self) -> None:
        with self._step_lock:
            self._steps += 1

    def set_rate(self, value: int) -> None:
        self.rate = max(1, min(500, int(value)))

    def _may_step(self) -> bool:
        if self.pause_event.is_set():
            return True
        with self._step_lock:
            if self._steps:
                self._steps -= 1
                return True
        return False

    def _publish(self, row: dict) -> None:
        while True:
            try:
                self.out.put_nowait(row)
                return
            except queue.Full:
                try:
                    self.out.get_nowait()
                except queue.Empty:
                    return

    def status(self) -> tuple[bool, float, str]:
        started = self.step_started
        return (bool(started), 0.0 if not started else time.monotonic() - started,
                self.last_error)

    def _lifecycle(self) -> None:
        if not bool(getattr(self.agent, "episode_terminal", False)):
            return
        self.total_deaths += 1
        cause = getattr(getattr(self.agent, "env", None), "last_cause", "")
        self.events.appendleft(f"MUERTE {self.total_deaths} {cause}".strip())
        child_every = (0 if self.spec.child is None else
                       int(self.spec.child.get("every_deaths", 0)))
        if child_every and self.total_deaths % child_every == 0:
            old = self.agent
            self.agent = self.spec.make_child(old)
            self.agent.thought_log = str(self.thought_log)
            self.generation += 1
            inherited = getattr(self.agent, "evidence_budget",
                                getattr(self.agent.q, "inherited_b", 0))
            self.events.appendleft(
                f"NACIMIENTO G{self.generation}: b={inherited}; CAM/Q/T nuevas")
            return
        respawn = getattr(self.agent, "respawn", None)
        if callable(respawn):
            respawn()
            self.events.appendleft("RESPAWN: memoria del individuo conservada")

    def _run(self) -> None:
        self.events.appendleft(f"TAREA {self.spec.ident} cargada")
        try:
            while not self.stop_event.is_set():
                if not self._may_step():
                    time.sleep(0.01)
                    continue
                begin = time.monotonic()
                self._tick()
                elapsed = time.monotonic() - begin
                delay = (1.0 / max(1, self.rate)) - elapsed
                if delay > 0:
                    self.stop_event.wait(delay)
        except Exception as exc:  # visible failure; the GUI must stay alive
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.events.appendleft("ERROR " + self.last_error)

    def _tick(self) -> None:
        self._lifecycle()
        agent = self.agent
        cell = agent.env.cell()
        wsp = agent.observation(cell)
        slot_before = agent.cam.get(wsp)
        q_before = ([0] * agent.n_actions if slot_before < 0
                    else list(agent.q.row(slot_before)))
        metrics_before = agent.metrics.as_dict()
        cortex_before = agent.metrics.cortex_calls
        self.step_started = time.monotonic()
        action = agent.turn(self.turn, greedy=self.spec.greedy)
        self.step_started = 0.0
        thought_row = _tail_json(self.thought_log)
        reward = int(getattr(agent, "last_reward",
                             getattr(agent.env, "last_reward", 0)))
        slot = agent.cam.get(wsp)
        q_row = ([0] * agent.n_actions if slot < 0 else list(agent.q.row(slot)))
        q_delta = (0 if slot < 0 or action >= len(q_row) else
                   q_row[action] - (q_before[action] if action < len(q_before) else 0))
        lif_a, lif_b, vertex = _lif512(wsp)
        feature = signature_for(wsp, LIF512)
        self.head.step(feature, self.turn)
        if self.spec.sleep_every and self.turn and self.turn % self.spec.sleep_every == 0:
            rules, report = consolidate(agent)
            self.rules_size = rules.size
            self.rules_report = report
            self.events.appendleft(
                f"SLEEP-2: {rules.size} reglas / {report['source_rows']} filas")
        pattern = getattr(agent, "pattern_memory", None)
        metrics = agent.metrics.as_dict()
        new_cortex = agent.metrics.cortex_calls - cortex_before
        if new_cortex:
            self.events.appendleft(f"CÓRTEX: {new_cortex} llamada(s), propuesta "
                                   f"{agent.last_cortex_action}")
        if q_delta:
            self.events.appendleft(f"APRENDE: Q[{slot},{action}] {q_delta:+d}")
        decoded = unpack(wsp)
        kind_name = (str(thought_row.get("kind")) if thought_row else
                     (KIND_NAME[cell.kind] if isinstance(cell.kind, int)
                      and 0 <= cell.kind < len(KIND_NAME) else str(cell.kind)))
        row = {
            "task": self.spec.title, "task_id": self.spec.ident,
            "description": self.spec.description, "turn": self.turn,
            "generation": self.generation, "deaths": self.total_deaths,
            "life": int(getattr(agent, "life_id", 0)),
            "life_turn": int(getattr(agent, "life_turns", 0)),
            "terminal": bool(getattr(agent, "episode_terminal", False)),
            "cell": int(cell.index), "kind": kind_name,
            "pose": [getattr(cell, key, None) for key in ("x", "y", "z", "heading")],
            "wsp": compact(wsp), "wsp_bytes": list(wsp), "vertex": vertex,
            "wsp_decoded": decoded,
            "lif_a": lif_a, "lif_b": lif_b,
            "alif_spikes": self.head.spikes, "alif_adaptation": list(self.head.a),
            "alif_spike_count": self.head.spike_count,
            "action": int(action), "action_name": ACTION_NAME[action],
            "proposed": agent.last_proposed_action,
            "gate": agent.last_gate_decision, "explore": bool(agent.last_explore),
            "reward": reward, "q": q_row, "q_delta": q_delta,
            "slot": slot, "cam_used": _occupied(agent),
            "cam_destroyed": int(agent.cam.destroyed),
            "t_pred": None if slot < 0 else agent.t.predict(slot, action),
            "t_known": sum(sum(int(n > 0) for n in r) for r in agent.t.n),
            "t_conflicts": int(agent.t.conflicts),
            "pattern": None if pattern is None else {
                "size": int(pattern.size), "capacity": int(pattern.capacity),
                "observations": int(pattern.observations),
                "conflicts": int(pattern.conflicts), "dropped": int(pattern.dropped)},
            "sleep_rules": self.rules_size, "sleep_report": self.rules_report,
            "H": getattr(agent, "H", None),
            "temperature": getattr(agent, "temperature", None),
            "evidence_budget": int(getattr(agent, "evidence_budget", 0)),
            "cortex_enabled": bool(getattr(agent, "cortex_enabled", False)),
            "cortex_calls": int(agent.metrics.cortex_calls),
            "cortex_action": agent.last_cortex_action,
            "attend_on": bool(agent.last_attend[0]),
            "attend_reason": int(agent.last_attend[1]),
            "attend_reason_name": (str(thought_row.get("reason_name"))
                                   if thought_row else str(agent.last_attend[1])),
            "cortex_log": _tail_json(self.cortex_log),
            "thought": thought_row,
            "metrics": metrics, "metrics_before": metrics_before,
            "events": list(self.events), "monotonic": time.monotonic(),
        }
        self._publish(row)
        self.turn += 1


@dataclass
class GraphNode:
    layer: str
    index: int
    xyz: tuple[float, float, float]
    item: int = 0


class NetworkCanvas:
    """A dependency-free orbitable projection of ECHO-2's measured layers."""

    COLORS = {
        "bg": "#07101d", "edge": "#17304a", "dim": "#1d3850",
        "input": "#39d9ff", "lif": "#8b7bff", "alif": "#ff62c0",
        "action": "#ffd166", "gate": "#5ff29d", "text": "#b8cbe0",
    }

    def __init__(self, tk, parent):
        self.tk = tk
        self.canvas = tk.Canvas(parent, background=self.COLORS["bg"],
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.nodes: list[GraphNode] = []
        self.edges: list[tuple[int, int, int]] = []
        self.yaw, self.pitch, self.zoom = -0.35, -0.12, 1.0
        self.drag = None
        self.last_size = (0, 0)
        self._build()
        self.canvas.bind("<Configure>", self._configure)
        self.canvas.bind("<ButtonPress-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._move)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda _e: self._zoom(1.08))
        self.canvas.bind("<Button-5>", lambda _e: self._zoom(0.92))

    def _grid(self, layer: str, x: float, count: int, rows: int) -> list[int]:
        cols = math.ceil(count / rows)
        ids = []
        for i in range(count):
            r, c = divmod(i, cols)
            y = (c - (cols - 1) / 2) * (3.8 / max(1, cols - 1))
            z = (r - (rows - 1) / 2) * (3.8 / max(1, rows - 1))
            ids.append(len(self.nodes))
            self.nodes.append(GraphNode(layer, i, (x, y, z)))
        return ids

    def _build(self) -> None:
        self.groups = {
            "input": self._grid("input", -5.0, 16, 4),
            "lif_a": self._grid("lif_a", -2.6, 256, 16),
            "lif_b": self._grid("lif_b", -0.2, 256, 16),
            "alif": self._grid("alif", 2.2, 128, 8),
            "action": self._grid("action", 4.3, 3, 3),
            "gate": self._grid("gate", 5.6, 1, 1),
        }
        links: list[tuple[int, int]] = []
        for i, source in enumerate(self.groups["input"]):
            for j in range(i, 256, 16):
                links.append((source, self.groups["lif_a"][j]))
        for i, source in enumerate(self.groups["lif_a"]):
            links.append((source, self.groups["lif_b"][i]))
            links.append((source, self.groups["lif_b"][(i * 37 + 11) % 256]))
        for i, source in enumerate(self.groups["lif_b"]):
            links.append((source, self.groups["alif"][i % 128]))
        # CAPACITY-1 ends at the adaptive head.  It is intentionally not
        # wired to Q: the current Agent still obtains its row through the
        # WSP/CAM lookup.  Three sparse links show that real lookup path
        # without drawing the 4096-row table as fake neurons.
        for i, target in enumerate(self.groups["action"]):
            links.append((self.groups["input"][i * 5], target))
        for source in self.groups["action"]:
            links.append((source, self.groups["gate"][0]))
        for a, b in links:
            item = self.canvas.create_line(0, 0, 0, 0, fill=self.COLORS["edge"], width=1)
            self.edges.append((a, b, item))
        for node in self.nodes:
            node.item = self.canvas.create_oval(0, 0, 1, 1, fill=self.COLORS["dim"],
                                                outline="")
        self.labels = {}
        for key, text_value in (("input", "WSP 16 B"), ("lif_a", "LIF 256 · HI"),
                                ("lif_b", "LIF 256 · LO"),
                                ("alif", "Adaptive-LIF 128 · monitor"),
                                ("action", "CAM → Q · 3 acciones"), ("gate", "GATE")):
            self.labels[key] = self.canvas.create_text(
                0, 0, text=text_value, fill=self.COLORS["text"],
                font=("TkDefaultFont", 9, "bold"))
        self.note = self.canvas.create_text(
            12, 12, anchor="nw", fill="#7890a8", font=("TkDefaultFont", 9),
            text="arrastra para orbitar · rueda para zoom · LIF/ALIF = monitor CAPACITY-1")

    def _project(self, xyz: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, z = xyz
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        xx, yy = x * cy - y * sy, x * sy + y * cy
        zz, yy = z * cp - yy * sp, z * sp + yy * cp
        depth = max(5.0, 15.0 + yy)
        scale = self.zoom * min(max(self.last_size[0], 400) / 13.5,
                                max(self.last_size[1], 300) / 7.2) * 15.0 / depth
        return (self.last_size[0] / 2 + xx * scale,
                self.last_size[1] / 2 + zz * scale, depth)

    def redraw(self) -> None:
        if not self.last_size[0]:
            return
        projected = [self._project(node.xyz) for node in self.nodes]
        for a, b, item in self.edges:
            ax, ay, _ = projected[a]
            bx, by, _ = projected[b]
            self.canvas.coords(item, ax, ay, bx, by)
        for node, (x, y, depth) in zip(self.nodes, projected):
            radius = max(1.4, 3.6 * self.zoom * 15.0 / depth)
            if node.layer in ("input", "action", "gate"):
                radius *= 1.8
            self.canvas.coords(node.item, x - radius, y - radius, x + radius, y + radius)
        for key, item in self.labels.items():
            group = self.groups[key]
            xs = [projected[i][0] for i in group]
            ys = [projected[i][1] for i in group]
            self.canvas.coords(item, sum(xs) / len(xs), min(ys) - 20)
        self.canvas.tag_raise(self.note)

    @staticmethod
    def _level(value: int, peak: int) -> float:
        return 0.0 if peak <= 0 else max(0.0, min(1.0, value / peak))

    @staticmethod
    def _mix(low: str, high: str, level: float) -> str:
        def rgb(value: str) -> tuple[int, int, int]:
            return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
        a, b = rgb(low), rgb(high)
        return "#" + "".join(f"{round(x + (y - x) * level):02x}" for x, y in zip(a, b))

    def activity(self, row: dict) -> None:
        values: dict[str, list[float]] = {}
        values["input"] = [v / 255.0 for v in row["wsp_bytes"]]
        for key in ("lif_a", "lif_b"):
            raw = row[key]
            peak = max(raw or [1])
            values[key] = [self._level(v, peak) for v in raw]
        values["alif"] = [1.0 if (row["alif_spikes"] >> i) & 1 else
                          min(0.55, row["alif_adaptation"][i] / 127.0)
                          for i in range(128)]
        q = row["q"]
        values["action"] = [1.0 if i == row["action"] else
                            (abs(q[i]) / 127.0 if i < len(q) else 0.0)
                            for i in range(3)]
        values["gate"] = [1.0]
        high = {"input": self.COLORS["input"], "lif_a": self.COLORS["lif"],
                "lif_b": self.COLORS["lif"], "alif": self.COLORS["alif"],
                "action": self.COLORS["action"], "gate": self.COLORS["gate"]}
        for key, group in self.groups.items():
            for node_id, level in zip(group, values[key]):
                self.canvas.itemconfigure(
                    self.nodes[node_id].item,
                    fill=self._mix(self.COLORS["dim"], high[key], level))

    def _configure(self, event) -> None:
        self.last_size = (event.width, event.height)
        self.redraw()

    def _down(self, event) -> None:
        self.drag = (event.x, event.y, self.yaw, self.pitch)

    def _move(self, event) -> None:
        if self.drag:
            x, y, yaw, pitch = self.drag
            self.yaw = yaw + (event.x - x) * 0.008
            self.pitch = max(-1.3, min(1.3, pitch + (event.y - y) * 0.008))
            self.redraw()

    def _zoom(self, factor: float) -> None:
        self.zoom = max(0.55, min(2.2, self.zoom * factor))
        self.redraw()

    def _wheel(self, event) -> None:
        self._zoom(1.08 if event.delta > 0 else 0.92)


class DroneWorldView:
    """VTK/OpenGL view driven only by poses emitted by the selected task.

    The coordinate frame and vehicle mesh are presentation.  Positions,
    headings, visited voxels and kinds always come from the live Agent; no
    wall, route or reward is reconstructed in this class.
    """

    def __init__(self, tk, parent):
        self.tk = tk
        self.available = False
        self.trail: deque[tuple[float, float, float]] = deque(maxlen=512)
        self.visited: dict[tuple[int, int, int], Any] = {}
        self.status_var = tk.StringVar(value="Inicializando motor VTK/OpenGL…")
        bar = tk.Frame(parent, bg="#07101d")
        bar.pack(fill="x")
        tk.Label(bar, textvariable=self.status_var, bg="#07101d", fg="#70ddff",
                 padx=12, pady=8, anchor="w",
                 font=("TkDefaultFont", 10, "bold")).pack(fill="x")
        try:
            import vtk
            from PIL import Image, ImageTk
            from vtkmodules.util.numpy_support import vtk_to_numpy
            self.vtk = vtk
            self.Image, self.ImageTk, self.vtk_to_numpy = Image, ImageTk, vtk_to_numpy
            self.image_label = tk.Label(parent, bg="#07101d", bd=0,
                                        cursor="fleur")
            self.image_label.pack(fill="both", expand=True)
            self.window = vtk.vtkRenderWindow()
            self.window.SetOffScreenRendering(1)
            self.window.SetSize(960, 620)
            self.window.SetMultiSamples(0)
            self.renderer = vtk.vtkRenderer()
            self.renderer.SetBackground(0.027, 0.063, 0.114)
            self.renderer.SetBackground2(0.055, 0.13, 0.20)
            self.renderer.GradientBackgroundOn()
            self.window.AddRenderer(self.renderer)
            self._scene()
            self.renderer.ResetCamera()
            camera = self.renderer.GetActiveCamera()
            camera.SetPosition(8.5, -10.5, 7.5)
            camera.SetFocalPoint(0, 0, 0)
            camera.SetViewUp(0, 0, 1)
            self.renderer.ResetCameraClippingRange()
            self.capture = vtk.vtkWindowToImageFilter()
            self.capture.SetInput(self.window)
            self.capture.SetInputBufferTypeToRGB()
            self.capture.ReadFrontBufferOff()
            self.last_render = 0.0
            self.drag = None
            self.image_label.bind("<ButtonPress-1>", self._down)
            self.image_label.bind("<B1-Motion>", self._move)
            self.image_label.bind("<MouseWheel>", self._wheel)
            self.image_label.bind("<Button-4>", lambda _e: self._dolly(1.12))
            self.image_label.bind("<Button-5>", lambda _e: self._dolly(0.89))
            self.available = True
            self._render(force=True)
            capabilities = str(self.window.ReportCapabilities())
            software = any(word in capabilities.lower() for word in ("llvmpipe", "softpipe"))
            mode = "OpenGL software" if software else "OpenGL GPU"
            renderer_name = ""
            for line in capabilities.splitlines():
                if "opengl renderer string" in line.lower():
                    renderer_name = line.split(":", 1)[-1].strip()
                    break
            self.backend_label = (
                f"VTK · {mode} · {(renderer_name or self.window.GetClassName())[:72]} · arrastra/rueda")
            self.status_var.set(self.backend_label)
        except Exception as exc:
            tk.Label(parent, text=f"VTK/OpenGL no disponible: {exc}",
                     bg="#07101d", fg="#ff829f", padx=20, pady=30).pack(fill="both", expand=True)
            self.status_var.set("Motor 3D no disponible")

    def _render(self, force: bool = False) -> None:
        if not self.available:
            return
        now = time.monotonic()
        if not force and now - self.last_render < 1.0 / 15.0:
            return
        self.last_render = now
        self.window.Render()
        self.capture.Modified()
        self.capture.Update()
        output = self.capture.GetOutput()
        width, height, _ = output.GetDimensions()
        data = self.vtk_to_numpy(output.GetPointData().GetScalars())
        data = data.reshape(height, width, 3)[::-1]
        image = self.Image.fromarray(data)
        box_w = max(320, self.image_label.winfo_width())
        box_h = max(240, self.image_label.winfo_height())
        image.thumbnail((box_w, box_h), self.Image.Resampling.BILINEAR)
        self.photo = self.ImageTk.PhotoImage(image=image)
        self.image_label.configure(image=self.photo)

    def _down(self, event) -> None:
        self.drag = (event.x, event.y)

    def _move(self, event) -> None:
        if not self.drag or not self.available:
            return
        x, y = self.drag
        camera = self.renderer.GetActiveCamera()
        camera.Azimuth((x - event.x) * 0.35)
        camera.Elevation((event.y - y) * 0.35)
        camera.OrthogonalizeViewUp()
        self.drag = (event.x, event.y)
        self.renderer.ResetCameraClippingRange()
        self._render(force=True)

    def _dolly(self, factor: float) -> None:
        if not self.available:
            return
        self.renderer.GetActiveCamera().Dolly(factor)
        self.renderer.ResetCameraClippingRange()
        self._render(force=True)

    def _wheel(self, event) -> None:
        self._dolly(1.12 if event.delta > 0 else 0.89)

    def _actor(self, source, color, opacity: float = 1.0):
        vtk = self.vtk
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(opacity)
        return actor

    def _scene(self) -> None:
        vtk = self.vtk
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(2.0, 2.0, 2.0)
        axes.SetShaftTypeToCylinder()
        axes.SetPosition(-2.5, -2.5, -2.5)
        self.renderer.AddActor(axes)

        cube = vtk.vtkCubeSource()
        cube.SetXLength(5.2)
        cube.SetYLength(5.2)
        cube.SetZLength(5.2)
        frame = self._actor(cube, (0.16, 0.42, 0.62), 0.13)
        frame.GetProperty().SetRepresentationToWireframe()
        frame.GetProperty().SetLineWidth(1.2)
        self.renderer.AddActor(frame)

        plane = vtk.vtkPlaneSource()
        plane.SetOrigin(-3.5, -3.5, -2.65)
        plane.SetPoint1(3.5, -3.5, -2.65)
        plane.SetPoint2(-3.5, 3.5, -2.65)
        plane.SetXResolution(14)
        plane.SetYResolution(14)
        grid = self._actor(plane, (0.10, 0.28, 0.38), 0.32)
        grid.GetProperty().SetRepresentationToWireframe()
        self.renderer.AddActor(grid)

        self.drone = vtk.vtkAssembly()
        body = vtk.vtkSphereSource()
        body.SetRadius(0.28)
        body.SetThetaResolution(24)
        body.SetPhiResolution(16)
        self.drone.AddPart(self._actor(body, (0.18, 0.78, 0.96)))
        for angle in (45, 135):
            arm = vtk.vtkCubeSource()
            arm.SetXLength(1.45)
            arm.SetYLength(0.075)
            arm.SetZLength(0.06)
            aa = self._actor(arm, (0.60, 0.70, 0.82))
            aa.RotateZ(angle)
            self.drone.AddPart(aa)
        self.rotors = []
        for x, y in ((0.5, 0.5), (-0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)):
            rotor = vtk.vtkCylinderSource()
            rotor.SetRadius(0.21)
            rotor.SetHeight(0.025)
            rotor.SetResolution(24)
            aa = self._actor(rotor, (1.0, 0.38, 0.72), 0.9)
            aa.SetPosition(x, y, 0.04)
            aa.RotateX(90)
            self.drone.AddPart(aa)
            self.rotors.append(aa)
        nose = vtk.vtkConeSource()
        nose.SetDirection(1, 0, 0)
        nose.SetHeight(0.48)
        nose.SetRadius(0.14)
        nose.SetCenter(0.42, 0, 0)
        nose.SetResolution(20)
        self.drone.AddPart(self._actor(nose, (1.0, 0.80, 0.25)))
        self.drone.SetScale(1.45)
        self.renderer.AddActor(self.drone)

        self.trail_points = vtk.vtkPoints()
        self.trail_lines = vtk.vtkCellArray()
        self.trail_poly = vtk.vtkPolyData()
        self.trail_poly.SetPoints(self.trail_points)
        self.trail_poly.SetLines(self.trail_lines)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self.trail_poly)
        self.trail_actor = vtk.vtkActor()
        self.trail_actor.SetMapper(mapper)
        self.trail_actor.GetProperty().SetColor(0.25, 0.95, 0.70)
        self.trail_actor.GetProperty().SetLineWidth(3)
        self.renderer.AddActor(self.trail_actor)

        self.overlay = vtk.vtkTextActor()
        self.overlay.SetPosition(16, 18)
        self.overlay.GetTextProperty().SetFontSize(18)
        self.overlay.GetTextProperty().SetColor(0.75, 0.88, 0.98)
        self.renderer.AddViewProp(self.overlay)

    @staticmethod
    def _point(pose: Sequence[Optional[int]]) -> Optional[tuple[float, float, float]]:
        if len(pose) < 3 or any(v is None for v in pose[:3]):
            return None
        return tuple((float(v) - 1.0) * 2.0 for v in pose[:3])

    def _mark(self, xyz: tuple[int, int, int], point, kind: str) -> None:
        if xyz in self.visited:
            return
        vtk = self.vtk
        source = vtk.vtkSphereSource()
        source.SetRadius(0.095 if kind != "GOAL" else 0.18)
        source.SetThetaResolution(12)
        source.SetPhiResolution(8)
        colors = {"GOAL": (0.25, 1.0, 0.45), "THREAT": (1.0, 0.20, 0.25),
                  "NOVEL": (1.0, 0.75, 0.18), "OBJECT": (0.4, 0.7, 1.0)}
        actor = self._actor(source, colors.get(kind, (0.25, 0.48, 0.66)), 0.85)
        actor.SetPosition(*point)
        self.renderer.AddActor(actor)
        self.visited[xyz] = actor

    def update(self, row: dict, render: bool = True) -> None:
        if not self.available:
            return
        point = self._point(row["pose"])
        if point is None:
            self.drone.SetVisibility(False)
            self.overlay.SetInput(
                f"{row['task']}\nSin pose x/y/z en esta tarea\nEl motor no inventa coordenadas")
            if render:
                self._render()
            return
        self.drone.SetVisibility(True)
        self.drone.SetPosition(*point)
        heading = row["pose"][3]
        orientations = ((0, 0, 0), (0, 0, 90), (0, -90, 0),
                        (0, 0, 180), (0, 0, -90), (0, 90, 0))
        if isinstance(heading, int) and 0 <= heading < len(orientations):
            self.drone.SetOrientation(*orientations[heading])
        for rotor in self.rotors:
            rotor.RotateY(37)
        if not self.trail or self.trail[-1] != point:
            self.trail.append(point)
        self.trail_points.Reset()
        self.trail_lines.Reset()
        for p in self.trail:
            self.trail_points.InsertNextPoint(*p)
        if len(self.trail) > 1:
            line = self.vtk.vtkPolyLine()
            line.GetPointIds().SetNumberOfIds(len(self.trail))
            for i in range(len(self.trail)):
                line.GetPointIds().SetId(i, i)
            self.trail_lines.InsertNextCell(line)
        self.trail_points.Modified()
        self.trail_lines.Modified()
        self.trail_poly.Modified()
        xyz = tuple(int(v) for v in row["pose"][:3])
        self._mark(xyz, point, row["kind"])
        self.overlay.SetInput(
            f"DRON AUTÓNOMO · G{row['generation']} · t={row['turn']}\n"
            f"pose={tuple(row['pose'])}  cell={row['cell']}  {row['kind']}\n"
            f"acción={row['action_name']}  reward={row['reward']:+d}  "
            f"visitados={len(self.visited)}")
        self.renderer.ResetCameraClippingRange()
        if render:
            self._render()

    def reset(self) -> None:
        self.trail.clear()
        if not self.available:
            return
        for actor in self.visited.values():
            self.renderer.RemoveActor(actor)
        self.visited.clear()
        self.trail_points.Reset()
        self.trail_lines.Reset()
        self.trail_poly.Modified()
        self.drone.SetPosition(0, 0, 0)
        self.status_var.set(getattr(
            self, "backend_label",
            f"VTK/OpenGL · {self.window.GetClassName()} · mapa observado"))
        self._render(force=True)


class EchoVizApp:
    def __init__(self, initial: Optional[TaskSpec] = None):
        import tkinter as tk
        from tkinter import filedialog, ttk
        self.tk, self.ttk, self.filedialog = tk, ttk, filedialog
        self.root = tk.Tk()
        self.root.title("ECHO-AI · NEURAL-VIZ-1 · GUI-3.5 native")
        self.root.geometry("1500x920")
        self.root.minsize(1100, 700)
        self.root.configure(bg="#07101d")
        self.tasks = discover_tasks()
        self.by_title = {task.title: task for task in self.tasks}
        self.engine: Optional[RuntimeEngine] = None
        self.current: Optional[dict] = None
        self.history: deque[dict] = deque(maxlen=180)
        self._style()
        self._layout()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        chosen = initial or (self.tasks[0] if self.tasks else None)
        if chosen:
            self.task_var.set(chosen.title)
            self.load_task(chosen)
        self.root.after(20, self.poll)

    def _style(self) -> None:
        style = self.ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="#0b1726", foreground="#d9e7f3",
                        fieldbackground="#102238", bordercolor="#203a56")
        style.configure("TButton", padding=6)
        style.configure("Treeview", rowheight=22, font=("TkFixedFont", 9),
                        background="#081321", foreground="#cfdeed",
                        fieldbackground="#081321", borderwidth=0)
        style.configure("Treeview.Heading", font=("TkDefaultFont", 9, "bold"))
        style.map("Treeview", background=[("selected", "#164a62")],
                  foreground=[("selected", "#ffffff")])
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#102238")],
                  selectbackground=[("readonly", "#102238")],
                  selectforeground=[("readonly", "#eaf6ff")],
                  foreground=[("readonly", "#eaf6ff")])

    def _layout(self) -> None:
        tk, ttk = self.tk, self.ttk
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Abrir tarea JSON…", command=self.open_task)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.close)
        menu.add_cascade(label="Archivo", menu=file_menu)
        view_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Ver", menu=view_menu)
        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Ayuda", menu=help_menu)
        self.root.configure(menu=menu)

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        ttk.Label(top, text="ECHO-AI  ·  RED NEURONAL EN VIVO",
                  font=("TkDefaultFont", 16, "bold")).pack(side="left")
        ttk.Label(top, text="GUI-3.5 nativa · sin servidor web",
                  foreground="#6fdcff").pack(side="left", padx=18)
        ttk.Label(top, text="Tarea:").pack(side="left", padx=(30, 5))
        self.task_var = tk.StringVar()
        self.combo = ttk.Combobox(top, textvariable=self.task_var,
                                  values=list(self.by_title), width=34, state="readonly")
        self.combo.pack(side="left")
        ttk.Button(top, text="Ejecutar", command=self.choose_task).pack(side="left", padx=4)
        ttk.Button(top, text="Abrir JSON…", command=self.open_task).pack(side="left")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        neural_tab = self.neural_tab = ttk.Frame(self.notebook)
        world_tab = self.world_tab = ttk.Frame(self.notebook)
        wsp_tab = self.wsp_tab = ttk.Frame(self.notebook)
        guide_tab = self.guide_tab = ttk.Frame(self.notebook)
        self.notebook.add(neural_tab, text="Red neuronal")
        self.notebook.add(world_tab, text="Dron 3D · GPU")
        self.notebook.add(wsp_tab, text="Mapa WSP · 16 bytes")
        self.notebook.add(guide_tab, text="Tutorial")
        for label, tab in (("Red neuronal", neural_tab), ("Dron 3D · GPU", world_tab),
                           ("Mapa WSP", wsp_tab), ("Tutorial", guide_tab)):
            view_menu.add_command(label=label,
                                  command=lambda value=tab: self.notebook.select(value))
        help_menu.add_command(label="Cómo leer la GUI",
                              command=lambda: self.notebook.select(guide_tab))
        help_menu.add_command(label="Formato WSP",
                              command=lambda: self.notebook.select(wsp_tab))

        body = ttk.Panedwindow(neural_tab, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10)
        graph_frame = ttk.Frame(body)
        info_frame = ttk.Frame(body, width=410)
        body.add(graph_frame, weight=4)
        body.add(info_frame, weight=2)
        self.graph = NetworkCanvas(tk, graph_frame)

        controls = ttk.Frame(info_frame, padding=(8, 4))
        controls.pack(fill="x")
        self.pause_button = ttk.Button(controls, text="Pausa", command=self.toggle_pause)
        self.pause_button.pack(side="left")
        ttk.Button(controls, text="Paso", command=self.step_once).pack(side="left", padx=4)
        ttk.Label(controls, text="ticks/s").pack(side="left", padx=(12, 3))
        self.rate_var = tk.IntVar(value=12)
        self.rate = ttk.Scale(controls, from_=1, to=120, variable=self.rate_var,
                              command=self.change_rate)
        self.rate.pack(side="left", fill="x", expand=True)
        self.rate_label = ttk.Label(controls, text="12", width=4)
        self.rate_label.pack(side="left")

        self.status = tk.Label(info_frame, anchor="w", justify="left", bg="#0b1726",
                               fg="#6fdcff", padx=10, pady=8,
                               font=("TkDefaultFont", 10, "bold"))
        self.status.pack(fill="x")
        self.cards = tk.Text(info_frame, bg="#081321", fg="#cfdeed",
                             insertbackground="white", relief="flat", padx=10, pady=8,
                             height=28, wrap="word", font=("TkFixedFont", 10),
                             state="disabled")
        self.cards.pack(fill="both", expand=True)
        self.cards.tag_configure("title", foreground="#70ddff",
                                 font=("TkFixedFont", 10, "bold"))
        self.cards.tag_configure("hot", foreground="#ff6e9f")
        self.cards.tag_configure("good", foreground="#62f3a6")
        self.cards.tag_configure("muted", foreground="#70889f")

        lower = ttk.Frame(neural_tab, padding=10)
        lower.pack(fill="x")
        columns = ("turn", "life", "state", "action", "reward", "dq", "wsp")
        self.diary = ttk.Treeview(lower, columns=columns, show="headings", height=8)
        widths = (70, 70, 90, 90, 70, 60, 650)
        for name, width in zip(columns, widths):
            self.diary.heading(name, text=name.upper())
            self.diary.column(name, width=width, stretch=name == "wsp")
        self.diary.pack(fill="x")
        self.diary.tag_configure("death", background="#4d1730")
        self.diary.tag_configure("learn", background="#123927")
        self.diary.tag_configure("cortex", background="#2f255c")

        self.world_view = DroneWorldView(tk, world_tab)
        self._build_wsp_tab(wsp_tab)
        self._build_guide_tab(guide_tab)
        self.notebook.bind("<<NotebookTabChanged>>", self._tab_changed)

    def _tab_changed(self, _event=None) -> None:
        if self.current is None:
            return
        selected = self.notebook.select()
        if selected == str(self.world_tab):
            self.world_view.update(self.current, render=True)
        elif selected == str(self.neural_tab):
            self.graph.activity(self.current)

    def _build_wsp_tab(self, parent) -> None:
        tk, ttk = self.tk, self.ttk
        header = tk.Label(
            parent, bg="#07101d", fg="#d9e7f3", anchor="w", justify="left",
            padx=14, pady=10, font=("TkDefaultFont", 11, "bold"),
            text=("WSP es una postal binaria de 16 bytes: describe qué percibe el agente. "
                  "No es la acción elegida. Los valores de la izquierda siguen el paquete vivo."))
        header.pack(fill="x")
        split = ttk.Panedwindow(parent, orient="horizontal")
        split.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        left, right = ttk.Frame(split), ttk.Frame(split)
        split.add(left, weight=3)
        split.add(right, weight=2)
        columns = ("byte", "field", "type", "value", "meaning")
        self.wsp_table = ttk.Treeview(left, columns=columns, show="headings", height=16)
        widths = (55, 100, 70, 110, 460)
        for name, width in zip(columns, widths):
            self.wsp_table.heading(name, text=name.upper())
            self.wsp_table.column(name, width=width, stretch=name == "meaning")
        fields = (
            (0, "src", "u8/atom", "sujeto de la percepción"),
            (1, "rel", "u8/atom", "relación percibida; OBSERVAR no significa esperar"),
            (2, "dst", "u8/atom", "objeto o destino semántico"),
            (3, "time", "u8/atom", "tiempo: AHORA, ANTES, DESPUES"),
            (4, "E.V", "int8", "valencia [-100,+100]"),
            (5, "E.A", "int8", "activación/arousal [-100,+100]"),
            (6, "E.D", "int8", "dominancia [-100,+100]"),
            (7, "E.C", "int8", "certeza [-100,+100]"),
            (8, "E.U", "int8", "urgencia [-100,+100]"),
            (9, "E.B", "int8", "estado corporal/térmico [-100,+100]"),
            (10, "flags", "u8 bits", "VERIFY, veto, inhibición y flags ABI"),
            (11, "domain", "u8", "dominio semántico"),
            (12, "generator", "u8", "origen del paquete; echoAI=0x05"),
            (13, "style", "u8", "estilo/canal auxiliar"),
            (14, "slot", "u8", "slot externo del paquete, no CAM[4096]"),
            (15, "seq", "u8", "secuencia/estado local 0..255"),
        )
        self.wsp_rows = []
        for byte, field, typ, meaning in fields:
            item = self.wsp_table.insert("", "end", values=(byte, field, typ, "—", meaning))
            self.wsp_rows.append(item)
        self.wsp_table.pack(fill="both", expand=True)
        self.wsp_current = tk.Label(left, bg="#081321", fg="#70ddff", anchor="w",
                                    justify="left", padx=10, pady=8,
                                    font=("TkFixedFont", 10), text="Esperando el primer WSP…")
        self.wsp_current.pack(fill="x")

        atom_title = tk.Label(right, text="ÁTOMOS SEMÁNTICOS DEFINIDOS",
                              bg="#07101d", fg="#70ddff", padx=8, pady=6,
                              font=("TkDefaultFont", 10, "bold"))
        atom_title.pack(fill="x")
        atoms = tk.Text(right, bg="#081321", fg="#cfdeed", relief="flat",
                        wrap="word", padx=10, pady=8, font=("TkFixedFont", 9))
        atom_lines = [f"{value:02d}  {name}" for name, value in
                      sorted(ATOM_ID.items(), key=lambda item: item[1])]
        atoms.insert("end", "\n".join(atom_lines))
        atoms.insert("end", "\n\n42..47  reservados por el ABI\n48..255  sin nombre semántico")
        atoms.insert("end", "\n\nPERCEPCIÓN DE CELDAS\n")
        for kind, (rel, dst) in sorted(CELL_ATOMS.items()):
            name = KIND_NAME[kind] if 0 <= kind < len(KIND_NAME) else str(kind)
            atoms.insert("end", f"{name:<8}  YO → {ATOM_NAME[rel]} → {ATOM_NAME[dst]}\n")
        atoms.configure(state="disabled")
        atoms.pack(fill="both", expand=True)

    def _build_guide_tab(self, parent) -> None:
        tk = self.tk
        guide = tk.Text(parent, bg="#081321", fg="#cfdeed", relief="flat",
                        padx=28, pady=20, wrap="word", spacing1=2, spacing3=7,
                        font=("TkDefaultFont", 11))
        guide.tag_configure("h1", foreground="#70ddff",
                            font=("TkDefaultFont", 18, "bold"), spacing3=12)
        guide.tag_configure("h2", foreground="#62f3a6",
                            font=("TkDefaultFont", 13, "bold"), spacing1=10)
        path = ROOT / "docs" / "NEURAL-VIZ1-GUIDE.md"
        source = path.read_text(encoding="utf-8") if path.is_file() else "Guía no encontrada."
        for line in source.splitlines():
            if line.startswith("# "):
                guide.insert("end", line[2:] + "\n", "h1")
            elif line.startswith("## "):
                guide.insert("end", line[3:] + "\n", "h2")
            else:
                guide.insert("end", line + "\n")
        guide.configure(state="disabled")
        scroll = tk.Scrollbar(parent, command=guide.yview)
        guide.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        guide.pack(fill="both", expand=True)

    def choose_task(self) -> None:
        spec = self.by_title.get(self.task_var.get())
        if spec:
            self.load_task(spec)

    def open_task(self) -> None:
        path = self.filedialog.askopenfilename(
            title="Tarea ECHO-2", filetypes=(("JSON", "*.json"), ("Todos", "*")))
        if path:
            self.load_task(TaskSpec.load(path))

    def load_task(self, spec: TaskSpec) -> None:
        if self.engine:
            self.engine.stop()
        self.history.clear()
        for child in self.diary.get_children():
            self.diary.delete(child)
        self.world_view.reset()
        self.engine = RuntimeEngine(spec)
        self.rate_var.set(spec.ticks_per_second)
        self.rate_label.configure(text=str(spec.ticks_per_second))
        self.task_var.set(spec.title)
        self.engine.start()

    def toggle_pause(self) -> None:
        if not self.engine:
            return
        paused = self.engine.pause_event.is_set()
        self.engine.set_paused(paused)
        self.pause_button.configure(text="Continuar" if paused else "Pausa")

    def step_once(self) -> None:
        if self.engine:
            self.engine.set_paused(True)
            self.engine.step_once()
            self.pause_button.configure(text="Continuar")

    def change_rate(self, _value=None) -> None:
        value = int(float(self.rate_var.get()))
        self.rate_label.configure(text=str(value))
        if self.engine:
            self.engine.set_rate(value)

    def poll(self) -> None:
        if self.engine:
            latest = None
            while True:
                try:
                    latest = self.engine.out.get_nowait()
                except queue.Empty:
                    break
            if latest:
                self.show(latest)
            busy, elapsed, error = self.engine.status()
            if error:
                self.status.configure(text="ERROR · " + error, fg="#ff6e9f")
            elif busy and elapsed > 0.35:
                mode = "CÓRTEX/LLM" if bool(getattr(self.engine.agent, "cortex_enabled", False)) else "CICLO"
                self.status.configure(text=f"{mode} OCUPADO · {elapsed:5.1f} s · la GUI sigue fluida",
                                      fg="#ffca68")
        self.root.after(20, self.poll)

    def _write_cards(self, row: dict) -> None:
        t = self.cards
        t.configure(state="normal")
        t.delete("1.0", "end")
        def line(title: str, body: str, tag: str = "") -> None:
            t.insert("end", title + "  ", "title")
            t.insert("end", body + "\n", tag)
        line("TAREA", row["task"])
        if row["description"]:
            line("CONTRATO", row["description"], "muted")
        line("TIEMPO", f"turno {row['turn']} · G{row['generation']} · muertes {row['deaths']} · vida {row['life_turn']}")
        line("CUERPO", f"cell {row['cell']} · pose {row['pose']} · H {row['H']} · temperatura {row['temperature']}",
             "hot" if row["terminal"] else "")
        line("WSP", row["wsp"])
        line("LIF 512", f"vertex 0x{row['vertex']:04X} · picos {max(row['lif_a'])}/{max(row['lif_b'])}")
        line("ALIF 128", f"spikes vivos {row['alif_spikes'].bit_count()} · acumulados {row['alif_spike_count']}")
        line("CAM", f"slot {row['slot']} · {row['cam_used']}/4096 · destruidas {row['cam_destroyed']}")
        line("T", f"pred {row['t_pred']} · filas {row['t_known']} · conflictos {row['t_conflicts']}")
        p = row["pattern"]
        line("PATTERN", "OFF en esta tarea" if p is None else
             f"{p['size']}/{p['capacity']} contextos · obs {p['observations']} · conflictos {p['conflicts']}",
             "muted" if p is None else "")
        line("Q", "  ".join(f"{ACTION_NAME[i]}={v:+d}" for i, v in enumerate(row["q"])))
        line("GATE", f"propuesta {row['proposed']} · veredicto {row['gate']} · ejecuta {row['action_name']} · explora {row['explore']}")
        line("APRENDIZAJE", f"reward {row['reward']:+d} · ΔQ elegida {row['q_delta']:+d}",
             "good" if row["q_delta"] else "muted")
        line("SLEEP-2", f"{row['sleep_rules']} reglas consolidadas (lectura periódica)")
        line("GEN-1", f"b heredable {row['evidence_budget']} · generación {row['generation']}")
        line("ATTEND", f"{'DESPIERTA' if row['attend_on'] else 'silencio'} · razón {row['attend_reason_name']}",
             "hot" if row["attend_on"] else "muted")
        line("CÓRTEX", f"{'ON' if row['cortex_enabled'] else 'OFF'} · calls {row['cortex_calls']} · propuesta {row['cortex_action']}",
             "hot" if row["cortex_enabled"] else "muted")
        cortex_row = row["cortex_log"]
        if cortex_row:
            line("LLM ENTRADA", str(cortex_row.get("extract", "")))
            line("LLM SALIDA", str(cortex_row.get("wsp_out", "")), "good")
            line("LLM ATENCIÓN", f"turno {cortex_row.get('turn')} · {cortex_row.get('reason_name')} · slot {cortex_row.get('slot')}")
        line("SEGURIDAD", f"false_facts {row['metrics']['false_facts']} · destroyed {row['metrics']['destroyed']}")
        if row["events"]:
            t.insert("end", "\nEVENTOS REALES\n", "title")
            t.insert("end", "\n".join(row["events"][:7]))
        t.configure(state="disabled")

    def _update_wsp(self, row: dict) -> None:
        p = row["wsp_decoded"]
        e, ext = p["E"], p["ext"]
        raw_values = (p["src"], p["rel"], p["dst"], p["time"],
                      e["V"], e["A"], e["D"], e["C"], e["U"], e["B"],
                      p["flags"], ext["domain"], ext["generator"], ext["style"],
                      ext["slot"], ext["seq"])
        for index, (item, value) in enumerate(zip(self.wsp_rows, raw_values)):
            old = self.wsp_table.item(item, "values")
            shown = (f"{value} · {ATOM_NAME.get(value, '?')}" if index < 4
                     else f"0x{value:02X} · {value}" if index in (10, 11, 12, 13, 14, 15)
                     else str(value))
            self.wsp_table.item(item, values=(*old[:3], shown, old[4]))
        self.wsp_current.configure(
            text=f"ACTUAL  {row['wsp']}\nHEX     {bytes(row['wsp_bytes']).hex()}")

    def show(self, row: dict) -> None:
        self.current = row
        self.history.append(row)
        selected = self.notebook.select()
        if selected == str(self.neural_tab):
            self.graph.activity(row)
        self.world_view.update(row, render=selected == str(self.world_tab))
        self._update_wsp(row)
        self.status.configure(
            text=f"LIVE · {row['task_id']} · turno {row['turn']} · GUI 50 Hz / motor {self.engine.rate if self.engine else 0} ticks/s",
            fg="#6fdcff")
        self._write_cards(row)
        tags = []
        if row["terminal"]:
            tags.append("death")
        elif row["cortex_calls"] > row["metrics_before"].get("cortex_calls", 0):
            tags.append("cortex")
        elif row["q_delta"]:
            tags.append("learn")
        state = "MUERE" if row["terminal"] else "vive"
        self.diary.insert("", "end", values=(row["turn"], f"G{row['generation']}/{row['life_turn']}",
                          state, row["action_name"], f"{row['reward']:+d}",
                          f"{row['q_delta']:+d}", row["wsp"]), tags=tuple(tags))
        children = self.diary.get_children()
        while len(children) > 120:
            self.diary.delete(children[0])
            children = children[1:]
        if children:
            self.diary.see(children[-1])

    def close(self) -> None:
        if self.engine:
            self.engine.stop()
        self.root.destroy()

    def run(self) -> int:
        self.root.mainloop()
        return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="ECHO-2 live native 3-D neural viewer; Ctrl-C or close stops.")
    parser.add_argument("--task", help="path to a declarative task JSON")
    parser.add_argument("--list-tasks", action="store_true")
    args = parser.parse_args(argv)
    if args.list_tasks:
        for task in discover_tasks():
            print(f"{task.ident}\t{task.title}\t{task.path}")
        return 0
    initial = TaskSpec.load(args.task) if args.task else None
    return EchoVizApp(initial).run()


if __name__ == "__main__":
    raise SystemExit(main())
