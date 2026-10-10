"""Count actual contradiction features in the existing development recorder."""
from collections import Counter
import json

from echo_arc.repair_loop_observe import Recorder as Previous
from echo_arc.repair_diagnostics import compact


class Recorder(Previous):
    def __init__(self, journal, *, origin, program):
        super().__init__(journal, origin=origin, program=program)
        self.contradiction_features = Counter()

    def write(self, **event):
        before = self.counts.get('contradictory_noop', 0)
        super().write(**event)
        if self.counts.get('contradictory_noop', 0) > before:
            self.contradiction_features[compact(self.last_features)] += 1

    def summary(self):
        return dict(super().summary(), contradiction_features=[
            {'features': json.loads(key), 'count': count}
            for key, count in sorted(self.contradiction_features.items())])
