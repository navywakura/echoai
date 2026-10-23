"""Learned-channel footprint margin and bounded differential wheel commands."""
from ..shield2.core import Controller as BaseController,export_table

ARMS=('legacy','slow','repair')


class Controller(BaseController):
 def __init__(self,arm,table,learning=False):
  if arm not in ARMS or (learning and arm!='legacy'):raise ValueError('arm/learning')
  super().__init__('slow' if arm=='repair' else arm,table,learning)
  self.arm=arm

 def decide(self,lid,move,speed_mm,vf_mm,cost):
  if self.arm!='repair':return super().decide(lid,move,speed_mm,vf_mm,cost)
  costly=self.gate.danger_tiers()
  expanded={c:[min(100,q+5) if q else 0 for q in readings] if c in costly else readings
            for c,readings in lid.items()}
  near=max((max(lid[c]) for c in costly),default=0)
  result=super().decide(expanded,move,speed_mm,vf_mm,cost)
  result.update(body_margin=5,allround_close=near,turn_limit_milli=250 if near>=75 else 1000)
  return result
