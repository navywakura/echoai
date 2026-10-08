"""Plan C1 custodian. RUN THIS ONLY WHERE NEITHER AGENT CAN READ YOUR FILES.

Public code, private state. Nothing secret lives in this file: the secret and
the salts are written to a private bundle on the custodian's own machine and
never leave it except as the final `secret` reveal, after the campaign is over.

Commit-reveal, in strict order:

    init     -> private bundle: 32-byte secret, one 32-byte salt per split
    commit   -> PUBLIC notice: protocol commitment + salted B/C inventory
                commitments. Publish it, with a date, outside the agents' tree.
    reveal B -> B's seeds, inventory and salt, handed to the examiner
    reveal C -> only after B has passed
    secret   -> after C, so anyone can check the rooms were fixed in advance

Rooms are derived from the secret by HMAC, so the custodian cannot choose them
after the fact, and the examiner cannot predict them before they are revealed.
"""
import argparse
import json
import os
import secrets
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, loads_strict, sha256_bytes
from echoai.nexus0.sim3.seal import (derive_seed, inventory_bytes, inventory_commitment,
                                     protocol_commitment)
from .custody import validate_notice
from .rehearsal_v2 import shape
from .space_a2 import Room, feasible
from .camera_c1 import declared_body

SPLITS = ('B', 'C')
MAX_ATTEMPTS_PER_ROOM = 200


def package_sha(room):
    return sha256_bytes(canonical_bytes(dict(seed=room['seed'], shape=room['shape'])))


def generate_split(secret, split, count, excluded):
    """Deterministic in (secret, split, count, excluded). Same code on both sides."""
    if type(secret) is not bytes or len(secret) != 32:
        raise ValueError('secret must be 32 bytes')
    seen, accepted, attempt = set(excluded), [], 0
    while len(accepted) < count:
        if attempt >= count*MAX_ATTEMPTS_PER_ROOM:
            raise ValueError('room generation exhausted; no fallback')
        seed = derive_seed(secret, split, attempt)
        attempt += 1
        room = Room(seed, declared_body())
        if feasible(room) is not None:
            continue
        fingerprint = shape(room)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        accepted.append(dict(seed=seed, shape=fingerprint))
    return accepted


def inventory(split, rooms):
    return [dict(split=split, index=i, package_sha256=package_sha(r)) for i, r in enumerate(rooms)]


def commit(secret, salts, protocol_bytes, *, kind, custodian, publication_reference):
    protocol = loads_strict(protocol_bytes)
    rooms = {}
    taken = list(protocol['excluded_shapes'])
    for split in SPLITS:
        rooms[split] = generate_split(secret, split, protocol['counts'][split], taken)
        taken += [r['shape'] for r in rooms[split]]
    digest = sha256_bytes(protocol_bytes)
    notice = dict(schema='transfer3-custody-v1', kind=kind, protocol_sha256=digest,
                  protocol_commitment=protocol_commitment(digest, secret),
                  custodian=custodian, publication_reference=publication_reference,
                  splits={s: dict(count=len(rooms[s]), inventory_commitment=inventory_commitment(
                      salts[s], inventory_bytes(inventory(s, rooms[s])))) for s in SPLITS})
    validate_notice(notice)
    return notice, rooms


def reveal(rooms, salts, split):
    if split not in SPLITS:
        raise ValueError('split')
    return dict(split=split, rooms=rooms[split], entries=inventory(split, rooms[split]),
                salt=salts[split].hex())


def _write_private(path, value):
    path = Path(path)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical_bytes(value))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('init', help='create the private bundle')
    a.add_argument('bundle', type=Path)
    c = sub.add_parser('commit', help='write the PUBLIC notice from a protocol file')
    c.add_argument('bundle', type=Path)
    c.add_argument('protocol', type=Path)
    c.add_argument('notice', type=Path)
    c.add_argument('--custodian', required=True)
    c.add_argument('--publication-reference', required=True)
    r = sub.add_parser('reveal', help='hand one split to the examiner')
    r.add_argument('bundle', type=Path)
    r.add_argument('protocol', type=Path)
    r.add_argument('split', choices=SPLITS)
    r.add_argument('out', type=Path)
    s = sub.add_parser('secret', help='after C: publish the secret for verification')
    s.add_argument('bundle', type=Path)
    s.add_argument('out', type=Path)
    args = p.parse_args()

    if args.command == 'init':
        _write_private(args.bundle, dict(secret=secrets.token_bytes(32).hex(),
                                         salts={s: secrets.token_bytes(32).hex() for s in SPLITS}))
        print('private bundle written; never copy it where an agent can read it')
        return
    bundle = loads_strict(args.bundle.read_bytes())
    secret = bytes.fromhex(bundle['secret'])
    salts = {k: bytes.fromhex(v) for k, v in bundle['salts'].items()}
    if args.command == 'secret':
        _write_private(args.out, dict(secret=bundle['secret']))
        print('secret written for final verification')
        return
    protocol_bytes = args.protocol.read_bytes()
    if args.command == 'commit':
        notice, _ = commit(secret, salts, protocol_bytes, kind='campaign',
                           custodian=args.custodian, publication_reference=args.publication_reference)
        with args.notice.open('xb') as stream:
            stream.write(canonical_bytes(notice))
        print(json.dumps(notice, indent=2, sort_keys=True))
        return
    protocol = loads_strict(protocol_bytes)
    rooms = {}
    taken = list(protocol['excluded_shapes'])
    for split in SPLITS:
        rooms[split] = generate_split(secret, split, protocol['counts'][split], taken)
        taken += [r['shape'] for r in rooms[split]]
    with args.out.open('xb') as stream:
        stream.write(canonical_bytes(reveal(rooms, salts, args.split)))
    print(f'reveal {args.split} written: {len(rooms[args.split])} rooms')


if __name__ == '__main__':
    main()
