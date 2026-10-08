"""Allowlisted, coordinate-free action-effect transfer; no episodic snapshot."""
from echoai.nexus0.compose1.model import Effects, state_packet

SCHEMA = 'transfer3-planar-effects-v1'


def validate(payload):
    if type(payload) is not dict or set(payload) != {'schema', 'effects'}:
        raise ValueError('transfer fields: no CAM, Q, map or provenance channel')
    if payload['schema'] != SCHEMA or type(payload['effects']) is not list:
        raise ValueError('transfer schema')
    if len(payload['effects']) > 4:
        raise ValueError('planar action capacity')
    previous = -1
    for row in payload['effects']:
        if type(row) is not dict or set(row) != {'action', 'delta', 'count'}:
            raise ValueError('effect fields')
        action, delta, count = row['action'], row['delta'], row['count']
        if type(action) is not int or not previous < action < 4:
            raise ValueError('unique sorted planar actions')
        previous = action
        if type(count) is not int or not 2 <= count <= 255:
            raise ValueError('effect count')
        if (type(delta) is not list or len(delta) != 3 or
                any(type(x) is not int for x in delta) or delta[2] != 0 or
                sum(abs(x) for x in delta) != 1):
            raise ValueError('unit relative planar displacement only')


def export(model):
    """Only the clear-action T row; never enumerate/copy episodic CAM or Q.

Ambiguous models fail closed, rather than silently hiding contradictory A
observations. Counts saturate at 255 in this versioned transfer format.
"""
    if model.t.conflicts:
        raise ValueError('conflicting school requires another protocol')
    source = model.slot(state_packet(1, 1))
    rows = []
    if source >= 0:
        for action in range(4):
            delta = model.predict(action)
            if delta is not None:
                rows.append(dict(action=action, delta=list(delta),
                                 count=min(255, model.t.n[source][action])))
    payload = dict(schema=SCHEMA, effects=rows)
    validate(payload)
    return payload


def restore(payload):
    """Rebuild abstract T in a fresh CAM; restored slots are not A episodes.

observe_effect supplies has_fact=0. No Q rewards or sensor evidence are
created; the numerical counts represent the exported A sufficient statistic.
"""
    validate(payload)
    model = Effects()
    for row in payload['effects']:
        for _ in range(row['count']):
            model.observe_effect(True, row['action'], tuple(row['delta']))
    return model


def scratch():
    return dict(schema=SCHEMA, effects=[])
