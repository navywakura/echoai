"""Opt-in attachment; no replacement of Agent Q, gate, CAM, T or SENSATION."""
from echoai.echo4.boundary import BoundaryMap, Pair
from echoai.echo4.sensation_agent import SensationAgent


class BoundaryAgent(SensationAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.boundary = BoundaryMap(self.cam)

    def observe_intervention(self, pair: Pair) -> None:
        # Caller must supply a trusted, matched experimental receipt.
        # Arbitrary online turns alone do not authorize causal attribution.
        self.boundary.observe(pair)

    def influence_estimate(self, packet: bytes, action: int):
        return self.boundary.estimate(packet, action)
