"""Passive, bounded B8 evidence; hypotheses about applicability are not gates."""
from collections import Counter
import json

from echo_arc import precise_patch as patch
from echo_arc.precise_observe import PreciseRecorder


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DiagnosticRecorder(PreciseRecorder):
    def __init__(self, journal):
        super().__init__(journal)
        self.states = Counter()
        self.counts = Counter()
        self.witnesses_b8 = {}
        self.current = None

    def write(self, **event):
        super().write(**event)
        if event["kind"] == "decision":
            f = dict(self.last_features)
            before, after = event["before"], event["after"]
            queue = before.get("to_try", [])
            reset_trial = bool(queue and queue[0] in before.get("reset_keys", [])
                               and event["action"][:2] == ["K", queue[0]]
                               and f["hold_remaining"] <= 1)
            self.states[compact(f)] += 1
            self.current = {"features": f, "action": event["action"][:2],
                            "hold_before": before.get("hold", 0),
                            "hold_after_choice": after.get("hold", 0),
                            "reset_trial_observed": reset_trial}
            self.counts["decisions"] += 1
        elif event["kind"] == "result" and self.current is not None:
            row = dict(self.current)
            row["outcome"] = {k: bool(event[k]) for k in ("changed", "game_over", "level_up")}
            b, a = event["before"], event["after"]
            row["outcome"].update(moved=b.get("pos") != a.get("pos"),
                new_events=max(0, a.get("events", 0) - b.get("events", 0)),
                new_prediction_errors=max(0, a.get("pred", [0, 0])[1] - b.get("pred", [0, 0])[1]))
            f, outcome = row["features"], row["outcome"]
            categories = ["terminal"]
            if row["reset_trial_observed"]:
                categories.append("reset_trial")
            if f["hold_remaining"] and not outcome["level_up"] and not outcome["new_events"]:
                categories.append("wait_without_progress")
            if outcome["new_prediction_errors"]:
                categories.append("prediction_error")
            if outcome["game_over"]:
                categories.append("game_over")
            if outcome["level_up"]:
                categories.append("progress")
            for key in categories:
                self.counts[key] += 1
                if key == "terminal" or key not in self.witnesses_b8:
                    self.witnesses_b8[key] = row

    def summary(self):
        return {"counts": dict(self.counts), "witnesses": self.witnesses_b8,
                "feature_counts": [{"features": json.loads(key), "count": count}
                                   for key, count in sorted(self.states.items())]}


def applicability(proposal, current, rows):
    """Evaluate settings on observed A states, without predicting unseen paths."""
    proposed = patch.validate(proposal)
    joined = patch.append(current, proposed)
    parameter, value = next(iter(proposed["patches"][0]["set"].items()))
    counts = Counter()
    examples = []
    for row in rows:
        assert row["origin"] == "DEVELOPMENT_A", "protected observations forbidden"
        for item in row["diagnostics"]["feature_counts"]:
            f, weight = item["features"], item["count"]
            _, matches = patch.settings(joined, f)
            if len(joined["patches"]) - 1 not in matches:
                continue
            counts["matching_decisions"] += weight
            old_params, _ = patch.settings(current, f)
            previous = old_params.get(parameter, patch.DEFAULTS[parameter])
            changed = value != previous
            if parameter == "COOLDOWN_CAP":
                changed = min(f["hold_remaining"], value) != min(f["hold_remaining"], previous)
            if changed:
                counts["setting_changes"] += weight
            opportunity = f["hold_remaining"] <= 1 if parameter == "HOLD" else True
            if changed and opportunity:
                counts["possible_consumption"] += weight
                if len(examples) < 2:
                    examples.append({"features": f, "before": previous, "proposed": value})
    return {"parameter": parameter, "value": value,
            **{k: counts[k] for k in ("matching_decisions", "setting_changes", "possible_consumption")},
            "examples": examples,
            "scope": "observed A settings only; execution decides actual effect"}


def feedback(verdicts):
    """Allowlist: even arbitrary verifier errors cannot leak protected B."""
    out = []
    for v in verdicts[-6:]:
        a = v.get("A", {})
        hint = v.get("applicability") or {}
        out.append({"proposal": patch.validate(v["proposal"]) if "proposal" in v else None,
                    "verdict": v["verdict"],
                    "training": {k: a[k] for k in ("gain", "changed_action_games", "activated_games") if k in a},
                    "applicability": {k: hint[k] for k in ("parameter", "value", "matching_decisions",
                        "setting_changes", "possible_consumption") if k in hint},
                    "protected_rejection": v["verdict"] == "V4"})
    return out


def focus_for(history, index):
    useful = [v for v in history if v.get("A", {}).get("gain", 0) > 0 and v["verdict"] != "accepted"]
    if useful:
        best = max(useful, key=lambda v: v["A"]["gain"])
        param = next(iter(best["proposal"]["patches"][0]["set"]))
        return "wait" if param in ("HOLD", "COOLDOWN_CAP") else "prediction"
    return ("wait", "prediction", "general")[index % 3]


def select_evidence(rows, arm, history, index):
    for r in rows:
        assert r["origin"] == "DEVELOPMENT_A"
    failing = [(i, r) for i, r in enumerate(rows) if r["levels_completed"] < 5]
    focus = focus_for(history, index)
    if arm == "fijo":
        selected = sorted(failing, key=lambda pair: (pair[1]["levels_completed"], pair[0]))[:3]
        keys = ("terminal", "game_over", "prediction_error", "reset_trial")
    else:
        metric = "reset_trial" if focus == "wait" else "prediction_error" if focus == "prediction" else "wait_without_progress"
        selected = sorted(failing, key=lambda pair: (
            -int(pair[1]["diagnostics"]["counts"].get(metric, 0) > 0),
            -pair[1]["levels_completed"], -pair[1]["diagnostics"]["counts"].get(metric, 0), pair[0]))[:3]
        keys = ("reset_trial", "wait_without_progress", "terminal") if focus == "wait" else \
               ("prediction_error", "game_over", "terminal")
    result = []
    for alias, (_, r) in enumerate(selected):
        d = r["diagnostics"]
        witnesses = []
        for key in keys:
            if key in d["witnesses"] and d["witnesses"][key] not in witnesses:
                witnesses.append(d["witnesses"][key])
            if len(witnesses) == 2:
                break
        result.append({"case": alias, "levels": r["levels_completed"], "counts": d["counts"],
                       "observed_sequences": witnesses})
    return result, focus
