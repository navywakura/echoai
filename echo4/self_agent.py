"""SELF-A opt-in observation hook; no change to policy or historical loops."""
from echoai.echo4.boundary import Pair
from echoai.echo4.boundary_agent import BoundaryAgent
from echoai.echo4.self_model import SelfChangeMonitor


class SelfAgent(BoundaryAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.self_change = SelfChangeMonitor(self.boundary)

    def calibrate_self_reference(self, pair: Pair) -> None:
        self.self_change.calibrate(pair)

    def seal_self_reference(self) -> None:
        self.self_change.seal()

    def compare_self_observation(self, pair: Pair):
        return self.self_change.compare(pair)
