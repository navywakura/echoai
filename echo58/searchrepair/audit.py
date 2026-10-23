"""Recorded-result consistency and program execution, explicitly no search replay."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .api import BEAMS,LIMIT,Budget,data,execute,verify_journal,config
from ..shield2.custody import read,write,digest,sha


def require(ok,msg):
 if not ok:raise ValueError(msg)


def validate_result(task,r):
 m=r['metrics']
 for name in ('limit','used','remaining','task_used','cortex_calls','candidates','tier'):
  require(type(m[name]) is int and m[name]>=0,'integer nonnegative metric '+name)
 require(type(m['counts']) is dict and all(type(k) is str and k and type(v) is int and v>=0 for k,v in m['counts'].items()),'work counters')
 for name,value in m.items():
  if type(value) is int:require(value>=0,'negative statistic '+name)
  if type(value) is dict:require(all(type(v) is int and v>=0 for v in value.values()),'nonnegative nested statistics')
 require(m['candidates']<=12000 and m['tier']<=4,'search bounds')
 require(m['candidates']==m['counts'].get('candidate_attempts',0),'candidate accounting')
 require(type(m['complete']) is bool,'closure boolean')
 require(m['search_strategy']=='certified' and m['ranking_bound_enabled'] is True,'search strategy')
 if r['status'] in ('budget_exhausted','search_exhausted'):require(m['complete'] is False,'exhaustion cannot close tier')
 else:require(m['complete'] is True,'non-exhausted tier incomplete')
 if r['status']=='search_exhausted':require(m['search_limit_hit'] is True and m['candidates']==12000,'candidate exhaustion')
 require(m['limit']==LIMIT and 0<=m['used']<=LIMIT,'work budget')
 require(m['used']==sum(m['counts'].values()) and m['remaining']==LIMIT-m['used'],'work accounting')
 require(m['task_used']==m['used'] and m['cortex_calls']==0,'actor work/LLM')
 require(r['test_verified'] is False,'query verification claim')
 ledger=Budget(20_000_000)
 if r['status']=='solved':
  require(m['complete'] is True and r['program'] is not None,'unclosed/absent program')
  for d in task['train']:
   predicted=execute(r['program'],d['input'],budget=ledger)
   require([list(row) for row in predicted]==d['output'],'program demonstration mismatch')
  predicted=[[list(row) for row in execute(r['program'],q['input'],budget=ledger)] for q in task['test']]
  require(predicted==r['predictions'],'program prediction mismatch')
 else:
  require(r['status'] in data.ABSTENTIONS and r['predictions']==[] and r['program'] is None,'invalid abstention')
 return ledger.snapshot()


def validate_journal(events,identity,task,result):
 begin,end=events[0],events[-1];cfg=config(identity['beam'])
 require(begin['kind']=='search_repair_begin' and begin['identity']==identity and
         begin['configuration']==cfg and begin['budget']==LIMIT,'journal begin protocol')
 require(end['kind']=='search_repair_end' and end['identity']==identity and
         end['status']==result['status'] and end['result_sha']==digest(result),'journal end result')
 observations=[e for e in events if e['kind']=='grid_observation']
 require(len(observations)==1,'one solver observation')
 o=observations[0]
 require(o['search']==cfg and o['cache_policy']=='interned' and o['hierarchical'] is True and
         o['demonstrations']==len(task['train']) and o['queries']==len(task['test']),'solver observation protocol')
 final=[e for e in events if e['kind']=='grid_result']
 require(len(final)==1 and final[0]['status']==result['status'] and final[0]['metrics']==result['metrics'] and
         final[0]['test_verified'] is False,'solver result consistency')
 previous_work=0
 for e in events:
  if e['kind']=='synthesis_frontier':
   require(type(e['retained']) is int and 0<=e['retained']<=identity['beam'],'retained frontier bound')
   require(1<=e['depth']<=4 and previous_work<=e['work']<=result['metrics']['used'],'frontier accounting')
   previous_work=e['work']
 require(result['metrics']['frontier_peak']<=identity['beam'],'frontier peak bound')


def utility(summary):
 candidate,base=summary['8'],summary['24']
 checks={'more_exact':candidate['exact']>base['exact'],
  'no_supported_regression':all(candidate['families'][f]['exact']>=base['families'][f]['exact'] for f in data.SUPPORTED_FAMILIES),
  'target_improvement':any(candidate['families'][f]['exact']>base['families'][f]['exact'] for f in ('inside_erase_crop','right_erase_crop_rotate')),
  'no_wrong_or_false':candidate['wrong']==0 and candidate['false_commitments']==0,'no_more_work':candidate['work']<=base['work']}
 return {'checks':checks,'pass':all(checks.values()),'scope':'development only; beam8 fixed prospectively'}


def summarize(rows):
 out={}
 for beam in BEAMS:
  selected=[r for r in rows if r['beam']==beam]
  def aggregate(rr):
   counts=Counter()
   for r in rr:counts.update(r['result']['metrics']['counts'])
   return {'cases':len(rr),'exact':sum(r['score']['outcome']=='exact' for r in rr),
    'wrong':sum(r['score']['outcome']=='wrong' for r in rr),'false_commitments':sum(r['score']['false_commitment'] for r in rr),
    'work':sum(r['result']['metrics']['used'] for r in rr),'work_counts':dict(counts),
    'statuses':dict(Counter(r['result']['status'] for r in rr)),
    'cases_with_complete_final_tier':sum(r['result']['metrics']['complete'] for r in rr),
    'wall_seconds':sum(r['wall_seconds'] for r in rr),'cpu_seconds':sum(r['cpu_seconds'] for r in rr)}
  out[str(beam)]=aggregate(selected)
  out[str(beam)]['families']={f:aggregate([r for r in selected if r['family']==f]) for f in data.FAMILIES}
 return out


def audit(root):
 from .bench import check_prepared,agenda
 root=Path(root);check_prepared(root)
 require(not (root/'failure.json').exists(),'instrumental failure')
 require((root/'completed.json').is_file(),'run incomplete')
 done=read(root/'completed.json');start=read(root/'started.json');prepared=read(root/'prepared.json')
 require(prepared['utc']<=start['utc']<=done['utc'],'run ordering')
 require(start['prepared_sha']==done['prepared_sha']==sha(root/'prepared.json'),'run commitment')
 jobs,_=agenda();expected={f'results/{i:02d}-beam{b}.json' for i in range(32) for b in BEAMS}
 require(set(done['results'])==expected,'result set')
 rows=[];generation=Counter();copy_work=Counter();evaluation_work=Counter()
 for i,j in enumerate(jobs):
  case=read(root/'private'/f'{i:02d}.json');public=read(root/'public'/f'{i:02d}.json')
  require(case['seed']==j['seed'] and case['family']==j['family'],'case agenda')
  require(public==data.public_task(case) and digest(public)==case['public_sha256'],'public case')
  for stage,ledger in case['costs'].items():generation[stage]+=ledger['used']
  copy_work.update(read(root/'copy-cost'/f'{i:02d}.json')['counts'])
  for b in BEAMS:
   name=f'results/{i:02d}-beam{b}.json';require(sha(root/name)==done['results'][name],'result commitment')
   r=read(root/name);identity={'index':i,'beam':b,'public_sha':digest(public),'prepared_sha':sha(root/'prepared.json')}
   require(r['identity']==identity,'result identity')
   require(start['utc']<=r['completed_utc']<=done['utc'],'result ordering')
   trace=root/r['journal'];require(sha(trace)==r['journal_sha'],'journal identity');verify_journal(trace)
   events=[json.loads(line) for line in trace.read_text().splitlines()]
   validate_journal(events,identity,public,r['result'])
   evaluation_work.update(validate_result(public,r['result'])['counts'])
   ledger=Budget(20_000_000);score=data.score_result(case,r['result'],ledger=ledger);evaluation_work.update(ledger.counts)
   rows.append({**r,'beam':b,'family':j['family'],'index':i,'score':score})
 s=summarize(rows);out={'audit':'recorded_result_consistency_pass','search_replay':False,
  'scope':'programs executed and receipts checked; search completeness not independently replayed',
  'summary':s,'utility':utility(s),'preparation_costs':dict(generation),'public_copy_costs':dict(copy_work),
  'evaluation_costs':dict(evaluation_work),'rows':rows}
 write(root/'audit.json',out);return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();out=audit(a.root)
 print(json.dumps({'audit':out['audit'],'utility':out['utility'],
  'summary':{b:{k:v for k,v in s.items() if k not in ('families','work_counts')} for b,s in out['summary'].items()}},indent=2))
