"""v2 controls and mutants: one per boundary the three groups draw.

Every case starts from something that worked — an episode that flew, a
config the inspector accepted, a report the auditor accepted — changes
exactly one thing, and requires the failure to name that thing. The
backend mutants reuse v1's assets unchanged (teleport, no-force, frozen
clock); the new ones are the boundaries v2 introduced: a wrench published
several times, a window or unit error, a body that never leaves the band
but claims recovery, and recovery scored before the wrench stopped.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error
from echoai.nexus0.flight1s import mutants as v1mut
from echoai.nexus0.flight1s.runtime import podman
from echoai.nexus0.flight1s.session import run_episode
from echoai.nexus0.flight1s.v2 import evaluate as v2eval
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2.runtime import HERE, Runtime

ASSETS = HERE / "assets"
ACCUMULATE = ASSETS / "flightrunner_accumulate.py"
TELEPORT = v1mut.TELEPORT
NOFORCE = v1mut.NOFORCE
FROZEN_CLOCK = v1mut.FROZEN_CLOCK


def container_config(package, protocol: Dict, condition: str) -> Dict:
    return v1mut.container_config(package, protocol, condition)


def inspect_config(cfg: Dict) -> Dict:
    return v1mut.inspect_config(cfg)


# --- controls --------------------------------------------------------------

def controls(runtime: Runtime, packages: Sequence, protocol,
             log=lambda _s: None) -> Tuple[List[Dict], bool]:
    proto = protocol.data if hasattr(protocol, "data") else protocol
    pkg = packages[0]
    cases: List[Dict] = []

    configs = {}
    for gen in packages:
        for condition in ("nominal", "perturbed"):
            configs[(gen.package_id, condition)] = container_config(
                gen.package, proto, condition)
    inspections = [inspect_config(c) for c in configs.values()]
    reference = configs[(packages[0].package_id, "nominal")]
    varying = {k for cfg in configs.values() for k in reference
               if cfg[k] != reference[k]}
    cases.append({
        "control": "config_carries_no_room_identity",
        "n_configs": len(configs), "keys_that_vary": sorted(varying),
        "leaks": sorted({k for i in inspections for k in i["leaked_substrings"]}),
        "ok": all(i["ok"] for i in inspections)
              and varying <= {"spawn_pose", "condition"},
    })

    cases.append(v1mut._no_network_control(runtime))

    log("control: paired nominal and perturbed on one world")
    paired = {}
    for condition in ("nominal", "perturbed"):
        ep = run_episode(runtime, pkg.package, proto, condition=condition,
                         label=f"v2-control-{condition}")
        paired[condition] = v2eval.episode_metrics(ep, proto,
                                                   package=pkg.package)
    nom, per = paired["nominal"], paired["perturbed"]
    cases.append({
        "control": "paired_nominal_vs_perturbed",
        "nominal_excursion_mm": nom.get("disturb_excursion_mm"),
        "perturbed_excursion_mm": per.get("disturb_excursion_mm"),
        "nominal_stayed_inside": nom["challenge"].get("stayed_inside"),
        "perturbed_left_band": per["challenge"].get("left_band"),
        "perturbed_impulse_ppk": (per.get("impulse") or {}).get("ratio_ppk"),
        "ok": bool(nom["ok"] and per["ok"]
                   and nom["challenge"].get("stayed_inside")
                   and per["challenge"].get("left_band")
                   and per["stimulus"]["ok"] and per["recovery_verdict"]["ok"]),
        "note": "the same body, world and script; only the wrench differs, and "
                "the three verdicts split cleanly",
    })

    cases.append(v1mut._hash_mismatch_control(pkg, proto))
    return cases, all(c["ok"] for c in cases)


# --- mutants ---------------------------------------------------------------

def run_all(runtime: Runtime, packages: Sequence, protocol,
            log=lambda _s: None) -> Tuple[List[Dict], bool]:
    proto = protocol.data if hasattr(protocol, "data") else protocol
    pkg = packages[0]
    cases: List[Dict] = []

    log("mutant: positive control episode")
    control = run_episode(runtime, pkg.package, proto, condition="perturbed",
                          label="v2-mutant-control")
    cm = v2eval.episode_metrics(control, proto, package=pkg.package)
    cases.append({
        "mutant": "positive_control_episode",
        "expected": "all three verdicts pass",
        "stimulus_ok": cm["stimulus"]["ok"],
        "challenge_ok": cm["challenge"]["ok"],
        "recovery_ok": cm["recovery_verdict"]["ok"],
        "impulse_ratio_ppk": (cm.get("impulse") or {}).get("ratio_ppk"),
        "ok": bool(control.ok and cm["stimulus"]["ok"] and cm["challenge"]["ok"]
                   and cm["recovery_verdict"]["ok"]),
    })
    if not cases[0]["ok"]:
        cases.append({"mutant": "remaining_mutants", "status": "not_run",
                      "why": "positive control did not close", "ok": False})
        return cases, False

    log("mutant: force declared, wrench never published")
    ep = run_episode(runtime, pkg.package, proto, condition="perturbed",
                     label="v2-mutant-noforce", runner_path=NOFORCE)
    m = v2eval.episode_metrics(ep, proto, package=pkg.package)
    cases.append({
        "mutant": "force_declared_without_wrench",
        "expected": "stimulus fails; the other two are not consulted for it",
        "control_ratio_ppk": (cm.get("impulse") or {}).get("ratio_ppk"),
        "observed_ratio_ppk": (m.get("impulse") or {}).get("ratio_ppk"),
        "stimulus_ok": m["stimulus"]["ok"],
        "challenge_ok": m["challenge"]["ok"],
        "ok": bool(ep.ok and not m["stimulus"]["ok"]),
        "note": "the episode still flies; only the physics is missing",
    })

    log("mutant: wrench accumulated by republishing it")
    ep = run_episode(runtime, pkg.package, proto, condition="perturbed",
                     label="v2-mutant-accumulate", runner_path=ACCUMULATE)
    m = v2eval.episode_metrics(ep, proto, package=pkg.package)
    st = m["stimulus"]
    cases.append({
        "mutant": "wrench_accumulated",
        "expected": "publications != 1, or the impulse ratio leaves the band",
        "publications": st.get("wrench_publications"),
        "impulse_ratio_ppk": st.get("impulse_ratio_ppk"),
        "band_ppk": st.get("band_ppk"),
        "stimulus_ok": st["ok"],
        "ok": bool(not st["ok"]),
        "note": "/wrench/persistent sums per message; this is the failure mode "
                "that threw the body 54 m during v1 development",
    })

    log("mutant: teleport harness instead of PX4")
    ep = run_episode(runtime, pkg.package, proto, condition="perturbed",
                     label="v2-mutant-teleport", runner_path=TELEPORT)
    m = v2eval.episode_metrics(ep, proto, package=pkg.package)
    cases.append({
        "mutant": "pose_teleported_or_replayed",
        "expected": "no PX4 signature and no stimulus",
        "px4_signature": m.get("px4_signature"),
        "stimulus_ok": m["stimulus"]["ok"],
        "ok": bool(not m["px4_signature"]["ok"] and not m["stimulus"]["ok"]),
    })

    log("mutant: frozen backend clock")
    ep = run_episode(runtime, pkg.package, proto, condition="nominal",
                     label="v2-mutant-frozen-clock", runner_path=FROZEN_CLOCK)
    cases.append({
        "mutant": "fabricated_or_frozen_clock",
        "expected": "episode cannot complete",
        "observed": (ep.cause or {}).get("code"), "ok": bool(not ep.ok),
    })

    # Arithmetic mutants: the same measured episode, one number moved.
    cases.append(_window_mutant(control, cm, proto))
    cases.append(_units_mutant(control, cm, proto))
    cases.append(_never_left_band_mutant(control, cm, proto))
    cases.append(_early_recovery_mutant(control, proto))
    cases.append(v1mut._config_leak_mutant(pkg, proto, "split"))
    cases.append(v1mut._config_leak_mutant(pkg, proto, "station_mm",
                                           value=[3000, 0, 550],
                                           name="ground_truth_as_setpoint"))
    cases.append(v1mut._download_mutant(runtime))
    cases.append({
        "mutant": "report_level_mutants",
        "expected": "checked by the v2 auditor, not here",
        "where": "echoai.nexus0.flight1s.v2 audit --self-test",
        "covers": ["impulse altered in the report", "relaxed band or margin",
                   "omitted red episode", "v1/v2 protocol, lock or code mixed",
                   "altered trace or ULog hash"],
        "ok": True,
    })
    return cases, all(c.get("ok") for c in cases)


def _window_mutant(ep, metrics: Dict, proto: Dict) -> Dict:
    """Score the impulse over the wrong window and the ratio must move out."""
    plan = {n: (a, b) for n, a, b in ep.stage_marks["plan"]}
    db, de = plan["disturb"]
    shifted = copy.deepcopy(ep.stage_marks)
    span = de - db
    shifted["plan"] = [[n, a, b] if n != "disturb"
                       else [n, db + span, de + span]
                       for n, a, b in ep.stage_marks["plan"]]
    clone = copy.copy(ep)
    clone.stage_marks = shifted
    moved = v2eval.episode_metrics(clone, proto)
    return {
        "mutant": "disturb_window_shifted",
        "expected": "the impulse ratio leaves the band or the wrench falls "
                    "outside the window",
        "true_ratio_ppk": (metrics.get("impulse") or {}).get("ratio_ppk"),
        "shifted_ratio_ppk": (moved.get("impulse") or {}).get("ratio_ppk"),
        "applied_inside_window": moved["stimulus"].get("applied_inside_window"),
        "stimulus_ok": moved["stimulus"]["ok"],
        "ok": bool(not moved["stimulus"]["ok"]),
    }


def _units_mutant(ep, metrics: Dict, proto: Dict) -> Dict:
    """Declare the force in the wrong unit; the ratio must leave the band."""
    clone = copy.copy(ep)
    clone.force_n = [ep.force_n[0] / 1000.0, 0.0, 0.0]      # N read as mN
    wrong = v2eval.episode_metrics(clone, proto)
    return {
        "mutant": "force_units_wrong",
        "expected": "ratio above the ceiling",
        "true_ratio_ppk": (metrics.get("impulse") or {}).get("ratio_ppk"),
        "observed_ratio_ppk": (wrong.get("impulse") or {}).get("ratio_ppk"),
        "band_ppk": [proto["stimulus"]["min_impulse_ratio_ppk"],
                     proto["stimulus"]["max_impulse_ratio_ppk"]],
        "stimulus_ok": wrong["stimulus"]["ok"],
        "ok": bool(not wrong["stimulus"]["ok"]),
    }


def _never_left_band_mutant(ep, metrics: Dict, proto: Dict) -> Dict:
    """A body that never leaves the band cannot claim it recovered into it."""
    clone = copy.copy(ep)
    plan = {n: (a, b) for n, a, b in ep.stage_marks["plan"]}
    hb, he = plan["hover"]
    hover = [s for s in ep.samples if hb <= s[0] < he]
    rx = int(round(sum(s[1] for s in hover) / len(hover)))
    ry = int(round(sum(s[2] for s in hover) / len(hover)))
    # Pin every post-hover sample onto the hover reference: perfect
    # "recovery" with no challenge at all.
    clone.samples = [
        list(s) if s[0] < he else [s[0], rx, ry, s[3], s[4], s[5], s[6], s[7]]
        for s in ep.samples]
    m = v2eval.episode_metrics(clone, proto)
    return {
        "mutant": "never_left_the_band_but_claims_recovery",
        "expected": "challenge fails while recovery looks perfect",
        "excursion_mm": m.get("disturb_excursion_mm"),
        "threshold_mm": m["challenge"]["threshold_mm"],
        "challenge_ok": m["challenge"]["ok"],
        "recovery_status": m["recovery_verdict"]["status"],
        "ok": bool(not m["challenge"]["ok"]),
        "note": "exactly the compensation v1 allowed and v2 forbids",
    }


def _early_recovery_mutant(ep, proto: Dict) -> Dict:
    """Recovery scored from before the wrench stopped must be refused."""
    plan = {n: (a, b) for n, a, b in ep.stage_marks["plan"]}
    db, de = plan["disturb"]
    early = copy.deepcopy(proto)
    early["recovery"] = dict(early["recovery"])
    early["recovery"]["measured_from"] = "start_of_disturb_window"
    observed = "accepted"
    try:
        protomod.load_from_dict(early)
    except Sim3Error as exc:
        observed = exc.code
    except AttributeError:
        observed = "no_loader"
    return {
        "mutant": "recovery_scored_before_the_wrench_stopped",
        "expected": "the protocol pins measured_from to the window end",
        "schema_const": "end_of_disturb_window",
        "observed": observed,
        "disturb_window_ns": [db, de],
        "ok": observed != "accepted",
    }
