"""Integer attribution. Input is public evidence; output remains a hypothesis."""
import struct

TTL = 250_000_000
SCHEMA = {'now_ns', 'capture_ns', 'delivered_ns', 'odometry_ns', 'north_mm',
          'distance_mm', 'yaw_mrad', 'rays'}
NAMES = ('none', 'self', 'external', 'both', 'unknown')


def wsp(action):
    if type(action) is not int or action not in (0, 1, 6):
        raise ValueError('action')
    return struct.pack('<BBBBbbbbbbBBBBBB', 2, 14 if action == 6 else 11,
                       5, 8, 0, 0, 0, 40, 0, 0, 0, 9, 8, action, 0, 0).hex()


def decode(w):
    data = bytes.fromhex(w)
    if len(data) != 16 or data[13] not in (0, 1, 6) or wsp(data[13]) != w:
        raise ValueError('noncanonical WSP intention')
    return data[13]


def fresh(frame):
    return (type(frame) is dict and set(frame) == SCHEMA
            and all(type(v) is int for v in frame.values())
            and 0 <= frame['capture_ns'] <= frame['delivered_ns'] <= frame['now_ns']
            and 0 <= frame['now_ns']-frame['capture_ns'] <= TTL
            and 0 <= frame['now_ns']-frame['odometry_ns'] <= TTL
            and abs(frame['capture_ns']-frame['odometry_ns']) <= 100_000_000
            and 3 <= frame['rays'] <= 512 and 300 <= frame['distance_mm'] <= 30000)


def prepare(intention, before):
    """Publication is ordered by the journal before command transmission.

    published_ns is the observation-clock lower bound, not a measurement of
    host publication latency; that latency is measured separately by session.
    """
    action = decode(intention)
    allowed = fresh(before)
    command = intention if allowed else wsp(6)
    delta = 1000 if action == 0 else -1000 if action == 1 else 0
    return dict(wsp=command, allowed=allowed, published_ns=before.get('now_ns', -1),
                predicted_north_mm=delta if allowed else None,
                predicted_range_delta_mm=-delta if allowed else None,
                prediction_source='bounded_skill_nominal_1m')


def attribute(intention, before, prepared, execution, after, *, mutant=''):
    action = decode(intention)
    own = sensor = residual = None
    reason = 'invalid_evidence'
    label = 'unknown'
    if prepared != prepare(intention, before):
        raise ValueError('prediction differs from pre-action evidence')
    if set(execution) != {'wsp', 'sent_ns', 'ack_ns', 'accepted'}:
        raise ValueError('execution schema')
    chronology = (all(type(execution[k]) is int for k in ('sent_ns', 'ack_ns'))
                  and prepared['published_ns'] <= execution['sent_ns'] <= execution['ack_ns']
                  and execution['ack_ns'] < after.get('capture_ns', -1)
                  and execution['ack_ns'] < after.get('odometry_ns', -1))
    valid = fresh(before) and fresh(after)
    if mutant == 'no_expiry':
        valid = set(before) == SCHEMA and set(after) == SCHEMA and after['distance_mm'] > 0
    ack = execution['accepted'] is True or mutant == 'no_ack'
    if valid and prepared['allowed'] and chronology and ack and execution['wsp'] == prepared['wsp']:
        own = after['north_mm']-before['north_mm']
        sensor = after['distance_mm']-before['distance_mm']
        residual = sensor+own
        yaw = abs((after['yaw_mrad']-before['yaw_mrad']+3142) % 6284-3142)
        expected = prepared['predicted_north_mm']
        confirmed = (abs(own) <= 200 if action == 6 else
                     own*expected > 0 and abs(own) >= 600 and abs(own-expected) <= 350)
        if mutant == 'no_confirmation':
            confirmed = True
        if mutant == 'no_odometry':
            residual = sensor
        if yaw > 80:
            reason = 'rotated_frame'
        elif not confirmed:
            reason = 'actuation_not_confirmed'
        else:
            external = abs(residual) > 300
            label = NAMES[int(action != 6)+2*int(external)]
            reason = 'paired_domain_hypothesis'
    code = NAMES.index(label)
    packet = struct.pack('<BBBBbbbbbbBBBBBB', 2, 31 if code == 4 else 14,
                         31 if code == 4 else 5, 8, 0, 0, 0, 0 if code == 4 else 40,
                         0, 0, 0, 9, 8, 20+code, 0, 0).hex()
    return dict(wsp=packet, label=label, reason=reason, north_delta_mm=own,
                range_delta_mm=sensor, external_delta_mm=residual,
                has_fact=False, cam_writes=0, cortex_calls=0)
