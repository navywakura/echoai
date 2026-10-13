"""Verify downloaded GPU proposals locally. GPU reports never confer success.

Every candidate runs in the existing hermetic Bubblewrap/cgroup boundary.
This fixed-prompt diagnostic is not an S/I2/F/E episode or a blind experiment.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('echoai', ROOT/'__init__.py',
                                            submodule_search_locations=[str(ROOT)])
package = importlib.util.module_from_spec(spec)
sys.modules['echoai'] = package
spec.loader.exec_module(package)
from echoai.pcworld.pilot import Episode, save, source_manifest
from echoai.pcworld.receipts import ReceiptStore, digest
from echoai.pcworld.runtime import load_runtime
from echoai.pcworld.verifier import check_observation


class ImportedProposal:
    is_llm = False  # No live model call here; remote usage is recorded separately.
    def __init__(self, model):
        self.model = model + '-imported-proposal'


def verify(run, inputs, downloaded, runtime_path, output):
    bundle = json.loads(inputs.read_text())
    report = json.loads(downloaded.read_text())
    if report.get('input_sha256') != hashlib.sha256(inputs.read_bytes()).hexdigest():
        raise ValueError('GPU result belongs to different input bytes')
    if bundle['local_run_result_sha256'] != hashlib.sha256((run/'result.json').read_bytes()).hexdigest():
        raise ValueError('local run binding differs')
    if report.get('errors') or report.get('candidate_executed_on_kaggle') is not False:
        raise ValueError('GPU diagnostic failed or used the wrong execution boundary')
    jobs = {j['id']: j for j in bundle['jobs']}
    records = report['records']
    if len(records) != len(jobs) or {r['task'] for r in records} != set(jobs):
        raise ValueError('missing or duplicate GPU proposal')
    tasks = {t['id']: t for t in json.loads((run/'tasks.json').read_text())}
    output.mkdir(parents=True, exist_ok=False)
    manifest = source_manifest()
    save(output/'sources.json', manifest)
    runtime = load_runtime(runtime_path)
    results = []
    for record in records:
        job = jobs[record['task']]
        if record['job_sha256'] != digest(job):
            raise ValueError('GPU job binding differs')
        if record.get('error'):
            results.append({'task': record['task'], 'passed': False, 'provider_error': record['error']})
            continue
        task = {**tasks[record['task']], 'initial': job['context']['source']}
        ep = Episode(output/task['id'], task, 'E', ImportedProposal(bundle['config']['model']), runtime=runtime,
                     seeded_diagnostic=True, episode_wall_seconds=300)
        ep.emit('observation', {'operation': 'imported_gpu_proposal', 'remote_record': record,
                               'scope': 'fixed witnessed repair prompt; not a live E episode',
                               'origin': report.get('origin', 'Kaggle GPU')})
        witnesses = [f for f in job['context']['repair_feedback']['failures']
                     if 'observed' in f and 'expected' in f and f.get('status','contradicted')=='contradicted']
        if not witnesses:
            raise ValueError('no value counterexample bound to retained program')
        baseline = [ep.check(ep.base, f['input']) for f in witnesses]
        for witness, actual in zip(witnesses, baseline):
            if any(actual.get(k) != witness.get(k) for k in ('input', 'observed', 'expected')):
                raise ValueError('local re-execution differs from exported failure witness')
            if actual['status'] != 'contradicted':
                raise ValueError('exported witness does not refute retained program')
        candidate = ep.apply_content(ep.base, record['output'].get('content'))
        values = []
        for value in task['public_inputs'] + [f['input'] for f in witnesses] + task['development_inputs']:
            if value not in values:
                values.append(value)
        properties = [ep.check(candidate, value, final=True) for value in values]
        passed = all(p['status'] == 'supported' for p in properties)
        summary = {'task': task['id'], 'passed': passed, 'cases': len(properties),
                   'candidate': candidate.id, 'budget': ep.budget.report(), 'remote_usage': record.get('usage'),
                   'scientific_claim': False, 'scope': 'finite local checks on an imported repair',
                   'origin': report.get('origin', 'Kaggle GPU')}
        ep.emit('property', {'gpu_diagnostic_result': summary})
        store = ReceiptStore(ep.path/'receipts', ep.path/'authority')
        errors = []
        bysha = {r['sha256']: r['body'] for r in store.records}
        for body in bysha.values():
            if 'property' not in body:
                continue
            observation = bysha[body['execution_receipt']]
            execution = observation['execution']
            if execution['isolation'].get('host_usr_mounted') is not False or execution['isolation'].get('runtime_snapshot') != runtime.id:
                errors.append('runtime isolation differs')
            for stream in ('stdout', 'stderr'):
                raw = base64.b64decode(execution[stream+'_b64'], validate=True)
                if (hashlib.sha256(raw).hexdigest() != execution[stream+'_sha256'] or
                        raw.decode(errors='replace') != execution[stream]):
                    errors.append('output digest differs')
            if check_observation(task['property'], observation['input'], execution) != body['property']:
                errors.append('property replay differs')
        audit = {'valid': store.audit()['ok'] and not errors, 'records': len(store.records), 'errors': errors}
        save(ep.path/'audit.json', audit)
        results.append({**summary, 'audit': audit})
    result = {'scientific_claim': False, 'results': results, 'sources_unchanged': manifest == source_manifest(),
              'passed': sum(r['passed'] and r.get('audit', {}).get('valid', False) for r in results),
              'total': len(results),
              'scope': 'imported inference; fresh local isolated execution and property replay',
              'input_sha256': report['input_sha256'],
              'inference_report_sha256': hashlib.sha256(downloaded.read_bytes()).hexdigest()}
    save(output/'result.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('run', 'inputs', 'downloaded', 'runtime', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    verify(args.run, args.inputs, args.downloaded, args.runtime, args.output)
