"""V2 transfers relative-feature Q, with identical locomotion in both arms."""
from echoai.nexus0.compose1.model import state_packet
from .model import restore as restore_effects
from .rehearsal import programmed

SCHEMA = 'transfer3-relative-q-v2'


def validate(payload):
    if type(payload) is not dict or set(payload) != {'schema', 'q'}:
        raise ValueError('policy fields')
    if payload['schema'] != SCHEMA or type(payload['q']) is not list or len(payload['q']) > 1728:
        raise ValueError('policy schema/capacity')
    previous = -1
    for row in payload['q']:
        if type(row) is not dict or set(row) != {'feature', 'values'}:
            raise ValueError('relative feature row')
        code, values = row['feature'], row['values']
        if type(code) is not int or not previous < code < 1728:
            raise ValueError('sorted unique relative features')
        previous = code
        if (type(values) is not list or len(values) != 7 or
                any(type(v) is not int or not -127 <= v <= 127 for v in values) or
                values[4:] != [0, 0, 0] or not any(values)):
            raise ValueError('nonzero planar Q int8 row')


def export(model):
    rows = []
    # Enumerate the public semantic vocabulary, not A's slots or packets.
    for code in range(1728):
        slot = model.slot(state_packet(code, 3))
        if slot < 0:
            continue
        values = [model.q.get(slot, a) for a in range(7)]
        if any(values):
            rows.append(dict(feature=code, values=values))
    payload = dict(schema=SCHEMA, q=rows)
    validate(payload)
    return payload


def restore(payload):
    validate(payload)
    model = restore_effects(programmed())
    for row in payload['q']:
        slot = model.slot(state_packet(row['feature'], 3), True)
        for action, value in enumerate(row['values']):
            model.q.set(slot, action, value)
    return model


def scratch():
    return dict(schema=SCHEMA, q=[])
