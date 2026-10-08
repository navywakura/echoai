"""Public constants and the canonical 16-byte intentions DRONE-3 may execute.

Integers only. Nothing here knows a world, a seed or a map. The geofence is a
declared operating volume, identical for every room; it is not the room.
"""
from echoai.core.wsp import pack

CELL_MM = 3000
ALTITUDE_MM = 2500
TTL_NS = 250_000_000                 # evidence and proposal freshness (FUSION/PX4-1)
ACK_TIMEOUT_NS = 2_000_000_000       # PX4-1
EXEC_TIMEOUT_NS = 15_000_000_000     # PX4-1
ARRIVAL_MM = 350                     # PX4-1: three distinct settled samples after ACK
ARRIVAL_SPEED_MM_S = 150
ARRIVAL_SAMPLES = 3
GEOFENCE_TARGET_MM = 12_000          # |east|,|north| of any requested cell centre
GEOFENCE_BODY_MM = 13_500            # |east|,|north| of the estimated body
HEIGHT_MIN_MM, HEIGHT_MAX_MM = 1800, 3200
AGENT_DEADLINE_NS = 1_000_000_000    # host monotonic: observation out -> WSP back
VECTORS = {0: (1, 0), 1: (-1, 0), 2: (0, 1), 3: (0, -1)}   # east+, east-, north+, north-
INSPECT = (7, 8, 9, 10)              # yaw 0, pi/2, pi, 3pi/2 (NED heading)
STOP = 6

# Byte layout of echoai.core.wsp.pack: 0 src, 1 rel, 2 dst, 3 time, 4..9 E(VADCUB),
# 10 flags, 11 domain, 12 generator, 13 style, 14 slot, 15 seq.
MOVE, OBSERVE = 11, 14


def intention(raw_hex):
    """Decode an agent WSP into ('move', action) | ('inspect', style) | ('stop', 6).

    Anything else is not an intention this body can execute. The slot byte is a
    region reference chosen by the agent; it never selects a target.
    """
    if type(raw_hex) is not str or len(raw_hex) != 32:
        raise ValueError('wsp size')
    w = bytes.fromhex(raw_hex)
    src, rel, dst, time = w[0], w[1], w[2], w[3]
    e, flags, domain, generator, style, seq = w[4:10], w[10], w[11], w[12], w[13], w[15]
    if (src, dst, time, flags, domain, generator, seq) != (2, 5, 8, 0, 9, 8, 0):
        raise ValueError('noncanonical intention')
    if rel == MOVE and style in VECTORS and e == bytes((0, 0, 0, 80, 0, 0)):
        return 'move', style
    if rel == OBSERVE and style in INSPECT and e == bytes(6) and w[14] == 0:
        return 'inspect', style
    if rel == OBSERVE and style == STOP and e == bytes(6):
        return 'stop', style
    raise ValueError('intention outside the executable set')


def inspect_wsp(k):
    return pack(src=2, rel=OBSERVE, dst=5, time=8, E={}, domain=9, generator=8, style=INSPECT[k]).hex()


def grid(position_mm):
    return (round(position_mm[0]/CELL_MM), round(position_mm[1]/CELL_MM))


def cell_target(cell):
    return [cell[0]*CELL_MM, cell[1]*CELL_MM, ALTITUDE_MM]
