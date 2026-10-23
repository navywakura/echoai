"""Integer controller. Original learned Gate, plus bounded speed/margin policy."""
from copy import deepcopy
from echoai.shield1.gate import Gate, ang, heading_closeness

ARMS=('legacy','slow','adaptive','budget_stop')


def export_table(gate):
 return {'channels':list(gate.channels),'n':deepcopy(gate.table.n),'k':deepcopy(gate.table.k)}


class Controller:
 def __init__(self,arm,table,learning=False):
  if arm not in ARMS or (learning and arm!='legacy'):raise ValueError('arm/learning')
  self.arm=arm;self.gate=Gate(table['channels'],'learned')
  self.gate.table.n=deepcopy(table['n']);self.gate.table.k=deepcopy(table['k'])
  self.gate.learning=learning

 def decide(self,lid,move,speed_mm,vf_mm,cost):
  if any(type(v) is not int for v in (speed_mm,vf_mm,cost)):raise ValueError('integer state')
  if speed_mm<0 or cost<0:raise ValueError('negative speed/cost')
  proposed=max(range(16),key=lambda b:(lid['goal'][b],-ang(b,12)))
  self.gate.margin=3+(min(2,max(0,(speed_mm-1)//500)) if self.arm=='adaptive' else 0)
  heading,gate_brake,verdict=self.gate.decide(lid,proposed,move)
  close=max((heading_closeness(lid[c],heading) for c in self.gate.danger_tiers()),default=0)
  target=None if self.arm=='legacy' else (700 if self.arm=='adaptive' and close<65 else 300)
  speed_brake=target is not None and vf_mm>target+100
  budget_brake=self.arm=='budget_stop' and cost>=20
  if budget_brake:heading=12
  relative=(heading-12)%16;signed=relative if relative<8 else relative-16
  nominal=1000 if abs(signed)<=1 else 300 if abs(signed)<=3 else 0
  throttle=None if target is None else min(nominal,max(0,(target-vf_mm)//2))
  return {'proposed':proposed,'heading':heading,'gate_brake':gate_brake,'verdict':verdict,
   'margin':self.gate.margin,'close':close,'target_mm':target,'speed_brake':speed_brake,
   'budget_brake':budget_brake,'brake':gate_brake or speed_brake or budget_brake,
   'throttle_milli':throttle}

 def observe(self,lid,cost):self.gate.observe(lid,cost)
