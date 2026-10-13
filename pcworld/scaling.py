"""Bounded 32B development study: six acquisitions, then sixty frozen receivers.

No resume, selective retry, seeded fault, historical donor or receiver publication.
Task variants are disjoint; some public boundary inputs recur across variants.
"""
import json
import math
from pathlib import Path
import time

from .adversarial import fixed_order
from .pilot import CONTRACT, audit_run, run_pilot, save, source_manifest
from .receipts import ReceiptStore, digest
from .repairs import repair_task_variants
from .runtime import load_runtime
from .shared import SharedConceptLibrary
from .transfer import metrics

CONDITIONS = ('S', 'I2', 'F', 'E', 'E_shared')


def validate_model_evidence(config, health):
    """Require the pinned live 32B worker declaration; raise ValueError on mismatch.

    Audit checks the saved pre-launch health response, not current availability.
    These are authenticated transport declarations, not hardware attestation.
    """
    revision = '9d3053fce650fe1cdbdb75998c2a87add9d178ef'
    sha = '4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085'
    if (not isinstance(health, dict) or health.get('worker_ready') is not True or
            health.get('stopped') is not False):
        raise ValueError('model evidence: worker must be ready and not stopped')
    expected = {'model_profile': 'qwen25-coder32b', 'model_revision': revision,
                'model_sha256': sha, 'model_bytes': 19851335872,
                'requested_devices': ['CUDA0', 'CUDA1']}
    metadata = health.get('metadata')
    if (not isinstance(metadata, dict) or any(metadata.get(k) != v for k, v in expected.items()) or
            type(metadata.get('model_bytes')) is not int):
        raise ValueError('model evidence: pinned 32B identity/devices differ')
    provider = {'model': 'pcworld-qwen25-coder32b', 'revision': revision, 'tokenizer': 'embedded GGUF ' + sha}
    if not isinstance(config, dict) or any(config.get(k) != v for k, v in provider.items()):
        raise ValueError('model evidence: provider identity differs from pinned 32B')
    offload, buffers = metadata.get('gpu_offload'), metadata.get('gpu_model_buffers_mib')
    if (not isinstance(offload, list) or not offload or
            any(pair not in (['65', '65'], [65, 65]) for pair in offload)):
        raise ValueError('model evidence: all 65/65 layers must be on GPU')
    if not isinstance(buffers, dict) or any(
            type(buffers.get(device)) not in (int, float) or
            (isinstance(buffers[device], float) and not math.isfinite(buffers[device])) or
            buffers[device] < 1024 for device in expected['requested_devices']):
        raise ValueError('model evidence: both GPU buffers must be finite and >=1024 MiB')


def _plan():
    tasks = repair_task_variants(24, seed=47)
    if tasks[:12] != repair_task_variants(12, seed=47):
        raise ValueError('24-task generator changed the historical targets')
    jobs = []
    for phase, selected in (('donor', tasks[18:24]), ('receiver', tasks[:12])):
        for i, task in enumerate(selected):
            order = ('E',) if phase == 'donor' else CONDITIONS[i % 5:] + CONDITIONS[:i % 5]
            for condition in order:
                jobs.append({'phase': phase, 'run': f"{phase}-{task['family']}-{task['variant']:02d}-{condition}",
                             'task_id': task['id'], 'family': task['family'], 'condition': condition,
                             'arm': 'E' if condition == 'E_shared' else condition})
    for task in tasks:
        task.update(probe_catalog='expanded-v2', probe_order_seed=20261013)
        task['fixed_probe_order'] = list(fixed_order(task))
    return jobs, {t['id']: t for t in tasks}


def _config(config):
    config = dict(config, seed=73)
    for key, value in {'context_tokens': 4096, 'max_output_tokens': 768, 'temperature_milli': 200}.items():
        if config.setdefault(key, value) != value:
            raise ValueError('scaling sampler differs: ' + key)
    return config


def _read(path):
    return json.loads(Path(path).read_text())


def _journal(path):
    # Never manufacture a replacement authority while auditing deleted evidence.
    for name in ('receipts/receipts.jsonl', 'authority/authority.json'):
        if not (path / name).is_file():
            raise ValueError('missing custody: ' + str(path / name))
    return ReceiptStore(path / 'receipts', path / 'authority')


def _row(job, report):
    if len(report['episodes']) != 1:
        raise ValueError('expected exactly one child episode')
    ep = report['episodes'][0]
    if ep['task'] != job['task_id'] or ep['arm'] != job['arm']:
        raise ValueError('child task/arm differs')
    return {**job, **metrics(ep), 'counterexamples_repaired': ep['counterexamples_repaired'],
            'cpu_us': ep['budget']['used']['cpu_us'],
            **({'shared_memory': ep['shared_memory']} if 'shared_memory' in ep else {})}


def _eligible(row):
    return row['development_accepted'] is True and row['counterexamples_repaired'] is True


def _aggregates(result):
    def total(rows):
        return {'episodes': len(rows), 'accepted': sum(r['development_accepted'] for r in rows),
                'errors': sum(r['error'] is not None for r in rows),
                **{key: sum(r[key] for r in rows) for key in
                   ('tokens', 'llm_calls', 'tools', 'critic_calls', 'repair_attempts', 'wall_ms',
                    'host_cpu_us', 'cpu_us', 'counterexamples', 'accepted_without_repair')}}
    return {'donors': total(result['donors']),
            'receivers': {c: total([r for r in result['receivers'] if r['condition'] == c]) for c in CONDITIONS},
            'publication': {k: sum(p[k] for p in result['publications']) for k in ('tools', 'wall_us', 'cpu_us')}}


def publication_matches(card, publication, output, job):
    expected = {'run_dir': str((Path(output) / job['run']).resolve()), 'task_id': job['task_id'],
                'family': job['family'], 'arm': 'E', 'author_agent_id': 'AGENT_A_' + job['family']}
    return digest(card) == publication.get('lesson_sha256') and all(
        card.get('provenance', {}).get(k) == v for k, v in expected.items())


def run_scaling(output, config, runtime, model_evidence=None):
    """Run at most 66 children once; every completed outcome is journaled."""
    validate_model_evidence(config, model_evidence)
    jobs, tasks = _plan()
    config = _config(config)
    if isinstance(runtime, (str, Path)):
        runtime = load_runtime(runtime)
    if runtime is None or not runtime.id:
        raise ValueError('pinned runtime required')
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=False)
    journal = ReceiptStore(output / 'receipts', output / 'authority')
    contract = {'schema': 'pcworld.scaling.v1', 'jobs': jobs, 'max_episodes': 66,
                'tasks_sha256': digest(tasks), 'config': config, 'model_evidence': model_evidence or {},
                'runtime_snapshot': runtime.id, 'sources': source_manifest(), 'protocol': _read(CONTRACT),
                'scientific_claim': False, 'historical_extra_lookup_tools': 1,
                'comparison': 'known development tasks; historical 14B comparison is descriptive'}
    save(output / 'contract.json', contract)
    journal.append({'kind': 'scaling_contract', 'contract': contract})
    result = {'schema': 'pcworld.scaling-result.v1', 'status': 'running', 'donors': [],
              'receivers': [], 'publications': [], 'libraries': {}, 'scientific_claim': False}

    def persist():
        result['aggregates'] = _aggregates(result)
        save(output / 'result.json', result)

    def execute(job, library=None):
        if source_manifest() != contract['sources']:
            raise ValueError('sources changed during study')
        report = run_pilot(output / job['run'], task_count=24, task_ids=[job['task_id']],
            arms=(job['arm'],), provider='http', split='development', config=config,
            suite='repair-v2', runtime=runtime, task_seed=47, task_families=[job['family']],
            episode_wall_seconds=900, probe_catalog='expanded-v2', probe_order_seed=20261013,
            cache_properties=False, seeded_diagnostic=False, model_evidence=contract['model_evidence'],
            shared_library=library)
        row = _row(job, report)
        result['donors' if job['phase'] == 'donor' else 'receivers'].append(row)
        journal.append({'kind': 'child_result', 'row': row, 'result_sha256': digest(report)})
        persist()
        audited = audit_run(output / job['run']); save(output / job['run'] / 'audit.json', audited)
        if not audited['valid']:
            raise ValueError('invalid child audit: ' + job['run'])

    persist()
    try:
        for job in jobs[:6]:
            execute(job)
        shared = SharedConceptLibrary(output / 'shared-library')
        empty = SharedConceptLibrary(output / 'empty-library')
        for row in result['donors']:
            if not _eligible(row):
                continue
            started, cpu = time.monotonic_ns(), time.process_time_ns()
            card = shared.publish_from_run(output / row['run'], row['task_id'], 'E', 'AGENT_A_' + row['family'])
            pub = {k: row[k] for k in ('run', 'task_id', 'family')}
            pub.update(lesson_sha256=digest(card), lesson_id=card['lesson_id'], tools=1,
                       wall_us=(time.monotonic_ns() - started) // 1000,
                       cpu_us=(time.process_time_ns() - cpu) // 1000)
            if not publication_matches(card, pub, output, row):
                raise ValueError('publication provenance differs')
            result['publications'].append(pub)
            journal.append({'kind': 'publication', 'publication': pub}); persist()
        result['libraries'] = {'shared-library': shared.identity(), 'empty-library': empty.identity()}
        journal.append({'kind': 'libraries_frozen', 'identities': result['libraries']}); persist()
        for job in jobs[6:]:
            for name, identity in result['libraries'].items():
                if SharedConceptLibrary(output / name).identity() != identity:
                    raise ValueError('frozen library changed')
            library = shared if job['condition'] == 'E_shared' else empty
            execute(job, library)
        if source_manifest() != contract['sources']:
            raise ValueError('sources changed during study')
        result['status'] = 'complete'
        return result
    except Exception as exc:
        result['status'] = 'error'; result['error'] = type(exc).__name__ + ': ' + str(exc)[:240]
        raise
    finally:
        result['sources_unchanged'] = source_manifest() == contract['sources']
        persist()
        journal.append({'kind': 'scaling_result', 'result_sha256': digest(result)})


def audit_scaling(output):
    """Authenticate sequence, eligibility, frozen recipes and all underlying runs."""
    output = Path(output).resolve(); total = 0
    try:
        def require(ok, message):
            if not ok:
                raise ValueError(message)
        contract, result = _read(output / 'contract.json'), _read(output / 'result.json')
        bodies = [r['body'] for r in _journal(output).records]
        require(bodies[0] == {'kind': 'scaling_contract', 'contract': contract}, 'contract custody differs')
        require(bodies[-1] == {'kind': 'scaling_result', 'result_sha256': digest(result)}, 'result custody differs')
        validate_model_evidence(contract['config'], contract['model_evidence'])
        jobs, tasks = _plan()
        require(contract['schema'] == 'pcworld.scaling.v1' and contract['jobs'] == jobs and
                contract['tasks_sha256'] == digest(tasks) and contract['max_episodes'] == 66,
                'study selection differs')
        require(contract['config'] == _config(contract['config']) and contract['runtime_snapshot'], 'config differs')
        require(contract['sources'] == source_manifest() and contract['protocol'] == _read(CONTRACT) and
                result['sources_unchanged'], 'sources/protocol changed')
        require(result['status'] == 'complete' and len(result['donors']) == 6 and len(result['receivers']) == 60,
                'incomplete study')
        require({p.name for p in output.iterdir() if p.is_dir()} ==
                {j['run'] for j in jobs} | {'receipts', 'authority', 'empty-library', 'shared-library'},
                'extra/missing study run directories')
        require(result['scientific_claim'] is False and contract['scientific_claim'] is False and
                contract['historical_extra_lookup_tools'] == 1, 'study scope differs')
        expected = [bodies[0]]
        child_bodies = []
        for job, row in zip(jobs, result['donors'] + result['receivers']):
            path = output / job['run']
            audited = audit_run(path); total += audited.get('records', 0)
            require(audited['valid'], 'invalid child audit: ' + job['run'])
            report, provider = _read(path / 'result.json'), _read(path / 'provider.json')
            require(row == _row(job, report), 'child metrics/selection differ')
            require(report['sources_unchanged'] and report['suite'] == 'repair-v2' and
                    report['seeded_diagnostic'] is False and report['scientific_claim'] is False, 'child scope differs')
            rc_records = _journal(path).records; rc = rc_records[0]['body']
            require(rc_records[-1]['body'] == {'kind': 'run_result', 'result_sha256': digest(report)},
                    'child result custody differs')
            require(provider.get('kind') == 'http' and provider['config'] == contract['config'] and
                    provider.get('local_evidence') == contract['model_evidence'], 'child provider differs')
            require(_read(path / 'tasks.json') == [tasks[job['task_id']]] and
                    _read(path / 'sources.json') == contract['sources'] and
                    _read(path / 'contract.json') == contract['protocol'], 'child task/sources/protocol differ')
            settings = {'kind': 'run_contract', 'arms': [job['arm']], 'suite': 'repair-v2',
                        'task_families': [job['family']], 'runtime_snapshot': contract['runtime_snapshot'],
                        'cache_properties': False, 'seeded_diagnostic': False, 'episode_wall_seconds': 900,
                        'tasks_sha256': digest([tasks[job['task_id']]]), 'sources_sha256': digest(contract['sources']),
                        'contract_sha256': digest(contract['protocol']), 'provider_sha256': digest(provider),
                        'episode_ids': [job['task_id'] + '-' + job['arm']]}
            if job['phase'] == 'receiver':
                name = 'shared-library' if job['condition'] == 'E_shared' else 'empty-library'
                settings['shared_library'] = {'path': str(output / name), 'identity': result['libraries'][name]}
                cost = row['shared_memory']
                available = job['condition'] == 'E_shared' and any(p['family'] == job['family'] for p in result['publications'])
                require(cost['tools'] == 1 and cost['lessons'] == int(available), 'lookup cost/delivery differs')
            else:
                require('shared_memory' not in row, 'donor consumed shared memory')
            require(rc == settings, 'child configuration differs: ' + job['run'])
            child_bodies.append({'kind': 'child_result', 'row': row, 'result_sha256': digest(report)})
        expected.extend(child_bodies[:6])
        eligible = [r for r in result['donors'] if _eligible(r)]
        pubs = result['publications']
        require(len(pubs) == len(eligible), 'eligible publications omitted/added')
        for name in ('empty-library', 'shared-library'):
            _journal(output / name)
        empty, shared = SharedConceptLibrary(output / 'empty-library'), SharedConceptLibrary(output / 'shared-library')
        require(result['libraries'] == {'empty-library': empty.identity(), 'shared-library': shared.identity()},
                'frozen library identity differs')
        records = shared.store.records
        require(len(empty.store.records) == 1 and len(records) == 1 + len(pubs), 'extra library records')
        for donor, pub, record in zip(eligible, pubs, records[1:]):
            require(all(pub[k] == donor[k] for k in ('run', 'task_id', 'family')), 'wrong publication donor')
            require(pub['tools'] == 1 and pub['wall_us'] >= 0 and pub['cpu_us'] >= 0, 'invalid publication costs')
            for variant in ('00', '01'):
                cards = shared.lookup(tasks['repair-v2-' + donor['family'] + '-' + variant])
                require(len(cards) == 1 and publication_matches(cards[0], pub, output, donor) and
                        cards[0]['lesson_id'] == pub['lesson_id'] == record['body']['lesson']['lesson_id'],
                        'recipe hash/provenance differs')
            expected.append({'kind': 'publication', 'publication': pub})
        expected.append({'kind': 'libraries_frozen', 'identities': result['libraries']})
        expected.extend(child_bodies[6:]); expected.append(bodies[-1])
        require(bodies == expected, 'study journal sequence/extras differ')
        require(result['aggregates'] == _aggregates(result), 'aggregates differ')
        return {'valid': True, 'errors': [], 'records': total + len(bodies), 'scientific_claim': False}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, IndexError) as exc:
        return {'valid': False, 'errors': [type(exc).__name__ + ': ' + str(exc)[:240]],
                'records': total, 'scientific_claim': False}
