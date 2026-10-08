"""The split-A calibration sweep, published in full.

The disturbance magnitude and the bands are the only numbers in
FLIGHT-1S that are chosen rather than declared, and choosing them on B or
C would consume those partitions. So they are chosen here, on split A
only, and everything the sweep saw — including the levels that were
rejected — is written to ``lab/flight1s/sweep.json`` and stays there.

The rules are fixed before the sweep runs, so the choice is mechanical:

* the recovery radius is the envelope the *undisturbed* vehicle occupies
  on A, rounded up. "Recovered" then means "back inside the space it
  would have occupied anyway", which is the only meaning that is not
  arbitrary;
* an admissible force must push the body clearly outside that envelope —
  at least twice the radius — and must not tip it past the attitude
  ceiling or end the episode on the ground;
* among the admissible levels, the smallest is taken. A bigger shove
  makes a prettier number and a weaker test.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.flight1s import evaluate
from echoai.nexus0.flight1s.protocol import calibration
from echoai.nexus0.flight1s.runtime import ECHOAI, Runtime
from echoai.nexus0.flight1s.session import run_episode

DEFAULT_OUTPUT = ECHOAI / "lab" / "flight1s" / "sweep.json"
FORCE_LEVELS_MN = (1000, 2000, 3000, 4000)
# Round 1 swept 1-4 N and found nothing admissible: the strongest level
# still moved the quietest A world only 303 mm, short of 2 x 200 mm. The
# rule was not touched — the candidate range was too narrow, so it was
# extended upward and round 1 is kept in lab/flight1s/sweep-round1-1to4N.json.
FORCE_LEVELS_EXTENDED_MN = (5000, 6000, 8000)
ATTITUDE_CEILING_MDEG = 25000        # 25 deg: past this it is a tumble, not a push
EXCURSION_FACTOR = 2                 # excursion must clear 2x the nominal envelope


def _ceil_to(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def run(runtime: Runtime, packages: Sequence, protocol_stub: Dict, *,
        output: Optional[Path] = None, log=print,
        force_levels: Sequence[int] = FORCE_LEVELS_MN,
        previous: Optional[Dict] = None) -> Dict:
    """Fly split A nominal, then each force level, and pick from the result.

    ``previous`` continues an earlier round: its nominal episodes and its
    radius are reused unchanged and its levels are carried forward, so a
    round that found nothing admissible stays in the record instead of
    being replaced by the one that did.
    """
    if previous is not None:
        nominal = list(previous["nominal_episodes"])
        radius_mm = int(previous["recovery_radius_mm"])
        envelope_mm = float(previous["nominal_envelope_mm"])
        carried = list(previous["levels"])
        log(f"continuing sweep: radius {radius_mm} mm from the previous round, "
            f"{len(carried)} levels carried forward")
    else:
        nominal = []
        carried = []
        for gen in packages:
            for repeat in (1, 2):
                label = f"sweep-nominal-{gen.package_id}-r{repeat}"
                log(f"sweep {label}")
                ep = run_episode(runtime, gen.package, protocol_stub,
                                 condition="nominal", label=label)
                nominal.append(evaluate.episode_metrics(ep, protocol_stub))
        radius_mm = None
        envelope_mm = None

    ok_nominal = [m for m in nominal if m.get("status") == "measured" and m["ok"]]
    if not ok_nominal:
        return {"status": "not_run", "reason": "no nominal episode completed",
                "nominal": nominal}
    if radius_mm is None:
        envelope_mm = max(m["hover_horiz_max_mm"] for m in ok_nominal)
        radius_mm = _ceil_to(envelope_mm, 50)
        log(f"nominal horizontal envelope {envelope_mm:.1f} mm -> "
            f"radius {radius_mm} mm")

    levels: List[Dict] = list(carried)
    for force_mn in force_levels:
        results = []
        for gen in packages:
            label = f"sweep-{force_mn}mN-{gen.package_id}"
            log(f"sweep {label}")
            ep = run_episode(runtime, gen.package, protocol_stub,
                             condition="perturbed", label=label,
                             force_mn=force_mn)
            results.append(evaluate.episode_metrics(ep, protocol_stub))
        measured = [m for m in results
                    if m.get("status") == "measured" and m["ok"]]
        entry = {
            "force_mn": force_mn,
            "n": len(results),
            "n_measured": len(measured),
            "episodes": results,
        }
        if measured:
            entry.update({
                "excursion_min_mm": min(m["disturb_excursion_mm"] for m in measured),
                "excursion_max_mm": max(m["disturb_excursion_mm"] for m in measured),
                "attitude_max_mdeg": max(m["disturb_attitude_max_mdeg"]
                                         for m in measured),
                "impulse_ratio_ppk": [m["impulse"].get("ratio_ppk")
                                      for m in measured],
            })
            entry["admissible"] = bool(
                len(measured) == len(results)
                and entry["excursion_min_mm"] >= EXCURSION_FACTOR * radius_mm
                and entry["attitude_max_mdeg"] <= ATTITUDE_CEILING_MDEG)
            entry["why"] = _why(entry, radius_mm)
        else:
            entry["admissible"] = False
            entry["why"] = "no episode completed at this level"
        levels.append(entry)
        log(f"  {force_mn} mN admissible={entry['admissible']} ({entry['why']})")

    levels.sort(key=lambda e: e["force_mn"])
    admissible = [e for e in levels if e["admissible"]]
    chosen = min(admissible, key=lambda e: e["force_mn"]) if admissible else None

    bands = None
    tolerances = None
    if chosen is not None:
        bands = {
            "hover_horiz_rms_mm": _ceil_to(
                max(m["hover_horiz_rms_mm"] for m in ok_nominal), 10),
            "hover_horiz_max_mm": radius_mm,
            "hover_vert_max_mm": _ceil_to(
                max(m["hover_vert_max_mm"] for m in ok_nominal), 10),
            "attitude_max_mdeg": ATTITUDE_CEILING_MDEG,
            "recovery_radius_mm": radius_mm,
            "recovery_hold_ms": 3000,
            "recovery_timeout_ms": 10000,
            "min_disturb_excursion_mm": EXCURSION_FACTOR * radius_mm,
        }
        tolerances = {
            "paired_hover_rms_mm": _ceil_to(
                2 * max(m["hover_horiz_rms_mm"] for m in ok_nominal), 10),
            "paired_recovery_ms": 5000,
            "clock_drift_max_ms": 100,
        }

    report = {
        "schema_version": 1,
        "scope": "flight_software_in_the_loop",
        "dataset_kind": "calibration",
        "split": "A",
        "rules_fixed_before_running": {
            "recovery_radius": "ceil(max nominal hover_horiz_max over A, 50 mm)",
            "admissible_force": f"excursion >= {EXCURSION_FACTOR} x radius in "
                                f"every A world, attitude <= "
                                f"{ATTITUDE_CEILING_MDEG} mdeg, all episodes complete",
            "choice": "smallest admissible level",
        },
        "rounds": (previous.get("rounds", []) if previous else []) + [
            {"force_levels_mn": list(force_levels),
             "kept_as": str(output or DEFAULT_OUTPUT)}],
        "previous_round_artifact": (
            "lab/flight1s/sweep-round1-1to4N.json" if previous else None),
        "nominal_episodes": nominal,
        "nominal_envelope_mm": envelope_mm,
        "recovery_radius_mm": radius_mm,
        "levels": levels,
        "chosen_force_mn": chosen["force_mn"] if chosen else None,
        "bands": bands,
        "tolerances": tolerances,
        "status": "chosen" if chosen else "no_admissible_level",
        "note": "Calibration only. Nothing here is a FLIGHT-1S result, and no "
                "B or C world was flown to produce it.",
    }
    dump_report(Path(output or DEFAULT_OUTPUT), report)
    return report


def _why(entry: Dict, radius_mm: int) -> str:
    if entry["n_measured"] != entry["n"]:
        return f"only {entry['n_measured']}/{entry['n']} episodes completed"
    if entry["excursion_min_mm"] < EXCURSION_FACTOR * radius_mm:
        return (f"excursion {entry['excursion_min_mm']:.0f} mm below "
                f"{EXCURSION_FACTOR} x {radius_mm} mm")
    if entry["attitude_max_mdeg"] > ATTITUDE_CEILING_MDEG:
        return (f"attitude {entry['attitude_max_mdeg']} mdeg above "
                f"{ATTITUDE_CEILING_MDEG} mdeg")
    return "clears the envelope without tumbling"
