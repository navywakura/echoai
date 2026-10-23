"""Frozen local codec benchmark. No model inference or environment execution."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import statistics
import time

from ..crece.artifacts import publish, save_new
from . import codec as c, corpus, metrics

TOKENIZER_SHA='c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539'
SOURCE_ROOT=Path('/home/user/github-restructure/worktrees/echoai-pcworld1/ECHO-5.5/artifacts/replays')
FORMATS=('wsp',)+c.FORMATS
COMMON=('Version 1 lossless public observation. Packet: src,rel,dst,time,E[6],flags,domain,generator,style,slot,seq; '
        'E signed -100..100, other bytes 0..255, no authority conferred. '
        'game_id and zero-based index identify stream; seq=index modulo 256. '
        'Feedback keys in order: state,levels_completed,win_levels,full_reset,available_actions,action_input. '
        'action_input preserves id/data presence; null,false,zero and absent differ. '
        'Feedback array starts with presence bitmask then present values in key order. '
        'Geometry object has mode,shapes,payload: shapes are [height,width] per layer, flattened layer/row order. '
        'raw payload is colors; rle payload [color,count] pairs; delta payload sorted [index,color] replacements, '
        'base is SHA256 of previous frame serialized as compact sorted-key ASCII JSON. '
        'Delta needs same game/shape,next index,no full_reset=true. First/reset/shape change sends full frame. '
        'Limits: 64 layers,128x128 each,integer colors 0..255,4MiB message. No other fields; reject invalid input. ')
WSP_LEGEND=COMMON+'W1|sixteen comma-separated packet integers|JSON [game_id,index,feedback_array]|JSON geometry. Parse complete JSON before delimiter.'
LEGENDS={
    'wsp':WSP_LEGEND,
    'named':COMMON+'Compact JSON object with keys version,packet,game_id,index,feedback,geometry. Feedback is named object.',
    'positional':COMMON+'Compact JSON array [1,packet,game_id,index,feedback_array,geometry].',
    'wrapped':WSP_LEGEND+' Transport is one JSON string containing the entire W1 message; JSON unescape then use W1 parser.'}


def load_tokenizer(path):
    c.require(corpus.file_hash(path)==TOKENIZER_SHA,'tokenizer hash mismatch')
    import tokenizers
    c.require(tokenizers.__version__=='0.23.3','tokenizer version mismatch')
    return tokenizers.Tokenizer.from_file(str(path))


def count(tokenizer,text):
    return len(tokenizer.encode(text,add_special_tokens=False).ids)


def best_encoding(record,fmt,tokenizer,base):
    candidates=[]
    for mode in c.MODES:
        try:
            text=c.encode(record,mode=mode,base=base) if fmt=='wsp' else c.encode_json(record,fmt,mode=mode,base=base)
        except ValueError as exc:
            if str(exc)!='message exceeds limit':raise
            candidates.append((None,mode,None));continue
        candidates.append((count(tokenizer,text),mode,text))
    valid=[(index,row) for index,row in enumerate(candidates) if row[0] is not None]
    c.require(bool(valid),'no geometry mode fits message limit')
    chosen=min(valid,key=lambda x:(x[1][0],x[0]))[1]
    g=c.geometry(record,chosen[1],base)
    return {'message':chosen[2],'mode':g['mode'],'tokens':chosen[0],
            'bytes':len(chosen[2].encode()),'candidate_tokens':dict((m,t) for t,m,_ in candidates)}


def source_files():
    package=Path(__file__).resolve().parent
    project=package.parents[1]
    rxos=project.parent
    return (list(sorted(package.glob('*.py')))+[project/'tests/test_echo58_wspstudy.py',
        package.parent/'crece/artifacts.py',rxos/'navi10_wsp.py',rxos/'navi10_qn.py'])


def prepare(root,source_root,tokenizer,contract,*,fixture=False):
    root=Path(root);source_root=Path(source_root).resolve();contract=Path(contract).resolve()
    if root.exists():raise FileExistsError(root)
    c.require(type(fixture) is bool,'fixture flag')
    if not fixture:
        c.require(source_root==SOURCE_ROOT,'unregistered public source root')
        c.require(contract.name=='WSP-R1-R2-DESIGN.md','unregistered contract')
    load_tokenizer(tokenizer)
    root.mkdir(parents=True,exist_ok=False)
    manifest=corpus.build(source_root,root/'corpus')
    sources=[]
    for index,path in enumerate(source_files()+[contract]):
        name=f'sources/{index:02d}-{path.name}'
        data=path.read_bytes();publish(root/name,data)
        sources.append({'path':str(path),'archive':name,'sha256':hashlib.sha256(data).hexdigest()})
    preflight={'version':1,'fixture':fixture,'exam_run':False,'python':platform.python_version(),
        'tokenizers':'0.23.3','tokenizer':str(Path(tokenizer).resolve()),'tokenizer_sha256':TOKENIZER_SHA,
        'sources':sources,'corpus_manifest_sha256':corpus.file_hash(root/'corpus/manifest.json'),
        'legends':LEGENDS,'mode_order':list(c.MODES),'formats':list(FORMATS),
        'repetitions':5,'records_per_game':64,'games':manifest['games']}
    save_new(root/'preflight.json',preflight)
    return preflight


def check_frozen(root):
    root=Path(root);p=c.loads((root/'preflight.json').read_text())
    c.require(p['legends']==LEGENDS and p['formats']==list(FORMATS) and p['mode_order']==list(c.MODES),'protocol changed')
    for row in p['sources']:
        c.require(corpus.file_hash(row['path'])==row['sha256'],'live source changed')
        c.require(corpus.file_hash(root/row['archive'])==row['sha256'],'archived source changed')
    c.require(corpus.file_hash(root/'corpus/manifest.json')==p['corpus_manifest_sha256'],'manifest changed')
    for row in p['games'].values():
        c.require(corpus.file_hash(row['source'])==row['source_sha256'],'public recording changed')
        c.require(corpus.file_hash(root/'corpus'/row['file'])==row['sha256'],'corpus changed')
    return p


def describe(values):
    values=sorted(values)
    return {'total':sum(values),'median':statistics.median(values),'p95':values[(95*len(values)+99)//100-1],
            'max':max(values)}


def run(root):
    root=Path(root);p=check_frozen(root)
    if (root/'results.json').exists():raise FileExistsError(root/'results.json')
    tokenizer=load_tokenizer(p['tokenizer']);games={};files={}
    for game in corpus.GAMES:
        records=[c.loads(s) for s in (root/'corpus'/p['games'][game]['file']).read_text().splitlines()]
        game_result={}
        for fmt in FORMATS:
            stream=c.StreamDecoder(records[0]['game_id']);rows=[];enc=[];dec=[];base=None
            for record in records:
                trials=[]
                for _ in range(5):
                    start=time.process_time_ns();row=best_encoding(record,fmt,tokenizer,base)
                    enc.append(time.process_time_ns()-start);trials.append(row)
                c.require(all(r==trials[0] for r in trials),'nondeterministic encoder')
                for _ in range(5):
                    start=time.process_time_ns()
                    restored=c.decode(row['message'],base=base) if fmt=='wsp' else c.decode_json(row['message'],fmt,base=base)
                    dec.append(time.process_time_ns()-start)
                    c.require(restored==record,'roundtrip mismatch')
                c.require(stream.consume(row['message'],fmt)==record,'stream mismatch')
                row.update(index=record['index'],record_sha256=c.digest(record));rows.append(row);base=record
            name=f'messages/{game}/{fmt}.jsonl'
            publish(root/name,('\n'.join(c.dumps(r) for r in rows)+'\n').encode())
            files[name]=corpus.file_hash(root/name)
            lc=count(tokenizer,LEGENDS[fmt]);tokens=[r['tokens'] for r in rows]
            game_result[fmt]={'tokens':tokens,'legend_tokens':lc,
                'tokens_descriptive':describe(tokens),'tokens_total_with_legend':sum(tokens)+lc,
                'tokens_median_with_legend':statistics.median(tokens)+lc/64,
                'first_message_with_legend':tokens[0]+lc,
                'bytes_descriptive':describe([r['bytes'] for r in rows]),
                'bytes_total_with_legend':sum(r['bytes'] for r in rows)+len(LEGENDS[fmt].encode()),
                'encode_cpu_ns':describe(enc),'decode_cpu_ns':describe(dec),
                'encode_cpu_samples_ns':enc,'decode_cpu_samples_ns':dec,
                'mode_counts':{m:sum(r['mode']==m for r in rows) for m in c.MODES}}
            print(f'{game} {fmt}: {sum(tokens)+lc} tokens; 64 exact roundtrips',flush=True)
        games[game]=game_result
    gate_input={g:{'wsp':{k:games[g]['wsp'][k] for k in ('tokens','legend_tokens')},
        'json':{f:{k:games[g][f][k] for k in ('tokens','legend_tokens')} for f in c.FORMATS}}
        for g,split in corpus.GAMES.items() if split=='evaluation'}
    check_frozen(root)
    result={'version':1,'fixture':p['fixture'],'exam_run':False,'phase':'W R1/R2',
        'records':192,'messages':768,'roundtrips_exact':768,'parse_failures':0,
        'r1_compatibility_green':True,'games':games,'gate_input':gate_input,
        'verdict':metrics.verdict(gate_input),'message_files':files,
        'preflight_sha256':corpus.file_hash(root/'preflight.json')}
    save_new(root/'results.json',result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','run'))
    parser.add_argument('root',type=Path);parser.add_argument('--tokenizer',type=Path)
    parser.add_argument('--contract',type=Path);args=parser.parse_args()
    if args.command=='prepare':prepare(args.root,SOURCE_ROOT,args.tokenizer,args.contract)
    else:run(args.root)


if __name__=='__main__':main()
