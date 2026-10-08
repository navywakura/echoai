"""Draft next-condition prompt evidence; not used by frozen B8/CPU inference."""
from echo_arc import precise_patch as patch
from echo_arc.repair_diagnostics import compact, feedback


def public_features(value):
    out={key:value[key] for key in patch.FEATURES}
    if any(type(out[k]) is not int or not lo<=out[k]<=hi for k,(lo,hi) in patch.FEATURES.items()):
        raise ValueError('invalid observed feature')
    return out


def public_read(entry):
    if entry['parameter'] not in ('HOLD','COOLDOWN_CAP'):
        raise ValueError('unsupported consumer')
    result={key:entry[key] for key in ('parameter','value','remaining_before','count')}
    result['features']=public_features(entry['features'])
    if any(type(result[k]) is not int for k in ('value','remaining_before','count')) or result['count']<=0:
        raise ValueError('invalid consumer observation')
    return result


def public_outcome(value):
    if not value:return {}
    return {'features':public_features(value['features']),
            'outcome':{key:value['outcome'][key] for key in
                       ('changed','game_over','level_up','moved','new_events','new_prediction_errors')}}


def evidence(rows, arm, history, index):
    if arm not in ('echo','fijo') or any(r['origin']!='DEVELOPMENT_A' for r in rows):
        raise ValueError('only paired development evidence is allowed')
    failing = [(i,r) for i,r in enumerate(rows) if r['levels_completed']<5]
    previous = [v for v in history if v.get('proposal')]
    focus = next(iter(previous[-1]['proposal']['patches'][0]['set'])) if previous else 'HOLD'
    # Native COOLDOWN_CAP has no reads because the operator is introduced by a
    # patch. Lack of a native read must not be mistaken for an inactive patch.
    if focus not in ('HOLD','COOLDOWN_CAP'):focus='HOLD'
    def reads(r):
        return sum(x['count'] for x in r['diagnostics']['consumers'] if x['parameter']==focus)
    if arm=='fijo':selected=sorted(failing,key=lambda p:(p[1]['levels_completed'],p[0]))[:3]
    else:selected=sorted(failing,key=lambda p:(-bool(reads(p[1])),-p[1]['levels_completed'],-reads(p[1]),p[0]))[:3]
    cases=[]
    for alias,(_,row) in enumerate(selected):
        observed=sorted(row['diagnostics']['consumers'],key=lambda x:(x['parameter']!=focus,-x['count'],compact(x)))
        cases.append({'case':alias,'levels':row['levels_completed'],
                      'actual_wait_control_reads':[public_read(x) for x in observed[:3]],
                      'latest_observed_outcome':public_outcome(row['diagnostics']['witnesses'].get('terminal',{})),
                      'scope':'reads on the current actor path only; inserted operations may create new reads'})
    return cases,focus


def compact_cases(cases):
    """Lossless removal of repeated feature names/values across read sites."""
    import copy
    cases=copy.deepcopy(cases)
    reads=[entry for case in cases for entry in case['actual_wait_control_reads']]
    common={key:reads[0]['features'][key] for key in patch.FEATURES
            if reads and all(entry['features'][key]==reads[0]['features'][key] for entry in reads)}
    for entry in reads:
        entry['features']={key:value for key,value in entry['features'].items() if key not in common}
    return {'common_read_features':common,'cases':cases}


def requests(arm, round_id, count, current, measured, history):
    common=('Propose ONE bounded JSON patch for ECHO. Choose its control first, then the conditions. '
        'Format {"patches":[{"set":{PARAM:INT},"when":{FEATURE:[OP,INT]}}]}. '
        'At most three AND guards; operators eq/ge/le. Need >=2 additional training levels and '
        'no individual level/score losses. Bounds '+compact(patch.LIMITS)+'; native values '+compact(patch.DEFAULTS)+
        '; observable features '+compact(patch.FEATURES)+'. HOLD is read at a deliberate reset assignment: '
        'its supplied features describe a real consumption, not merely a matching guard. '
        'It changes a future wait, never a running wait. COOLDOWN_CAP introduces an operation that clamps '
        'the current wait; it can affect a native actor without having any native recorded reads. '
        'A default value or a guard that misses the relevant reads may have no effect. '
        'Changed consumption is not proof of improved actions or levels: execution decides. '
        'Each read inherits common_read_features plus its feature overrides; terminal features are complete. '
        'Current accepted program: '+compact(current['program'])+'. Your own measured attempts: '+
        compact(feedback(history))+'. No task IDs, private state, solver or reserved data. ')
    out=[]
    for offset in range(count):
        index=round_id*count+offset
        cases,focus=evidence(measured['rows'],arm,history,index)
        ask='Here are three incomplete tasks. Propose a general repair that helps solve them. ' if arm=='fijo' else (
            'Use the observed consumers to diagnose a near-success case. Focus '+focus+'. '
            'If your last proposal changed no actions, choose a different value, guard or control. '
            'If it gained levels but was rejected, refine its scope from training evidence. '
            'Protected rejection supplies no private details. ')
        out.append({'id':index,'type':'GENERIC' if arm=='fijo' else 'CONSUMPTION_'+focus,
                    'prompt':common+ask+compact(compact_cases(cases))+' Return JSON only.'})
    return out
