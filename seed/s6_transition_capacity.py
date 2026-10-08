"""Preregistered human instrument controls; no model and no examination."""
import hashlib
import json
from pathlib import Path
import signal
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b8 as previous, s6_precise_capacity as capacity
from echo_arc import stale_transition as patch
from echo_arc.transition_observe import TransitionRecorder

REPO=previous.REPO
ROOT=REPO/'lab/seed/s6-transition-capacity-20260929'
LIVE=REPO/'lab/observability/s6-transition-capacity-20260929'
A=previous.A
B=[(v,seed,0,2000) for v in (2,3) for seed in range(24620,24640)]
SOURCES=list(dict.fromkeys(previous.SOURCES+['echo_arc/stale_transition.py','echo_arc/transition_observe.py',
    'seed/s6_transition_capacity.py','tests/test_stale_transition.py','docs/ECHO45-S6-TRANSITION-CONTROL.md']))
atomic,sha,canonical,now=previous.atomic,previous.sha,previous.canonical,previous.now


def strategy(program=None):return {'format':'local','program':patch.validate(patch.EMPTY if program is None else program)}


class Execution:
    @staticmethod
    def validate(value):
        if set(value)!={'format','program'} or value['format']!='local':raise ValueError('local policy only')
        return strategy(value['program'])
    @staticmethod
    def digest(value):return sha(Execution.validate(value))


Execution.play=staticmethod(FunctionType(capacity.Execution.play.__code__,dict(capacity.Execution.play.__globals__,
    patch=patch,Execution=Execution),'play',capacity.Execution.play.__defaults__))


def controls():
    specs=[('reset_stuck_1',{'reset_known':['eq',1],'stagnation':['ge',8]},1),
           ('body_stuck_1',{'body_known':['eq',1],'stagnation':['ge',8]},1),
           ('stuck_2',{'stagnation':['ge',8]},2),('stuck_4',{'stagnation':['ge',16]},4)]
    return [{'name':name,'candidate':strategy({'patches':[{'when':guard,'set':{'REVALIDATE_NOOP':limit}}]})}
            for name,guard,limit in specs]


def profile():
    previous.integrity()
    return {'parent_profile_sha256':sha(previous.integrity()),'sources':{
        name:hashlib.sha256((REPO/name).read_bytes()).hexdigest() for name in SOURCES},
        'A':A,'B':B,'controls':controls(),'llm_calls':0,'exam_access':False,'workers':4,'max_games':760}


def integrity():
    value=json.loads((ROOT/'profile.json').read_text())
    assert value==json.loads(canonical(profile())), 'frozen control source changed'
    return value


def status(stage,**fields):
    value={'at':now(),'stage':stage,**fields};atomic(ROOT/'status.json',value);print(canonical(value),flush=True)


def play_one(item):
    from echo_arc import agent,runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    value,spec,record_dir=item
    version,seed,rep,budget=spec
    assert version in (2,3) and (seed in range(20) or seed in range(24620,24640)) and rep==0 and budget==2000
    assert record_dir is None or seed in range(20)
    agent._COMP_CACHE.clear();signal.alarm(240);recorder=None
    try:
        env=_gym_env(version,seed);counted=previous.old.accounting().ResetCounter(env)
        if record_dir:
            recorder=TransitionRecorder(Journal(Path(record_dir)/'arc-decisions.jsonl'))
            recorder.write(kind='start',origin='DEVELOPMENT',agent='transition-capacity',budget=budget)
            recorder.write(kind='game',game=env.game_id)
        record=Execution.play(counted,budget,runner.seed_for(env.game_id,rep),value,recorder)
        record.update(version=version,seed=seed,rep=rep,budget=budget,game=env.game_id,family=env.game.fam,
                      baseline=env.baseline_actions,policy_sha256=Execution.digest(value),
                      automatic_reset_indices=counted.automatic,origin='DEVELOPMENT_A' if seed<20 else 'PROTECTED_B')
        record['score']=runner.official_game_score(record['actions_per_level'],env.baseline_actions)
        if recorder:record.update(episodes=recorder.episodes(),diagnostics=recorder.summary())
        assert counted.emitted==len(record['actions']);previous.old.accounting().check_record(record)
        return record
    finally:
        if recorder:recorder.write(kind='end',status='closed');recorder.close()
        signal.alarm(0)


measure=FunctionType(capacity.measure.__code__,dict(capacity.measure.__globals__,ROOT=ROOT,LIVE=LIVE,
    integrity=integrity,status=status,Execution=Execution,play_one=play_one),'measure',capacity.measure.__defaults__)
verify=FunctionType(previous.base.verify.__code__,dict(previous.base.verify.__globals__,A=A,B=B,patch=patch,
    strategy=strategy,c=SimpleNamespace(measure=measure,result=capacity.result)),'verify',previous.base.verify.__defaults__)


def run():
    p=profile()
    if (ROOT/'profile.json').exists():integrity()
    else:
        atomic(ROOT/'profile.json',p)
        for name in SOURCES:
            dest=ROOT/'source-archive'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((REPO/name).read_bytes())
    if (ROOT/'summary.json').exists():return
    a=measure('baseline/A',strategy(),A)
    native=json.loads((previous.ROOT/'measurements/baseline/A.json').read_text())
    assert all(capacity.same_behavior(x,y) for x,y in zip(a['rows'],native['rows']))
    disabled=strategy({'patches':[{'when':{'level':['ge',0]},'set':{'REVALIDATE_NOOP':0}}]})
    plain=measure('preflight/disabled',disabled,[(3,n,0,2000) for n in (0,1,11)])
    for row in plain['rows']:
        assert capacity.same_behavior(row,next(r for r in a['rows'] if r['version']==row['version'] and r['seed']==row['seed']))
    b=measure('baseline/B',strategy(),B,observed=False)
    atomic(ROOT/'preflight.json',{'pass':True,'A':a['levels'],'observed_contradictory_noops':sum(
        r['diagnostics']['counts'].get('contradictory_noop',0) for r in a['rows'])})
    verdicts=[];winner=None
    for control in controls():
        _,_,_,verdict=verify('controls/'+control['name'],canonical(control['candidate']['program']),strategy(),a,b)
        row=dict(verdict,name=control['name']);verdicts.append(row)
        atomic(ROOT/'verdicts'/f"{control['name']}.json",row)
        if row['verdict']=='accepted' and winner is None:winner=control['name']
        status('VERDICT',name=control['name'],verdict=row['verdict'],gain=row.get('A',{}).get('gain'))
    result={'at':now(),'positive':winner is not None,'winner':winner,'verdicts':verdicts,
            'profile_sha256':sha(integrity()),'human_control':True,'llm_calls':0,'exam_opened':False,'s6_green':False}
    atomic(ROOT/'summary.json',result);status('CLOSED',positive=result['positive'],winner=winner,s6_green=False)


if __name__=='__main__':
    from seed import s6_transition_capacity
    s6_transition_capacity.run()
