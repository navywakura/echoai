"""Bounded summaries consumed from the existing passive ARC decision journal."""
from collections import deque

from echo_arc.local_patch import features


class Recorder:
    def __init__(self, journal):
        self.journal = journal
        self.actor = None
        self.objects = {}
        self.last_features = {}
        self.last_state = None
        self.last_before = None
        self.stagnation = 0
        self.tail = deque(maxlen=2)
        self.witnesses = {}

    def bind_actor(self, actor):
        self.actor = actor

    def name(self, color):
        if color not in self.objects:
            self.objects[color] = "object" + str(len(self.objects) + 1)
        return self.objects[color]

    def view(self, beliefs):
        temporal = beliefs.get("temporal_state", {})
        return {"body_known": beliefs.get("me") is not None, "level": beliefs.get("level", 0),
                "path_remaining": beliefs.get("path_remaining", 0),
                "predictions": beliefs.get("pred", [0, 0]), "events": beliefs.get("events", 0),
                "effect_active": temporal.get("effect_active", False),
                "coverage_complete": temporal.get("coverage_complete", False),
                "entries": temporal.get("entries", 0),
                "orders": [{"sequence": [self.name(c) for c in r["sequence"]],
                            "supports": r["supports"], "conflicts": r["conflicts"]}
                           for r in temporal.get("orders", [])[:3]],
                "counts": [{"object": self.name(r["kind"]), "entries": r["entries"],
                            "supports": r["supports"], "conflicts": r["conflicts"]}
                           for r in temporal.get("thresholds", [])[:3]]}

    def write(self, **event):
        if event["kind"] == "decision":
            state = event.get("state")
            self.stagnation = min(2000, self.stagnation + 1) if state == self.last_state else 0
            self.last_state = state
            self.last_before = event["before"]
            self.last_features = dict(getattr(self.actor, "patch_features", {}) or
                                      features(self.actor, self.stagnation))
            event["repair_features"] = self.last_features
            event["repair_matches"] = list(getattr(self.actor, "patch_matches", []))
        elif event["kind"] == "result":
            before, after = self.last_before or event["before"], event["after"]
            b, a = self.view(before), self.view(after)
            result = {"step": event["step"], "features": self.last_features,
                      "before": b, "action": list(event["action"][:2]), "after": a,
                      "moved": before.get("pos") != after.get("pos"),
                      "changed": event["changed"], "game_over": event["game_over"],
                      "level_up": event["level_up"]}
            self.tail.append(result)
            if result["level_up"]:
                self.witnesses["progress"] = result
            elif result["game_over"]:
                self.witnesses["game_over"] = result
            elif a["predictions"][1] > b["predictions"][1]:
                self.witnesses["prediction_error"] = result
            elif a["events"] > b["events"]:
                self.witnesses["world_event"] = result
        self.journal.write(**event)

    def episodes(self):
        chosen = list(self.tail)
        for key in ("prediction_error", "game_over", "world_event", "progress"):
            if key in self.witnesses and self.witnesses[key] not in chosen:
                chosen.insert(0, self.witnesses[key])
                break
        return chosen[-3:]

    def close(self):
        self.journal.close()
