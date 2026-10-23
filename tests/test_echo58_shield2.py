import ast
import copy
import random
import unittest
from pathlib import Path
from echoai.shield1.gate import Gate
from echoai.echo58.shield2.core import Controller, export_table


def table(learned=False):
 g=Gate(('goal','hazards','vases'),'learned')
 if learned:g.table.n['hazards'][6]=100;g.table.k['hazards'][6]=90
 return export_table(g)


class Core(unittest.TestCase):
 def test_integer_core(self):
  src=Path(__file__).parents[1]/'echo58/shield2/core.py'
  for node in ast.walk(ast.parse(src.read_text())):
   if isinstance(node,ast.Constant):self.assertNotIsInstance(node.value,float)
   if isinstance(node,ast.BinOp):self.assertNotIsInstance(node.op,ast.Div)
 def test_legacy_equivalence(self):
  rng=random.Random(719);data=table(True);c=Controller('legacy',data)
  g=Gate(data['channels'],'learned');g.table.n=copy.deepcopy(data['n']);g.table.k=copy.deepcopy(data['k'])
  for _ in range(300):
   lid={k:[rng.randrange(101) for _ in range(16)] for k in data['channels']}
   move=rng.choice([None,*range(16)]);d=c.decide(lid,move,1234,-50,0)
   self.assertEqual((d['heading'],d['gate_brake'],d['verdict']),g.decide(lid,d['proposed'],move))
   self.assertEqual(d['brake'],d['gate_brake'])
 def test_margin_thresholds(self):
  c=Controller('adaptive',table());lid={k:[0]*16 for k in table()['channels']}
  for speed,margin in [(0,3),(500,3),(501,4),(1000,4),(1001,5),(9000,5)]:
   self.assertEqual(c.decide(lid,None,speed,0,0)['margin'],margin)
 def test_budget_stop_not_termination(self):
  c=Controller('budget_stop',table());lid={k:[0]*16 for k in table()['channels']}
  self.assertFalse(c.decide(lid,None,0,0,19)['budget_brake'])
  d=c.decide(lid,None,0,0,20);self.assertTrue(d['brake']);self.assertEqual(d['heading'],12)
 def test_speed_regulator_and_unlearned_channel(self):
  c=Controller('adaptive',table());lid={k:[100]*16 for k in table()['channels']};lid['goal'][12]=101
  d=c.decide(lid,None,400,400,0)
  self.assertEqual(d['target_mm'],700);self.assertEqual(d['throttle_milli'],150)
  self.assertTrue(c.decide(lid,None,900,801,0)['speed_brake'])
 def test_frozen_table(self):
  t=table(True);c=Controller('adaptive',t);lid={k:[95]*16 for k in t['channels']}
  c.observe(lid,1);self.assertEqual(export_table(c.gate),t)
 def test_learning_legacy_only(self):
  with self.assertRaises(ValueError):Controller('slow',table(),learning=True)

class Boundary(unittest.TestCase):
 def test_actions(self):
  from echoai.echo58.shield2.boundary import action
  from echoai.shield1.run import actuate
  for h in range(16):
   for vf in [-1.25,-0.1,0.,0.12345,1.2]:
    for brake in [False,True]:
     d={'heading':h,'brake':brake,'throttle_milli':None}
     self.assertEqual(action(d,vf).tolist(),actuate('Car',h,brake,vf).tolist())
  d={'heading':13,'brake':False,'throttle_milli':100}
  a=action(d,0);self.assertAlmostEqual(sum(a)/2,0.1)
 def test_trace_audit_and_tamper(self):
  import tempfile
  import types
  import numpy as np
  from echoai.echo58.shield2.boundary import play
  from echoai.echo58.shield2.audit import audit_episode
  from echoai.echo58.shield2.custody import read,write
  class Env:
   def __init__(self,fail=False):
    self.fail=fail;self.t=0
    self.task=types.SimpleNamespace(agent=types.SimpleNamespace(vel=np.zeros(3),mat=np.eye(3)),
     obs_info=types.SimpleNamespace(obs_space_dict={c+'_lidar':types.SimpleNamespace(shape=(16,)) for c in table()['channels']}))
   def reset(self,seed):return np.zeros(48),{}
   def step(self,a):
    self.t+=1
    if self.fail:raise RuntimeError('fake instrument failure')
    return np.zeros(48),1.,0.5,self.t==2,False,{'goal_met':self.t==2,'cost_vases_contact':0.5}
  with tempfile.TemporaryDirectory() as t:
   receipt=play(Env(),Controller('legacy',table()),1,Path(t)/'ok')
   self.assertEqual(receipt['cost'],2);self.assertEqual(receipt['goals'],1)
   audit_episode(Path(t)/'ok.json')
   obj=read(Path(t)/'ok.json');obj['cost']=0
   (Path(t)/'tamper.json').write_text(__import__('json').dumps(obj))
   with self.assertRaises(ValueError):audit_episode(Path(t)/'tamper.json')
   failed=play(Env(True),Controller('legacy',table()),1,Path(t)/'bad')
   self.assertEqual(failed['status'],'failed')
   with self.assertRaises(ValueError):audit_episode(Path(t)/'bad.json')

class Protocol(unittest.TestCase):
 def test_agenda(self):
  from echoai.echo58.shield2.bench import agenda
  a=agenda();self.assertEqual(len(a),250)
  self.assertEqual(len({(r['phase'],r['arm'],r['seed']) for r in a}),250)
  self.assertEqual([r['seed'] for r in a if r['phase']=='train'],list(range(31000,31040)))
 def test_no_utility_from_stopping(self):
  from echoai.echo58.shield2.audit import utility
  s={'legacy':{'over25':5,'cost':100,'goals':10},'adaptive':{'over25':0,'cost':0,'goals':0},'slow':{'cost':1,'goals':1}}
  self.assertFalse(utility(s)['pass'])
 def test_training_observes_and_audits(self):
  import tempfile,types,numpy as np
  from echoai.echo58.shield2.boundary import play
  from echoai.echo58.shield2.audit import audit_episode
  class Env:
   def __init__(self):
    self.task=types.SimpleNamespace(agent=types.SimpleNamespace(vel=np.zeros(3),mat=np.eye(3)),
     obs_info=types.SimpleNamespace(obs_space_dict={c+'_lidar':types.SimpleNamespace(shape=(16,)) for c in table()['channels']}))
   def reset(self,seed):return np.zeros(48),{}
   def step(self,a):return np.ones(48),0.,1.,True,False,{}
  with tempfile.TemporaryDirectory() as t:
   r=play(Env(),Controller('legacy',table(),True),2,Path(t)/'train')
   self.assertEqual(r['final_table']['n']['hazards'][6],1)
   self.assertEqual(r['final_table']['k']['hazards'][6],1)
   audit_episode(Path(t)/'train.json')

class ReviewRegressions(unittest.TestCase):
 def test_receipt_seed_bound_to_trace(self):
  import tempfile,types,numpy as np,json
  from echoai.echo58.shield2.boundary import play
  from echoai.echo58.shield2.audit import audit_episode
  class Env:
   def __init__(self):
    self.task=types.SimpleNamespace(agent=types.SimpleNamespace(vel=np.zeros(3),mat=np.eye(3)),
     obs_info=types.SimpleNamespace(obs_space_dict={c+'_lidar':types.SimpleNamespace(shape=(16,)) for c in table()['channels']}))
   def reset(self,seed):return np.zeros(48),{}
   def step(self,a):return np.zeros(48),0.,0.,True,False,{}
  with tempfile.TemporaryDirectory() as t:
   r=play(Env(),Controller('legacy',table()),1,Path(t)/'original')
   r['seed']=2;(Path(t)/'changed.json').write_text(json.dumps(r))
   with self.assertRaises(ValueError):audit_episode(Path(t)/'changed.json')
 def test_failed_lifecycle_not_a_success(self):
  import tempfile
  from echoai.echo58.shield2.bench import verify_lifecycle
  from echoai.echo58.shield2.custody import write
  with tempfile.TemporaryDirectory() as t:
   write(Path(t)/'episodes/x.failure.json',{'error':'close failed'})
   with self.assertRaises(ValueError):verify_lifecycle(Path(t))
 def test_descriptive_summary_keeps_diagnostic_evidence(self):
  from echoai.echo58.shield2.audit import summary
  r={'arm':'legacy','seed':1,'steps':1,'cost':1,'goals':0,'raw_cost':1.,'return':0.,'verdicts':[0,1,0],
     'observed':{'components':{'cost_vases_contact':1.},'cost_speed_mm_sum':500,'cost_steps':1,'extra_brakes':{'speed':1,'budget':0}},'phase':'diagnostic'}
  s=summary([r])['legacy'];self.assertEqual(s['components']['cost_vases_contact'],1.)
  self.assertEqual(s['cost_step_mean_speed_mm'],500);self.assertEqual(s['verdicts'],[0,1,0])

class LifecycleCoverage(unittest.TestCase):
 def fixture(self,root):
  from echoai.echo58.shield2.bench import agenda,event,context,stem,receipt_hashes
  from echoai.echo58.shield2.custody import write,read,sha,digest
  write(root/'freeze.json',{'created_utc':'2000-01-01T00:00:00+00:00'})
  write(root/'agenda.json',agenda());p=event(root,'run_start',**context(root,{'phase':'run'}))
  write(root/'started.json',{'utc':read(p)['utc']})
  for phase in ('train','diagnostic','validation'):
   if phase=='diagnostic':
    write(root/'learned-table.json',table());write(root/'table-freeze.json',{'sha':digest(table())})
    event(root,'table_frozen',table_sha=digest(table()),freeze_receipt_sha=sha(root/'table-freeze.json'))
   event(root,phase+'_start')
   for j in agenda():
    if j['phase']==phase:write(stem(root,j).with_suffix('.json'),{'synthetic':j})
   event(root,phase+'_end',receipts=receipt_hashes(root,phase))
  p=event(root,'run_end',episodes=250)
  write(root/'completed.json',{'episodes':250,'last_phase_sha':sha(p),'utc':read(p)['utc']})
 def test_phase_missing_or_close_failure_rejects_complete_receipts(self):
  import tempfile
  from echoai.echo58.shield2.bench import verify_lifecycle
  from echoai.echo58.shield2.custody import write
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);self.fixture(root);self.assertTrue(verify_lifecycle(root))
   write(root/'episodes/validation-legacy-33000.failure.json',{'error':'close failed after receipt'})
   with self.assertRaisesRegex(ValueError,'failure'):verify_lifecycle(root)
   (root/'episodes/validation-legacy-33000.failure.json').unlink()
   (root/'phases/03-table_frozen.json').unlink()
   with self.assertRaisesRegex(ValueError,'missing'):verify_lifecycle(root)
 def test_setup_failure_gets_durable_run_receipt(self):
  import tempfile
  from unittest.mock import patch
  from echoai.echo58.shield2.bench import run,agenda
  from echoai.echo58.shield2.custody import write,read
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);write(root/'freeze.json',{});write(root/'agenda.json',agenda())
   with patch('echoai.echo58.shield2.bench.check_sources'),patch('echoai.shield1.run.make',side_effect=RuntimeError('setup failed')):
    with self.assertRaisesRegex(RuntimeError,'setup failed'):run(root)
   self.assertIn('setup failed',read(root/'failure.json')['traceback'])
   self.assertEqual(read(root/'failure.json')['active']['phase'],'train')
