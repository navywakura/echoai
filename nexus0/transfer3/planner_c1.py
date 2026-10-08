"""Plan C1 planner: re-register the camera, then run the unchanged pipeline.

Everything downstream of the frame is the historical agent: FUSION-1 evidence
memory, the two-family admission gate, the cost planner with uniform costs, the
reserve rule. The only difference between arms is the mount offset the agent
believes, applied to the frame before it is ingested.
"""
from . import calib_c1, costs_a2
from .planner_a2 import CostPlanner


class CalibratedPlanner(CostPlanner):
    def __init__(self, model, goal, camera, *, reserve):
        super().__init__(model, goal, costs_a2.nominal(), learning=False, reserve=reserve)
        calib_c1.validate(camera)
        self.offset = tuple(camera['offset'])

    def update(self, frame):
        return super().update(calib_c1.reregister(frame, self.offset))

    def admitted(self):
        """Cells the agent would currently let itself enter. Reported for audit."""
        return sorted(list(p) for p in self.beliefs if self.free(p))
