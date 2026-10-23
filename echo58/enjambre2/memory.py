"""Private consequences remain facts; received global postcards remain testimony."""
from collections import Counter
import json

from ..enjambre.team import Private as LegacyPrivate,Reader as LegacyReader,L1,L2,RM,as_counts,bound
from ..memx.memory import OUTCOMES
from .transport import BAD,eligible,token


class Trust:
    def __init__(self,author):
        self.author=author;self.good={};self.bad={};self.verified=set();self.events=[]

    def credible(self,author):
        return self.bad.get(author,0)==0 or self.good.get(author,0)>=3*self.bad[author]

    def observe(self,claims,keys,outcome,round,world):
        pending=[]
        for layer,key in keys:
            speakers={a:c for a,c in claims.get((layer,key),{}).items() if a!=self.author and eligible(c)}
            disputed=len({OUTCOMES[c[0]] in BAD for c in speakers.values()})>1
            updates=[]
            for author,c in sorted(speakers.items()):
                ident=(layer,key,author)
                if ident in self.verified:continue
                wrong=(OUTCOMES[c[0]] in BAD)!=(outcome in BAD)
                updates.append([author,int(wrong),int(not wrong and disputed)])
                pending.append((ident,author,int(wrong),int(not wrong and disputed)))
            if updates:self.events.append({'round':round,'world':world,'layer':layer,'key':list(key),
                'outcome':outcome,'speakers':[[a,*c] for a,c in sorted(speakers.items())],
                'updates':updates})
        for ident,author,wrong,credit in pending:
            self.verified.add(ident)
            if wrong:self.bad[author]=self.bad.get(author,0)+wrong
            if credit:self.good[author]=self.good.get(author,0)+credit


class Private(LegacyPrivate):
    def __init__(self,author):
        super().__init__();self.author=author;self.trust=Trust(author)
        self.claims={};self.round=0;self.observations=[];self.remote_observations=[]

    def set_snapshot(self,claims,round):self.claims=claims;self.round=round

    def observe(self,ident,sig,act,hand,outcome):
        self.observations.append([self.round,self.world,ident,sig,act,hand,outcome])
        keys=((L1,self.mem.cfg.l1_key(ident,sig,act,hand)),(L2,self.mem.cfg.l2_key(sig,act,hand)))
        self.trust.observe(self.claims,keys,outcome,self.round,self.world)
        super().observe(ident,sig,act,hand,outcome)

    def remote_observe(self,p,changed):
        changed=sorted(changed)
        self.remote_observations.append([self.round,self.world,p,changed])
        super().remote_observe(p,changed)


class Reader(LegacyReader):
    def __init__(self,arm,private,claims,provenance,records,notes,*,world,round):
        super().__init__(private.mem.cfg,private,None,notes,world=world)
        self.arm=arm;self.claims=claims;self.provenance=provenance;self.records=records
        self.me=private.author;self.trust=private.trust;self.world=world;self.round=round
        self.trace=Counter();self.global_asks=0;self.abstentions=0

    def _sources(self,layer,key,remove_altered=False):
        entries=self.claims.get((layer,key),{})
        out={}
        for author,claim in entries.items():
            index=self.provenance.get((layer,key),{}).get(author)
            if remove_altered and index is not None and self.records[index]['altered']:continue
            if self.arm in ('por_autor','prudente') and (author==self.me or not eligible(claim)):continue
            if self.arm=='prudente' and not self.trust.credible(author):continue
            out[author]=claim
        return out

    def resolve(self,layer,key,remove_altered=False):
        if self.arm=='sin_global':return None
        entries=self._sources(layer,key,remove_altered)
        if not entries:return None
        if self.arm!='prudente':
            values=list(entries.values())
            if self.arm=='por_autor':values=[(c[0],3,3) for c in values]
            result=bound(as_counts(values),*self.cfg.bounds[1 if layer!=L2 else 2])
            return result if layer!=RM else ('LINK' if result=='PASS' else None)
        voices=len({a for a in entries if self.trust.good.get(a,0)>0})+int(any(self.trust.good.get(a,0)==0 for a in entries))
        if layer==RM:return 'LINK' if voices>=2 else None
        outcomes={OUTCOMES[c[0]] for c in entries.values()}
        if outcomes<=BAD:return 'HURT' if voices>=2 else None
        if not outcomes&BAD and len(outcomes)==1:return next(iter(outcomes))
        return None

    def _global(self,layer,key):
        if self.arm=='sin_global':return None
        self.global_asks+=1
        result=self.resolve(layer,key)
        if result is None:self.abstentions+=1
        entries=self.claims.get((layer,key),{})
        if entries:
            ids=self.provenance.get((layer,key),{})
            altered=[index for author,index in ids.items() if author!=self.me and self.records[index]['altered']]
            row={'round':self.round,'world':self.world,'agent':self.me,'layer':layer,'key':list(key),
                'reply':result,'without_altered':self.resolve(layer,key,True),
                'entries':[[a,*v] for a,v in sorted(entries.items())],
                'postcards':[[a,i] for a,i in sorted(ids.items())],
                'altered':sorted(altered),'good':dict(self.trust.good),'bad':dict(self.trust.bad),
                'observation_index':len(self.private.observations)}
            row['remote_observation_index']=len(self.private.remote_observations)
            row['request']=list(self.request)
            self.trace[json.dumps(row,sort_keys=True,separators=(',',':'))]+=1
        return result

    def recall(self,ident,sig,act,hand):
        local=super().recall(ident,sig,act,hand)
        if local is not None:return local
        self.request=(ident,sig,act,hand)
        for layer,key in ((L1,self.cfg.l1_key(ident,sig,act,hand)),(L2,self.cfg.l2_key(sig,act,hand))):
            result=self._global(layer,key)
            if result is not None:
                self.hits+=1;self.by_source['global']+=1;self.last=(1 if layer==L1 else 2,key)
                return result
        return None

    def knows(self,p,g):
        if super().knows(p,g):return True
        self.request=(p,g)
        return self._global(RM,(p,g))=='LINK'

    def queries_receipt(self):
        return [dict(json.loads(row),count=count) for row,count in sorted(self.trace.items())]
