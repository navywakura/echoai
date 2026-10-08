"""An ambiguous match is not evidence of a new family.

Opt-in for PATTERN-1R. The original ECHO-2 learner is unchanged. Counts of
unassigned observations remain in the snapshot and the school's denominator.
"""
from echoai.nexus0.pattern1 import InvariantPatternMemory


class AbstainingPatternMemory(InvariantPatternMemory):
    def observe(self, signature, outcome):
        signature = self._signature(signature)
        outcome = self._outcome(outcome)
        family, distance, tied = self._nearest(signature, outcome=outcome)
        if family >= 0 and distance <= self.max_hamming and tied:
            self.observations += 1
            self.dropped += 1
            return None
        return super().observe(signature, outcome)
