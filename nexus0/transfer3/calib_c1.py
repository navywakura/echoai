"""Agent-safe camera extrinsic calibration. Knows sensors, never the world.

The estimate uses only the agent's own frames: for each candidate mount offset,
re-register the camera and count where it agrees and disagrees with the LiDAR,
which is declared as the body's calibrated reference. The best candidate wins.

Re-registration moves each camera report back to the cell it describes. It never
changes a value and never touches the LiDAR, so the fusion gate still demands two
independent families before admitting a cell: VERIFY is not weakened.
"""
from echoai.nexus0.fusion1.core import UNKNOWN, packet, unpack

SCHEMA = 'transfer3-camera-extrinsic-c1'
# The declared tolerance of the camera mount, public in the body spec.
CANDIDATES = tuple((x, y) for x in (-1, 0, 1) for y in (-1, 0, 1))
UNKNOWN_HEX = packet(UNKNOWN, 0).hex()


def validate(payload):
    if type(payload) is not dict or set(payload) != {'schema', 'offset', 'agreement', 'disagreement'}:
        raise ValueError('camera calibration fields: no map, geometry or episode channel')
    if payload['schema'] != SCHEMA:
        raise ValueError('camera calibration schema')
    offset = payload['offset']
    if type(offset) is not list or len(offset) != 2 or tuple(offset) not in CANDIDATES \
            or any(type(v) is not int for v in offset):
        raise ValueError('offset outside the declared mount tolerance')
    for key in ('agreement', 'disagreement'):
        if type(payload[key]) is not int or payload[key] < 0:
            raise ValueError('agreement counts')
    return payload


def nominal():
    return validate(dict(schema=SCHEMA, offset=[0, 0], agreement=0, disagreement=0))


def prior(offset):
    return validate(dict(schema=SCHEMA, offset=list(offset), agreement=0, disagreement=0))


def reregister(frame, offset):
    """Move each camera report back to the cell it describes. LiDAR untouched."""
    ox, oy = offset
    if (ox, oy) == (0, 0):
        return frame
    camera = {tuple(c['position']): c['depth'] for c in frame['cells']}
    cells = []
    for c in frame['cells']:
        p = tuple(c['position'])
        cells.append(dict(position=c['position'],
                          depth=camera.get((p[0]+ox, p[1]+oy, p[2]), UNKNOWN_HEX),
                          lidar=c['lidar']))
    return dict(frame, cells=cells)


def consistency(frames, offset):
    agree = disagree = 0
    for frame in frames:
        registered = reregister(frame, offset)
        for c in registered['cells']:
            lidar = unpack(bytes.fromhex(c['lidar']))[0]
            camera = unpack(bytes.fromhex(c['depth']))[0]
            if lidar == UNKNOWN or camera == UNKNOWN:
                continue
            if lidar == camera:
                agree += 1
            else:
                disagree += 1
    return agree, disagree


def estimate(frames):
    """Deterministic argmax of (agreement - disagreement, agreement), smallest offset on ties."""
    if not frames:
        raise ValueError('calibration needs at least one frame')
    best = None
    for offset in CANDIDATES:
        agree, disagree = consistency(frames, offset)
        key = (agree-disagree, agree, -abs(offset[0])-abs(offset[1]), offset)
        if best is None or key > best[0]:
            best = (key, offset, agree, disagree)
    _, offset, agree, disagree = best
    return validate(dict(schema=SCHEMA, offset=list(offset), agreement=agree, disagreement=disagree))
