"""The A-v2 calibration: 64 flights plus negative controls, all published.

v1 chose its numbers from four episodes per level, and four was not
enough to bound the spread of a closed-loop outcome — the split-A minimum
was 455 mm and the full bench reached 292 mm. v2 measures 8 fresh
nominal and 8 fresh perturbed repeats in each of the four A worlds, plus
one negative control per world, in an order permuted by a new seed.

The rules that turn those numbers into the frozen protocol are in
``protocol.py`` and were written before this ran. Nothing here looks at
B or C, and nothing here looks at v1's outcomes to pick a threshold.

The calibration is also a gate. If the negative controls do not separate
cleanly, or the push does not take the body out of the band, or an
episode fails to recover, this stops and the red stands: B and C are not
flown.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.sim3.generate import SplitMix64
from echoai.nexus0.flight1s import mutants as v1mut
from echoai.nexus0.flight1s.session import run_episode
from echoai.nexus0.flight1s.v2 import evaluate as v2eval
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2.runtime import ECHOAI, Runtime

DEFAULT_OUTPUT = ECHOAI / "lab" / "flight1s-v2" / "calibration.json"
REPEATS_PER_WORLD = 8
CALIBRATION_ORDER_SEED = 20260911
ATTITUDE_CEILING_MDEG = 25000
BAND_ROUNDING_MM = 10


def episode_order(seed: int, n_pairs: int) -> List[str]:
    """A permuted sequence of paired conditions from a seed. Never adaptive."""
    rng = SplitMix64(seed)
    order: List[str] = []
    for _ in range(n_pairs):
        pair = ["nominal", "perturbed"]
        if rng.below(2):
            pair.reverse()
        order.extend(pair)
    return order


def _ceil_to(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def _stat(values: Sequence[float]) -> Optional[Dict]:
    vals = sorted(v for v in values if isinstance(v, (int, float)))
    if not vals:
        return None
    return {"n": len(vals), "min": vals[0], "p50": vals[len(vals) // 2],
            "max": vals[-1]}


def run(runtime: Runtime, packages: Sequence, *, output: Optional[Path] = None,
        log=print, repeats: int = REPEATS_PER_WORLD,
        force_mn: int = protomod.FORCE_MN) -> Dict:
    stub = protomod.calibration(force_mn)
    # A v1-shaped view for the shared evaluator while no protocol exists yet.
    shim = {
        "stages": stub["stages"], "body": stub["body"],
        "bands": {"recovery_radius_mm": protomod.V1_RECOVERY_RADIUS_MM,
                  "recovery_hold_ms": 3000, "recovery_timeout_ms": 10000,
                  "attitude_max_mdeg": ATTITUDE_CEILING_MDEG},
    }
    order = episode_order(CALIBRATION_ORDER_SEED, repeats)

    episodes: List[Dict] = []
    negatives: List[Dict] = []
    for gen in packages:
        for slot in range(repeats):
            for condition in order[slot * 2:slot * 2 + 2]:
                label = f"cal-{condition}-{gen.package_id}-r{slot + 1}"
                log(f"calibration {label}")
                ep = run_episode(runtime, gen.package, stub,
                                 condition=condition, label=label)
                m = v2eval.v1.episode_metrics(ep, shim, package=gen.package)
                m["package_id"] = gen.package_id
                m["repeat"] = slot + 1
                m["events"] = [e for e in ep.events
                               if e.get("ev", "").startswith("wrench")]
                m["wrench_published"] = ep.wrench_published
                episodes.append(m)
        label = f"cal-negative-{gen.package_id}"
        log(f"calibration {label} (force declared, wrench never published)")
        ep = run_episode(runtime, gen.package, stub, condition="perturbed",
                         label=label, runner_path=v1mut.NOFORCE)
        m = v2eval.v1.episode_metrics(ep, shim, package=gen.package)
        m["package_id"] = gen.package_id
        negatives.append(m)

    nominal = [m for m in episodes
               if m["condition"] == "nominal" and m["ok"]
               and m.get("status") == "measured"]
    perturbed = [m for m in episodes
                 if m["condition"] == "perturbed" and m["ok"]
                 and m.get("status") == "measured"]
    neg_ok = [m for m in negatives
              if m["ok"] and m.get("status") == "measured"]

    result: Dict = {
        "schema_version": 1,
        "scope": "flight_software_in_the_loop",
        "dataset_kind": "calibration",
        "protocol_version": 2,
        "split": "A",
        "order_seed": CALIBRATION_ORDER_SEED,
        "force_mn": force_mn,
        "repeats_per_world": repeats,
        "n_worlds": len(packages),
        "rules_fixed_before_running": {
            "recovery_radius_mm": f"max({protomod.V1_RECOVERY_RADIUS_MM}, "
                                  f"ceil(max nominal hover_horiz_max on A, "
                                  f"{protomod.RADIUS_ROUNDING_MM}))",
            "exit_margin_mm": "speed ceiling x sample interval ceiling, plus "
                              "the hover reference standard error, rounded up",
            "min_impulse_ratio_ppk": protomod.impulse_floor_ppk([])["rule"],
            "max_impulse_ratio_ppk": protomod.IMPULSE_CEILING_PPK,
            "gate": "negative controls must separate, every perturbed episode "
                    "must leave the band and recover, attitude within the "
                    "ceiling; otherwise stop and keep the red",
        },
        "episodes": episodes,
        "negative_controls": negatives,
        "counts": {"nominal": len(nominal), "perturbed": len(perturbed),
                   "negative": len(neg_ok),
                   "flown": len(episodes) + len(negatives)},
    }

    if not nominal or not perturbed:
        result["status"] = "not_run"
        result["reason"] = "not enough completed episodes to calibrate"
        dump_report(Path(output or DEFAULT_OUTPUT), result)
        return result

    envelope_mm = max(m["hover_horiz_max_mm"] for m in nominal)
    radius_mm = protomod.recovery_radius_mm(envelope_mm)
    margin = protomod.exit_margin_mm()
    threshold_mm = radius_mm + margin["exit_margin_mm"]

    neg_ratios = [m["impulse"]["ratio_ppk"] for m in neg_ok
                  if (m.get("impulse") or {}).get("ratio_ppk") is not None]
    floor = protomod.impulse_floor_ppk(neg_ratios)
    pos_ratios = [m["impulse"]["ratio_ppk"] for m in perturbed
                  if (m.get("impulse") or {}).get("ratio_ppk") is not None]

    excursions = [m["disturb_excursion_mm"] for m in perturbed]
    attitudes = [m["disturb_attitude_max_mdeg"] for m in perturbed]
    recovered = [m for m in perturbed
                 if (m.get("recovery") or {}).get("status") == "recovered"]
    nominal_excursions = [m["disturb_excursion_mm"] for m in nominal]

    per_world: Dict[str, Dict] = {}
    for gen in packages:
        pid = gen.package_id
        w_nom = [m for m in nominal if m["package_id"] == pid]
        w_per = [m for m in perturbed if m["package_id"] == pid]
        per_world[pid] = {
            "n_nominal": len(w_nom), "n_perturbed": len(w_per),
            "hover_horiz_max_mm": _stat([m["hover_horiz_max_mm"] for m in w_nom]),
            "hover_horiz_rms_mm": _stat([m["hover_horiz_rms_mm"] for m in w_nom]),
            "excursion_mm": _stat([m["disturb_excursion_mm"] for m in w_per]),
            "impulse_ppk": _stat([(m.get("impulse") or {}).get("ratio_ppk")
                                  for m in w_per]),
            "recovery_ms": _stat([(m.get("recovery") or {}).get("recovery_ms")
                                  for m in w_per]),
        }

    gate = {
        "all_episodes_completed": len(nominal) + len(perturbed)
                                  == len(packages) * repeats * 2,
        "negatives_measured": len(neg_ok) == len(packages),
        "negatives_below_floor": bool(
            neg_ratios and max(neg_ratios) < floor["min_impulse_ratio_ppk"]),
        "positives_inside_band": bool(
            pos_ratios
            and min(pos_ratios) >= floor["min_impulse_ratio_ppk"]
            and max(pos_ratios) <= protomod.IMPULSE_CEILING_PPK),
        "every_perturbed_left_the_band": bool(
            excursions and min(excursions) > threshold_mm),
        "no_nominal_left_the_band": bool(
            nominal_excursions and max(nominal_excursions) <= threshold_mm),
        "attitude_within_ceiling": bool(
            attitudes and max(attitudes) <= ATTITUDE_CEILING_MDEG),
        "every_perturbed_recovered": len(recovered) == len(perturbed),
    }
    passed = all(gate.values())

    result.update({
        "nominal_envelope_mm": envelope_mm,
        "recovery_radius_mm": radius_mm,
        "exit_margin": margin,
        "challenge_threshold_mm": threshold_mm,
        "impulse_floor": floor,
        "separation": {
            "negative_ratio_ppk": _stat(neg_ratios),
            "perturbed_ratio_ppk": _stat(pos_ratios),
            "gap_ppk": (min(pos_ratios) - max(neg_ratios))
                       if pos_ratios and neg_ratios else None,
        },
        "nominal": {
            "hover_horiz_rms_mm": _stat([m["hover_horiz_rms_mm"] for m in nominal]),
            "hover_horiz_max_mm": _stat([m["hover_horiz_max_mm"] for m in nominal]),
            "hover_vert_max_mm": _stat([m["hover_vert_max_mm"] for m in nominal]),
            "attitude_mdeg": _stat([m["hover_attitude_max_mdeg"] for m in nominal]),
            "excursion_mm": _stat(nominal_excursions),
        },
        "perturbed": {
            "excursion_mm": _stat(excursions),
            "attitude_mdeg": _stat(attitudes),
            "recovery_ms": _stat([(m.get("recovery") or {}).get("recovery_ms")
                                  for m in perturbed]),
        },
        "per_world": per_world,
        "gate": gate,
        "status": "chosen" if passed else "gate_failed",
    })

    if passed:
        result["bands"] = {
            "horiz_rms_mm": _ceil_to(
                max(m["hover_horiz_rms_mm"] for m in nominal), BAND_ROUNDING_MM),
            "horiz_max_mm": radius_mm,
            "vert_max_mm": _ceil_to(
                max(m["hover_vert_max_mm"] for m in nominal), BAND_ROUNDING_MM),
            "attitude_max_mdeg": ATTITUDE_CEILING_MDEG,
        }
        result["tolerances"] = {
            "paired_hover_rms_mm": _ceil_to(
                2 * max(m["hover_horiz_rms_mm"] for m in nominal),
                BAND_ROUNDING_MM),
            "paired_recovery_ms": 5000,
            "clock_drift_max_ms": 100,
        }
        result["stimulus"] = {
            "min_impulse_ratio_ppk": floor["min_impulse_ratio_ppk"],
            "max_impulse_ratio_ppk": protomod.IMPULSE_CEILING_PPK,
        }
    else:
        result["bands"] = None
        result["tolerances"] = None
        result["stimulus"] = None
        result["reason"] = "; ".join(k for k, v in gate.items() if not v)

    dump_report(Path(output or DEFAULT_OUTPUT), result)
    return result
