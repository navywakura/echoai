"""New untouched cohort, four arms and the existing B1--B5 criteria."""
from types import FunctionType
from seed import s6b10 as s, s6b9_exam as previous, s6_precise_capacity as c

measure = FunctionType(c.measure.__code__, dict(s.measure.__globals__, ROOT=s.ROOT / 'exam/measurements'),
                       'measure', c.measure.__defaults__)
def development_one(item):
    worker = FunctionType(previous.development_one.__code__, dict(previous.development_one.__globals__, s=s),
                          'development_one', previous.development_one.__defaults__)
    return worker(item)


development = FunctionType(previous.development.__code__, dict(previous.development.__globals__, s=s,
    development_one=development_one), 'development', previous.development.__defaults__)
run = FunctionType(previous.run.__code__, dict(previous.run.__globals__, s=s, measure=measure, development=development))
