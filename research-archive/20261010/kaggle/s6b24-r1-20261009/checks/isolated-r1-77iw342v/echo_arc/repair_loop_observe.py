"""Combine existing consumer and transition witnesses without a second journal."""
from types import FunctionType, SimpleNamespace
from echo_arc import consumer_observe as consumers, stale_transition as patch, precise_patch
from echo_arc.transition_observe import TransitionRecorder

interface=SimpleNamespace(validate=patch.validate,agent_class=patch.agent_class,
                          apply_cooldown=precise_patch.apply_cooldown)


class Recorder(consumers.ConsumptionRecorder,TransitionRecorder):
    __init__=FunctionType(consumers.ConsumptionRecorder.__init__.__code__,
        dict(consumers.ConsumptionRecorder.__init__.__globals__,patch=interface),
        '__init__',consumers.ConsumptionRecorder.__init__.__defaults__,
        consumers.ConsumptionRecorder.__init__.__closure__)


traced_agent_class=FunctionType(consumers.traced_agent_class.__code__,
    dict(consumers.traced_agent_class.__globals__,patch=interface))
