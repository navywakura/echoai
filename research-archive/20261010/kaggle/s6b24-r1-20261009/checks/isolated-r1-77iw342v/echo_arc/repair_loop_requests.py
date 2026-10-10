"""ECHO selects observed failure mechanisms; FIJO retains generic selection."""
from echo_arc import stale_transition as patch
from echo_arc.consumer_requests import public_read,public_features,public_outcome,compact_cases
from echo_arc.repair_diagnostics import compact


def feedback(history):
    return [{'proposal':patch.validate(v['proposal']) if v.get('proposal') else None,
             'verdict':v['verdict'],'protected_rejection':v['verdict']=='V4',
             'training':{k:v.get('A',{})[k] for k in ('gain','changed_action_games','activated_games') if k in v.get('A',{})}}
            for v in history[-6:]]


def evidence(rows,arm,history,index):
    if arm not in ('echo','fijo') or any(r['origin']!='DEVELOPMENT_A' for r in rows):
        raise ValueError('only paired development evidence')
    failing=[(i,r) for i,r in enumerate(rows) if r['levels_completed']<5]
    def count(row,kind):
        if kind=='transition':return row['diagnostics']['counts'].get('contradictory_noop',0)
        return sum(e['count'] for e in row['diagnostics']['consumers'] if e['parameter']=='HOLD')
    scores={kind:sum((5-r['levels_completed'])*count(r,kind) for _,r in failing) for kind in ('transition','wait')}
    # Discourage repeatedly ineffective question types using own A outcomes.
    for kind in scores:
        misses=sum(v.get('type')=='MECHANISM_'+kind.upper() and v.get('A',{}).get('gain',0)<=0 for v in history)
        scores[kind]=scores[kind]/(1+misses)
    focus=max(scores,key=lambda kind:(scores[kind],kind=='transition'))
    if arm=='fijo':selected=sorted(failing,key=lambda p:(p[1]['levels_completed'],p[0]))[:3]
    else:selected=sorted(failing,key=lambda p:(-bool(count(p[1],focus)),-p[1]['levels_completed'],
                                              -count(p[1],focus),p[0]))[:3]
    cases=[]
    for alias,(_,row) in enumerate(selected):
        d=row['diagnostics']
        cases.append({'case':alias,'levels':row['levels_completed'],
            'contradictory_noops':d['counts'].get('contradictory_noop',0),
            'contradiction_examples':[{'features':public_features(x['features']),
                'predicted_change':True,'observed_change':False} for x in d['contradictory_noop_examples'][:2]],
            'actual_wait_control_reads':[public_read(x) for x in sorted(d['consumers'],key=lambda e:-e['count'])[:2]],
            'latest_observed_outcome':public_outcome(d['witnesses'].get('terminal',{}))})
    return compact_cases(cases),focus


def requests(arm,round_id,count,current,measured,history):
    common=('Propose ONE bounded JSON repair to ECHO. Choose control then guard. '
        'Format {"patches":[{"set":{PARAM:INT},"when":{FEATURE:[OP,INT]}}]}. '
        'One parameter, at most three AND guards, operators eq/ge/le. Need >=2 more training levels '
        'without any individual level/score loss. Parameter bounds '+compact(patch.LIMITS)+
        '; native values '+compact(patch.DEFAULTS)+'; observable features '+compact(patch.FEATURES)+'. '
        'REVALIDATE_NOOP is a new available operation: 0 disabled; N>0 revises an existing prediction '
        'of change after N observed no-change contradictions under the guard. It records a self-loop '
        'and clears the queued plan, without erasing historical facts or declaring the action unsafe. '
        'Later changing observations can restore a transition. No correction on GAME OVER/level change. '
        'HOLD sets future reset waits at actual reads; COOLDOWN_CAP clamps a running wait and is '
        'introduced by a patch, so no native reads do not prove it is inactive. '
        'Read features inherit common_read_features plus their overrides. Other feature maps are complete. '
        'The examples are observations of the current actor, not guarantees about a new path. '
        'Current accepted program '+compact(current['program'])+'. Your own measured attempts '+
        compact(feedback(history))+'. No task IDs, coordinates, private state, solver or reserved data. ')
    output=[]
    for offset in range(count):
        index=round_id*count+offset
        cases,focus=evidence(measured['rows'],arm,history,index)
        ask='Here are three incomplete tasks. Propose a general repair that helps solve them. ' if arm=='fijo' else (
            'ECHO selected the '+focus+' mechanism from its observed unresolved failures. '
            'Repair that mechanism using these observations. If your last attempt gained levels but '
            'was rejected, refine magnitude or scope from your own training evidence. '
            'If it changed no actions, correct the guard/control rather than repeat it. '
            'A protected rejection supplies no private details. ')
        output.append({'id':index,'type':'GENERIC' if arm=='fijo' else 'MECHANISM_'+focus.upper(),
                       'prompt':common+ask+compact(cases)+' Return JSON only.'})
    return output
