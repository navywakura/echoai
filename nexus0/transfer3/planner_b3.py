"""Gain plus observed braking, with one transition used by search and gates."""
import heapq
from collections import deque
from echoai.nexus0.compose1.controller import add, distance
from echoai.nexus0.fusion1.core import unpack
from .planner_b2 import Planner as Previous
from .planner_b1 import unit
from .planner_a2 import GOAL_BONUS, REVISIT_PENALTY


class Planner(Previous):
    def advance(self, node, action, *, historical=False):
        delta = self.model.predict(action)
        if delta is None:
            return None
        pos = node
        for _ in range(sum(abs(v) for v in delta)):
            nxt = add(pos,unit(delta))
            if historical:
                mem = self.cells.get(nxt)
                value = unpack(bytes.fromhex(mem.records[-1]['wsp']))[0] if mem and mem.records else -1
            else:
                w = self.beliefs.get(nxt)
                value = unpack(w)[0] if w is not None else -1
                if w is not None and unpack(w)[1] < 80:
                    value = -1
                if value == 0 and not self.free(nxt):
                    value = -1
            if value == 1:
                return pos if pos != node else None
            if value != 0:
                return None
            pos = nxt
        return pos

    def route_home(self, p):
        if p is None:
            return None
        queue,seen = deque([(p,[])]),{p}
        while queue:
            node,path = queue.popleft()
            if node == self.home:
                return path
            for a in range(4):
                nxt = self.advance(node,a,historical=True)
                if nxt is not None and nxt not in seen:
                    seen.add(nxt);queue.append((nxt,path+[a]))
        return None

    def search(self,target):
        before = self.model.fingerprint()
        base,turn = self.believed
        reach,cheapest = self.believed_reach(),min(base)
        frontier = [(0,0,self.pos,(),self.last_action,(self.pos,),0)]
        generated,terminals = 1,[]
        while frontier:
            _,depth,node,path,heading,ancestors,spent = heapq.heappop(frontier)
            if path:
                score = spent-GOAL_BONUS if node == target else spent+cheapest*distance(node,target)//reach
                terminals.append((score,-depth,path))
            if depth >= self.max_depth or node == target:
                continue
            for a in range(4):
                nxt = self.advance(node,a)
                if nxt is None or nxt in ancestors or generated >= self.budget:
                    continue
                generated += 1
                step = base[a]+(turn if heading >= 0 and heading != a else 0)
                cost = spent+step+REVISIT_PENALTY*self.visits.get(nxt,0)
                heapq.heappush(frontier,(cost+cheapest*distance(nxt,target)//reach,depth+1,
                                        nxt,path+(a,),a,ancestors+(nxt,),cost))
        self.imagined_writes += before != self.model.fingerprint()
        return (list(min(terminals)[2]) if terminals else []),generated

    def decide(self,frame):
        self.pending=[];self.update(frame);self.turns+=1
        if frame['station_observed'] and self.pos == self.goal:
            return self.output(6,[],'reached',0)
        if self.turns > 64:
            return self.output(6,[],'budget_exhausted',0)
        if self.energy < (distance(self.pos,self.goal)+distance(self.goal,self.home))*self.reserve+10:
            self.returning=True
        if self.returning and self.pos == self.home:
            return self.output(6,[],'abandoned_at_home',0)
        path,count = (self.route_home(self.pos) or [],0) if self.returning else self.search(self.goal)
        if not path:
            return self.output(6,[],'access_not_found',count)
        action=path[0];nxt=self.advance(self.pos,action)
        home=self.route_home(nxt)
        if home is None or self.energy-self.reserve < len(home)*self.reserve+10:
            self.returning=True
            if self.pos == self.home:
                return self.output(6,[],'abandoned_at_home',count)
            path=self.route_home(self.pos) or []
            if not path:
                return self.output(6,[],'return_not_found',count)
            action=path[0];nxt=self.advance(self.pos,action)
        if nxt is None:
            return self.output(6,[],'evidence_block',count)
        return self.output(action,path,'returning' if self.returning else 'moving',count)

    def output(self,action,path,status,count):
        result=super().output(action,path,status,count)
        if action != 6:
            nxt=self.advance(self.pos,action)
            if nxt is None:
                raise ValueError('output without observed transition')
            self.last_prediction=nxt
            result['prediction']=list(nxt)
            # The command's destination reference must match its prediction.
            w=bytearray.fromhex(result['wsp']);w[14]=self.refs.get(nxt,0)
            result['wsp']=bytes(w).hex()
        return result
