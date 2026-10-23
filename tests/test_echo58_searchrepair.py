import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from echoai.echo58.searchrepair.api import data,Budget,actor,config
from echoai.echo58.searchrepair.bench import agenda
from echoai.echo58.searchrepair.audit import validate_result,utility


class SearchRepair(unittest.TestCase):
 def test_agenda_fixed_and_fresh(self):
  a,ledger=agenda();self.assertEqual(len(a),32);self.assertEqual(len({x['seed'] for x in a}),32)
  self.assertEqual(ledger['initial']['used'],0);self.assertEqual(ledger['initial']['counts'],{})
  self.assertEqual({x['family'] for x in a},set(data.FAMILIES))
 def test_only_public_input_reaches_solver(self):
  case=data.make_case(42,'inside_erase_crop');public=data.public_task(case)
  with patch('echoai.echo58.searchrepair.api.solve',return_value={'mock':True}) as s:
   actor(public,8)
   task=s.call_args.args[0];self.assertEqual(set(task),{'train','test'})
   self.assertTrue(all(set(q)=={'input'} for q in task['test']))
   self.assertEqual(s.call_args.kwargs['synthesis'],config(8));self.assertFalse(s.call_args.kwargs['learn'])
   self.assertIsNone(s.call_args.kwargs['library'])
  bad=copy.deepcopy(public);bad['test'][0]['output']=[[9]]
  with self.assertRaises(ValueError):actor(bad,8)
 def test_full_grammar_fixed_and_no_extra_arms(self):
  from echo5.programs import synthesis_atoms
  self.assertEqual(len(list(synthesis_atoms())),326)
  for n in (4,8,24,48):
   cfg=config(n);self.assertEqual(cfg['max_depth'],4);self.assertIsNone(cfg['grammar'])
  with self.assertRaises(ValueError):config(1)
 def test_budget_exhaustion_abstains(self):
  from echoai.echo58.searchrepair.api import solve
  task={'train':[{'input':[[1,0],[0,0]],'output':[[0,1],[0,0]]}], 'test':[{'input':[[2,0],[0,0]]}]}
  r=solve(task,budget=1,cache_policy='interned',synthesis=config(8))
  self.assertEqual(r['status'],'budget_exhausted');self.assertEqual(r['predictions'],[])
  self.assertIsNone(r['program']);self.assertFalse(r['test_verified'])
 def test_external_program_check_and_tamper(self):
  task={'train':[{'input':[[0,1],[0,0]],'output':[[0,1],[0,0]]}], 'test':[{'input':[[0,2],[0,0]]}]}
  from echoai.echo58.searchrepair.api import solve
  r=solve(task,budget=2_000_000,cache_policy='interned',synthesis=config(8))
  validate_result(task,r)
  broken=copy.deepcopy(r);broken['metrics']['used']+=1
  with self.assertRaises(ValueError):validate_result(task,broken)
  if r['status']=='solved':
   broken=copy.deepcopy(r);broken['predictions'][0][0][0]=9
   with self.assertRaises(ValueError):validate_result(task,broken)

class ScientificControls(unittest.TestCase):
 def test_utility_does_not_hide_regression_or_replace_primary(self):
  def arm(exact,work):
   return {'exact':exact,'work':work,'wrong':0,'false_commitments':0,
           'families':{f:{'exact':2} for f in data.FAMILIES}}
  s={'24':arm(12,100),'8':arm(13,90)}
  s['8']['families']['inside_erase_crop']['exact']=3
  self.assertTrue(utility(s)['pass'])
  s['8']['families']['pack_reflect']['exact']=1
  self.assertFalse(utility(s)['pass'])
  s['8']['families']['pack_reflect']['exact']=2;s['8']['false_commitments']=1
  self.assertFalse(utility(s)['pass'])
 def test_consensus_keeps_ambiguous_control_closed(self):
  from echoai.echo58.searchrepair.api import solve
  task={'train':[{'input':[[0,1,0]],'output':[[0,1,0]]}],
        'test':[{'input':[[2,0,0]]}]}
  r=solve(task,budget=2_000_000,cache_policy='interned',synthesis=config(8))
  self.assertEqual(r['status'],'ambiguous');self.assertEqual(r['predictions'],[])
  validate_result(task,r)
 def test_failure_and_missing_completion(self):
  from echoai.echo58.searchrepair.bench import check_prepared
  from echoai.echo58.searchrepair.audit import audit
  from echoai.echo58.shield2.custody import write
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);write(root/'failure.json',{'error':'failed'})
   with patch('echoai.echo58.searchrepair.bench.check_prepared'):
    with self.assertRaisesRegex(ValueError,'instrumental failure'):audit(root)
   (root/'failure.json').unlink()
   with patch('echoai.echo58.searchrepair.bench.check_prepared'):
    with self.assertRaisesRegex(ValueError,'incomplete'):audit(root)

class ReviewRegressions(unittest.TestCase):
 def task(self):return {'train':[{'input':[[0,1],[0,0]],'output':[[0,1],[0,0]]}], 'test':[{'input':[[0,1],[0,0]]}]}
 def result(self):return actor(self.task(),8)
 def test_impossible_counters_bounds_and_closure(self):
  r=self.result();r.update(status='budget_exhausted',predictions=[],program=None,hypothesis=None)
  r['metrics']['complete']=False
  for mutation in ('negative_counts','candidate_bound','tier_bound','complete_exhaustion'):
   bad=copy.deepcopy(r);m=bad['metrics']
   if mutation=='negative_counts':m.update(counts={'negative':-1,'positive':1},used=0,remaining=2_000_000,task_used=0)
   elif mutation=='candidate_bound':m['candidates']=12001
   elif mutation=='tier_bound':m['tier']=5
   else:m['complete']=True
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_result(self.task(),bad)
 def test_journal_fixed_protocol_and_result_consistency(self):
  import json
  from echoai.echo58.searchrepair.api import Recorder
  from echoai.echo58.searchrepair.audit import validate_journal
  from echoai.echo58.shield2.custody import digest
  with tempfile.TemporaryDirectory() as t:
   identity={'index':0,'beam':8,'public_sha':digest(self.task()),'prepared_sha':'test'}
   with Recorder(Path(t)/'thought.jsonl') as journal:
    journal.write(kind='search_repair_begin',identity=identity,configuration=config(8),budget=2_000_000)
    r=actor(self.task(),8,journal)
    journal.write(kind='search_repair_end',identity=identity,status=r['status'],result_sha=digest(r))
   events=[json.loads(line) for line in (Path(t)/'thought.jsonl').read_text().splitlines()]
   validate_journal(events,identity,self.task(),r)
   for mutation in ('begin_config','observation_cache','grid_result','end_status'):
    bad=copy.deepcopy(events)
    if mutation=='begin_config':bad[0]['configuration']['beam_width']=48
    elif mutation=='observation_cache':next(x for x in bad if x['kind']=='grid_observation')['cache_policy']='legacy'
    elif mutation=='grid_result':next(x for x in bad if x['kind']=='grid_result')['metrics']['used']+=1
    else:bad[-1]['status']='unsolved'
    with self.subTest(mutation=mutation),self.assertRaises(ValueError):validate_journal(bad,identity,self.task(),r)

class PreparedEvidence(unittest.TestCase):
 def test_real_source_and_case_hash_mutations(self):
  import platform
  from echoai.echo58.searchrepair.bench import check_prepared
  from echoai.echo58.shield2.custody import write,sha
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);source=root/'source.py';source.write_text('fixture\n')
   archived=root/'frozen/source.py';archived.parent.mkdir();archived.write_bytes(source.read_bytes())
   case=root/'public/00.json';write(case,{'fixture':True});jobs,ledger=agenda()
   write(root/'freeze.json',{'sources':{str(source):sha(source)},'archives':{'frozen/source.py':sha(archived)},'python':platform.python_version()})
   write(root/'agenda.json',jobs);write(root/'seed-ledger.json',ledger)
   write(root/'prepared.json',{'freeze_sha':sha(root/'freeze.json'),'agenda_sha':sha(root/'agenda.json'),
      'seed_ledger_sha':sha(root/'seed-ledger.json'),'cases':{'public/00.json':sha(case)}})
   check_prepared(root)
   source.write_text('changed\n')
   with self.assertRaisesRegex(ValueError,'source changed'):check_prepared(root)
   source.write_bytes(archived.read_bytes());case.write_text('{}\n')
   with self.assertRaisesRegex(ValueError,'case changed'):check_prepared(root)
