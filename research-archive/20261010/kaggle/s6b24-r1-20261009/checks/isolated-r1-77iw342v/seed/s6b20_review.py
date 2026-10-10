"""Independent arithmetic review: no solver, controller or game imports."""
import hashlib
import json
import math
from pathlib import Path
import sys


def read(path):return json.loads(path.read_text())
def sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def validate(measured):
    rows=measured['rows']
    assert measured['trace_digest']==sha(rows)
    assert measured['levels']==sum(r['levels_completed'] for r in rows)
    assert measured['score']==sum(r['score'] for r in rows)
    for row in rows:
        assert math.isfinite(row['score'])
        assert row['levels_completed']==len(row['actions_per_level'])
        assert len(row['frames'])==len(row['actions'])+1
        assert len(row['actions'])-len(row['automatic_reset_indices'])<=row['budget']
        numerator=0;denominator=sum(range(1,len(row['baseline'])+1))
        for i,reference in enumerate(row['baseline'],1):
            used=row['actions_per_level'][i-1] if i<=len(row['actions_per_level']) else 0
            numerator+=i*(min(reference/used,1)**2 if used else 0)
        assert math.isclose(row['score'],100*numerator/denominator,abs_tol=1e-10,rel_tol=0)


def diff(base,after):
    assert [[r[k] for k in ('version','seed','rep','budget')] for r in base['rows']]==[[r[k] for k in ('version','seed','rep','budget')] for r in after['rows']]
    return dict(gain=after['levels']-base['levels'],score_delta=after['score']-base['score'],
        loss_indices=[i for i,(b,a) in enumerate(zip(base['rows'],after['rows'],strict=True)) if a['levels_completed']<b['levels_completed'] or a['score']+1e-10<b['score']])


def review(root,manifest_path):
    manifest=read(manifest_path);repo=Path(__file__).resolve().parents[1]
    for name,h in manifest['sources'].items():assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==h,name
    for name,h in manifest['inputs'].items():assert hashlib.sha256((manifest_path.parent/name).read_bytes()).hexdigest()==h,name
    count=0;measurements=0
    for namespace in root.iterdir():
        if not namespace.is_dir():continue
        for p in (namespace/'cache').glob('*/*.json'):
            saved=read(p);assert saved['key']==p.stem and saved['digest']==sha(saved['record']);count+=1
        for p in (namespace/'measurements').rglob('*.json'):
            m=read(p);validate(m);measurements+=1
            if 'audit' in namespace.name or p.name=='replay.json':continue
            assert m==read(p.with_suffix('')/'replay.json')
            audit=namespace.name.replace('micro-','audit-',1) if namespace.name.startswith('micro-') else namespace.name+'-audit'
            assert m==read(root/audit/'measurements'/p.relative_to(namespace/'measurements'))
    budget=read(root/'budget.json');assert count==budget['scheduled_games']<=budget['cap']
    assert sum(x['count'] for x in budget['reservations'])==count
    if manifest['stage']=='capacity':
        result=read(root/'capacity.json');audit=read(root/'capacity-audit.json')
        assert audit['valid'] and audit['capacity_sha256']==sha(result)
        plan=read(manifest_path.parent/'capacity-plan.json');assert result['plan_sha256']==sha(plan)
        base=read(root/'capacity/measurements/baseline.json')
        for cell in result['results']:
            d=diff(base,read(root/'capacity/measurements'/(cell['name']+'.json')))
            assert cell['diff']==d and cell['passed']==(d['gain']>=2 and not d['loss_indices'])
        for name,d in result['broad'].items():
            assert d==diff(read(root/'capacity/measurements/full-baseline.json'),read(root/'capacity/measurements'/('full-'+name+'.json')))
        assert set(result['qualified'])=={n for n,d in result['broad'].items() if d['gain']>=2 and not d['loss_indices']}
        assert result['capacity_passed']==bool(result['qualified'])
    else:
        result=read(root/'micro.json');audit=read(root/'micro-audit.json')
        assert audit['valid'] and audit['micro_sha256']==sha(result)
        first={}
        for cell in result['cells']:
            step=read(root/'steps'/cell['arm']/('%03d.json'%(cell['slot']-1)))
            assert step['profile_sha256']==sha(manifest)
            if cell['levels'] is None:continue
            folder=root/('micro-'+cell['arm'])/'measurements'
            d=diff(read(folder/'baseline.json'),read(folder/'candidate'/('%03d.json'%(cell['slot']-1))))
            assert cell['diff']==d and step['event']['A']==d
            passed=d['gain']>=2 and not d['loss_indices']
            assert (cell['verdict']=='A_ONLY_PASS')==passed
            if passed:
                assert cell['arm'] not in first
                first[cell['arm']]=dict(slot=cell['slot'],policy=step['event']['candidate'])
        assert first==result['winners']
        for phase in ('qualification','retention'):
            if not (root/(phase+'.json')).exists():continue
            q=read(root/(phase+'.json'));a=read(root/(phase+'-audit.json'))
            assert a['valid'] and a[phase+'_sha256']==sha(q)
            base=read(root/phase/'measurements/baseline.json')
            for n,d in q['scores'].items():assert d==diff(base,read(root/phase/'measurements'/(n+'.json')))
            assert set(q['winners'])=={n for n,d in q['scores'].items() if not d['loss_indices'] and (phase=='retention' or d['gain']>=2)}
        assert not read(root/'closed.json')['s6_green']
    receipt=dict(valid=True,cache_records=count,measurements=measurements,profile_sha256=sha(manifest),exam_opened=False)
    (root/'arithmetic-review.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
    print(json.dumps(receipt));return receipt


if __name__=='__main__':review(Path(sys.argv[1]),Path(sys.argv[2]))
