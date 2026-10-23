"""C v2 development only. Frozen C v1 physics, private learning and action policy."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import platform
import random
import traceback

from ..crece.artifacts import publish,save_new
from ..enjambre.cagent import CAgent
from ..enjambre.coop import KINDS,CoopWorld,language,play_together
from ..enjambre.team import RM,as_counts,read
from .memory import Private,Reader
from .transport import ATTACKS,Attacker,Board,require

ARMS=('honesto','ingenuo','por_autor','prudente','sin_global','oraculo')
MACROS=(1,2,3)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mission(m):
    require(type(m) is int and m in MACROS,'development macros only')
    b=12_100_000+1000*m;kinds=[k for k in KINDS for _ in range(2)]
    random.Random(b).shuffle(kinds)
    return [{'kind':k,'seed':b+i} for i,k in enumerate(kinds)]


def jobs():
    return [(a,t,m) for m in MACROS for a in ARMS for t in (('none',) if a=='honesto' else ATTACKS)]


def round_record(result,r):
    return {'round':next(rr for rr in result['rounds'] if rr['round']==r),
        'publications':[p for p in result['publications'] if p['round']==r],
        'observations':[[row for row in rows if row[0]==r] for rows in result['observations']],
        'remote_observations':[[row for row in rows if row[0]==r] for rows in result['remote_observations']],
        'notes':[n for n in result['notes'] if n['after_round']==r],
        'trust_events':[[event for event in t['events'] if event['round']==r] for t in result['trust']]}


def run_team(arm,attack,m,sink=None):
    require((arm,attack,m) in jobs(),'unregistered development job')
    worlds=mission(m);ids=language(12_100_000+1000*m+999);bad_author=m%4
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
                readers.append(rd);agents.append(CAgent(source=rd,learn=p,me=slot,private=p))
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
    return {'arm':arm,'attack':attack,'macro':m,'phase':'development','exam_run':False,'bad_author':bad_author,
        'worlds':worlds,'language_ids':list(ids.values()),'score':sum(solved_round),'solved_round':solved_round,
        'solved':sum(s is not None for s in solved),'destroyed':sum(p.destroyed for p in mine)+board.destroyed,
        'card_bytes':sorted({len(raw) for raw in board.log}),'rounds':rounds,'notes':note_receipts,
        'publications':board.records,'observations':[p.observations for p in mine],
        'remote_observations':[p.remote_observations for p in mine],
        'trust':[{'good':p.trust.good,'bad':p.trust.bad,'events':p.trust.events,'verified':len(p.trust.verified)} for p in mine],**st}


def sources():
    here=Path(__file__).resolve().parent;project=here.parents[1]
    paths=list(sorted(here.glob('*.py')))+[project/'tests/test_echo58_enjambre2.py',here.parent/'crece/artifacts.py']
    for folder,names in {'enjambre':('team','coop','cagent'),'memx':('agent','memory','world'),
                         'acumula':('agent','config'),'b3':('policy',)}.items():
        paths.extend(here.parent/folder/(name+'.py') for name in names)
    paths.extend([project.parent/'navi10_wsp.py',project.parent/'navi10_qn.py'])
    paths.extend(here.parent/folder/'__init__.py' for folder in ('enjambre','memx','acumula','b3','crece'))
    paths.extend([here.parent/'__init__.py',project/'__init__.py'])
    return paths


def prepare(root,contract):
    root=Path(root);contract=Path(contract).resolve()
    if root.exists():raise FileExistsError(root)
    root.mkdir(parents=True,exist_ok=False);frozen=[]
    for i,path in enumerate(sources()+[contract]):
        name=f'sources/{i:02d}-{path.name}';publish(root/name,path.read_bytes())
        frozen.append({'path':str(path),'archive':name,'sha256':sha(path)})
    preflight={'version':1,'phase':'development','exam_run':False,'automatic_exam':False,
        'python':platform.python_version(),'implementation':platform.python_implementation(),
        'jobs':[list(x) for x in jobs()],'missions':{str(m):mission(m) for m in MACROS},
        'languages':{str(m):list(language(12_100_000+1000*m+999).values()) for m in MACROS},'sources':frozen}
    save_new(root/'preflight.json',preflight);return preflight


def check_frozen(root):
    root=Path(root);p=json.loads((root/'preflight.json').read_text())
    require(p['jobs']==[list(x) for x in jobs()] and p['exam_run'] is False and p['automatic_exam'] is False,'schedule/scope altered')
    require(p['missions']=={str(m):mission(m) for m in MACROS},'missions changed')
    require(p['languages']=={str(m):list(language(12_100_000+1000*m+999).values()) for m in MACROS},'languages changed')
    for x in p['sources']:
        require(sha(x['path'])==x['sha256'] and sha(root/x['archive'])==x['sha256'],'frozen input changed')
    return p


def name(job):a,t,m=job;return f'{a}-{t}-m{m}.json'


def worker(job,journals):
    def sink(record):
        r=record['round']['round']
        save_new(Path(journals)/name(job).removesuffix('.json')/f'r{r:02d}.json',record)
        print(canonical({'job':job,'round':r,'episodes':len(record['round']['episodes']),
            'harm':sum(ep['result']['harm'] for ep in record['round']['episodes'])}),flush=True)
    try:return {'status':'ok','job':list(job),'result':run_team(*job,sink=sink)}
    except Exception:return {'status':'error','job':list(job),'error':traceback.format_exc()}


def run(root,workers=4):
    root=Path(root);check_frozen(root)
    require(type(workers) is int and 1<=workers<=4,'one to four CPU workers')
    if (root/'runs').exists():raise FileExistsError(root/'runs')
    (root/'runs').mkdir();receipts={}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(worker,job,str(root/'rounds')):job for job in jobs()}
        for future in as_completed(futures):
            job=futures[future];row=future.result();path=root/'runs'/name(job)
            save_new(path,row);receipts[path.name]=sha(path)
            print(canonical({'job':job,'status':row['status'],
                'score':row.get('result',{}).get('score'),'harm':row.get('result',{}).get('harm')}),flush=True)
    check_frozen(root)
    save_new(root/'completed.json',{'jobs':receipts,'jobs_count':len(receipts),
        'preflight_sha256':sha(root/'preflight.json'),'exam_run':False,
        'round_files':{str(p.relative_to(root)):sha(p) for p in sorted((root/'rounds').rglob('*.json'))}})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','run'))
    parser.add_argument('root',type=Path);parser.add_argument('--contract',type=Path);parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root,args.contract)
    else:run(args.root,args.workers)
