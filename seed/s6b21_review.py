"""B21-A arithmetic review uses the frozen independent B20 arithmetic checker."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

from seed.s6b20_review import review as check, read, sha


def review(root,manifest):
    # Different implementation from the researcher: stdlib, no solver imports.
    m=read(manifest);fixture=read(manifest.parent/'baseline.json')
    result=read(root/'micro.json');logical=0;inputs_checked=0
    for name,kind,seed in m['configuration']['cells']:
        cells=[x for x in result['cells'] if x['arm']==name]
        assert cells and [x['slot'] for x in cells]==list(range(1,len(cells)+1))
        assert len(cells)==18 or cells[-1]['verdict']=='A_ONLY_PASS'
        assert all(x['verdict']!='A_ONLY_PASS' for x in cells[:-1])
        base=read(root/('micro-'+name)/'measurements/baseline.json');history=[]
        for index,cell in enumerate(cells):
            saved=read(root/'steps'/name/f'{index:03d}.json');event=saved['event'];req=saved['request']
            data=gzip.decompress((root/'investigator-inputs'/(saved['input_sha256']+'.json.gz')).read_bytes())
            assert hashlib.sha256(data).hexdigest()==saved['input_sha256']
            assert json.loads(data)==dict(policy=fixture['policy'],base=base,own_history=history,
                accepted_history=fixture['history'],kind=kind,index=index,seed=seed)
            assert sha(req)==saved['request_sha256']
            assert event['usage']==dict(input_tokens=0,output_tokens=0,model_calls=0)
            assert event['base_sha256']==sha(fixture['policy'])
            if 'proposal' in event:
                assert event['proposal_sha256']==sha(event['proposal'])
                assert event['policy_sha256']==sha(event['candidate'])
                assert event['development']['origin']=='DEVELOPMENT_A'
                assert event['consumption_sha256']==sha(event['development']['candidate_consumers'])
                measured=read(root/('micro-'+name)/'measurements/candidate'/f'{index:03d}.json')
                behavior=[{k:row[k] for k in ('version','seed','rep','actions','frames','automatic_reset_indices')}
                          for row in measured['rows']]
                assert event['behavior_sha256']==sha(behavior)
                assert event['trajectory_sha256']==measured['trace_digest']
                if kind=='balanced' and index<10:
                    expected=m['configuration']['agendas'][str(seed)][index]
                    assert req['schedule']==expected
                    assert event['proposal']['patches'][0]['set']['HOLD']==expected['value']
            history.append(event);inputs_checked+=1
        logical+=len(cells)
    assert logical==len(result['cells'])<=126
    receipt=check(root,manifest)
    receipt.update(logical_attempts=logical,exact_input_records=inputs_checked,
                   model_calls=0,scope='B21-A: search and retention only')
    (root/'arithmetic-review.json').write_text(json.dumps(receipt,sort_keys=True)+'\n')
    return receipt


if __name__=='__main__':review(Path(sys.argv[1]),Path(sys.argv[2]))
