"""B12 reserved exam, using the unchanged B11 evaluation and B1--B5 checks."""
from types import FunctionType
from seed import s6b11_exam as previous, s6b12 as s

measure = FunctionType(s.measure.__code__, dict(s.measure.__globals__, ROOT=s.ROOT / 'exam/measurements'),
                       'measure', s.measure.__defaults__)


def development_one(item):
    native = previous.s6_precise_exam.previous.development_one
    return FunctionType(native.__code__, dict(native.__globals__, s=s))(item)


development = FunctionType(previous.development.__code__,
    dict(previous.development.__globals__, s=s, development_one=development_one))
_run = FunctionType(previous.run.__code__, dict(previous.run.__globals__, s=s,
    measure=measure, development=development))


def run():
    (s.ROOT / 'exam/measurements').mkdir(parents=True, exist_ok=True)
    return _run()
