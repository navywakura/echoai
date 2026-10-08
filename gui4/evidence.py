"""Read sealed ECHO-3 reports without recomputing anything.

Every figure this module returns comes from a file under ``lab/``.  Nothing
here runs a bench, opens a campaign or touches a lock.  When a report is
missing the reader says so instead of guessing: a case with no evidence is
shown disabled, never invented.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

ECHOAI = Path(__file__).resolve().parents[1]
LAB = ECHOAI / "lab"


def sha8(path: Path) -> str:
    """First 8 hex digits of a file's sha256, or '' when unreadable."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return ""


def load(relative: str) -> Optional[dict]:
    """Load one JSON document under ``lab/``; None when absent or broken."""
    path = LAB / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def dig(source: Any, *path: Any, default: Any = None) -> Any:
    """Walk nested dicts/lists, returning ``default`` on any missing step."""
    node = source
    for key in path:
        try:
            node = node[key]
        except (KeyError, IndexError, TypeError):
            return default
    return node


@dataclass
class Figure:
    """One measured number, with the denominator and wording it needs."""

    label: str
    value: str
    detail: str = ""


@dataclass
class Evidence:
    """A sealed report reduced to what a panel should show."""

    phase: str
    source: str
    available: bool
    sha8: str = ""
    figures: list[Figure] = field(default_factory=list)
    limit: str = ""
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "phase": self.phase,
            "source": self.source,
            "available": self.available,
            "sha8": self.sha8,
            "figures": [(f.label, f.value, f.detail) for f in self.figures],
            "limit": self.limit,
            "reason": self.reason,
        }


def _missing(phase: str, source: str) -> Evidence:
    return Evidence(phase, source, False,
                    reason=f"falta {source} en lab/; no se inventa el número")


def _fraction(numerator: Any, denominator: Any) -> str:
    if numerator is None or denominator is None:
        return "sin dato"
    return f"{numerator}/{denominator}"


def drone3() -> Evidence:
    source = "echo3_drone3_report.json"
    report = load(source)
    if report is None:
        return _missing("DRONE-3", source)
    figures = []
    for stage, name in (("validation", "Validación"), ("confirmation", "Confirmación")):
        aggregate = dig(report, "stages", stage, "aggregate", default={})
        figures.append(Figure(
            f"{name} · vuelos", _fraction(aggregate.get("passed"), aggregate.get("flights")),
            f"holgura mínima {aggregate.get('min_clearance_mm', '?')} mm · "
            f"{aggregate.get('collisions', '?')} colisiones"))
    hard = dig(report, "stages", "validation", "aggregate", "hard", default={})
    figures.append(Figure("Restricciones duras", "todas 0" if hard and not any(hard.values())
                          else "sin dato", " · ".join(sorted(hard)) if hard else ""))
    figures.append(Figure("Mutantes detectados", str(len(report.get("mutants") or []))))
    figures.append(Figure("Manipulaciones rechazadas", str(len(report.get("manipulations") or []))))
    return Evidence(
        "DRONE-3", source, True, sha8(LAB / source), figures,
        limit="Energía simulada, mundo estático salvo la intervención declarada, "
              "celdas de 3 m. HIL y jaula siguen en false.")


def transfer3() -> Evidence:
    source = "transfer3/campaign-c1-v2/certificate.json"
    certificate = load(source)
    if certificate is None:
        return _missing("TRANSFER-3", source)
    figures = [Figure("Campaña", "sellada con custodia humana",
                      str(certificate.get("custodian", "")))]
    for stage, name in (("B", "Validación B"), ("C", "Confirmación C")):
        exam = load(f"transfer3/campaign-c1-v2/exam-{stage}.json")
        nominal = dig(exam, "verdict", "comparisons", "nominal", default={})
        wins, losses = nominal.get("block_wins"), nominal.get("block_losses")
        figures.append(Figure(
            f"{name} · bloques", _fraction(wins, losses),
            f"ganadas {nominal.get('gained', '?')} · perdidas {nominal.get('lost', '?')} "
            f"frente al mismo agente sin la experiencia"))
    figures.append(Figure("Pérdidas atribuibles a la calibración",
                          str(dig(load("transfer3/campaign-c1-v2/exam-C.json"),
                                  "verdict", "attributable_losses", default="sin dato"))))
    return Evidence(
        "TRANSFER-3", source, True, sha8(LAB / source), figures,
        limit="Salas estáticas de dos paredes en simulación funcional. "
              "Sin hardware, sin vuelo, sin ruido real de sensor.")


def _checks(phase: str, source: str, limit: str, unit: str) -> Evidence:
    """Reports that expose ``stages -> {episodes, checks, passed}``."""
    report = load(source)
    if report is None:
        return _missing(phase, source)
    figures = []
    for stage, name in (("bench", "Banco"), ("validation", "Validación"),
                        ("confirmation", "Confirmación")):
        node = dig(report, "stages", stage)
        if not isinstance(node, dict):
            continue
        figures.append(Figure(
            f"{name} · {unit}", str(node.get("episodes", "sin dato")),
            f"{node.get('checks', '?')} comprobaciones · "
            f"{'pasa' if node.get('passed') else 'no pasa'}"))
    mutations = report.get("mutation_tests") or {}
    cases = mutations.get("cases") or []
    if cases:
        figures.append(Figure("Mutantes detectados",
                              _fraction(sum(1 for c in cases if c.get("ok")), len(cases))))
    return Evidence(phase, source, True, sha8(LAB / source), figures, limit=limit)


def pattern1r() -> Evidence:
    return _checks(
        "PATTERN-1R", "echo3_pattern1r_v4_report.json",
        "Dos familias LiDAR; aprendizaje y examen por replay, no en vuelo. "
        "El desglose 4591/4866 vive en el informe escrito, no en este JSON.",
        "episodios")


def dynamic1() -> Evidence:
    return _checks(
        "DYNAMIC-1", "echo3_dynamic1_v2_report.json",
        "Seguimiento de la normal de una cara desde hover. "
        "No hay compensación general del movimiento propio.",
        "episodios")


def px41() -> Evidence:
    source = "echo3_px41_report.json"
    report = load(source)
    if report is None:
        return _missing("PX4-1", source)
    figures = []
    for stage, name in (("validation", "Validación"), ("confirmation", "Confirmación")):
        node = report.get(stage) or {}
        figures.append(Figure(f"{name} · vuelos",
                              _fraction(node.get("passed"), node.get("n"))))
        blocked = sum(int(dig(row, "audit", "blocked", default=0))
                      for row in node.get("rows") or [])
        if blocked:
            figures.append(Figure(f"{name} · intentos inválidos bloqueados",
                                  f"{blocked}/{blocked}",
                                  "sobre envolvente, autoridad, exclusión y secuencia"))
    mutants = dig(report, "controls", "mutants", default={})
    if mutants:
        figures.append(Figure(
            "Mutantes detectados",
            _fraction(sum(1 for m in mutants.values() if m.get("detected")), len(mutants)),
            " · ".join(sorted(mutants))))
    return Evidence(
        "PX4-1", source, True, sha8(LAB / source), figures,
        limit="Objetivos norte/sur de un metro y una transacción supervisada.")


def host1() -> Evidence:
    source = "echo3_host1_report.json"
    report = load(source)
    if report is None:
        return _missing("HOST-1", source)
    figures = []
    for stage, name in (("validation", "Validación"), ("confirmation", "Confirmación")):
        policies = dig(report, stage, "policies", default={})
        agent, control = policies.get("consequence") or {}, policies.get("button") or {}
        if agent:
            figures.append(Figure(
                f"{name} · elecciones útiles",
                _fraction(agent.get("useful"), agent.get("total")),
                f"control por botón {_fraction(control.get('useful'), control.get('total'))}"))
        paired = dig(report, stage, "paired_by_seed", default={})
        if paired:
            figures.append(Figure(f"{name} · bloques por semilla",
                                  _fraction(paired.get("wins"), paired.get("losses"))))
    return Evidence(
        "HOST-1", source, True, sha8(LAB / source), figures,
        limit="Autoridad actualizada por consecuencias; calibración supervisada "
              "sobre cinta de máquina, sin confianza humana general.")


#: Every EVIDENCE case resolves through this table.
READERS = {
    "drone3": drone3,
    "transfer3": transfer3,
    "pattern1r": pattern1r,
    "px41": px41,
    "host1": host1,
    "dynamic1": dynamic1,
}


def read(name: str) -> Evidence:
    reader = READERS.get(name)
    if reader is None:
        return Evidence(name, "", False, reason=f"no hay lector de evidencia para {name!r}")
    return reader()
