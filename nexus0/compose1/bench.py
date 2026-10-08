"""Audited functional composition; never relabels a kinematic run as PX4."""
import argparse
import copy
import json
import random
import select
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path
from .space import Space,DIRECTIONS,add,distance
from .controller import Composer
from .training import train
from echoai.nexus0.fusion1.bench import seal
from echoai.nexus0.fusion1.replay import ECHOAI,file_hash
from echoai.nexus0.sim3.sandbox import bwrap_argv,self_test
from echoai.nexus0.sim3.runtime import Runtime

HERE=Path(__file__).resolve().parent
ROOT=ECHOAI/'lab/compose1'
REPORT=ECHOAI/'lab/echo3_compose1_report.json'
MODES=('echo8','echo32','q','no_expiry','conventional','one_step')
CONDITIONS=('static','dynamic','closed','low_energy')
PROTOCOL=dict(version=1,development=list(range(20261801,20261817)),
              validation=list(range(202618101,202618133)),
              confirmation=list(range(202618201,202618233)),
              modes=list(MODES),conditions=list(CONDITIONS),max_steps=64,
              depth=4,budgets=[8,32],body_radius_mm=400,cell_mm=1000,
              simulator='integer_kinematic_voxels',sitl_gate=False)
MODULES=('constants.py','types.py','qtable.py','world.py','gate.py',
         'fusion1/core.py','fusion1/integration.py','compose1/controller.py','compose1/model.py')
PARENT_MODULES=('core/cam.py','core/qn.py','core/wsp.py')


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'x') as f:json.dump(value,f,sort_keys=True,indent=2)


def inventory():
    paths=list(HERE.glob('*.py'))+[ECHOAI/'nexus0'/m for m in MODULES]
    paths += [ECHOAI.parent/m for m in PARENT_MODULES]
    paths += [ECHOAI/'tests/test_compose1.py',ECHOAI/'docs/COMPOSE1-DESIGN.md',
              ECHOAI/'nexus0/fusion1/bench.py',ECHOAI/'nexus0/fusion1/replay.py',
              ECHOAI/'nexus0/sim3/sandbox.py',ECHOAI/'nexus0/sim3/runtime.py']
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.name):file_hash(p) for p in sorted(set(paths))}


class Caged:
    def __init__(self,model,goal,mode):
        self.tmp=tempfile.TemporaryDirectory(prefix='compose1-code-')
        library=Path(self.tmp.name)
        for m in MODULES:
            dest=library/'echoai/nexus0'/m;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ECHOAI/'nexus0'/m,dest)
        for m in PARENT_MODULES:shutil.copyfile(ECHOAI.parent/m,library/m)
        argv=bwrap_argv(HERE/'consumer.py');split=argv.index('--remount-ro')
        argv[split:split]=['--ro-bind',str(library),'/agent']
        self.proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
        self.ready=self.call(dict(model=model,goal=list(goal),mode=mode))
        if self.ready['spatial_cells']!=0:raise ValueError('inherited map')

    def call(self,frame):
        self.proc.stdin.write(json.dumps(frame,sort_keys=True)+'\n');self.proc.stdin.flush()
        if not select.select([self.proc.stdout],[],[],15)[0]:raise TimeoutError('consumer response')
        line=self.proc.stdout.readline()
        if not line:raise RuntimeError(self.proc.stderr.read()[-800:])
        return json.loads(line)

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
        self.proc.stdout.close();self.proc.stderr.close();self.tmp.cleanup()


def true_home_distance(world,p):
    if p in world.solids or not (0<p[0]<6 and 0<p[1]<6 and 0<p[2]<4):return None
    queue=deque([(p,0)]);seen={p}
    while queue:
        node,n=queue.popleft()
        if node==world.start:return n
        for delta in DIRECTIONS[:6]:
            nxt=add(node,delta)
            if nxt not in seen and nxt not in world.solids and 0<nxt[0]<6 and 0<nxt[1]<6 and 0<nxt[2]<4:
                seen.add(nxt);queue.append((nxt,n+1))
    return None


def mission(snapshot,seed,condition,mode,*,isolated=True,trace_path=None):
    world=Space(seed,condition)
    oracle=world.oracle_distance()
    agent=Caged(snapshot,world.goal,mode) if isolated else Composer(snapshot,world.goal,mode)
    baseline=agent.ready['model_sha256'] if isolated else agent.model.fingerprint()
    records=[];durations=[];reserve_violations=0;false_facts=0
    fh=open(trace_path,'x') if trace_path else None
    try:
        for _ in range(PROTOCOL['max_steps']+1):
            frame=world.scan();start=time.perf_counter_ns()
            response=agent.call(frame) if isolated else agent.decide(frame)
            durations.append(time.perf_counter_ns()-start)
            event=dict(observation=frame,prediction=response)
            # The prediction is written and flushed BEFORE the body executes.
            if fh:fh.write(json.dumps(dict(kind='before_action',**event),sort_keys=True)+'\n');fh.flush()
            status=response['status']
            if status not in ('moving','returning'):
                false_facts+=status=='reached' and not (frame['station_observed'] and world.pos==world.goal)
                event['consequence']=None;records.append(event)
                break
            w=bytes.fromhex(response['wsp']);action=w[13]
            if len(w)!=16 or w[1]!=11 or not 0<=action<6:raise ValueError('invalid action WSP')
            target=add(world.pos,DIRECTIONS[action]);home=true_home_distance(world,target)
            reserve_violations += home is None or world.energy-4<(home*4+10)
            consequence=world.step(action);event['consequence']=consequence;records.append(event)
            if fh:fh.write(json.dumps(dict(kind='after_action',consequence=consequence),sort_keys=True)+'\n');fh.flush()
        else:status='budget_exhausted'
    finally:
        if fh:fh.close()
        if isolated:agent.close()
    last=records[-1]['prediction'];timings=sorted(durations)
    return dict(seed=seed,condition=condition,mode=mode,records=records,status=status,
                reached=status=='reached' and not false_facts,collisions=world.collisions,
                false_facts=false_facts,reserve_violations=reserve_violations,
                imagined_writes=last['imagined_writes'],model_unchanged=all(r['prediction']['model_sha256']==baseline for r in records),
                expansions_max=max(r['prediction']['candidates'] for r in records),
                depth_max=max(r['prediction']['depth'] for r in records),
                steps=world.steps,energy_remaining=world.energy,revisions=last['revisions'],
                ended_home=world.pos==world.start,oracle_static_steps=oracle,
                oracle_static_feasible=oracle is not None and 2*oracle*4+10<=(30 if condition=='low_energy' else 240),
                isolated=isolated,initial_map_cells=0,model_initial_sha256=baseline,
                performance=dict(p99_ns=timings[min(len(timings)-1,len(timings)*99//100)],
                                 scope='whole_consumer_round_trip_including_audit_hashes',
                                 spatial_cells=last['spatial_cells'],cam_used=last['cam_used']))


def metrics(rows):
    groups={}
    for mode in MODES:
        subset=[r for r in rows if r['mode']==mode]
        groups[mode]={kind:dict(missions=sum(r['condition']==kind for r in subset),
                               reached=sum(r['reached'] for r in subset if r['condition']==kind),
                               ended_home=sum(r['ended_home'] for r in subset if r['condition']==kind)) for kind in CONDITIONS}
        groups[mode]['totals']={key:sum(r[key] for r in subset) for key in ('collisions','false_facts','reserve_violations','imagined_writes','steps')}
    paired=[]
    for r in rows:
        if r['mode']=='echo32' and r['oracle_static_feasible']:
            q=next(x for x in rows if x['mode']=='q' and x['seed']==r['seed'])
            paired.append(int(r['reached'])-int(q['reached']))
    rng=random.Random(20261899)
    means=sorted(sum(rng.choice(paired) for _ in paired)/len(paired) for _ in range(2000)) if paired else [0.]
    complete=[r for r in rows if r['mode'] in ('echo8','echo32')]
    safe=bool(complete) and all(r['collisions']==r['false_facts']==r['reserve_violations']==r['imagined_writes']==0 and r['model_unchanged'] and r['depth_max']<=4 and r['expansions_max']<=(8 if r['mode']=='echo8' else 32) for r in complete)
    return dict(groups=groups,paired_difference=sum(paired),paired_missions=len(paired),
                paired_mean_interval_95=[means[len(means)*25//1000],means[min(len(means)-1,len(means)*975//1000)]],
                safe=safe,functional_green=safe and sum(paired)>0)


def stage(name,seeds,snapshot):
    root=ROOT/name;root.mkdir()
    rows=[]
    for index,seed in enumerate(seeds):
        condition=CONDITIONS[index%4]
        for mode in MODES:
            label=f'{seed}-{mode}'
            row=mission(snapshot,seed,condition,mode,trace_path=root/(label+'.jsonl'))
            save(root/(label+'.json'),seal(row));rows.append(row)
        print(json.dumps(dict(stage=name,seed=seed,condition=condition,
                              reached={r['mode']:r['reached'] for r in rows[-len(MODES):]})),flush=True)
    result=seal(dict(name=name,missions=len(rows),metrics=metrics(rows),
                     records={p.name:file_hash(p) for p in sorted(root.glob('*'))}))
    save(root/'report.json',result)
    return result


def develop():
    if (ROOT/'development').exists():raise FileExistsError('development already recorded')
    snapshot,info=train();save(ROOT/'training.json',seal(dict(model=snapshot,info=info)))
    r=stage('development',PROTOCOL['development'],snapshot)
    save(ROOT/'development-candidate.json',seal(dict(inventory=inventory(),report_sha256=r['sha256'])))
    print(json.dumps(r['metrics'],indent=2));return r['metrics']['functional_green']


def mutants(snapshot):
    out=[]
    for mode,condition,key in [('write_rollout','static','imagined_writes'),
                                ('ignore_evidence','static','collisions'),
                                ('ignore_reserve','low_energy','reserve_violations')]:
        r=mission(snapshot,20261801,condition,mode)
        twin=mission(snapshot,20261801,condition,'echo32')
        out.append(dict(name=mode,caught=r[key]>0,honest_passed=twin[key]==0,metric=key,value=r[key]))
    world=Space(20261801)
    pair=[]
    for mode in ('goal_is_fact','echo32'):
        agent=Caged(snapshot,world.start,mode)
        try:pair.append(agent.call(world.scan())['status'])
        finally:agent.close()
    out.append(dict(name='goal_is_fact',caught=pair[0]=='reached',honest_passed=pair[1]!='reached'))
    agent=Caged(snapshot,world.goal,'echo32');caught=False
    try:
        frame=world.scan();frame['world_id']=20261801
        try:agent.call(frame)
        except RuntimeError:caught=True
    finally:agent.close()
    out.append(dict(name='private_id',caught=caught,honest_passed=True))
    return out


def compare_record(record,expected):
    # Timing is a host measurement, never a functional green criterion.
    ignored={'performance','isolated','sha256'}
    a={k:v for k,v in record.items() if k not in ignored}
    b={k:v for k,v in expected.items() if k not in ignored}
    return [k for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)]


def tamper_tests(record,expected):
    changes={
        'omit_step':lambda r:r['records'].pop(),
        'fake_success':lambda r:r.update(reached=not r['reached']),
        'alter_prediction':lambda r:r['records'][0]['prediction'].update(prediction=[99,99,99]),
        'alter_action':lambda r:r['records'][0]['prediction'].update(wsp='00'*16),
        'hide_writes':lambda r:r.update(imagined_writes=1),
        'fake_result':lambda r:r.update(energy_remaining=-999)}
    results=[]
    for name,change in changes.items():
        r=copy.deepcopy(record);change(r);fs=compare_record(r,expected)
        results.append(dict(name=name,caught=bool(fs),findings=fs))
    return results


def audit_stage(name,seeds,snapshot):
    root=ROOT/name;r=json.loads((root/'report.json').read_text());issues=[];rows=[]
    if r!=seal(r):issues.append('report_hash')
    files={p.name:file_hash(p) for p in sorted(root.glob('*')) if p.name!='report.json'}
    if r['records']!=files:issues.append('evidence_files')
    for index,seed in enumerate(seeds):
        for mode in MODES:
            saved=json.loads((root/f'{seed}-{mode}.json').read_text())
            if saved!=seal(saved):issues.append(f'{seed}/{mode}/hash')
            replayed=mission(snapshot,seed,CONDITIONS[index%4],mode,isolated=False)
            fs=compare_record(saved,replayed)
            if fs:issues.append(f'{seed}/{mode}/'+','.join(fs))
            # The append-only stream must show before/after in exact order.
            stream=[json.loads(line) for line in (root/f'{seed}-{mode}.jsonl').read_text().splitlines()]
            rebuilt=[]
            for step in replayed['records']:
                rebuilt.append(dict(kind='before_action',observation=step['observation'],prediction=step['prediction']))
                if step['consequence'] is not None:rebuilt.append(dict(kind='after_action',consequence=step['consequence']))
            if stream!=rebuilt:issues.append(f'{seed}/{mode}/publication_order')
            rows.append(replayed)
    calculated=metrics(rows)
    if calculated!=r['metrics'] or r['missions']!=len(rows):issues.append('metrics/denominator')
    tamper=tamper_tests(json.loads((root/f'{seeds[0]}-echo32.json').read_text()),rows[1])
    if not all(t['caught'] for t in tamper):issues.append('auditor_mutations')
    return dict(evidence_valid=not issues,findings=issues,missions=len(rows),metrics=calculated,tamper_tests=tamper)


def accept():
    if (ROOT/'lock.json').exists() or REPORT.exists():raise FileExistsError('immutable chain')
    dev=json.loads((ROOT/'development/report.json').read_text())
    candidate=json.loads((ROOT/'development-candidate.json').read_text())
    if not dev['metrics']['functional_green'] or candidate['inventory']!=inventory():raise ValueError('development red or changed')
    trained=json.loads((ROOT/'training.json').read_text())
    regression=subprocess.run([sys.executable,'-m','echoai.tests.test_compose1','-q'],capture_output=True)
    save(ROOT/'regression.json',dict(returncode=regression.returncode,output=(regression.stdout+regression.stderr).decode()))
    if regression.returncode:raise RuntimeError('regression')
    isolation=self_test(Runtime(available=True,lock=json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']))
    if not isolation['ok']:raise RuntimeError('cage')
    negative=mutants(trained['model']);save(ROOT/'mutants.json',negative)
    if not all(m['caught'] and m['honest_passed'] for m in negative):raise RuntimeError('mutant sensitivity')
    lock=seal(dict(protocol=PROTOCOL,inventory=inventory(),training_sha256=file_hash(ROOT/'training.json'),
                   development_sha256=dev['sha256'],fusion1_sha256=file_hash(ECHOAI/'lab/echo3_fusion1_report.json'),
                   isolation=isolation,mutants_sha256=file_hash(ROOT/'mutants.json'),regression_sha256=file_hash(ROOT/'regression.json')))
    save(ROOT/'lock.json',lock);stages={};errors=[]
    try:
        for name in ('validation','confirmation'):
            r=stage(name,PROTOCOL[name],trained['model']);stages[name]=r['metrics']
            if not r['metrics']['functional_green']:break
    except Exception as e:errors.append(type(e).__name__+': '+str(e))
    green=not errors and len(stages)==2 and all(s['functional_green'] for s in stages.values()) and inventory()==lock['inventory']
    audits={name:audit_stage(name,PROTOCOL[name],trained['model']) for name in stages}
    valid=not errors and inventory()==lock['inventory'] and all(a['evidence_valid'] for a in audits.values())
    result=seal(dict(functional_green=green and valid,compose1_green=False,evidence_valid=valid,
                     lock_sha256=lock['sha256'],stages=stages,audits=audits,mutants=negative,
                     errors=errors,sitl_gate=False,pending=['Gazebo/PX4 execution of learned effects and reserved physical transfer']))
    save(REPORT,result);print(json.dumps(result,indent=2));return result['functional_green']


def audit():
    lock=json.loads((ROOT/'lock.json').read_text());report=json.loads(REPORT.read_text());issues=[]
    if lock!=seal(lock) or report!=seal(report) or report['lock_sha256']!=lock['sha256']:issues.append('seal')
    if inventory()!=lock['inventory'] or lock['protocol']!=PROTOCOL:issues.append('code/protocol')
    for path,key in [('training.json','training_sha256'),('mutants.json','mutants_sha256'),('regression.json','regression_sha256')]:
        if file_hash(ROOT/path)!=lock[key]:issues.append(path)
    if file_hash(ECHOAI/'lab/echo3_fusion1_report.json')!=lock['fusion1_sha256']:issues.append('fusion_parent')
    training=json.loads((ROOT/'training.json').read_text())
    regenerated,info=train()
    if training['model']!=regenerated or training['info']!=info:issues.append('training_recomputed')
    audits={name:audit_stage(name,PROTOCOL[name],regenerated) for name in report['stages']}
    if audits!=report['audits']:issues.append('audit_summary')
    if report['mutants']!=json.loads((ROOT/'mutants.json').read_text()):issues.append('mutants_summary')
    valid=not issues and all(a['evidence_valid'] for a in audits.values())
    green=valid and len(audits)==2 and all(a['metrics']['functional_green'] for a in audits.values())
    if report['functional_green']!=green or report['evidence_valid']!=valid or report['compose1_green'] or report['sitl_gate']:issues.append('verdict')
    result=dict(evidence_valid=valid and not issues,functional_green=green and not issues,compose1_green=False,findings=issues)
    print(json.dumps(result,indent=2));return result['evidence_valid']


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('develop','accept','audit'))
    args=ap.parse_args();raise SystemExit(0 if globals()[args.command]() else 1)
