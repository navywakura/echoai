import copy
import tempfile
import unittest
from pathlib import Path
from echoai.echo58.shieldconfirm.protocol import agenda,assess,sign_test


def rows():
 return [{**j,'cost':100 if j['arm']=='legacy' else 0,'goals':1,'steps':1000}
         for j in agenda() if j['phase']=='validation']


class Protocol(unittest.TestCase):
 def test_exact_agenda_and_fresh_independent_lineages(self):
  a=agenda();self.assertEqual(len(a),280)
  self.assertEqual(len({(j['replica'],j['phase'],j['arm'],j['seed']) for j in a}),280)
  self.assertEqual([j['seed'] for j in a if j['phase']=='train' and j['replica']==0],list(range(41000,41040)))
  self.assertEqual([j['seed'] for j in a if j['phase']=='train' and j['replica']==1],list(range(42000,42040)))
  for rep in (0,1):
   seeds={j['seed'] for j in a if j['replica']==rep and j['phase']=='validation'}
   self.assertEqual(seeds,set(range(51000+1000*rep,51050+1000*rep)))
 def test_full_green_requires_u_and_b(self):
  a=assess(rows());self.assertEqual(a['U']['status'],'green');self.assertEqual(a['B']['status'],'green')
  self.assertEqual(a['status'],'green');self.assertEqual(a['sign']['wins'],100)
 def test_utility_green_residual_tail_keeps_full_red(self):
  rr=rows();next(r for r in rr if r['arm']=='slow')['cost']=26
  a=assess(rr);self.assertEqual(a['U']['status'],'green');self.assertEqual(a['B']['status'],'red')
  self.assertEqual(a['status'],'red')
 def test_no_pooled_mask_of_bad_replica(self):
  rr=rows()
  for r in rr:
   if r['replica']==1 and r['arm']=='slow':r['goals']=0
  a=assess(rr);self.assertEqual(a['U']['status'],'red');self.assertFalse(a['U']['checks']['r1_progress'])
 def test_insensitive_replica_inconclusive_not_green(self):
  rr=rows()
  for r in rr:
   if r['replica']==1 and r['arm']=='legacy':r['cost']=0
  a=assess(rr);self.assertEqual(a['U']['status'],'inconclusive');self.assertEqual(a['status'],'inconclusive')
 def test_missing_duplicate_and_invalid_counters_reject(self):
  for rr in (rows()[:-1],[*rows(),rows()[0]]):
   with self.assertRaises(ValueError):assess(rr)
  rr=rows();rr[0]['cost']=-1
  with self.assertRaises(ValueError):assess(rr)
 def test_exact_sign_fraction_ties_and_direction(self):
  self.assertEqual(sign_test(0,0,100)['numerator'],1)
  self.assertEqual(sign_test(0,0,100)['denominator'],1)
  self.assertFalse(sign_test(8,2,90)['significant'])
  s=sign_test(9,1,90);self.assertEqual((s['numerator'],s['denominator']),(11,1024));self.assertTrue(s['significant'])
  rr=rows()
  for r in rr:r['cost']=0
  rr[0]['cost']=1
  a=assess(rr);self.assertEqual(a['sign']['wins'],1);self.assertEqual(a['sign']['losses'],0);self.assertEqual(a['sign']['ties'],99)

class Evidence(unittest.TestCase):
 def executor(self):
  from concurrent.futures import Future
  class Immediate:
   def __init__(self,**kwargs):pass
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def submit(self,fn,*args):
    f=Future()
    try:f.set_result(fn(*args))
    except BaseException as e:f.set_exception(e)
    return f
  return Immediate
 def env(self,root,close_failure=False):
  import types,numpy as np
  class Env:
   def __init__(self):
    self.task=types.SimpleNamespace(agent=types.SimpleNamespace(vel=np.zeros(3),mat=np.eye(3)),
      obs_info=types.SimpleNamespace(obs_space_dict={c+'_lidar':types.SimpleNamespace(shape=(16,)) for c in ('goal','hazards')}))
   def reset(self,seed):
    if seed>=51000:
     assert (root/'tables-committed.json').exists(),'validation before table barrier'
    return np.zeros(32),{}
   def step(self,act):return np.zeros(32),1.,0.,True,False,{'goal_met':True,'cost_sum':0.}
   def close(self):
    if close_failure:raise RuntimeError('close failed after complete receipt')
  return Env()
 def test_full_fake_run_equal_tables_and_custody_mutations(self):
  from contextlib import redirect_stdout
  from io import StringIO
  from unittest.mock import patch
  from echoai.echo58.shieldconfirm.bench import prepare,run,verify_lifecycle,stem
  from echoai.echo58.shieldconfirm.audit import audit
  from echoai.echo58.shield2.custody import read,write
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run';prepare(root)
   with patch('echoai.echo58.shieldconfirm.bench.ProcessPoolExecutor',self.executor()),patch('echoai.shield1.run.make',side_effect=lambda *a:self.env(root)),redirect_stdout(StringIO()):run(root)
   self.assertTrue(verify_lifecycle(root))
   tables=[read(root/'tables'/f'r{r}.json') for r in (0,1)]
   self.assertEqual(tables[0],tables[1]);self.assertEqual(tables[0]['n']['goal'][0],40)
   result=audit(root);self.assertEqual(result['episodes'],280);self.assertEqual(result['assessment']['status'],'inconclusive')
   phase=root/'phases/03-tables_frozen.json';raw=phase.read_bytes();phase.unlink()
   with self.assertRaises(ValueError):verify_lifecycle(root)
   phase.write_bytes(raw)
   write(root/'validation.failure.json',{'error':'late process failure'})
   with self.assertRaises(ValueError):verify_lifecycle(root)
 def test_setup_or_close_failure_durable_and_no_validation(self):
  from contextlib import redirect_stdout
  from io import StringIO
  from unittest.mock import patch
  from echoai.echo58.shieldconfirm.bench import prepare,run
  from echoai.echo58.shield2.custody import read
  for failure in ('setup','close'):
   with self.subTest(failure=failure),tempfile.TemporaryDirectory() as t:
    root=Path(t)/'run';prepare(root)
    factory=(lambda *a: (_ for _ in ()).throw(RuntimeError('setup failed'))) if failure=='setup' else lambda *a:self.env(root,True)
    with patch('echoai.echo58.shieldconfirm.bench.ProcessPoolExecutor',self.executor()),patch('echoai.shield1.run.make',side_effect=factory),redirect_stdout(StringIO()):
     with self.assertRaises(RuntimeError):run(root)
    self.assertTrue((root/'failure.json').exists());self.assertFalse((root/'tables-committed.json').exists())
    self.assertFalse(list((root/'episodes').glob('*validation*')))
    self.assertEqual(read(root/'failure.json')['active']['phase'],'train')

class ReviewRegressions(Evidence):
 # Inherit fake-env/executor helpers; suppress duplicate inherited test discovery.
 test_full_fake_run_equal_tables_and_custody_mutations=None
 test_setup_or_close_failure_durable_and_no_validation=None
 def complete(self,root):
  from contextlib import redirect_stdout
  from io import StringIO
  from unittest.mock import patch
  from echoai.echo58.shieldconfirm.bench import prepare,run
  prepare(root)
  with patch('echoai.echo58.shieldconfirm.bench.ProcessPoolExecutor',self.executor()),patch('echoai.shield1.run.make',side_effect=lambda *a:self.env(root)),redirect_stdout(StringIO()):run(root)
 def test_repeat_is_nonmutating(self):
  from echoai.echo58.shieldconfirm.bench import run
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run';self.complete(root)
   before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   with self.assertRaises(FileExistsError):run(root)
   after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   self.assertEqual(before,after)
 def test_orphan_trace_is_rejected(self):
  from echoai.echo58.shieldconfirm.bench import verify_lifecycle
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run';self.complete(root)
   (root/'episodes/r0-validation-slow-99999.jsonl.gz').write_bytes(b'orphan')
   with self.assertRaises(ValueError):verify_lifecycle(root)
 def test_preflight_failure_is_durable(self):
  from unittest.mock import patch
  from echoai.echo58.shieldconfirm.bench import prepare,run
  from echoai.echo58.shield2.custody import read
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)/'run';prepare(root)
   with patch('echoai.echo58.shieldconfirm.bench.check_sources',side_effect=RuntimeError('preflight failed')):
    with self.assertRaises(RuntimeError):run(root)
   self.assertEqual(read(root/'failure.json')['active']['phase'],'preflight')
