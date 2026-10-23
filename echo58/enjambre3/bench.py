"""C3 orchestration derived from C2; imported physics/private learning are unchanged."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import platform
import random
import traceback

from ..crece.artifacts import publish,save_new
from ..enjambre.coop import KINDS,CoopWorld,language,play_together
from ..enjambre.team import RM,as_counts,read
from ..enjambre2.memory import Private
from ..enjambre2.transport import ATTACKS,Attacker,Board,require
from ..enjambre2.bench import canonical,digest,sha,round_record,sources as c2_sources
from .memory import Reader
from .agent import Agent

CONTROLS=('ingenuo','prudente','por_autor','sin_global')
CANDIDATES=('v3_n1','v3_n2','v3_n3')
BASES={'development':13_100_000,'validation':13_500_000}
MACROS={'development':tuple(range(1,4)),'validation':tuple(range(1,11))}

def arms(phase,threshold=None):
    require(phase in BASES,'registered phase required')
    if phase=='development':return CONTROLS+CANDIDATES
    require(threshold in (1,2,3),'selected threshold required')
    return CONTROLS+(f'v3_n{threshold}',f'sin_alarma_n{threshold}',f'sin_liberacion_n{threshold}')

def jobs(phase,threshold=None):
    return [(a,t,m) for m in MACROS[phase] for a in arms(phase,threshold) for t in ATTACKS]

def mission(m,phase):
    require(phase in BASES and type(m) is int and m in MACROS[phase],'registered fresh mission only')
    b=BASES[phase]+1000*m;kinds=[k for k in KINDS for _ in range(2)]
    random.Random(b).shuffle(kinds)
    return [{'kind':k,'seed':b+i} for i,k in enumerate(kinds)]

def run_team(arm,attack,m,phase,threshold=None,sink=None):
    require((arm,attack,m) in jobs(phase,threshold),'unregistered development job')
    worlds=mission(m,phase);ids=language(BASES[phase]+1000*m+999);bad_author=m%4
    solved=[None]*8;failed_eps=[0]*8;needs=[False]*8
    mine=[Private(a) for a in range(4)];notes=[{} for _ in range(4)];at=[None]*4
    board=Board();attacker=None if arm=='honesto' else Attacker(bad_author,attack)
    rounds=[];note_receipts=[];fresh=iter(range(8));round_id=0
    st={'episodes':0,'failed':0,'harm':0,'postcards':0,'notes_cards':0,'helps':0,'asked':0,'held':0,
        'answers':dict.fromkeys(('here','private','notes','global'),0),
        'by_kind':{k:{'harm':0,'episodes':0} for k in KINDS}}

    def assign(a):
        for w in fresh:at[a]=w;return
        at[a]=None;open_=[w for w in range(8) if solved[w] is None]
        if not open_:return
        w=min(open_,key=lambda x:(not needs[x],-failed_eps[x],x));at[a]=w;st['helps']+=1
        notes[a]={};got={};raw_notes=[]
        for b in range(4):
            if b==a:continue
            for raw in mine[b].notes_cards(b,w):
                layer,_,key,o,n,total=read(raw)
                got.setdefault((RM,key) if layer==RM else key,[]).append((o,n,total))
                raw_notes.append(raw.hex());st['notes_cards']+=1
        for key,entries in got.items():notes[a][key]=as_counts(entries)
        note_receipts.append({'after_round':round_id,'agent':a,'world':w,'postcards':raw_notes})

    for a in range(4):assign(a)
    for round_id in range(1,31):
        if all(s is not None for s in solved):break
        claims,provenance=board.snapshot()
        for p in mine:p.set_snapshot(claims,round_id)
        visible=claims;visible_ids=provenance
        if arm=='oraculo':
            visible={k:{a:c for a,c in v.items() if a!=bad_author} for k,v in claims.items()}
            visible_ids={k:{a:i for a,i in v.items() if a!=bad_author} for k,v in provenance.items()}
        rr={'round':round_id,'assignments':list(at),'postcards_before':len(board.records),'episodes':[]}
        played=[]
        for w in range(8):
            team=[a for a in range(4) if at[a]==w]
            if not team:continue
            cw=CoopWorld(worlds[w]['kind'],worlds[w]['seed'],len(team),ids)
            agents=[];readers=[]
            for slot,a in enumerate(team):
                p=mine[a];p.world=w
                rd=Reader(arm,p,visible,visible_ids,board.records,notes[a],world=w,round=round_id)
                readers.append(rd);agents.append(Agent(source=rd,learn=p,me=slot,private=p))
            results=play_together(cw,agents)
            require(all(type(x) is dict for x in results),'physical agent thread failed')
            win=cw.solved_by is not None
            if win and solved[w] is None:solved[w]=round_id
            needs[w]=needs[w] or cw.needs_help
            for a,rd,x in zip(team,readers,results):
                for k in st['answers']:st['answers'][k]+=rd.by_source[k]
                st['episodes']+=1;st['harm']+=x['harm'];st['asked']+=x['asked'];st['held']+=x['held']
                st['by_kind'][worlds[w]['kind']]['harm']+=x['harm']
                st['by_kind'][worlds[w]['kind']]['episodes']+=1
                if not win:st['failed']+=1;failed_eps[w]+=1
                rr['episodes'].append({'agent':a,'world':w,'win':win,'result':x,'answers':rd.by_source,
                    'global_asks':rd.global_asks,'abstentions':rd.abstentions,'queries':rd.queries_receipt()})
                played.append(a)
        for a in played:
            p=mine[a];cards=p.l2_cards(a)+p.l1_cards(a)+p.remote_cards(a)
            pairs=attacker.transform(cards,round_id) if attacker is not None and a==bad_author else [(raw,raw) for raw in cards]
            for original,sent in pairs:board.post(sent,author=a,round=round_id,original=original)
            st['postcards']+=len(cards)
        for a in range(4):
            if at[a] is None or solved[at[a]] is not None:assign(a)
        rr['postcards_after']=len(board.records);rr['next_assignments']=list(at);rounds.append(rr)
        if sink is not None:
            sink(round_record({'rounds':rounds,'publications':board.records,'notes':note_receipts,
                'observations':[p.observations for p in mine],'remote_observations':[p.remote_observations for p in mine],
                'trust':[{'events':p.trust.events} for p in mine]},round_id))
    solved_round=[s if s is not None else 31 for s in solved]
    return {'arm':arm,'attack':attack,'macro':m,'phase':phase,'threshold':threshold,'exam_run':False,'bad_author':bad_author,
        'worlds':worlds,'language_ids':list(ids.values()),'score':sum(solved_round),'solved_round':solved_round,
        'solved':sum(s is not None for s in solved),'destroyed':sum(p.destroyed for p in mine)+board.destroyed,
        'card_bytes':sorted({len(raw) for raw in board.log}),'rounds':rounds,'notes':note_receipts,
        'publications':board.records,'observations':[p.observations for p in mine],
        'remote_observations':[p.remote_observations for p in mine],
        'trust':[{'good':p.trust.good,'bad':p.trust.bad,'events':p.trust.events,'verified':len(p.trust.verified)} for p in mine],**st}


def sources():
    here=Path(__file__).resolve().parent;project=here.parents[1]
    docs=project/'ECHO-5.8/docs'
    return list(dict.fromkeys(list(sorted(here.glob('*.py')))+c2_sources()+[
        project/'tests/test_echo58_enjambre3.py',docs/'ENJAMBRE3-DESIGN-20261023.md',
        docs/'ENJAMBRE3-PLAN-20261023.md']))

def prepare(root,phase,threshold=None,selection=None):
    root=Path(root)
    if root.exists():raise FileExistsError(root)
    if phase=='validation':
        require(selection is not None,'development selection required')
        row=json.loads(Path(selection).read_text())
        require(row['selected']==f'v3_n{threshold}' and row['selection_rule']=='violations,harm,score,n_min', 'selection mismatch')
    root.mkdir(parents=True,exist_ok=False);frozen=[]
    for i,path in enumerate(sources()+([Path(selection).resolve()] if selection else [])):
        name=f'sources/{i:02d}-{path.name}';publish(root/name,path.read_bytes())
        frozen.append({'path':str(path.resolve()),'archive':name,'sha256':sha(path)})
    p={'version':1,'phase':phase,'threshold':threshold,'exam_run':False,'automatic_exam':False,
       'python':platform.python_version(),'implementation':platform.python_implementation(),
       'jobs':[list(x) for x in jobs(phase,threshold)],
       'missions':{str(m):mission(m,phase) for m in MACROS[phase]},'sources':frozen,
       'selection_sha256':sha(selection) if selection else None}
    save_new(root/'preflight.json',p);return p

def check_frozen(root):
    root=Path(root);p=json.loads((root/'preflight.json').read_text());phase=p['phase'];n=p['threshold']
    require(p['jobs']==[list(x) for x in jobs(phase,n)] and p['exam_run'] is False and p['automatic_exam'] is False,'scope/schedule changed')
    require(p['missions']=={str(m):mission(m,phase) for m in MACROS[phase]},'missions changed')
    for row in p['sources']:
        require(sha(row['path'])==row['sha256'] and sha(root/row['archive'])==row['sha256'],'frozen source changed: '+row['path'])
    return p

def name(job):
    a,t,m=job;return f'{a}-{t}-m{m}.json'

def worker(job,journals,phase,n):
    def sink(record):
        r=record['round']['round']
        save_new(Path(journals)/name(job).removesuffix('.json')/f'r{r:02d}.json',record)
        print(canonical({'phase':phase,'job':job,'round':r,'episodes':len(record['round']['episodes']),
            'harm':sum(ep['result']['harm'] for ep in record['round']['episodes'])}),flush=True)
    try:return {'status':'ok','job':list(job),'result':run_team(*job,phase,n,sink=sink)}
    except Exception:return {'status':'error','job':list(job),'error':traceback.format_exc()}

def run(root,workers=3):
    root=Path(root);p=check_frozen(root);phase=p['phase'];n=p['threshold']
    require(type(workers) is int and 1<=workers<=4,'one to four CPU workers')
    if (root/'runs').exists():raise FileExistsError(root/'runs')
    (root/'runs').mkdir();receipts={}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(worker,job,str(root/'rounds'),phase,n):job for job in jobs(phase,n)}
        for future in as_completed(futures):
            job=futures[future];row=future.result();path=root/'runs'/name(job)
            save_new(path,row);receipts[path.name]=sha(path)
            print(canonical({'phase':phase,'job':job,'status':row['status'],
                'score':row.get('result',{}).get('score'),'harm':row.get('result',{}).get('harm')}),flush=True)
    check_frozen(root)
    save_new(root/'completed.json',{'jobs':receipts,'jobs_count':len(receipts),
        'preflight_sha256':sha(root/'preflight.json'),'exam_run':False,
        'round_files':{str(path.relative_to(root)):sha(path) for path in sorted((root/'rounds').rglob('*.json'))}})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','run'))
    p.add_argument('root',type=Path);p.add_argument('--phase',choices=tuple(BASES),default='development')
    p.add_argument('--threshold',type=int);p.add_argument('--selection',type=Path);p.add_argument('--workers',type=int,default=3)
    a=p.parse_args()
    if a.command=='prepare':print(canonical(prepare(a.root,a.phase,a.threshold,a.selection)))
    else:run(a.root,a.workers)
