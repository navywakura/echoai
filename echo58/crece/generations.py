"""F2 fixed-budget generations. Resume from immutable requests, trials and snapshots."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import time
from types import FunctionType

from ..acumula import bench as B1
from ..acumula.agent import XAgent
from ..acumula.config import Config
from ..acumula3 import bench as B3
from ..b3.trace import CORRECTED
from . import runtime as R
from .api import complete
from .pacing import paced_complete, QuotaDeferred
from .equiv import LAB, FAMILIES, digest, log, observed
from .mechanical import check
from .persistence import store_piece, reference_specs, plugs_from_specs, save_snapshot, load_snapshot
from .pilot import save_new, evaluate, gate, extract_code, prompt_for
from .artifacts import durable_directory

ARMS = ('crece','sin_fichas','sin_relevo','azar_gramatica','acepta_azar','piezas_b3','sin_piezas')
MODELS = ('openai/gpt-oss-120b',)


def bounded_call(folder, model, prompt, *, call=complete, pause=time.sleep):
    folder = Path(folder)
    durable_directory(folder)
    identity = folder/'request.json'
    if not identity.exists() and any(folder.glob('attempt-*.json')):
        raise ValueError('request identity missing for existing attempt history')
    save_new(identity, {'model': model, 'prompt': prompt,
                        'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}, identical=True)
    last = {'status':0, 'content':'', 'error_type':'AttemptsExhausted', 'cached':False}
    for attempt in range(3):
        marker = folder/f'attempt-{attempt}.json'
        receipt = folder/f'attempt-{attempt}-result.json'
        if receipt.exists():
            last = json.loads(receipt.read_text())
        elif marker.exists():
            # Possibly sent before interruption: conservatively consume the slot.
            continue
        else:
            if attempt:
                pause(10 * attempt)
            def reserve():
                save_new(marker, {'model':model, 'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
                                  'reserved_ns':time.time_ns()})
            last = call(model, prompt, LAB/'api-cache', before_call=reserve)
            save_new(receipt, last)
        if last.get('deferred_until',0)>time.time():
            raise QuotaDeferred(last['deferred_until'])
        if last['status'] == 200 and last['content']:
            return last
    if last['status']==429:
        raise RuntimeError('HTTP budget exhausted on quota; protocol remains technically incomplete')
    return last


def curve_green(failures):
    return any(failures[g] < failures[g-1] and failures[g+1] < failures[g] for g in range(1,len(failures)-1))


def random_selection(trials, seed):
    pool = [t['generation'] for t in trials if t['spec'] is not None]
    count = sum(t['accepted'] for t in trials)
    selected = random.Random(seed).sample(pool, count)
    return {'pool':pool, 'count':count, 'selected_generations':selected, 'rng_seed':seed}


def random_instance(trial):
    spec = trial['spec']
    return {**spec, 'name':f"{spec['sha256']}-g{trial['generation']}"}


def rejected_feedback(directory, arm, generation):
    if arm not in ('crece','sin_relevo'):
        return []
    history=[]
    for previous in range(1,generation):
        trial=json.loads((Path(directory)/arm/f'trial-{previous}.json').read_text())
        if trial['accepted'] or trial['mechanical'].get('stage')=='API':
            continue
        item={'source':trial['source'],'source_sha256':trial['source_sha256'],
              'champion_snapshot':trial.get('champion_snapshot'),
              'mechanical':trial['mechanical'],'reasons':[]}
        if not trial['mechanical']['green']:
            item['reasons'].append('mechanical_check_failed')
        elif trial['mechanical'].get('duplicate_active'):
            item['reasons'].append('already_active')
        elif 'base' in trial:
            base,candidate=trial['base'],trial['candidate']
            success_delta=sum(candidate[f]['success']-base[f]['success'] for f in base)
            harm_delta=sum(candidate[f]['harm']-base[f]['harm'] for f in base)
            item.update(success_delta=success_delta,harm_delta=harm_delta)
            if success_delta<=0:item['reasons'].append('no_global_success_gain')
            if any(candidate[f]['success']<base[f]['success'] for f in base):
                item['reasons'].append('success_regression_in_a_family')
            if any(candidate[f]['harm']>base[f]['harm'] for f in base):
                item['reasons'].append('harm_regression_in_a_family')
            if any(candidate[f]['plug_errors'] for f in candidate):
                item['reasons'].append('runtime_errors')
        history.append(item)
    return history


def symbolic_intent(intent):
    if not intent:
        return ()
    return ('DROP_ACTION' if intent[0]=='DROP' else intent[0], *intent[1:])


def symbolic_outcome(outcome):
    return 'UNKNOWN' if outcome is None else 'PICKED' if outcome=='PICK' else outcome


def symbolic_effect(effect):
    kind=effect[0]
    if kind in (R.E_BAN,R.E_UNTIL):
        row={'type':'BAN' if kind==R.E_BAN else 'BAN_UNTIL_PROGRESS','id':effect[1],
             'action':('ENTER','PICK','TOGGLE','DROP_ACTION')[effect[2]]}
        if kind==R.E_BAN:row['scope']=('EPISODE','HAND','ANY')[effect[3]]
        return row
    if kind==R.E_NOTE:
        return {'type':'NOTE','key':effect[1],'scope':('EPISODE','HAND','ANY')[effect[2]]}
    return {'type':'DROP_AT' if kind==R.E_DROP else 'GOTO','cell':effect[1]}


class TrainingAgent(observed(R.HAgent)):
    def run(self,*args,**kwargs):
        self.audit_effects=[]
        return super().run(*args,**kwargs)

    def _dispatch(self,moment,obs,world,ctx):
        start=len(self.plug_events)
        action_step=len(self.trace) if moment==R.OUTCOME else len(self.trace)+1
        result=super()._dispatch(moment,obs,world,ctx)
        for _,name,hook,effect in self.plug_events[start:]:
            self.audit_effects.append({'step':action_step,'piece':name,
                                       'hook':('DECIDE','OUTCOME','DROP','IDLE')[hook],
                                       'effect':symbolic_effect(effect)})
        return result


def recent_effects(agent):
    first=max(1,len(agent.trace)-19)
    return [row for row in agent.audit_effects if first<=row['step']<=len(agent.trace)]


def training_fiches(memory, plugs, seeds):
    failures, all_rows = [], []
    for family in FAMILIES:
        for seed in seeds:
            agent = TrainingAgent(source=memory.probe_copy(), plugs=plugs)
            world = B3.W.make_world(family, seed, 'A2')
            try:
                row = agent.run(world)
            finally:
                world.close()
            all_rows.append({'family':family, 'seed':seed, 'result':row, 'trace_sha256':digest(agent.trace)})
            if not row['success']:
                failures.append({'signals':row['signals'], 'result':{k:row[k] for k in ('success','harm','steps','wasted')},
                                 'tail':[{'step':step,'action':p,'intent':symbolic_intent(it),'outcome':symbolic_outcome(out),'pos':ob['pos'],'hand':ob['hand'],
                                          'heading':ob['dir'],'reward':ob['reward'],
                                          'terminated':ob['terminated'],'truncated':ob['truncated']}
                                         for step,(p,it,out,ob) in enumerate(agent.trace[-20:],max(1,len(agent.trace)-19))],
                                 'last_grid':agent.trace[-1][3]['grid'], 'picked':tuple(agent.picked.items()),
                                 'opened':tuple(agent.opened.items()), 'progress':agent.progress,
                                 'active_effects':recent_effects(agent)})
    chosen, seen = [], set()
    for row in failures:
        signature = tuple(row['signals'])
        if signature not in seen:
            chosen.append(row)
            seen.add(signature)
        if len(chosen) == 3:
            break
    for row in failures:
        if len(chosen) == 3:
            break
        if row not in chosen:
            chosen.append(row)
    return {'fiches':chosen, 'episodes':all_rows}


def grammar_source(seed):
    rng = random.Random(seed)
    kind, threshold = rng.randrange(4), rng.randrange(1,5)
    bodies = (
        f'if moment == DECIDE and c.intent and c.intent[0] == TOGGLE and v.opened(c.intent[1]) >= {threshold}:\n        return (BAN(c.intent[2], TOGGLE, ANY),)',
        f'if moment == DECIDE and c.intent and c.intent[0] == DROP_ACTION and c.drop_for and v.hand and v.picked(c.drop_for) >= {threshold}:\n        return (BAN(c.drop_for, PICK, HAND),)',
        f'if moment == IDLE and v.idle >= {threshold}:\n        cells = tuple(p for p in v.reach() if p != v.pos)\n        if cells:\n            return (GOTO(min(cells, key=lambda p: (v.visits(p), abs(p[0]-v.pos[0])+abs(p[1]-v.pos[1]), p))),)',
        f'if moment == OUTCOME and c.intent and c.intent[0] == PICK and c.out == PICKED and c.dropped_here == (c.intent[2], v.progress) and v.picked(c.intent[2]) >= {threshold}:\n        return (BAN_UNTIL_PROGRESS(c.intent[2], PICK),)')
    return 'def piece(moment, v, c):\n    ' + bodies[kind] + '\n    return ()\n'


def build_memory(macro):
    build = FunctionType(B1.start_memory.__code__, {**B1.start_memory.__globals__, 'XAgent':observed(XAgent)})
    cfg = Config()
    for edit in CORRECTED:
        cfg = cfg.apply(edit)
    return build(macro).reconfigure(cfg).probe_copy()


def score(root, memory, specs, seeds):
    key = digest({'memory':digest(memory.raw), 'edits':memory.cfg.edits, 'pieces':specs, 'seeds':seeds})
    path = Path(root)/'scores'/f'{key}.json'
    if path.exists():
        return json.loads(path.read_text())
    values = evaluate(memory, plugs_from_specs(root, specs), seeds)
    save_new(path, values, identical=True)
    return values


def one_job(job):
    root, model, macro = Path(job[0]), job[1], job[2]
    directory = root/model.replace('/','--')/f'm{macro}'
    durable_directory(directory)
    done = directory/'job-result.json'
    if done.exists():
        return json.loads(done.read_text())
    model_offset = 500_000_000
    probe_seeds = tuple(model_offset+13_000_000+100_000*macro+i for i in range(12))
    initial_path = directory/'sin_piezas/g0.json'
    if initial_path.exists():
        memory, _, _ = load_snapshot(root, initial_path)
    else:
        memory = build_memory(macro)
        save_snapshot(root, initial_path, memory, [], {'model':model,'macro':macro,'arm':'sin_piezas','generation':0})
    for arm in ARMS:
        path = directory/arm/'g0.json'
        if not path.exists():
            save_snapshot(root, path, memory, reference_specs() if arm == 'piezas_b3' else [],
                          {'model':model,'macro':macro,'arm':arm,'generation':0})
    states = json.loads((LAB/'f1-training.json').read_text())['states']
    crece_trials = []
    for generation in range(1,6):
        training_seeds = tuple(model_offset+11_000_000+100_000*macro+1000*generation+i for i in range(5))
        validation_seeds = tuple(model_offset+12_000_000+100_000*macro+1000*generation+i for i in range(8))
        for arm in ('crece','sin_fichas','sin_relevo','azar_gramatica'):
            trial_path = directory/arm/f'trial-{generation}.json'
            snapshot_path = directory/arm/f'g{generation}.json'
            _, _, parent = load_snapshot(root, directory/arm/f'g{generation-1}.json')
            parent_specs = parent['pieces']
            base_specs = [] if arm == 'sin_relevo' else parent_specs
            if trial_path.exists():
                trial = json.loads(trial_path.read_text())
            else:
                log('f2_proposal_start', model=model, macro=macro, generation=generation, arm=arm)
                if arm == 'azar_gramatica':
                    source = grammar_source(model_offset+14_000_000+100_000*macro+generation)
                    receipt = {'status':200,'content':source,'cached':False,'request_sha256':None}
                else:
                    fiche_path = directory/arm/f'fiches-{generation}.json'
                    if arm == 'sin_fichas':
                        fiches = []
                    elif fiche_path.exists():
                        fiches = json.loads(fiche_path.read_text())['fiches']
                    else:
                        data = training_fiches(memory, plugs_from_specs(root,base_specs), training_seeds)
                        save_new(fiche_path,data)
                        fiches = data['fiches']
                    feedback=rejected_feedback(directory,arm,generation)
                    prompt = prompt_for({'episodes':fiches},feedback if feedback else None)
                    prompt += f'\nDEVELOPMENT REQUEST: model={model}, macro={macro}, generation={generation}.\n'
                    if feedback:
                        prompt += 'Rejected pieces above failed in their recorded champion context; they are not universally forbidden. Use the measured reasons when proposing the next piece.\n'
                    if arm == 'crece':
                        codes = [{'piece':s['name'],'source':(root/'objects'/f"{s['sha256']}.py").read_text()}
                                 for s in base_specs]
                        prompt += 'ACTIVE PIECES (already installed; propose an additional useful rule):\n' + json.dumps(codes)
                    if arm == 'sin_fichas':
                        prompt += 'No failure observations are supplied in this control. Propose using only the interface and examples.\n'
                    receipt = bounded_call(directory/arm/f'request-{generation}', model, prompt,
                                           call=paced_complete)
                    source = extract_code(receipt['content'])
                sha = hashlib.sha256(source.encode()).hexdigest()
                trial = {'generation':generation,'model':model,'macro':macro,'arm':arm,'source':source,
                         'source_sha256':sha,'request_sha256':receipt.get('request_sha256'),
                         'champion_snapshot':parent['snapshot_sha256'] if arm!='sin_relevo' else
                             json.loads((directory/arm/'g0.json').read_text())['snapshot_sha256'],
                         'http_status':receipt['status'],'accepted':False,'spec':None}
                if receipt['status'] != 200 or not receipt['content']:
                    trial['mechanical'] = {'green':False,'stage':'API'}
                elif any(s['sha256']==sha for s in base_specs):
                    trial['mechanical'] = {'green':True,'duplicate_active':True}
                    trial['spec'] = store_piece(root, source)
                else:
                    mechanical = check(source,states)
                    trial['mechanical'] = {k:v for k,v in mechanical.items() if k != 'responses'}
                    if mechanical['green']:
                        spec = store_piece(root,source)
                        trial['spec'] = spec
                        base = score(root,memory,base_specs,validation_seeds)
                        candidate = score(root,memory,base_specs+[spec],validation_seeds)
                        trial.update(base=base,candidate=candidate,seeds=validation_seeds)
                        trial['accepted'] = gate(base,candidate) and not any(v['plug_errors'] for v in candidate.values())
                save_new(trial_path,trial)
                log('f2_trial', model=model, macro=macro, generation=generation, arm=arm,
                    accepted=trial['accepted'], mechanical=trial['mechanical'])
                print(json.dumps({'model':model,'macro':macro,'generation':generation,'arm':arm,
                                  'accepted':trial['accepted'],'mechanical':trial['mechanical']}),flush=True)
            specs = base_specs+[trial['spec']] if trial['accepted'] else parent_specs
            if not snapshot_path.exists():
                save_snapshot(root,snapshot_path,memory,specs,{'model':model,'macro':macro,'arm':arm,
                              'generation':generation,'parent':parent['snapshot_sha256'],'trial_sha256':digest(trial)})
            if arm == 'crece':
                crece_trials.append(trial)
        for arm in ('piezas_b3','sin_piezas'):
            path = directory/arm/f'g{generation}.json'
            if not path.exists():
                _,_,parent = load_snapshot(root,directory/arm/f'g{generation-1}.json')
                save_snapshot(root,path,memory,parent['pieces'],{'model':model,'macro':macro,'arm':arm,
                              'generation':generation,'parent':parent['snapshot_sha256']})
    # Retrospective acceptance-count control, fixed before looking at probe scores.
    selection = random_selection(crece_trials, model_offset+14_000_000+100_000*macro)
    selected = selection['selected_generations']
    save_selection = directory/'random-selection.json'
    if not save_selection.exists():
        save_new(save_selection, selection)
    for generation,trial in enumerate(crece_trials,1):
        path = directory/'acepta_azar'/f'g{generation}.json'
        if not path.exists():
            _,_,parent = load_snapshot(root,directory/'acepta_azar'/f'g{generation-1}.json')
            specs = parent['pieces'] + ([random_instance(trial)] if generation in selected else [])
            save_snapshot(root,path,memory,specs,{'model':model,'macro':macro,'arm':'acepta_azar',
                          'generation':generation,'parent':parent['snapshot_sha256']})
    curves = {}
    for arm in ARMS:
        curves[arm] = []
        for generation in range(6):
            _,_,snapshot = load_snapshot(root,directory/arm/f'g{generation}.json')
            values = score(root,memory,snapshot['pieces'],probe_seeds)
            curves[arm].append({'failed':sum(v['episodes']-v['success'] for v in values.values()),
                                'harm':sum(v['harm'] for v in values.values()),
                                'plug_errors':sum(v['plug_errors'] for v in values.values()),'families':values})
            log('f2_probe',model=model,macro=macro,arm=arm,generation=generation,
                failed=curves[arm][-1]['failed'],harm=curves[arm][-1]['harm'])
    result = {'model':model,'macro':macro,'curves':curves,'random_selection':selected}
    save_new(done,result)
    return result


def run(root, jobs=2):
    for name in ('f0-equiv.json','f1-pilot.json'):
        if not json.loads((LAB/name).read_text())['green']:
            raise ValueError(f'prerequisite not green: {name}')
    root=Path(root)
    durable_directory(root)
    protocol=Path(__file__).resolve().parents[2]/'ECHO-5.8/docs/B4-CRECE-F2-PROTOCOLO-V5-R1-API.md'
    interface_protocol = protocol.with_name('B4-CRECE-F2-PROTOCOLO-V5-INTERFACE120B.md')
    feedback_protocol = protocol.with_name('B4-CRECE-F2-PROTOCOLO-V4-FEEDBACK.md')
    inherited_protocol = protocol.with_name('B4-CRECE-F2-PROTOCOLO.md')
    provider_protocol = protocol.with_name('B4-CRECE-F2-PROTOCOLO-V3-GROQ.md')
    manifest={'protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
              'interface_protocol_sha256':hashlib.sha256(interface_protocol.read_bytes()).hexdigest(),
              'feedback_protocol_sha256':hashlib.sha256(feedback_protocol.read_bytes()).hexdigest(),
              'inherited_protocol_sha256':hashlib.sha256(inherited_protocol.read_bytes()).hexdigest(),
              'provider_protocol_sha256':hashlib.sha256(provider_protocol.read_bytes()).hexdigest(),
              'frozen_base':B3.frozen_state(),
              'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
              'models':list(MODELS),'macros':[1,2],'generations':5,'max_http_attempts':90,
              'provider':'groq','reasoning_effort':'low','max_tokens':2048,'seed_offset':500_000_000}
    start=root/'started.json'
    if start.exists():
        old=json.loads(start.read_text())
        if old!=manifest:
            raise ValueError('F2 protocol/code changed; cannot silently resume')
    else:
        save_new(start,manifest)
    tasklist=[(str(root),model,macro) for model in MODELS for macro in (1,2)]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        results=list(pool.map(one_job,tasklist))
    combined={}
    for model in MODELS:
        matching=[r for r in results if r['model']==model]
        curves={arm:[sum(r['curves'][arm][g]['failed'] for r in matching) for g in range(6)] for arm in ARMS}
        combined[model]={'curves':curves,'green':curve_green(curves['crece'])}
    current={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    if current != manifest['sources'] or hashlib.sha256(protocol.read_bytes()).hexdigest() != manifest['protocol_sha256']:
        raise ValueError('F2 code/protocol changed during run')
    if B3.frozen_state() != manifest['frozen_base'] or hashlib.sha256(inherited_protocol.read_bytes()).hexdigest() != manifest['inherited_protocol_sha256']:
        raise ValueError('F2 inherited base/protocol changed during run')
    if hashlib.sha256(provider_protocol.read_bytes()).hexdigest()!=manifest['provider_protocol_sha256']:
        raise ValueError('F2 provider protocol changed during run')
    if hashlib.sha256(feedback_protocol.read_bytes()).hexdigest()!=manifest['feedback_protocol_sha256']:
        raise ValueError('F2 feedback protocol changed during run')
    if hashlib.sha256(interface_protocol.read_bytes()).hexdigest()!=manifest['interface_protocol_sha256']:
        raise ValueError('F2 interface protocol changed during run')
    report={'phase':'F2','green':combined[MODELS[0]]['green'],'models':combined,'runs':results,'exam_run':False}
    save_new(root/'results.json',report)
    print(json.dumps({'phase':'F2','models':combined,'green':report['green']}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=LAB/'f2-v5-r1-interface120b')
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    run(args.root,args.jobs)
