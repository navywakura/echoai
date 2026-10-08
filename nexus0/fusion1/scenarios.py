"""Public development/test stimuli; condition names never reach the consumer."""
import hashlib
import random
from .core import packet, BARRIER, VISIBLE, ABSENT, PRESENT, UNKNOWN, TTL, SKEW

CONDITIONS = ('clear', 'blocked', 'conflict', 'reverse_conflict', 'different_predicate',
              'different_region', 'different_epoch', 'expired', 'duplicates',
              'correlated', 'late_old', 'future', 'corrupt', 'no_return',
              'recovery', 'invalid_retires', 'unpaired_time', 'host_claim')


def observe(source, value, t, *, arrival=None, predicate=BARRIER, region=0, epoch=0,
            valid=True, corrupt=False):
    extract = f'{source}:measurement={value};capture={t}'
    return dict(op='observe', wsp=packet(value, 40, predicate, region, epoch).hex(),
                source=source, capture_ns=t, delivered_ns=t if arrival is None else arrival,
                valid=valid, extract=extract,
                extract_sha256=('0'*64 if corrupt else hashlib.sha256(extract.encode()).hexdigest()))


def query(t, predicate=BARRIER, region=0, epoch=0):
    return dict(op='query', now_ns=t, predicate=predicate, region=region, epoch=epoch)


def scenario(kind, rng):
    t = rng.randrange(1_000_000_000, 10_000_000_000)
    delta = rng.randrange(1, SKEW//2)
    a,b = ('depth','lidar') if rng.randrange(2) else ('lidar','depth')
    o = lambda source,value,when,**kw: observe(source,value,when,**kw)
    q = lambda when: query(when)
    if kind in ('clear','blocked','conflict','reverse_conflict'):
        values = {'clear':(0,0),'blocked':(1,1),'conflict':(1,0),'reverse_conflict':(0,1)}[kind]
        return [o(a,values[0],t),o(b,values[1],t+delta),q(t+delta)]
    if kind == 'different_predicate':
        return [o(a,0,t),o(b,1,t+delta,predicate=VISIBLE),q(t+delta),query(t+delta,VISIBLE)]
    if kind == 'different_region':
        return [o(a,0,t),o(b,1,t+delta,region=1),q(t+delta),query(t+delta,region=1)]
    if kind == 'different_epoch':
        return [o(a,0,t),o(b,1,t+delta,epoch=1),q(t+delta),query(t+delta,epoch=1)]
    if kind == 'expired':
        return [o(a,0,t),o(b,0,t+delta),q(t+delta),q(t+delta+TTL+1)]
    if kind == 'duplicates':
        first=o(a,0,t)
        return [first,dict(first,delivered_ns=t+delta),dict(first,delivered_ns=t+2*delta),q(t+2*delta)]
    if kind == 'correlated':
        return [o('depth',0,t),o('rgb',0,t+delta),q(t+delta)]
    if kind == 'late_old':
        return [o(a,1,t),o(a,0,t-1,arrival=t+delta),o(b,1,t+2*delta),q(t+2*delta)]
    if kind == 'future':
        return [o(a,0,t+delta,arrival=t),o(b,0,t),q(t)]
    if kind == 'corrupt':
        return [o(a,0,t,corrupt=True),o(b,0,t+delta),q(t+delta)]
    if kind == 'no_return':
        return [o(a,UNKNOWN,t),o(b,0,t+delta),q(t+delta)]
    if kind == 'recovery':
        return [o(a,1,t),o(b,0,t+delta),q(t+delta),q(t+TTL+1),
                o(a,0,t+TTL+2),o(b,0,t+TTL+3),q(t+TTL+3)]
    if kind == 'invalid_retires':
        return [o(a,0,t),o(b,0,t+delta),q(t+delta),o(a,0,t+2*delta,valid=False),q(t+2*delta)]
    if kind == 'unpaired_time':
        return [o(a,1,t),o(b,0,t+SKEW+1),q(t+SKEW+1)]
    if kind == 'host_claim':
        return [o('host',0,t),o(a,0,t+delta),q(t+delta)]
    raise ValueError(kind)


def generate(seed, repetitions):
    rng = random.Random(seed)
    return [dict(condition=kind, repetition=i, commands=scenario(kind,rng))
            for i in range(repetitions) for kind in CONDITIONS]
