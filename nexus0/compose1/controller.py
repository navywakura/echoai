"""Receding-horizon composition over observed cells and learned effects.

No simulator import. This module is the same in every held-out room.
"""
import hashlib
import heapq
import json
from collections import deque
from echoai.core.wsp import pack
from echoai.nexus0.fusion1.core import EvidenceMemory, packet, unpack
from echoai.nexus0.fusion1.integration import admit
from .model import Effects


def add(a,b):return tuple(x+y for x,y in zip(a,b))
def distance(a,b):return sum(abs(x-y) for x,y in zip(a,b))


def point(p):
    if not isinstance(p,(list,tuple)) or len(p)!=3 or any(type(x) is not int or abs(x)>10000 for x in p):
        raise ValueError('invalid odometry/position')
    return tuple(p)


class Composer:
    def __init__(self,model,goal,mode='echo32'):
        if mode not in ('echo8','echo32','one_step','q','conventional','no_expiry','write_rollout','ignore_reserve','goal_is_fact','ignore_evidence'):
            raise ValueError('mode')
        self.model=Effects.restore(model);self.goal=point(goal);self.mode=mode
        self.budget=8 if mode=='echo8' else 32
        self.max_depth=1 if mode=='one_step' else 4
        self.cells={};self.refs={};self.visits={};self.last_values={}
        self.home=None;self.turns=0;self.returning=False;self.revisions=0
        self.last_prediction=None;self.prediction_errors=0;self.imagined_writes=0
        self.pending=[];self.plan_invalidations=0
        self.learned_fingerprint=self.model.fingerprint()

    def update(self,frame):
        if set(frame)!={'now_ns','odometry','energy','station_observed','cells'}:
            raise ValueError('unexpected frame field / private channel')
        if type(frame['now_ns']) is not int or frame['now_ns']<0 or type(frame['energy']) is not int \
                or type(frame['station_observed']) is not bool:raise ValueError('sensor scalar')
        self.pos=point(frame['odometry']);self.energy=frame['energy'];self.now=frame['now_ns']
        if self.home is None:self.home=self.pos
        if self.last_prediction is not None and self.pos!=self.last_prediction:
            self.prediction_errors+=1;self.pending=[];self.plan_invalidations+=1
        self.visits[self.pos]=self.visits.get(self.pos,0)+1
        for cell in frame['cells']:
            if set(cell)!={'position','depth','lidar'}:raise ValueError('cell schema')
            p=point(cell['position'])
            if p not in self.cells:
                if len(self.cells)>=256:raise ValueError('spatial capacity')
                self.refs[p]=len(self.cells);self.cells[p]=EvidenceMemory('no_expiry' if self.mode=='no_expiry' else '')
            mem=self.cells[p]
            for source in ('depth','lidar'):
                w=bytes.fromhex(cell[source]);value,certainty,_,_,_=unpack(w)
                w=packet(value,certainty,region=self.refs[p])
                extract=json.dumps(dict(source=source,position=list(p),wsp=w.hex(),capture_ns=self.now),sort_keys=True)
                mem.ingest(w,source=source,capture_ns=self.now,delivered_ns=self.now,valid=True,
                           extract=extract,extract_sha256=hashlib.sha256(extract.encode()).hexdigest())
        self.beliefs={p:m.resolve(now_ns=self.now,region=self.refs[p]) for p,m in self.cells.items()}
        for p,w in self.beliefs.items():
            value=unpack(w)[0]
            if p in self.last_values and value!=self.last_values[p] and value!=-1:self.revisions+=1
            self.last_values[p]=value

    def free(self,p):
        w=self.beliefs.get(p)
        return w is not None and admit(w)[0]==0

    def feature(self):
        blocked=[]
        for a in range(6):
            delta=self.model.predict(a)
            blocked.append(delta is None or not self.free(add(self.pos,delta)))
        return self.model.feature(self.pos,self.goal,blocked)

    def route_home(self,p):
        # Historical path is a cost estimate; the next movement still needs
        # fresh evidence. Former free cells do not become executable on memory.
        known={cell for cell,m in self.cells.items() if m.records and
               unpack(bytes.fromhex(m.records[-1]['wsp']))[0]==0}
        queue=deque([(p,[])]);seen={p}
        while queue:
            node,path=queue.popleft()
            if node==self.home:return path
            for a in range(6):
                delta=self.model.predict(a)
                if delta is None:continue
                nxt=add(node,delta)
                if nxt in known and nxt not in seen:
                    seen.add(nxt);queue.append((nxt,path+[a]))
        return None

    def search(self,target):
        before=self.model.fingerprint()
        qvalues=self.model.values(self.feature())
        if self.mode=='conventional':qvalues=[0]*7
        frontier=[(0,0,self.pos,[])];seen={self.pos};generated=1;best=None
        while frontier:
            _,depth,node,path=heapq.heappop(frontier)
            if path:
                cursor=self.pos;novelty=0
                for action in path:
                    cursor=add(cursor,self.model.predict(action))
                    novelty+=self.visits.get(cursor,0)*20
                score=-10000+depth if node==target else distance(node,target)*10+depth+novelty
                candidate=(score,-depth,-qvalues[path[0]],path)
                if best is None or candidate<best:best=candidate
            if depth==self.max_depth:continue
            for action in range(6):
                delta=self.model.predict(action)
                if delta is None:continue
                nxt=add(node,delta)
                if nxt in seen or (not self.free(nxt) and self.mode!='ignore_evidence'):continue
                if generated>=self.budget:break
                generated+=1;seen.add(nxt)
                heapq.heappush(frontier,(distance(nxt,target),depth+1,nxt,path+[action]))
        if self.mode=='write_rollout':self.model.observe_effect(True,0,(1,0,0))
        self.imagined_writes+=before!=self.model.fingerprint()
        return ([] if best is None else best[3]),generated

    def decide(self,frame):
        self.update(frame);self.turns+=1
        if frame['station_observed'] and self.pos==self.goal:
            return self.output(6,[],'reached',0)
        if self.mode=='goal_is_fact' and self.pos==self.goal:
            return self.output(6,[],'reached',0)
        if self.turns>64:return self.output(6,[],'budget_exhausted',0)
        lower_bound=(distance(self.pos,self.goal)+distance(self.goal,self.home))*4+10
        if self.energy<lower_bound and self.mode!='ignore_reserve':self.returning=True
        if self.returning and self.pos==self.home:return self.output(6,[],'abandoned_at_home',0)
        if self.returning:
            path=self.route_home(self.pos) or [];count=0
        elif self.mode=='q':
            values=self.model.values(self.feature())
            allowed=[a for a in range(6) if self.model.predict(a) is not None and self.free(add(self.pos,self.model.predict(a)))]
            path=[max(allowed,key=lambda a:(values[a],-a))] if allowed else [];count=0
        else:
            if self.pending and not self.free(add(self.pos,self.model.predict(self.pending[0]))):
                self.pending=[];self.plan_invalidations+=1
            if self.pending:path,count=list(self.pending),0
            else:path,count=self.search(self.goal)
        if not path:return self.output(6,[],'access_not_found',count)
        action=path[0];nxt=add(self.pos,self.model.predict(action))
        home=self.route_home(nxt)
        if self.mode!='ignore_reserve' and (home is None or self.energy-4<len(home)*4+10):
            self.returning=True
            if self.pos==self.home:return self.output(6,[],'abandoned_at_home',count)
            path=self.route_home(self.pos) or []
            if not path:return self.output(6,[],'return_not_found',count)
            action=path[0];nxt=add(self.pos,self.model.predict(action))
        if not self.free(nxt) and self.mode!='ignore_evidence':return self.output(6,[],'evidence_block',count)
        self.pending=path[1:] if not self.returning else []
        return self.output(action,path,'returning' if self.returning else 'moving',count)

    def output(self,action,path,status,count):
        path=path[:4]
        delta=self.model.predict(action) if action!=6 else (0,0,0)
        nxt=add(self.pos,delta) if delta is not None else self.pos
        self.last_prediction=nxt
        wsp=pack(src=2,rel=11 if action!=6 else 14,dst=5,time=8,E=dict(C=80 if action!=6 else 0),
                 domain=9,generator=8,style=action,slot=self.refs.get(nxt,0))
        return dict(wsp=wsp.hex(),prediction=list(nxt),plan=path,status=status,candidates=count,
                    depth=len(path),revisions=self.revisions,prediction_errors=self.prediction_errors,
                    imagined_writes=self.imagined_writes,model_sha256=self.model.fingerprint(),
                    plan_invalidations=self.plan_invalidations,
                    spatial_cells=len(self.cells),cam_used=self.model.cam.used,
                    cam_destroyed=self.model.cam.destroyed)
