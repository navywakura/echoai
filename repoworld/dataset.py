"""Curator-side ingestion; only an allowlisted projection crosses into online use.

Parquet is read by column projection, not loaded and then redacted. This module
does not export, log or store a sealed catalog. Its caller owns that authority.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
from .types import PublicTask

PUBLIC_FIELDS = ('instance_id', 'repo', 'base_commit', 'problem_statement')
DOCS = Path(__file__).resolve().parents[1] / 'repository/docs'


def sha256_file(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def public_task(row: dict) -> PublicTask:
    if not isinstance(row, dict) or any(type(row.get(k)) is not str for k in PUBLIC_FIELDS):
        raise ValueError('invalid public task schema')
    repo = row['repo']
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', repo) or repo.split('/')[1] in ('.','..'):
        raise ValueError('invalid repository')
    if not re.fullmatch(re.escape(repo.replace('/', '__')) + r'-[0-9]+', row['instance_id']):
        raise ValueError('instance/repository mismatch')
    if not re.fullmatch(r'[0-9a-f]{40}', row['base_commit']):
        raise ValueError('full base commit required')
    if not row['problem_statement'] or len(row['problem_statement'].encode('utf-8')) > 256*1024:
        raise ValueError('missing or oversized public issue')
    return PublicTask(**{k:row[k] for k in PUBLIC_FIELDS})


def _unique(rows):
    seen = set()
    for row in rows:
        task = public_task(row)
        if task.instance_id in seen:
            raise ValueError('duplicate instance ID')
        seen.add(task.instance_id)
        yield task


def read_fixed_dataset(path: Path, expected_sha256: str) -> list[dict]:
    path = Path(path)
    if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256) or sha256_file(path) != expected_sha256:
        raise ValueError('dataset hash mismatch')
    # Path and containing directory are curator capabilities, never tool inputs.
    if path.suffix == '.parquet':
        import pyarrow.parquet as pq
        rows = pq.read_table(path, columns=list(PUBLIC_FIELDS)).to_pylist()
    elif path.suffix == '.json':
        if path.stat().st_size > 64*1024*1024:
            raise ValueError('JSON dataset exceeds limit')
        rows = json.loads(path.read_bytes())
    else:
        raise ValueError('unsupported dataset format')
    if type(rows) is not list or len(rows) > 10000:
        raise ValueError('incompatible dataset schema')
    result = [asdict(task) for task in _unique(rows)]
    if sha256_file(path) != expected_sha256:
        raise ValueError('dataset changed during read')
    return result


def select_public_tasks(rows: list[dict], roster: list[dict]) -> list[PublicTask]:
    tasks = {t.instance_id:t for t in _unique(rows)}
    selected, seen = [], set()
    for entry in roster:
        identifier = entry.get('instance_id')
        if identifier in seen or identifier not in tasks:
            raise ValueError('missing or duplicate roster ID')
        seen.add(identifier)
        task = tasks[identifier]
        if task.repo != entry.get('repo') or task.base_commit != entry.get('base_commit'):
            raise ValueError('roster identity mismatch')
        selected.append(task)
    return selected


def sample_roster(sample):
    """Flatten all registered groups; sealed runtime must cover every one."""
    result = list(sample['primary']) + list(sample['calibration'])
    for chain in sample['memory_chains']:
        result.append(chain['donor'])
        result.extend(chain['targets'])
    return result


def validate_launch(contract: dict, sample_path: Path, lock: dict | None,
                    *, contract_sha256: str | None = None):
    """Registration gate, not a substitute for later runtime/custody preflight.

Callers must provide the SHA of the exact on-disk sealed contract. Deliberately
no convenience override for the design proposal or for local calibration.
"""
    if contract.get('status') != 'sealed' or contract.get('launch_enabled') is not True:
        raise ValueError('design contract cannot launch')
    if lock is None or contract_sha256 is None:
        raise ValueError('sealed lock and exact contract digest required')
    import jsonschema
    try:
        jsonschema.Draft202012Validator(json.loads((DOCS/'swebench/SWE-RUN-LOCK.schema.json').read_text())).validate(lock)
    except jsonschema.ValidationError as e:
        raise ValueError('invalid run lock') from e
    sample_hash = sha256_file(sample_path)
    if sample_hash != contract['dataset']['sample_sha256'] or lock['sample_sha256'] != sample_hash:
        raise ValueError('sample hash mismatch')
    if lock['contract_sha256'] != contract_sha256 or lock['model_sha256'] != contract['model']['sha256']:
        raise ValueError('contract/model hash mismatch')
    if lock['harness_commit'] != contract['harness']['commit']:
        raise ValueError('harness mismatch')
    roster = sample_roster(json.loads(Path(sample_path).read_bytes()))
    expected = {e['instance_id']:e['base_commit'] for e in roster}
    actual = {e['instance_id']:e['base_commit'] for e in lock['instances']}
    if len(expected) != len(roster) or len(actual) != len(lock['instances']) or actual != expected:
        raise ValueError('lock roster/commit mismatch')
    return True
