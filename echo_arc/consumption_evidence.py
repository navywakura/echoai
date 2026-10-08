"""Exact observed native HOLD assignments; separate from frozen B8 heuristics.

This diagnostic only describes the recorded native path. It neither executes
repairs nor claims that a changed internal wait will improve an action/result.
"""
from collections import Counter
import json

from echo_arc import precise_patch as patch


def native_hold_sites(events, *, origin, native_policy):
    if origin != "DEVELOPMENT_A" or patch.validate(native_policy) != patch.EMPTY:
        raise ValueError("only native, unsealed development A is supported")
    counts = Counter()
    for event in events:
        if event.get("kind") != "decision":
            continue
        before, after = event["before"], event["after"]
        # In the frozen native controller the assignment of HOLD=40 is the
        # only choose() transition from remaining wait <=1 to exactly 40.
        # Require its deliberate queued reset as a second independent witness.
        queue = before.get("to_try", [])
        if not (before.get("hold", 0) <= 1 and after.get("hold", 0) == patch.DEFAULTS["HOLD"]
                and queue and queue[0] in before.get("reset_keys", [])
                and list(event["action"][:2]) == ["K", queue[0]]):
            continue
        f = event["repair_features"]
        if set(f) != set(patch.FEATURES):
            raise ValueError("incomplete or unknown observed feature set")
        if any(type(f[k]) is not int or not lo <= f[k] <= hi for k, (lo, hi) in patch.FEATURES.items()):
            raise ValueError("observed feature outside declared range")
        counts[json.dumps(f, sort_keys=True, separators=(",", ":"))] += 1
    return [{"features": json.loads(key), "count": count} for key, count in sorted(counts.items())]


def assess_hold(proposal, sites):
    proposed = patch.validate(proposal)
    if len(proposed["patches"]) != 1 or set(proposed["patches"][0]["set"]) != {"HOLD"}:
        raise ValueError("one HOLD proposal required; other consumers are not inferred")
    value = proposed["patches"][0]["set"]["HOLD"]
    hits = sum(row["count"] for row in sites if patch.settings(proposed, row["features"])[1])
    changed = hits if value != patch.DEFAULTS["HOLD"] else 0
    return {"observed_native_assignments": sum(r["count"] for r in sites),
            "matching_assignment_sites": hits, "would_change_assigned_wait": changed,
            "diagnosis": "NO_OBSERVED_CONSUMPTION" if not hits else "NATIVE_VALUE" if not changed else "CHANGES_OBSERVED_ASSIGNMENT",
            "action_improvement": "UNMEASURED", "scope": "native recorded A path only"}
