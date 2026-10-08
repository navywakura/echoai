"""Rebuild figures and a closure receipt from measured integration artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed.integration_campaign import read,save,file_sha
from seed.arc_memory import sha


def main():
    root=REPO/'lab/seed';out=root/'integration-closure-20261002';out.mkdir(exist_ok=True)
    development=read(root/'integration-v2-20261002/primary-summary.json')
    followup=read(root/'integration-followup-20261002/run/primary-summary.json')
    memory=read(root/'integration-transfer-20261002/primary-summary.json')
    audits={name:read(root/name/'audit-summary.json') for name in
      ('integration-dev1-20261002','integration-dev64-20261002','integration-v2-20261002',
       'integration-followup-20261002/run','integration-transfer-20261002')}
    validation=REPO/'lab/localdev/arc-integration-closure-r1-20261002'
    if read(validation/'result.json')['status']!='PASSED':raise RuntimeError('engineering validation not closed')
    tests=read(validation/'checks/01-selected/result.json')
    before=read(out/'protected-before.json')
    changed=[f for f,h in before.items() if file_sha(REPO/f)!=h]
    if changed:raise RuntimeError('protected sources changed: '+str(changed))
    receipts={name:{'sha256':file_sha(root/name/'audit-summary.json'),
                    'replays_identical':record['replays_identical']} for name,record in audits.items()}
    primary=followup['totals']['all']['v2']
    # No promotion is inferred from equal aggregate counts alone.
    confirm=bool(primary['gains_vs_v1_no_views']) and not primary['losses_vs_v1_no_views']
    def contribution(with_arm,without_arm):
        values={}
        for arm in (with_arm,without_arm):
            rows=[read(p) for p in (root/'integration-followup-20261002/run/primary'/arm).glob('*.json')]
            values[arm]={r['task'] for r in rows if r['correct']}
        return {'gains':sorted(values[with_arm]-values[without_arm]),
                'losses':sorted(values[without_arm]-values[with_arm]),
                'accuracy_advantage':bool(values[with_arm]-values[without_arm]) and not values[without_arm]-values[with_arm]}
    effects={'memory':contribution('v2','v2_no_memory'),
             'refinement':contribution('v2','v2_no_refinement'),
             'views':contribution('v2_views','v2'),
             'consistency':contribution('v2','v2_no_consistency'),
             'guide_500k':contribution('v2','v2_no_guide')}
    result={'scope':'public development and constructed-family transfer, not an official ARC score',
      'protected_sources':len(before),'protected_changes':changed,'audits':receipts,
      'tests_passed':sum(r['outcome']=='passed' for r in tests['details']['cases']),
      'synthetic_memory_gates':memory['gates'],'followup_candidate_promotion':confirm,
      'followup_component_effects':effects,'S6':'DEFERRED_BY_OWNER','echo45_release_ready':False,
      'source_manifest_before':before,
      'development':development['totals'],'followup':followup['totals']}
    save(out/'result.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(13,4.8))
    colors=['#52525b','#7c3aed','#a78bfa']
    for axis,label,summary,population,denominator in ((axes[0],'Desarrollo ARC-1',development,'arc1',64),(axes[1],'Seguimiento ARC-1/2',followup,'all',128)):
        arms=['v1_no_views','v2','v2_no_refinement']
        counts=[summary['totals'][population][a]['solved'] for a in arms]
        bars=axis.bar(['V1','V2','Sin refinar'],counts,color=colors)
        axis.bar_label(bars,labels=[str(n)+'/'+str(denominator) for n in counts],padding=3)
        axis.set_ylim(0,max(6,max(counts)+2));axis.set_title(label);axis.set_ylabel('Aciertos exactos')
    arms=['reset','memory','remove_formative']
    work=[memory['totals']['all'][a]['primitive_calls']/1000 for a in arms]
    bars=axes[2].bar(['Sin memoria','Memoria','Retirada\nformativa'],work,color=colors)
    axes[2].bar_label(bars,fmt='%.1f',padding=3);axes[2].set_ylim(0,max(work)*1.22)
    axes[2].set_title('Memoria · 64 casos sintéticos');axes[2].set_ylabel('Miles de aplicaciones primitivas')
    fig.suptitle('ECHO-4.5 · Integración y límites observados',fontsize=15)
    fig.text(.5,.01,'Presupuesto común de programas. CPU y adquisición se informan por separado. Estas cifras no son puntuaciones ARC oficiales.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.045,1,.93))
    fig.savefig(out/'integration-results.png',dpi=160);fig.savefig(out/'integration-results.svg')
    print(json.dumps({k:result[k] for k in ('tests_passed','protected_sources','followup_candidate_promotion','followup_component_effects')}))


if __name__=='__main__':main()
