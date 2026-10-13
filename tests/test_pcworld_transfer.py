"""Cross-episode exposure must not bypass current verification or accounting."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

class Transfer(unittest.TestCase):
    def test_empty_library_lookup_is_charged_and_auditable(self):
        from echoai.pcworld.shared import SharedConceptLibrary
        from echoai.pcworld.pilot import run_pilot,audit_run
        with tempfile.TemporaryDirectory() as d:
            lib=SharedConceptLibrary(Path(d)/'library')
            report=run_pilot(Path(d)/'run',task_count=1,arms=('S',),shared_library=lib)
            r=report['episodes'][0]
            self.assertEqual(r['shared_memory']['lessons'],0)
            self.assertEqual(r['shared_memory']['tools'],1)
            self.assertTrue(r['development_accepted'])
            self.assertTrue(audit_run(Path(d)/'run')['valid'])

    def test_lesson_only_enters_first_proposal_and_cannot_skip_checks(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        class Library:
            path=Path('/unused-library')
            def identity(self):return 'a'*64
            def lookup(self,task):return [{'instruction':'Untrusted prior recipe, recheck', 'verified_patch':'fake'}]
        class Recording(FixtureProvider):
            def __init__(self):self.contexts=[]
            def call(self,role,task,context,**kw):
                self.contexts.append((role,context))
                return super().call(role,task,context,**kw)
        with tempfile.TemporaryDirectory() as d:
            provider=Recording()
            ep=Episode(Path(d)/'run',development_tasks(1)[0],'S',provider,shared_library=Library())
            result=ep.run()
            self.assertIn('shared_lessons',provider.contexts[0][1])
            self.assertTrue(all('shared_lessons' not in c for _,c in provider.contexts[1:]))
            self.assertTrue(result['final_properties'])
            self.assertTrue(any(role=='self_review' for role,_ in provider.contexts))

    def test_invalid_task_filter_fails_before_creating_run(self):
        from echoai.pcworld.pilot import run_pilot
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                run_pilot(Path(d)/'run',task_count=1,task_ids=['missing'])
            self.assertFalse((Path(d)/'run').exists())

    def test_empty_library_cannot_be_removed_after_run_to_pass_audit(self):
        from echoai.pcworld.shared import SharedConceptLibrary
        from echoai.pcworld.pilot import run_pilot,audit_run
        with tempfile.TemporaryDirectory() as d:
            lib=SharedConceptLibrary(Path(d)/'library')
            run_pilot(Path(d)/'run',task_count=1,arms=('S',),shared_library=lib)
            (lib.path/'receipts'/'receipts.jsonl').unlink()
            self.assertFalse(audit_run(Path(d)/'run')['valid'])

    def test_failed_lookup_charges_work_and_stops_inference(self):
        from echoai.pcworld.pilot import Episode
        from echoai.pcworld.tasks import FixtureProvider,development_tasks
        class Broken:
            def identity(self):raise ValueError('damaged provenance')
        with tempfile.TemporaryDirectory() as d:
            ep=Episode(Path(d)/'run',development_tasks(1)[0],'S',FixtureProvider(),shared_library=Broken())
            result=ep.run()
            self.assertFalse(result['development_accepted'])
            self.assertEqual(result['fixture_calls'],0)
            self.assertEqual(result['budget']['used']['tools'],1)
            self.assertIn('damaged provenance',result['error'])

    def test_metrics_no_repair_does_not_mean_no_critic_or_universal_proof(self):
        from echoai.pcworld.transfer import metrics
        ep=dict(development_accepted=True,tokens=100,llm_calls=3,repair_attempts=0,
                wall_ms=1,host_cpu_us=1,error=None,counterexamples=[],
                budget={'used':{'tools':8,'critic_calls':2}})
        result=metrics(ep)
        self.assertTrue(result['accepted_without_repair'])
        self.assertEqual(result['critic_calls'],2)
        ep['development_accepted']=False
        self.assertFalse(metrics(ep)['accepted_without_repair'])

    def test_publication_binds_exact_campaign_donor_and_payload(self):
        from echoai.pcworld.transfer import publication_matches,DONOR
        from echoai.pcworld.receipts import digest
        donor=Path('/tmp/current-donor')
        lesson={'source':'pass','provenance':{'run_dir':str(donor),'task_id':DONOR,
                                            'arm':'E','author_agent_id':'AGENT_A'}}
        pub={'lesson_sha256':digest(lesson)}
        self.assertTrue(publication_matches(lesson,pub,donor))
        self.assertFalse(publication_matches(lesson,pub,Path('/tmp/old-donor')))
        self.assertFalse(publication_matches({**lesson,'source':'changed'},pub,donor))
        for field in ('task_id','arm','author_agent_id'):
            wrong={**lesson,'provenance':{**lesson['provenance'],field:'wrong'}}
            self.assertFalse(publication_matches(wrong,{'lesson_sha256':digest(wrong)},donor))

    def test_paired_audit_requires_identical_runtime_and_episode_limits(self):
        from echoai.pcworld.transfer import run_settings_match
        c={'runtime_snapshot':'r','arms':['E'],'suite':'repair-v2',
           'cache_properties':False,'seeded_diagnostic':False,'episode_wall_seconds':900,
           'task_families':['records']}
        self.assertTrue(run_settings_match(c,'r'))
        for field,value in [('runtime_snapshot','other'),('episode_wall_seconds',1200),
                            ('arms',['S']),('seeded_diagnostic',True),('cache_properties',True),
                            ('suite','fixtures'),('task_families',['path'])]:
            self.assertFalse(run_settings_match({**c,field:value},'r'))
        self.assertFalse(run_settings_match(c,None))
