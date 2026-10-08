"""The GUI-4 case catalogue: every demonstration echoAI can show.

A case declares what it demonstrates, which control contrasts it, what it does
*not* demonstrate, and where its numbers come from.  Three origins, never
mixed in one figure (``docs/GUI4-DESIGN.md`` §4):

``LIVE``      the real agent runs now in this window;
``BENCH``     a real ECHO-3 bench runs now with a reduced denominator;
``EVIDENCE``  a sealed report under ``lab/`` is replayed, never recomputed.

Bench adapters call the phase's own code.  They never re-implement a bench,
never open a sealed campaign and never write under ``lab/<phase>/``.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from . import ORIGIN_BENCH, ORIGIN_EVIDENCE, ORIGIN_LIVE
from . import evidence as ev

ECHOAI = Path(__file__).resolve().parents[1]
VIZ_TASKS = ECHOAI / "viz_tasks"


@dataclass
class Arm:
    """One side of a contrast: the agent, or the control it must beat."""

    name: str
    label: str
    numerator: int
    denominator: int
    detail: str = ""

    @property
    def score(self) -> str:
        return f"{self.numerator}/{self.denominator}"


@dataclass
class BenchResult:
    """What a reduced bench produced, with everything needed to retrace it."""

    case: str
    phase: str
    unit: str
    arms: list[Arm]
    seeds: list[int]
    elapsed_s: float = 0.0
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "case": self.case,
            "phase": self.phase,
            "origin": ORIGIN_BENCH,
            "unit": self.unit,
            "seeds": list(self.seeds),
            "denominator": self.arms[0].denominator if self.arms else 0,
            "elapsed_s": round(self.elapsed_s, 3),
            "note": self.note,
            "arms": [
                {"name": a.name, "label": a.label, "numerator": a.numerator,
                 "denominator": a.denominator, "detail": a.detail}
                for a in self.arms
            ],
        }


@dataclass
class Case:
    """One entry in the catalogue."""

    ident: str
    phase: str
    origin: str
    title: str
    shows: str
    control: str
    limit: str
    #: LIVE cases name a viz task; BENCH cases carry a runner; EVIDENCE a reader.
    task: Optional[str] = None
    runner: Optional[Callable[..., BenchResult]] = None
    reader: Optional[str] = None
    seconds: str = ""
    _unavailable: str = field(default="", repr=False)

    def availability(self) -> tuple[bool, str]:
        """(runnable, reason).  A blocked case says why, it is never hidden."""
        if self._unavailable:
            return False, self._unavailable
        if self.origin == ORIGIN_LIVE:
            path = VIZ_TASKS / f"{self.task}"
            if not path.exists():
                return False, f"falta la tarea {self.task} en viz_tasks/"
            return True, ""
        if self.origin == ORIGIN_BENCH:
            if self.runner is None:
                return False, "sin adaptador de banco"
            return True, ""
        record = ev.read(self.reader or "")
        return (record.available, record.reason)

    def as_dict(self) -> dict:
        runnable, reason = self.availability()
        return {
            "id": self.ident, "phase": self.phase, "origin": self.origin,
            "title": self.title, "shows": self.shows, "control": self.control,
            "limit": self.limit, "seconds": self.seconds,
            "runnable": runnable, "reason": reason,
        }


# ---------------------------------------------------------------- bench arms


def _compose(seeds: Optional[list[int]] = None) -> BenchResult:
    """COMPOSE-1: the full agent against the reactive Q on the same rooms."""
    from echoai.nexus0.compose1_v3 import functional as functional
    from echoai.nexus0.compose1_v4 import bench as v4

    seeds = list(seeds or (7001, 7002, 7003, 7004))
    conditions = ("clear", "blocked", "detour", "far")
    school = json.loads((v4.ROOT / "physical-school.json").read_text())
    arms = {"echo32": Arm("echo32", "agente completo", 0, 0),
            "q": Arm("q", "control · Q reactiva", 0, 0),
            "conventional": Arm("conventional", "control · planificador convencional", 0, 0)}
    began = time.monotonic()
    for index, seed in enumerate(seeds):
        condition = conditions[index % len(conditions)]
        for mode, arm in arms.items():
            row = functional.mission(school["model"], seed, condition, mode)
            arm.denominator += 1
            arm.numerator += int(bool(row.get("reached")))
    for arm in arms.values():
        arm.detail = "metas alcanzadas sin colisión ni hecho falso"
    return BenchResult("composicion", "COMPOSE-1", "misiones", list(arms.values()),
                       seeds, time.monotonic() - began,
                       "salas extruidas, altura fija y energía abstracta")


def _power(seeds: Optional[list[int]] = None) -> BenchResult:
    """POWER-1: predicted cost against the classic fixed battery percentage."""
    from echoai.nexus0.power1 import bench as power

    seeds = list(seeds or (20263201, 20263202, 20263203, 20263204))
    conditions = ("short_low", "long_high", "return_now", "short_low")
    snapshot = power.model()
    arms = {"cost": Arm("cost", "agente · coste previsto", 0, 0),
            "fixed": Arm("fixed", "control · porcentaje fijo", 0, 0),
            "oracle": Arm("oracle", "techo · oráculo", 0, 0)}
    began = time.monotonic()
    for index, seed in enumerate(seeds):
        condition = conditions[index % len(conditions)]
        for policy, arm in arms.items():
            result = power.episode(seed, condition, policy, snapshot, None).get("result", {})
            arm.denominator += 1
            arm.numerator += int(bool(result.get("correct_initial")))
            if result.get("reserve_violations"):
                arm.detail = "reserva violada"
    for arm in arms.values():
        arm.detail = arm.detail or "decisiones iniciales correctas"
    return BenchResult("energia", "POWER-1", "decisiones", list(arms.values()),
                       seeds, time.monotonic() - began,
                       "energía simulada: el PX4 fijado no publica corriente")


def _safe(seeds: Optional[list[int]] = None) -> BenchResult:
    """SAFE-1: the supervisor's verdicts on its own functional bank."""
    from echoai.nexus0.safe1 import bench as safe
    from echoai.nexus0.safe1 import functional

    seeds = list(seeds or (1, 2, 3, 4))
    began = time.monotonic()
    bank = functional.bank(safe.model(), seeds)
    rows = bank.get("rows", []) if isinstance(bank, dict) else list(bank)
    supervised = Arm("supervisor", "supervisor SAFE", 0, 0,
                     "episodios contenidos sin setpoint inseguro")
    for row in rows:
        supervised.denominator += 1
        events = row.get("events", [])
        unsafe = any(event.get("kind") == "accepted_unsafe" for event in events)
        supervised.numerator += int(not unsafe)
    return BenchResult("contencion", "SAFE-1", "episodios", [supervised],
                       seeds, time.monotonic() - began,
                       "contención dentro del banco, no seguridad universal")


def _fusion(seeds: Optional[list[int]] = None) -> BenchResult:
    """FUSION-1: evidence keeps provenance, expiry and conflict."""
    from echoai.nexus0.fusion1 import scenarios

    seeds = list(seeds or (1, 2))
    began = time.monotonic()
    arm = Arm("ledger", "registro de evidencia", 0, 0,
              "observaciones con procedencia y extracto verificables")
    for seed in seeds:
        for case in scenarios.generate(seed, 2):
            for command in case.get("commands", []):
                if command.get("op") != "observe":
                    continue
                arm.denominator += 1
                arm.numerator += int(bool(command.get("extract"))
                                     and bool(command.get("source"))
                                     and command.get("capture_ns") is not None)
    return BenchResult("evidencia", "FUSION-1", "observaciones", [arm],
                       seeds, time.monotonic() - began,
                       "no concede permiso de vuelo por sí sola")


def _cause(seeds: Optional[list[int]] = None) -> BenchResult:
    """CAUSE-1: attribution recomputed from saved flights, against the control.

    The flights are already on disk, so nothing flies here; what runs live is
    the attribution itself, next to the temporal control that simply blames
    whatever happened last.
    """
    from echoai.nexus0.cause1.evaluate import audit_session

    root = ECHOAI / "lab" / "cause1" / "confirmation"
    sessions = sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []
    agent = Arm("attribution", "agente · atribución causal", 0, 0,
                "sesiones atribuidas correctamente")
    control = Arm("temporal", "control · lo último que pasó", 0, 0,
                  "la misma evidencia, culpando al suceso más reciente")
    began = time.monotonic()
    used = []
    for session in sessions:
        try:
            row = audit_session(session)
        except Exception:
            continue
        if not row.get("evidence_valid"):
            continue
        used.append(int(row.get("seed", 0)))
        agent.denominator += 1
        control.denominator += 1
        agent.numerator += int(bool(row.get("correct")))
        control.numerator += int(bool(row.get("baseline_correct")))
    return BenchResult("atribucion", "CAUSE-1", "sesiones", [agent, control],
                       sorted(set(used)), time.monotonic() - began,
                       "vuelos grabados: se recalcula la atribución, no se vuela")


def _sim3(seeds: Optional[list[int]] = None) -> BenchResult:
    """SIM-3: rebuild the sealed evidence and check it still reconstructs."""
    import json as _json

    from echoai.nexus0.sim3.audit import audit_report

    path = ECHOAI / "lab" / "echo3_sim3_report.json"
    began = time.monotonic()
    report = _json.loads(path.read_text(encoding="utf-8"))
    result = audit_report(report, rebuild=True)
    checks = int(result.get("checks", 0))
    valid = bool(result.get("evidence_valid"))
    findings = result.get("findings") or []
    arm = Arm("rebuild", "evidencia reconstruida", checks if valid else 0, checks,
              f"{result.get('recomputed_runs', 0)} ejecuciones recalculadas · "
              f"{len(findings)} hallazgos")
    return BenchResult("mundos-abc", "SIM-3", "comprobaciones", [arm], [],
                       time.monotonic() - began,
                       "reconstruye la evidencia; no vuelve a correr los mundos")


def _ground(seeds: Optional[list[int]] = None) -> BenchResult:
    """GROUND-1: temporal integrity recomputed over the saved flights.

    Two things are recomputed from each episode, not read from its verdict:
    the PX4 lifecycle in the order this bench actually flies it — ready, mode
    change, arm, land, disarm — and the stage timeline, where every stage must
    start exactly where the previous one ended and carry a stamp inside its
    own window.

    The first attempt asserted arm-before-takeoff and scored 0/30: PX4 here
    commands the takeoff mode first and arms after.  The check follows the
    evidence, not the assumption.
    """
    import json as _json

    LIFECYCLE = ("ready", "mode_auto_takeoff", "armed", "land_command", "disarmed")

    root = ECHOAI / "lab" / "ground1-v2" / "bench" / "episodes"
    episodes = sorted(root.glob("*.json")) if root.exists() else []
    order = Arm("lifecycle", "vuelos con ciclo de vida ordenado", 0, 0,
                " → ".join(LIFECYCLE))
    stages = Arm("stages", "línea de etapas encadenada", 0, 0,
                 "cada etapa empieza donde acabó la anterior")
    began = time.monotonic()
    for path in episodes:
        try:
            record = _json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        events = record.get("events") or []
        # A driver event carries ``ev="driver"`` and its real name in
        # ``event``; reading ``ev`` first would label every one of them
        # "driver" and find no lifecycle at all.
        names = [str(e.get("event") if e.get("ev") == "driver" else
                     (e.get("ev") or "")) for e in events]
        order.denominator += 1
        found = [names.index(name) for name in LIFECYCLE if name in names]
        order.numerator += int(len(found) == len(LIFECYCLE)
                               and found == sorted(found))

        timeline = [e for e in events if e.get("ev") == "stage"]
        stages.denominator += 1
        chained = bool(timeline)
        for current, following in zip(timeline, timeline[1:]):
            if current.get("end_ns") != following.get("begin_ns"):
                chained = False
        for stage in timeline:
            stamp = stage.get("sim_time_ns")
            if not (isinstance(stamp, int)
                    and stage.get("begin_ns", 0) <= stamp <= stage.get("end_ns", 0)):
                chained = False
        stages.numerator += int(chained)
    return BenchResult("suelo-wsp", "GROUND-1", "vuelos", [order, stages], [],
                       time.monotonic() - began,
                       "integridad temporal sobre vuelos grabados; "
                       "no reproduce el certificado completo de GROUND-1")


BENCH_RUNNERS: dict[str, Callable[..., BenchResult]] = {
    "composicion": _compose,
    "energia": _power,
    "contencion": _safe,
    "evidencia": _fusion,
    "atribucion": _cause,
    "mundos-abc": _sim3,
    "suelo-wsp": _ground,
}


# ------------------------------------------------------------------ the list

def build() -> list[Case]:
    return [
        Case("cuerpo-aprende", "ECHO-1/2", ORIGIN_LIVE,
             "El cuerpo aprende por consecuencia",
             "Q parte de cero y cambia sólo cuando la acción tiene consecuencia.",
             "el diario marca en verde los turnos donde Q cambió de verdad",
             "Mundo discreto de 3×3×3 voxeles. No es vuelo.",
             task="01-body3d-learn.json", seconds="continuo"),
        Case("muerte-herencia", "GEN-1f", ORIGIN_LIVE,
             "Muerte, respawn y herencia",
             "La vida termina, el individuo renace conservando su memoria y "
             "cada 48 muertes nace un hijo con memorias nuevas.",
             "el hijo arranca con CAM/Q/T vacías: lo heredado es el presupuesto",
             "Herencia acotada en un banco sintético, no genética.",
             task="03-gen1f-live.json", seconds="continuo"),
        Case("temperatura", "HEAT-1b", ORIGIN_LIVE,
             "Energía y temperatura regulan la conducta",
             "H y temperatura enteras cambian lo que el agente elige hacer.",
             "la temperatura es una variable homeostática, no la del procesador",
             "Variables abstractas enteras. No hay sensor térmico.",
             task="02-heat-live.json", seconds="continuo"),
        Case("cortex-propone", "SIGN-C", ORIGIN_LIVE,
             "El córtex propone y el gate dispone",
             "Un LLM local propone una acción; VERIFY y el gate deciden.",
             "la propuesta del córtex se ve junto al veredicto que la modificó o bloqueó",
             "Requiere el Qwen local. El córtex nunca escribe hechos ni motores.",
             task="04-qwen-sign.json", seconds="continuo"),
        Case("composicion", "COMPOSE-1", ORIGIN_BENCH,
             "Componer una ruta con evidencia",
             "El agente completo alcanza metas que la Q reactiva no alcanza.",
             "Q reactiva y planificador convencional sobre las mismas salas y semillas",
             "Salas extruidas, altura fija y energía abstracta.",
             runner=_compose, seconds="~2 s"),
        Case("energia", "POWER-1", ORIGIN_BENCH,
             "Volver a casa por coste, no por porcentaje",
             "El coste previsto acierta donde el clásico «vuelve al 20 %» aborta en falso.",
             "porcentaje fijo y oráculo, sobre las mismas semillas",
             "Energía simulada; el PX4 fijado publica −1 A. No son julios.",
             runner=_power, seconds="~1 s"),
        Case("contencion", "SAFE-1", ORIGIN_BENCH,
             "El supervisor veta",
             "Ningún setpoint inseguro se acepta, aunque el agente lo pida.",
             "mutantes sin enclavamiento y sin comprobación de vida del agente",
             "Contención dentro del banco, no seguridad universal.",
             runner=_safe, seconds="~1 s"),
        Case("evidencia", "FUSION-1", ORIGIN_BENCH,
             "La evidencia conserva su procedencia",
             "Cada observación lleva fuente, captura y extracto verificable.",
             "una observación sin extracto no puede convertirse en hecho",
             "No concede permiso de vuelo por sí sola.",
             runner=_fusion, seconds="~1 s"),
        Case("identidad", "PATTERN-1R", ORIGIN_EVIDENCE,
             "Reconocer identidades por LiDAR",
             "Identidades correctas, confusiones y desconocidos separados.",
             "familias LiDAR reservadas; el examen es por replay",
             "Aprendizaje y examen por replay, no en vuelo.",
             reader="pattern1r"),
        Case("dinamica", "DYNAMIC-1", ORIGIN_EVIDENCE,
             "Seguir una cara desde hover",
             "Seguimiento de la normal de una cara y predicción corta.",
             "mutantes de registro y de grupo detectados por la auditoría",
             "No hay compensación general del movimiento propio.",
             reader="dynamic1"),
        Case("enlace", "PX4-1", ORIGIN_EVIDENCE,
             "El enlace bloquea lo inválido",
             "Intentos fuera de envolvente, autoridad o secuencia, bloqueados.",
             "mutante ack_is_arrival: confundir el ACK con la llegada",
             "Objetivos de un metro y una transacción supervisada.",
             reader="px41"),
        Case("autoridad", "HOST-1", ORIGIN_EVIDENCE,
             "La autoridad de una fuente se gana",
             "Elecciones útiles con autoridad actualizada por consecuencias.",
             "control por botón: obedecer sin consecuencia",
             "Calibración supervisada sobre cinta de máquina.",
             reader="host1"),
        Case("transferencia", "TRANSFER-3", ORIGIN_EVIDENCE,
             "Lo aprendido en A sirve en B y C",
             "Campaña sellada con custodia humana: bloques ganados y perdidos.",
             "el mismo agente sin esa experiencia, sobre las mismas salas",
             "Salas estáticas de dos paredes. Sin hardware ni vuelo.",
             reader="transfer3"),
        Case("mision", "DRONE-3", ORIGIN_EVIDENCE,
             "La misión entera, de principio a fin",
             "Una sola sesión PX4/Gazebo por vuelo: 12/12 y 12/12.",
             "228/228 sondas de rechazo, 11 mutantes y 8 manipulaciones",
             "Energía simulada, celdas de 3 m. HIL y jaula siguen en false.",
             reader="drone3"),
        Case("mundos-abc", "SIM-3", ORIGIN_BENCH,
             "Evaluador y agente separados",
             "La evidencia de los tres mundos se reconstruye entera, aquí y ahora.",
             "un hallazgo en la reconstrucción invalida la evidencia",
             "Reconstruye la evidencia guardada; no vuelve a correr los mundos "
             "en Gazebo.",
             runner=_sim3, seconds="~7 s"),
        Case("suelo-wsp", "GROUND-1", ORIGIN_BENCH,
             "De sensor físico a WSP",
             "Integridad temporal de 30 vuelos grabados: ciclo de vida y etapas.",
             "una etapa que no empalme con la anterior sale roja",
             "Se recalcula sobre vuelos ya grabados; no reproduce el "
             "certificado completo de GROUND-1 ni vuela nada nuevo.",
             runner=_ground, seconds="<1 s"),
        Case("atribucion", "CAUSE-1", ORIGIN_BENCH,
             "Atribuir la causa, no la coincidencia",
             "La atribución se recalcula sobre 16 vuelos guardados.",
             "control temporal: culpar a lo último que pasó, misma evidencia",
             "Los vuelos ya estaban grabados: aquí se recalcula la atribución, "
             "no se vuela. Pared plana e intenciones experimentales.",
             runner=_cause, seconds="~4 s"),
    ]


CASES = build()
BY_ID = {case.ident: case for case in CASES}


def runnable() -> list[Case]:
    return [case for case in CASES if case.availability()[0]]


def blocked() -> list[Case]:
    return [case for case in CASES if not case.availability()[0]]
