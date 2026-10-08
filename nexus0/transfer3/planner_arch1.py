"""ARCH-1: bounded plan commitment. A versioned planner extension, not a new core.

Every planner in this line replans from scratch at each step. That makes it
robust to a wrong model and, as Plans A and B measured, unable to profit from a
right one: a plan that would have derailed costs nothing when it is discarded
before it runs.

Here the agent may commit to up to `commitment` actions of the plan it found.
The commitment buys nothing for free:

* **no gate is skipped.** A committed action passes exactly the same
  admissibility, burst-path, evidence and reserve checks as a freshly searched
  one, on the observation of the step that executes it. A committed plan is a
  proposal, never a licence.
* **a derailed plan is abandoned.** If the body did not land where the model
  predicted, the remaining commitment is dropped and the agent replans. That is
  what makes an inaccurate model expensive, which is the whole point.

`commitment=1` reproduces the historical behaviour exactly, so the arm that
represents today's architecture is the same code with one parameter.
"""
from .planner_b1 import GainPlanner

COMMITMENT_RANGE = (1, 8)


class CommittedPlanner(GainPlanner):
    def __init__(self, *args, commitment=1, **kwargs):
        super().__init__(*args, **kwargs)
        if type(commitment) is not int or not COMMITMENT_RANGE[0] <= commitment <= COMMITMENT_RANGE[1]:
            raise ValueError('commitment out of declared range')
        self.commitment = commitment
        self.committed = []
        self.served = False
        self.commitments_kept = 0
        self.commitments_derailed = 0

    def update(self, frame):
        before = self.prediction_errors
        super().update(frame)
        if self.prediction_errors > before and self.committed:
            # The body is not where the plan assumed; the rest of it is void.
            self.committed = []
            self.commitments_derailed += 1

    def search(self, target):
        """Serve the committed plan if one stands; otherwise search and store one.

        `decide` is inherited verbatim, so every gate, every early return and
        every status keeps the historical control flow. With `commitment = 1`
        the stored slice `path[1:1]` is always empty, so this method reduces to
        the parent's search and the arm is the historical planner by
        construction rather than by resemblance.
        """
        if self.committed:
            self.served = True
            return list(self.committed), 0
        self.served = False
        path, generated = super().search(target)
        self.committed = list(path[1:self.commitment]) if path else []
        return path, generated

    def output(self, action, path, status, count):
        # `served` distinguishes an action taken from a standing commitment from
        # the head of a plan just found. Without it a straight run like [0, 0, 0]
        # would look like a kept commitment and silently drop an action.
        if status == 'moving' and self.served:
            if self.committed and self.committed[0] == action:
                self.committed.pop(0)
                self.commitments_kept += 1
        elif status != 'moving':
            # Returning, blocked or finished: nothing proposed earlier survives.
            self.committed = []
        self.served = False
        return super().output(action, path, status, count)
