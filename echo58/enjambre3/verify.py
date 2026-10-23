"""Offline audit adapted from C2; independently resolves C3, never executes worlds."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from ..enjambre.team import Private as LegacyPrivate,Reader as LegacyReader,L1,L2,RM,ACTS,as_counts,read
from ..memx.memory import OUTCOMES
from . import bench as b
from ..enjambre2.transport import BAD,decode,require


def resolved(arm,entries,me,good,bad,layer):
    # Independently specified reader; no import of C3 Reader or candidate resolver.
    if arm.startswith(('v3_n','sin_alarma_n','sin_liberacion_n')):
        nmin=int(arm.rsplit('n',1)[1])
        entries={a:c for a,c in entries.items() if a!=me and c[1]>=nmin and 100*c[1]>=85*c[2]
                 and (bad.get(a,0)==0 or good.get(a,0)>=3*bad[a])}
        if not entries:return None
        if layer==RM:return 'LINK' if len(entries)>=2 else None
        danger=sum(OUTCOMES[c[0]] in BAD for c in entries.values())
        if danger:
            return None if danger==1 and arm.startswith('sin_alarma_') else 'HURT'
        names={OUTCOMES[c[0]] for c in entries.values()}
        return next(iter(names)) if len(names)==1 else None
    entries={a:c for a,c in entries.items() if arm not in ('prudente','por_autor') or
             (a!=me and c[1]>=3 and c[1]*100>=85*c[2])}
    if arm=='prudente':entries={a:c for a,c in entries.items() if not bad.get(a,0) or good.get(a,0)>=3*bad[a]}
    if arm=='sin_global' or not entries:return None
    if arm=='prudente':
        voices=sum(good.get(a,0)>0 for a in entries)+int(any(not good.get(a,0) for a in entries))
        if layer==RM:return 'LINK' if voices>=2 else None
        names=[OUTCOMES[c[0]] for c in entries.values()]
        if all(x in BAD for x in names):return 'HURT' if voices>=2 else None
        return names[0] if len(set(names))==1 and names[0] not in BAD else None
    counts=[0]*7
    for o,n,total in entries.values():
        if arm=='por_autor':n=total=3
        counts[o]+=n;counts[6]+=total-n
    best=max(range(6),key=lambda i:(counts[i],-i));total=sum(counts);answer=None
    if counts[best]>=3 and 100*counts[best]>=85*total:answer=OUTCOMES[best]
    elif counts[1]+counts[2]>=3 and 100*(counts[1]+counts[2])>=85*total:answer='HURT'
    return answer if layer!=RM else ('LINK' if answer=='PASS' else None)


def validate_request(q,private,notes):
    request=q['request'];layer=q['layer'];key=tuple(q['key'])
    require(type(request) is list and layer in (L1,L2,RM),'physical request schema')
    rd=LegacyReader(private.mem.cfg,private,None,notes,world=q['world'])
    if layer==RM:
        require(len(request)==2 and all(type(i) is int and 1<=i<=255 for i in request),'remote request')
        require(tuple(request)==key and not rd.knows(*request),'remote key/private precedence')
    else:
        require(len(request)==4,'recall request')
        ident,sig,act,hand=request
        require(type(ident) is int and 1<=ident<=255 and type(sig) is int and 0<=sig<=127 and
            act in ACTS and type(hand) is int and 0<=hand<=255,'recall request values')
        derived=private.mem.cfg.l1_key(*request) if layer==L1 else private.mem.cfg.l2_key(sig,act,hand)
        require(derived==key and rd.recall(*request) is None,'recall key/local/private/notes precedence')


def validate_job(job,x):
    phase=x['phase'];threshold=x['threshold']
    require(x.get('exam_run') is False and phase in b.BASES,'fresh study only')
    arm,attack,m=job
    require((x['arm'],x['attack'],x['macro'])==tuple(job) and tuple(job) in b.jobs(phase,threshold),'job identity')
    require(x['worlds']==b.mission(m,phase) and x['bad_author']==m%4,'mission/author altered')
    require(x['language_ids']==list(b.language(b.BASES[phase]+1000*m+999).values()),'language altered')
    require(x['destroyed']==0,'memory destruction')
    publications=x['publications'];latest={};provenance={};cursor=0;ids=set()
    private=[LegacyPrivate() for _ in range(4)];good=[{} for _ in range(4)];bad=[{} for _ in range(4)]
    query_private=[LegacyPrivate() for _ in range(4)];query_obs=[0]*4;query_remote=[0]*4
    verified=[set() for _ in range(4)];events=[[] for _ in range(4)]
    histories=[{0:({},{})} for _ in range(4)];observed=[0]*4
    solved=[31]*8;st={'episodes':0,'failed':0,'harm':0,'postcards':len(publications),
        'notes_cards':sum(len(n['postcards']) for n in x['notes']),'helps':len(x['notes']),'asked':0,'held':0,
        'answers':dict.fromkeys(('here','private','notes','global'),0),
        'by_kind':{k:{'harm':0,'episodes':0} for k in b.KINDS}}
    exposure=affected=global_asks=abstentions=altered=0;kind_failed=dict.fromkeys(b.KINDS,0)
    require(1<=len(x['rounds'])<=30,'round budget')
    for rr in x['rounds']:
        r=rr['round'];require(r==x['rounds'].index(rr)+1,'round order')
        require(rr['postcards_before']==cursor,'round snapshot changed')
        episodes=rr['episodes'];participants={ep['agent']:ep['world'] for ep in episodes}
        require(len(participants)==len(episodes),'duplicate agent episode')
        require(participants=={a:w for a,w in enumerate(rr['assignments']) if w is not None},'assignment episode mismatch')
        if r==1:require(rr['assignments']==[0,1,2,3],'initial assignment')
        else:require(rr['assignments']==x['rounds'][r-2]['next_assignments'],'assignment continuity')
        for a in range(4):
            for obs in x['observations'][a]:
                if obs[0]!=r:continue
                _,w,i,s,act,h,outcome=obs
                require(participants.get(a)==w and outcome in OUTCOMES,'unowned physical observation')
                cfg=private[a].mem.cfg;pending=[]
                for layer,key in ((L1,cfg.l1_key(i,s,act,h)),(L2,cfg.l2_key(s,act,h))):
                    speakers={author:c for author,c in latest.get((layer,key),{}).items()
                        if author!=a and c[1]>=3 and c[1]*100>=85*c[2]}
                    disputed=len({OUTCOMES[c[0]] in BAD for c in speakers.values()})>1;updates=[]
                    for author,c in sorted(speakers.items()):
                        ident=(layer,key,author)
                        if ident in verified[a]:continue
                        wrong=int((OUTCOMES[c[0]] in BAD)!=(outcome in BAD));credit=int(not wrong and disputed)
                        updates.append([author,wrong,credit]);pending.append((ident,author,wrong,credit))
                    if updates:events[a].append({'round':r,'world':w,'layer':layer,'key':list(key),'outcome':outcome,
                        'speakers':[[author,*c] for author,c in sorted(speakers.items())],'updates':updates})
                for ident,author,wrong,credit in pending:
                    verified[a].add(ident)
                    if wrong:bad[a][author]=bad[a].get(author,0)+wrong
                    if credit:good[a][author]=good[a].get(author,0)+credit
                observed[a]+=1;histories[a][observed[a]]=(dict(good[a]),dict(bad[a]))
                private[a].world=w;private[a].observe(i,s,act,h,outcome)
            for row in x['remote_observations'][a]:
                if row[0]!=r:continue
                _,w,p,changed=row;require(participants.get(a)==w,'unowned remote observation')
                private[a].world=w;private[a].remote_observe(p,changed)
        for ep in episodes:
            a=ep['agent'];w=ep['world'];res=ep['result'];kind=x['worlds'][w]['kind']
            require(type(ep['win']) is bool and 0<=res['steps']<=300 and res['harm'] in (0,1),'physical budget')
            require(solved[w]==31,'episode after solved world')
            st['episodes']+=1;st['failed']+=not ep['win'];st['harm']+=res['harm']
            kind_failed[kind]+=not ep['win']
            st['asked']+=res['asked'];st['held']+=res['held'];st['by_kind'][kind]['episodes']+=1
            st['by_kind'][kind]['harm']+=res['harm']
            for key,value in ep['answers'].items():st['answers'][key]+=value
            global_asks+=ep['global_asks'];abstentions+=ep['abstentions'];logged=answered=recalls=0
            for q in sorted(ep['queries'],key=lambda q:(q['observation_index'],q['remote_observation_index'])):
                require((q['agent'],q['world'],q['round'])==(a,w,r),'query context')
                layer=q['layer'];key=tuple(q['key']);entries=latest.get((layer,key),{});ps=provenance.get((layer,key),{})
                if arm=='oraculo':entries={p:c for p,c in entries.items() if p!=m%4};ps={p:i for p,i in ps.items() if p!=m%4}
                require(q['entries']==[[p,*c] for p,c in sorted(entries.items())] and
                    q['postcards']==[[p,i] for p,i in sorted(ps.items())],'query evidence changed')
                require(q['observation_index'] in histories[a],'query saw future observation')
                oi=q['observation_index'];ri=q['remote_observation_index'];qp=query_private[a]
                require(type(oi) is int and type(ri) is int and query_obs[a]<=oi<=len(x['observations'][a]) and
                    query_remote[a]<=ri<=len(x['remote_observations'][a]),'query history positions')
                for observation in x['observations'][a][query_obs[a]:oi]:
                    when,world,ident,sig,act,hand,outcome=observation
                    require(when<=r,'future private observation');qp.world=world;qp.observe(ident,sig,act,hand,outcome)
                for remote in x['remote_observations'][a][query_remote[a]:ri]:
                    when,world,p,changed=remote;require(when<=r,'future remote observation')
                    qp.world=world;qp.remote_observe(p,changed)
                query_obs[a]=oi;query_remote[a]=ri
                notes={};handovers=[n for n in x['notes'] if n['agent']==a and n['after_round']<r]
                if handovers:
                    grouped=defaultdict(list)
                    for raw in handovers[-1]['postcards']:
                        nl,_,nk,o,n,total=read(bytes.fromhex(raw))
                        grouped[(RM,nk) if nl==RM else nk].append((o,n,total))
                    notes={nk:as_counts(cs) for nk,cs in grouped.items()}
                validate_request(q,qp,notes)
                g,d=histories[a][q['observation_index']]
                require(q['good']=={str(p):n for p,n in g.items()} and q['bad']=={str(p):n for p,n in d.items()},'query trust changed')
                indices=sorted(i for p,i in ps.items() if p!=a and publications[i]['altered'])
                clean={p:c for p,c in entries.items() if not publications[ps[p]]['altered']}
                require(q['altered']==indices,'exposure index changed')
                require(q['reply']==resolved(arm,entries,a,g,d,layer) and
                    q['without_altered']==resolved(arm,clean,a,g,d,layer),'query resolution changed')
                n=q['count'];require(type(n) is int and n>0,'query count')
                logged+=n;answered+=n*(q['reply'] is not None);recalls+=n*(q['reply'] is not None and layer!=RM)
                if indices:exposure+=n;affected+=n*(q['reply']!=q['without_altered'])
            require(logged<=ep['global_asks'] and ep['global_asks']-ep['abstentions']==answered,'query accounting')
            require(ep['answers']['global']==recalls,'global recall count')
        for w in {ep['world'] for ep in episodes if ep['win']}:solved[w]=r
        after=rr['postcards_after'];require(cursor<=after<=len(publications),'publication boundary')
        batch=publications[cursor:after];by_author=defaultdict(list)
        for pub in batch:by_author[pub['author']].append(pub)
        for a,w in participants.items():
            expected=private[a].l2_cards(a)+private[a].l1_cards(a)+private[a].remote_cards(a)
            actual=by_author.get(a,[])
            require([p['original'] for p in actual]==[raw.hex() for raw in expected],'original postcard not from private consequences')
            if a==m%4 and arm!='honesto':
                for raw in expected:
                    layer,_,key,*_=decode(raw,a)
                    if layer==L1:ids.update(i for i in (key[0],key[3]) if i)
                    elif layer==RM:ids.update(i for i in key if i)
            for pub,raw in zip(actual,expected):
                sent=bytearray(raw);layer,_,key,o,n,total=decode(raw,a)
                if a==m%4 and arm!='honesto':
                    if layer!=RM and ((attack=='false_safe' and OUTCOMES[o] in BAD) or
                                      (attack=='false_alarm' and OUTCOMES[o] not in BAD)):
                        sent[2]=0 if attack=='false_safe' else 2;sent[14]=sent[15]=255
                    elif layer==RM and attack=='false_remote':
                        choices=sorted(ids-set(key))
                        if choices:sent[2]=choices[0];sent[14]=sent[15]=255
                require(pub['sent']==bytes(sent).hex() and pub['altered']==(raw!=bytes(sent)),'attack changed')
        for pub in batch:
            require(pub['index']==cursor and pub['round']==r and pub['author'] in participants,'publication provenance')
            layer,a,key,o,n,total=decode(bytes.fromhex(pub['sent']),pub['author'])
            latest.setdefault((layer,key),{})[a]=(o,n,total);provenance.setdefault((layer,key),{})[a]=cursor
            altered+=pub['altered'];cursor+=1
        for note in (n for n in x['notes'] if n['after_round']==r):
            a=note['agent'];w=note['world'];expected=[]
            require(rr['next_assignments'][a]==w,'handoff destination')
            for sender in range(4):
                if sender!=a:expected.extend(raw.hex() for raw in private[sender].notes_cards(sender,w))
            require(note['postcards']==expected,'handoff notes changed')
    require(cursor==len(publications),'unconsumed publications')
    require(len(x['rounds'])==30 or all(s<31 for s in solved),'incomplete development job')
    for a in range(4):
        require(observed[a]==len(x['observations'][a]),'observation outside played rounds')
        expected={'good':{str(p):n for p,n in good[a].items()},'bad':{str(p):n for p,n in bad[a].items()},
            'events':events[a],'verified':len(verified[a])}
        require(x['trust'][a]==expected,'trust ledger changed')
    require(x['card_bytes']==([16] if publications else []),'packet size receipt')
    require(x['solved_round']==solved and x['score']==sum(solved) and x['solved']==sum(s<31 for s in solved),'score altered')
    for k,v in st.items():require(x[k]==v,'aggregate altered: '+k)
    trust_by_author={str(p):{'good':sum(good[a].get(p,0) for a in range(4)),
        'bad':sum(bad[a].get(p,0) for a in range(4))} for p in range(4)}
    by_kind_details={k:dict(st['by_kind'][k],failed=kind_failed[k],
        score=sum(s for w,s in zip(x['worlds'],solved) if w['kind']==k),
        solved=sum(s<31 for w,s in zip(x['worlds'],solved) if w['kind']==k)) for k in b.KINDS}
    physical={'probe_actions':0,'probe_harm':0,'released_actions':0,'released_harm':0,
              'harm_probe_legacy':0,'steps':0,'actions':0,'release_queries':0}
    for a in range(4):
        action_rows=[]
        for rr in x['rounds']:
            for ep in rr['episodes']:
                if ep['agent']!=a:continue
                r=ep['result'];physical['steps']+=r['steps'];physical['harm_probe_legacy']+=r['harm_probe']
                physical['release_queries']+=r['release_queries']
                require(r['release_queries']>=0,'negative release queries')
                for action in r['actions']:
                    require(action['prior'] is None or action['prior'] in OUTCOMES,'invalid prior')
                    require(type(action['provisional_alarm']) is bool,'invalid provisional flag')
                    probe=action['prior'] is None or action['provisional_alarm']
                    physical['actions']+=1;physical['probe_actions']+=probe
                    physical['probe_harm']+=probe and action['outcome']=='HURT'
                    physical['released_actions']+=action['provisional_alarm']
                    physical['released_harm']+=action['provisional_alarm'] and action['outcome']=='HURT'
                    action_rows.append((rr['round'],ep['world'],action['ident'],action['sig'],
                                        action['act'],action['hand'],action['outcome']))
                require(sum(row['outcome']=='HURT' for row in r['actions'])<=r['harm'],'action harm mismatch')
        require(action_rows==[tuple(row) for row in x['observations'][a]],'actions/consequences mismatch')
    require(physical['probe_harm']<=st['harm'],'probe harm exceeds physical harm')
    return dict(st,physical=physical,by_kind_details=by_kind_details,trust_by_author=trust_by_author,
        score=x['score'],solved=x['solved'],altered_postcards=altered,
        exposure_queries=exposure,affected_memory_responses=affected,global_asks=global_asks,abstentions=abstentions)


def verify(root):
    root=Path(root);pre=b.check_frozen(root);phase=pre['phase'];threshold=pre['threshold'];done=json.loads((root/'completed.json').read_text())
    require(done['preflight_sha256']==b.sha(root/'preflight.json') and done['exam_run'] is False,'completion scope')
    expected={b.name(job):job for job in b.jobs(phase,threshold)}
    require(set(done['jobs'])==set(expected) and done['jobs_count']==len(expected),'registered receipts required')
    require({p.name for p in (root/'runs').iterdir()}==set(expected),'extra or missing job')
    rows={};expected_rounds={}
    for name,job in expected.items():
        path=root/'runs'/name;require(b.sha(path)==done['jobs'][name],'job receipt changed')
        receipt=json.loads(path.read_text());require(receipt['status']=='ok' and receipt['job']==list(job),'failed or mismatched job')
        rows[name]=validate_job(job,receipt['result'])
        for rr in receipt['result']['rounds']:
            rel=f'rounds/{name.removesuffix(".json")}/r{rr["round"]:02d}.json';expected_rounds[rel]=done['round_files'].get(rel)
            require((root/rel).is_file() and b.sha(root/rel)==expected_rounds[rel],'durable round receipt changed/missing')
            require(json.loads((root/rel).read_text())==b.round_record(receipt['result'],rr['round']),'round receipt differs from job')
    require(set(expected_rounds)==set(done['round_files'])==
        {str(p.relative_to(root)) for p in (root/'rounds').rglob('*.json')},'round receipt manifest mismatch')
    b.check_frozen(root)
    return {'audit_green':True,'phase':phase,'exam_run':False,'jobs':len(expected),
        'scientific_exam_verdict':None,'rows':rows,'completed_sha256':b.sha(root/'completed.json'),
        'preflight_sha256':b.sha(root/'preflight.json')}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    print(b.canonical(verify(parser.parse_args().root)))
