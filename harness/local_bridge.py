"""Private ECHO integration for echo-nexus. NEVER export this file to its public repo.

Only development runs and existing reports are exposed. S6 sources stay frozen.
The public harness receives JSON, not imports, policies, or experiment programs.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
ARC_PYTHON = ROOT / "lab/arc3/ARC-AGI-3-Agents/.venv/bin/python"
OUT = ROOT / "lab/observability/echo-nexus"


def emit(row):
    print(json.dumps(row, ensure_ascii=False, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)), flush=True)


def new_run(name):
    path = OUT / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + name + "-" + uuid.uuid4().hex[:8])
    path.mkdir(parents=True, exist_ok=False)
    return path


def manifest(target):
    from gui4.catalog import CASES
    from gui4 import evidence
    from seed.arc_comparison import prepared, freeze_guard
    prepared()
    freeze_guard()
    target = Path(target).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    reports = target.parent / "reports"
    reports.mkdir(exist_ok=True)
    tests = []
    def test(ident, title, default=False, arc=False):
        tests.append({"id": ident, "title": title, "kind": "development", "default": default,
                      "argv": [str(ARC_PYTHON) if arc else "/usr/bin/python3", str(Path(__file__).resolve()), "run", ident],
                      "cwd": str(ROOT), "timeout": 600})
    test("integrity", "Integridad de las fuentes congeladas", True)
    test("arc-gym", "ECHO v5.7 · ARC3-GYM v3 · semilla de desarrollo 0", True, True)
    test("arc-capabilities", "Objetos, relaciones y composición · 12 tareas sintéticas", False)
    test("unit-observation", "Regresión del visor y del diseño de comparación", True)
    for case in CASES:
        if case.origin == "EVIDENCE":
            path = reports / (case.ident + ".json")
            path.write_text(json.dumps(asdict(evidence.read(case.reader)), ensure_ascii=False, indent=2, default=str))
            tests.append({"id": case.ident, "title": case.title, "kind": "evidence", "report": str(path)})
        elif case.ident == "cortex-propone":
            tests.append({"id": case.ident, "title": case.title, "kind": "sealed", "note":
                          "La demo antigua activa el córtex del núcleo. NEXUS-0 permanece OFF; usa /connect para el neocórtex externo."})
        else:
            test(case.ident, case.title, case.ident == "cuerpo-aprende")
    for ident, title, path in (
        ("s6-status", "S6-B11 · estado del coordinador, solo lectura", "lab/seed/s6b11-20260929/status.json"),
        ("memory-audit", "EGO-MEMORIA-3E · auditoría sellada", "lab/seed/village3-receipts-20260929/audit.json"),
        ("arc-reference", "Referencia ARC-1/2/3 · auditoría histórica", "lab/final/echo45-20260928/audit.json"),
        ("arc-diagnostics", "Diagnóstico sintético previo · comparación de tres brazos", "lab/final/echo45-comparison-prep-20260929/v2/development/summary.json"),
    ):
        tests.append({"id": ident, "title": title, "kind": "evidence", "report": str(ROOT / path)})
    # Complete inventory, but no automatic blanket execution of research tests.
    inventory = reports / "unit-test-inventory.json"
    inventory.write_text(json.dumps({"origin": "INVENTORY", "note": "El inventario no ejecuta ni certifica tests.",
        "files": [str(p.relative_to(ROOT)) for p in sorted((ROOT / "tests").glob("test_*.py"))]}, indent=2))
    tests.append({"id": "unit-inventory", "title": "Inventario completo de pruebas de código", "kind": "evidence", "report": str(inventory)})
    target.write_text(json.dumps({"schema": "echo-nexus-backend-v1", "name": "ECHO-4 / 4.5 · laboratorio local",
                                 "tests": tests}, ensure_ascii=False, indent=2))
    print(json.dumps({"manifest": str(target), "entries": len(tests)}))


def run_live(case):
    from nexus0.neural_viz_gui import RuntimeEngine, TaskSpec
    root = new_run(case.ident)
    spec = TaskSpec.load(ROOT / "viz_tasks" / case.task)
    # Existing tasks default to OFF; reject any descriptor that enables it.
    if spec.environment:
        raise ValueError("No se permiten cambios de entorno en este adaptador")
    engine = RuntimeEngine(spec, thought_log=root / "thought.jsonl", cortex_log=root / "cortex.jsonl")
    if getattr(engine.agent, "cortex_enabled", False):
        raise ValueError("El núcleo debe mantener el córtex desactivado")
    emit({"kind": "start", "origin": "LIVE / desarrollo", "text": case.shows + " Diario: " + str(engine.thought_log)})
    emit({"kind": "progress", "step": 0, "budget": 48})
    for turn in range(48):
        engine._tick()
        row = engine.out.get_nowait()
        row["cell_kind"] = row["kind"]
        row["kind"] = "telemetry"
        mask = row.get("alif_spikes")
        if isinstance(mask, int):
            row["alif_spikes"] = [(mask >> i) & 1 for i in range(128)]
        row["origin"] = "LIVE / ECHO · monitor neuronal medido"
        emit(row)
        emit({"kind": "progress", "step": turn + 1, "budget": 48})
        from echoai.nexus0.body3d import Body3DEnv, FLOOR, BLOCKED, GOAL_XYZ, DIRS
        if isinstance(engine.agent.env, Body3DEnv):
            # Three actual z slices; a viewer projection, never an agent input.
            grid = [[0] * 31 for _ in range(11)]
            pose = tuple(row["pose"][:3])
            cell_world = {}
            for z in range(3):
                for y in range(3):
                    for x in range(3):
                        xyz = (x, y, z)
                        color = 1 if xyz in FLOOR else 5
                        if xyz == GOAL_XYZ:
                            color = 4
                        if engine.agent.env.layout == "block" and xyz == BLOCKED:
                            color = 2
                        if xyz == pose:
                            color = 10
                        for dy in range(2):
                            for dx in range(2):
                                iy, ix = 1 + y * 3 + dy, 1 + z * 10 + x * 3 + dx
                                grid[iy][ix] = color
                                cell_world[f"{ix},{iy}"] = [x,y,z]
            emit({"kind": "frame", "origin": "LIVE / Body3D · z=0,1,2 · blanco=cuerpo", "grid": grid, "observer": {"position": [1+pose[2]*10+pose[0]*3, 1+pose[1]*3],
                  "direction": list(DIRS[row["pose"][3]][:2]), "direction_kind": "mirada real",
                  "world_position": list(pose), "world_direction": list(DIRS[row["pose"][3]]), "cell_world": cell_world}})
        time.sleep(0.06)
    if engine.agent.metrics.cortex_calls:
        raise ValueError("Llamada inesperada al córtex")
    emit({"kind": "progress", "step": 48, "budget": 48,
          "stop_reason": "Ventana de observación de 48 turnos completada"})
    emit({"kind": "result", "text": "48 turnos observados; 0 llamadas LLM. Monitor LIF separado de Q + gate."})


def run_arc():
    from seed import arc3gym as gym
    from echo_arc import runner
    from echo_arc.observe import Journal, observed_play
    gym.VERSION = 3
    root = new_run("arc-gym")
    class VisibleGym:
        def __init__(self):
            self.env = gym.GymEnv(0)
            self.n = 0
        def show(self, obs):
            if obs is not None:
                frame = obs.frame[-1]
                emit({"kind": "frame", "origin": "LIVE / ARC3-GYM · desarrollo · no ARC oficial",
                      "grid": frame.tolist() if hasattr(frame, "tolist") else frame, "turn": self.n})
                self.n += 1
            return obs
        def reset(self):
            return self.show(self.env.reset())
        def step(self, *a, **kw):
            return self.show(self.env.step(*a, **kw))
    journal = Journal(root / "arc-decisions.jsonl")
    original_write = journal.write
    def visible_write(**event):
        original_write(**event)
        # The canonical hashed journal is unchanged. stdout is just a viewer relay.
        emit(dict(event, origin="LIVE / ARC3-GYM · desarrollo"))
    journal.write = visible_write
    try:
        journal.write(kind="start", text="ECHO v5.7 · 120 decisiones · semilla 0 · LLM OFF")
        result = observed_play(VisibleGym(), 120, runner.seed_for("gym-v3-train-0"), journal, agent_name="v5.7", delay=0.015)
    finally:
        journal.close()
    (root / "result.json").write_text(json.dumps(result))
    emit({"kind": "result", "text": f"{result['levels_completed']}/{result['win_levels']} niveles de desarrollo · "
          f"{len(result['actions'])} acciones. No es una puntuación ARC oficial."})


def run_capabilities():
    from seed import arc_capabilities as a, arc_comparison as c
    from echo_arc.observe import Journal
    c.prepared()
    root = new_run("capabilities")
    state = c.read(c.HISTORICAL / "profile.json")["learned"]
    rows = []
    for task in a.suite():
        emit({"kind": "frame", "origin": "LIVE / diagnóstico sintético", "grid": task["task"]["train"][0]["input"]})
        journal = Journal(root / (task["id"] + ".jsonl"))
        original_write = journal.write
        def visible_write(**event):
            original_write(**event)
            # Do not copy synthesized programs into viewer text or public captures.
            emit({"kind": event.get("kind", "decision"), "text": str(event.get("kind", "decision")),
                  "origin": "LIVE / diagnóstico sintético"})
        journal.write = visible_write
        try:
            result = a.solve_public(c.solver_input(task["task"]), "full", state, journal)
        finally:
            journal.close()
        correct = c.judge(task["task"], result)
        rows.append({"task": task["id"], "correct": correct, "trials": result["trials"]})
        emit({"kind": "result", "text": f"{task['id']} · exacta={correct} · {result['trials']} ensayos"})
    (root / "summary.json").write_text(json.dumps(rows))
    emit({"kind": "result", "text": f"{sum(r['correct'] for r in rows)}/12. Reproducción de desarrollo; no una capacidad nueva."})


def run(ident):
    if hasattr(os, "nice"):
        os.nice(10)
    if ident == "integrity":
        from seed.arc_comparison import freeze_guard, prepared
        prepared()
        guard = freeze_guard()
        emit({"kind": "result", "text": "Fuentes congeladas intactas; candidato ARC aún sujeto al cierre S6."})
    elif ident == "arc-gym":
        run_arc()
    elif ident == "arc-capabilities":
        run_capabilities()
    elif ident == "unit-observation":
        env = dict(os.environ, PYTHONPATH=str(ROOT.parent), MPLCONFIGDIR="/tmp/echo-nexus-mpl")
        raise SystemExit(subprocess.call([sys.executable, "-m", "unittest", "tests.test_arc_comparison", "tests.test_arc_capabilities",
                                         "tests.test_observe", "tests.test_observe_s6", "-q"], cwd=ROOT, env=env))
    else:
        from gui4.catalog import BY_ID
        case = BY_ID[ident]
        if case.origin == "LIVE" and ident != "cortex-propone":
            run_live(case)
        elif case.origin == "BENCH":
            emit(dict(case.runner().as_dict(), kind="result", origin="BENCH / desarrollo"))
        else:
            raise ValueError("Este caso no se ejecuta desde el arnés")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=("manifest", "run"))
    p.add_argument("value")
    args = p.parse_args()
    (manifest if args.operation == "manifest" else run)(args.value)
