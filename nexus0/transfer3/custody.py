"""Public-commitment checks and an explicitly public custody rehearsal.

Reuses SIM-3 primitives; does not generate final worlds or private secrets.
Cryptographic consistency is not proof of external custody or publication time.
"""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from echoai.nexus0.sim3.canon import Sim3Error, canonical_bytes, sha256_bytes
from echoai.nexus0.sim3.seal import (
    REHEARSAL_SECRET, REHEARSAL_SALT, protocol_commitment,
    derive_seed, inventory_bytes, inventory_commitment, seal, open_once,
    read_seal,
)


def digest(value):
    if (type(value) is not str or len(value) != 64 or
            any(c not in '0123456789abcdef' for c in value)):
        raise ValueError('expected lowercase SHA-256')
    return value


def validate_notice(notice):
    fields = {'schema', 'kind', 'protocol_sha256', 'protocol_commitment',
              'custodian', 'publication_reference', 'splits'}
    if type(notice) is not dict or set(notice) != fields:
        raise ValueError('notice fields')
    if notice['schema'] != 'transfer3-custody-v1':
        raise ValueError('notice schema')
    if notice['kind'] not in ('rehearsal', 'campaign'):
        raise ValueError('notice kind')
    for key in ('protocol_sha256', 'protocol_commitment'):
        digest(notice[key])
    for key in ('custodian', 'publication_reference'):
        if type(notice[key]) is not str or not notice[key].strip():
            raise ValueError('custodian and external publication reference required')
    splits = notice['splits']
    if type(splits) is not dict or set(splits) != {'B', 'C'}:
        raise ValueError('both reserved splits required')
    for row in splits.values():
        if type(row) is not dict or set(row) != {'count', 'inventory_commitment'}:
            raise ValueError('split fields')
        if type(row['count']) is not int or not 1 <= row['count'] <= 100000:
            raise ValueError('split count')
        digest(row['inventory_commitment'])


def verify_reveal(notice, split, entries, salt):
    """Bind an inventory to the *published* salted commitment, not a local latch.

Does not read worlds, verify their geometry, or establish custody. Intended for
the future examiner after opening; it must not be called to peek at sealed C.
"""
    validate_notice(notice)
    if split not in ('B', 'C'):
        raise ValueError('reserved split required')
    expected = notice['splits'][split]
    if type(entries) is not list or len(entries) != expected['count']:
        raise ValueError('inventory count')
    seen = set()
    for row in entries:
        if type(row) is not dict or set(row) != {'split', 'index', 'package_sha256'}:
            raise ValueError('inventory fields')
        index = row['index']
        if (row['split'] != split or type(index) is not int or
                not 0 <= index < 2**32 or index in seen):
            raise ValueError('inventory split/index')
        seen.add(index)
        digest(row['package_sha256'])
    raw = inventory_bytes(entries)
    if inventory_commitment(salt, raw) != expected['inventory_commitment']:
        raise ValueError('published inventory commitment mismatch')
    return sha256_bytes(raw)


def verify_protocol(notice, protocol_bytes, secret):
    validate_notice(notice)
    actual = sha256_bytes(protocol_bytes)
    if (actual != notice['protocol_sha256'] or
            protocol_commitment(actual, secret) != notice['protocol_commitment']):
        raise ValueError('published protocol commitment mismatch')


def rehearsal():
    """No real worlds, no randomness, no campaign artifacts, no flight."""
    protocol = canonical_bytes({'scope': 'custody-rehearsal-only', 'version': 1})
    inventories = {
        split: [dict(split=split, index=i, package_sha256=sha256_bytes(
            canonical_bytes({'dummy_seed': derive_seed(REHEARSAL_SECRET, split, i)})))
            for i in range(2)] for split in ('B', 'C')}
    notice = dict(schema='transfer3-custody-v1', kind='rehearsal',
                  protocol_sha256=sha256_bytes(protocol),
                  protocol_commitment=protocol_commitment(sha256_bytes(protocol), REHEARSAL_SECRET),
                  custodian='public rehearsal; no custody',
                  publication_reference='not published; test fixture only',
                  splits={s: dict(count=2, inventory_commitment=inventory_commitment(
                      REHEARSAL_SALT, inventory_bytes(rows))) for s, rows in inventories.items()})
    verify_protocol(notice, protocol, REHEARSAL_SECRET)
    states = {}
    with TemporaryDirectory(prefix='echoai-transfer3-rehearsal-') as directory:
        for split, entries in inventories.items():
            inventory_sha = verify_reveal(notice, split, entries, REHEARSAL_SALT)
            path = Path(directory)/f'{split}.json'
            seal(path, split=split, commitment=notice['splits'][split]['inventory_commitment'],
                 inventory_sha256=inventory_sha, custodian=notice['custodian'], n_packages=2)
            with open_once(path):
                verify_reveal(notice, split, entries, REHEARSAL_SALT)
            try:
                with open_once(path):
                    raise AssertionError('second opening allowed')
            except Sim3Error as exc:
                if exc.code != 'seal_already_consumed':
                    raise
            states[split] = read_seal(path).state
    return dict(scope='custody-rehearsal-only', rehearsal_ok=True,
                transfer3_green=False, campaign_created=False,
                campaign_C_opened=False, dummy_states=states, public_notice=notice)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['rehearsal'])
    parser.parse_args()
    print(json.dumps(rehearsal(), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
