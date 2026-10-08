"""Independent reference adjudicator. Does not import or call the reducer.

Numbers are intentionally explicit so an implementation edit cannot silently
change the acceptance rule. Inputs and output WSP are decoded independently.
"""
import hashlib
import json
import struct


def expected(commands):
    events, seen, out = [], set(), []
    for cmd in commands:
        if cmd['op'] == 'observe':
            identity = {k:v for k,v in cmd.items() if k not in ('op','delivered_ns')}
            key = json.dumps(identity, sort_keys=True)
            if key not in seen:
                seen.add(key)
                events.append(cmd)
            continue
        selected = []
        for source in ('depth','rgb','lidar','host'):
            subset = [(i,e) for i,e in enumerate(events)
                      if e['source']==source and e['capture_ns']<=e['delivered_ns']
                      and tuple(bytes.fromhex(e['wsp'])[13:16]) ==
                      (cmd['predicate'],cmd['region'],cmd['epoch'])]
            if not subset:
                continue
            i,e=max(subset,key=lambda item:(item[1]['capture_ns'],item[0]))
            if source == 'host' or not e['valid'] or e['capture_ns']>e['delivered_ns'] \
                    or not 0 <= cmd['now_ns']-e['capture_ns'] <= 250_000_000 \
                    or not e['extract'] or hashlib.sha256(e['extract'].encode()).hexdigest()!=e['extract_sha256']:
                continue
            raw=bytes.fromhex(e['wsp'])
            if raw[1:3] not in (bytes([14,5]),bytes([14,7])):
                continue
            selected.append((i,e,1 if raw[2]==5 else 0))
        if selected:
            newest=max(e['capture_ns'] for _,e,_ in selected)
            selected=[r for r in selected if newest-r[1]['capture_ns']<=100_000_000]
        values={v for _,_,v in selected}
        sources={('camera' if e['source'] in ('depth','rgb') else 'lidar') for _,e,_ in selected}
        value=next(iter(values)) if len(values)==1 else -1
        confidence=80 if value!=-1 and len(sources)>=2 else 40 if value!=-1 else 0
        rel,dst=(31,31) if value==-1 else (14,5 if value else 7)
        wsp=struct.pack('<BBBBbbbbbbBBBBBB',2,rel,dst,8,0,10,0,confidence,0,0,0,8,7,
                        cmd['predicate'],cmd['region'],cmd['epoch']).hex()
        out.append(dict(wsp=wsp,allow_advance=cmd['predicate']==1 and value==0 and confidence>=80,
                        attend=len(values)>1 and len(sources)>=2,history_n=len(events)))
    return out


def findings(commands, result):
    wanted=expected(commands)
    failures=[]
    if len(result.get('decisions',[]))!=len(wanted):
        return ['query_count']
    for i,(a,b) in enumerate(zip(wanted,result['decisions'])):
        for key in a:
            if a[key]!=b.get(key):failures.append(f'{i}/{key}')
    if len(result.get('history',[])) != (wanted[-1]['history_n'] if wanted else 0):
        failures.append('history_retained')
    return failures


def last_writer(commands):
    value=None
    out=[]
    for c in commands:
        if c['op']=='observe':
            w=bytes.fromhex(c['wsp']);value=0 if w[2]==7 else 1 if w[2]==5 else None
        else:out.append(value==0)
    return out


def wilson(success,n):
    if not n:return None
    z=1.959963984540054; p=success/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*((p*(1-p)/n+z*z/(4*n*n))**.5)/den
    return [max(0.,mid-half),min(1.,mid+half)]
