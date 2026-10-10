"""Mini terminal for real ECHO records, with no model or second thought bus.

python3 observe.py --launch --demo     open a window, run training diagnostic, keep watching
python3 observe.py                    watch local logs (including newly created sessions)
python3 observe.py --once --plain     print recent historical records and exit
"""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
ARC_PYTHON = ROOT / "lab/arc3/ARC-AGI-3-Agents/.venv/bin/python"
ARC_SCHEMA = "echo45-arc-decisions-v1"
CALCULATIONS = {"_plan": "búsqueda de ruta", "_plan_clicks": "plan de clics",
                "_frontier_step": "exploración", "_cause_step": "prueba causal",
                "_goal": "candidato a meta"}


def clean(value, limit=220):
    text = str(value)
    text = "".join(c if ord(c) >= 32 and not 127 <= ord(c) <= 159 else " " for c in text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def action_name(action):
    kind, key, xy = action
    if kind == "R":
        return "reiniciar"
    if kind == "C":
        return f"clic en {xy}"
    return {1: "arriba", 2: "abajo", 3: "izquierda", 4: "derecha"}.get(key, f"tecla {key}")


def render(row, technical=False):
    """Label only recorded data. No fabricated introspection or causal 'because'."""
    if not isinstance(row, dict):
        raise ValueError("el registro no es un objeto")
    if row.get("schema") == ARC_SCHEMA:
        payload = {k: v for k, v in row.items() if k != "hash"}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if hashlib.sha256(raw.encode()).hexdigest() != row.get("hash"):
            raise ValueError("hash del registro ARC incorrecto")
        kind = row["kind"]
        if row.get("agent") == "echo45-relational-v3":
            if kind == "observation":
                return [f"REJILLA V3 · contexto {clean(row['context'])} · acción {clean(row['action'])}",
                        f"  Valores de política {clean(row['policy_scores'])} · presupuesto {row['budget']}"]
            if kind == "result":
                metrics = row["metrics"]
                return [f"REJILLA V3 · resultado {clean(row['status'])}",
                        f"  Trabajo {metrics['work']} · programas probados {metrics['trials']} · "
                        f"programas verificados {metrics['verified_programs']}"]
        if kind == "observation":
            return []  # Raw observation stays in the diary, alongside the decision/result.
        if kind == "decision":
            b = row["before"]
            out = [f"Paso {row['step']} · ACCIÓN: {action_name(row['action'])}",
                   f"  Hipótesis: cuerpo {b.get('me')} · posición {b.get('pos')} · objetivo {b.get('target')}",
                   f"  Plan restante: {b['path_remaining']} pasos / {b['clicks_remaining']} clics · espera {b.get('hold', 0)}"]
            if row.get("branches"):
                out.insert(1, "  Rama observada: " + row["branches"][-1]["label"])
            temporal = row["after"].get("temporal_state")
            if temporal:
                out.append("  Memoria temporal: entradas " + clean(temporal["counts"], 95))
                out.append("  Prueba registrada: " + clean(temporal["decision"], 140))
                out.append("  Orden " + clean(temporal["orders"], 95) +
                           " · umbral " + clean(temporal["thresholds"], 95))
            calls = []
            for r in row["returns"]:
                name = r["method"].split(".")[-1]
                if name in CALCULATIONS:
                    value = r["value"]
                    outcome = "sin candidato" if value is None else clean(value, 65)
                    calls.append(f"{CALCULATIONS[name]}: {outcome}")
            if calls:
                out.append("  Calculó: " + " / ".join(dict.fromkeys(calls)))
            if row.get("parameter_consumptions"):
                out.append("  Controles leídos: " + clean(row["parameter_consumptions"]))
            if technical:
                selected = [r for r in row["returns"] if r["method"].endswith(".choose")]
                out.append("  Ramas ejecutadas: " + " → ".join(f"{r['method']}:{r['line']}" for r in selected))
            return out
        if kind == "result":
            before, after = row["before"], row["after"]
            status = ("NIVEL COMPLETADO" if row["level_up"] else
                      "GAME OVER" if row["game_over"] else
                      "cambió la observación" if row["changed"] else "observación sin cambio")
            out = [f"  Resultado paso {row['step']}: {status}",
                   f"  Modelo: predicciones [aciertos, fallos] {after.get('pred')} · hipótesis {after['hypotheses_count']}"]
            if after["hypotheses_count"] > before["hypotheses_count"]:
                out.append("  Nuevas hipótesis (estado declarado por ARC): " + clean(after["recent_hypotheses"]))
            if row.get("contradictory_noop"):
                out.append("  Predicción contradicha: esperaba un cambio y no se observó.")
            if row.get("transition_revisions"):
                out.append("  Revisiones de transición registradas: " + clean(row["transition_revisions"]))
            return out
        if kind == "start":
            out = [f"INICIO {row['origin']} · ARC {row['agent']} · presupuesto {row['budget']}"]
            if "mission" in row:
                out.append("  Misión registrada: " + row["mission"])
            return out
        if kind == "game":
            return ["PRUEBA: " + row["game"]]
        if kind == "verified_hypothesis":
            return ["REJILLA · programa ajustado a las demostraciones: " + clean(row["program"]),
                    f"  Ejemplos coincidentes: {row['demonstrations']} · respuesta de test sin verificar"]
        if kind == "refinement_round":
            return [f"REJILLA · ronda {row['iteration']} · programas probados {row['trials']} · hipótesis ajustadas {row['verified']}",
                    "  Fallos medidos en demostraciones: " + clean(row["best_errors"])]
        if kind == "refinement_result":
            return [f"REJILLA · {clean(row['status'])} · programas probados {row['trials']} · grupos de predicciones {row['prediction_groups']}",
                    "  Las respuestas de test las comprueba después el evaluador."]
        if kind == "game_end":
            return [f"FIN {row['game']} · niveles {row['levels']} · acciones {row['actions']} · reinicios automáticos {row['resets']}"]
        if kind == "end":
            return ["SESIÓN: " + row["status"] + (" · " + row["error"] if "error" in row else "")]
        raise ValueError(f"tipo ARC desconocido: {kind}")
    if "q_row" in row and "wsp" in row:
        # Reuse TALK-1; do not change the core's thought keys or invent new events.
        if str(ROOT.parent) not in sys.path:
            sys.path.insert(0, str(ROOT.parent))
        from echoai.nexus0 import talk
        talk.validate(row)
        return [f"NÚCLEO · turno {row['turn']} · observó {row['kind']} · {talk.BODY[row['action']]}",
                f"  Q {row['q_row']} · gate {talk.GATE[row['gate_decision']]} · recompensa {row['reward']}",
                f"  Atención: {talk.REASON_ES[row['reason_name']]} · T predijo {row['t_pred']}",
                f"  Aprendizaje: nuevo {row['n']} · sorpresa {row['s']} · ΔQ {row['delta']}"]
    kind = row.get("kind")
    if kind == "village_decision":
        return [f"ALDEA · episodio {row['episode']} · interlocutor {clean(row['agent'])}",
                f"  Contexto del diario: {row['context']} · valores de acciones {row['q_values']}",
                f"  Decisión ejecutada: verificar {row['verified']} · escribir {row['wrote']}",
                f"  Coste observado: {row['cost']} · prueba guardada: {clean(row.get('entry_hash'))}",
                "  Reclamaciones observadas: " + clean(row['claims'])]
    if kind in ("requests", "answers"):
        out = []
        # Paired experiments record arm-keyed requests and a separate answer
        # receipt. Read their actual IDs; never invent a missing prompt/answer.
        requests = row.get("requests")
        receipt = row.get("answers")
        if isinstance(requests, dict):
            for arm, batch in requests.items():
                for req in batch:
                    out += [f"S6 · {clean(arm)} · petición {req['id'] + 1} · tipo {clean(req['type'])}",
                            "  Petición registrada: " + clean(req["prompt"])]
            return out
        if isinstance(receipt, dict) and isinstance(receipt.get("arms"), dict):
            for arm, batch in receipt["arms"].items():
                for answer in batch:
                    out += [f"S6 · {clean(arm)} · respuesta a petición {answer['id'] + 1}",
                            "  Propuesta del modelo: " + clean(answer["answer"])]
            return out
        answers = row.get("answers", [])
        for i, req in enumerate(row["requests"]):
            out += [f"S6 · petición {req['id'] + 1} · tipo {req['type']}",
                    "  Petición registrada: " + clean(req["prompt"])]
            if i < len(answers):
                out.append("  Propuesta del modelo: " + clean(answers[i]))
        return out
    if kind == "verdict":
        label = " · ".join(clean(row[k]) for k in ("arm", "seed") if k in row)
        out = [f"S6 · propuesta {row['id'] + 1} · {label + ' · ' if label else ''}{row['verdict']} · {clean(row.get('reason', ''))}"]
        for partition in ("A", "B"):
            measured = row.get(partition)
            if isinstance(measured, dict):
                out.append(f"  {partition}: {measured['before_levels']} → {measured['after_levels']} niveles"
                           + f" · ganancia {measured['gain']} · pérdidas {len(measured['loss_indices'])}")
            else:
                out.append(f"  {partition}: {row.get('prior_' + partition, 'no evaluado')} → "
                           + str(row.get('trial_' + partition, 'no evaluado')))
        return out
    if kind == "proposal":
        return [f"S6-A · petición {row.get('type')} · veredicto {clean(row.get('verdict'))}",
                "  Petición registrada: " + clean(row.get("prompt", ""))]
    return []


class Tail:
    """Follow complete JSONL records; handle split writes, truncation and rotation."""
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0
        self.pending = b""
        self.identity = None
        self.line = 0

    def skip_history(self):
        """Attach at EOF without parsing old records; preserve a split last line."""
        with self.path.open("rb") as f:
            stat = os.fstat(f.fileno())
            end, pending = stat.st_size, b""
            position = end
            while position:
                start = max(0, position - 4096)
                f.seek(start)
                pending = f.read(position - start) + pending
                if b"\n" in pending:
                    pending = pending.rsplit(b"\n", 1)[1]
                    break
                if len(pending) > 2 * 1024 * 1024:
                    raise ValueError("línea demasiado larga; no se puede mostrar completa")
                position = start
            self.identity = (stat.st_dev, stat.st_ino)
            self.offset, self.pending, self.line = end, pending, 0

    def read(self, history=0):
        with self.path.open("rb") as f:
            stat = os.fstat(f.fileno())
            identity = (stat.st_dev, stat.st_ino)
            new = self.identity is None or identity != self.identity or stat.st_size < self.offset
            if new:
                self.identity, self.pending, self.line = identity, b"", 0
                self.offset = max(0, stat.st_size - 1024 * 1024) if history else 0
                f.seek(self.offset)
                if self.offset:
                    f.readline()  # Drop only the partial leading line.
                    self.offset = f.tell()
            else:
                f.seek(self.offset)
            data = self.pending + f.read(1024 * 1024)
            self.offset = f.tell()
        lines = data.split(b"\n")
        self.pending = lines.pop()
        if len(self.pending) > 2 * 1024 * 1024:
            raise ValueError("línea demasiado larga; no se puede mostrar completa")
        if new and history:
            # Historical display only promises the last requested records.
            # Avoid decoding a megabyte for every archived diary at startup.
            lines = [line for line in lines if line.strip()][-history:]
        records = []
        for line in lines:
            self.line += 1
            if line.strip():
                try:
                    records.append(json.loads(line))
                except ValueError as exc:
                    raise ValueError(f"JSON ilegible, línea leída {self.line}") from exc
        return records[-history:] if new and history else records


def discover(root):
    lab = root / "lab"
    # Do not scan simulator-private traces or vendored model/tool directories.
    paths = [lab / "thought.jsonl"]
    for base, names in ((lab / "observability", ("arc-decisions.jsonl", "thought.jsonl")),
                        (lab / "seed", ("journal.jsonl",))):
        if base.exists():
            for folder, dirs, files in os.walk(base, followlinks=False):
                dirs[:] = [d for d in dirs if d not in ("cache", "exam", "records", "private", "determinism", "__pycache__")]
                for name in names:
                    path = Path(folder) / name
                    if name in files and not path.is_symlink():
                        paths.append(path)
    return sorted({p for p in paths if p.is_file() and not p.is_symlink()})


def display(lines, tty, status):
    if tty:
        cols, rows = shutil.get_terminal_size((100, 28))
        sys.stdout.write("\033[H\033[2J")
        header = ["echoAI · decisiones observables", "ARC v5.7/v5.8 / núcleo / S6 · hipótesis ≠ hechos", status, "─" * min(cols - 1, 95)]
        visible = list(lines)[-max(1, rows - len(header) - 1):]
        sys.stdout.write("\n".join(clean(s, cols - 1) for s in header + visible) + "\n")
    sys.stdout.flush()


def watch(args):
    followers, lines = {}, deque(maxlen=200)
    tty = sys.stdout.isatty() and not args.plain
    child = None
    if args.demo or args.run:
        if not ARC_PYTHON.is_file():
            if args.demo:
                raise RuntimeError("no existe el entorno gestionado ARC; el visor por sí solo usa Python estándar")
        out = ROOT / "lab/observability" / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8] + "-development")
        out.mkdir(parents=True, exist_ok=False)
        log = (out / "process.log").open("x", encoding="utf-8")
        command = args.run or [str(ARC_PYTHON), "-m", "echo_arc.observe", "gym", "--budget", "240",
                               "--delay", "0.035", "--out", str(out)]
        env = dict(os.environ)
        env["NAVI_THOUGHT_LOG"] = str(out / "thought.jsonl")
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT.parent), str(ROOT), env.get("PYTHONPATH", "")])
        try:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        finally:
            log.close()
        lines.append("Diagnóstico de desarrollo: 4 juegos de entrenamiento." if args.demo else
                     "Proceso de desarrollo iniciado; registro del núcleo habilitado.")
    next_scan = 0
    reads = 0
    display(lines, tty, "Buscando diarios locales de desarrollo…")
    try:
        while True:
            now = time.monotonic()
            if now >= next_scan:
                paths = [Path(p) for p in args.files] if args.files else discover(ROOT)
                recent = set(sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[:3])
                for p in paths:
                    if p not in followers:
                        tail = Tail(p)
                        followers[p] = tail
                        # Existing data is always marked historical, even a running file.
                        try:
                            if p not in recent and not args.files:
                                tail.skip_history()
                                continue
                            for row in tail.read(history=2):
                                caption = render(row, args.technical)
                                if caption:
                                    lines.append("HISTÓRICO · " + clean(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p))
                                    lines.extend(clean(s) for s in caption)
                                    if not tty:
                                        print("\n".join(list(lines)[-len(caption)-1:]))
                        except (OSError, ValueError, KeyError, TypeError) as exc:
                            text = "ERROR de lectura · " + clean(p) + " · " + clean(exc)
                            lines.append(text)
                            if not tty:
                                print(text, flush=True)
                next_scan = now + 3
            changed = False
            for p, tail in list(followers.items()):
                try:
                    rows = tail.read()
                    for row in rows:
                        reads += 1
                        caption = render(row, args.technical)
                        if not caption:
                            continue
                        text = ["NUEVO REGISTRO · " + clean(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p), *caption]
                        lines.extend(clean(s) for s in text)
                        if not tty:
                            print("\n".join(clean(s) for s in text), flush=True)
                        changed = True
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    text = "ERROR de lectura · " + clean(p) + " · " + clean(exc)
                    lines.append(text)
                    if not tty:
                        print(text, flush=True)
                    del followers[p]
                    changed = True
            if child is not None:
                code = child.poll()
                status = "Diagnóstico de desarrollo en curso" if code is None else f"Diagnóstico terminado (salida {code}); esperando nuevas trazas"
            else:
                status = "Esperando registros locales; los históricos no indican una prueba activa"
            status += f" · {len(followers)} archivos · {reads} registros nuevos"
            display(lines, tty, status)
            if args.once:
                return 0
            time.sleep(0.15 if changed else 0.35)
    finally:
        # Closing this mini terminal stops only its own optional development demo.
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--launch", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--plain", action="store_true")
    ap.add_argument("--technical", action="store_true")
    ap.add_argument("--run", nargs=argparse.REMAINDER, help="comando de desarrollo; habilita thought.jsonl del núcleo")
    args = ap.parse_args(argv)
    if (args.demo or args.run) and args.once:
        ap.error("--demo y --run mantienen el visor abierto; no se combinan con --once")
    if args.demo and args.run:
        ap.error("elige --demo o --run")
    if args.run == []:
        ap.error("--run requiere un comando")
    if args.launch:
        terminal = shutil.which("xfce4-terminal")
        if terminal is None:
            ap.error("no se encontró xfce4-terminal; ejecuta el visor sin --launch")
        command = [sys.executable, str(ROOT / "observe.py"), *[a for a in (argv or sys.argv[1:]) if a != "--launch"]]
        subprocess.run([terminal, "--disable-server", "--title=echoAI · decisiones observables",
                        "--geometry=105x28", "--working-directory=" + str(ROOT), "-x", *command], check=True)
        return 0
    try:
        return watch(args)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
