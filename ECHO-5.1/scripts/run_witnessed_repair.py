"""Repair-only diagnostic with previously observed counterexamples.

No live critic; no claim of adaptive discovery or superiority over S/I2/F.
Uses the existing episode, budget, sandbox, receipts, thought bus and auditor.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT/'ECHO-5.1/scripts/run.py'))
from echoai.pcworld.pilot import Episode, CONTRACT, source_manifest, save, audit_run
from echoai.pcworld.provider import HTTPProvider
from echoai.pcworld.receipts import ReceiptStore, digest
from echoai.pcworld.runtime import load_runtime, runtime_store


def run(previous, output, config_path, runtime_path):
    collect=runpy.run_path(str(Path(__file__).with_name('prepare_kaggle_repair.py')))['collect_jobs']
    jobs=collect(previous)
    old={t['id']:t for t in json.loads((previous/'tasks.json').read_text())}
    tasks=[{**old[j['id']], 'initial':j['context']['source']} for j in jobs]
    config=json.loads(config_path.read_text());provider=HTTPProvider(config)
    output.mkdir(parents=True,exist_ok=False)
    runtime=runtime_store(output/'runtime').capture(load_runtime(runtime_path))
    save(output/'runtime/runtime.json',{'schema':'pcworld.runtime.v1','snapshot':runtime.id})
    root=ReceiptStore(output/'receipts',output/'authority')
    manifest=source_manifest();save(output/'sources.json',manifest)
    contract=json.loads(CONTRACT.read_text());save(output/'contract.json',contract)
    save(output/'tasks.json',tasks)
    provenance={'kind':'http','model':provider.model,'config':config,'contains_credentials':False,
                'diagnostic':'fixed observed failures; original proposer source; no live critic',
                'previous_result_sha256':digest(json.loads((previous/'result.json').read_text()))}
    save(output/'provider.json',provenance)
    root.append({'kind':'run_contract','tasks_sha256':digest(tasks),'sources_sha256':digest(manifest),
                 'arms':['E'],'episode_ids':[t['id']+'-E' for t in tasks],
                 'contract_sha256':digest(contract),'suite':'repair-v2','runtime_snapshot':runtime.id,
                 'cache_properties':False,'seeded_diagnostic':True,'episode_wall_seconds':900,
                 'provider_sha256':digest(provenance)})
    episodes=[]
    for task,job in zip(tasks,jobs):
        if source_manifest()!=manifest: raise RuntimeError('sources changed')
        ep=Episode(output/(task['id']+'-E'),task,'E',provider,runtime=runtime,
                   seeded_diagnostic=True,episode_wall_seconds=900)
        for value in task['public_inputs']: ep.check(ep.base,value)
        for witness in job['context']['repair_feedback']['failures']:
            actual=ep.check(ep.base,witness['input'])
            if actual['status']!='contradicted' or any(actual.get(k)!=witness.get(k) for k in ('observed','expected')):
                raise ValueError('previous counterexample not reproduced')
            ep.counterexamples.append(witness['input'])
        candidate=ep.base;error=None
        try: candidate=ep.guarded_repair(ep.base)
        except (ValueError,RuntimeError,OSError) as exc: error=type(exc).__name__+': '+str(exc)
        episodes.append(ep.finish(candidate,error=error))
    result={'schema':'pcworld.development.v1','episodes':episodes,'scientific_claim':False,
            'seeded_diagnostic':True,'sources_unchanged':source_manifest()==manifest,
            'scope':'repair-only replay; not a full E episode or a four-arm comparison',
            'llm_calls':sum(e['llm_calls'] for e in episodes)}
    save(output/'result.json',result)
    root.append({'kind':'run_result','result_sha256':digest(result)})
    audit=audit_run(output);save(output/'audit.json',audit)
    print(json.dumps({'audit':audit,'repaired':sum(e['counterexamples_repaired'] and e['final_cases_passed'] for e in episodes)},indent=2))
    if not audit['valid']: raise RuntimeError('diagnostic audit failed')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('previous','output','config','runtime'):p.add_argument(name,type=Path)
    a=p.parse_args();run(a.previous,a.output,a.config,a.runtime)
