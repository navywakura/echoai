"""Actuator/custody tests run in the existing optional simulator environment."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from echoai.echo58.shieldrepair.core import Controller
from echoai.echo58.shieldrepair.boundary import action,play
from echoai.echo58.shieldrepair.episode_audit import audit_episode
from echoai.echo58.shieldrepair.bench import run,prepare
from echoai.echo58.shield2.custody import read,write
from echoai.echo58.shield2.boundary import action as baseline_action
from echoai.tests.test_echo58_shieldrepair import learned,lid


class BoundaryTests(unittest.TestCase):
 def test_outside_cone_wheel_difference_bounded(self):
  d=lid();d['goal'][12]=0;d['goal'][4]=100;d['vases'][0]=80
  decision=Controller('repair',learned()).decide(d,None,0,0,0)
  wheels=action(decision,0)
  self.assertLessEqual(abs(wheels[0]-wheels[1]),0.5)
  self.assertEqual(max(abs(wheels)),0.25)

 def test_common_braking_preserved(self):
  d={'heading':4,'brake':True,'throttle_milli':0,'turn_limit_milli':250}
  wheels=action(d,.2)
  self.assertAlmostEqual(sum(wheels)/2,-.4)
  self.assertLessEqual(abs(wheels[0]-wheels[1]),.5)

 def test_unaffected_controls_action_exact(self):
  for arm in ('legacy','slow'):
   d=Controller(arm,learned()).decide(lid(),None,0,0,0)
   self.assertEqual(action(d,0).tolist(),baseline_action(d,0).tolist())

 def test_cannot_restart_mutate_attempt(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);write(p/'started.json',{'sentinel':1});before=(p/'started.json').read_bytes()
   with self.assertRaises(FileExistsError):run(p)
   self.assertEqual((p/'started.json').read_bytes(),before)
   self.assertFalse((p/'failure.json').exists())

 def test_cannot_prepare_overwrite_existing(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);write(p/'freeze.json',{'sentinel':1})
   with self.assertRaises(ValueError):prepare(p)
   self.assertEqual(read(p/'freeze.json'),{'sentinel':1})

 def test_step_failure_persists_failed_receipt(self):
  from unittest.mock import patch
  class Env:
   def reset(self,seed):return None,{}
   def step(self,action):raise RuntimeError('synthetic step failure')
  state={'lid':lid(),'move':None,'vf':0.0,'speed':0.0,'vf_mm':0,'speed_mm':0}
  with tempfile.TemporaryDirectory() as tmp:
   stem=Path(tmp)/'failure'
   with patch('echoai.echo58.shieldrepair.boundary.slices',return_value={}),patch('echoai.echo58.shieldrepair.boundary.state',return_value=state):
    receipt=play(Env(),Controller('repair',learned()),1,stem)
   self.assertEqual(receipt['status'],'failed');self.assertIn('synthetic step failure',receipt['error'])
   with self.assertRaises(ValueError):audit_episode(stem.with_suffix('.json'))

 def test_recorded_action_and_chain_tampering_rejected(self):
  from unittest.mock import patch
  class Env:
   def reset(self,seed):return None,{}
   def step(self,action):return None,1.,0.,True,False,{'goal_met':True}
  state={'lid':lid(),'move':None,'vf':0.0,'speed':0.0,'vf_mm':0,'speed_mm':0}
  with tempfile.TemporaryDirectory() as tmp:
   stem=Path(tmp)/'success'
   with patch('echoai.echo58.shieldrepair.boundary.slices',return_value={}),patch('echoai.echo58.shieldrepair.boundary.state',return_value=state):
    receipt=play(Env(),Controller('repair',learned()),1,stem)
   self.assertEqual(audit_episode(stem.with_suffix('.json'))['goals'],1)
   trace=stem.with_suffix('.jsonl.gz');rows=list(gzip.open(trace,'rt'));row=json.loads(rows[1]);row['data']['action'][0]=.99
   with gzip.open(trace,'wt') as stream:stream.writelines([rows[0],json.dumps(row)+'\n'])
   with self.assertRaises(ValueError):audit_episode(stem.with_suffix('.json'))

if __name__=='__main__':unittest.main()
