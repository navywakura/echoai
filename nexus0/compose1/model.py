"""T and Q are the existing tables indexed by actual CAM slots.

Six displacement outcomes are learned from measured differences; the planner
does not get the world's transition function or its map.
"""
import hashlib
import json
from echoai.core.cam import Cam
from echoai.core.qn import simhash16
from echoai.core.wsp import pack
from echoai.nexus0.world import World
from echoai.nexus0.qtable import QTable


def state_packet(code,style):
    return pack(src=2,rel=14,dst=4,time=8,E={},domain=9,generator=8,
                style=style,slot=code&255,seq=(code>>8)&255)


class Effects:
    def __init__(self):
        self.cam=Cam();self.t=World(n_actions=7);self.q=QTable(n_actions=7)
        self.insertion=[];self.deltas={}

    def slot(self,w,create=False):
        s=self.cam.get(w)
        if s<0 and create:
            s=self.cam.put(w,simhash16(w),0,has_fact=0,source='compose1-observed')
            if s>=0:self.insertion.append(w.hex())
        return s

    def observe_effect(self,clear,action,delta):
        source=self.slot(state_packet(int(clear),1),True)
        delta=tuple(delta)
        # Outcome naming is by measured displacement, independent of action ID.
        if delta not in self.deltas.values():
            dest=self.slot(state_packet(len(self.deltas),2),True);self.deltas[dest]=delta
        dest=next(k for k,v in self.deltas.items() if v==delta)
        self.t.observe(source,action,dest)

    def predict(self,action):
        source=self.slot(state_packet(1,1))
        if source<0 or self.t.conf(source,action)<2:return None
        dest=self.t.predict(source,action)
        return self.deltas.get(dest)

    @staticmethod
    def feature(p,goal,blocked):
        code=0
        for a,b in zip(p,goal):code=code*3+(0 if b<a else 2 if b>a else 1)
        mask=sum((1<<i) for i,v in enumerate(blocked) if v)
        return state_packet(code*64+mask,3)

    def values(self,feature):
        slot=self.slot(feature)
        return [self.q.get(slot,a) if slot>=0 else 0 for a in range(7)]

    def learn_reward(self,feature,action,reward,next_feature):
        s=self.slot(feature,True);n=self.slot(next_feature,True)
        self.q.update(s,action,reward,n)

    def snapshot(self):
        slots=[i for i,s in enumerate(self.cam.slot) if s.occupied]
        return dict(packets=list(self.insertion),deltas={str(k):list(v) for k,v in self.deltas.items()},
                    conflicts=self.t.conflicts,inv_dropped=self.t.inv_dropped,
                    t={str(i):dict(pred=self.t.pred[i],n=self.t.n[i],alt=self.t.alt[i],alt_n=self.t.alt_n[i],inv=self.t.inv[i]) for i in slots},
                    q={str(i):[self.q.get(i,a) for a in range(7)] for i in slots})

    def fingerprint(self):
        return hashlib.sha256(json.dumps(self.snapshot(),sort_keys=True,separators=(',',':')).encode()).hexdigest()

    @classmethod
    def restore(cls,snapshot):
        obj=cls()
        for w in snapshot['packets']:obj.slot(bytes.fromhex(w),True)
        obj.deltas={int(k):tuple(v) for k,v in snapshot['deltas'].items()}
        obj.t.conflicts=snapshot['conflicts'];obj.t.inv_dropped=snapshot['inv_dropped']
        for k,r in snapshot['t'].items():
            i=int(k)
            for name in ('pred','n','alt','alt_n','inv'):getattr(obj.t,name)[i]=list(r[name])
        for k,row in snapshot['q'].items():
            for a,value in enumerate(row):obj.q.set(int(k),a,value)
        if obj.snapshot()!=snapshot:raise ValueError('snapshot does not reconstruct')
        return obj
