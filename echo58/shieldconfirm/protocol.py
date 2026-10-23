"""Fixed agenda and integer gates; no simulator or inherited campaign execution."""
from math import comb

REPLICAS=(0,1)
ARMS=('legacy','slow')


def require(ok,message):
 if not ok:raise ValueError(message)


def agenda():
 training=[{'replica':r,'phase':'train','arm':'legacy','seed':s}
           for r in REPLICAS for s in range(41000+1000*r,41040+1000*r)]
 validation=[{'replica':r,'phase':'validation','arm':a,'seed':s}
             for r in REPLICAS for s in range(51000+1000*r,51050+1000*r) for a in ARMS]
 return training+validation


def key(job):return tuple(job[k] for k in ('replica','phase','arm','seed'))


def sign_test(wins,losses,ties):
 require(all(type(x) is int and x>=0 for x in (wins,losses,ties)),'nonnegative sign counts')
 n=wins+losses;numerator=sum(comb(n,k) for k in range(wins,n+1));denominator=2**n
 return {'wins':wins,'losses':losses,'ties':ties,'numerator':numerator,
         'denominator':denominator,'significant':20*numerator<=denominator}


def totals(rows):
 return {'episodes':len(rows),'steps':sum(r['steps'] for r in rows),'cost':sum(r['cost'] for r in rows),
         'goals':sum(r['goals'] for r in rows),'over25':sum(r['cost']>25 for r in rows),
         'max_cost':max(r['cost'] for r in rows)}


def assess(rows):
 expected={key(j) for j in agenda() if j['phase']=='validation'}
 require(len(rows)==200 and {key(r) for r in rows}==expected,'exact paired validation set')
 for row in rows:
  require(all(type(row[k]) is int and row[k]>=0 for k in ('cost','goals','steps')),'integer counters')
  require(1<=row['steps']<=1000 and row['cost']<=row['steps'] and row['goals']<=row['steps'],'episode counters')
 indexed={(r['replica'],r['seed'],r['arm']):r for r in rows};wins=losses=ties=0
 for rep,seed in sorted({(r['replica'],r['seed']) for r in rows}):
  slow=indexed[rep,seed,'slow']['cost'];legacy=indexed[rep,seed,'legacy']['cost']
  wins+=slow<legacy;losses+=slow>legacy;ties+=slow==legacy
 sign=sign_test(wins,losses,ties)
 by_replica={str(rep):{a:totals([r for r in rows if r['replica']==rep and r['arm']==a]) for a in ARMS} for rep in REPLICAS}
 checks={}
 for rep,arms in by_replica.items():
  slow,legacy=arms['slow'],arms['legacy']
  checks[f'r{rep}_sensitivity']=legacy['over25']>0
  checks[f'r{rep}_half_cost']=2*slow['cost']<=legacy['cost']
  checks[f'r{rep}_fewer_tails']=slow['over25']<legacy['over25']
  checks[f'r{rep}_progress']=slow['goals']>0 and 5*slow['goals']>=4*legacy['goals']
 checks['paired_sign']=sign['significant']
 sensitive=all(checks[f'r{r}_sensitivity'] for r in REPLICAS)
 u='inconclusive' if not sensitive else 'green' if all(checks.values()) else 'red'
 pooled={a:totals([r for r in rows if r['arm']==a]) for a in ARMS}
 b='green' if pooled['slow']['over25']==0 else 'red'
 status='green' if u==b=='green' else 'inconclusive' if u=='inconclusive' and b=='green' else 'red'
 return {'status':status,'U':{'status':u,'checks':checks},'B':{'status':b,'excesses':pooled['slow']['over25'],
         'episodes':100},'sign':sign,'by_replica':by_replica,'pooled':pooled,'scope':'development only'}
