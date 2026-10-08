"""Same parameter-first grammar, extending the API with bounded transition revision."""
from types import FunctionType
from echo_arc.parameter_first_grammar import Grammar as Previous
from echo_arc.stale_transition import LIMITS


class Grammar(Previous):
    __init__=FunctionType(Previous.__init__.__code__,dict(Previous.__init__.__globals__,LIMITS=LIMITS))
