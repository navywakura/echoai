"""Extract only the fixed public observation fields; never run a game."""
import copy
import hashlib
import json
from pathlib import Path

from .codec import FEEDBACK,dumps,loads,require,validate_record

GAMES={'bp35':'calibration','s5i5':'evaluation','sp80':'evaluation'}


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def normalise(source,index):
    require(type(source) is dict and type(source.get('data')) is dict,'public data object required')
    data=source['data'];feedback={}
    for key in FEEDBACK:
        if key not in data:continue
        value=data[key]
        if key=='action_input' and value is not None:
            require(type(value) is dict,'public action object required')
            value={k:copy.deepcopy(value[k]) for k in ('id','data') if k in value}
        feedback[key]=copy.deepcopy(value)
    require('game_id' in data and 'frame' in data,'public game/frame missing')
    out={'version':1,'packet':[2,14,4,8,0,0,0,0,0,0,0,0,0,0,0,index%256],
         'game_id':data['game_id'],'index':index,'feedback':feedback,'frame':copy.deepcopy(data['frame'])}
    validate_record(out)
    return out


def build(source_root,output,*,count=64):
    source_root=Path(source_root).resolve();output=Path(output)
    if output.exists():raise FileExistsError(output)
    require(type(count) is int and 1<=count<=64,'bounded corpus prefix required')
    manifest={'version':1,'records_per_game':count,'games':{},
        'scope':'Historical public third-party recordings; codec evaluation, no game execution.',
        'excluded_fields':['timestamp','guid','action_input.reasoning']}
    encoded={}
    for game,split in GAMES.items():
        source=source_root/f'{game}-recording.jsonl';before=file_hash(source);rows=[]
        with source.open(encoding='utf-8') as f:
            for index,line in enumerate(f):
                if index==count:break
                rows.append(normalise(loads(line),index))
        require(len(rows)==count,'recording shorter than fixed prefix')
        require(len({r['game_id'] for r in rows})==1,'game changed inside recording')
        require(file_hash(source)==before,'source changed during corpus extraction')
        name=f'{game}.jsonl';content=('\n'.join(dumps(r) for r in rows)+'\n').encode()
        encoded[name]=content
        manifest['games'][game]={'split':split,'source':str(source),'source_sha256':before,
            'file':name,'sha256':hashlib.sha256(content).hexdigest(),'records':len(rows),
            'selected_source_lines':[1,count],'game_id':rows[0]['game_id'],
            'record_sha256':[hashlib.sha256(dumps(r).encode()).hexdigest() for r in rows]}
    output.mkdir(parents=True,exist_ok=False)
    for name,content in encoded.items():
        with (output/name).open('xb') as f:f.write(content)
    with (output/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
    return manifest
