"""Local durable supervisor for the requested capacity comparison and S6 notice.

Only capacity development can be resumed here. Frozen S6 owns its own service,
promotions, model submissions and audit. No new S6 inference is launched here.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from seed import kenyon_arc1 as capacity

REPO = capacity.REPO
ROOT = REPO / "lab/validation/echo45-completion-20260930"
S6 = REPO / "lab/seed/s6b11-20260929"
DOC = REPO / "docs/ECHO45-VALIDATION-CAPACITY-S6-RESULTS.md"


def outcome(validation, cap, s6):
    return {"validation_green": bool(validation),
            "capacity_finished": cap is not None,
            "capacity_green": bool(cap and cap.get("green")),
            "s6_finished": s6 is not None,
            "s6_green": bool(s6 and s6.get("s6_green")),
            "all_green": bool(validation and cap and cap.get("green") and s6 and s6.get("s6_green"))}


def optional(path):
    return capacity.read(path) if path.exists() else None


def write_report(error=None):
    validation = (REPO / "lab/validation/nexus0-20260930/complete.log").read_text()
    valid = "Ran 488 tests" in validation and "OK (expected failures=1)" in validation
    cap, s6 = optional(capacity.ROOT / "summary.json"), optional(S6 / "closed.json")
    result = outcome(valid, cap, s6)
    result["at"] = capacity.datetime.now(capacity.timezone.utc).isoformat()
    result["capacity_status"] = optional(capacity.ROOT / "status.json")
    result["s6_status"] = optional(S6 / "status.json")
    if error:
        result["error"] = error
    capacity.save(ROOT / "status.json", result)
    cap_label = "VERDE" if result["capacity_green"] else "ROJO" if cap else "EN EJECUCIÓN"
    supervisor = optional(S6 / "supervisor.json") or {}
    s6_stopped = ((result["s6_status"] or {}).get("stage") == "PENDING_ERROR" or
                  (supervisor.get("state") == "FINISHED" and bool(supervisor.get("exit_code"))))
    s6_label = ("VERDE" if result["s6_green"] else "ROJO" if s6 else
                "DETENIDO / PENDIENTE" if s6_stopped else "EN EJECUCIÓN")
    lines = ["# Validación, capacidad ARC-1 y S6-B11", "", "Actualizado: " + result["at"], "",
             "- NEXUS-0: " + ("validación aprobada, 488 pruebas y un fallo esperado histórico." if valid else "pendiente."),
             "- CAPACITY-500K: **" + cap_label + "**. Tres brazos en 250 tareas ARC-1 de training, con replay completo.",
             "- S6-B11: **" + s6_label + "**. Sus cinco criterios conservan su contrato.", "",
             "Estado conjunto: **" + ("VERDE" if result["all_green"] else "PENDIENTE / NO VERDE") + "**.", ""]
    if cap:
        lines += ["Aciertos de desarrollo: " + ", ".join(f"{arm} {row['solved']}/{row['of']}" for arm, row in cap["totals"].items()) + ".", ""]
    if error:
        lines += ["Incidencia del supervisor: " + error, ""]
    lines += ["[Validación](ECHO45-NEXUS0-VALIDATION-20260930.md) · [Comparación](ECHO45-CAPACITY500K-ARC1-RESULTS.md) · [S6](ECHO45-S6-B11-RESULTS.md).", "",
              "El supervisor usa un servicio de usuario y un aviso local de escritorio. Sigue mientras el equipo permanezca encendido; no envía mensajes a terceros.", ""]
    DOC.write_text("\n".join(lines))
    return result


def notify(result):
    if result["all_green"]:
        title, body = "ECHO-4.5 · validación, capacidad y S6 VERDES", "Los tres pasos solicitados cumplen sus criterios. Informe en docs/ECHO45-VALIDATION-CAPACITY-S6-RESULTS.md."
    else:
        title, body = "ECHO-4.5 · evaluación terminada con pendientes", "Capacidad/S6 conservan sus resultados reales. Revisa docs/ECHO45-VALIDATION-CAPACITY-S6-RESULTS.md."
    command = shutil.which("notify-send")
    delivered = False
    if command:
        notice = subprocess.run([command, "--app-name=echoAI", title, body], capture_output=True, text=True)
        delivered = notice.returncode == 0
    capacity.save(ROOT / "notification.json", {"at": result["at"], "all_green": result["all_green"],
                                              "desktop_delivered": delivered, "title": title})


def archive_interrupted_journals():
    stamp = str(time.time_ns())
    archived = []
    for phase in ("primary", "audit"):
        for folder in sorted((capacity.ROOT / phase / "decisions").glob("*/*")):
            if (capacity.ROOT / phase / "results" / folder.parent.name / (folder.name + ".json")).exists():
                continue
            destination = capacity.ROOT / "interrupted" / stamp / phase / "decisions" / folder.parent.name / folder.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            folder.rename(destination)
            archived.append(str(destination.relative_to(capacity.ROOT)))
    capacity.save(ROOT / "handoff.json", {"at": stamp, "archived_incomplete_attempts": archived,
                  "sources_unchanged": True, "per_attempt_expansion_ceiling": capacity.CONFIG["expansions"],
                  "interrupted_cpu_cost": "not measurable; incomplete traces preserved separately"})


def publish_candidate():
    """Create an optional next candidate only after the audited capacity gate."""
    summary = capacity.read(capacity.ROOT / "summary.json")
    if not summary["green"]:
        return
    profile = capacity.integrity()
    assert summary["profile_sha256"] == capacity.digest(profile)
    assert all(summary["checks"].values()) and summary["replays"] == 750
    guide = capacity.fit_guides(profile)["guide500k"]
    target = capacity.ROOT / "candidate"
    target.mkdir(exist_ok=True)
    (target / "weights.bin").write_bytes(guide.weights)
    capacity.save(target / "manifest.json", {"name": "ECHO45-CAPACITY500K-DEV-CANDIDATE", "enabled": True,
                  "state": profile["state"], "primitive_names": guide.names, "units": guide.units,
                  "examples": guide.examples, "weights_sha256": hashlib.sha256(guide.weights).hexdigest(),
                  "profile_sha256": capacity.digest(profile), "summary_sha256": capacity.digest(summary),
                  "interface": "SparsePrimitiveGuide.guided_library", "official_arc_score": False,
                  "s6_integration": "requires a new condition; B11 unchanged"})


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "supervisor.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        capacity.integrity()
        write_report()
        if not (capacity.ROOT / "summary.json").exists():
            archive_interrupted_journals()
            with (capacity.ROOT / "process.log").open("a") as stream:
                process = subprocess.run([sys.executable, "-u", "-m", "seed.kenyon_arc1", "follow"],
                    cwd=REPO, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
            if process.returncode:
                result = write_report("capacity process exit " + str(process.returncode))
                notify(result)
                return process.returncode
        publish_candidate()
        while True:
            result = write_report()
            if result["capacity_finished"] and result["s6_finished"]:
                notify(result)
                return 0
            supervisor = optional(S6 / "supervisor.json")
            if supervisor and supervisor.get("state") == "FINISHED" and supervisor.get("exit_code"):
                result = write_report("S6 supervisor stopped with exit " + str(supervisor["exit_code"]))
                notify(result)
                return 1
            time.sleep(20)


if __name__ == "__main__":
    raise SystemExit(run())
