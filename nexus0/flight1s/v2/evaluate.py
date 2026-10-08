"""Three questions, three verdicts, three denominators.

v1 asked whether the body moved 400 mm and called the answer
"disturbance". That conflates the input with the controller's response,
and it punished PX4 for rejecting the push well. Here:

* :func:`stimulus` — was a physical input applied? One wrench, published
  once inside the window and withdrawn at its end, and a momentum change
  in the backend's own pose stream inside the frozen band. Displacement
  is not consulted.
* :func:`challenge` — did that input take the body out of the band from
  which recovery is later claimed? Excursion strictly beyond
  ``radius + exit_margin``, where the margin is measurement resolution.
* :func:`recovery` — did PX4 bring it back and hold it, measured only
  from the moment the wrench stopped, with the reference unchanged?

None of the three can pay for another. A run with a perfect impulse that
never left the band fails ``challenge``; a run that left the band and
stayed out fails ``recovery``; a run that recovered from a push that was
never applied fails ``stimulus``.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

from echoai.nexus0.flight1s import evaluate as v1
from echoai.nexus0.flight1s.session import Episode

COL = v1.COL


def _shim(protocol: Dict) -> Dict:
    """A v1-shaped view so the shared arithmetic stays the shared arithmetic."""
    return {
        "stages": protocol["stages"],
        "body": protocol["body"],
        "bands": {
            "recovery_radius_mm": protocol["recovery"]["radius_mm"],
            "recovery_hold_ms": protocol["recovery"]["hold_ms"],
            "recovery_timeout_ms": protocol["recovery"]["timeout_ms"],
            "attitude_max_mdeg": protocol["hover_bands"]["attitude_max_mdeg"],
        },
    }


def _plan(ep: Episode) -> Dict:
    return {name: (a, b) for name, a, b in (ep.stage_marks or {}).get("plan", [])}


def _wrench_events(ep: Episode) -> Dict:
    applied = [e for e in ep.events if e.get("ev") == "wrench_applied"]
    cleared = [e for e in ep.events if e.get("ev") == "wrench_cleared"]
    return {
        "applied": [int(e["sim_time_ns"]) for e in applied],
        "cleared": [int(e["sim_time_ns"]) for e in cleared],
    }


def stimulus(ep: Episode, metrics: Dict, protocol: Dict) -> Dict:
    """Question 1. Judged on the input, never on what survived it."""
    spec = protocol["stimulus"]
    disturb = protocol["disturbance"]
    plan = _plan(ep)
    out: Dict = {"label": ep.label, "condition": ep.condition}
    if ep.condition != "perturbed":
        out.update({"status": "not_applicable", "ok": True})
        return out
    if "disturb" not in plan:
        out.update({"status": "not_measured", "ok": False})
        return out

    db, de = plan["disturb"]
    events = _wrench_events(ep)
    imp = metrics.get("impulse") or {}
    ratio = imp.get("ratio_ppk")

    inside = [t for t in events["applied"] if db <= t <= de]
    cleared_at_end = [t for t in events["cleared"] if de <= t <= de + 200_000_000]
    out.update({
        "status": "measured",
        "wrench_publications": ep.wrench_published,
        "required_publications": disturb["publications"],
        "applied_ns": events["applied"],
        "cleared_ns": events["cleared"],
        "applied_inside_window": len(inside) == 1,
        "cleared_at_window_end": len(cleared_at_end) == 1,
        "force_n": ep.force_n,
        "commanded_impulse_mn_s": spec["commanded_impulse_mn_s"],
        "measured_impulse_mn_s": (int(round(imp["measured_n_s"] * 1000))
                                  if imp.get("measured_n_s") is not None else None),
        "impulse_ratio_ppk": ratio,
        "band_ppk": [spec["min_impulse_ratio_ppk"], spec["max_impulse_ratio_ppk"]],
        "measurement": spec["measurement"],
    })
    out["ok"] = bool(
        ep.ok
        and ep.wrench_published == disturb["publications"]
        and out["applied_inside_window"]
        and out["cleared_at_window_end"]
        and imp.get("status") == "measured"
        and ratio is not None
        and spec["min_impulse_ratio_ppk"] <= ratio <= spec["max_impulse_ratio_ppk"]
    )
    return out


def challenge(ep: Episode, metrics: Dict, protocol: Dict) -> Dict:
    """Question 2. Did the input actually take it out of the band?"""
    spec = protocol["challenge"]
    threshold = int(spec["recovery_radius_mm"]) + int(spec["exit_margin_mm"])
    out: Dict = {"label": ep.label, "condition": ep.condition,
                 "threshold_mm": threshold,
                 "radius_mm": spec["recovery_radius_mm"],
                 "exit_margin_mm": spec["exit_margin_mm"]}
    excursion = metrics.get("disturb_excursion_mm")
    out["excursion_mm"] = excursion
    if ep.condition != "perturbed":
        # For the paired control the same number is reported and the
        # expectation is the opposite: it must stay inside.
        out.update({"status": "control",
                    "stayed_inside": excursion is not None
                                     and excursion <= threshold,
                    "ok": excursion is not None and excursion <= threshold})
        return out
    if excursion is None:
        out.update({"status": "not_measured", "ok": False})
        return out
    out.update({"status": "measured", "left_band": excursion > threshold,
                "margin_beyond_mm": round(excursion - threshold, 3),
                "ok": bool(ep.ok and excursion > threshold)})
    return out


def recovery(ep: Episode, metrics: Dict, protocol: Dict) -> Dict:
    """Question 3. Measured only after the wrench stops."""
    spec = protocol["recovery"]
    plan = _plan(ep)
    out: Dict = {"label": ep.label, "condition": ep.condition,
                 "radius_mm": spec["radius_mm"], "hold_ms": spec["hold_ms"],
                 "timeout_ms": spec["timeout_ms"]}
    if ep.condition != "perturbed":
        out.update({"status": "not_applicable", "ok": True})
        return out
    if "disturb" not in plan:
        out.update({"status": "not_measured", "ok": False})
        return out
    _, de = plan["disturb"]
    rec = metrics.get("recovery") or {}
    out.update({
        "status": rec.get("status", "not_measured"),
        "recovery_ms": rec.get("recovery_ms"),
        "final_offset_mm": rec.get("final_offset_mm"),
        "measured_from_ns": de,
        "measured_from": spec["measured_from"],
    })
    out["ok"] = bool(
        ep.ok and rec.get("status") == "recovered"
        and rec.get("recovery_ms") is not None
        and rec["recovery_ms"] <= spec["timeout_ms"])
    return out


def episode_metrics(ep: Episode, protocol: Dict, package=None) -> Dict:
    """Everything v1 measured, plus the three separated verdicts."""
    shim = _shim(protocol)
    m = v1.episode_metrics(ep, shim, package=package)
    m["stimulus"] = stimulus(ep, m, protocol)
    m["challenge"] = challenge(ep, m, protocol)
    m["recovery_verdict"] = recovery(ep, m, protocol)
    m["protocol_version"] = 2
    return m


def hover_within_bands(metrics: Dict, protocol: Dict) -> Dict:
    """The hover bands are descriptive here; they gate nothing on their own."""
    bands = protocol["hover_bands"]
    return {
        "horiz_rms_mm": metrics.get("hover_horiz_rms_mm"),
        "horiz_max_mm": metrics.get("hover_horiz_max_mm"),
        "vert_max_mm": metrics.get("hover_vert_max_mm"),
        "attitude_max_mdeg": metrics.get("hover_attitude_max_mdeg"),
        "bands": bands,
        "within": bool(
            (metrics.get("hover_horiz_rms_mm") or 0) <= bands["horiz_rms_mm"]
            and (metrics.get("hover_horiz_max_mm") or 0) <= bands["horiz_max_mm"]
            and (metrics.get("hover_vert_max_mm") or 0) <= bands["vert_max_mm"]
            and (metrics.get("hover_attitude_max_mdeg") or 0)
                <= bands["attitude_max_mdeg"]),
    }
