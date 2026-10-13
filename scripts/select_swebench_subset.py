#!/usr/bin/env python3
"""Select a prospective panel from public metadata only; no model or test scores."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path

FIELDS = {'instance_id', 'repo', 'base_commit', 'created_at', 'version',
          'environment_setup_commit'}
SEED = 20261013


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False).encode()).hexdigest()


def select(metadata, seed=SEED, size=24):
    rows = metadata['instances']
    if len(rows) != 300 or any(set(r) != FIELDS for r in rows):
        raise ValueError('Require exactly the 300 metadata-only Lite records')
    if len({r['instance_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate instance ID')
    counts = Counter(r['repo'] for r in rows)
    if not len(counts) <= size <= len(rows):
        raise ValueError('Cannot allocate at least one per repository')
    # One per repository, then Hamilton allocation of the remaining places.
    ideals = {repo: Fraction((size-len(counts))*n, len(rows)) for repo,n in counts.items()}
    quotas = {repo: 1 + int(value) for repo,value in ideals.items()}
    left = size - sum(quotas.values())
    for repo in sorted(counts, key=lambda r: (-(ideals[r]-int(ideals[r])), r))[:left]:
        quotas[repo] += 1
    if any(quotas[r] > counts[r] for r in counts):
        raise ValueError('Allocation exceeds a stratum')

    def rank(row, purpose):
        return hashlib.sha256(f'{seed}:{purpose}:{row["instance_id"]}'.encode()).hexdigest()

    primary = []
    for repo in sorted(counts):
        primary += sorted((r for r in rows if r['repo'] == repo),
                          key=lambda r: (rank(r,'primary'),r['instance_id']))[:quotas[repo]]
    used = {r['instance_id'] for r in primary}
    calibration = []
    for repo in ['pallets/flask','psf/requests','pytest-dev/pytest','sympy/sympy']:
        pool = [r for r in rows if r['repo'] == repo and r['instance_id'] not in used]
        row = min(pool, key=lambda r: (rank(r,'calibration'),r['instance_id']))
        calibration.append(row); used.add(row['instance_id'])
    chains = []
    for repo in ['pytest-dev/pytest', 'sympy/sympy']:
        pool = sorted((r for r in rows if r['repo'] == repo and r['instance_id'] not in used),
                      key=lambda r: (r['created_at'],r['instance_id']))
        donor = pool[0]
        candidates = [r for r in pool[1:] if r['created_at'] > donor['created_at']]
        targets = sorted(sorted(candidates, key=lambda r: (rank(r,'memory'),r['instance_id']))[:3],
                         key=lambda r: (r['created_at'],r['instance_id']))
        if len(targets) != 3: raise ValueError('Insufficient later memory targets')
        chains.append(dict(chain_id=repo.replace('/','__'), donor=donor, targets=targets))
        used.update(r['instance_id'] for r in [donor,*targets])
    return dict(schema_version='repoworld.sample.v1', seed=seed,
                metadata_sha256=digest(sorted(rows,key=lambda r:r['instance_id'])),
                dataset=metadata['dataset'], revision=metadata['revision'], split=metadata['split'],
                selection='one-per-repo-plus-Hamilton; SHA256 seed:purpose:instance_id',
                population_by_repo=dict(sorted(counts.items())),
                allocation_by_repo=dict(sorted(quotas.items())),
                primary=primary, calibration=calibration, memory_chains=chains,
                replacements_allowed=False, environment_eligibility='not yet executed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = select(json.loads(args.metadata.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(f'{len(result["primary"])} primary issues; 4 calibration; 2 donor/3-target chains')
