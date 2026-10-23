"""Read-only audit against original public rows and saved transmitted messages."""
import argparse
from fractions import Fraction
from pathlib import Path
import statistics

from . import bench as b, codec as c, corpus, metrics


def independently_normalise(row,index):
    data=row['data'];feedback={}
    for key in ('state','levels_completed','win_levels','full_reset','available_actions','action_input'):
        if key in data:
            value=data[key]
            if key=='action_input' and value is not None:
                value={k:v for k,v in value.items() if k in ('id','data')}
            feedback[key]=value
    return {'version':1,'packet':[2,14,4,8]+[0]*11+[index%256],
        'game_id':data['game_id'],'index':index,'feedback':feedback,'frame':data['frame']}


def audit_gate(games):
    savings=[];wt=jt=0;baselines={};no_regression=True
    for game,row in games.items():
        best=min(row['json'],key=lambda f:(sum(row['json'][f]['tokens'])+row['json'][f]['legend_tokens'],f))
        baselines[game]=best;w=row['wsp'];j=row['json'][best]
        wsum=sum(w['tokens'])+w['legend_tokens'];jsum=sum(j['tokens'])+j['legend_tokens']
        wt+=wsum;jt+=jsum;no_regression &= wsum<=jsum
        for wc,jc in zip(w['tokens'],j['tokens']):
            denominator=jc*64+j['legend_tokens']
            savings.append(Fraction(denominator-wc*64-w['legend_tokens'],denominator))
    savings.sort();med=(savings[63]+savings[64])/2;total=Fraction(jt-wt,jt)
    return {'green':med>=Fraction(3,20) and total>=Fraction(3,20) and no_regression,
        'median_saving':{'numerator':med.numerator,'denominator':med.denominator},
        'total_saving':{'numerator':total.numerator,'denominator':total.denominator},
        'baseline_by_game':baselines,'no_game_regression':no_regression}


def verify(root):
    root=Path(root);p=b.check_frozen(root);r=c.loads((root/'results.json').read_text())
    c.require(r['preflight_sha256']==corpus.file_hash(root/'preflight.json'),'preflight altered')
    c.require(r['fixture']==p['fixture'] and r['exam_run'] is False,'scope altered')
    tokenizer=b.load_tokenizer(p['tokenizer']);counts={};n=0
    for game in corpus.GAMES:
        info=p['games'][game]
        with Path(info['source']).open() as stream:
            gold=[independently_normalise(c.loads(next(stream)),i) for i in range(64)]
        saved=[c.loads(s) for s in (root/'corpus'/info['file']).read_text().splitlines()]
        c.require(gold==saved and [c.digest(x) for x in gold]==info['record_sha256'],'corpus lost source information')
        counts[game]={}
        for fmt in b.FORMATS:
            name=f'messages/{game}/{fmt}.jsonl'
            c.require(corpus.file_hash(root/name)==r['message_files'][name],'saved message file changed')
            rows=[c.loads(s) for s in (root/name).read_text().splitlines()]
            c.require(len(rows)==64,'message count')
            stream=c.StreamDecoder(gold[0]['game_id']);base=None;tokens=[];sizes=[];modes=[]
            for record,row in zip(gold,rows):
                c.require(row['index']==record['index'] and row['record_sha256']==c.digest(record),'record identity')
                c.require(stream.consume(row['message'],fmt)==record,'saved message roundtrip')
                actual=b.count(tokenizer,row['message']);c.require(actual==row['tokens'],'token count mismatch')
                c.require(len(row['message'].encode())==row['bytes'],'byte count mismatch')
                expected=b.best_encoding(record,fmt,tokenizer,base)
                c.require(all(row[k]==v for k,v in expected.items()),'mode selection mismatch')
                tokens.append(actual);sizes.append(row['bytes']);modes.append(row['mode']);n+=1;base=record
            lc=b.count(tokenizer,p['legends'][fmt]);g=r['games'][game][fmt]
            expected={'tokens':tokens,'legend_tokens':lc,'tokens_descriptive':b.describe(tokens),
                'tokens_total_with_legend':sum(tokens)+lc,
                'tokens_median_with_legend':statistics.median(tokens)+lc/64,
                'first_message_with_legend':tokens[0]+lc,'bytes_descriptive':b.describe(sizes),
                'bytes_total_with_legend':sum(sizes)+len(p['legends'][fmt].encode()),
                'mode_counts':{m:modes.count(m) for m in c.MODES}}
            for kind in ('encode','decode'):
                samples=g[f'{kind}_cpu_samples_ns']
                c.require(type(samples) is list and len(samples)==320 and
                    all(type(v) is int and v>=0 for v in samples),'invalid timing samples')
                expected[f'{kind}_cpu_samples_ns']=samples
                expected[f'{kind}_cpu_ns']=b.describe(samples)
            c.require(g==expected,'reported derived metrics mismatch')
            counts[game][fmt]={'tokens':tokens,'legend_tokens':lc}
    gate={g:{'wsp':counts[g]['wsp'],'json':{f:counts[g][f] for f in c.FORMATS}}
        for g,split in corpus.GAMES.items() if split=='evaluation'}
    c.require(gate==r['gate_input'],'gate input altered')
    check=audit_gate(gate)
    c.require(all(r['verdict'][key]==value for key,value in check.items()),'gate verdict mismatch')
    c.require(r['verdict']==metrics.verdict(gate),'derived verdict field mismatch')
    c.require(r['r1_compatibility_green'] is True and r['parse_failures']==0 and r['roundtrips_exact']==n==768,'compatibility mismatch')
    c.require(r['records']==192 and r['messages']==768,'reported sample size mismatch')
    b.check_frozen(root)
    return {'audit_green':True,'fixture':p['fixture'],'exam_run':False,'records':192,'messages':n,
        'scientific_green':check['green'],'verdict':check,'results_sha256':corpus.file_hash(root/'results.json')}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path)
    print(c.dumps(verify(parser.parse_args().root)))
