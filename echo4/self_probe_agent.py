"""Opt-in diagnostic factory; ordinary SelfAgent behavior remains unchanged."""
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.self_attribution import SelfAttributor


class SelfProbeAgent(SelfAgent):
    def new_self_diagnosis(self, initial_packet, nominal_trace):
        return SelfAttributor(self.self_change, initial_packet, nominal_trace)
