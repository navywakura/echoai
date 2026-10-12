from pathlib import Path
import importlib
import tempfile
import unittest

class Pilot(unittest.TestCase):
    def test_dry_run_never_calls_model_and_names_full_budget(self):
        p=importlib.import_module('echoai.pcworld.pilot')
        result=p.estimate(tasks=60,repetitions=2)
        self.assertEqual(result['episodes'],480);self.assertEqual(result['tokens_ceiling'],12000000)
        self.assertEqual(result['scientific_result'],'pending')
    def test_fixture_pipeline_receipts_are_auditable_not_llm_evidence(self):
        p=importlib.import_module('echoai.pcworld.pilot')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            report=p.run_pilot(root,task_count=1,arms=('S',),provider='fixture')
            self.assertEqual(len(report['episodes']),1)
            self.assertTrue(report['episodes'][0]['development_accepted'],report)
            self.assertEqual(report['llm_calls'],0)
            self.assertFalse(report['scientific_claim'])
            self.assertTrue(p.audit_run(root)['valid'])
    def test_cannot_open_confirmation_from_development_cli(self):
        p=importlib.import_module('echoai.pcworld.pilot')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'confirmation'):
                p.run_pilot(Path(d)/'nope',task_count=1,arms=('E',),provider='fixture',split='confirmation')
    def test_I2_initial_source_restore_is_charged_and_recorded(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        with tempfile.TemporaryDirectory() as d:
            episode=Episode(Path(d)/'run',development_tasks(1)[0],'I2',FixtureProvider())
            result=episode.run()
            self.assertTrue(result['development_accepted'])
            self.assertEqual(result['budget']['used']['tools'],17)
            patches=[r for r in episode.receipts.records if r['body'].get('operation')=='apply_patch'
                     and r['body']['kind']=='observation']
            self.assertEqual(len(patches),3)
    def test_audit_detects_provider_and_archived_source_changes(self):
        import json,os
        from echoai.pcworld.pilot import run_pilot,audit_run
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            report=run_pilot(root,task_count=1,arms=('S',))
            provider=root/'provider.json';original=provider.read_bytes()
            data=json.loads(original);data['model']='different-model';provider.write_text(json.dumps(data))
            self.assertFalse(audit_run(root)['valid'])
            provider.write_bytes(original)
            self.assertTrue(audit_run(root)['valid'])
            from echoai.pcworld.snapshots import SnapshotStore
            episode=report['episodes'][0]
            store=SnapshotStore(root/(episode['task']+'-'+episode['arm'])/'snapshots')
            snapshot=store.get(episode['candidate'])
            source=snapshot.root/'solution.py';os.chmod(source,0o600);source.write_text('changed')
            self.assertFalse(audit_run(root)['valid'])

class CounterexampleFlow(unittest.TestCase):
    def test_final_acceptance_requires_public_and_remembered_cases(self):
        from unittest.mock import patch
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        for failed_input in ([1,2],[100]):
            with self.subTest(failed_input=failed_input),tempfile.TemporaryDirectory() as d:
                episode=Episode(Path(d)/'run',development_tasks(1)[0],'S',FixtureProvider())
                episode.counterexamples=[[100]]
                def check(snapshot,value,**kw):
                    return {'input':value,'status':'contradicted' if value==failed_input else 'supported'}
                with patch.object(episode,'check',side_effect=check): result=episode.finish(episode.base)
                self.assertFalse(result['development_accepted'])
    def test_single_agent_can_self_review_and_repair_a_publicly_passing_bug(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        class SelfReviewer(FixtureProvider):
            def __init__(self): self.proposals=0;self.roles=[]
            def call(self,role,task,context,**kw):
                self.roles.append(role)
                if role=='propose':
                    self.proposals+=1
                    if self.proposals==1:
                        return {'content':task['initial']},{'tokens':0,'llm_calls':0,'fixture_calls':1}
                return super().call(role,task,context,**kw)
        with tempfile.TemporaryDirectory() as d:
            provider=SelfReviewer()
            result=Episode(Path(d)/'run',development_tasks(1)[0],'S',provider).run()
            self.assertTrue(result['development_accepted'])
            self.assertIn('self_review',provider.roles)
            self.assertNotIn('critic',provider.roles)
            self.assertEqual(result['counterexamples'],[[-3,2,2]])
    def test_critic_is_consulted_once_per_unchanged_candidate(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        class NoRepair(FixtureProvider):
            def call(self,role,task,context,**kw):
                if role=='propose':
                    return {'content':task['initial']},{'tokens':0,'llm_calls':0,'fixture_calls':1}
                return super().call(role,task,context,**kw)
        with tempfile.TemporaryDirectory() as d:
            result=Episode(Path(d)/'run',development_tasks(1)[0],'F',NoRepair()).run()
            self.assertEqual(result['budget']['used']['critic_calls'],1)
            self.assertFalse(result['development_accepted'])
    def test_actual_cpu_overrun_keeps_execution_receipt_and_full_charge(self):
        from unittest.mock import patch
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        from echoai.pcworld.accounting import BudgetExceeded
        with tempfile.TemporaryDirectory() as d:
            episode=Episode(Path(d)/'run',development_tasks(1)[0],'S',FixtureProvider())
            execution={'snapshot':episode.base.id,'argv':['/usr/bin/python3'],'status':'CPU_LIMIT',
                       'resources':{'cpu_us':4000000}}
            with patch('echoai.pcworld.pilot.execute',return_value=execution):
                with self.assertRaises(BudgetExceeded): episode.check(episode.base,[1])
            observations=[r for r in episode.receipts.records if 'execution' in r['body']]
            self.assertEqual(len(observations),1)
            self.assertEqual(episode.budget.report()['used']['cpu_us'],4000000)
            self.assertEqual(episode.budget.report()['pending'],0)
    def test_unknown_property_keeps_its_status_in_controller_feedback(self):
        from unittest.mock import patch
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        with tempfile.TemporaryDirectory() as d:
            episode=Episode(Path(d)/'run',development_tasks(1)[0],'E',FixtureProvider())
            with patch.object(episode,'check',return_value={'status':'unknown'}), \
                 patch('echoai.pcworld.pilot.choose',return_value='finish') as choose:
                episode.run()
            self.assertEqual(choose.call_args.kwargs['property_status'],'unknown')
    def test_T12_real_critic_counterexample_survives_into_repair(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        class FaultThenRepair(FixtureProvider):
            def __init__(self): self.proposals=0
            def call(self,role,task,context,**kw):
                if role!='critic':
                    self.proposals+=1
                    if self.proposals==1:
                        return {'content':task['initial']},{'tokens':0,'llm_calls':0,'fixture_calls':1}
                return super().call(role,task,context,**kw)
        with tempfile.TemporaryDirectory() as d:
            result=Episode(Path(d)/'run',development_tasks(1)[0],'F',FaultThenRepair()).run()
            self.assertTrue(result['development_accepted'],result)
            self.assertEqual(result['counterexamples'],[[-3,2,2]])
            self.assertGreaterEqual(result['fixture_calls'],3)

class HermeticPilot(unittest.TestCase):
    def test_repair_suite_requires_runtime_and_real_provider(self):
        from echoai.pcworld.pilot import run_pilot
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'pinned runtime'):
                run_pilot(Path(d)/'run',suite='repair-v1',task_count=1)
    def test_pure_cache_repeats_candidate_and_invalidates_changed_input(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        from echoai.pcworld.runtime import build_runtime
        from unittest.mock import patch
        from echoai.pcworld.runner import execute
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);runtime=build_runtime(root/'runtime')
            episode=Episode(root/'run',development_tasks(1)[0],'S',FixtureProvider(),runtime=runtime,cache_properties=True)
            with patch('echoai.pcworld.pilot.execute',wraps=execute) as run:
                episode.check(episode.base,[1,2]);episode.check(episode.base,[1,2]);episode.check(episode.base,[3])
                self.assertEqual(run.call_count,3)
            props=[r['body'] for r in episode.receipts.records if 'property_cache' in r['body']]
            self.assertEqual([p['property_cache']['hit'] for p in props],[False,True,False])
    def test_seeded_diagnostic_labels_fault_and_rechecks_repair(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        with tempfile.TemporaryDirectory() as d:
            episode=Episode(Path(d)/'run',development_tasks(1)[0],'F',FixtureProvider(),seeded_diagnostic=True)
            result=episode.run()
            self.assertTrue(result['seeded_diagnostic'])
            self.assertEqual(result['counterexamples'],[[-3,2,2]])
            self.assertTrue(result['development_accepted'])
    def test_checker_identity_includes_native_and_python_dependencies(self):
        from echoai.pcworld.pilot import checker_identity
        identity=checker_identity()
        names='\n'.join(identity['dependencies'])
        self.assertIn('fractions.py',names)
        self.assertIn('_csv.',names)
        self.assertIn('json/decoder.py',names)
        from unittest.mock import patch
        import csv
        before=identity
        with patch.object(csv,'reader',lambda *a,**k:iter([['changed']])):
            self.assertNotEqual(checker_identity(),before)
    def test_audit_requires_existing_cache_and_referenced_receipts(self):
        from echoai.pcworld.pilot import run_pilot,audit_run
        from echoai.pcworld.runtime import build_runtime
        from echoai.pcworld.property_cache import PropertyCache
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);runtime=build_runtime(root/'runtime')
            out=root/'run'
            result=run_pilot(out,task_count=1,arms=('S',),runtime=runtime,cache_properties=True)
            self.assertTrue(result['episodes'][0]['development_accepted'])
            self.assertTrue(audit_run(out)['valid'])
            cache=out/'dev-sum_positive-S/property-cache';cache.rename(root/'saved-cache')
            self.assertFalse(audit_run(out)['valid'])
            self.assertFalse(cache.exists(),'audit must not recreate missing custody')
            PropertyCache(cache)
            self.assertFalse(audit_run(out)['valid'],'empty authenticated cache cannot witness past hits')
