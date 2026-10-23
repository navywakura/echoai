"""Private inference handoff: no live network or GPU in these tests."""
import base64
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREPARE = runpy.run_path(str(ROOT/'repository/scripts/prepare_kaggle_repair.py'))['prepare']
DOWNLOAD = runpy.run_path(str(ROOT/'repository/scripts/kaggle_repair_worker.py'))['download']


class GPUHandoff(unittest.TestCase):
    def test_unsuccessful_local_repair_does_not_enable_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir()
            (run/'result.json').write_text(json.dumps({'episodes':[
                {'counterexamples_repaired':False,'final_cases_passed':False}]}))
            with self.assertRaisesRegex(ValueError,'prerequisite'):
                PREPARE(run,root/'upload','owner/private-test')
            self.assertFalse((root/'upload').exists())

    def test_upload_is_private_and_contains_no_private_oracle_or_receipt_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir()
            (run/'result.json').write_text(json.dumps({'episodes':[
                {'task':'example','arm':'E','counterexamples_repaired':True,'final_cases_passed':True}]}))
            task={k:'public' for k in ('description','property','checker','input_schema','preconditions')}
            task.update(id='example',input_json_schema={'type':'array'},
                        development_inputs=['PRIVATE_ORACLE_SENTINEL'])
            (run/'tasks.json').write_text(json.dumps([task]))
            ep=run/'example-E';tree=ep/'snapshots'/'version'/'tree';tree.mkdir(parents=True)
            (tree/'solution.py').write_text('print(0)')
            body={'role':'propose','snapshot':'version','repair_feedback':{
                'failures':[{'input':[1],'observed':0,'expected':1}], 'public_examples':[]}}
            (ep/'thought.jsonl').write_text(json.dumps({'body':body})+'\n')
            (ep/'authority').mkdir();(ep/'authority/key').write_text('AUTHORITY_SECRET_SENTINEL')
            out=root/'upload';PREPARE(run,out,'owner/private-test')
            self.assertIs(json.loads((out/'kernel-metadata.json').read_text())['is_private'],True)
            payload=(out/'input-local.json').read_text()
            self.assertNotIn('PRIVATE_ORACLE_SENTINEL',payload)
            self.assertNotIn('development_inputs',payload)
            self.assertNotIn('AUTHORITY_SECRET_SENTINEL',payload)
            self.assertIn('print(0)',payload)
            sources=json.loads((out/'upload-manifest.json').read_text())
            self.assertEqual(set(sources),{'repair-input.json','connector/pcworld/__init__.py',
                'connector/pcworld/provider.py','connector/pcworld/protocol.py','proposer-worker.py'})
            compile((out/'kernel.py').read_text(),'kernel.py','exec')

    def test_private_worker_source_embedding_rejects_path_escape(self):
        write=runpy.run_path(str(ROOT/'repository/scripts/prepare_kaggle_repair.py'))['write_bundle']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);bundle={'jobs':[], 'config':{}}
            write(bundle,root/'valid','owner/private-test',extra_sources={'inference_relay.py':'# transport only'})
            manifest=json.loads((root/'valid/upload-manifest.json').read_text())
            self.assertIn('inference_relay.py',manifest)
            self.assertTrue(json.loads((root/'valid/kernel-metadata.json').read_text())['is_private'])
            for i,name in enumerate(('../escape.py','/tmp/escape.py','proposer-worker.py')):
                with self.assertRaises(ValueError):
                    write(bundle,root/str(i),'owner/private-test',extra_sources={name:'bad'})

    def test_wrong_download_hash_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_bytes(b'wrong bytes')
            dest=root/'model'
            with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
                DOWNLOAD(source.as_uri(),dest,hashlib.sha256(b'expected').hexdigest())
            self.assertFalse(dest.exists())

    def test_imported_fixture_is_executed_hermetically_before_success(self):
        from echoai.pcworld.repairs import repair_tasks
        from echoai.pcworld.receipts import digest
        from echoai.pcworld.runtime import build_runtime
        from echoai.tests.test_pcworld_repair_gap import FIXED
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);run=root/'run';run.mkdir()
            task=repair_tasks()[1]
            (run/'tasks.json').write_text(json.dumps([task]))
            (run/'result.json').write_text('{}')
            failure={'input':[{'id':'b','value':2},{'id':'b','value':3}],
                     'observed':[{'id':'b','value':3}],'expected':[{'id':'b','value':2}]}
            job={'id':task['id'],'context':{'source':task['initial'],'repair_feedback':{'failures':[failure]}}}
            bundle={'jobs':[job],'config':{'model':'fixture-no-model'},
                    'local_run_result_sha256':hashlib.sha256((run/'result.json').read_bytes()).hexdigest()}
            inputs=root/'input.json';inputs.write_text(json.dumps(bundle))
            report={'input_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),
                    'candidate_executed_on_kaggle':False,'errors':[], 'origin':'unit-test fixture, not inference',
                    'records':[{'task':task['id'],'job_sha256':digest(job),'output':{'content':FIXED}}]}
            downloaded=root/'downloaded.json';downloaded.write_text(json.dumps(report))
            build_runtime(root/'runtime')
            cmd=[sys.executable,'-I','-B',str(ROOT/'repository/scripts/verify_kaggle_repair.py'),
                 str(run),str(inputs),str(downloaded),str(root/'runtime'),str(root/'verified')]
            check=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            self.assertEqual(check.returncode,0,check.stderr)
            result=json.loads((root/'verified/result.json').read_text())
            self.assertEqual(result['passed'],1)
            self.assertTrue(result['results'][0]['audit']['valid'])
            report['input_sha256']='0'*64;downloaded.write_text(json.dumps(report))
            cmd[-1]=str(root/'tampered')
            check=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            self.assertNotEqual(check.returncode,0)
            self.assertFalse((root/'tampered').exists())
