"""Strict compact JSON controls retaining the complete WSP Archive information."""
import base64
import binascii
import hashlib
import hmac
import zlib

from ..wspfiles import codec as wsp

LAYOUTS = ('b64-rows', 'b64-columns', 'b85-columns')


def _layout(layout):
    wsp.require(type(layout) is str and layout in LAYOUTS, 'unknown JSON layout')


def _text(raw, layout):
    fn = base64.b85encode if layout == 'b85-columns' else base64.b64encode
    return fn(raw).decode('ascii')


def _bytes(text, layout):
    wsp.require(type(text) is str, 'encoded packet string required')
    try:
        encoded = text.encode('ascii')
        raw = (base64.b85decode(encoded) if layout == 'b85-columns'
               else base64.b64decode(encoded, validate=True))
        wsp.require(_text(raw, layout) == text, 'noncanonical packet encoding')
        return raw
    except (UnicodeError, binascii.Error, ValueError) as exc:
        raise ValueError('invalid packet encoding') from exc


def encode(archive, layout, *, integrity=True, compressed=False):
    _layout(layout)
    wsp.require(type(integrity) is bool and type(compressed) is bool, 'boolean options required')
    wsp.encode(archive)  # Apply exactly the original Archive type and size limits.
    data = [1, archive.profile, archive.provenance, archive.metadata]
    if layout == 'b64-rows':
        data.append([[_text(r.packet, layout), r.metadata] for r in archive.records])
    else:
        data.extend((_text(b''.join(r.packet for r in archive.records), layout),
                     [r.metadata for r in archive.records]))
    raw = wsp.dumps(data)
    if integrity:
        raw += hashlib.sha256(raw).digest()
    wsp.require(len(raw) <= wsp.MAX_FILE, 'JSON file exceeds limit')
    return zlib.compress(raw, 9) if compressed else raw


def decode(raw, layout, *, integrity=True, compressed=False):
    _layout(layout)
    wsp.require(type(integrity) is bool and type(compressed) is bool, 'boolean options required')
    wsp.require(type(raw) is bytes and len(raw) <= wsp.MAX_FILE, 'file bytes/size required')
    if compressed:
        raw = wsp.decompress(raw)
    if integrity:
        wsp.require(len(raw) >= 32, 'missing checksum')
        payload, checksum = raw[:-32], raw[-32:]
        wsp.require(hmac.compare_digest(hashlib.sha256(payload).digest(), checksum),
                    'JSON checksum mismatch')
        raw = payload
    data = wsp.loads(raw)
    expected = 5 if layout == 'b64-rows' else 6
    wsp.require(type(data) is list and len(data) == expected, 'positional archive schema')
    version, profile, provenance, metadata = data[:4]
    wsp.require(type(version) is int and version == 1, 'unknown JSON archive version')
    records = []
    if layout == 'b64-rows':
        rows = data[4]
        wsp.require(type(rows) is list and len(rows) <= wsp.MAX_RECORDS, 'record count/type')
        for row in rows:
            wsp.require(type(row) is list and len(row) == 2, 'record schema')
            packet = _bytes(row[0], layout)
            wsp.require(len(packet) == 16, 'packet length')
            records.append(wsp.Record(packet, row[1]))
    else:
        block, metas = _bytes(data[4], layout), data[5]
        wsp.require(len(block) % 16 == 0 and len(block) // 16 <= wsp.MAX_RECORDS, 'packet block length')
        wsp.require(type(metas) is list and len(metas) == len(block) // 16, 'metadata count/type')
        records = [wsp.Record(block[i*16:(i+1)*16], meta) for i, meta in enumerate(metas)]
    archive = wsp.Archive(profile, provenance, tuple(records), metadata)
    wsp.encode(archive)  # Validate all descriptors, metadata objects and bounds.
    return archive
