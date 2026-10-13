#!/usr/bin/env python3
"""Plot an independently audited export. This program does NOT authenticate receipts.

Every planned primary arm/issue/seed must appear, including errors and exhaustion.
Synthetic fixtures always bear a watermark. No SWE-bench measurements ship here.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'ECHO-5.1/docs/swebench/SWE-RESULTS.schema.json'
ARMS = ('S', 'I2', 'F', 'E')
COLORS = ('#6b7280', '#a07853', '#357e9d', '#175c44')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def load_registration(contract_path, sample_path):
    contract_bytes = contract_path.read_bytes(); sample_bytes = sample_path.read_bytes()
    contract = json.loads(contract_bytes); sample = json.loads(sample_bytes)
    if hashlib.sha256(sample_bytes).hexdigest() != contract['dataset']['sample_sha256']:
        raise ValueError('Sample bytes differ from the registered contract')
    return dict(primary_instances=[r['instance_id'] for r in sample['primary']],
        primary_seeds=contract['model']['seeds'],
        contract_sha256=hashlib.sha256(contract_bytes).hexdigest(),
        repos={r['instance_id']:r['repo'] for r in sample['primary']},
        memory_chains=[dict(chain_id=c['chain_id'],repo=c['donor']['repo'],
            target_instances=[r['instance_id'] for r in c['targets']]) for c in sample['memory_chains']])


def validate(data, *, registration=None):
    import jsonschema
    try:
        canonical(data)  # Reject NaN/Infinity even where JSON Schema allows numbers.
        jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(data)
    except (jsonschema.ValidationError, ValueError, TypeError) as exc:
        raise ValueError(f'Invalid analysis export: {exc}') from exc
    for r in data['primary'] + data['memory']:
        if (r['status'] == 'resolved') != r['echo_verified_resolved']:
            raise ValueError('Status and verified resolution disagree')
        if r['echo_verified_resolved'] and r['official_raw_resolved'] is not True:
            raise ValueError('Verified resolution requires the official raw result')
        if (r['official_raw_resolved'] is True and not r['echo_verified_resolved']
                and not r['validity_reason']):
            raise ValueError('Official/verified discrepancy requires an explicit reason')
    if data['data_kind'] == 'measured':
        if registration is None:
            raise ValueError('Measured export requires the independent registered contract/sample')
        if (set(data['primary_instances']) != set(registration['primary_instances'])
                or set(data['primary_seeds']) != set(registration['primary_seeds'])
                or data['contract_sha256'] != registration['contract_sha256']):
            raise ValueError('Export differs from the registered primary schedule/contract')
        expected_chains = {c['chain_id']:(c['repo'],c['target_instances']) for c in registration['memory_chains']}
        actual_chains = {c['chain_id']:(c['repo'],c['target_instances']) for c in data['memory_chains']}
        if actual_chains != expected_chains:
            raise ValueError('Export differs from the registered memory schedule')
        if any(registration['repos'].get(r['instance_id']) != r['repo'] for r in data['primary']):
            raise ValueError('Export repository differs from registered task')
    expected = {(i, s, a) for i in data['primary_instances']
                for s in data['primary_seeds'] for a in ARMS}
    actual = [(r['instance_id'],r['seed'],r['arm']) for r in data['primary']]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('Primary matrix incomplete or duplicated; do not omit failures')
    repos = defaultdict(set)
    for r in data['primary']:
        repos[r['instance_id']].add(r['repo'])
        if not 0 <= r['regressions_blocked'] <= r['public_regressions'] <= r['proposed_patches']:
            raise ValueError('Invalid patch-level regression denominator')
    if any(len(v) != 1 for v in repos.values()):
        raise ValueError('Repository mismatch in paired arms')
    if data['data_kind'] == 'measured' and data['audit_report_sha256'] is None:
        raise ValueError('Measured exports must reference the separate custody audit')
    chains = {r['chain_id']:r for r in data['memory_chains']}
    if len(chains) != len(data['memory_chains']): raise ValueError('Duplicate memory chain')
    targets = [i for c in chains.values() for i in c['target_instances']]
    if len(set(targets)) != len(targets) or set(targets) & set(data['primary_instances']):
        raise ValueError('Memory targets must be distinct and disjoint from the primary panel')
    expected_memory = {(c['chain_id'], i, p, arm)
        for c in chains.values() for p,i in enumerate(c['target_instances'],1)
        for arm in ('empty','shared')}
    actual_memory = [(r['chain_id'],r['instance_id'],r['position'],r['condition'])
                     for r in data['memory']]
    if len(set(actual_memory)) != len(actual_memory) or set(actual_memory) != expected_memory:
        raise ValueError('Memory matrix incomplete or duplicated')
    return data


def wilson(success, n):
    """Descriptive binomial interval only; does not adjust repository clustering."""
    if n == 0: return None
    z = 1.959963984540054
    p = success / n; denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return [max(0,center-half), min(1,center+half)]


def summarize(data, *, registration=None):
    validate(data, registration=registration)
    arms = {}
    for arm in ARMS:
        rows = [r for r in data['primary'] if r['arm'] == arm]
        n = len(rows); successes = sum(r['status'] == 'resolved' for r in rows)
        tokens = sum(r['tokens'] for r in rows); wall = sum(r['wall_seconds'] for r in rows)
        proposed = sum(r['proposed_patches'] for r in rows)
        regressions = sum(r['public_regressions'] for r in rows)
        blocked = sum(r['regressions_blocked'] for r in rows)
        arms[arm] = dict(n=n, resolved=successes, rate=successes/n,
            official_raw_resolved=sum(r['official_raw_resolved'] is True for r in rows),
            official_raw_missing=sum(r['official_raw_resolved'] is None for r in rows),
            discrepancies=sum(r['official_raw_resolved'] is True and not r['echo_verified_resolved'] for r in rows),
            wilson95=wilson(successes,n), tokens=tokens, mean_tokens=tokens/n,
            mean_wall_seconds=wall/n, tokens_per_resolved=tokens/successes if successes else None,
            wall_seconds_per_resolved=wall/successes if successes else None,
            proposed_patches=proposed, regressive_patches=regressions, blocked=blocked,
            blocked_fraction=blocked/regressions if regressions else None)
    pairs = {}
    by_key = {(r['instance_id'],r['seed'],r['arm']):r for r in data['primary']}
    for control in ('S','I2','F'):
        wins = losses = ties = 0
        for i in data['primary_instances']:
            for s in data['primary_seeds']:
                e = by_key[i,s,'E']['status'] == 'resolved'
                c = by_key[i,s,control]['status'] == 'resolved'
                wins += e and not c; losses += c and not e; ties += e == c
        pairs[control] = dict(wins=wins,losses=losses,ties=ties)
    memory = None
    if data['memory_chains']:
        empty = [r for r in data['memory'] if r['condition'] == 'empty']
        shared = [r for r in data['memory'] if r['condition'] == 'shared']
        donor_tokens = sum(c['donor_tokens'] for c in data['memory_chains'])
        donor_wall = sum(c['donor_wall_seconds'] for c in data['memory_chains'])
        memory = dict(empty_tokens=sum(r['tokens'] for r in empty),
            shared_marginal_tokens=sum(r['tokens'] for r in shared),
            shared_full_tokens=donor_tokens+sum(r['tokens'] for r in shared),
            empty_wall_seconds=sum(r['wall_seconds'] for r in empty),
            shared_marginal_wall_seconds=sum(r['wall_seconds'] for r in shared),
            shared_full_wall_seconds=donor_wall+sum(r['wall_seconds'] for r in shared),
            donor_tokens=donor_tokens, donor_wall_seconds=donor_wall,
            empty_resolved=sum(r['status']=='resolved' for r in empty),
            shared_resolved=sum(r['status']=='resolved' for r in shared), n=len(empty))
    not_started = sum(r['status'] == 'not_started' for r in data['primary'] + data['memory'])
    return dict(data_kind=data['data_kind'], arms=arms, paired_E=pairs, memory=memory,
                not_started=not_started, complete=not_started == 0,
                custody_verified_by_plotter=False,
                uncertainty='Wilson descriptive only; clustered issues/repeated seeds are not independent')


def render(data, output, *, registration=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    result = summarize(data, registration=registration)
    output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
        'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,
        'figure.dpi':110,'savefig.dpi':300})

    def save(fig, name, footnote):
        if not result['complete']:
            fig.text(.5,.985,f'CAMPAÑA INCOMPLETA: {result["not_started"]} episodios sin iniciar',
                     ha='center',va='top',fontsize=9,color='#a13030')
        fig.text(.5,.035,footnote,ha='center',fontsize=8,color='#444444')
        if data['data_kind'] == 'synthetic':
            fig.text(.5,.55,'DATOS SINTÉTICOS · NO ES UN RESULTADO',ha='center',
                va='center',rotation=20,fontsize=16,color='#bd3939',alpha=.35)
        fig.tight_layout(rect=(0,.10,1,.98))
        fig.savefig(output/(name+'.png'))
        fig.savefig(output/(name+'.pdf'), metadata={'Creator':'ECHO RepoWorld analysis',
                    'CreationDate':None,'ModDate':None})
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8,4.8))
    heights = [100*result['arms'][a]['rate'] for a in ARMS]
    errors = [[max(0,100*(result['arms'][a]['rate']-result['arms'][a]['wilson95'][0])) for a in ARMS],
              [max(0,100*(result['arms'][a]['wilson95'][1]-result['arms'][a]['rate'])) for a in ARMS]]
    official = [100*result['arms'][a]['official_raw_resolved']/result['arms'][a]['n'] for a in ARMS]
    ax.bar([i-.18 for i in range(4)],official,width=.34,color=COLORS,alpha=.35,label='Oficial bruto (harness fijado)')
    ax.bar([i+.18 for i in range(4)],heights,width=.34,color=COLORS,yerr=errors,capsize=4,label='Verificado por ECHO')
    ax.set_xticks(range(4),ARMS);ax.legend(fontsize=8,loc='upper left')
    for i,a in enumerate(ARMS):
        v=result['arms'][a]; ax.text(i+.18,heights[i]+3,f'{v["resolved"]}/{v["n"]}',ha='center')
    ax.set(ylim=(0,125),ylabel='Episodios resueltos (%)',title='Resolución sobre todos los episodios previstos')
    save(fig,'01_resolution','IC Wilson descriptivo; no ajustado por repositorio. Errores y agotamientos cuentan como no resueltos.')

    fig, axes = plt.subplots(1,2,figsize=(10,4.8))
    for j,key in enumerate(('regressive_patches','blocked_fraction')):
        vals=[result['arms'][a][key] for a in ARMS]
        axes[j].bar(ARMS,[0 if v is None else v*(100 if j else 1) for v in vals],color=COLORS)
        for i,a in enumerate(ARMS):
            v=result['arms'][a]
            label=f'{v["regressive_patches"]}/{v["proposed_patches"]}' if not j else (
                f'{v["blocked"]}/{v["regressive_patches"]}' if vals[i] is not None else 'N/D')
            axes[j].text(i,0,label,ha='center',va='bottom',fontsize=9)
    axes[0].set(title='Parches con regresión pública',ylabel='Número de parches (únicos por estado)')
    axes[1].set(title='Regresiones públicas bloqueadas',ylabel='Bloqueados / regresivos (%)',ylim=(0,110))
    save(fig,'02_regressions','Misma suite pública de diagnóstico en todos los brazos. Un rollback no demuestra por sí solo una ventaja causal.')

    fig, axes = plt.subplots(1,2,figsize=(10,4.8))
    for ax,metric,label in zip(axes,('mean_tokens','mean_wall_seconds'),
                             ('Tokens por issue','Segundos por issue')):
        for a,color in zip(ARMS,COLORS):
            v=result['arms'][a]; ax.scatter(v[metric],100*v['rate'],s=70,c=color,label=a)
        ax.legend(fontsize=8)
        ax.set(xlabel=label,ylabel='Resolución verificada (%)',ylim=(-5,110))
    save(fig,'03_cost_resolution','Incluye coste de fallos. Tokens, tiempo local y consumo de GPU se contabilizan por separado.')

    fig, axes = plt.subplots(1,2,figsize=(10,4.8))
    if not data['memory']:
        for ax in axes:
            ax.axis('off'); ax.text(.5,.5,'Transferencia no medida',ha='center',va='center',transform=ax.transAxes)
    else:
        for ax,field,label in zip(axes,('tokens','wall_seconds'),('Tokens acumulados','Segundos acumulados')):
            max_rank=max(r['position'] for r in data['memory'])
            for condition,color in [('empty',COLORS[0]),('shared',COLORS[3])]:
                totals=[]; full=[]
                for rank in range(1,max_rank+1):
                    costs=[]; full_costs=[]
                    for c in data['memory_chains']:
                        if len(c['target_instances']) < rank: continue
                        cost=sum(r[field] for r in data['memory'] if r['chain_id']==c['chain_id']
                                 and r['condition']==condition and r['position']<=rank)
                        costs.append(cost); full_costs.append(cost+c['donor_'+field])
                    totals.append(statistics.mean(costs)); full.append(statistics.mean(full_costs))
                ax.plot(range(1,max_rank+1),totals,'o-',color=color,
                        label='Memoria vacía' if condition=='empty' else 'Compartida: receptores')
                if condition == 'shared': ax.plot(range(1,max_rank+1),full,'--',color=color,label='Compartida + adquisición')
            ax.set(xlabel='Número de issue receptor en la cadena',ylabel=label)
            ax.set_xticks(range(1,max_rank+1));ax.legend(fontsize=8)
    note = 'Media por cadena; adquisición incluye publicación y donantes fallidos.'
    if result['memory']:
        v=result['memory']
        note += f' Resueltos: vacío {v["empty_resolved"]}/{v["n"]}, compartida {v["shared_resolved"]}/{v["n"]}.'
    save(fig,'04_memory',note)
    result['input_sha256']=hashlib.sha256(canonical(data)).hexdigest()
    result['contract_sha256']=data['contract_sha256']
    result['audit_report_sha256']=data['audit_report_sha256']
    result['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['python']=platform.python_version();result['matplotlib']=matplotlib.__version__
    (output/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--contract',type=Path,help='Independent registered contract, required for measured data')
    parser.add_argument('--sample',type=Path,help='Independent registered sample, required for measured data')
    args=parser.parse_args()
    try:
        if bool(args.contract) != bool(args.sample):
            raise ValueError('Supply both --contract and --sample')
        registered=load_registration(args.contract,args.sample) if args.contract else None
        result=render(json.loads(args.results.read_text()),args.output,registration=registered)
    except (ValueError,OSError,KeyError) as exc: parser.exit(2,str(exc)+'\n')
    print(f'4 PDF + 4 PNG; data_kind={result["data_kind"]}; custody verified separately')
