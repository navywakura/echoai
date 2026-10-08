"""Independent result arithmetic and private V3 closure/figures; no new solver runs."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
from seed.relational_tasks import task,correct,FAMILIES
from seed.relational_campaign import integrity,save
from seed.program_guide_campaign import integrity as guide_integrity


def read(p):return json.loads(p.read_text())


def main():
    r=ROOT/'lab/seed/relational-v3-20261003';g=ROOT/'lab/seed/program-guide-20261003'
    profile=integrity(r);guide_integrity(g)
    ra=read(r/'audit.json');ga=read(g/'audit.json')
    if not ra['valid'] or not ga['valid']:raise ValueError('both replays required')
    rows=read(r/'primary/rows.json');summary=read(r/'primary/summary.json');guide=read(g/'primary/summary.json')
    index={(a['seed'],a['family'],a['arm']):a for a in rows}
    expected={(s,f,a) for s in profile['confirmation_seeds'] for f in FAMILIES for a in profile['arms']}
    if len(rows)!=len(expected) or set(index)!=expected:raise ValueError('missing/duplicate experimental cell')
    for row in rows:
        if correct(row['result'],task(row['family'],row['seed']))!=row['correct']:
            raise ValueError('stored correctness differs from independent judge')
        m=row['result']['metrics']
        if m['work']>profile['config']['budget'] or sum(m['counts'].values())!=m['work']:
            raise ValueError('budget accounting differs')
    totals={a:sum(row['correct'] for row in rows if row['arm']==a) for a in profile['arms']}
    for arm,n in totals.items():
        if n!=summary['totals']['all'][arm]['solved']:raise ValueError('totals differ')
    def no_loss(a,b):return all(not r['correct'] or index[s,f,a]['correct'] for (s,f,c),r in index.items() if c==b)
    schedule={a:sum(r['result']['metrics']['work'] for r in rows if r['arm']==a and r['family'] in ('rotate','compose'))
              for a in ('new_policy','new_fixed','search_first')}
    reduction=1-schedule['new_policy']/min(schedule['new_fixed'],schedule['search_first'])
    wd=read(r/'primary/withdrawals.json')
    withdrawal={a:sum(row['work'] for row in wd if row['arm']==a) for a in ('intact','formative','control')}
    cons=read(r/'primary/consistency.json')
    wrong=lambda enabled:sum(a['committed'] and not a['correct'] for a in cons if a['family']=='ambiguous' and a['enabled']==enabled)
    checks={
       'REL':totals['new_policy']>totals['old_fixed'] and no_loss('new_policy','old_fixed'),
       'MEM':reduction>=.10 and no_loss('new_policy','new_fixed') and no_loss('new_policy','search_first')
          and withdrawal['formative']>withdrawal['control'] and all(a['correct'] for a in wd),
       'SYN':summary['totals']['compose']['no_memory']['solved']>summary['totals']['compose']['no_refinement']['solved']
          and no_loss('no_memory','no_refinement'),
       'VIEW':totals['views']>totals['no_memory'] and no_loss('views','no_memory'),
       'CONS':wrong(True)==0 and wrong(False)>0 and all(a['correct'] for a in cons if a['family']=='control')}
    if checks!=summary['gates']:raise ValueError('module gates differ')
    gt={a:{'correct':0,'wrong':0,'queries':0} for a in guide['totals']};deltas=[]
    for seed in range(49100,49108):
        data=read(g/'primary'/(str(seed)+'.json'));before={a:v['correct'] for a,v in gt.items()}
        if len(data['rows'])!=2048:raise ValueError('guide query count differs')
        for row in data['rows']:
            gt[row['arm']]['correct']+=row['correct'];gt[row['arm']]['queries']+=1
            gt[row['arm']]['wrong']+=row['committed'] and not row['correct']
        deltas.append(((gt['500000']['correct']-before['500000'])-(gt['65536']['correct']-before['65536']))/512)
    checks['GUIDE']=all(x>0 for x in deltas) and sum(deltas)/8>=.05 and all(v['wrong']==0 for v in gt.values())
    checks['GUIDE']&=gt['500000']['correct']-gt['none']['correct']>=.05*4096 and gt['exhaustive']['correct']==4096
    if checks['GUIDE']!=guide['GUIDE']:raise ValueError('guide gate differs')
    original=read(ROOT/'lab/seed/relational-v3-work-20261003/original-sources.json')
    changed=[f for f,h in original.items() if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h]
    if changed:raise ValueError('original sources changed: '+repr(changed))
    # CLI acquired and resumed in separate processes.
    workroot=ROOT/'lab/seed/relational-v3-work-20261003'
    cli=read(workroot/'cli-prediction.json')['result'];resumed=read(workroot/'cli-resumed.json')['result']
    private=read(workroot/'cli-task.json')
    if not correct(cli,private) or not correct(resumed,private):raise ValueError('installed candidate smoke failed')
    closure={'valid':True,'module_gates':checks,'all_module_gates_green':all(checks.values()),
        'S6_green':False,'release_ready':False,'ARC_improvement_certified':False,
        'rows_independently_recounted':len(rows),'full_replays':ra['full_solves'],
        'policy_fit_replays':ra['fit_episodes'],'guide_queries_replayed_per_arm':ga['queries_per_arm'],
        'guide_seeds':ga['seeds'],'original_sources_unchanged':len(original),
        'policy_schedule_reduction':reduction,'all_suite_policy_reduction':summary['adaptive_work_reduction'],
        'cli_acquire_and_resume_valid':True,'candidate_sha256':read(r/'primary/candidate.json')['sha256']}
    save(r/'closure.json',closure)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    purple='#7252b8';gray='#777777';light='#c6b8e1'
    ax=axes[0,0]
    keys=('old_fixed','new_policy','integrated')
    ax.bar(['DSL anterior','Relacional + memoria','Integrado + vistas'],[totals[k] for k in keys],color=[gray,light,purple])
    ax.set_title('Resolución exacta · 192 puzzles sintéticos');ax.set_ylim(0,215);ax.set_ylabel('Tareas resueltas')
    for i,k in enumerate(keys):ax.text(i,totals[k]+3,str(totals[k]),ha='center')
    ax=axes[0,1];keys=('new_fixed','new_policy')
    ax.bar(['Mejor orden fijo','Orden aprendido'],[schedule[k] for k in keys],color=[gray,purple])
    ax.set_title(f'Planificación · 64 tareas · ahorro {100*reduction:.2f}%');ax.set_ylabel('Unidades lógicas de trabajo')
    ax=axes[1,0];keys=('none','65536','500000','exhaustive')
    values=[100*gt[k]['correct']/gt[k]['queries'] for k in keys]
    ax.bar(['Sin guía\n1 programa','65k\n1 programa','500k\n1 programa','Sin guía\n32 programas'],values,color=[gray,light,purple,gray])
    ax.set_ylim(0,115);ax.set_title('Recuperación de programas · 4096 consultas');ax.set_ylabel('Exactitud (%)')
    for i,v in enumerate(values):ax.text(i,v+2,f'{v:.2f}%',ha='center')
    ax=axes[1,1]
    ax.bar(['Primera solución','Consistencia'],[wrong(False),wrong(True)],color=[gray,purple])
    ax.set_ylim(0,35);ax.set_title('32 puzzles ambiguos · errores comprometidos');ax.set_ylabel('Respuestas erróneas emitidas')
    ax.text(.5,29,'Consistencia: 32 abstenciones\nControl inequívoco: ambos 32/32',ha='center')
    fig.suptitle('ECHO-4.5 V3 · bancos de módulos; sin nueva certificación ARC',fontsize=14)
    for ext in ('png','svg'):fig.savefig(r/('module-results.'+ext),dpi=170)
    plt.close(fig)
    matrix=[[summary['totals'][f][a]['solved'] for a in ('old_fixed','no_refinement','no_memory','views','integrated')] for f in FAMILIES]
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    ax.imshow(matrix,vmin=0,vmax=32,cmap='Purples',aspect='auto')
    ax.set_xticks(range(5),['DSL anterior','Sin refinamiento','Sin memoria','Con vistas','Integrado'])
    ax.set_yticks(range(6),['Rotación','Color por rol','Copia por rol','Composición','Regla girada','Composición girada'])
    for i,row in enumerate(matrix):
        for j,v in enumerate(row):ax.text(j,i,f'{v}/32',ha='center',va='center',color='white' if v>16 else 'black')
    ax.set_title('Exactitud por familia sintética · presupuesto común 500.000 unidades')
    for ext in ('png','svg'):fig.savefig(r/('family-results.'+ext),dpi=170)
    print(json.dumps(closure,sort_keys=True))


if __name__=='__main__':main()
