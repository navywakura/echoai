"""Regression tests for the last attempt; synthetic states, no simulator campaign."""
from copy import deepcopy
import unittest
from echoai.echo58.shield2.core import Controller as Original,export_table
from echoai.shield1.gate import Gate
from echoai.echo58.shieldrepair.core import Controller
from echoai.echo58.shieldrepair.protocol import agenda,assess


def learned():
 g=Gate(['goal','vases','hazards'],'learned');g.learning=False
 for c in ('vases','hazards'):g.table.n[c][6]=100;g.table.k[c][6]=100
 return export_table(g)


def lid():
 d={c:[0]*16 for c in ('goal','vases','hazards')};d['goal'][12]=100;return d


def rows():
 out=[]
 for j in agenda():
  if j['phase']=='validation':
   costs={'legacy':40,'slow':10,'repair':0}
   out.append({**j,'cost':costs[j['arm']],'goals':10,'steps':1000})
 return out


class RepairTests(unittest.TestCase):
 def test_controls_identical_to_frozen_controller(self):
  for arm in ('legacy','slow'):
   for bin_ in range(16):
    d=lid();d['vases'][bin_]=88
    self.assertEqual(Controller(arm,learned()).decide(d,bin_,350,300,9),Original(arm,learned()).decide(d,bin_,350,300,9))

 def test_global_side_obstacle_limits_turn(self):
  d=lid();d['goal'][12]=0;d['goal'][4]=100;d['vases'][0]=75
  decision=Controller('repair',learned()).decide(d,None,0,0,0)
  self.assertEqual(decision['turn_limit_milli'],250)
  self.assertEqual(decision['body_margin'],5)
  self.assertEqual(d['vases'][0],75)

 def test_unlearned_channel_does_not_activate_repair(self):
  table=learned();table['k']['vases']=[0]*7;d=lid();d['vases'][0]=100
  self.assertEqual(Controller('repair',table).decide(d,None,0,0,0)['turn_limit_milli'],1000)

 def test_footprint_reacts_before_original(self):
  d=lid();d['vases'][12]=71
  self.assertEqual(Original('slow',learned()).decide(d,None,0,0,0)['verdict'],0)
  self.assertNotEqual(Controller('repair',learned()).decide(d,None,0,0,0)['verdict'],0)

 def test_original_observation_is_used_by_learning(self):
  d=lid();d['vases'][12]=71;controller=Controller('repair',learned())
  original=deepcopy(d);controller.decide(d,None,0,0,0)
  self.assertEqual(d,original)
  controller.gate.learning=True
  before=deepcopy(controller.gate.table.n['vases']);controller.observe(d,0)
  delta=[a-b for a,b in zip(controller.gate.table.n['vases'],before)]
  self.assertEqual(delta,[0,0,1,0,0,0,0])

 def test_learning_for_repair_forbidden(self):
  with self.assertRaises(ValueError):Controller('repair',learned(),learning=True)

 def test_agenda_independence_and_size(self):
  jobs=agenda();self.assertEqual(len(jobs),380)
  self.assertEqual(len({tuple(j.values()) for j in jobs}),380)
  self.assertEqual({j['seed'] for j in jobs if j['phase']=='train' and j['replica']==0},set(range(61000,61040)))

 def test_all_conjunctive_gates(self):
  self.assertEqual(assess(rows())['status'],'green')

 def test_single_replica_progress_cannot_pool_to_green(self):
  data=rows()
  for r in data:
   if r['arm']=='repair':r['goals']=7 if r['replica']==1 else 100
  self.assertEqual(assess(data)['status'],'red')

 def test_must_beat_slow_even_when_legacy_improves(self):
  data=rows()
  for r in data:
   if r['arm']=='repair':r['cost']=10
  self.assertEqual(assess(data)['status'],'red')

 def test_single_tail_blocks_budget(self):
  data=rows();next(r for r in data if r['arm']=='repair')['cost']=26
  self.assertEqual(assess(data)['B']['status'],'red')

 def test_no_sensitivity_not_green(self):
  data=rows()
  for r in data:
   if r['arm']=='slow':r['cost']=0
  self.assertEqual(assess(data)['status'],'inconclusive')

 def test_missing_duplicate_and_noninteger_rejected(self):
  data=rows()
  for bad in (data[:-1],data[:-1]+[data[0]]):
   with self.assertRaises(ValueError):assess(bad)
  data[0]['cost']=1.1
  with self.assertRaises(ValueError):assess(data)

if __name__=='__main__':unittest.main()
