"""TRANSFER-3 C1 camera calibration applied to physical frames.

The cage receives two frozen integers, the mount offset in cells. Re-registration
moves each camera (depth) record back to the cell it describes and never
touches the LiDAR, so FUSION-1 still needs two independent families to admit a
cell. The payload is selected host-side for the body's declared nominal mount
and verified against the certified campaign by hash; nothing of the campaign's
rooms, episodes, maps or Q enters DRONE-3.
"""
import hashlib
import json
from pathlib import Path

from echoai.nexus0.transfer3 import calib_c1

ECHOAI = Path(__file__).resolve().parents[2]
CAMPAIGN = ECHOAI/'lab/transfer3/campaign-c1-v2'
CERTIFICATE_SHA256 = '8c77aead2ccdfcc846f39cb2151364f67699988d422df4812786af7eedc39cd2'
FREEZE_SHA256 = 'c73b751010ee24e6d7e77c2f33b857f52e29d9524936c0bde5ac0592c5f2c613'
PAYLOADS_SHA256 = '3aa2c2152c86612032c32bea99bc0aab4d7548ce1c6a9da6ed8e716d5285bcaa'
BODY_MOUNT = '0,0'   # the SITL x500's depth cameras sit at their modelled pose


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def provenance(root=CAMPAIGN):
    """Host-side check. Returns the two integers and the evidence that binds them."""
    root = Path(root)
    certificate = root/'certificate.json'
    freeze_path = root/'freeze.json'
    if hashlib.sha256(certificate.read_bytes()).hexdigest() != CERTIFICATE_SHA256:
        raise ValueError('TRANSFER-3 certificate hash')
    if hashlib.sha256(freeze_path.read_bytes()).hexdigest() != FREEZE_SHA256:
        raise ValueError('TRANSFER-3 freeze hash')
    cert = json.loads(certificate.read_text())
    frozen = json.loads(freeze_path.read_text())
    if cert.get('transfer3_green') is not True or cert.get('freeze_sha256') != FREEZE_SHA256:
        raise ValueError('certificate does not bind this freeze')
    if frozen['payloads_sha256'] != PAYLOADS_SHA256 or canonical_sha(frozen['payloads']) != PAYLOADS_SHA256:
        raise ValueError('frozen payloads hash')
    payload = calib_c1.validate(frozen['payloads'][BODY_MOUNT])
    offset = list(payload['offset'])
    return dict(offset=offset, body_mount=BODY_MOUNT, payload_sha256=canonical_sha(payload),
                certificate_sha256=CERTIFICATE_SHA256, freeze_sha256=FREEZE_SHA256,
                payloads_sha256=PAYLOADS_SHA256, schema=payload['schema'])


def check_offset(offset):
    if type(offset) is not list or len(offset) != 2 or any(type(v) is not int for v in offset) \
            or tuple(offset) not in calib_c1.CANDIDATES:
        raise ValueError('calibration must be two integers inside the declared mount tolerance')
    return offset


def reregister(frame, offset):
    """Physical frame -> same frame with camera records moved back by the offset."""
    ox, oy = check_offset(list(offset))
    if (ox, oy) == (0, 0):
        return frame
    lidar, depth = {}, {}
    for cell in frame['cells']:
        p = tuple(cell['position'])
        for record in cell['sources']:
            (lidar if record['source'] == 'lidar' else depth).setdefault(p, []).append(record)
    moved = {}
    for (x, y, z), records in depth.items():
        moved.setdefault((x-ox, y-oy, z), []).extend(records)
    cells = []
    for p in sorted(set(lidar) | set(moved)):
        sources = lidar.get(p, [])+moved.get(p, [])
        cells.append(dict(position=list(p), sources=sources))
    return dict(frame, cells=cells)


def abstract(frame):
    """Physical frame -> C1's {position, depth, lidar} form, for the consistency check."""
    unknown = calib_c1.UNKNOWN_HEX
    cells = []
    for cell in frame['cells']:
        row = dict(position=cell['position'], depth=unknown, lidar=unknown)
        for record in cell['sources']:
            row['lidar' if record['source'] == 'lidar' else 'depth'] = record['wsp']
        cells.append(row)
    return dict(frame, cells=cells)
