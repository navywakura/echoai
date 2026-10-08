"""Private, explicitly kinematic 3D benchmark. Never mounted in the agent cage."""
import random
from echoai.nexus0.fusion1.core import packet

DIRECTIONS=((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(0,0,0))
MOVE_COST, WAIT_COST, LAND_COST, MARGIN = 4, 1, 2, 8


def add(a,b):return tuple(x+y for x,y in zip(a,b))
def distance(a,b):return sum(abs(x-y) for x,y in zip(a,b))


class Space:
    def __init__(self,seed,condition='static'):
        rng=random.Random(seed)
        self.condition=condition
        self.rotation=rng.randrange(4)
        self.gap=(3,rng.choice((1,2,4,5)),rng.randrange(1,4))
        self.next_gap=(3,6-self.gap[1],4-self.gap[2])
        self.start=self.rotate((1,3,2));self.goal=self.rotate((5,3,2))
        self.pos=self.start;self.steps=0;self.energy=30 if condition=='low_energy' else 240
        self.collisions=0;self.moved=False;self.station_seen=False
        self.solids=self.make_solids(self.gap if condition!='closed' else None)
        self.camera_solids=set(self.solids)

    def rotate(self,p):
        x,y,z=p
        for _ in range(self.rotation):x,y=6-y,x
        return x,y,z

    def make_solids(self,gap):
        out=set()
        for x in range(7):
            for y in range(7):
                for z in range(5):
                    if x in (0,6) or y in (0,6) or z in (0,4) or (x==3 and (x,y,z)!=gap):
                        out.add(self.rotate((x,y,z)))
        return out

    def scan(self):
        # Two independent idealized range channels; a moved door causes one
        # camera exposure of lag. This is declared stimulus, not real optics.
        visible={self.pos}
        for direction in DIRECTIONS[:6]:
            p=self.pos
            for _ in range(4):
                p=add(p,direction)
                if not (0<=p[0]<7 and 0<=p[1]<7 and 0<=p[2]<5):break
                visible.add(p)
                if p in self.solids:break
        now=self.steps*25_000_000
        cells=[]
        for p in sorted(visible):
            cells.append(dict(position=list(p),depth=packet(int(p in self.camera_solids),40).hex(),
                              lidar=packet(int(p in self.solids),40).hex()))
        self.camera_solids=set(self.solids)
        station=self.pos==self.goal
        self.station_seen |= station
        return dict(now_ns=now,odometry=list(self.pos),energy=self.energy,
                    station_observed=station,cells=cells)

    def step(self,action):
        if type(action) is not int or not 0<=action<7:raise ValueError('action')
        before=self.pos;target=add(before,DIRECTIONS[action]);blocked=target in self.solids
        if blocked:self.collisions+=1
        else:self.pos=target
        cost=WAIT_COST if action==6 else MOVE_COST
        self.energy-=cost;self.steps+=1
        if self.condition=='dynamic' and self.steps>=4 and not self.moved and self.pos!=self.rotate(self.gap):
            self.solids=self.make_solids(self.next_gap);self.moved=True
        return dict(before=list(before),after=list(self.pos),delta=[b-a for a,b in zip(before,self.pos)],
                    blocked=blocked,cost=cost,energy=self.energy)

    def oracle_distance(self):
        queue=[(self.start,0)];seen={self.start}
        for p,d in queue:
            if p==self.goal:return d
            for v in DIRECTIONS[:6]:
                n=add(p,v)
                if n not in seen and n not in self.solids:
                    seen.add(n);queue.append((n,d+1))
        return None
