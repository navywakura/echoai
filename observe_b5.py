"""Display actual new S6/refinement records through the existing mini terminal."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from types import FunctionType

import observe as previous


def render(row, technical=False):
    kind = row.get("kind")
    if row.get("schema") == previous.ARC_SCHEMA and (kind in
            ("verified_hypothesis", "refinement_round", "refinement_result") or
            (kind == "start" and "mission" not in row)):
        payload = {key: value for key, value in row.items() if key != "hash"}
        raw = previous.json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if previous.hashlib.sha256(raw.encode()).hexdigest() != row.get("hash"):
            raise ValueError("hash del registro ARC incorrecto")
        if kind == "start":
            return [f"INICIO {row['origin']} · {row['agent']} · presupuesto {row['budget']}"]
        if kind == "verified_hypothesis":
            return [f"REJILLAS · regla coincide en {row['demonstrations']} demostraciones",
                    "  Programa probado: " + previous.clean(row["program"]), "  Respuesta nueva: aún no verificada"]
        if kind == "refinement_round":
            return [f"REJILLAS · ronda {row['iteration']} · {row['trials']} programas · {row['verified']} verificados",
                    "  Errores medidos: " + previous.clean(row["best_errors"])]
        return [f"REJILLAS · {row['status']} · {row['trials']} programas · {row['verified']} verificados",
                f"  Grupos de predicciones: {row['prediction_groups']} · respuesta nueva sin certificar"]
    if kind == "raw":
        return [f"S6 SIN FILTRO · propuesta {row['id'] + 1} · {row['verdict']}",
                f"  Parches acumulados: {len(row['strategy']['program']['patches'])} · utilidad/regresión sin filtrar"]
    if kind == "verdict" and "A" in row:
        out = [f"S6 · propuesta {row['id'] + 1} · {row['verdict']} · {previous.clean(row.get('reason', ''))}"]
        for cohort in ("A", "B"):
            if cohort in row:
                measured = row[cohort]
                out.append(f"  {cohort}: {measured['before_levels']}→{measured['after_levels']} · pérdidas individuales {len(measured['loss_indices'])}")
        return out
    return previous.render(row, technical)


def discover(root):
    bases = [root / "lab/observability/s6-precise-capacity-20260928/main",
             root / "lab/seed/s6b5-20260928", root / "lab/seed/refinement-dev-20260928/decisions"]
    files = []
    for base in bases:
        if base.exists():
            files += [p for p in base.rglob("*") if p.name in ("arc-decisions.jsonl", "journal.jsonl")
                      and not p.is_symlink() and not {"exam", "cache", "source-archive"} & set(p.relative_to(base).parts)]
    return sorted(files)


watch = FunctionType(previous.watch.__code__, dict(previous.watch.__globals__, render=render, discover=discover),
                     previous.watch.__name__, previous.watch.__defaults__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*")
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--technical", action="store_true")
    args = parser.parse_args()
    if args.launch:
        terminal = shutil.which("xfce4-terminal")
        if terminal is None:
            parser.error("no se encontró xfce4-terminal")
        command = [sys.executable, str(Path(__file__).resolve()), *[a for a in sys.argv[1:] if a != "--launch"]]
        subprocess.run([terminal, "--disable-server", "--title=echoAI · S6-B5 y reglas verificadas",
                        "--geometry=105x28", "--working-directory=" + str(previous.ROOT), "-x", *command], check=True)
        return 0
    args.demo, args.run = False, None
    try:
        return watch(args)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
