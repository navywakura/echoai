"""WSP file v1: bounded archival storage, never an authority or event bus."""
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import struct
import zlib

MAGIC = b'ECHOWSP\0'
HEADER = struct.Struct('<8sHHIII')
VERSION = 1
MAX_FILE = 64 * 1024 * 1024
MAX_DESCRIPTOR = 8 * 1024 * 1024
MAX_METADATA = 32 * 1024 * 1024
MAX_RECORDS = 100000
PROFILES = frozenset(('wsp16-session-v1', 'memx-replay-v1'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Record:
    packet: bytes
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Archive:
    profile: str
    provenance: dict
    records: tuple
    metadata: dict = field(default_factory=dict)


def json_value(value, depth=0):
    require(depth <= 32, 'JSON depth exceeds 32')
    if value is None or type(value) in (bool, int):
        return
    if type(value) is str:
        try: value.encode('utf-8')
        except UnicodeError as exc: raise ValueError('invalid UTF-8 string') from exc
        return
    if type(value) is float:
        require(math.isfinite(value), 'nonfinite JSON number'); return
    if type(value) is dict:
        require(len(value) <= MAX_RECORDS, 'JSON collection too large')
        for key, item in value.items():
            require(type(key) is str, 'JSON key must be string')
            json_value(key, depth + 1); json_value(item, depth + 1)
        return
    if type(value) is list:
        require(len(value) <= MAX_RECORDS, 'JSON collection too large')
        for item in value: json_value(item, depth + 1)
        return
    raise ValueError('unsupported JSON type')


def dumps(value):
    json_value(value)
    try: return json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, UnicodeError, RecursionError) as exc: raise ValueError('invalid JSON') from exc


def _pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, 'duplicate JSON key')
        out[key] = value
    return out


def _constant(value):
    raise ValueError('nonfinite JSON constant')


def loads(data):
    require(type(data) in (str, bytes), 'JSON bytes or string required')
    try:
        if type(data) is bytes: data = data.decode('utf-8')
        require(len(data.encode('utf-8')) <= MAX_FILE, 'JSON exceeds file limit')
        value = json.loads(data, object_pairs_hook=_pairs, parse_constant=_constant)
        json_value(value)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise ValueError('invalid JSON document') from exc


def _descriptor(a):
    require(type(a) is Archive, 'Archive required')
    require(type(a.profile) is str and a.profile in PROFILES, 'unknown interpretation profile')
    require(type(a.provenance) is dict and type(a.metadata) is dict, 'descriptor objects required')
    return {'profile': a.profile, 'provenance': a.provenance, 'metadata': a.metadata}


def _validate(a):
    descriptor = dumps(_descriptor(a))
    require(len(descriptor) <= MAX_DESCRIPTOR, 'descriptor exceeds limit')
    require(type(a.records) is tuple and len(a.records) <= MAX_RECORDS, 'record count/type limit')
    for r in a.records:
        require(type(r) is Record and type(r.packet) is bytes and len(r.packet) == 16,
                'packet must be original sixteen bytes')
        require(type(r.metadata) is dict, 'record metadata object required')
        json_value(r.metadata)
    return descriptor


def encode(a):
    descriptor = _validate(a)
    metadata = dumps([r.metadata for r in a.records])
    require(len(metadata) <= MAX_METADATA, 'record metadata exceeds limit')
    size = HEADER.size + len(descriptor) + 16 * len(a.records) + len(metadata) + 32
    require(size <= MAX_FILE, 'file exceeds limit')
    prefix = HEADER.pack(MAGIC, VERSION, 0, len(a.records), len(descriptor), len(metadata))
    raw = prefix + descriptor + b''.join(r.packet for r in a.records) + metadata
    return raw + hashlib.sha256(raw).digest()


def _envelope(raw):
    require(type(raw) is bytes, 'file bytes required')
    require(HEADER.size + 32 <= len(raw) <= MAX_FILE, 'file size out of bounds')
    magic, version, flags, count, nd, nm = HEADER.unpack_from(raw)
    require(magic == MAGIC and version == VERSION and flags == 0, 'incompatible WSP file header')
    require(count <= MAX_RECORDS and nd <= MAX_DESCRIPTOR and nm <= MAX_METADATA, 'declared size limit')
    require(HEADER.size + nd + 16 * count + nm + 32 == len(raw), 'truncated or trailing WSP file')
    require(hmac.compare_digest(hashlib.sha256(raw[:-32]).digest(), raw[-32:]), 'WSP checksum mismatch')
    desc = loads(raw[HEADER.size:HEADER.size + nd])
    require(type(desc) is dict and set(desc) == {'profile', 'provenance', 'metadata'}, 'descriptor schema')
    _descriptor(Archive(desc['profile'], desc['provenance'], (), desc['metadata']))
    return desc, count, HEADER.size + nd, nm


def decode(raw):
    desc, count, start, nm = _envelope(raw)
    meta = loads(raw[start + 16 * count:len(raw) - 32])
    require(type(meta) is list and len(meta) == count, 'record metadata count mismatch')
    require(all(type(item) is dict for item in meta), 'record metadata objects required')
    records = tuple(Record(raw[start + 16*i:start + 16*(i+1)], item) for i, item in enumerate(meta))
    return Archive(desc['profile'], desc['provenance'], records, desc['metadata'])


def packet_at(raw, index):
    """Verify envelope/hash; return packet without interpreting record metadata."""
    _, count, start, _ = _envelope(raw)
    require(type(index) is int and 0 <= index < count, 'packet index out of bounds')
    return raw[start + 16*index:start + 16*(index+1)]


def to_json(a):
    _validate(a)
    raw = dumps([1, a.profile, a.provenance, a.metadata,
                 [[r.packet.hex(), r.metadata] for r in a.records]])
    require(len(raw) <= MAX_FILE, 'JSON file exceeds limit')
    return raw.decode('utf-8')


def from_json(text):
    data = loads(text)
    require(type(data) is list and len(data) == 5, 'positional archive schema')
    v, profile, provenance, metadata, rows = data
    require(type(v) is int and v == 1, 'unknown JSON archive version')
    require(type(rows) is list and len(rows) <= MAX_RECORDS, 'JSON records required')
    records = []
    for r in rows:
        require(type(r) is list and len(r) == 2 and type(r[0]) is str
                and re.fullmatch('[0-9a-f]{32}', r[0]), 'packet hex schema')
        records.append(Record(bytes.fromhex(r[0]), r[1]))
    a = Archive(profile, provenance, tuple(records), metadata)
    descriptor = _validate(a)
    metadata_size = len(dumps([r.metadata for r in a.records]))
    require(metadata_size <= MAX_METADATA, 'record metadata exceeds limit')
    require(HEADER.size + len(descriptor) + 16*len(records) + metadata_size + 32 <= MAX_FILE,
            'imported file exceeds limit')
    return a


def read_bytes(path):
    with Path(path).open('rb') as f:
        require(f.seek(0, 2) <= MAX_FILE, 'file exceeds limit')
        f.seek(0)
        raw = f.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, 'file exceeds limit')
    return raw


def write(path, archive):
    raw = encode(archive)
    with Path(path).open('xb') as f: f.write(raw)
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return decode(read_bytes(path))


def decompress(raw, *, limit=None):
    if limit is None: limit = MAX_FILE
    require(type(raw) is bytes and len(raw) <= MAX_FILE, 'compressed input limit')
    require(type(limit) is int and 0 < limit <= MAX_FILE, 'expansion limit')
    try:
        d = zlib.decompressobj()
        out = d.decompress(raw, limit + 1)
        require(len(out) <= limit and d.eof and not d.unused_data and not d.unconsumed_tail,
                'compressed truncation, trailing data or expansion limit')
        return out
    except zlib.error as exc: raise ValueError('corrupt compressed data') from exc
