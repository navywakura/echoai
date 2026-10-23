"""Prospective 12-world storage integration; no historical exam execution."""
import argparse
import hashlib
import json
from pathlib import Path

from ..memx.memory import Memory
from .memory import load_memory
from .play import episode,audit_episode


def save(path,data):
    with path.open('x') as f:json.dump(data,f,sort_keys=True,indent=2);f.write('\n')


def run(root,archive,original):
    root.mkdir(parents=True,exist_ok=False)
    summary=[];manifest={}
    for family in ('LavaGapS7','DoorKey6','DynObs6'):
        for seed in (202610230,202610231):
            for regime in ('A1','A2'):
                group={}
                for arm in ('original','wsp','empty'):
                    memory=Memory.load(original) if arm=='original' else load_memory(archive) if arm=='wsp' else None
                    receipt=episode(memory,family,seed,regime);group[arm]=receipt
                    name=f'{family}-{seed}-{regime}-{arm}.json';save(root/name,receipt)
                    manifest[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
                same=group['original']['trace']==group['wsp']['trace'] and group['original']['result']==group['wsp']['result']
                assert same and group['wsp']['memory_unchanged'],'storage changed behavior'
                summary.append(dict(family=family,seed=seed,regime=regime,same=same,
                    outcomes={a:r['result'] for a,r in group.items()},queries=group['wsp']['source_queries'],hits=group['wsp']['source_hits'],
                    differs_from_empty=group['wsp']['trace']!=group['empty']['trace']))
                print(json.dumps(summary[-1],sort_keys=True),flush=True)
    for label,path in [('archive',archive),('original_memory',original)]:
        manifest[label]={'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest['sources']={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),Path(__file__).with_name('play.py')]}
    save(root/'manifest.json',manifest)
    result=dict(worlds=12,episodes=36,identical=sum(x['same'] for x in summary),
        source_queries=sum(x['queries'] for x in summary),source_hits=sum(x['hits'] for x in summary),
        differs_from_empty=sum(x['differs_from_empty'] for x in summary),summary=summary)
    assert result['source_queries']>0 and result['source_hits']>0,'memory not exercised'
    save(root/'results.json',result)


def audit(root):
    if not __debug__:raise RuntimeError('Offline audit requires Python without -O; assertions must remain enabled')
    m=json.loads((root/'manifest.json').read_text())
    for name in ('archive','original_memory'):
        assert hashlib.sha256(Path(m[name]['path']).read_bytes()).hexdigest()==m[name]['sha256']
    for name,digest in m['sources'].items():
        current=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        if current!=digest:
            # The measured policy is unchanged. Preserve the runner at run time
            # and explicitly bind this strengthened audit as a later amendment.
            change=json.loads((root/'audit-amendment.json').read_text())
            assert name==str(Path(__file__).resolve()) and change['original_sha256']==digest
            assert current==change['audit_sha256']
            assert hashlib.sha256((root/'integration-at-run.py').read_bytes()).hexdigest()==digest
            assert hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()==change['manifest_sha256']
    n=hits=queries=same=changed=0;summary=[]
    for family in ('LavaGapS7','DoorKey6','DynObs6'):
        for seed in (202610230,202610231):
            for regime in ('A1','A2'):
                rs={}
                for arm in ('original','wsp','empty'):
                    name=f'{family}-{seed}-{regime}-{arm}.json';raw=(root/name).read_bytes()
                    assert hashlib.sha256(raw).hexdigest()==m[name]
                    r=json.loads(raw);rs[arm]=r
                    memory=Memory.load(m['original_memory']['path']) if arm=='original' else load_memory(m['archive']['path']) if arm=='wsp' else None
                    audit_episode(r,memory);n+=1
                    if arm=='wsp':
                        assert memory.queries==r['source_queries'] and memory.hits==r['source_hits']
                        hits+=memory.hits;queries+=memory.queries
                assert rs['original']['trace']==rs['wsp']['trace'] and rs['original']['result']==rs['wsp']['result']
                same+=1;changed+=rs['empty']['trace']!=rs['wsp']['trace']
                summary.append(dict(family=family,seed=seed,regime=regime,same=True,
                    outcomes={a:r['result'] for a,r in rs.items()},queries=rs['wsp']['source_queries'],hits=rs['wsp']['source_hits'],
                    differs_from_empty=rs['wsp']['trace']!=rs['empty']['trace']))
    result=json.loads((root/'results.json').read_text())
    assert result==dict(worlds=12,episodes=n,identical=same,source_queries=queries,
                        source_hits=hits,differs_from_empty=changed,summary=summary),'complete integration result differs'
    return dict(valid=True,episodes=n,worlds_identical=same,source_hits=hits,source_queries=queries,changed_from_empty=changed,
                scope='policy replay from actual MiniGrid observations; no physics replay or new performance claim')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('run','audit'))
    p.add_argument('root',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--original',type=Path);a=p.parse_args()
    if a.command=='run':
        if not a.archive or not a.original:p.error('--archive and --original required')
        run(a.root,a.archive,a.original)
    else:print(json.dumps(audit(a.root),sort_keys=True))
