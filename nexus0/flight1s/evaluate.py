"""The evaluator: integers in, verdicts out, nothing back to the vehicle.

Everything here reads private truth — the backend's pose stream, the
stage marks, the applied force — and turns it into millimetres,
millidegrees and milliseconds. It never writes to the driver, never
reaches PX4, and never fills in a quantity it did not observe.

Two measurements carry the weight of the slice.

*The hover reference is what the vehicle actually held*, taken as the
mean position over the hover window, and the steadiness is measured
about that. Where it settled relative to the commanded 1.5 m is reported
separately, as its own number, so a bias cannot hide inside a spread.

*The impulse ratio* is how we know a force was applied rather than
declared. The change in the body's momentum over the disturbance window,
computed from the backend's own pose stream, divided by F·Δt. A wrench
that was announced but never published gives roughly zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.flight1s.session import Episode

MASS_G = 2064          # x500_base: 2.0 kg body + 4 x 16.077 g rotors
COL = {"t": 0, "x": 1, "y": 2, "z": 3, "roll": 4, "pitch": 5, "yaw": 6, "w": 7}


@dataclass
class Verdict:
    ok: bool = True
    failures: List[str] = field(default_factory=list)
    measured: Dict = field(default_factory=dict)

    def fail(self, why: str) -> None:
        self.ok = False
        self.failures.append(why)


def _window(samples: Sequence[Sequence[int]], lo: int, hi: int) -> List[Sequence[int]]:
    return [s for s in samples if lo <= s[COL["t"]] < hi]


def _mean(values: Sequence[int]) -> int:
    return int(round(sum(values) / len(values))) if values else 0


def _radial_um(sample: Sequence[int], ref: Tuple[int, int]) -> float:
    return math.hypot(sample[COL["x"]] - ref[0], sample[COL["y"]] - ref[1])


def _velocity_x_mm_s(a: Sequence[int], b: Sequence[int]) -> Optional[float]:
    dt_ns = b[COL["t"]] - a[COL["t"]]
    if dt_ns <= 0:
        return None
    return (b[COL["x"]] - a[COL["x"]]) / 1000.0 / (dt_ns / 1e9)


def _px4_signature(ep: Episode) -> Dict:
    """Did PX4 actually fly this, or did something move the body?

    Three things a real episode has and a harness does not: a flight log
    that PX4 itself wrote, the driver's own arm and mode-switch events,
    and PX4's console saying it armed. A teleport harness can fake a pose
    trace; faking all of these means running PX4.
    """
    events = {e.get("event") for e in ep.driver_events}
    console = " ".join(ep.px4_tail)
    return {
        "ulog_present": bool(ep.ulog_sha256) and ep.ulog_bytes > 100_000,
        "ulog_bytes": ep.ulog_bytes,
        "driver_armed": "armed" in events,
        "driver_mode_switch": "mode_auto_takeoff" in events,
        "px4_console_armed": "Armed by external command" in console,
        "ok": bool(ep.ulog_sha256 and ep.ulog_bytes > 100_000
                   and "armed" in events and "mode_auto_takeoff" in events),
    }


def _collisions(samples, package, protocol: Dict, plan: Dict) -> Dict:
    """Did the envelope ever touch something it was not allowed to touch?

    Recomputed from the backend's pose stream against the world's own
    boxes, so a report that omits a collision does not remove it. Ground
    contact with the floor is authorised before the climb and inside the
    landing window; a barrier or the station is never authorised.
    """
    if package is None:
        return {"status": "not_measured"}
    radius_um = int(protocol["body"]["envelope_radius_mm"]) * 1000
    climb_begin = plan["climb"][0]
    recover_end = plan["recover"][1]
    hits = []
    for model in package.sdf.models:
        role = package.roles[model.name]
        if role == "floor":
            continue
        box = model.aabb
        for sample in samples:
            t = sample[COL["t"]]
            if not (climb_begin <= t <= recover_end):
                continue
            if not box.intersects_xy_disc(sample[COL["x"]] // 1000,
                                          sample[COL["y"]] // 1000,
                                          radius_um // 1000):
                continue
            z_mm = sample[COL["z"]] // 1000
            if box.lo[2] - 200 <= z_mm <= box.hi[2] + 200:
                hits.append({"model": model.name, "role": role,
                             "sim_time_ns": t})
                break
    return {"status": "measured", "unauthorised": len(hits), "hits": hits[:5],
            "window": [climb_begin, recover_end],
            "source": "backend pose stream against the world AABBs"}


def episode_metrics(ep: Episode, protocol: Dict, package=None) -> Dict:
    """Everything the report says about one episode, in integers."""
    out: Dict = {"label": ep.label, "condition": ep.condition, "ok": ep.ok,
                 "cause": ep.cause}
    samples = ep.samples
    marks = ep.stage_marks or {}
    plan = {name: (a, b) for name, a, b in marks.get("plan", [])}
    if not samples or not plan:
        out["status"] = "not_measured"
        return out

    stages = protocol["stages"]
    rest_z = int(marks.get("rest_z_um", 0))
    commanded_z = rest_z + int(stages["takeoff_alt_mm"]) * 1000

    hb, he = plan["hover"]
    hover = _window(samples, hb, he)
    if not hover:
        out["status"] = "not_measured"
        return out
    ref = (_mean([s[COL["x"]] for s in hover]),
           _mean([s[COL["y"]] for s in hover]),
           _mean([s[COL["z"]] for s in hover]))

    horiz = [_radial_um(s, (ref[0], ref[1])) for s in hover]
    vert = [abs(s[COL["z"]] - ref[2]) for s in hover]
    out.update({
        "rest_z_um": rest_z,
        "commanded_z_um": commanded_z,
        "hover_ref_um": list(ref),
        "hover_alt_offset_mm": round((ref[2] - commanded_z) / 1000.0, 3),
        "hover_horiz_rms_mm": round(
            math.sqrt(sum(v * v for v in horiz) / len(horiz)) / 1000.0, 3),
        "hover_horiz_max_mm": round(max(horiz) / 1000.0, 3),
        "hover_vert_rms_mm": round(
            math.sqrt(sum(v * v for v in vert) / len(vert)) / 1000.0, 3),
        "hover_vert_max_mm": round(max(vert) / 1000.0, 3),
        "hover_attitude_max_mdeg": max(
            max(abs(s[COL["roll"]]) for s in hover),
            max(abs(s[COL["pitch"]]) for s in hover)),
        "hover_samples": len(hover),
    })

    db, de = plan["disturb"]
    rb, re = plan["recover"]
    after = _window(samples, db, re)
    if after:
        excursion = max(_radial_um(s, (ref[0], ref[1])) for s in after)
        out["disturb_excursion_mm"] = round(excursion / 1000.0, 3)
        out["disturb_attitude_max_mdeg"] = max(
            max(abs(s[COL["roll"]]) for s in after),
            max(abs(s[COL["pitch"]]) for s in after))
        out["disturb_vert_max_mm"] = round(
            max(abs(s[COL["z"]] - ref[2]) for s in after) / 1000.0, 3)
        speeds = []
        for i in range(len(after) - 1):
            v = _velocity_x_mm_s(after[i], after[i + 1])
            if v is not None:
                speeds.append(v)
        out["max_speed_x_mm_s"] = round(max(speeds), 1) if speeds else None

    out["impulse"] = _impulse(samples, db, de, ep.force_n)
    out["recovery"] = _recovery(samples, ref, de, re, protocol)
    out["timing"] = _timing(ep, samples, marks)
    out["px4_signature"] = _px4_signature(ep)
    out["collisions"] = _collisions(samples, package, protocol, plan)
    out["wrench_published"] = ep.wrench_published
    out["force_n"] = ep.force_n
    out["ulog_sha256"] = ep.ulog_sha256
    out["ulog_bytes"] = ep.ulog_bytes
    out["status"] = "measured"
    return out


def _impulse(samples, db: int, de: int, force_n: Sequence[float]) -> Dict:
    """Δ(m·v) over the disturbance window against F·Δt, in integers."""
    fx = float(force_n[0]) if force_n else 0.0
    dt_s = (de - db) / 1e9
    expected = fx * dt_s
    pre = _window(samples, db - 300_000_000, db)
    post = _window(samples, db, de + 300_000_000)
    if len(pre) < 3 or len(post) < 3:
        return {"status": "not_measured"}
    v_before = _velocity_x_mm_s(pre[0], pre[-1])
    peaks = []
    for i in range(len(post) - 1):
        v = _velocity_x_mm_s(post[i], post[i + 1])
        if v is not None:
            peaks.append(v)
    if v_before is None or not peaks:
        return {"status": "not_measured"}
    v_peak = max(peaks)
    delta_p = (v_peak - v_before) / 1000.0 * (MASS_G / 1000.0)
    return {
        "status": "measured",
        "expected_n_s": round(expected, 4),
        "measured_n_s": round(delta_p, 4),
        "ratio_ppk": int(round(1000 * delta_p / expected)) if expected else None,
        "v_before_mm_s": round(v_before, 1),
        "v_peak_mm_s": round(v_peak, 1),
        "mass_g": MASS_G,
        "source": "finite difference of the backend pose stream",
    }


def _recovery(samples, ref, de: int, re: int, protocol: Dict) -> Dict:
    """First moment after the wrench stops from which it stays inside R."""
    bands = protocol.get("bands")
    if not bands:
        return {"status": "not_measured", "why": "no frozen bands"}
    radius_um = int(bands["recovery_radius_mm"]) * 1000
    hold_ns = int(bands["recovery_hold_ms"]) * 1_000_000
    tail = _window(samples, de, re + 1)
    if not tail:
        return {"status": "not_measured"}
    for i, sample in enumerate(tail):
        if _radial_um(sample, (ref[0], ref[1])) > radius_um:
            continue
        held = True
        for later in tail[i:]:
            if later[COL["t"]] - sample[COL["t"]] > hold_ns:
                break
            if _radial_um(later, (ref[0], ref[1])) > radius_um:
                held = False
                break
        else:
            held = tail[-1][COL["t"]] - sample[COL["t"]] >= hold_ns
        if held:
            return {"status": "recovered",
                    "recovery_ms": int((sample[COL["t"]] - de) / 1_000_000),
                    "radius_mm": bands["recovery_radius_mm"],
                    "hold_ms": bands["recovery_hold_ms"]}
    return {"status": "not_recovered", "radius_mm": bands["recovery_radius_mm"],
            "final_offset_mm": round(_radial_um(tail[-1], (ref[0], ref[1]))
                                     / 1000.0, 3)}


def _timing(ep: Episode, samples, marks: Dict) -> Dict:
    """Clock hygiene: monotonic, no gaps that hide a stall."""
    times = [s[COL["t"]] for s in samples]
    regressions = sum(1 for a, b in zip(times, times[1:]) if b < a)
    gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
    gaps.sort()
    def pct(p):
        return gaps[min(len(gaps) - 1, int(len(gaps) * p))] // 1_000_000 if gaps else None
    return {
        "clock_regressions": regressions,
        "sample_gap_ms_p50": pct(0.50),
        "sample_gap_ms_p95": pct(0.95),
        "sample_gap_ms_p99": pct(0.99),
        "sample_gap_ms_max": gaps[-1] // 1_000_000 if gaps else None,
        "effective_sample_hz": round(
            len(samples) / ((times[-1] - times[0]) / 1e9), 1)
            if len(times) > 1 and times[-1] > times[0] else None,
        "armed_to_disarmed_ms": int(
            (marks.get("disarmed_ns", 0) - marks.get("armed_ns", 0)) / 1_000_000)
            if marks.get("disarmed_ns") and marks.get("armed_ns") else None,
        "landed_z_um": samples[-1][COL["z"]] if samples else None,
    }
