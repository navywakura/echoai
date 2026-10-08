"""Private v5.8 factory, preserving the frozen runner and its global registry."""
from types import FunctionType

from echo_arc import runner
from echo_arc.temporal_agent import (Arc3EchoV58, Arc3EchoV58NoCount,
                                     Arc3EchoV58NoMemory, Arc3EchoV58NoOrder)


AGENTS = {"v5.8": Arc3EchoV58, "v5.8-noorder": Arc3EchoV58NoOrder,
          "v5.8-nocount": Arc3EchoV58NoCount, "v5.8-nomemory": Arc3EchoV58NoMemory}


def agent_class(name):
    return AGENTS[name] if name in AGENTS else runner.agent_class(name)


def play(env, budget, seed, *, agent_name="v5.8", journal=None):
    def factory(name):
        cls = agent_class(name)
        if journal is None:
            return cls
        from echo_arc.observe import ObservedAgent
        return lambda *a, **kw: ObservedAgent(cls(*a, **kw), journal)
    namespace = dict(runner.play.__globals__, agent_class=factory)
    original = runner.play
    adapted = FunctionType(original.__code__, namespace, original.__name__,
                           original.__defaults__, original.__closure__)
    return adapted(env, budget, seed, agent_name=agent_name)
