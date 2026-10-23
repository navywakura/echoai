#!/usr/bin/env python3
"""Retry only infrastructure failures of a signed all-instance curator gate.

No actor or LLM runs. Original failures remain immutable. Graded failures are
retained, never retried here, and keep the aggregate invalid. The aggregate
records both attempts, this utility's digest and the parent custody receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / 'repository/scripts/run_repoworld.py'), run_name='bootstrap')
from echoai.pcworld.receipts import canonical, _atomic_write
from echoai.repoworld.calibration import source_manifest
from echoai.repoworld.dataset import sample_roster, sha256_file
from echoai.repoworld.evaluator import CuratorCapability, HARNESS_COMMIT, curator_command, existing_receipts
from echoai.repoworld.study import write_gate

# Graded failures, assertion failures and timeouts are deliberately excluded.
RETRYABLE = {'BuildImageError', 'APIError', 'ImageNotFound', 'official_image_missing'}


def authenticated_parent(directory):
    directory = Path(directory)
    envelope = json.loads((directory / 'report.json').read_bytes())
    report = envelope['report']
    records = existing_receipts(directory).records
    if not any(r['sha256'] == envelope['receipt_id'] and
               r['body'] == {'event': 'repoworld.gate', 'report': report} for r in records):
        raise ValueError('parent custody authentication failed')
    if report['kind'] != 'official-controls' or report.get('scope') != 'all':
        raise ValueError('parent must cover the full official roster')
    if report.get('source_unchanged') is not True or report['source_manifest'] != source_manifest():
        raise ValueError('parent curator sources changed; repeat controls')
    return envelope


def select_failures(report, roster):
    expected = {r['instance_id']: r['base_commit'] for r in roster}
    rows = report['results']
    if len(rows) != len(expected) or {r['instance_id'] for r in rows} != set(expected):
        raise ValueError('parent roster is incomplete or duplicated')
    failed = []
    for row in rows:
        if row['base_commit'] != expected[row['instance_id']]:
            raise ValueError('base commit changed')
        if row.get('valid') is True:
            if row.get('error') or row.get('empty_patch_resolved') is not False or row.get('gold_patch_resolved') is not True:
                raise ValueError('inconsistent passing control')
            if set(row.get('controls', {})) != {'empty', 'gold'} or not all(v.get('valid') is True for v in row['controls'].values()):
                raise ValueError('missing control evidence')
        elif row.get('error') in RETRYABLE:
            failed.append(row['instance_id'])
        # A graded/non-infrastructure failure remains in the original report.
        # It is neither rerun nor converted into success by an unrelated retry.
    if not failed:
        raise ValueError('no infrastructure failure to retry')
    return failed


def run(args):
    frozen = source_manifest()
    envelope = authenticated_parent(args.parent)
    parent = envelope['report']
    contract = json.loads(args.contract.read_bytes())
    sample = json.loads(args.sample.read_bytes())
    roster = sample_roster(sample)
    if parent['sample_sha256'] != sha256_file(args.sample) or parent['dataset_sha256'] != contract['dataset']['parquet_sha256']:
        raise ValueError('parent sample/dataset mismatch')
    failed = select_failures(parent, roster)
    cap_data = json.loads(args.curator.read_bytes())
    for key in ('python', 'harness', 'dataset', 'output'):
        cap_data[key] = Path(cap_data[key])
    cap = CuratorCapability(**cap_data)
    request = json.loads((args.parent / 'request.json').read_bytes())
    if (request['harness'] != str(cap.harness.resolve()) or
        request['dataset'] != str(cap.dataset.resolve()) or
        request['dataset_sha256'] != cap.dataset_sha256 or
        cap.dataset_sha256 != parent['dataset_sha256'] or
        sha256_file(cap.dataset) != cap.dataset_sha256 or
        request.get('evict_pulled_images', False) != cap.evict_pulled_images):
        raise ValueError('curator capability differs from original request')
    commit = subprocess.check_output(['git', '-C', str(cap.harness), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(cap.harness), 'status', '--porcelain', '--untracked-files=no'])
    if commit != HARNESS_COMMIT or dirty or parent['harness_commit'] != commit:
        raise ValueError('official harness changed')
    service = os.environ.get('REPOWORLD_CURATOR_SERVICES')
    service_sha = os.environ.get('REPOWORLD_CURATOR_SERVICES_SHA256')
    if not service or sha256_file(Path(service)) != service_sha:
        raise ValueError('pinned service manifest required')
    for row in parent['results']:
        if row.get('service_manifest_sha256') not in (None, service_sha):
            raise ValueError('service profile changed')
        if row['valid']:
            for kind, evidence in row['controls'].items():
                path = args.parent / row['instance_id'] / kind / 'test_output.txt'
                if sha256_file(path) != evidence['log_sha256']:
                    raise ValueError('retained control evidence changed')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    retry = args.output / 'retry'
    retry.mkdir(mode=0o700)
    request = {**request, 'instances': [r for r in request['instances'] if r['instance_id'] in failed]}
    if {r['instance_id'] for r in request['instances']} != set(failed):
        raise ValueError('retry request mismatch')
    _atomic_write(retry / 'request.json', canonical(request))
    env = dict(os.environ)
    if cap.docker_host:
        env['DOCKER_HOST'] = cap.docker_host
    with (retry / 'curator-private.log').open('wb') as log:
        proc = subprocess.run(curator_command(cap.python, '--controls', str((retry / 'request.json').resolve())),
                              cwd=retry, env=env, stdout=log, stderr=log, timeout=3600)
    if proc.returncode:
        raise RuntimeError('retry curator failed; private diagnostic retained')
    rows = json.loads((retry / 'controls.json').read_bytes())
    if len(rows) != len(failed) or {r['instance_id'] for r in rows} != set(failed):
        raise ValueError('retry result roster mismatch')
    replacements = {r['instance_id']: r for r in rows}
    original = {r['instance_id']: r for r in parent['results']}
    for iid, row in replacements.items():
        for key in ('base_commit', 'official_image_digest', 'official_eval_script_sha256', 'sealed_tests_sha256'):
            if key in original[iid] and row.get(key) != original[iid][key]:
                raise ValueError('retry changed frozen identity: ' + key)
    retry_gate = write_gate(retry, dict(kind='official-controls-infrastructure-retry', valid=all(r['valid'] for r in rows),
        results=rows, parent_receipt_id=envelope['receipt_id'], request_sha256=sha256_file(retry/'request.json'),
        private_log_sha256=sha256_file(retry/'curator-private.log'), gpu_hours=0, llm_calls=0), source_before=frozen)
    merged = [replacements.get(r['instance_id'], r) for r in parent['results']]
    report = {k: v for k, v in parent.items() if k not in ('source_manifest', 'source_unchanged', 'results', 'valid')}
    report.update(results=merged, valid=retry_gate['valid'] and all(r['valid'] for r in merged),
        parent_directory=str(args.parent.resolve()), parent_report_sha256=sha256_file(args.parent/'report.json'),
        parent_receipt_id=envelope['receipt_id'], retry_report_sha256=sha256_file(retry/'report.json'),
        retry_utility_sha256=sha256_file(Path(__file__)), retried_instances=failed,
        original_attempts=len(parent['results']), retry_attempts=len(rows),
        evidence_directories={r['instance_id']: str((retry if r['instance_id'] in failed else args.parent).resolve()) for r in merged})
    return write_gate(args.output, report, source_before=frozen)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent', 'curator', 'contract', 'sample', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    result = run(parser.parse_args())
    print(json.dumps({k: result[k] for k in ('valid', 'retried_instances', 'original_attempts', 'retry_attempts', 'source_unchanged')}, indent=2))
    raise SystemExit(0 if result['valid'] else 1)
