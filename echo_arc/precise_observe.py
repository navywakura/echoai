"""Passive snapshots in the existing journal; no tracing or second bus."""
from echo_arc.observe import ObservedAgent, snapshot, plain
from echo_arc.repair_evidence import Recorder
from echo_arc.precise_patch import features


class PreciseRecorder(Recorder):
    def capture(self, actor, state):
        stagnation = min(2000, self.stagnation + 1) if state == self.last_state else 0
        self.before_features = features(actor, stagnation)

    def write(self, **event):
        if event["kind"] == "decision":
            self.stagnation = self.before_features["stagnation"]
            self.last_state, self.last_before = event["state"], event["before"]
            self.last_features = dict(self.before_features)
            event["repair_features"] = self.last_features
            event["repair_matches"] = list(getattr(self.actor, "patch_matches", []))
            self.journal.write(**event)
        else:
            super().write(**event)


class PreciseObservedAgent(ObservedAgent):
    def choose(self, state):
        before = snapshot(self._actor)
        self._journal.capture(self._actor, state)
        act = self._actor.choose(state)
        object.__setattr__(self, "_step", self._step + 1)
        self._journal.write(kind="decision", step=self._step, state=state, action=plain(act),
                            before=before, after=snapshot(self._actor), returns=[], branches=[])
        return act
