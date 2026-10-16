"""Descriptive plots from an already audited export; no HMAC authentication."""
from pathlib import Path
G = Path(__file__).resolve().parent

def render(report, analysis):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap, BoundaryNorm
    from matplotlib.patches import Patch
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'figure.dpi':110,
        'pdf.fonttype':42, 'savefig.dpi':300, 'axes.spines.top':False,
        'axes.spines.right':False})
    out = G / 'figures'; out.mkdir(exist_ok=True)
    rows = report['rows']; arms = ['S', 'I2', 'F', 'E', 'E_no_guard']
    colors = ['#34798f', '#8094a2', '#c58b39', '#38715c', '#986c91']

    def save(fig, name):
        fig.savefig(out/(name+'.png'), bbox_inches='tight')
        fig.savefig(out/(name+'.pdf'), bbox_inches='tight',
            metadata={'CreationDate':None, 'ModDate':None})
        plt.close(fig)

    # Redraw the memory chart with its observed intervention explicitly labelled.
    # This changes presentation only; the frozen plotter and its export stay intact.
    fig, axes = plt.subplots(1,2,figsize=(11,5))
    chains=analysis['memory_chains']
    for ax,field,ylabel in zip(axes,('tokens','wall_seconds'),('Tokens acumulados','Segundos acumulados')):
        for condition,color in [('empty','#6b7280'),('shared','#175c44')]:
            costs=[]; full=[]
            for rank in (1,2,3):
                per_chain=[sum(r[field] for r in analysis['memory'] if r['chain_id']==c['chain_id']
                    and r['condition']==condition and r['position']<=rank) for c in chains]
                costs.append(sum(per_chain)/len(chains))
                full.append(sum(v+c['donor_'+field] for v,c in zip(per_chain,chains))/len(chains))
            ax.plot((1,2,3),costs,'o-',color=color,label='Condición vacía' if condition=='empty' else 'Compartida (sin lecciones)')
            if condition=='shared':ax.plot((1,2,3),full,'--',color=color,label='Compartida + donantes')
        ax.set(xlabel='Posición del receptor en la cadena',ylabel=ylabel,xticks=(1,2,3))
        ax.legend(fontsize=8)
    retrieved=sum(v['lessons_retrieved'] for k,v in report['summary'].items() if k.startswith('memory/'))
    published=sum(v['lessons_published'] for v in report['summary'].values())
    fig.suptitle(f'Memoria: {published} lecciones publicadas, {retrieved} recuperadas',fontsize=12)
    fig.text(.5,.02,'Media de dos cadenas; resueltos 0/6 en ambas condiciones. La diferencia de coste no acredita transferencia.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.07,1,.93));save(fig,'04_memory')

    indexed = {(r['instance_id'],r['arm']):r for r in rows
               if r['phase'] in ('primary','guard_ablation')}
    instances = analysis['primary_instances']
    states = {'not_started':0, 'unresolved':1, 'resolved':2}
    matrix = [[states[indexed[i,a]['evaluation_status']] for a in arms] for i in instances]
    cmap = ListedColormap(['#e7c87e','#bc7171','#5b9279'])
    fig, ax = plt.subplots(figsize=(9,10))
    ax.imshow(matrix, cmap=cmap, norm=BoundaryNorm([-.5,.5,1.5,2.5],3), aspect='auto')
    ax.set_xticks(range(len(arms)), arms)
    ax.set_yticks(range(len(instances)), instances, fontsize=8)
    ax.set_title('Cobertura y resultado oficial por issue\nPrincipal: 17/24 ejecutados por brazo; ablación: 24/24', pad=14)
    ax.legend(handles=[Patch(color=cmap(k),label=label) for k,label in enumerate(
        ['No iniciado','No resuelto','Resuelto y verificado'])],loc='upper center',
        bbox_to_anchor=(.5,-.05),ncol=3,fontsize=8)
    fig.tight_layout(); save(fig,'05_coverage')

    fig, axes = plt.subplots(1,2,figsize=(10,4.5))
    for idx,arm in enumerate(arms[:4]):
        v=report['summary']['primary/'+arm]
        axes[0].bar(arm,v['mean_tokens_executed'],color=colors[idx])
        axes[0].text(idx,v['mean_tokens_executed'],f"{v['mean_tokens_executed']:,.0f}",ha='center',va='bottom',fontsize=8)
        axes[1].bar(arm,100*v['executed_rate'],color=colors[idx])
        axes[1].text(idx,100*v['executed_rate']+2,f"{v['resolved']}/{v['executed']}",ha='center',fontsize=9)
    axes[0].set(title='Tokens medios por episodio ejecutado',ylabel='Tokens de entrada + salida',ylim=(0,29000))
    rate_ceiling=max(25,max(100*report['summary']['primary/'+a]['executed_rate'] for a in arms[:4])*1.4+8)
    axes[1].set(title='Resolución del subconjunto ejecutado',ylabel='Resuelto y verificado (%)',ylim=(0,rate_ceiling))
    fig.suptitle('Los mismos 17 issues en S / I2 / F / E',fontsize=12)
    fig.text(.5,.015,'Descriptivo: corte por tiempo y agrupación por repositorio. Menos tokens no implica más soluciones.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,.94)); save(fig,'06_executed_subset')

    phases = ['calibration','primary','guard_ablation','memory_donor','memory']
    times = [sum(w['seconds'] for w in report['worker_runs'] if w['phase']==phase)/3600 for phase in phases]
    fig, ax = plt.subplots(figsize=(8,4.7))
    ax.bar(['Calibración','Principal','Ablación','Donantes','Receptores'], times, color='#527e90')
    for i,t in enumerate(times):ax.text(i,t,f'{t:.2f} h',ha='center',va='bottom',fontsize=9)
    ax.set(ylabel='Horas de sesión del worker',title='Tiempo registrado en Kaggle por fase')
    ax.set_ylim(0,max(times)*1.2)
    fig.text(.5,.02,'Incluye arranque y recuperación de red; no es energía ni tiempo de inferencia puro. Evaluación final local.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,1)); save(fig,'07_worker_time')
