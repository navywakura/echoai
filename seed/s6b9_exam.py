"""B9 uses the unchanged four-arm exam logic on a distinct unopened cohort."""
from types import FunctionType
from seed import s6b9 as s,s6b8_exam as previous,s6_precise_capacity as c

measure=FunctionType(c.measure.__code__,dict(s.measure.__globals__,ROOT=s.ROOT/'exam/measurements'),
                     'measure',c.measure.__defaults__)


def development_one(item):
    native=previous.previous.previous.development_one
    return FunctionType(native.__code__,dict(native.__globals__,s=s),native.__name__,native.__defaults__)(item)


native_development=previous.previous.previous.development
development=FunctionType(native_development.__code__,dict(native_development.__globals__,s=s,
    development_one=development_one),native_development.__name__,native_development.__defaults__)
run=FunctionType(previous.run.__code__,dict(previous.run.__globals__,s=s,measure=measure,development=development))
