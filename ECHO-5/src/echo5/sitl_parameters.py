"""Explicit, bounded simulator calibration; no device or parameter I/O.

The inherited driver still applies its stock startup hook and MAVLink readback.
Only explicitly bounded PX4 1.15 estimator parameters are added before boot.
"""
import math
import hashlib
import json
from pathlib import Path
import struct


LEGACY_ALLOWED = frozenset({
    'EKF2_GPS_DELAY', 'MPC_XY_VEL_P_ACC', 'MPC_XY_VEL_D_ACC',
    'MPC_XY_VEL_I_ACC', 'EKF2_NOAID_NOISE', 'EKF2_GPS_P_NOISE',
    'EKF2_GPS_V_NOISE', 'EKF2_HGT_REF', 'EKF2_BARO_NOISE'})
EXTRA = 'EKF2_ACC_B_NOISE'
EXTRA_RANGES = {EXTRA: (0, .01), 'EKF2_ACC_NOISE': (.01, 1.0)}


def validate_parameters(parameters):
    if type(parameters) is not dict or not set(parameters) <= LEGACY_ALLOWED | EXTRA_RANGES.keys():
        raise ValueError('unexpected SITL calibration parameter')
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in parameters.values()):
        raise ValueError('SITL parameters must be finite numbers')
    for name, (low, high) in EXTRA_RANGES.items():
        if name in parameters and not low <= parameters[name] <= high:
            raise ValueError(f'{name} outside PX4 1.15 documented [{low}, {high}]')
    return dict(parameters)


def configure_driver(driver, parameters):
    parameters = validate_parameters(parameters)
    if frozenset(driver.ALLOWED) != LEGACY_ALLOWED:
        raise ValueError('inherited parameter allowlist changed')
    # The class is the disposable container's imported driver, never a source edit.
    extensions = {name: EXTRA_RANGES[name] for name in parameters if name in EXTRA_RANGES}
    driver.ALLOWED = set(LEGACY_ALLOWED) | {EXTRA} | extensions.keys()
    return dict(schema='echo5.sitl.parameter-adapter.v1', requested=parameters,
                extension=EXTRA, range=[0, .01], extensions=extensions, timing='before_px4_boot',
                readback='inherited_MAVLink_driver_plus_independent_ULog')


def audit_parameters(expected, initial, changes):
    """Reconcile independent ULog values, rejecting any nonmatching retune."""
    expected = validate_parameters(expected)
    if type(initial) is not dict or type(changes) is not list:
        raise ValueError('ULog parameter evidence must be an object and a list')
    findings = []
    def matches(name, value):
        return (type(value) in (int, float) and math.isfinite(value)
                and math.isclose(value, expected[name], rel_tol=0, abs_tol=1e-5))
    for name in sorted(expected):
        if not matches(name, initial.get(name)):
            findings.append('ulog_parameter_readback:' + name)
    for change in changes:
        if type(change) is not list or len(change) != 3 or not isinstance(change[1], str):
            raise ValueError('malformed ULog parameter change')
        _, name, value = change
        if name in expected and not matches(name, value):
            findings.append('ulog_parameter_changed:' + name)
    return findings


def packet_integrity(path):
    """Check every ULog frame, including a truncated final header/payload.

    Deliberately reject appended/segmented logs in this bounded SITL profile.
    This proves framing of the bytes present, not omniscience about the logger.
    """
    packets = 0
    with Path(path).open('rb') as stream:
        header = stream.read(16)
        if len(header) != 16 or header[:8] != b'ULog\x01\x12\x35\x01':
            raise ValueError('unsupported or incomplete ULog header')
        while True:
            header = stream.read(3)
            if not header:
                break
            if len(header) != 3:
                raise ValueError('truncated ULog message header')
            size, kind = struct.unpack('<HB', header)
            body = stream.read(size)
            if len(body) != size:
                raise ValueError('truncated ULog message body')
            if kind not in b'BFIMPQARDLCSO':
                raise ValueError('unknown ULog record type')
            if packets == 0 and kind != ord('B'):
                raise ValueError('missing initial ULog flags')
            if kind == ord('B') and (len(body) < 40 or any(body[8:40])):
                raise ValueError('incompatible or appended ULog data')
            if kind == ord('O'):
                raise ValueError('ULog dropout invalidates parameter history')
            if kind == ord('P'):
                if not body or len(body) != 1 + body[0] + 4:
                    raise ValueError('malformed typed ULog parameter')
                key = body[1:1+body[0]].decode('ascii')
                scalar, separator, name = key.partition(' ')
                if scalar not in ('float', 'int32_t') or not separator or not name:
                    raise ValueError('invalid ULog parameter key')
            packets += 1
        if not packets:
            raise ValueError('empty ULog')
        return dict(complete_frames=True, packets=packets, bytes=stream.tell())


class _TrackedLogReader:
    """Require a clean EOF read; pyulog otherwise swallows some struct errors."""
    def __init__(self, path):
        self.stream = Path(path).open('rb')
        self.eof = False
        self.closed_at = None

    def read(self, size=-1):
        data = self.stream.read(size)
        if size != 0 and not data:
            self.eof = True
        return data

    def seek(self, *args):
        self.eof = False
        return self.stream.seek(*args)

    def tell(self):
        return self.stream.tell()

    def close(self):
        if not self.stream.closed:
            self.closed_at = self.stream.tell()
            self.stream.close()


def extract_ulog_parameters(path, nonce, relative_file):
    """Used in the producer and a fresh, isolated auditor process."""
    from pyulog import ULog  # available only in the pinned SITL image
    health = packet_integrity(path)
    reader = _TrackedLogReader(path)
    try:
        log = ULog(reader, message_name_filter_list=[
            'vehicle_status', 'vehicle_local_position', 'vehicle_land_detected', 'battery_status'],
            disable_str_exceptions=False)
    finally:
        reader.close()
    if not reader.eof or reader.closed_at != health['bytes']:
        raise ValueError('ULog parser stopped before clean EOF')
    health['parser_clean_eof'] = True
    health.update(corruption=bool(log.file_corruption), dropouts=len(log.dropouts),
                  start_us=int(log.start_timestamp), end_us=int(log.last_timestamp))
    if health['corruption'] or health['dropouts']:
        raise ValueError('incomplete or corrupt ULog parameter history')
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            sha.update(block)
    result = dict(schema='echo5.sitl.ulog-parameters.v1', nonce=nonce,
                  file=relative_file, sha256=sha.hexdigest(),
                  extractor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  initial=log.initial_parameters, changes=log.changed_parameters, health=health)
    return json.loads(json.dumps(result, allow_nan=False))


def reconcile_parameter_evidence(captured, extracted, *, nonce, sha256, start_ns, end_ns):
    if captured != extracted:
        raise ValueError('ULog parameters not independently reconstructible')
    if (captured.get('schema') != 'echo5.sitl.ulog-parameters.v1'
            or captured.get('nonce') != nonce or captured.get('sha256') != sha256):
        raise ValueError('ULog parameter identity mismatch')
    h = captured['health']
    if (h.get('complete_frames') is not True or h.get('parser_clean_eof') is not True
            or h.get('corruption') is not False
            or h.get('dropouts') != 0 or h.get('packets', 0) < 1
            or not 0 < h['start_us']*1000 <= start_ns < end_ns
            or h['end_us']*1000 < end_ns - 60_000_000):
        raise ValueError('ULog history does not cover the measured episode')


def require_parameter_manifest(manifest, relative_file):
    required = {'configuration.json', 'runner.py', 'sitl_parameters.py',
                'out/px4-parameter-adapter.json', 'out/ulog-parameters.json',
                'out/ulog-evidence.json', 'out/' + relative_file}
    if not required <= set(manifest):
        raise ValueError('missing parameter evidence in manifest')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--relative-file', required=True)
    args = parser.parse_args()
    print(json.dumps(extract_ulog_parameters(args.file, args.nonce, args.relative_file), allow_nan=False))
