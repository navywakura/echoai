"""Fixed communication/absence probes, also replayed against the isolated consumer."""
from .core import Host, signal
from .world import Local
from echoai.nexus0.cause1.core import wsp


def communication(consumer=None):
    consumer = consumer or Local()
    rows = []
    base = dict(now_ns=1_000_000_000, symbol=1, opportunity=True, budget=100, reserve=40,
                busy=False, safe=True, flight=None)
    cases = [(str(s), dict(base, symbol=s), 'silence' if s == 0 else 'communication') for s in range(5)]
    cases += [('no_opportunity', dict(base, opportunity=False), 'silence'),
              ('reserve', dict(base, budget=41), 'silence'), ('busy', dict(base, busy=True), 'silence'),
              ('safety', dict(base, safe=False), 'silence'),
              ('flight', dict(base, flight=wsp(0)), 'flight_candidate'),
              ('unsafe_flight', dict(base, safe=False, flight=wsp(0)), 'silence'),
              ('communication_as_flight', dict(base, flight=signal(1, False)), 'silence')]
    for name, request, expected in cases:
        consumer.call(dict(op='init', policy='consequence'))
        result = consumer.call(dict(op='communicate', args=[request]))
        rows.append(dict(name=name, request=request, response=result, ok=result['channel'] == expected))
    for name, later, budget in [('cooldown', 1_500_000_000, 100), ('spent', 2_000_000_000, 42)]:
        consumer.call(dict(op='init', policy='consequence'))
        first = dict(base, budget=budget)
        a = consumer.call(dict(op='communicate', args=[first]))
        second = dict(first, now_ns=later)
        b = consumer.call(dict(op='communicate', args=[second]))
        rows.append(dict(name=name, first=first, a=a, second=second, b=b,
                         ok=a['channel'] == 'communication' and b['channel'] == 'silence'))
    return rows
