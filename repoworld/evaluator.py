"""Final curator only. No official bytes are loaded before the global barrier."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from ..pcworld.receipts import ReceiptStore, canonical, _atomic_write
from .dataset import sha256_file

HARNESS_COMMIT='726c5461e2ef52d83cf1ea2107870a8bb3328d57'


def strict_verdict(*,raw_resolved,patch_applied,custody_valid,environment_valid,budget_valid,fail_to_pass,pass_to_pass,states):
    required=list(fail_to_pass)+list(pass_to_pass)
    missing=[t for t in required if states.get(t) not in ('PASSED','XFAIL')]
    conditions=dict(upstream_resolved=raw_resolved is True,patch_applied=patch_applied is True,
        custody=custody_valid is True,environment=environment_valid is True,budget=budget_valid is True,
        nonempty_f2p=bool(fail_to_pass),all_tests_observed=not missing)
    return dict(official_raw_resolved=raw_resolved is True,echo_verified_resolved=all(conditions.values()),
        validity_reason=','.join(k for k,v in conditions.items() if not v) or 'verified-under-declared-test-semantics',
        missing_or_not_passing=missing,required_count=len(required))


def existing_receipts(directory):
    directory=Path(directory)
    if not (directory/'authority/authority.json').is_file() or not (directory/'receipts/receipts.jsonl').is_file():
        raise ValueError('existing custody authority and journal required; auditor never creates keys')
    return ReceiptStore(directory/'receipts',directory/'authority')


def freeze_set(directory,schedule,submissions,*,lock_sha256):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    ids=[r['cell_id'] for r in schedule]
    if len(set(ids))!=len(ids) or set(submissions)!=set(ids):raise ValueError('global barrier: all scheduled cells must be frozen')
    if any(not re.fullmatch('[A-Za-z0-9_-]{1,200}',k) for k in ids):raise ValueError('cell identifier')
    if (directory/'freeze.json').exists():
        validate_frozen_set(directory,schedule,lock_sha256=lock_sha256)
        return json.loads((directory/'freeze.json').read_bytes())
    store=ReceiptStore(directory/'receipts',directory/'authority');patches=directory/'patches';patches.mkdir(exist_ok=True)
    entries={}
    for identifier in ids:
        submission=submissions[identifier];raw=submission['model_patch'].encode('utf-8')
        if len(raw)>512*1024:raise ValueError('final patch capacity')
        _atomic_write(patches/(identifier+'.diff'),raw)
        entries[identifier]=dict(instance_id=submission['instance_id'],arm=submission['arm'],
            diff_sha256=hashlib.sha256(raw).hexdigest(),submission_sha256=hashlib.sha256(canonical(submission)).hexdigest())
    value=dict(schema='repoworld.frozen-set.v1',lock_sha256=lock_sha256,
        schedule_sha256=hashlib.sha256(canonical(schedule)).hexdigest(),entries=entries)
    receipt=store.append(dict(event='repoworld.global-freeze',value=value))
    frozen=dict(value=value,receipt_id=receipt['sha256']);_atomic_write(directory/'freeze.json',canonical(frozen))
    return frozen


def validate_frozen_set(directory,schedule,*,lock_sha256):
    directory=Path(directory);store=existing_receipts(directory)
    frozen=json.loads((directory/'freeze.json').read_bytes());value=frozen['value']
    records=store.records
    if not any(r['sha256']==frozen['receipt_id'] and r['body']==dict(event='repoworld.global-freeze',value=value) for r in records):raise ValueError('freeze custody mismatch')
    if value['lock_sha256']!=lock_sha256 or value['schedule_sha256']!=hashlib.sha256(canonical(schedule)).hexdigest():raise ValueError('freeze lock/schedule mismatch')
    if set(value['entries'])!={r['cell_id'] for r in schedule}:raise ValueError('incomplete freeze')
    for key,row in value['entries'].items():
        if sha256_file(directory/'patches'/(key+'.diff'))!=row['diff_sha256']:raise ValueError('frozen diff changed')
    return True


@dataclass(frozen=True)
class CuratorCapability:
    python: Path
    harness: Path
    dataset: Path
    dataset_sha256: str
    output: Path
    docker_host: str | None = None
    evict_pulled_images: bool = False


def curator_command(python,*arguments):
    # Resolving a venv's Python symlink selects the host prefix and loses its
    # pinned packages. Keep the absolute launcher path, including its venv.
    return [str(Path(python).absolute()),'-I',str(Path(__file__).with_name('official_curator.py').resolve()),*arguments]


def evaluate_sealed(directory,schedule,*,curator_capability,run_lock):
    """Invoke the pinned official harness in a distinct curator process.

    Both the dataset and hidden test identities stay in that process. Results
    are readable by the auditor only after every registered patch is frozen.
    """
    cap=curator_capability;directory=Path(directory)
    lock_sha=hashlib.sha256(canonical(run_lock)).hexdigest()
    validate_frozen_set(directory,schedule,lock_sha256=lock_sha)
    if sha256_file(cap.dataset)!=cap.dataset_sha256:raise ValueError('curator dataset digest mismatch')
    commit=subprocess.check_output(['git','-C',str(cap.harness),'rev-parse','HEAD'],text=True,timeout=10).strip()
    dirty=subprocess.check_output(['git','-C',str(cap.harness),'status','--porcelain','--untracked-files=no'],timeout=10)
    if commit!=HARNESS_COMMIT or run_lock['harness_commit']!=commit or dirty:raise ValueError('official harness revision/bytes changed')
    cap.output.mkdir(mode=0o700,parents=True,exist_ok=True)
    frozen=json.loads((directory/'freeze.json').read_bytes())['value']
    groups={}
    for row in schedule:
        key=(row['phase'],row['arm'],row['seed'],row.get('condition','none'))
        groups.setdefault(key,[]).append(row)
    import os
    env=dict(os.environ)
    if cap.docker_host:env['DOCKER_HOST']=cap.docker_host
    # This helper imports/executes only the pinned trusted harness. Candidate
    # code runs exclusively inside the official isolated evaluator containers.
    helper=Path(__file__).with_name('official_curator.py')
    all_reports=[]
    outcomes=ReceiptStore(directory.parent/'curator-results/receipts',directory.parent/'curator-results/authority')
    for (phase,arm,seed,condition),rows in groups.items():
        if len({r['instance_id'] for r in rows})!=len(rows):raise ValueError('duplicate issue in official prediction batch')
        run_id='echo-'+hashlib.sha256(canonical(dict(lock=lock_sha,phase=phase,arm=arm,seed=seed,condition=condition,patches=[frozen['entries'][r['cell_id']] for r in rows]))).hexdigest()[:24]
        destination=cap.output/run_id;destination.mkdir(mode=0o700,exist_ok=True)
        predictions=[dict(instance_id=r['instance_id'],model_name_or_path=run_id,
            model_patch=(directory/'patches'/(r['cell_id']+'.diff')).read_text()) for r in rows]
        _atomic_write(destination/'predictions.jsonl',b''.join(canonical(r)+b'\n' for r in predictions))
        request=dict(harness=str(cap.harness.resolve()),dataset=str(cap.dataset.resolve()),dataset_sha256=cap.dataset_sha256,
                     predictions=str((destination/'predictions.jsonl').resolve()),run_id=run_id,evict_pulled_images=cap.evict_pulled_images,
                     instances=[r for r in run_lock['instances'] if r['instance_id'] in {v['instance_id'] for v in rows}])
        _atomic_write(destination/'request.json',canonical(request))
        with (destination/'curator.log').open('ab') as log:
            proc=subprocess.run(curator_command(cap.python,str((destination/'request.json').resolve())),
                cwd=destination,env=env,stdout=log,stderr=log,timeout=7200)
        if proc.returncode:raise RuntimeError('official curator failed; preserved log at '+str(destination/'curator.log'))
        results=json.loads((destination/'verdicts.json').read_bytes())
        if set(results)!={r['instance_id'] for r in rows}:raise ValueError('official report identity set mismatch')
        for row in rows:
            value=results[row['instance_id']];raw=value['official_report'] or {}
            passed=(raw.get('resolved') is True and raw.get('patch_successfully_applied') is True
                    and value['found'] is True and value['nonempty_f2p'] is True and value['all_required_observed'] is True)
            outcome=dict(official_raw_resolved=raw.get('resolved'),echo_verified_resolved=passed,
                validity_reason='all required test identities observed' if passed else value['evidence_status']+':unresolved-or-invalid',
                report_sha256=value['report_sha256'],log_sha256=value['log_sha256'],run_id=run_id,
                patch_sha256=frozen['entries'][row['cell_id']]['diff_sha256'])
            body=dict(event='repoworld.final-outcome',cell_id=row['cell_id'],outcome=outcome)
            previous=[r['body'] for r in outcomes.records if r['body'].get('cell_id')==row['cell_id']]
            if previous and previous!=[body]:raise ValueError('conflicting official result replay')
            if not previous:outcomes.append(body)
        all_reports.append(str(destination/'verdicts.json'))
    return dict(reports=all_reports,global_barrier=True)
